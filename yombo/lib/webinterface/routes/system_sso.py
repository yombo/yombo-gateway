"""
Handles user login/logout, which includes SSO from my.yombo.net.
"""

# Import python libraries
from hashlib import sha256
import jwt
from jwt.exceptions import PyJWTError, DecodeError, InvalidSignatureError, ExpiredSignatureError
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.classes.dictobject import DictObject
from yombo.core.log import get_logger
from yombo.lib.webinterface.auth import get_session
import yombo.utils
from yombo.utils.datatypes import coerce_value

logger = get_logger("library.webinterface.routes.system_sso")


def route_system_sso(webapp):
    with webapp.subroute("/system/sso") as webapp:

        @webapp.route("/user_auth", methods=["GET"])
        @get_session()
        def page_system_sso_auth_get(webinterface, request, session):
            """ """
            return webinterface.redirect(request, "/user/login")

        @webapp.route("/user_auth", methods=["POST"])
        @get_session(create_session=True)
        @inlineCallbacks
        def page_system_sso_auth_post(webinterface, request, session):
            gateway_id = webinterface._gateway_id
            if "token" not in request.args:
                session.add_alert("Error with incoming SSO request: token is missing")
                return webinterface.redirect(request, "/")
            if "login_request_id" not in request.args:
                session.add_alert("Error with incoming SSO request: login_request_id is missing")
                return webinterface.redirect(request, "/")

            token = request.args.get("token", [{}])[0]
            token_hash = sha256(yombo.utils.unicode_to_bytes(token)).hexdigest()
            if token_hash in webinterface.user_login_tokens:
                session.add_alert("The authentication token has already been claimed and cannot be used again.",
                                  level="danger")
                return webinterface.redirect(request, "/user/login")

            jwt_hash = request.args.get("jwt_hash", [{}])[0]
            jwt_public = webinterface._Configs.get(f"jwt.{jwt_hash}.key", None)
            if jwt_public is None:
                response = yield webinterface._Requests.request("get", f"https://yombo.net/jwt/{jwt_hash}")
                jwt_public = response.content_raw
                webinterface._Configs.set(f"jwt.{jwt_hash}.key", jwt_public)
                webinterface._Configs.set(f"jwt.{jwt_hash}.time", int(time()))

            try:
                token_data = jwt.decode(token, jwt_public, verify=True, issuer="https://api.yombo.net",
                                        audience=[f"gw {gateway_id}"], leeway=60)
            except DecodeError as e:
                session.add_alert("Error decoding SSO token from yombo.net: SSO Token (JWT) appears to be malformed, try again.")
                return webinterface.redirect(request, "/")
            except InvalidSignatureError as e:
                session.add_alert("Error decoding SSO token from yombo.net: Appears to have been tampered with, try again.")
                return webinterface.redirect(request, "/")
            except ExpiredSignatureError as e:
                session.add_alert("Error decoding SSO token from yombo.net: Token has expired, check the clock running Yombo Gateawy and try again.")
                return webinterface.redirect(request, "/")
            except PyJWTError as e:
                session.add_alert(f"Error decoding SSO token from yombo.net: {type(e).__name__}")
                return webinterface.redirect(request, "/")

            try:
                user = webinterface._Users.get(token_data["user_id"])
            except KeyError:
                logger.warn("Unable to find user during login.")
                if webinterface._Loader.operating_mode == 'run':
                    session.add_alert("It appears this user is not allowed to login here.",
                                      level="danger")
                    return webinterface.redirect(request, "/")

                user = DictObject({
                    "id": token_data['user_id'],
                    "user_id": token_data['user_id'],
                    "email": token_data['email'],
                    "name": token_data['name'],
                    "access_code_string": "",
                })

            session.set_refresh_token(request, token_data["refresh_token"], token_data["refresh_token_expires_at"])
            session.set_access_token(request, token_data["access_token"], token_data["access_token_expires_at"])
            session.user = user
            return login_redirect(webinterface, request, session)

        def login_redirect(webinterface, request, session=None, location=None):
            if session is not None and "login_redirect" in session:
                location = session["login_redirect"]
                session.delete("login_redirect")
            if location is None:
                location = "/"
            return webinterface.redirect(request, location)
