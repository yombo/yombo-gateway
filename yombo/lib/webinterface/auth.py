from functools import wraps
from time import time
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.core.exceptions import YomboWarning
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
    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        @inlineCallbacks
        def wrapped_f(webinterface, request, *a, **kw):
            update_request(webinterface, request)
            # request._ = webinterface.i18n(request)
            # if hasattr(request, 'breadcrumb') is False:
            #     request.breadcrumb = []
            #     webinterface.misc_wi_data['breadcrumb'] = request.breadcrumb
            # print("session: %s" % session.__dict__)

            request.auth_id = None
            try:
                session = yield webinterface.sessions.load(request)
            except YomboWarning as e:
                logger.warn("Discarding request, appears to be malformed session id.")
                page = webinterface.get_template(request, webinterface._dir + 'pages/login_user.html')
                # print "require_auth..session: %s" % session
                returnValue(page.render(alerts=webinterface.get_alerts()))

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
                return return_need_login(webinterface, request, **kwargs)

            if session is not None:  # if we have a session, they may pass
                if 'auth' in session:
                    if session['auth'] is True:
                        session.touch()
                        request.auth_id = session['auth_id']
                        results = yield call(f, webinterface, request, session, *a, **kw)
                        return results
            else:  # session doesn't exist
                if login_redirect is not None: # only create a new session if we need too
                    if session is None:
                        try:
                            session = webinterface.sessions.create(request)
                        except YomboWarning as e:
                            logger.warn("Discarding request, appears to be malformed request. Unable to create session.")
                            return return_need_login(webinterface, request, **kwargs)
                        session['auth_pin'] = False
                        session['auth'] = False
                        session['auth_id'] = ''
                        session['auth_time'] = 0
                        session['yomboapi_session'] = ''
                        session['yomboapi_login_key'] = ''
                        request.received_cookies[webinterface.sessions.config.cookie_session] = session.session_id
                    session['login_redirect'] = login_redirect

            return return_need_login(webinterface, request, **kwargs)
        return wrapped_f
    return deco


def return_need_login(webinterface, request, **kwargs):
    if needs_web_pin(webinterface, request):
        if 'api' in kwargs and kwargs['api'] is True:
            return return_api_error(request, 'submit pin first')
        page = webinterface.get_template(request, webinterface._dir + 'pages/login_pin.html')
    else:
        if 'api' in kwargs and kwargs['api'] is True:
            return return_api_error(request, 'error with request', 500)
        page = webinterface.get_template(request, webinterface._dir + 'pages/login_user.html')
    return page.render(alerts=webinterface.get_alerts())


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
            # print("jjj")

            if needs_web_pin(webinterface, request):
                # print("jjj 2")
                if session is not None:  # if we have a session, they may pass
                    if 'auth_pin' in session:
                        # print("kkk 1")
                        if session['auth_pin'] is True:
                            # print("kkkk 2")
                            session.touch()
                            request.auth_id = session['auth_id']
                            results = yield call(f, webinterface, request, session, *a, **kw)
                            return results
                else:  # session doesn't exist
                    # print("mmm")
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
                            session['auth_time'] = 0
                            session['yomboapi_session'] = ''
                            session['yomboapi_login_key'] = ''
                            request.received_cookies[webinterface.sessions.config.cookie_session] = session.session_id
                        session['login_redirect'] = login_redirect
            else:
                # print("qqq 2")
                results = yield call(f, webinterface, request, session, *a, **kw)
                return results

            return return_need_pin(webinterface, request, **kwargs)
        return wrapped_f
    return deco


def return_need_pin(webinterface, request, **kwargs):
    if 'api' in kwargs and kwargs['api'] is True:
        return return_api_error(request, 'submit pin first')
    page = webinterface.get_template(request, webinterface._dir + 'pages/login_pin.html')
    return page.render(alerts=webinterface.get_alerts())


def needs_web_pin(webinterface, request):
    """
    First checks if request is within the local network, we don't prompt for pin.

    If otherwise, we check the cookies to see if client already sent a valid pin.

    :param webinterface:
    :param request:
    :return:
    """
    client_ip = request.getClientIP()
    if client_ip == "127.0.0.1":
        return False

    network_info = get_local_network_info()
    if ip_addres_in_local_network(client_ip):
        return False

    if webinterface.auth_pin_required:  # if user has configured gateway to require a pin
        cookie_pin = webinterface.sessions.config.cookie_pin
        if cookie_pin in request.received_cookies:  # and it matches a submitted one,
            return False  # then we don't need one.

        # had to break these up... - kept dieing on me
        # Display the PIN to the console for the user to see, but only once every 30 seconds at most.
        if webinterface._display_pin_console_time < int(time())-30:
            webinterface._display_pin_console_time = int(time())
            webinterface.display_pin_console()
        return True
    return False
