"""

"""
# Import python libraries
import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import AUTH_TYPE_AUTHKEY, AUTH_TYPE_WEBSESSION, CONTENT_TYPE_TEXT_PLAIN
from yombo.constants.permissions import AUTH_PLATFORM_MQTT
from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import get_session
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.apiv1.mosquitto_auth")

ACCESS_MAP = {
    1: "read",
    2: "write",
    4: "read",  # This is really subscribe - but to read, you must subscribe.
}


def route_api_v1_mosquitto_auth(webapp):
    with webapp.subroute("/api/v1/mosquitto_auth") as webapp:

        @webapp.route("/log_incoming")
        @get_session(auth_required=True)
        def page_system_mqtt_log(webinterface, request, session):
            """
            Get the incoming log.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            session.is_allowed(AUTH_PLATFORM_MQTT, "view")
            page = webinterface.webapp.templates.get_template(webinterface.wi_dir + "/pages/mqtt/log.html")
            return webinterface.render_api(request,
                                           data_type="backup_info",
                                           attributes={"log": webinterface._MQTTYombo.log_incoming},
                                           )

        @webapp.route("/log_outgoing")
        @get_session(auth_required=True)
        def page_system_mqtt_log(webinterface, request, session):
            """
            Get the incoming log.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            session.is_allowed(AUTH_PLATFORM_MQTT, "view")
            # page = webinterface.webapp.templates.get_template(webinterface.wi_dir + "/pages/mqtt/log.html")
            return webinterface.render_api(request,
                                           data_type="backup_info",
                                           attributes={"log": webinterface._MQTTYombo.log_outgoing},
                                           )

        @webapp.route("/publish")
        @get_session(auth_required=True)
        @inlineCallbacks
        def api_v1_mqtt(webinterface, request, session):
            session.is_allowed(AUTH_PLATFORM_MQTT, "publish")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!   /api/v1/mqtt: %s" % request)
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

        @inlineCallbacks
        def get_user(webinterface, username, password=None):
            """ Fetch the user item. Based on the username, it tries different types."""
            username_parts = username.split("-", 2)
            if len(username_parts) != 2:
                raise YomboWarning(f"mqtt auth should have 2 parts: {username_parts}")

            if username_parts[0] == "yombogw":
                if username_parts[0].isalnum() and username_parts[1].isalnum():
                    gwid = username_parts[1]
                    gateway = webinterface._Gateways.gateways[gwid]
                    user_data = {
                        "type": "gateway",
                        "username": gwid,
                        "auth": None,
                        "topics": {
                            "yombo_presence/gw/#": ['read'],
                            "yombo_presence/gw/{gwid}": ['write'],
                            f"yombo_gw/+/{gwid}/#": ['read'],
                            "yombo_gw/+/global/#": ['read', 'write'],
                            "yombo_gw/+/cluster/#": ['write'],
                        },
                        "password_validated": False
                    }
                    if password is not None and password in (gateway.mqtt_auth, gateway.mqtt_auth_next):
                        user_data["password_validated"] = True
                    return user_data
                else:
                    logger.warn("MQTT username has invalid characters: {user}", user=username)
                    raise YomboWarning("MQTT username has invalid characters")

            elif username_parts[0] == "authkey":
                print(f"mqttauth got userparts: {username_parts}")
                try:
                    auth_key = webinterface._AuthKeys.get_session_by_id(username_parts[1])
                    if auth_key.is_valid is False:
                        return None
                    print(f"authkey found: {auth_key}")
                    print(f"authkey found dict: {auth_key.__dict__}")
                    return {
                        "type": "authkey",
                        "username": auth_key.machine_label,
                        "auth": auth_key,
                        "topics": None,
                        "password_validated": True
                    }
                    print(f"authkey found, results: {results}")
                    return results

                except Exception as e:
                    print(f"Error looking for auth key: {e}")
                    YomboWarning("Authkey not found.")

            elif username_parts[0] == "web":
                print(f"web session userparts: {username_parts}")
                try:
                    session = yield webinterface._WebSessions.get_session_by_id(username_parts[1])
                    if session.is_valid is False:
                        return None
                    print(f"websession found: {session}")
                    return {
                        "type": "websession",
                        "username": username_parts[1],
                        "auth": session,
                        "topics": None,
                        "password_validated": True
                    }
                    # return user_data
                except Exception as e:
                    print(f"Error looking for auth key: {e}")
                    YomboWarning("Authkey not found.")

            elif username_parts[0] == "mqtt":
                try:
                    auth = webinterface._MQTTUsers.get(username, password)
                    if auth.is_valid is False:
                        return None
                except:
                    return None
                return {
                    "type": "mqttuser",
                    "username": username,
                    "auth": auth,
                    "topics": None,
                    "password_validated": True
                }
            return None

        @webapp.route("/auth/user", methods=["POST", "GET"])
        @inlineCallbacks
        def api_v1_mosquitto_auth_user(request):
            """
            Used by the mosquitto broker to validate a user. Doesn't do any ACL checking.

            :param webinterface:
            :param request:
            :return:
            """
            logger.debug("api_v1_mosquitto_auth_user: {args}", args=request.args)
            logger.debug("api_v1_mosquitto_auth_user: data {data}", data=request.content.read())
            #args: {b'username': [b'yombogw-GWID'], b'password': [b'passwd'], b'topic': [b''], b'acc': [b'-1'], b'clientid': [b'']}
            webinterface = webapp.webinterface
            request.setHeader("Content-Type", CONTENT_TYPE_TEXT_PLAIN)
            request.setResponseCode(403)
            try:
                user_data = yield get_user(webinterface, request.args[b"username"][0].decode(), request.args[b"password"][0].decode())
            except Exception as e:
                logger.warn("MQTT user not found: {e}", e=e)
                user_data = None

            logger.debug("mqtt: auth, user_data: {user_data}", user_data=user_data)
            if user_data is None:
                return " "

            if user_data["type"] == "gateway":
                if user_data["password_validated"] is False:
                    return " "
                request.setResponseCode(200)
                return " "

            if user_data["type"] == "mqttuser":
                if user_data["password_validated"] is False:
                    return " "
                request.setResponseCode(200)
                return " "

            if user_data["type"] == "authkey":
                request.setResponseCode(200)
                return " "

            if user_data["type"] == "websession":
                request.setResponseCode(200)
                return " "

            # elif user_data["type"] == AUTH_TYPE_WEBSESSION:
            #     try:
            #         session = yield webinterface._WebSessions.get_session_by_id(user_data["username"])
            #         if session.is_valid():
            #             response_code = 200
            #     except YomboWarning as e:
            #         pass
            #
            # elif user_data["type"] == AUTH_TYPE_AUTHKEY:
            #     logger.info("mqtt: is authkey type")
            #     try:
            #         session = webinterface._AuthKeys.get_session_by_id(user_data["username"])
            #         logger.info("mqtt: auth/user, authkey session: {session}", session=session)
            #         if session.is_valid():
            #             logger.info("mqtt: auth/user, authkey session is good, 200.")
            #             response_code = 200
            #     except YomboWarning as e:
            #         logger.info("mqtt: auth/user, authkey session error: {e}", e=e)
            #         pass

            return " "

        @webapp.route("/auth/superuser", methods=["POST"])
        def api_v1_mosquitto_auth_superuser(request):
            """
            Used by the mosquitto broker to validate a super user. Hint: There are no super users.

            :param webinterface:
            :param request:
            :return:
            """
            response_code = 403
            request.setHeader("Content-Type", CONTENT_TYPE_TEXT_PLAIN)
            request.setResponseCode(response_code)
            return

        @webapp.route("/auth/acl", methods=["POST"])
        @inlineCallbacks
        def api_v1_mosquitto_auth_acl(request):
            """
            Used by the mosquitto broker to validate a if clients can access, read, or write to various topics.

            ACC values:
                0: no access
                1: read
                2: write
                4: subscribe

            See test/misc/test_mqtt_topic_matching.py for tinkering.

            :param request:
            :return:
            """
            # print("MQTT ACL ####################################")
            # print("MQTT ACL ####################################")
            # print("MQTT ACL ####################################")
            # print(f"api_v1_mosquitto_auth_acl: args {request.args}")

            request.setResponseCode(200)
            # print("ACL, valid - gateway with yombo_gw")
            return  # No one other than gateways can access this.

            webinterface = webapp.webinterface
            #
            # def _topic_search(topic_requested: str, topic_allowed: list) -> bool:
            #     """
            #     Attempts to match a requested topic with a list of topics allowed.
            #
            #     Insipired by: https://github.com/beerfactory/hbmqtt/blob/master/hbmqtt/plugins/topic_checking.py
            #     """
            #     req_split = topic_requested.split('/')
            #     allowed_split = topic_allowed.split('/')
            #     ret = True
            #     for i in range(max(len(req_split), len(allowed_split))):
            #         try:
            #             req_aux = req_split[i]
            #             allowed_aux = allowed_split[i]
            #         except IndexError:
            #             ret = False
            #             break
            #         if allowed_aux == '#':
            #             break
            #         elif (allowed_aux == '+') or (allowed_aux == req_aux):
            #             continue
            #         else:
            #             ret = False
            #             break
            #     return ret
            #
            # def topic_match(user: dict, req_topic: str, req_access: list) -> bool:
            #     """
            #     Match requested topic with user allowed topics. If user has a matching topic, it's access
            #     it validated.
            #     """
            #     access_req = ACCESS_MAP[req_access]
            #     allowed_topics = user["topics"]
            #
            #     if len(req_topic) < 0:
            #         return False
            #
            #     if req_topic:
            #         if len(allowed_topics):
            #             for allowed_topic, allowed_permissions in allowed_topics.items():
            #                 if _topic_search(req_topic, allowed_topic):
            #                     print(
            #                         f"--> topic_matched {req_topic}- requested perm: {access_req} - allowed: {allowed_permissions}")
            #                     if access_req in allowed_permissions:
            #                         return True
            #             return False
            #         else:
            #             return False
            #     else:
            #         return False

            response_code = 403
            request.setHeader("Content-Type", CONTENT_TYPE_TEXT_PLAIN)
            request.setResponseCode(403)

            # print("/api/v1/mosquitto_auth/auth/acl: %s" % request.args)
            # logger.debug("mqtt acl: {args}", args=request.args)

            try:
                user_data = yield get_user(webinterface, request.args[b"username"][0].decode())
            except KeyError as e:
                print(f"user data go an error: {e}")
                return

            print(f"user_data: {user_data}")

            access = {
                0: "noaccess",
                1: "read",
                2: "write",
                4: "subscribe",
            }

            requested_topic = request.args[b"topic"][0].decode()
            requested_access = access[int(request.args[b"acc"][0].decode())]

            topic_parts = requested_topic.split("/")
            # TODO: Fine grain
            requested_access = request.args[b"acc"][0].decode()  # acc: 1 = read only, 2 is write, 4 is subscribe.

            if requested_topic.startswith("/"):
                return

            if user_data is None:
                return

            print(f"requested_topic: {requested_topic}")

            if user_data["type"] == "gateway":
                if requested_topic.startswith("yombo_gw"):

                    if len(topic_parts) < 4 and requested_topic.endswith('#') is False:
                        print("ACL, invalid, must be at least 4 parts for topic.")
                        return  # Must have at least 4 parts

                    request.setResponseCode(200)
                    print("ACL, valid - gateway with yombo_gw")
                    return  # No one other than gateways can access this.

                request.setResponseCode(200)
                print("ACL, valid - gateway can temp do whatever")
                return  # GW's can read/write/subscribe.

            if requested_topic.startswith("yombo_gw"):
                if user_data["type"] != "gateway":
                    print("ACL, invalid, access to yombo_gw is for gateways only.")
                    return  # No one other than gateways can access this.

            if user_data["auth"] is not None:
                print("ACL, auth start.")
                request.setResponseCode(200)
                print("ACL, valid - has auth, and has permission.")
                return

                if topic_parts[0] in ("yombo", "yombo_set"):
                    if len(topic_parts) == 1:
                        return  # Not enough parts.
                    platform = topic_parts[1]

                    action = "*"
                    if len(topic_parts) >= 3:
                        action = topic_parts[2]

                    item_id = "*"
                    if len(topic_parts) >= 4:
                        item_id = topic_parts[2]

                    if webinterface._Permissions.is_allowed(platform, action, item_id):
                        request.setResponseCode(200)
                        print("ACL, valid - has auth, and has permission.")
                        return
                    return
                # Else, the authkey can do anything on the MQTT
                # TODO: add some permissions?
                request.setResponseCode(200)
                print("ACL, valid - has auth, and has permission.")
                return
            elif user_data["type"] == "mqttuser":
                if topic_parts[0] in ("yombo", "yombo_set"):
                    print("ACL, INVALID - yombo or yombo_set.")
                    return  # Don't try to sneak past
                # TODO: will finish once mqttuser library is feature complete.
                request.setResponseCode(200)
                print("ACL, valid - mqttuser.")
                return

            print("ACL, INVALID - default catch")
            return  # If not found, just reject it.