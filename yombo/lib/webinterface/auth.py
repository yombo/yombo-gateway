from functools import wraps
from time import time
import traceback
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from ratelimit import RateLimitException

from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboWarning, YomboRestart
from yombo.utils import ip_addres_in_local_network, bytes_to_unicode, sha256_compact
from yombo.lib.webinterface.routes.api_v1.__init__ import return_error, args_to_dict

from yombo.core.log import get_logger
logger = get_logger('library.webinterface.auth')


def get_session(roles=None, *args, **kwargs):

    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        def wrapped_f(webinterface, request, *a, **kw):
            session = yield webinterface._WebSessions.load(request)
            return call(f, webinterface, request, session, *a, **kw)
        return wrapped_f
    return deco


def update_request(webinterface, request):
    """
    Does some basic conversions for us.

    :param request: 
    :return: 
    """
    request.received_cookies = bytes_to_unicode(request.received_cookies)
    request.args = bytes_to_unicode(request.args)
    webinterface.webapp.templates.globals['_'] = webinterface.i18n(request)
    request.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate')
    request.setHeader('Expires', '0')


def check_idempotence(webinterface, request, session):
    idempotence = request.getHeader('x-idempotence')
    if idempotence is None:
        arguments = args_to_dict(request.args)
        idempotence = arguments.get('_idempotence', None)
    request.idempotence = idempotence
    if idempotence is not None:
        idempotence = sha256_compact("%s:%s" % (session.user_id, idempotence))
        if idempotence in webinterface.idempotence:
            return return_error(request, 'idempotence error', 409,
                                "This idempotence key has already be processed.")
        webinterface.idempotence[idempotence] = int(time())
        return True
    return False


def run_first(create_session=None, *args, **kwargs):
    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        @inlineCallbacks
        def wrapped_f(webinterface, request, *a, **kw):
            session = None
            update_request(webinterface, request)
            request.auth_id = None
            host = request.getHeader('host')
            if host is None:
                logger.info("Discarding request, appears to be malformed host header")
                return return_need_login(webinterface, request, None, **kwargs)
            host_info = host.split(':')
            request.requestHeaders.setRawHeaders('host_name', [host_info[0]])

            if len(host_info) > 1:
                request.requestHeaders.setRawHeaders('host_port', [host_info[1]])
            else:
                request.requestHeaders.setRawHeaders('host_port', [None])

            if hasattr(request, 'breadcrumb') is False:
                request.breadcrumb = []
                webinterface.misc_wi_data['breadcrumb'] = request.breadcrumb

            try:
                session = webinterface._APIAuth.get_session_from_request(request)
                session.touch()
            except YomboWarning as e:
                try:
                    session = yield webinterface._WebSessions.get_session_from_request(request)
                    session.touch()
                except YomboWarning as e:
                    pass

            try:
                if create_session is True:
                    session = webinterface._WebSessions.create_from_request(request)
            except RateLimitException as e:
                logger.warn("Too many sessions being created, stopping this one!")
                return _("ui::messages::rate_limit_exceeded", "Too many attempts, try again later.")

            if session is not None:
                if session.check_valid():
                    request.auth_id = session.auth_id

            results = yield call(f, webinterface, request, session, *a, **kw)
            return results
        return wrapped_f
    return deco


