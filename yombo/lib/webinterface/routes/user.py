"""
Handles user login/logout, which includes SSO from my.yombo.net.
"""

# Import python libraries
from hashlib import sha256
import jwt

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.classes.dictobject import DictObject
from yombo.core.log import get_logger
from yombo.lib.webinterface.auth import get_session
import yombo.utils
from yombo.utils.datatypes import coerce_value

logger = get_logger("library.webinterface.routes.user")


def route_user(webapp):
    with webapp.subroute("/user") as webapp:

        @webapp.route("/logout2")
        @get_session()
        def page_user_logout2_get(*args, **kwargs):
            print(f"page_user_logout2_get 1: {args} - {kwargs}")
            print(f"page_user_logout2_get 2: {webapp}")
            return "asdfa"

        @webapp.route("/logout")
        @get_session()
        # @inlineCallbacks
        def page_user_logout_get(webinterface, request, session):
            # print("page logout get 1: %s" % session)
            # if session is False:
            #     print("page logout no session.. redirecting to home...")
            #     # return request.redirect("/")
            #     return webinterface.redirect(request, "/")
            try:
                webinterface._WebSessions.close_session(request)
            except Exception as e:
                pass
            return request.redirect("/")

        @webapp.route("/login", methods=["GET"])
        @get_session(create_session=True)
        def page_user_login_user_get(webinterface, request, session):
            if session.is_valid() is True and session.has_user is True:
                print("login, but already have a valid user user....")
                return request.redirect("/")
            host = request.getHost()
            hostname = request.getRequestHostname().decode('utf-8')
            session["login_request_id"] = yombo.utils.random_string(length=30)

            auto_login_redirect_input = coerce_value(request.args.get('autoredirect', 0), 'int')
            auto_login_redirect = 0
            if isinstance(auto_login_redirect_input, int):
                if auto_login_redirect == 1:
                    auto_login_redirect = 1
            if auto_login_redirect == 0 and "auto_login_redirect" in session:
                auto_login_redirect = session["auto_login_redirect"]

            return webinterface.render_template(request,
                                                webinterface.wi_dir + "/pages/user/login.html",
                                                login_request_id=session["login_request_id"],
                                                secure=1 if request.isSecure() else 0,
                                                hostname=hostname,
                                                port=host.port,
                                                gateway_id=webinterface._gateway_id,
                                                autoredirect=auto_login_redirect,
                                                )

        # @webapp.route("/auth_sso", methods=["GET"])
        # @get_session()
        # def page_user_auth_sso_get(webinterface, request, session):
        #     return webinterface.redirect(request, "/user/login")
        #
        # @webapp.route("/auth_sso", methods=["POST"])
        # @get_session(create_session=True)
        # @inlineCallbacks
        # def page_user_auth_sso_post(webinterface, request, session):
        #     gateway_id = webinterface._gateway_id
        #     if "token" not in request.args:
        #         session.add_alert("Error with incoming SSO request: token is missing")
        #         return webinterface.redirect(request, "/user/auth_sso")
        #     if "request_id" not in request.args:
        #         session.add_alert("Error with incoming SSO request: request_id is missing")
        #         return webinterface.redirect(request, "/user/auth_sso")
        #
        #     token = request.args.get("token", [{}])[0]
        #     token_hash = sha256(yombo.utils.unicode_to_bytes(token)).hexdigest()
        #     # print(f"Tokens in cache: {webinterface.user_login_tokens}")
        #     if token_hash in webinterface.user_login_tokens:
        #         session.add_alert("The authentication token has already been claimed and cannot be used again.",
        #                           level="danger")
        #         return webinterface.redirect(request, "/user/login")
        #
        #     token_data = jwt.decode(token, verify=False)
        #     try:
        #         user = webinterface._Users.get(token_data["user_id"])
        #     except KeyError:
        #         logger.warn("Unable to find user during login.")
        #         if webinterface._Loader.operating_mode == 'run':
        #             session.add_alert("It appears this user is not allowed to login here.",
        #                               level="danger")
        #             return webinterface.redirect(request, "/")
        #
        #         user = DictObject({
        #             "id": token_data['user_id'],
        #             "user_id": token_data['user_id'],
        #             "email": token_data['email'],
        #             "name": token_data['name'],
        #             "access_code_string": "",
        #         })
        #
        #     response = yield webinterface._YomboAPI.request(
        #         "POST",
        #         f"/v1/gateways/{gateway_id}/check_user_token",
        #         body={
        #             "token": token,
        #         }
        #     )
        #     data = response.content["data"]["attributes"]
        #
        #     if data["is_valid"] is True:
        #         session.set_refresh_token(request, data["refresh_token"], data["refresh_token_expires_at"])
        #         session.set_access_token(request, data["access_token"], data["access_token_expires_at"])
        #         session.user = user
        #         return login_redirect(webinterface, request, session)
        #     else:
        #         session.add_alert("Token was invalid.", "warning")
        #         return webinterface.redirect(request, "/user/login")

        def login_redirect(webinterface, request, session=None, location=None):
            if session is not None and "login_redirect" in session:
                location = session["login_redirect"]
                session.delete("login_redirect")
            if location is None:
                location = "/"
            return webinterface.redirect(request, location)
