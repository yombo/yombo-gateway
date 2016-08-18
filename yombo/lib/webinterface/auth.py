from functools import wraps
from time import time

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

            session = webinterface.sessions.load(request)

            if needs_web_pin(webinterface, session):
                page = webinterface.get_template(request, webinterface._dir + 'pages/login_pin.html')
                return page.render(alerts=webinterface.get_alerts(),
                               data=webinterface.data,
                           )

            if session is not None:
                if 'auth' in session:
                    if session['auth'] is True:
        #                    print "ddd:33"
                        session['last_access'] = int(time())
                        try:
                            del session['login_redirect']
                        except:
                            pass
                        return call(f, webinterface, request, session, *a, **kw)
            if login_redirect is not None:
                session.set('login_redirect', login_redirect)
            page = webinterface.get_template(request, webinterface._dir + 'pages/login_user.html')
            # print "require_auth..session: %s" % session
            return page.render(alerts=webinterface.get_alerts(),
                               data=webinterface.data,
                               )
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

            session = webinterface.sessions.load(request)

            if needs_web_pin(webinterface, session):
                page = webinterface.get_template(request, webinterface._dir + 'pages/login_pin.html')
                return page.render(alerts=webinterface.get_alerts(),
                               data=webinterface.data,
                           )
            return call(f, webinterface, request, session, *a, **kw)
        return wrapped_f
    return deco

def needs_web_pin(webinterface, session):
    if webinterface.auth_pin_required:
#            print "auth pin:::: %s" % session
        # had to break these up... - kept dieing on me
        has_pin = False
        if session is not None:
            if 'auth_pin' in session:
                if session['auth_pin'] is True:
                    has_pin = True

        if has_pin is False:
            if webinterface._display_pin_console_time < int(time())-30:
                webinterface._display_pin_console_time = int(time())
                webinterface.display_pin_console()
            if has_pin is False:
                if webinterface._display_pin_console_time < int(time())-30:
                    webinterface._display_pin_console_time = int(time())
                    webinterface.display_pin_console()
            return True
    return False
