# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `AMQPYombo @ Library Documentation <https://yombo.net/docs/libraries/amqpyombo>`_

This library is responsible for handling configuration and control messages with the Yombo servers. It requests
configurations and directs them to the configuration handler. It also directs any control messages to the control
handler.

This library utilizes the amqp library to handle the low level handling.

This connection should be maintained 100% of the time. This allows control messages to be received by your devices
or 3rd party sources such as Amazon Alexa, Google Home, etc etc.

.. warning::

   This library is not intended to be accessed by module developers or end users. These functions, variables,
   and classes were not intended to be accessed directly by modules. These are documented here for completeness.

.. todo::

   The gateway needs to check for a non-responsive server or if it doesn't get a response in a timely manor.
   Perhaps disconnect and reconnect to another server? -Mitch

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2015-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/amqpyombo/__init__.html>`_
"""

# Import python libraries
import msgpack
from time import time
from typing import Any, Callable, ClassVar, List, Optional, Union

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred

# Import Yombo libraries
from yombo.classes.maxdict import MaxDict
from yombo.constants.amqpyombo import KEEPALIVE, PREFETCH_COUNT
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.amqp_mixin import AMQPMixin
from yombo.utils import percentage, random_string, random_int
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.amqpyombo")

PROTOCOL_VERSION = 7  # Which version of the yombo protocol we have implemented.


class AMQPYombo(YomboLibrary, AMQPMixin):
    """
    Handles interactions with Yombo servers through the AMQP library.
    """
    request_configs: ClassVar[bool] = False
    amqp: ClassVar = None  # holds our pointer for out amqp connection.
    amqp_control_handler: ClassVar = None
    amqp_system_handler: ClassVar = None
    message_log = MaxDict(400)  # Track incoming and outgoing messages. Meta data only, include correlation info.
    # message_correlations = MaxDict(400)  # Track various bits of information for sent correlation_ids.
    send_local_information_loop: ClassVar = None  # used to periodically send yombo servers updated information

    @property
    def connected(self):
        return self._States.get("amqp.amqpyombo.state")

    @connected.setter
    def connected(self, val):
        return self._States.set("amqp.amqpyombo.state", val, value_type="bool", request_context=self._FullName)

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Loads various variables and calls :py:meth:connect() when it's ready.

        :return:
        """
        self.connected = False

        self.user_id = f"{self._Configs.get('core.system_user_prefix')}_" \
                       f"{self._Configs.get('core.gwid', 'local', False)}"
        self.add_default_routes = self._Configs.get("amqpyombo.add_default_routes", True)

        self.amqpyombo_options = {   # Stores callbacks and routing information.
            "connected": [],
            "disconnected": [],
            "routing": {},
        }
        self.amqpyombo_options_called = False
        if self.add_default_routes:
            # Handlers for processing various messages.
            from yombo.lib.amqpyombo.amqpcontrol import AmqpControl
            from yombo.lib.amqpyombo.amqpsystem import AmqpSystem
            self.amqp_control_handler = AmqpControl(self)
            self.amqp_system_handler = AmqpSystem(self)
            self.amqpyombo_options["routing"] = {
                "control": [self.amqp_control_handler.amqp_incoming],
                "system": [self.amqp_system_handler.amqp_incoming],
                "sslcerts": [self._SSLCerts.amqp_incoming],
            }
        yield self.connect()

    def _stop_(self, **kwargs):
        """
        Called by the Yombo system when it's time to shutdown. This in turn calls the disconnect.
        :return:
        """
        if self.amqp_control_handler is not None:
            self.amqp_control_handler._stop_()
        if self.amqp_system_handler is not None:
            self.amqp_system_handler._stop_()
        self.disconnect()  # will be cleaned up by amqp library anyways, but it's good to be nice.

    def _unload_(self, **kwargs):
        """Disconnect the AMQPYombo connection on shutdown."""
        if self.amqp is not None:
            self.amqp.disconnect()

    @inlineCallbacks
    def _modules_imported_(self, **kwargs):
        """
        Call the '_amqpyombo_options_' hook to check if other modules should do something when the AMQPYombo connection
        opens and closes. It also checks if other modules have routes that can handle incoming messages.
        when t
        :param kwargs:
        :return:
        """
        results = yield global_invoke_all("_amqpyombo_options_", called_by=self)
        connected_callbacks = []  # Have to put this here since _modules_imported_ is invoked well after the initial
                                  # connection has been started.
        for component_name, data in results.items():
            if "connected" in data:
                self.amqpyombo_options["connected"].append(data["connected"])
                connected_callbacks.append(data["connected"])
            if "disconnected" in data:
                self.amqpyombo_options["disconnected"].append(data["disconnected"])
            if "routing" in data:
                for key, the_callback in data["gateway_routing"].items():
                    if key not in self.amqpyombo_options["gateway_routing"]:
                        self.amqpyombo_options["gateway_routing"][key] = []
                    self.amqpyombo_options["gateway_routing"][key].append(the_callback)

        if self.connected is True:
            for callback in self.amqpyombo_options["connected"]:
                callback()

    @inlineCallbacks
    def connect(self):
        """
        Called by '_init_' to connect to Yombo AMQP server.
        """
        if self.amqp is None:
            already_have_amqp = None
        else:
            already_have_amqp = True

        if self._Configs.get("amqpyombo.hostname", "", False) != "":
            amqp_host = self._Configs.get("amqpyombo.hostname")
            amqp_port = self._Configs.get("amqpyombo.port", 5672)
            amqp_use_ssl = self._Configs.get("amqpyombo.use_ssl", False)
        else:
            amqp_port = 5671
            amqp_use_ssl = True
            environment = self._Configs.get("server.environment", "production", False)
            if environment == "production":
                amqp_host = "amqp.yombo.net"
            elif environment == "staging":
                amqp_host = "amqpstg.yombo.net"
            elif environment == "development":
                amqp_host = "amqpdev.yombo.net"
            else:
                amqp_host = "amqp.yombo.net"

        keepalive = self._Configs.get("amqpyombo.keepalive", KEEPALIVE, False)
        prefetch_count = self._Configs.get("amqpyombo.prefetch_count", PREFETCH_COUNT, False)

        # get a new amqp instance and connect.
        if self.amqp is None:
            self.amqp = yield self._AMQP.new(hostname=amqp_host,
                                             # port=amqp_port,
                                             port=5666,
                                             use_ssl=amqp_use_ssl,
                                             virtual_host="yombo",
                                             username=self.user_id,
                                             password=self._Configs.get("core.gwhash"),
                                             client_id="amqpyombo",
                                             keepalive=keepalive,
                                             prefetch_count=prefetch_count,
                                             connected_callbacks=self.amqp_connected,
                                             disconnected_callbacks=self.amqp_disconnected,
                                             critical_connection=True)
        self.amqp.connect()

        # The servers will have a dedicated queue for us.
        if already_have_amqp is None:
            self.amqp.subscribe("ygw.q." + self.user_id,
                                incoming_callbacks=self.amqp_incoming,
                                auto_ack=False,
                                persistent=True)

    def disconnect(self):
        """
        Called by the yombo system when it's time to shutdown.

        :return:
        """
        if self._Loader.operating_mode != "run":
            return
        request_msg = self.generate_message_request(
            exchange_name="ysrv.e.gw_system",
            source="yombo.gateway.lib.amqpyombo",
            destination="yombo.server.gw_system",
            request_type="disconnect",
            message_headers={"request_type": "disconnect,"},
        )
        logger.debug("Sending amqpyombo disconnect")
        self.publish(**request_msg)

    def amqp_connected(self):
        """
        Setup from the 'connect' method, set in the 'connected_callback' argument.

        This method is called once the AMQPYombo connection is complete. This setups the loop that updates
        Yombo about our current status. Primarily used for Dynamic DNS updates.

        :return:
        """
        self.connected = True

        for callback in self.amqpyombo_options["connected"]:
            callback()

        if self.send_local_information_loop is None:
            self.send_local_information_loop = LoopingCall(self.send_local_information)

        # Sends various information, helps Yombo cloud know we are alive and where to find us.
        self.send_local_information()

        if self.send_local_information_loop.running is False:
            self.send_local_information_loop.start(random_int(60 * 60 * 4, .2), False)

    def amqp_disconnected(self):
        """
        Called by AQMP when disconnected.

        :return:
        """
        logger.debug("amqpyombo yombo disconnected: {state}", state=self._States.get('amqp.amqpyombo.state'))
        if self.connected is False:
            logger.error(
                "Unable to connect. This may be due to multiple connections or bad gateway hash. See: http://g2.yombo.net/noconnect")
            self._Loader.sigint = True
            self.amqp.disconnect()
            reactor.stop()
            return

        self.connected = False
        for the_callback in self.amqpyombo_options["disconnected"]:
            the_callback()
        if self.send_local_information_loop is not None and self.send_local_information_loop.running:
            self.send_local_information_loop.stop()

    def send_local_information(self):
        """
        Say hello, send some information about us. What we use these IP addresses for:

        Devices in your home can connect directly to the gateway for faster access. We give this information
        to your clients so they can find the gateway easier/faster.

        Your external IP is also given to your clients so they can attempt to connect directly to the gateway when
        you are not at home.

        If either of these connections are not available, applications can use the Yombo servers as proxy and will
        be delivered here as either a control or status request message.

        :return:
        """
        request_message = self.generate_message_request(
            exchange_name="ysrv.e.gw_system",
            source="yombo.gateway.lib.amqpyombo",
            destination="yombo.server.gw_system",
            body={
                "internal_ipv4": self._Configs.get("networking.localipaddress.v4"),
                "external_ipv4": self._Configs.get("networking.externalipaddress.v4"),
                "internal_ipv6": self._Configs.get("networking.externalipaddress.v6"),
                "external_ipv6": self._Configs.get("networking.externalipaddress.v6"),
                "internal_http_port": self._Configs.get("webinterface.nonsecure_port"),
                "external_http_port": self._Configs.get("webinterface.nonsecure_port"),
                "internal_http_secure_port": self._Configs.get("webinterface.secure_port"),
                "external_http_secure_port": self._Configs.get("webinterface.secure_port"),
                "internal_mqtt": self._Configs.get("mosquitto.server_listen_port"),
                "internal_mqtt_le": self._Configs.get("mosquitto.server_listen_port_le_ssl"),
                "internal_mqtt_ss": self._Configs.get("mosquitto.server_listen_port_ss_ssl"),
                "internal_mqtt_ws": self._Configs.get("mosquitto.server_listen_port_websockets"),
                "internal_mqtt_ws_le": self._Configs.get("mosquitto.server_listen_port_websockets_le_ssl"),
                "internal_mqtt_ws_ss": self._Configs.get("mosquitto.server_listen_port_websockets_ss_ssl"),
                "external_mqtt": self._Configs.get("mosquitto.server_listen_port"),
                "external_mqtt_le": self._Configs.get("mosquitto.server_listen_port_le_ssl"),
                "external_mqtt_ss": self._Configs.get("mosquitto.server_listen_port_ss_ssl"),
                "external_mqtt_ws": self._Configs.get("mosquitto.server_listen_port_websockets"),
                "external_mqtt_ws_le": self._Configs.get("mosquitto.server_listen_port_websockets_le_ssl"),
                "external_mqtt_ws_ss": self._Configs.get("mosquitto.server_listen_port_websockets_ss_ssl"),
            },
            request_type="connected",
            # callback=self.receive_local_information,
        )
        self.publish(priority="high", **request_message)

    def incoming_raw(self, channel, deliver, properties, message):
        """
        Receives the raw AMQP message from the AMQP server. This method will validate the message format, validate
        the headers, decode it's contents, and make the message more easily consumed by other modules/libraries.

        After this, it will forward to the 'incoming_callback' as defined in the subscription for final processing.

        :param channel:
        :param deliver:
        :param properties:
        :param message:
        :return:
        """
        received_at = time()
        if hasattr(properties, "headers") is False:
            raise YomboWarning("Missing headers property.")
        if not hasattr(properties, "user_id") or properties.user_id is None:
            self._Statistics.increment("lib.amqpyombo.received.discarded.nouserid", bucket_size=15, anon=True)
            raise YomboWarning("user_id missing.")
        if not hasattr(properties, "content_type") or properties.content_type is None:
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_type_missing", bucket_size=15,
                                       anon=True)
            raise YomboWarning("content_type missing.")
        if properties.content_type not in ("msgpack", "msgpack_zip", "msgpack_lz4"):
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_type_invalid", bucket_size=15,
                                       anon=True)
            raise YomboWarning("content_type does not hold a valid value.")

        property_headers = properties.headers
        required_message_headers = ("yombo_version", "route", "body_signature", "msg_sent_at")
        property_headers["msg_sent_at"] = float(property_headers["msg_sent_at"])
        for required in required_message_headers:
            if required not in property_headers:
                raise YomboWarning(f"Required property header is missing: {required}")

        if "yombo_version" not in property_headers:
            raise YomboWarning("Missing protocol header 'yombo_version'.")

        if int(property_headers["yombo_version"]) > PROTOCOL_VERSION:
            raise YomboWarning("This gateway software needs to be updated, AMQP Yombo protocol version mismatch.")
        message = self._Tools.data_unpickle(message, properties.content_type)

        if "headers" not in message:
            raise YomboWarning("headers missing from message.")
        if "body" not in message:
            raise YomboWarning("body missing from message.")

        message_headers = message["headers"]

        del message["headers"]
        required_message_headers = ("source", "destination", "message_type", "protocol_version", "correlation_id",
                                    "msg_created_at", "data_type")
        for required in required_message_headers:
            if required not in message_headers:
                logger.warn(f"Required message header is missing: {required}")
                raise YomboWarning(f"Required message header is missing: {required}")

        correlation_id = None
        reply_correlation_id = None

        if "correlation_id" in message_headers:
            correlation_id = message_headers["correlation_id"]
        if "reply_correlation_id" in message_headers:
            reply_correlation_id = message_headers["reply_correlation_id"]

        received_message_meta = {
            "content_type": properties.content_type,
            "msg_created_at": message_headers["msg_created_at"],
            "msg_sent_at": property_headers["msg_sent_at"],
            "msg_received_at": received_at,
            "direction": "incoming",
            "correlation_id": correlation_id,
            "reply_received_at": time(),
            "reply_correlation_id": reply_correlation_id,
            "reply_at": None,
            "round_trip_timing": None,
            "payload_size": len(message),
            "content_encoding": None,
        }

        sent_message_meta = None
        correlation_info = None
        if reply_correlation_id is not None:
            if reply_correlation_id.isalnum() is False or len(reply_correlation_id) < 15 or \
                    len(reply_correlation_id) > 100:
                raise YomboWarning("Invalid reply_correlation_id.")
            if reply_correlation_id not in self.message_log:
                # If there's no correlation and it's a Yombo message, ignore.
                raise YomboWarning("We don't know what message this is a reply to, must be old.")

            message_data = self.message_log[reply_correlation_id]
            sent_message_meta = message_data["message_meta"]
            correlation_info = message_data["correlation_info"]
            try:
                received_message_meta["round_trip_timing"] = received_at - sent_message_meta["msg_sent_at"]
            except Exception as e:
                logger.warn("Problem calculating message round_trip_timing: {e}", e=e)

        return {
            "channel": channel,
            "deliver": deliver,
            "properties": properties,
            "message": message["body"],
            "message_headers": message_headers,
            "property_headers": property_headers,
            "received_message_meta": received_message_meta,
            "sent_message_meta": sent_message_meta,
            "correlation_info": correlation_info,
        }

    @inlineCallbacks
    def amqp_incoming_routing(self, **kwargs):
        """
        Route the incoming message, this overrides AMQPMixin router.

        :param channel:
        :param deliver:
        :param properties:
        :param message:
        :param data:
        :return:
        """
        print(f"amqpyombo: amqp_incoming_routing: {kwargs}")
        message_headers = kwargs["message_headers"]
        if "gateway_routing" not in message_headers:
            raise YomboWarning("Discarding request message, header 'gateway_routing' is missing.")

        # Now, route the message. If it's a yombo message, send it to your AQMPYombo for delivery
        correlation_info = kwargs["correlation_info"]
        if correlation_info is not None and correlation_info["callback"] is not None and \
                callable(correlation_info["callback"]) is True:
            logger.debug("calling message callback, not incoming queue callback")
            yield maybeDeferred(correlation_info["callback"], **kwargs)

        # Lastly, send it to the callback defined by the hooks returned.
        else:
            routing = message_headers["gateway_routing"]
            logger.info("amqp_incoming_routing: routing: {routing}", routing=routing)

            # print("amqp_incoming..correlation info: %s" % correlation_info)
            print(f"amqp_incoming_routing..routing: {routing}")
            print(f"amqp_incoming_routing...available routes: {self.amqpyombo_options['routing']}")
            if routing in self.amqpyombo_options["routing"]:
                print("found a default route")
                for the_callback in self.amqpyombo_options["routing"][routing]:
                    print("about to call callback: %s" % the_callback)
                    yield maybeDeferred(the_callback, **kwargs)

    def generate_message_response(self, exchange_name: Optional[str] = None, source: Optional[str] = None,
                                  destination: Optional[str] = None, message_headers: Optional[dict] = None,
                                  body: Optional[Any] = None, routing_key: Optional[str] = None,
                                  callback: Optional[Callable] = None, correlation_id: Optional[str] = None,
                                  message_type: Optional[str] = None, response_type: Optional[str] = None,
                                  data_type: Optional[str] = None, route: Optional[List[str]] = None,
                                  gateway_routing: Optional[str] = None, reply_correlation_id: Optional[str] = None,
                                  previous_properties: Optional[dict] = None,
                                  previous_message_headers: Optional[dict] = None):
        """
        Generate a response message. Used locally and by other libraries and modules to send standard
        yombo messages.

        :param exchange_name:
        :param source:
        :param destination:
        :param message_headers:
        :param body:
        :param routing_key:
        :param callback:
        :param correlation_id:
        :param message_type:
        :param response_type:
        :param data_type:
        :param route:
        :param gateway_routing:
        :param reply_correlation_id:
        :param previous_properties:
        :param previous_message_headers:
        :return:
        """
        if self._Loader.operating_mode != "run":
            return {}
        if previous_properties is None:
            raise YomboWarning("generate_message_response() requires 'previous_properties' argument.")
        if previous_message_headers is None:
            raise YomboWarning("generate_message_response() requires 'previous_headers' argument.")

        if message_type is None:
            message_type = "response"

        if "correlation_id" in previous_message_headers and previous_message_headers["correlation_id"] is not None and \
                previous_message_headers["correlation_id"][0:2] != "xx_":
            reply_correlation_id = previous_message_headers["correlation_id"]

        response_msg = self.generate_message(exchange_name=exchange_name,
                                             source=source,
                                             destination=destination,
                                             message_type=message_type,
                                             data_type=data_type,
                                             body=body,
                                             routing_key=routing_key,
                                             callback=callback,
                                             correlation_id=correlation_id,
                                             message_headers=message_headers,
                                             reply_correlation_id=reply_correlation_id,
                                             route=route,
                                             gateway_routing=gateway_routing,
                                             )
        if response_type is not None:
            response_msg["body"]["headers"]["response_type"] = response_type

        return response_msg

    def generate_message_request(self, exchange_name: Optional[str] = None, source=None,
                                 destination: Optional[str] = None, message_headers: Optional[dict] = None,
                                 body: Optional[Any] = None, routing_key: Optional[str] = None,
                                 callback: Optional[Union[List[Callable], Callable]] = None,
                                 correlation_id: Optional[str] = None, message_type: Optional[str] = None,
                                 request_type: Optional[str] = None, data_type: Optional[str] = None,
                                 route: Optional[list] = None, gateway_routing: Optional[str] = None):
        if self._Loader.operating_mode != "run":
            return {}

        if message_type is None:
            message_type = "request"

        request_msg = self.generate_message(exchange_name=exchange_name,
                                            source=source,
                                            destination=destination,
                                            message_type=message_type,
                                            data_type=data_type,
                                            body=body,
                                            routing_key=routing_key,
                                            callback=callback,
                                            correlation_id=correlation_id,
                                            message_headers=message_headers,
                                            route=route,
                                            gateway_routing=gateway_routing,
                                            )
        if request_type is not None:
            request_msg["body"]["headers"]["request_type"] = request_type

        return request_msg

    def generate_message(self, exchange_name: str, source: str, destination: str, message_type: str,
                         data_type: Optional[str] = None, body: Optional[Any] = None,
                         routing_key: Optional[str] = None, callback: Optional[Union[List[Callable], Callable]] = None,
                         correlation_id: Optional[str] = None, message_headers: Optional[dict] = None,
                         reply_correlation_id: Optional[str] = None, route=None, gateway_routing: Optional[str] = None):
        """
        When interacting with Yombo AMQP servers, we use a standard messaging layout. The format
        below helps other functions and libraries conform to this standard.

        This only creates the message, it doesn't send it. Use the publish() function to complete that.

        **Usage**:

        .. code-block:: python

           requestData = {
               "exchange_name" : "gw_other",
               "source"        : "yombo.gateway.lib.configurationupdate",
               "destination"   : "yombo.server.configs",
               "callback"      : self.amqp_direct_incoming,
               "data_type      : "object",
               "body"          : payload_content,  # Usually a dictionary.
               },
           }
           request = self.AMQPYombo.generateRequest(**requestData)

        :param exchange_name: The exchange the request should go to.
        :type exchange_name: str
        :param source: Value for the 'source' field.
        :type source: str
        :param destination: Value of the 'destination' field.
        :type destination: str
        :param message_type: Type of header. Usually one of: request, response
        :type message_type: str
        :param data_type: One of: Object, Objects, or String
        :type data_type: string
        :param body: The part that will become the body, or payload, of the message.
        :type body: str, dict, list
        :param routing_key: Routing key to use for message delivery. Usually '*'.
        :type routing_key: str
        :param callback: A pointer to the function to return results to. This function will receive 4 arguments:
          sendInfo (Dict) - Various details of the sent packet. deliver (Dict) - Deliver fields as returned by Pika.
          props (Pika Object) - Message properties, includes headers. msg (dict) - The actual content of the message.
        :type callback: function
        :param correlation_id: A correlation_id to use.
        :type correlation_id: string
        :param message_headers: Extra headers. Note: these cannot be validated with GPG/PGP keys.
        :type message_headers: dict

        :return: A dictionary that can be directly returned to Yombo SErvers via AMQP
        :rtype: dict
        """
        if self._Loader.operating_mode != "run":
            return {}

        if routing_key is None:
            routing_key = "*"

        if body is None:
            body = {}

        if correlation_id is None:
            correlation_id = random_string(length=24)

        if data_type is None:
            if isinstance(body, list):
                data_type = "objects"
            elif isinstance(body, str):
                data_type = "string"
            else:
                data_type = "object"

        if route is None:
            route = ["yombo.gw.amqpyombo:" + self.user_id]
        else:
            route.append("yombo.gw.amqpyombo:" + self.user_id)

        msg_created_at = time()
        request_msg = {
            "exchange_name": exchange_name,
            "routing_key": routing_key,
            "body": {
                "headers": {
                    "source": source + ":" + self.user_id,
                    "destination": destination,
                    "message_type": message_type.lower(),
                    "protocol_version": PROTOCOL_VERSION,
                    "correlation_id": correlation_id,
                    "msg_created_at": msg_created_at,
                    "data_type": data_type.lower(),
                },
                "body": body,
            },
            "properties": {
                "user_id": self.user_id,  # system id is required to be able to send it.
                "content_type": "msgpack",
                "headers": {
                    "route": route,
                    "yombo_version": PROTOCOL_VERSION,
                    "body_signature": "",
                },
            },
            "meta": {
                "finalized_for_sending": False,
            },
        }

        if gateway_routing is not None:
            request_msg["body"]["headers"]["gateway_routing"] = gateway_routing
        if isinstance(message_headers, dict):
            request_msg["body"]["headers"].update(message_headers)

        if callback is not None:
            request_msg["callback"] = callback
            if correlation_id is None:
                request_msg["body"]["headers"]["correlation_id"] = random_string(length=24)

        if reply_correlation_id is not None:
            request_msg["body"]["headers"]["reply_correlation_id"] = reply_correlation_id

        return request_msg

    def finalize_message(self, message: dict):
        if "correlation_id" in message["body"]["headers"]:
            message["properties"]["correlation_id"] = message["body"]["headers"]["correlation_id"]
        if "reply_correlation_id" in message["body"]["headers"]:
            message["properties"]["headers"]["reply_correlation_id"] = message["body"]["headers"]["reply_correlation_id"]
        message["body"] = msgpack.packb(message["body"])

        # Lets test if we can compress. Set headers as needed.

        beforeZlib = len(message["body"])
        if beforeZlib > 900:
            message["properties"]["content_type"] = "msgpack_zip"
            message["body"] = self._Tools.data_pickle(message["body"], "zip")
        message["meta"]["compression_percent"] = round(percentage(len(message["body"]), beforeZlib), 2)
        message["meta"]["finalized_for_sending"] = True
        return message

    def publish(self, **kwargs):
        """
        Publishes a message. Use generate_message(), generate_message_request, or generate_message_response to
        create the message.

        kwargs contains:
          * exchange_name
          * routing_key
          * body
            * headers
            * body
          * properties
            * user_id
            * content_type
            * headers (non-hashed, non-encrypted, essential routing/decoding headers)
              * route
              * yombo_version
              * body_signature
          * meta

        :return:
        """
        if self._Loader.operating_mode != "run":
            return

        logger.debug("about to publish: {kwargs}", kwargs=kwargs)
        if kwargs["meta"]["finalized_for_sending"] is False:
            kwargs = self.finalize_message(kwargs)
        if "callback" in kwargs:
            if "correlation_id" not in kwargs["properties"]:
                kwargs["properties"]["correlation_id"] = random_string()

        results = self.amqp.publish(**kwargs)
        correlation_info = results["correlation_info"]
        if correlation_info is not None:
            correlation_id = correlation_info["correlation_id"]
            self.message_log[correlation_id] = results