def require_auth(roles=None, login_redirect=None, *args, **kwargs):
    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        @inlineCallbacks
        def wrapped_f(webinterface, request, *a, **kw):
            update_request(webinterface, request)
            request.auth_id = None
            # print(request)

            host = request.getHeader('host')
            if host is None:
                logger.info("Discarding request, appears to be malformed host header")
                return return_need_login(webinterface, request, None, **kwargs)
            host_info = host.split(':')
            request.requestHeaders.setRawHeaders('host_name', [host_info[0]])

            if len(host_info) > 1:
                request.requestHeaders.setRawHeaders('host_port', [host_info[1]])
            else:
                request.requestHeaders.setRawHeaders('host_port', [None])

            if hasattr(request, 'breadcrumb') is False:
                request.breadcrumb = []
                webinterface.misc_wi_data['breadcrumb'] = request.breadcrumb

            if 'api' in kwargs and kwargs['api'] is True:
                try:
                    session = webinterface._APIAuth.get_session_from_request(request)
                    session.touch()
                except YomboWarning as e:
                    logger.debug("API key not found, trying web session (cookie).")
                    try:
                        session = yield webinterface._WebSessions.get_session_from_request(request)
                    except YomboWarning as e:
                        logger.info("API request doesn't have session cookie. Bye bye: {e}", e=e)
                        return return_need_login(webinterface, request, None, **kwargs)
                    results = check_idempotence(webinterface, request, session)
                    if isinstance(results, bool) is False:
                        return results
            else:
                try:
                    session = yield webinterface._WebSessions.get_session_from_request(request)
                except YomboWarning as e:
                    setup_login_redirect(webinterface, request, None, login_redirect)
                    logger.debug("Discarding request, api requests not accepted: {e}", e=e)
                    logger.debug("Request: {request}", request=request)
                    return return_need_login(webinterface, request, None, **kwargs)

            if session.session_type == "websession":  # if we have a session, then inspect to see if it's valid.
                if session.check_valid() is False:
                    return return_need_login(webinterface, request, session, **kwargs)

            elif session.session_type == "apiauth":  # If we have an API session, we are good if it's valid.
                if session.check_valid() is False:
                    return return_need_login(webinterface,
                                             request,
                                             session,
                                             api_message="API Key is not valid.",
                                             **kwargs)
            session.touch()
            request.auth_id = session.auth_id
            # if session.session_type == "websession":
            #     print("auth type websession")
            #     try:
            #         print("pre check_if_gw_info_needed")
            #         yield webinterface._Startup.check_has_valid_gw_auth(session=session['yomboapi_session'])
            #         print("post check_if_gw_info_needed")
            #     except YomboRestart:
            #         print("YomboRestart check_if_gw_info_needed")
            #         webinterface._Notifications.add({'title': 'Restarting',
            #                                          'message': 'The gateway has downloaded an update that requires a restart. Please wait.',
            #                                          'source': 'System',
            #                                          'persist': False,
            #                                          'priority': 'high',
            #                                          'always_show': True,
            #                                          'always_show_allow_clear': False,
            #                                          'id': 'system_rebooting',
            #                                          'local': True,
            #                                          })
            #         page = webinterface.get_template(request, webinterface.wi_dir + '/pages/restart.html')
            #         return page.render(alerts=webinterface.get_alerts())

            try:
                results = yield call(f, webinterface, request, session, *a, **kw)
                return results
            except Exception as e:  # catch anything here...so can display details.
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("Function: {f}", f=f)
                logger.error("Request: {request}", request=request)
                logger.error("{trace}", trace=traceback.format_exc())
                logger.error("--------------------------------------------------------")
                content_type = request.getHeader('content-type')
                if isinstance(content_type, str):
                    content_type = content_type.lower()
                else:
                    content_type = ''
                if 'json' in content_type:
                    return return_error(request, 'Server Error', 500, traceback.format_exc())
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/misc/traceback.html')
                return page.render(traceback=traceback.format_exc())

        return wrapped_f
    return deco


