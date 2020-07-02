# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Gateway Communications @ Library Documentation <https://yombo.net/docs/libraries/mqttyombo>`_

Handles inter-gateway communications. Broadcasts information about this gateway on startup. It will
also broadcast a message for all gateways to send their updated status information.

If this is the master gateway, it will also track additional gateway details, such as long device status history.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.21.0
   Added as gatewaycommunications library.
.. versionadded:: 0.24.0
   Renamed to mqttyombo and expanded the library.

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/mqttyombo/__init__.html>`_
"""
from collections import deque
from random import randint
import socket
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.constants.mqttyombo import *
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.lib.mqttyombo.atoms_mixin import AtomsMixin
from yombo.lib.mqttyombo.incoming_gw_mixin import IncomingGwMixin
from yombo.lib.mqttyombo.ping_mixin import PingMixin
from yombo.lib.mqttyombo.publishing_mixin import PublishingMixin
from yombo.lib.mqttyombo.states_mixin import StatesMixin
from yombo.utils import sleep

logger = get_logger("library.mqttyombo")


class MQTTYombo(YomboLibrary, PublishingMixin, IncomingGwMixin,
                AtomsMixin, PingMixin, StatesMixin):
    ok_to_publish_updates = False
    enabled = False

    def _init_(self, **kwargs):
        """Setup MQTTYombo library."""
        self.enabled = self._Configs.get("mqttyombo.enabled", True, False)

        self.ok_to_publish_updates = False
        self.log_incoming = deque([], 150)
        self.log_outgoing = deque([], 150)
        self.subscription_callbacks = {}
        self.mqtt = None

        self.default_host = "127.0.0.1"
        self.default_port = 1885
        self.default_use_ssl = True
        self.default_ws_port = None
        self.default_ws_use_ssl = True
        self.default_username = "yombogw-" + self._gateway_id

        local_gateway = self._Gateways.local
        self.default_password1 = local_gateway.mqtt_auth
        self.default_password2 = local_gateway.mqtt_auth_next

        if self._is_master:
            self.default_host = "127.0.0.1"
            self.default_port = self._Configs.get("mosquitto.server_listen_port", None, False)
            self.default_use_ssl = False
            self.default_ws_port = None
            self.default_ws_use_ssl = None

    def _load_(self, **kwargs):
        """Determine connection details to the MQTT broker."""
        master_gateway = self._Gateways.master

        def test_port(host, port, local):
            """ Quick function to test if host is listening to a port. """
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if local is True:
                sock.settimeout(0.5)
            logger.debug("Test host:port: {host}:{port}", host=host, port=port)
            if port is None:
                return False
            results = sock.connect_ex((host, port))
            logger.debug("Test host:port, results: {results}", results=results)
            return results

        # Now determine the optimal mqtt connection to the master gateway. Order or preference:
        # 1) We prefer localhost with no SSL since it's all internal - less CPU on low end devics.
        # 2) Local network, but with SSL preferred.
        # 3) Remote network, only SSL!
        # print(f"Is master: {self._is_master}")
        mqtt_hosts = []
        if self._is_master:
            mqtt_hosts.append({
                "address": "127.0.0.1",
                "local": True,
                "mqtt": [
                    {"port": self._Configs.get("mosquitto.server_listen_port"), "use_ssl": False},
                    {"port": self._Configs.get("mosquitto.server_listen_port_le_ssl"), "use_ssl": True},
                    {"port": self._Configs.get("mosquitto.server_listen_port_ss_ssl"), "use_ssl": True},
                    {"port": master_gateway.internal_mqtt_le, "use_ssl": True},
                    {"port": master_gateway.internal_mqtt_ss, "use_ssl": True},
                    {"port": master_gateway.internal_mqtt, "use_ssl": False},
                ],
                "ws": [
                    # {"port": master_gateway.internal_mqtt_ws, "ssl": False},
                    {"port": self._Configs.get("mosquitto.server_listen_port_websockets_le_ssl"), "use_ssl": True},
                    {"port": self._Configs.get("mosquitto.server_listen_port_websockets_ss_ssl"), "use_ssl": True},
                    {"port": master_gateway.internal_mqtt_ws_le, "use_ssl": True},
                    {"port": master_gateway.internal_mqtt_ws_ss, "use_ssl": True},
                    {"port": master_gateway.internal_mqtt_ws, "use_ssl": False},
                ]
            })
            fqdn = self._Configs.get("dns.fqdn", None, False)
            if fqdn is not None:
                mqtt_hosts.append({
                        "address": "internal." + fqdn,
                        "local": True,
                        "mqtt": [
                            {"port": self._Configs.get("mosquitto.server_listen_port"), "use_ssl": False},
                            {"port": self._Configs.get("mosquitto.server_listen_port_le_ssl"), "use_ssl": True},
                            {"port": self._Configs.get("mosquitto.server_listen_port_ss_ssl"), "use_ssl": True},
                        ],
                        "ws": [
                            # {"port": master_gateway.internal_mqtt_ws, "use_ssl": False},
                            {"port": self._Configs.get("mosquitto.server_listen_port_websockets_le_ssl"), "use_ssl": True},
                            {"port": self._Configs.get("mosquitto.server_listen_port_websockets_ss_ssl"), "use_ssl": True},
                        ]
                    }
                )
            else:
                mqtt_hosts.append({
                    "address": self._Configs.get("networking.localipaddress.v4"),
                        "local": False,
                        "mqtt": [
                            {"port": self._Configs.get("mosquitto.server_listen_port"), "use_ssl": False},
                            {"port": self._Configs.get("mosquitto.server_listen_port_ss_ssl"), "use_ssl": True},
                        ],
                        "ws": [
                            # {"port": master_gateway.internal_mqtt_ws, "use_ssl": False},
                            {"port": self._Configs.get("mosquitto.server_listen_port_websockets_ss_ssl"), "use_ssl": True},
                        ]
                    }
                )

        else:
            mqtt_hosts.append({
                    "address": "internal." + master_gateway.dns_name,
                    "local": True,
                    "mqtt": [
                        {"port": master_gateway.internal_mqtt_le, "use_ssl": True},
                        {"port": master_gateway.internal_mqtt_ss, "use_ssl": True},
                        {"port": master_gateway.internal_mqtt, "use_ssl": False},
                    ],
                    "ws": [
                        {"port": master_gateway.internal_mqtt_ws_le, "use_ssl": True},
                        {"port": master_gateway.internal_mqtt_ws_ss, "use_ssl": True},
                    ]
                }
            )
            mqtt_hosts.append({
                "address": "external." + master_gateway.dns_name,
                    "local": False,
                    "mqtt": [
                        {"port": master_gateway.external_mqtt_le, "use_ssl": True},
                        {"port": master_gateway.external_mqtt_ss, "use_ssl": True},
                    ],
                    "ws": [
                        {"port": master_gateway.external_mqtt_ws_le, "use_ssl": True},
                        {"port": master_gateway.external_mqtt_ws_ss, "use_ssl": True},
                    ]
                }
            )

        for host in mqtt_hosts:
            address = host["address"]
            local = host["local"]
            for port in host["mqtt"]:
                if port["port"] is None:
                    continue
                if test_port(address, port["port"], local) == 0:  # if 0, we can connect and server is listening.
                    self.default_host = address
                    self.default_port = port["port"]
                    self.default_use_ssl = port["use_ssl"]
                    break
            if self.default_host is not None:
                for port in host["ws"]:
                    if test_port(address, port["port"], local) == 0:  # if 0, we can connect and server is listening.
                        self.default_ws_port = port["port"]
                        self.default_ws_use_ssl = port["use_ssl"]
                        break
                break

        if self.default_host is None:
            logger.warn("Cannot find an open MQTT port to the master gateway.")

    @inlineCallbacks
    def _start_(self, **kwargs):
        """
        Connect to the MQTT broker for gateway communications. Subscribes to various topics.

        :param kwargs:
        :return:
        """
        self.subscription_callbacks = {}
        if self.enabled is False:
            return
        self.last_will = self._MQTT.last_will(f"yombo_gw/{self._gateway_id}/cluster/offline", "offline")
        self.mqtt = yield self._MQTT.new(hostname=self.default_host, port=self.default_port,
                                         username=self.default_username, password=self.default_password1,
                                         use_ssl=self.default_use_ssl, last_will=self.last_will,
                                         on_message_callback=self.incoming_parse,
                                         client_id=f"mqttyombo-{self._gateway_id}")
        # print(f"mqtt:::::::::::::::::::::::::: {self.mqtt}")

        # Each library is gets it's own subscriptions, one for itself and one for 'cluster'.
        # This allows each specific topic to be routed to the correct library for an incoming message
        # Cluster - gateways within a the cluster.
        # Global - all gateways, within the cluster or not (not fully implemented yet, need to shovel
        #          messages between clusters).
        libraries = ["atoms", "states"]
        destinations = ["global", "cluster", self._gateway_id]

        incoming_yombo_gw_id = self.unqiue_subscription_id()
        self.subscription_callbacks[incoming_yombo_gw_id] = self.incoming_yombo_gw_base

        incoming_yombo_id = self.unqiue_subscription_id()
        self.subscription_callbacks[incoming_yombo_id] = self.incoming_yombo_base

        for library in libraries:
            on_message_callback = getattr(self, f"incoming_{library}")
            for destination in destinations:
                self.mqtt.subscribe(f"yombo_gw/+/{destination}/{library}",
                                    qos=1,
                                    subscription_identifier=incoming_yombo_gw_id)

            subscribe_id = self.unqiue_subscription_id()
            self.subscription_callbacks[subscribe_id] = on_message_callback
            self.mqtt.subscribe(f"yombo/#",
                                qos=1,
                                subscription_identifier=incoming_yombo_id)

        # self.test()  # todo: move to unit tests..  Todo: Create unit tests.. :-)

    def _started_(self, **kwargs):
        """
        Publish that this gateway is online, start pinging other gateways.

        :param kwargs:
        :return:
        """
        # print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! mqtt started 1")
        if self.enabled is False:
            return
        # print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! mqtt started 2")

        self.publish_yombo_gw(topic="system/online", payload=None, destination="global", publish=True)
        reactor.callLater(0.1, self.send_all_info, set_ok_to_publish_updates=True)

        if self._is_master is True:
            ping_interval = self._Configs.get("mqttyombo.ping_interval_master", 120, False)
        else:
            ping_interval = self._Configs.get("mqttyombo.ping_interval_members", 600, False)

        self.send_presence_loop = LoopingCall(self.send_presence)
        self.send_presence_loop.start(30, False)

        # self.ping_gateways_loop = LoopingCall(self.ping_gateways)
        # self.ping_gateways_loop.start(ping_interval, True)

    @inlineCallbacks
    def _stop_(self, **kwargs):
        """Tell other gateways we are going offline."""
        if self.enabled is False or hasattr(self, "_Loader") is False or self._Loader.operating_mode != "run":
            return

        if hasattr(self, "mqtt") and self.mqtt is not None:
            self.publish_yombo_gw(topic="system/offline", payload=None, destination="global", publish=True)
            yield sleep(0.100)

    def unqiue_subscription_id(self):
        """Generate a unique subscription ID that is not already in use."""
        subscribe_id = None
        while subscribe_id in self.subscription_callbacks or subscribe_id is None:
            subscribe_id = randint(10, 200000)
        return subscribe_id

    def get_return_destination(self, destination=None):
        if destination is None or destination is "":
            return "all"
        return destination

    def add_subscription(self, topic, on_message_callback):
        """
        Adds an additional topic to subscribe to along with it's callback. This allows modules to handle additional
        mqtt requests.

        :param topic:
        :param on_message_callback:
        :return:
        """
        destinations = ["global", "cluster", self._gateway_id]
        for destination in destinations:
            subscribe_id = self.unqiue_subscription_id()
            self.subscription_callbacks[subscribe_id] = on_message_callback
            self.mqtt.subscribe(f"yombo_gw/+/{destination}/{topic}",
                                qos=1,
                                subscription_identifier=subscribe_id)

    @inlineCallbacks
    def incoming_parse(self, client, topic, body, qos, properties, *args, **kwargs):
        """
        Handles _all_ the incoming messages, including messages from non-gateways. Validates the message, and then
        routes them to the proper final callback.

        :param client:
        :param topic:
        :param payload:
        :param qos:
        :param properties:
        :return:
        """
        # print(f"mqttyombo, incoming_parse: topic={topic}")
        # print(f"mqttyombo, incoming_parse: body={body}")
        # print(f"mqttyombo, incoming_parse: properties={properties}")
        # print(f"mqttyombo, incoming_parse: args={args}")
        # print(f"mqttyombo, incoming_parse: kwargs={kwargs}")

        if "subscription_identifier" not in properties:
            logger.warn("Discarding topic '{topic}', missing subscription_identifier.", topic=topic)
            return

        subscription_identifier = properties["subscription_identifier"][0]
        if subscription_identifier not in self.subscription_callbacks:
            logger.warn("Discarding topic '{topic}', missing subscription_identifier from callbacks.", topic=topic)
            return

        yield maybeDeferred(self.subscription_callbacks[subscription_identifier], topic=topic, body=body, qos=qos,
                            properties=properties)


        topic_parts = topic.split("/")
        if topic_parts[0] not in ("yombo_gw", "yombo_req"):
            return


        topic_source = topic_parts[1]
        topic_destination = topic_parts[2]

        if topic_source not in self._Gateways.gateways:
            logger.debug("Dropping mqttyombo payload - source gateway is unknown.")
            return

        if topic_source == self._gateway_id:
            logger.debug("Dropping mqttyombo payload - source is us.")
            return

        if topic_destination not in (self._gateway_id, "cluster", "global"):
            logger.debug("Dropping mqttyombo payload - destination gateway is not for us..")
            return

        # Validate properties
        if "content_type" not in properties:
            logger.debug("Dropping mqttyombo payload - missing content_type in properties.")
            return
        if "sig" not in properties:
            logger.debug("Dropping mqttyombo payload - missing sig in properties.")
            return
        if "message_type" not in properties:
            logger.debug("Dropping mqttyombo payload - missing message_type in properties.")
            return
        if "protocol_version" not in properties:
            logger.debug("Dropping mqttyombo payload - missing protocol_version in properties.")
            return

        payload = self._Tools.data_unpickle(body, properties["content_type"])

        # Validate headers
        if "headers" not in payload:
            logger.debug("Dropping mqttyombo payload - missing headers.")
            return
        headers = payload["headers"]
        if "correlation_id" not in headers:
            logger.debug("Dropping mqttyombo payload - correlation_id from headers.")
            return
        if "message_type" not in headers:
            logger.debug("Dropping mqttyombo payload - message_type from headers.")
            return
        if "reply_correlation_id" not in headers:
            logger.debug("Dropping mqttyombo payload - reply_correlation_id from headers.")
            return
        if "created_at" not in headers:
            logger.debug("Dropping mqttyombo payload - created_at from headers.")
            return

        # Validate body
        if "body" not in payload:
            logger.debug("Dropping mqttyombo payload - missing body.")
            return

        self._Gateways.gateways[topic_source].last_seen = time()
        self._Gateways.gateways[topic_source].last_communications.append({
                "time": int(time()),
                "direction": "received",
                "topic": topic,
            })

        subscription_identifier = properties["subscription_identifier"]
        if subscription_identifier in self.subscription_callbacks:
            self.subscription_callbacks[subscription_identifier](topic=topic, payload=payload["body"],
                                                                 headers=headers, properties=properties,
                                                                 source=topic_source, destination=topic_destination)
        else:
            logger.warn("Dropping mqttyombo payload - unknown subscription_id, topic: {topic}", topic=topic)
