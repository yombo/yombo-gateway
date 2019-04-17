# Import python libraries
import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet.defer import maybeDeferred

# Import Yombo libraries
from yombo.constants import AUTH_TYPE_AUTHKEY, AUTH_TYPE_WEBSESSION
from yombo.constants import CONTENT_TYPE_TEXT_PLAIN
from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth, run_first
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.apiv1.mqtt")


def route_api_v1_mqtt(webapp):
    with webapp.subroute("/api/v1/mqtt") as webapp:

        @webapp.route("/log_incoming")
        @require_auth()
        def page_system_mqtt_log(webinterface, request, session):
            """
            Get the incoming log.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            if session.has_access("system_options", "*", "mqtt") is False:
                return webinterface.render_api_error(request, session, response_code=403)
            page = webinterface.webapp.templates.get_template(webinterface.wi_dir + "/pages/mqtt/log.html")
            return webinterface.render_api(request, session,
                                           data_type="backup_info",
                                           attributes={"id": webinterface._Gateways.local_id,
                                                       "log": webinterface._GatewayComs.log_incoming},
                                           )

        @webapp.route("/log_outgoing")
        @require_auth()
        def page_system_mqtt_log(webinterface, request, session):
            """
            Get the incoming log.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            if session.has_access("system_options", "*", "mqtt") is False:
                return webinterface.render_api_error(request, session, response_code=403)
            # page = webinterface.webapp.templates.get_template(webinterface.wi_dir + "/pages/mqtt/log.html")
            return webinterface.render_api(request, session,
                                           data_type="backup_info",
                                           attributes={"id": webinterface._Gateways.local_id,
                                                       "log": webinterface._GatewayComs.log_incoming},
                                           )

        @webapp.route("/publish")
        @run_first()
        @inlineCallbacks
        def api_v1_mqtt(webinterface, request, session):
            if session.has_access("system_options", "*", "mqtt") is False:
                return webinterface.render_api_error(request, session, response_code=403)
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!   /api/v1/mqtt: %s" % request)
            session.has_access("system_options", "*", "mqtt")
            topic = request.args.get("topic")[0]  # please do some validation!!
            message = request.args.get("message")[0]  # please do some validation!!
            qos = int(request.args.get("qos")[0])  # please do some validation!!

            try:
                yield webinterface._MQTT.mqtt_local_client.publish(topic, message, qos)
                results = {"status": 200, "message": "MQTT message sent successfully."}
                return json.dumps(results)
            except Exception as e:
                results = {"status": 500, "message": "MQTT message count not be sent."}
                return json.dumps(results)

        def split_username(username):
            username_parts = username.split("_", 4)
            if len(username_parts) < 2:
                raise YomboWarning(f"MQTT username should have at least 2 parts: {username_parts}")

            if username_parts[0].isalnum() and username_parts[1].isalnum():
                user = {
                    "type": username_parts[0],
                    "username": username_parts[1],
                }
            else:
                logger.warn("MQTT username has invalid characters: {user}", user=username)
                raise YomboWarning("MQTT username has invalid characters")
            return user

        @webapp.route("/auth/user", methods=["POST", "GET"])
        @inlineCallbacks
        def api_v1_mqtt_auth_user(webinterface, request):
            """
            Used by the mosquitto broker to validate a user.

            :param webinterface:
            :param request:
            :return:
            """
            request.setHeader("Content-Type", CONTENT_TYPE_TEXT_PLAIN)
            response_code = 403
            user = split_username(request.args[b"username"][0].decode())
            password = request.args[b"password"][0].decode()
            user_id = user["username"]
            logger.info("mqtt user: {user}", user=user)
            if user["type"] == "yombogw":
                if user_id in webinterface._Gateways.gateways:
                    gateway = webinterface._Gateways.gateways[user_id]
                    if password in (gateway.mqtt_auth, gateway.mqtt_auth_prev, gateway.mqtt_auth_next):
                        response_code = 200

            elif user["type"] == AUTH_TYPE_WEBSESSION:
                try:
                    session = yield webinterface._WebSessions.get_session_by_id(user["username"])
                    if session.is_valid():
                        response_code = 200
                except YomboWarning as e:
                    pass

            elif user["type"] == AUTH_TYPE_AUTHKEY:
                try:
                    session = webinterface._AuthKeys.get_session_by_id(user["username"])
                    if session.is_valid():
                        response_code = 200
                except YomboWarning:
                    pass

            yield maybeDeferred(request.setResponseCode, response_code)
            return

        @webapp.route("/mqtt/auth/superuser", methods=["POST"])
        def api_v1_mqtt_auth_superuser(webinterface, request):
            """
            Used by the mosquitto broker to validate a super user.

            :param webinterface:
            :param request:
            :return:
            """
            # print("/api/v1/mqtt/auth/superuser: %s" % request.args)
            response_code = 403
            logger.info("mqtt superuser: {args}", args=request.args)
            user = split_username(request.args[b"username"][0].decode())
            password = request.args[b"password"][0].decode()

            if user["type"] == "yombogw":
                response_code = 200

            request.setHeader("Content-Type", CONTENT_TYPE_TEXT_PLAIN)
            request.setResponseCode(response_code)
            return

        @webapp.route("/mqtt/auth/acl", methods=["POST"])
        def api_v1_mqtt_auth_acl(webinterface, request):
            """
            Used by the mosquitto broker to validate a if clients can access, read, or write to various topics.

            :param webinterface:
            :param request:
            :return:
            """
            # print("/api/v1/mqtt/auth/acl: %s" % request)
            logger.info("mqtt acl: {args}", args=request.args)

            user = split_username(request.args[b"username"][0].decode())
            topic = request.args[b"topic"][0].decode()
            access = request.args[b"acc"][0].decode()
            # acc: 1 = read only, 2 is read-write

            response_code = 200
            request.setHeader("Content-Type", CONTENT_TYPE_TEXT_PLAIN)
            request.setResponseCode(response_code)
            return
