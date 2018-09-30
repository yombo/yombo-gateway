# Import python libraries
from time import time
from random import randint

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.web.static import File

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth_pin, require_auth, run_first
from yombo.core.exceptions import YomboWarning, YomboRestart
import yombo.ext.totp
import yombo.utils

def route_home(webapp):
    with webapp.subroute("") as webapp:

        @webapp.route('/robots.txt')
        def robots_txt(webinterface, request):
            return "User-agent: *\nDisallow: /\n"

        @webapp.route('/')
        def home(webinterface, request):
            if webinterface.operating_mode == 'config':
                return config_home(webinterface, request)
            elif webinterface.operating_mode == 'first_run':
                return first_run_home(webinterface, request)
            return run_home(webinterface, request)

        @require_auth()
        def run_home(webinterface, request, session):
            page = webinterface.webapp.templates.get_template(webinterface.wi_dir + '/pages/index.html')
            delayed_device_commands = webinterface._Devices.delayed_commands()
            return page.render(alerts=webinterface.get_alerts(),
                               device_commands_delayed=delayed_device_commands,
                               )

        @require_auth()
        def config_home(webinterface, request, session):
            page = webinterface.get_template(request, webinterface.wi_dir + '/config_pages/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )
        @run_first()
        def first_run_home(webinterface, request, session):
            return webinterface.redirect(request, '/setup_wizard/1')

        @webapp.route('/logout')
        @run_first()
        # @inlineCallbacks
        def page_logout_get(webinterface, request, session):
            # print("page logout get 1: %s" % session)
            # if session is False:
            #     print("page logout no session.. redirecting to home...")
            #     # return request.redirect("/")
            #     return webinterface.redirect(request, "/?")
            try:
                webinterface._WebSessions.close_session(request)
            except Exception as e:
                pass
            return request.redirect("/?")

        @webapp.route('/login/user', methods=['GET'])
        @require_auth_pin()
        def page_login_user_get(webinterface, request, session):
            return webinterface.redirect(request, '/?')

        @webapp.route('/login/user', methods=['POST'])
        @require_auth_pin(create_session=True)
        @inlineCallbacks
        def page_login_user_post(webinterface, request, session):
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
            user = None
            if webinterface.operating_mode == 'run':
                try:
                    user = webinterface._Users.get(submitted_email)
                except KeyError:
                    webinterface.add_alert('Email address not allowed to access gateway.', 'warning')
                    page = webinterface.get_template(request, webinterface.wi_dir + '/pages/misc/login_user.html')
                    return page.render(alerts=webinterface.get_alerts())

            try:
                results = yield webinterface._YomboAPI.user_login_with_credentials(
                    submitted_email, submitted_password, submitted_g_recaptcha_response)
            except YomboWarning as e:
                webinterface.add_alert("%s: %s" % (e.errorno, e.message), 'warning')
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/misc/login_user.html')
                return page.render(alerts=webinterface.get_alerts())
            if results['code'] == 200:
                login = results['response']['login']
                session._user = user
                session.auth_pin = True
                session['yomboapi_session'] = login['session']
                session['yomboapi_login_key'] = login['login_key']

                request.received_cookies[webinterface._WebSessions.config.cookie_session_name] = session.auth_id
                try:
                    webinterface._YomboAPI.check_if_new_gateway_credentials_needed(login['session'])
                except YomboRestart:
                    page = webinterface.get_template(request, webinterface.wi_dir + '/pages/restart.html')
                    return page.render(alerts=webinterface.get_alerts())
                except YomboWarning:
                    print("Got an error, will handle it later....")
                return login_redirect(webinterface, request, session)
            else:
                webinterface.add_alert(results['msg'], 'warning')
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/misc/login_user.html')
                return page.render(alerts=webinterface.get_alerts())

        def login_redirect(webinterface, request, session=None, location=None):
            if session is not None and 'login_redirect' in session:
                location = session['login_redirect']
                session.delete('login_redirect')
            if location is None:
                location = "/?"
            return webinterface.redirect(request, location)

        @webapp.route('/login/pin', methods=['GET'])
        @run_first()
        def page_login_pin_get(webinterface, request, session):
            return webinterface.redirect(request, '/?')

        @webapp.route('/login/pin', methods=['POST'])
        @run_first(create_session=True)
        def page_login_pin_post(webinterface, request, session):
            submitted_pin = request.args.get('authpin')[0]
            if submitted_pin.isalnum() is False:
                webinterface.add_alert('Invalid authentication.', 'warning')
                return webinterface.redirect(request, '/login/pin')

            def create_pin_session(l_webinterface, l_request, l_session):
                if l_session is None:
                    l_session = webinterface._WebSessions.create(request)
                l_session.auth_pin = True
                l_session.auth_id = None
                l_session['yomboapi_session'] = ''
                l_session['yomboapi_login_key'] = ''
                request.received_cookies[l_webinterface._WebSessions.config.cookie_session_name] = l_session.auth_id

            if webinterface.auth_pin_type() == 'pin':
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
            return File(webinterface.app_dir + "/yombo/lib/webinterface/static/dist")

