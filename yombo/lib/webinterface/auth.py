from functools import wraps
from time import time
from yombo.utils import get_local_network_info, ip_address_in_network

from twisted.internet.defer import inlineCallbacks, returnValue

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
        # @inlineCallbacks
        def wrapped_f(webinterface, request, *a, **kw):
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

            session = webinterface.sessions.load(request)
            if login_redirect is not None:
                if session is False:
                    session = webinterface.sessions.create(request)
                    session['auth'] = False
                    session['auth_id'] = ''
                    session['auth_time'] = 0
                    session['yomboapi_session'] = ''
                    session['yomboapi_login_key'] = ''
                    request.received_cookies[webinterface.sessions.config.cookie_session] = session.session_id
                session['login_redirect'] = login_redirect

            if needs_web_pin(webinterface, request):
                page = webinterface.get_template(request, webinterface._dir + 'pages/login_pin.html')
                return page.render(alerts=webinterface.get_alerts())
                               # data=webinterface.data)


            if session is not False:
                if 'auth' in session:
                    if session['auth'] is True:
        #                    print "ddd:33"
                        session['last_access'] = int(time())
                        # try:
                        #     del session['login_redirect']
                        # except:
                        #     pass
                        return call(f, webinterface, request, session, *a, **kw)
            print "session : %s" % session


            page = webinterface.get_template(request, webinterface._dir + 'pages/login_user.html')
            # print "require_auth..session: %s" % session
            return page.render(alerts=webinterface.get_alerts())
                               # data=webinterface.data)
        return wrapped_f

    return deco

def require_auth_pin(*args, **kwargs):
    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        def wrapped_f(webinterface, request, *a, **kw):
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

            if needs_web_pin(webinterface, request):
                page = webinterface.get_template(request, webinterface._dir + 'pages/login_pin.html')
                return page.render(alerts=webinterface.get_alerts(),
                               data=webinterface.data)

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
    if ip_address_in_network(client_ip, network_info['cidr']):
        if client_ip != network_info['gateway']:
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
