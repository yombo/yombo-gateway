# Import python libraries
from hashlib import sha256
from time import time
import jwt
from random import randint

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.names import client
from twisted.web.static import File

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth, run_first
from yombo.core.exceptions import YomboWarning, YomboRestart
import yombo.ext.totp
import yombo.utils

def route_home(webapp):
    with webapp.subroute("") as webapp:

        @webapp.route("/robots.txt")
        def robots_txt(webinterface, request):
            return "User-agent: *\nDisallow: /\n"

        @webapp.route("/")
        @run_first()
        def home(webinterface, request, session):
            # print(f"webinterface.operating_mode: {webinterface.operating_mode}")
            if webinterface.operating_mode == "config":
                return config_home(webinterface, request)
            elif webinterface.operating_mode == "first_run":
                return first_run_home(webinterface, request)
            if session is None or session.enabled is False or session.is_valid() is False or session.has_user is False:
                return webinterface.redirect(request, "/user/login")
            return File(webinterface.working_dir + "/frontend/")

        @require_auth()
        def config_home(webinterface, request, session):
            page = webinterface.get_template(request, webinterface.wi_dir + "/config_pages/index.html")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @run_first()
        def first_run_home(webinterface, request, session):
            return webinterface.redirect(request, "/setup_wizard/1")

        @webapp.route("/user/logout")
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

        @webapp.route("/user/login", methods=["GET"])
        @run_first(create_session=True)
        def page_login_user_get(webinterface, request, session):
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/misc/login_user.html")

            host = request.getHost()
            session["login_request_id"] = yombo.utils.random_string(length=50)
            background_image_ids = [456, 477, 478, 480, 503, 520, 640]  # https://picsum.photos/images
            image_id = background_image_ids[int(time()/10)%len(background_image_ids)]
            return page.render(
                alerts=session.get_alerts(),
                request_id=session["login_request_id"],
                secure=1 if request.isSecure() else 0,
                hostname=host.host,
                port=host.port,
                gateway_id=webinterface.gateway_id(),
                image_id=image_id
            )

        @webapp.route("/user/auth_sso", methods=["POST"])
        @run_first(create_session=True)
        @inlineCallbacks
        def page_login_user_post(webinterface, request, session):
            gateway_id = webinterface.gateway_id()
            if "token" not in request.args:
                session.add_alert("Error with incoming SSO request: token is missing")
                return webinterface.redirect(request, "/user/auth_sso")
            if "request_id" not in request.args:
                session.add_alert("Error with incoming SSO request: request_id is missing")
                return webinterface.redirect(request, "/user/auth_sso")

            token = request.args.get("token", [{}])[0]
            token_hash = sha256(yombo.utils.unicode_to_bytes(token)).hexdigest()
            print(f"Tokens in cache: {webinterface.user_login_tokens}")
            if token_hash in webinterface.user_login_tokens:
                session.add_alert("The authentication token has already been claimed and cannot be used again.",
                                  level="danger",
                                  dismissible=False)
                return webinterface.redirect(request, "/user/login")
            # webinterface.user_login_tokens[token_hash] = True

            token_data = jwt.decode(token, verify=False)
            print(f"TOekn user_id: {token_data['user_id']}")
            print(f"Users: {webinterface._Users.users}")
            user = webinterface._Users.get(token_data["user_id"])
            print(f"User: {user}")
            print(f"User access_token: {user.access_token}")
            print(f"User refresh_token: {user.refresh_token}")

            request_id = request.args.get("request_id", [{}])[0]
            response = yield webinterface._YomboAPI.request(
                "POST", f"/v1/gateways/{gateway_id}/check_user_token",
                {
                    "token": token,
                }
            )
            data = response.content["data"]["attributes"]
            print(f"resonse: {data}")

            if data["is_valid"] is True:
                session.user = webinterface._Users.get(data["user_id"])
                request.received_cookies[webinterface._WebSessions.config.cookie_session_name] = session.auth_id
                return login_redirect(webinterface, request, session)
            else:
                session.add_alert("Token was invalid.", "warning")
                return webinterface.redirect(request, "/user/login")

        def login_redirect(webinterface, request, session=None, location=None):
            if session is not None and "login_redirect" in session:
                location = session["login_redirect"]
                session.delete("login_redirect")
            if location is None:
                location = "/?"
            return webinterface.redirect(request, location)

        @webapp.route("/css/", branch=True)
        def static_frontend_css(webinterface, request):
            """ For frontend css stylesheets. """
            request.responseHeaders.removeHeader("Expires")
            request.setHeader("Cache-Control", f"max-age={randint(3600, 7200)}")
            return File(webinterface.working_dir + "/frontend/css")

        @webapp.route("/img/", branch=True)
        def static_frontend_img(webinterface, request):
            """ For frontend images. """
            request.responseHeaders.removeHeader("Expires")
            request.setHeader("Cache-Control", f"max-age={randint(3600, 7200)}")
            return File(webinterface.working_dir + "/frontend/img")

        @webapp.route("/js/", branch=True)
        def static_frontend_js(webinterface, request):
            """ For frontend javascript files. """
            request.responseHeaders.removeHeader("Expires")
            request.setHeader("Cache-Control", f"max-age={randint(3600, 7200)}")
            return File(webinterface.working_dir + "/frontend/js")

        @webapp.route("/favicon.ico")
        def static(webinterface, request):
            request.responseHeaders.removeHeader("Expires")
            request.setHeader("Cache-Control", f"max-age={randint(3600, 7200)}")
            return File(webinterface.working_dir + "/frontend/img/icons/favicon.ico")


