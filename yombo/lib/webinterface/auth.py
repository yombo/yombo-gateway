from functools import wraps
from time import time
import traceback
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.sessions import Session
from yombo.utils import get_local_network_info, ip_addres_in_local_network, bytes_to_unicode

from yombo.core.log import get_logger
logger = get_logger('library.webinterface.auth')


def return_api_error(request, message=None, status=None):
    request.setHeader('Content-Type', 'application/json')
    if status is None:
        status = 401
    request.setResponseCode(status)
    if message is None:
        message = "Not authorized"
    return json.dumps({
        'status': status,
        'message': message,
    })

def get_session(roles=None, *args, **kwargs):

    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        def wrapped_f(webinterface, request, *a, **kw):
            session = yield webinterface.sessions.load(request)
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


def run_first(*args, **kwargs):
    # print("run first.... 1")
    # for arg in args:
    #     print("arg: %s" % arg)
    # print("run first.... 2 %s" % kwargs)
    # for kwarg, value in kwargs.items():
    #     print("kwarg: %s -> " % (kwarg, value))
    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        @inlineCallbacks
        def wrapped_f(webinterface, request, *a, **kw):
            update_request(webinterface, request)
            # request._ = webinterface.i18n(request)

            request.auth_id = None
            try:
                session = yield webinterface.sessions.load(request)
            except YomboWarning as e:
                logger.warn("Discarding request, appears to be malformed session id.")
                page = webinterface.get_template(request, webinterface._dir + 'pages/login_user.html')
                return page.render(alerts=webinterface.get_alerts())

            if session is not False:
                if 'auth' in session:
                    if session['auth'] is True:
                        session.touch()
                        request.auth_id = session['auth_id']

            return call(f, webinterface, request, session, *a, **kw)
            # return call(f, webinterface, request, *a, **kw)
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

            host = request.getHeader('host')
            if host is None:
                logger.warn("Discarding request, appears to be malformed session id.")
                return return_need_login(webinterface, request, False, **kwargs)
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
                session = yield webinterface.sessions.load(request)
            except YomboWarning as e:
                logger.warn("Discarding request, appears to be malformed session id.")
                return return_need_login(webinterface, request, False, **kwargs)

            if isinstance(session, Session):  # if we have a session, then inspect to see if it's valid.
                if 'auth' in session:
                    if session['auth'] is True:
                        session.touch()
                        request.auth_id = session['auth_id']
                        try:
                            results = yield call(f, webinterface, request, session, *a, **kw)
                            return results
                        except Exception as e: # catch anything here...so can display details.
                            logger.error("---------------==(Traceback)==--------------------------")
                            logger.error("{trace}", trace=traceback.format_exc())
                            logger.error("--------------------------------------------------------")
                            page = webinterface.get_template(request, webinterface._dir + 'pages/misc/traceback.html')
                            return page.render(traceback=traceback.format_exc())
            else:  # session doesn't exist
                if login_redirect is not None: # only create a new session if we need too
                    if session is False:
                        try:
                            session = webinterface.sessions.create(request)
                        except YomboWarning as e:
                            logger.warn("Discarding request, appears to be malformed request. Unable to create session.")
                            return return_need_login(webinterface, request, False, **kwargs)
                        session['auth_pin'] = False
                        session['auth'] = False
                        session['auth_id'] = ''
                        session['auth_at'] = 0
                        session['yomboapi_session'] = ''
                        session['yomboapi_login_key'] = ''
                        request.received_cookies[webinterface.sessions.config.cookie_session_name] = session.session_id
                    session['login_redirect'] = login_redirect

            return return_need_login(webinterface, request, session, **kwargs)
        return wrapped_f
    return deco


def require_auth_pin(roles=None, login_redirect=None, *args, **kwargs):
    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        @inlineCallbacks
        def wrapped_f(webinterface, request, *a, **kw):
            update_request(webinterface, request)
            request.auth_id = None

            host = request.getHeader('host')
            host_info = host.split(':')
            if host is None:
                logger.warn("Discarding request, appears to be malformed session id.")
                return return_need_login(webinterface, request, False, **kwargs)
            request.requestHeaders.setRawHeaders('host_name', [host_info[0]])

            if len(host_info) > 1:
                request.requestHeaders.setRawHeaders('host_port', [host_info[1]])
            else:
                request.requestHeaders.setRawHeaders('host_port', [None])

            if hasattr(request, 'breadcrumb') is False:
                request.breadcrumb = []
                webinterface.misc_wi_data['breadcrumb'] = request.breadcrumb

            try:
                session = yield webinterface.sessions.load(request)  # will be None if nothing found.
            except YomboWarning as e:
                logger.warn("Discarding request, appears to be malformed session id.")
                return return_need_pin(webinterface, request, **kwargs)

            if check_needs_web_pin(webinterface, request, session):
                if isinstance(session, Session):  # if we have a session, then inspect to see if it's valid.
                    if 'auth_pin' in session:
                        if session['auth_pin'] is True:
                            session.touch()
                            request.auth_id = session['auth_id']
                            results = yield call(f, webinterface, request, session, *a, **kw)
                            return results
                else:  # session doesn't exist
                    if login_redirect is not None:  # only create a new session if we need too
                        if session is None:
                            try:
                                session = webinterface.sessions.create(request)
                            except YomboWarning as e:
                                logger.warn(
                                    "Discarding request, appears to be malformed request. Unable to create session.")
                                return return_need_pin(webinterface, request, **kwargs)
                            session['auth_pin'] = False
                            session['auth'] = False
                            session['auth_id'] = ''
                            session['auth_at'] = 0
                            session['yomboapi_session'] = ''
                            session['yomboapi_login_key'] = ''
                            request.received_cookies[webinterface.sessions.config.cookie_session_name] = session.session_id
                        session['login_redirect'] = login_redirect
            else:
                results = yield call(f, webinterface, request, session, *a, **kw)
                return results

            return return_need_pin(webinterface, request, **kwargs)
        return wrapped_f
    return deco


def return_need_login(webinterface, request, session, **kwargs):
    if check_needs_web_pin(webinterface, request, session):
        return return_need_pin(webinterface, request, **kwargs)
    else:
        if 'api' in kwargs and kwargs['api'] is True:
            return return_api_error(request, 'error with request', 500)
    page = webinterface.get_template(request, webinterface._dir + 'pages/login_user.html')
    return page.render(alerts=webinterface.get_alerts())


def return_need_pin(webinterface, request, **kwargs):
    if 'api' in kwargs and kwargs['api'] is True:
        return return_api_error(request, 'submit pin first')
    if webinterface._display_pin_console_at < int(time()) - 30:
        webinterface._display_pin_console_at = int(time())
        webinterface.display_pin_console()
    page = webinterface.get_template(request, webinterface._dir + 'pages/login_pin.html')
    return page.render(alerts=webinterface.get_alerts())


def check_needs_web_pin(webinterface, request, session):
    """
    First checks if request is within the local network, we don't prompt for pin.

    If otherwise, we check the cookies to see if client already sent a valid pin.

    :param webinterface:
    :param request:
    :return:
    """
    if webinterface.auth_pin_required is False:  # if user has configured gateway to require a pin
        return False

    client_ip = request.getClientIP()
    if client_ip == "127.0.0.1":
        return False

    if ip_addres_in_local_network(client_ip):
        return False

    if session is False or session is None:
        return True

    if session['auth_pin'] is True:
        return False
    return True  # catch all...just in case.