def require_auth_pin(roles=None, login_redirect=None, create_session=None, *args, **kwargs):
    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        @inlineCallbacks
        def wrapped_f(webinterface, request, *a, **kw):
            update_request(webinterface, request)
            request.auth_id = None

            host = request.getHeader('host')
            if host is None:
                logger.info("Discarding request, appears to be malformed host header")
                return return_need_pin(webinterface, request, **kwargs)
            host_info = host.split(':')
            request.requestHeaders.setRawHeaders('host_name', [host_info[0]])

            if len(host_info) > 1:
                request.requestHeaders.setRawHeaders('host_port', [host_info[1]])
            else:
                request.requestHeaders.setRawHeaders('host_port', [None])

            if hasattr(request, 'breadcrumb') is False:
                request.breadcrumb = []
                webinterface.misc_wi_data['breadcrumb'] = request.breadcrumb

            try:
                session = yield webinterface._WebSessions.get_session_from_request(request)
            except YomboWarning as e:
                logger.info("No session found: {e}", e=e)
                if create_session is True:
                    try:
                        if create_session is True:
                            session = webinterface._WebSessions.create_from_request(request)
                    except RateLimitException as e:
                        logger.warn("Too many sessions being created!")
                        return _("ui::messages::rate_limit_exceeded", "Too many attempts, try again later.")
                else:
                    session = None


            if check_needs_web_pin(webinterface, request, session):
                if session is None:
                    return return_need_pin(webinterface, request, **kwargs)

                if session.session_type == 'websession':  # if we have a websession, then inspect to see if it's valid.
                    if 'auth_pin' in session:
                        if session['auth_pin'] is True:
                            session.touch()
                            request.auth_id = session.auth_id
                            results = yield call(f, webinterface, request, session, *a, **kw)
                            return results
                elif session.session_type == "apiauth":  # If we have an API session, we are good if it's valid.
                    if session.check_valid() is False:
                        return return_need_pin(webinterface, request, **kwargs)
                    results = yield call(f, webinterface, request, session, *a, **kw)
                    return results
                else:
                    return return_need_pin(webinterface, request, **kwargs)

            else:
                if session.check_valid():
                    request.auth_id = session.auth_id
                results = yield call(f, webinterface, request, session, *a, **kw)
                return results
        return wrapped_f
    return deco


def setup_login_redirect(webinterface, request, session, login_redirect):
    """
    If login_redirect is not none, return a session. Either create a new session or
    update the existing session.

    :param webinterface:
    :param request:
    :param login_redirect:
    :return:
    """
    if login_redirect is None:  # only create a new session if we need too
        return

    if session is None:
        try:
            session = webinterface._WebSessions.create_from_request(request)
        except YomboWarning as e:
            logger.warn("Discarding request, appears to be malformed request. Unable to create session.")
            return return_need_login(webinterface, request, None)
        except RateLimitException as e:
            logger.warn("Too sessions being created!")
            return _("ui::messages::rate_limit_exceeded", "Too many attempts, try again later.")

    session.create_type = 'login_redirect'
    request.received_cookies[webinterface._WebSessions.config.cookie_session_name] = session.session_id
    session['login_redirect'] = login_redirect
    return session


def return_need_login(webinterface, request, session, api_message=None, **kwargs):
    if check_needs_web_pin(webinterface, request, session):
        return return_need_pin(webinterface, request, **kwargs)
    else:
        content_type = request.getHeader('content-type')
        if isinstance(content_type, str):
            content_type = content_type.lower()
        else:
            content_type = ''
        if ('api' in kwargs and kwargs['api'] is True) or 'json' in content_type:
            return return_error(request, 'Unauthorized', 401, api_message)
    page = webinterface.get_template(request, webinterface.wi_dir + '/pages/login_user.html')
    return page.render(alerts=webinterface.get_alerts())


def return_need_pin(webinterface, request, **kwargs):
    content_type = request.getHeader('content-type')
    if isinstance(content_type, str):
        content_type = content_type.lower()
    else:
        content_type = ''
    if ('api' in kwargs and kwargs['api'] is True) or 'json' in content_type:
        return return_error(request, 'Unauthorized - Pin required', 401)
    if webinterface._display_pin_console_at < int(time()) - 30:
        webinterface._display_pin_console_at = int(time())
        webinterface.display_pin_console()
    page = webinterface.get_template(request, webinterface.wi_dir + '/pages/login_pin.html')
    return page.render(alerts=webinterface.get_alerts())


def check_needs_web_pin(webinterface, request, session):
    """
    First checks if request is within the local network, we don't prompt for pin.

    If otherwise, we check the cookies to see if client already sent a valid pin.

    :param webinterface:
    :param request:
    :return:
    """
    # print("CNWP: %s" % session)
    if session is not None and 'auth_pin' in session and session['auth_pin'] is True:
        return False

    if webinterface.auth_pin_required is False:  # if user has configured gateway to not require a pin
        return False

    client_ip = request.getClientIP()
    if client_ip == "127.0.0.1":
        return False

    if ip_addres_in_local_network(client_ip):
        return False

    return True  # catch all...just in case.
