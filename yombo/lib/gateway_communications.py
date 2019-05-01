# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. warning::

   This library is not intended to be accessed by module developers or end users. These functions, variables,
   and classes were not intended to be accessed directly by modules. These are documented here for completeness.

.. note::

  * For library documentation, see: `Gateway Communications @ Library Documentation <https://yombo.net/docs/libraries/gateway_communications>`_

Handles inter-gateway communications. Broadcasts information about this gateway on startup. It will
also broadcast a message for all other gateways to send their updated status information.

If this is the master gateway, it will also track additional gateway details, such as long device status history.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.21.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/gateway_communications.html>`_
"""
from copy import deepcopy
from collections import deque
import socket
from time import time
import traceback

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import random_int, data_pickle, data_unpickle, random_string, sleep, sha256_compact

logger = get_logger("library.gateway_communications")


class Gateway_Communications(YomboLibrary):
    ok_to_publish_updates = False

    def _init_(self, **kwargs):
        if self._Loader.operating_mode != "run":
            return

        self.ok_to_publish_updates = False
        self.log_incoming = deque([], 150)
        self.log_outgoing = deque([], 150)
        self.mqtt = None
        self.gateway_id = self._Configs.gateway_id
        self.is_master = self._Configs.is_master
        self.master_gateway_id = self._Configs.master_gateway_id

        # Internal here means for internal use, for the framework only or modules making
        # connections to the MQTT broker for Yombo use.
        # The non-internal is used to show to external services/devices/webpages.
        self.client_default_host = None
        self.client_default_port = None
        self.client_default_ssl = None
        self.client_default_ws_port = None
        self.client_default_ws_ssl = None

    def _load_(self, **kwargs):
        if self._Loader.operating_mode != "run":
            return

        local_gateway = self._Gateways.local
        master_gateway = self._Gateways.master

        self.client_default_username = "yombogw_" + self.gateway_id()
        self.client_default_password1 = local_gateway.mqtt_auth
        self.client_default_password2 = local_gateway.mqtt_auth_next

        if self._Loader.operating_mode != "run":
            logger.warn("Gateway communications disabled when not in run mode.")
            return

        def test_port(host, port):
            """ Quick function to test if host is listening to a port. """
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            logger.info("# Test non ssl host - port: {host} - {port}", host=host, port=port)
            if port is None:
                return False
            return sock.connect_ex((host, port))

        # Now determine the optimal mqtt connection to the master gateway. Order or preference:
        # 1) We prefer localhost with no SSL since it's all internal - less CPU on low end devics.
        # 2) Local network, but with SSL preferred.
        # 3) Remote network, only SSL!
        if self.is_master():
            fqdn = self._Configs.get("dns", "fqdn", None, False)
            if fqdn is not None:
                mqtt_hosts = [
                    {
                        "address": "internal." + fqdn,
                        "mqtt": [
                            {"port": self._Configs.get("mqtt", "server_listen_port"), "ssl": False},
                            {"port": self._Configs.get("mqtt", "server_listen_port_le_ssl"), "ssl": True},
                            {"port": self._Configs.get("mqtt", "server_listen_port_ss_ssl"), "ssl": True},
                        ],
                        "ws": [
                            # {"port": master_gateway.internal_mqtt_ws, "ssl": False},dns_
                            {"port": self._Configs.get("mqtt", "server_listen_port_websockets_le_ssl"), "ssl": True},
                            {"port": self._Configs.get("mqtt", "server_listen_port_websockets_ss_ssl"), "ssl": True},
                        ]
                    }
                ]
            else:
                mqtt_hosts = [
                    {
                        "address": self._Configs.get("core", "localipaddress_v4"),
                        "mqtt": [
                            {"port": self._Configs.get("mqtt", "server_listen_port"), "ssl": False},
                            {"port": self._Configs.get("mqtt", "server_listen_port_ss_ssl"), "ssl": True},
                        ],
                        "ws": [
                            # {"port": master_gateway.internal_mqtt_ws, "ssl": False},
                            {"port": self._Configs.get("mqtt", "server_listen_port_websockets_ss_ssl"), "ssl": True},
                        ]
                    }
                ]

        else:
            mqtt_hosts = [
                {
                    "address": "internal." + master_gateway.dns_name,
                    "mqtt": [
                        {"port": master_gateway.internal_mqtt_le, "ssl": True},
                        {"port": master_gateway.internal_mqtt_ss, "ssl": True},
                        {"port": master_gateway.internal_mqtt, "ssl": False},
                    ],
                    "ws": [
                        {"port": master_gateway.internal_mqtt_ws_le, "ssl": True},
                        {"port": master_gateway.internal_mqtt_ws_ss, "ssl": True},
                    ]
                },
                {
                    "address": "external." + master_gateway.dns_name,
                    "mqtt": [
                        {"port": master_gateway.external_mqtt_le, "ssl": True},
                        {"port": master_gateway.external_mqtt_ss, "ssl": True},
                    ],
                    "ws": [
                        {"port": master_gateway.external_mqtt_ws_le, "ssl": True},
                        {"port": master_gateway.external_mqtt_ws_ss, "ssl": True},
                    ]
                }

            ]

        for host in mqtt_hosts:
            address = host["address"]
            for port in host["mqtt"]:
                if test_port(address, port["port"]) == 0:  # if 0, we can connect and server is listening.
                    self.client_default_host = address
                    self.client_default_port = port["port"]
                    self.client_default_ssl = port["ssl"]
                    break
            if self.client_default_host is not None:
                for port in host["ws"]:
                    if test_port(address, port["port"]) == 0:  # if 0, we can connect and server is listening.
                        self.client_default_ws_port = port["port"]
                        self.client_default_ws_ssl = port["ssl"]
                        break
                break

        if self.client_default_host is None:
            logger.warn("Cannot find an open MQTT port to the master gateway.")

    def _start_(self, **kwargs):
        """
        Connect to the MQTT broker for gateway communciations. Subscribes to various topics.
        :param kwargs:
        :return:
        """
        if self._Loader.operating_mode != "run":
            return
        self.mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming,
                                   client_id=f"Yombo-gwcoms-{self.gateway_id()}")

        # self.test()  # todo: move to unit tests..  Todo: Create unit tests.. :-)
        # Data broadcasts or data responses to gateways
        self.mqtt.subscribe("ybo_gw/+/all")
        self.mqtt.subscribe("ybo_gw/+/cluster")
        self.mqtt.subscribe(f"ybo_gw/+/{self.gateway_id()}")

        # Requests from other gateways
        self.mqtt.subscribe("ybo_req/+/all/#")
        self.mqtt.subscribe("ybo_req/+/cluster/#")
        self.mqtt.subscribe(f"ybo_req/+/{self.gateway_id()}")

    def _started_(self, **kwargs):
        """
        Publish that this gateway is online, start pinging other gateways.
        :param kwargs:
        :return:
        """
        if self._Loader.operating_mode != "run":
            return
        self.publish_data(destination_id="all",
                          component_type="lib", component_name="system_state",
                          payload="online")
        reactor.callLater(3, self.send_all_info, set_ok_to_publish_updates=True)

        if self.is_master is True:
            ping_interval = self._Configs.get("mqtt", "ping_interval_master", 120, False)
        else:
            ping_interval = self._Configs.get("mqtt", "ping_interval_members", 600, False)

        self.ping_gateways_loop = LoopingCall(self.ping_gateways)
        self.ping_gateways_loop.start(ping_interval, True)

    @inlineCallbacks
    def _stop_(self, **kwargs):
        """
        Tell other gateways we are going offline.
        """
        if hasattr(self, "_Loader") is False or self._Loader.operating_mode != "run":
            return
        if hasattr(self, "mqtt"):
            if self.mqtt is not None:
                self.publish_data(destination_id="all",
                                  component_type="lib", component_name="system_state",
                                  payload="offline")
                yield sleep(0.2)

    @inlineCallbacks
    def ping_gateways(self):
        """
        Pings all the known gateways.

        :return:
        """
        my_gateway_id = self.gateway_id()
        for gateway_id, gateway in self._Gateways.gateways.items():
            if gateway_id in ("local", "all", "cluster", my_gateway_id) or len(gateway_id) < 13:
                continue
            current_time = time()
            request_id = self.publish_data(destination_id=gateway_id,
                                           component_type="lib", component_name="system_ping",
                                           payload=time(), message_type="req")
            self._Gateways.gateways[gateway_id].ping_request_id = request_id
            self._Gateways.gateways[gateway_id].ping_request_at = current_time
            yield sleep(0.1)

    def _atoms_set_(self, **kwargs):
        """
        Publish a new atom, only if it"s from ourselves.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return
        if "source" in kwargs and kwargs["source"] == "gateway_coms":
            return
        if kwargs["gateway_id"] != self.gateway_id():
            return

        atom = {kwargs["key"]: kwargs["value_full"]}
        self.publish_data(destination_id="all",
                          component_type="lib", component_name="atoms_set",
                          payload=atom)

    def _device_command_(self, **kwargs):
        """
        A new command for a device has been sent. This is used to tell other gateways that either a local device
        is about to do something, other another gateway should do something.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return

        device_command = kwargs["device_command"].asdict()
        if device_command["source_gateway_id"] != self.gateway_id():
            return

        payload = {
            "state": "new",
            "device_command": device_command
        }

        self.publish_data(destination_id="all",
                          component_type="lib", component_name="device_command",
                          payload=payload)

    def _device_command_status_(self, **kwargs):
        """
        A device command has changed status. Update everyone else.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return
        if "source" in kwargs and kwargs["source"] == "gateway_coms":
            return

        device_command = kwargs["device_command"]
        if device_command.source_gateway_id != self.gateway_id():
            return

        history = device_command.last_history()
        payload = {
            device_command.request_id: {
                "request_id": kwargs["device_command"].request_id,
                "log_time": history["time"],
                "status": history["status"],
                "message": history["msg"],
            }
        }

        self.publish_data(destination_id="all",
                          component_type="lib", component_name="device_command_status",
                          payload=payload)

    def _device_status_(self, **kwargs):
        """
        Publish a new state, if it's from ourselves.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return
        source = kwargs.get("source", None)
        if source == "gateway_coms":
            return
        device = kwargs["device"]
        device_id = device.device_id

        if self.gateway_id() != device.gateway_id:
            return

        self.publish_data(destination_id="all",
                          component_type="lib", component_name="device_status",
                          payload=[device.status_all.asdict()])

    def _notification_add_(self, **kwargs):
        """
        Publish a new notification, if it"s from ourselves.

        :param kwargs:
        """
        # print("_device_status_: %s" % kwargs["command"])
        if self.ok_to_publish_updates is False:
            return

        notice = kwargs["notification"]
        if notice.local is True:
            return

        # print("checking if i should send this device_status.  %s != %s" % (self.gateway_id(), device.gateway_id))
        if self.gateway_id() != notice.gateway_id:
            return

        message = {
            "action": "add",
            "notice": kwargs["event"],
        }

        topic = "lib/notification/" + notice.notification_id
        # print("sending _device_status_: %s -> %s" % (topic, message))
        # self.publish_data("gw", "all", topic, message)

    def _notification_delete_(self, **kwargs):
        """
        Delete a notification, if it's from ourselves.

        :param kwargs:
        :return:
        """
        # print("_device_status_: %s" % kwargs["command"])
        if self.ok_to_publish_updates is False:
            return

        notice = kwargs["notification"]
        if notice.local is True:
            return

        # print("checking if i should send this device_status.  %s != %s" % (self.gateway_id(), device.gateway_id))
        if self.gateway_id() != notice.gateway_id:
            return

        message = {
            "action": "delete",
            "notice": kwargs["event"],
        }

        topic = "lib/notification/" + notice.notification_id
        # print("sending _device_status_: %s -> %s" % (topic, message))
        # self.publish_data("gw", "all", topic, message)

    def _states_set_(self, **kwargs):
        """
        Publish a new state, if it's from ourselves.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return
        if "source" in kwargs and kwargs["source"] == "gateway_coms":
            return
        gateway_id = kwargs["gateway_id"]
        if gateway_id != self.gateway_id() and gateway_id not in ("global", "cluster"):
            return

        message = deepcopy(kwargs["value_full"])
        message["key"] = kwargs["key"]

        state = {kwargs["key"]: kwargs["value_full"]}
        self.publish_data(destination_id="all",
                          component_type="lib", component_name="states_set",
                          payload=state)

    @inlineCallbacks
    def mqtt_incoming(self, topic, raw_message, qos, retain):
        """
        All incoming items for these topics are delivered here:
        ybo_gw/+/["all", "cluster", or local gateway] - Broadcasts to al, or gw to gw coms
        ybo_req/+/["all", "cluster", or local gateway] - Other gateways requesting info

        All incoming
        :param topic:
        :param raw_message:
        :param qos:
        :param retain:
        :return:
        """
        # ybo_req/src_gwid/dest_gwid
        topic_parts = topic.split("/", 10)
        if topic_parts[0] not in ("ybo_req", "ybo_gw"):  # this shouldn"t ever happen.
            logger.info("Received a message, but it's has the wrong topic type.")
            return

        try:
            message = self.decode_message(topic, raw_message)
        except YomboWarning as e:
            logger.info("Could not decode inter-gateway coms message: {e}", e=e)
            return

        gateway_id = self.gateway_id()
        body = message["body"]
        if body["source_id"] == gateway_id:
            logger.debug("discarding message that I sent: %s." % body["source_id"])
            return
        if body["destination_id"] not in (gateway_id, "all", "cluster"):
            logger.info("MQTT message doesn't list us as a target, dropping")
            return

        # logger.debug("got mqtt in: {topic} - {message}", topic=topic, message=message)

        if body["source_id"] in self._Gateways.gateways:
            self._Gateways.gateways[body["source_id"]].last_scene = time()
            self._Gateways.gateways[body["source_id"]].last_communications.append({
                "time": body["time_received"],
                "direction": "received",
                "topic": f"{topic}/{body['component_type']}/{body['component_name']}",
            })
        else:
            raise YomboWarning("Received an mqtt gw-coms message from an unknown gateway. Dropping.")

        self.log_incoming.append({"received": time(), "topic": topic, "message": message})
        if topic_parts[0] == "ybo_gw":
            yield self.mqtt_incomming_gw(topic_parts, message)
        elif topic_parts[0] == "ybo_req":
            yield self.mqtt_incomming_request(topic_parts, message)

    @inlineCallbacks
    def mqtt_incomming_request(self, topics, message):
        # ybo_req/src_gwid/dest_gwid

        body = message["body"]
        source_id = body["source_id"]
        component_type = body["component_type"]
        component_name = body["component_name"]
        payload = body["payload"]

        if component_type not in ("lib", "module"):
            logger.info("Gateway COMS received invalid component type: {component_type}", component_type=component_type)
            return False

        if component_type == "module":
            try:
                module = self._Modules[component_name]
            except Exception:
                logger.info("Received inter-gateway MQTT coms for module {module}, but module not found. Dropping.",
                            module=component_name)
                return False
            try:
                yield maybeDeferred(module._inter_gateway_mqtt_req_, topics, message)
            except Exception:
                logger.info("Received inter-gateway MQTT coms for module {module}, but module doesn't have function '_inter_gateway_mqtt_req_' Dropping.",
                            module=component_name)
                return False

        elif component_type == "lib":
            # return_topic = source_id + "/" + component_type + "/"+ component_name
            if component_name == "system_ping":
                self.publish_data(destination_id=source_id,
                                  component_type="lib", component_name="system_ping_response",
                                  payload=time(), reply_to=body["message_id"])
            elif component_name == "atoms":
                item_requested = payload
                self.send_atoms(destination_id=source_id, atom_id=item_requested)
            elif component_name == "device_commands":
                item_requested = payload
                self.send_device_commands(destination_id=source_id, device_command_id=item_requested)
            elif component_name == "device_status":
                item_requested = payload
                self.send_device_status(destination_id=source_id, device_id=item_requested)
            elif component_name == "states":
                item_requested = payload
                self.send_states(destination_id=source_id, state_id=item_requested)
            # elif component_name == "scenes":
            #     self.send_scenes(destination_id=source_id, scene_id=item_request_id)
        return True

    @inlineCallbacks
    def mqtt_incomming_gw(self, topics, message):
        # ybo_gw/src_gwid/dest_gwid

        body = message["body"]
        source_id = body["source_id"]
        component_type = body["component_type"]
        component_name = body["component_name"]
        payload = body["payload"]
        if component_type == "module":
            try:
                module = self._Modules[component_name]
            except Exception as e:
                logger.info("Received inter-gateway MQTT coms for module {module}, but module not found. Dropping.", module=component_name)
                return False
            try:
                yield maybeDeferred(module._inter_gateway_mqtt_, topics, message)
            except Exception as e:
                logger.info("Received inter-gateway MQTT coms for module {module}, but module doesn't have function '_inter_gateway_mqtt_' Dropping.", module=component_name)
                return False
        elif component_type == "lib":
            try:
                if component_name == "system_ping_response":
                    reply_to = body["reply_to"]
                    if reply_to is None:
                        raise YomboWarning("lib.system_ping requires a reply_id, but not found. Dropping.")
                    if source_id in self._Gateways.gateways and \
                            self._Gateways.gateways[source_id].ping_request_id == reply_to:
                        gateway = self._Gateways.gateways[source_id]
                        gateway.ping_roundtrip = round(
                            (body["payload"] - gateway.ping_request_at) * 100, 2)
                        gateway.ping_response_at = body["time_received"]
                        gateway.ping_time_offset = round(body["payload"] - body["time_received"], 2)
                elif component_name == "atoms_set":
                    for name, value in payload.items():
                        self._Atoms.set_from_gateway_communications(name, value, self)
                elif component_name == "device_command":
                    self.incoming_data_device_command(body)
                elif component_name == "device_command_status":
                    self.incoming_data_device_command_status(body)
                elif component_name == "device_status":
                    self.incoming_data_device_status(body)
                elif component_name == "notification":
                    self.incoming_data_notification(body)
                elif component_name == "states_set":
                    for name, value in payload.items():
                        self._States.set_from_gateway_communications(name, value, self)
                # elif component_name == "scenes":
                #     for name, value in message["payload"].items():
                #         self._Scenes.set_from_gateway_communications(name, value, self)
                elif component_name == "system_state":
                    if payload == "online":
                        self._Gateways.gateways[source_id].com_status = "online"
                        reactor.callLater(random_int(2, .8), self.send_all_info, destination_id=source_id)
                    if payload == "offline":
                        self._Gateways.gateways[source_id].com_status = "offline"
            except Exception as e:  # catch anything here...so can display details.
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.format_exc())
                logger.error("--------------------------------------------------------")
        return True

    def incoming_data_device_command(self, body):
        """
        Handles incoming device commands. Only the master node will store device command information for
        other gateways.

        :param body:
        :return:
        """
        payload = body["payload"]
        source_id = body["source_id"]

        def do_device_command(parent, device_command):
            device = parent._Devices.get(device_command["device_id"])
            if device.gateway_id != parent.gateway_id() and parent.is_master() is not True:  # if we are not a master, we don't care!
                # print("do_device_command..skipping due to not local gateway and not a master: %s" % parent.is_master())
                # print("dropping device command..  dest gw: %s" % device_command["gateway_id"])
                # print("dropping device command..  self.gateway_id: %s" % self.gateway_id)
                return False
            device_command["broadcast_at"] = None
            device_command["device"] = device
            device_command["source_gateway_id"] = source_id
            parent._Devices.add_device_command(device_command)

        if isinstance(payload["device_command"], list):
            for device_command in payload["device_command"]:
                do_device_command(device_command)
        else:
            do_device_command(self, payload["device_command"])
        return True

    def incoming_data_device_command_status(self, body):
        """
        Handles incoming device commands.

        :param body:
        :return:
        """
        payload = body["payload"]
        source_id = body["source_id"]

        for request_id, data in payload.items():
            if request_id not in self._Devices.device_commands:
                msg = {"request_id": request_id}
                # self.publish_data("req", source_id, "lib/device_commands", msg)
            else:
                self._Devices.update_device_command(
                    request_id,
                    data["status"],
                    data["message"],
                    data["log_time"],
                    source_id,
                )
        return True

    def incoming_data_notification(self, body):
        """
        Handles incoming device status.

        Todo: Complete this method.

        :param body:
        :return:
        """
        return True
        payload = message["payload"]
        payload["status_source"] = "gateway_coms"

    def incoming_data_device_status(self, body):
        """
        Handles incoming device status.

        :param body:
        :return:
        """
        payload = body["payload"]
        source_id = body["source_id"]

        for status in payload:
            device_id = status["device_id"]
            if device_id not in self._Devices:
                logger.info("MQTT Received device status for a device that doesn't exist, dropping: {device_id}",
                            device_id=device_id)
                continue
            device = self._Devices[device_id]
            status["source"] = "gateway_coms"
            device.set_status_internal(status)
        return True

    def encode_message(self, destination_id=None, component_type=None, component_name=None,
                       payload=None, reply_to=None):
        """
        Creates a basic dictionary to represent the message and then pickles it using JSON.

        :param payload: Dictionary to send.
        :param destination_id:
        :return:
        """
        if destination_id is None:
            destination_id = "all"

        message_id = random_string(length=20)
        body = {
            "payload": payload,
            "time_sent": time(),
            "source_id": self.gateway_id(),
            "destination_id": destination_id,
            "message_id": message_id,
            "component_type": component_type,
            "component_name": component_name,
            "reply_to": reply_to,
            "protocol_version": 2,
            }
        message_out = {
            "body": data_pickle(body, "msgpack_base85"),
        }
        message_out["hash"] = sha256_compact(message_out["body"])
        message = {
            "body": body,
            "hash": message_out["hash"],
        }
        return message_id, message, data_pickle(message_out, "msgpack_base85")

    def decode_message(self, topic, raw_message):
        """
        Decode a message from another gateway.

        :param payload: Dictionary to send.
        :param destination_id:
        :return:
        """
        # ybo_req/src_gwid/dest_gwid
        topic_parts = topic.split("/", 3)

        message = data_unpickle(raw_message, encoder="msgpack_base85")

        required_keys = ("body", "hash")
        if all(required in message for required in required_keys) is False:
            raise YomboWarning("MQTT Gateway is dropping message, missing a required message field.")

        message_hash = message["hash"]
        generated_hash = sha256_compact(message["body"])
        if message_hash != generated_hash:
            raise YomboWarning("Invalid incoming check hash.")

        message["body"] = data_unpickle(message["body"], encoder="msgpack_base85")
        message["body"]["time_received"] = time()
        required_keys = ("payload", "time_sent", "source_id", "destination_id", "message_id",
                         "component_type", "component_name", "reply_to", "protocol_version")
        if all(required in message["body"] for required in required_keys) is False:
            raise YomboWarning("MQTT Gateway is dropping message, missing a required body field.")

        body = message["body"]

        if body["source_id"] != topic_parts[1]:
            raise YomboWarning("Gateway source_id doesn't match topic source_id")
        if body["destination_id"] != topic_parts[2]:
            raise YomboWarning("Gateway destination_id doesn't match topic destination_id")

        return message

    def publish_data(self, destination_id=None,  component_type=None, component_name=None,
                     payload=None, reply_to=None, message_type=None):

        if destination_id is None:
            destination_id = "all"
        if component_type is None or component_name is None:
            raise YomboWarning("Must have 'component_type' and 'component_name' arguments.")
        if message_type is None:
            message_type = "gw"
        final_topic = f"ybo_{message_type}/{self.gateway_id()}/{destination_id}"
        message_id, message, message_out = self.encode_message(destination_id=destination_id,
                                                               component_type=component_type,
                                                               component_name=component_name,
                                                               payload=payload,
                                                               reply_to=reply_to
                                                               )

        self.log_outgoing.append({"sent": time(), "topic": final_topic, "message": message})
        self.mqtt.publish(final_topic, message_out)

        # logger.debug("gateways publish data: {topic} {message}", topic=final_topic, message=message)
        self._Gateways.gateways[self.gateway_id()].last_communications.append({
            "time": time(),
            "direction": "sent",
            "topic": f"{final_topic}/{component_type}/{component_name}",
        })
        if destination_id in self._Gateways.gateways:
            self._Gateways.gateways[destination_id].last_communications.append({
                "time": time(),
                "direction": "sent",
                "topic": f"{final_topic}/{component_type}/{component_name}",
            })

        return message_id

    def send_all_info(self, destination_id=None, set_ok_to_publish_updates=None):
        """
        Called when this gateway starts up and when another gateway comes online.

        :param gateways: Reference to the gateway library
        :param destination_id:
        :param set_ok_to_publish_updates:
        :return:
        """
        self.send_atoms(destination_id)
        self.send_device_status(destination_id)
        self.send_states(destination_id)
        # self.send_scenes(destination_id)

        if set_ok_to_publish_updates is True:
            self.ok_to_publish_updates = True

    def send_atoms(self, destination_id=None, atom_id=None):
        return_gw = self.get_return_destination(destination_id)
        if atom_id is None or atom_id == "#":
            self.publish_data(destination_id=destination_id,
                              component_type="lib", component_name="atoms_set",
                              payload=self._Atoms.get("#", full=True))
        else:
            self.publish_data(destination_id=destination_id,
                              component_type="lib", component_name="atoms_set",
                              payload={atom_id: self._Atoms.get(atom_id, full=True)})

    def send_device_commands(self, destination_id=None, device_command_id=None):
        return_gw = self.get_return_destination(destination_id)
        if return_gw == "all" and device_command_id is None:
            logger.debug("device commands request must have device_command_id or return gateway id.")
            return
        if device_command_id is None:
            found_device_commands = self._Devices.get_gateway_device_commands(self.gateway_id())
        elif device_command_id in self._Devices.device_commands:
            if self._Devices.device_commands[device_command_id].gateway_id == self.gateway_id():
                found_device_commands = {device_command_id: self._Devices.device_commands[device_command_id].asdict()}
        self.publish_data(destination_id=destination_id,
                          component_type="lib", component_name="device_command",
                          payload=found_device_commands)

    def send_device_status(self, destination_id=None, device_id=None):
        gateway_id = self.gateway_id()
        return_gw = self.get_return_destination(destination_id)
        message = []
        if device_id is None:
            for device_id, device in self._Devices.devices.items():
                if device.gateway_id == gateway_id or device.status != 1:
                    continue
                message.append(device.status_all.asdict())
        else:
            if device_id in self._Devices:
                device = self._Devices[device_id]
                if device.gateway_id == gateway_id or device.status != 1:
                    return
                message.append(device.status_all.asdict())
        if len(message) > 0:
            self.publish_data(destination_id=destination_id,
                              component_type="lib", component_name="device_status",
                              payload=message)

    def send_states(self, destination_id=None, state_id=None):
        return_gw = self.get_return_destination(destination_id)
        if state_id is None or state_id == "#":
            self.publish_data(destination_id=destination_id,
                              component_type="lib", component_name="states_set",
                              payload=self._States.get("#", full=True))
        else:
            self.publish_data(destination_id=destination_id,
                              component_type="lib", component_name="states_set",
                              payload={state_id: self._States.get(state_id, full=True)})

    # def send_scenes(self, destination_id=None, scene_id=None):
    #     return_gw = self.get_return_destination(destination_id)
    #     if scene_id is None or scene_id == "#":
    #         self.publish_data("gw", return_gw, "lib/scenes", self._Scenes.get())
    #     else:
    #         self.publish_data("gw", return_gw, "lib/scenes",
    #                           {scene_id: self._Scenes.get(scene_id, full=True)})

    def get_return_destination(self, destination_id=None):
        if destination_id is None or destination_id is "":
            return "all"
        return destination_id

    def test(self):
        self.mqtt_test_connection = self.new(self.server_listen_ip,
            self.server_listen_port, "yombo", self.default_client_mqtt_password1, False,
            self.test_mqtt_in, self.test_on_connect )

        self.mqtt_test_connection.subscribe("yombo/#")

        self.sendDataLoop = LoopingCall(self.test_send_data)
        self.sendDataLoop.start(5, True)

    def test_on_connect(self):
        print("in on connect in library...")
        self.test_send_data()

    def test_send_data(self):
        print("mqtt sending test package")
        self.mqtt_test_connection.publish("yombo/devices/asdf/asdf", "open")

    def test_mqtt_in(self, topic, payload, qos, retain):
        print(f"i got this: {topic} / {payload}")
