from functools import wraps
from time import time

from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.core.exceptions import YomboWarning
from yombo.utils import get_local_network_info, ip_address_in_network

from yombo.core.log import get_logger
logger = get_logger('library.webinterface.auth')


def get_session(roles=None, *args, **kwargs):

    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        def wrapped_f(webinterface, request, *a, **kw):
            session = webinterface.sessions.load(request)
            return call(f, webinterface, request, session, *a, **kw)
        return wrapped_f

    return deco

def require_auth(roles=None, login_redirect=None, *args, **kwargs):

    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        @inlineCallbacks
        def wrapped_f(webinterface, request, *a, **kw):
            request.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate')
            request.setHeader('Expires', '0')
            # print "auth wrapped_f roles: %s" % roles
            # print "auth wrapped_f request: %s" % request.received_cookies
            # print "auth wrapped_f request: %s" % type(request)

            # print "auth wrapped_f aa a: %s" % a
            # print "auth wrapped_f aa type(a): %s" % type(a)
            # for val in a:
            #     print "auth wrapped_f a val: %s" % val
            #     print "auth wrapped_f a type(val): %s" % type(val)
            # print "auth wrapped_f aa kw:"
            # for val in kw:
            #     print "auth wrapped_f kw val: %s" % val
            #
            # do your authentication here
            # webinterface = a[0]
            # request = a[1]
            # session = "mysession"

            # print "request:url: %s" % request.path
            if hasattr(request, 'breadcrumb') is False:
                request.breadcrumb = []
                webinterface.misc_wi_data['breadcrumb'] = request.breadcrumb

            try:
                session = yield webinterface.sessions.load(request)
            except YomboWarning as e:
                logger.warn("Discarding request, appears to be malformed session id.")
                page = webinterface.get_template(request, webinterface._dir + 'pages/login_user.html')
                # print "require_auth..session: %s" % session
                returnValue(page.render(alerts=webinterface.get_alerts()))

            if login_redirect is not None:
                if session is False:
                    try:
                        session = webinterface.sessions.create(request)
                    except YomboWarning as e:
                        logger.warn("Discarding request, appears to be malformed request. Unable to create session.")
                        page = webinterface.get_template(request, webinterface._dir + 'pages/login_user.html')
                        # print "require_auth..session: %s" % session
                        returnValue(page.render(alerts=webinterface.get_alerts()))
                    session['auth'] = False
                    session['auth_id'] = ''
                    session['auth_time'] = 0
                    session['yomboapi_session'] = ''
                    session['yomboapi_login_key'] = ''
                    request.received_cookies[webinterface.sessions.config.cookie_session] = session.session_id
                session['login_redirect'] = login_redirect

            if needs_web_pin(webinterface, request):
                page = webinterface.get_template(request, webinterface._dir + 'pages/login_pin.html')
                returnValue(page.render(alerts=webinterface.get_alerts()))
                # return page.render(alerts=webinterface.get_alerts())
                # data=webinterface.data)

            if session is not False:
                if 'auth' in session:
                    if session['auth'] is True:
                        session.touch()
                        # try:
                        #     del session['login_redirect']
                        # except:
                        #     pass
                        results = yield call(f, webinterface, request, session, *a, **kw)
                        returnValue(results)
                        # return call(f, webinterface, request, session, *a, **kw)

            page = webinterface.get_template(request, webinterface._dir + 'pages/login_user.html')
            # print "require_auth..session: %s" % session
            returnValue(page.render(alerts=webinterface.get_alerts()))
                               # data=webinterface.data)
        return wrapped_f
    return deco

def require_auth_pin(*args, **kwargs):
    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        def wrapped_f(webinterface, request, *a, **kw):
            request.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate')
            request.setHeader('Expires', '0')
            # print "auth wrapped_f request: %s" % request.received_cookies
            # print "auth wrapped_f request: %s" % type(request)

            # print "auth wrapped_f aa a: %s" % a
            # print "auth wrapped_f aa type(a): %s" % type(a)
            # for val in a:
            #     print "auth wrapped_f a val: %s" % val
            #     print "auth wrapped_f a type(val): %s" % type(val)
            # print "auth wrapped_f aa kw:"
            # for val in kw:
            #     print "auth wrapped_f kw val: %s" % val

            # do your authentication here
            # webinterface = a[0]
            # request = a[1]
            # session = "mysession"
            if hasattr(request, 'breadcrumb') is False:
                request.breadcrumb = []
                webinterface.misc_wi_data['breadcrumb'] = request.breadcrumb

            if needs_web_pin(webinterface, request):
                page = webinterface.get_template(request, webinterface._dir + 'pages/login_pin.html')
                return page.render(alerts=webinterface.get_alerts(),
                               data=webinterface.data)

            return call(f, webinterface, request, *a, **kw)
        return wrapped_f
    return deco

def run_first(*args, **kwargs):
    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        def wrapped_f(webinterface, request, *a, **kw):
            webinterface.webapp.templates.globals['_'] = webinterface.i18n(request)
            # request._ = webinterface.i18n(request)
            # if hasattr(request, 'breadcrumb') is False:
            #     request.breadcrumb = []
            #     webinterface.misc_wi_data['breadcrumb'] = request.breadcrumb
            return call(f, webinterface, request, *a, **kw)
        return wrapped_f
    return deco

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
    if ip_address_in_network(client_ip, network_info['ipv4']['cidr']):
        if client_ip != network_info['ipv4']['gateway']:
            return False

    if webinterface.auth_pin_required:
        cookie_pin = webinterface.sessions.config.cookie_pin
        if cookie_pin in request.received_cookies:
            return False
#            print "auth pin:::: %s" % session
        # had to break these up... - kept dieing on me
        if webinterface._display_pin_console_time < int(time())-30:
            webinterface._display_pin_console_time = int(time())
            webinterface.display_pin_console()

        return True
    return False
