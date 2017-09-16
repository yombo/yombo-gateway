# Import python libraries
from time import time
from random import randint

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, Deferred, maybeDeferred
from twisted.web.static import File

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth_pin, require_auth, run_first
import yombo.ext.totp
import yombo.utils

def route_home(webapp):
    with webapp.subroute("") as webapp:

        @webapp.route('/')
        def home(webinterface, request):
            if webinterface.operating_mode == 'config':
                return config_home(webinterface, request)
            elif webinterface.operating_mode == 'first_run':
                return first_run_home(webinterface, request)
            return run_home(webinterface, request)

        @require_auth()
        def run_home(webinterface, request, session):
            # print("run_home aaaaaa")
            page = webinterface.webapp.templates.get_template(webinterface._dir + 'pages/index.html')
            delayed_device_commands = webinterface._Devices.get_delayed_commands()
            return page.render(alerts=webinterface.get_alerts(),
                               device_commands_delayed = delayed_device_commands,
                               automation_rules = len(webinterface._Loader.loadedLibraries['automation'].rules),
                               devices=webinterface._Libraries['devices'].devices,
                               modules=webinterface._Libraries['modules'].modules,
                               # states=webinterface._Libraries['states'].get_states(),
                               )

        @require_auth()
        def config_home(webinterface, request, session):
            # auth = webinterface.require_auth(request)
            # if auth is not None:
            #     return auth

            page = webinterface.get_template(request, webinterface._dir + 'config_pages/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )
        @run_first()
        def first_run_home(webinterface, request, session):
            return webinterface.redirect(request, '/setup_wizard/1')

        @webapp.route('/logout')
        @run_first()
        def page_logout_get(webinterface, request, session):
            try:
                webinterface.sessions.close_session(request)
            except:
                pass
            return webinterface.redirect(request, "/?")

        @webapp.route('/login/user', methods=['GET'])
        @require_auth_pin()
        def page_login_user_get(webinterface, request, session):
            return webinterface.redirect(request, '/?')

        @webapp.route('/login/user', methods=['POST'])
        @require_auth_pin()
        @inlineCallbacks
        def page_login_user_post(webinterface, request, session):
            # print("rquest.args: %s"  % request.args)
            if 'g-recaptcha-response' not in request.args:
                webinterface.add_alert('Captcha Missing', 'warning')
                return login_redirect(webinterface, request)
            if 'email' not in request.args:
                webinterface.add_alert('Email Missing', 'warning')
                return login_redirect(webinterface, request)
            if 'password' not in request.args:
                webinterface.add_alert('Password Missing', 'warning')
                return login_redirect(webinterface, request)
            submitted_g_recaptcha_response = request.args.get('g-recaptcha-response')[0]
            submitted_email = request.args.get('email')[0]
            submitted_password = request.args.get('password')[0]
            # print("submitted_email: %s" % submitted_email)
            # if submitted_pin.isalnum() is False:
            #     alerts = { '1234': webinterface.make_alert('Invalid authentication.', 'warning')}
            #     return webinterface.require_auth(request, alerts)

            # print("webinterface.operating_mode: %s" % webinterface.operating_mode)
            if webinterface.operating_mode == 'run':
                results = yield webinterface._LocalDB.get_gateway_user_by_email(webinterface.gateway_id(), submitted_email)
                if len(results) != 1:
                    webinterface.add_alert('Email address not allowed to access gateway.', 'warning')
                    #            webinterface.sessions.load(request)
                    page = webinterface.get_template(request, webinterface._dir + 'pages/login_user.html')
                    return page.render(alerts=webinterface.get_alerts())

            results = yield webinterface._YomboAPI.user_login_with_credentials(submitted_email, submitted_password, submitted_g_recaptcha_response)
            if (results['code'] == 200):
                login = results['content']['response']['login']
                # print("login was good...")

                if session is False:
                    session = webinterface.sessions.create(request)

                session['auth'] = True
                session['auth_pin'] = True
                session['auth_id'] = submitted_email
                session['auth_at'] = time()
                session['yomboapi_session'] = login['session']
                session['yomboapi_login_key'] = login['login_key']
                request.received_cookies[webinterface.sessions.config.cookie_session_name] = session.session_id
                # print("session saved...")
                if webinterface.operating_mode == 'first_run':
                    webinterface._YomboAPI.save_system_login_key(login['login_key'])
                    webinterface._YomboAPI.save_system_session(login['session'])
                return login_redirect(webinterface, request, session)
            else:
                webinterface.add_alert(results['content']['message'], 'warning')
                page = webinterface.get_template(request, webinterface._dir + 'pages/login_user.html')
                return page.render(alerts=webinterface.get_alerts())

        def login_redirect(webinterface, request, session=None, location=None):
            if session is not None and 'login_redirect' in session:
                location = session['login_redirect']
                session.delete('login_redirect')
            if location is None:
                location = "/?"
            # print("login_redirect: %s" % location)
            return webinterface.redirect(request, location)

        @webapp.route('/login/pin', methods=['GET'])
        @run_first()
        def page_login_pin_get(webinterface, request, session):
            return webinterface.redirect(request, '/?')

        @webapp.route('/login/pin', methods=['POST'])
        @run_first()
        def page_login_pin_post(webinterface, request, session):
            submitted_pin = request.args.get('authpin')[0]

            if submitted_pin.isalnum() is False:
                webinterface.add_alert('Invalid authentication.', 'warning')
                return webinterface.redirect(request, '/login/pin')

            def create_pin_session(webinterface, request, session):
                if session is False:
                    session = webinterface.sessions.create(request)
                session['auth_pin'] = True
                session['auth'] = False
                session['auth_id'] = ''
                session['auth_at'] = 0
                session['yomboapi_session'] = ''
                session['yomboapi_login_key'] = ''
                request.received_cookies[webinterface.sessions.config.cookie_session_name] = session.session_id

            if webinterface.auth_pin_type() == 'pin':
                # print("pins: %s == %s" % (submitted_pin, webinterface.auth_pin()))
                if submitted_pin == webinterface.auth_pin():
                    create_pin_session(webinterface, request, session)
                else:
                    return webinterface.redirect(request, '/login/pin')
            elif webinterface.auth_pin_type() == 'totp':
                if yombo.ext.totp.valid_totp(submitted_pin, webinterface.secret_pin_totp(), window=10):
                    create_pin_session(webinterface, request, session)
                else:
                    return webinterface.redirect(request, '/login/pin')
            elif webinterface.auth_pin_type() == 'none':
                create_pin_session(webinterface, request, session)

            return webinterface.redirect(request, '/?')

        @webapp.route('/static/', branch=True)
        @run_first()
        def static(webinterface, request, session):
            request.responseHeaders.removeHeader('Expires')
            request.setHeader('Cache-Control', 'max-age=%s' % randint(3600, 7200))
            return File(webinterface._current_dir + "/lib/webinterface/static/dist")

