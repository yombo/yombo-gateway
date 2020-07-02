"""

.. warning::

   This library is not intended to be accessed by module developers or end users. These functions, variables,
   and classes were not intended to be accessed directly by modules. These are documented here for completeness.

.. note::

  * For library documentation, see: `MQTTYombo @ Library Documentation <https://yombo.net/docs/libraries/mqttyombo>`_

Handles all activities relating to sending MQTT messages.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/mqttyombo/publishing.html>`_
"""
from copy import deepcopy
from collections import deque
import socket
from time import time
import traceback
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.constants.mqttyombo import MQTT_PROTOCOL_VERSION
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import random_string
from yombo.utils.dictionaries import dict_len

logger = get_logger("library.gateway_communications")


class PublishingMixin:

    def send_all_info(self, destination_id=None, set_ok_to_publish_updates=None):
        """
        Called when this gateway starts up and when another gateway comes online.

        :param gateways: Reference to the gateway library
        :param destination_id:
        :param set_ok_to_publish_updates:
        :return:
        """
        self.send_atoms(destination_id)
        self.send_states(destination_id)
        # self.send_device_states(destination_id)
        # self.send_scenes(destination_id)

        if set_ok_to_publish_updates is True:
            self.ok_to_publish_updates = True

    def generate_response(self, topic, payload, destination=None, correlation_id=None, publish: Optional[bool] = None):
        """
        Generate a response message from a previous message. Uses publish to do the heavy lifting.

        :param topic:
        :param payload:
        :param destination:
        :return:
        """
        if correlation_id is None:
            raise YomboWarning("generate_response required correlation_id.")
        return self.publish_yombo_gw(topic, payload, message_type="response", destination=destination,
                                     headers={"reply_correlation_id": correlation_id}, publish=publish)

    def send_items(self, outgoing, topic, destination=None, target_topics=None, headers=None,
                   reply_correlation_id=None):
        """
        Helper function to send bulk data to endpoints.

        :param destination:
        :param topic: Topic to send, AKA platform.
        :param target_topics:
        :return:
        """
        if target_topics is None:
            target_topics = ["yombo_gw", "yombo"]

        if isinstance(target_topics, str):
            target_topics = [target_topics]

        if isinstance(reply_correlation_id, str):
            if headers is None:
                headers = {"reply_correlation_id": reply_correlation_id}
            else:
                headers["reply_correlation_id"] = reply_correlation_id

        if isinstance(outgoing, dict):
            results = {}
            if "yombo_gw" in target_topics:
                for key, value in outgoing.items():
                    results[value._Parent._storage_primary_field_name] = value.to_database()
                self.publish_yombo_gw(topic, results, destination=destination, headers=headers)
            if "yombo" in target_topics:
                results = {}
                for key, value in outgoing.items():
                    results[value._Parent._storage_primary_field_name] = value.to_external()
                self.publish_yombo(topic, results, headers=headers)
        else:
            if "yombo_gw" in target_topics:
                self.publish_yombo_gw(
                    topic,
                    outgoing.to_database(),
                    destination=destination,
                    headers=headers
                )
            if "yombo" in target_topics:
                self.publish_yombo(
                    topic,
                    outgoing.to_external(),
                    headers=headers
                )

    def publish_yombo(self, topic: str, payload: Optional[Any] = None,
                      headers: Optional[dict] = None,
                      jsonapi: Optional[bool] = None,
                      topic_prefix: Optional[str] = None) -> Union[None, dict]:
        """
        Publishes to yombo/# topics, meant for IoT things to receive data streams. This uses JSON to encode
        a more basic payload as compared to publish_yombo_gw. This also includes the Frontend application.

        :param topic: Topic name to append to the standard topic.
        :param payload: Dictionary to send.
        :param headers: Any headers to add. This is added to the 'user_property' portion of the MQTT message.
        :param jsonapi: If true, sets user_property jsonapi to "1".
        :param topic_prefix: Change the default 'yombo' topic prefix.

        :return: If publish is True, returns None. Else, returns the dictionary to send to publish_message().
        """
        if topic_prefix is None:
            topic_prefix = "yombo"
        encoded_body = payload
        if isinstance(payload, dict) or isinstance(payload, list):
            encoded_body = self._Tools.data_pickle(payload, "json")
            content_type = "json"
        elif payload is None:
            encoded_body = ""
            content_type = "none"
        else:
            encoded_body = payload
            content_type = payload.__class__.__name__
        message = {
            "topic": f"{topic_prefix}/{topic}",
            "body": encoded_body,
            "kwargs": {
                "content_type": content_type,
                "message_expiry_interval": 5,
                "qos": 1,
                "user_property": [
                    ("created_at", str(round(time(), 3))),
                    ("protocol_version", MQTT_PROTOCOL_VERSION),
                    ("source", self._gateway_id),
                    ("sig", self._Hash.sha256_compact(encoded_body)),  # TODO: convert to HMAC or something.
                ],
            },
        }
        if jsonapi is True:
            message["kwargs"]["user_property"].append(("jsonapi", "1"))
        if isinstance(headers, dict) and len(headers) > 0:
            for key, value in headers.items():
                message["kwargs"]["user_property"].append((key, value))
        self.publish_message(message)
        return message

    def publish_yombo_gw(self, topic: str, payload: Optional[Any] = None, message_type: Optional[str] = None,
                         destination: Optional[str] = None, headers: Optional[dict] = None,
                         publish: Optional[bool] = None) -> Union[None, dict]:
        """
        Used to send to other gateways. The difference between this and publish_yombo is this encodes in msgpack and
        zips it if the payload is large.

        :param topic: Topic name to append to the standard topic.
        :param payload: Dictionary to send.
        :param message_type: Either: request, broadcast, or response. Defaults to broadcast.
        :param destination: The ID to send the message to.
        :param publish: If True, publish the message. Default: True.
        :param headers: Add any headers to the headers portion within the payload portion of the MQTT message.
        :return: If publish is True, returns None. Else, returns the dictionary to send to publish_message().
        """
        if publish is None:
            publish = True

        if message_type is None:
            message_type = "broadcast"
        if destination is None:
            destination = "cluster"

        message_id = random_string(length=20)
        body = {
            "payload": payload,
            "headers": {
                "correlation_id": message_id,
                "destination": destination,
                "source": self._gateway_id,
                "message_type": message_type,
                "created_at": round(time(), 3),
            }
        }
        if isinstance(headers, dict) and len(headers) > 0:
            body["headers"].update(headers)

        if payload is not None:
            if dict_len(body) < 1000:
                content_type = "msgpack"
            else:
                content_type = "msgpack_zip"
            encoded_body = self._Tools.data_pickle(body, content_type)
        else:
            content_type = "none"
            encoded_body = ""

        message = {
            "topic": f"yombo_gw/{self._gateway_id}/{destination}/{topic}",
            "body": encoded_body,
            "kwargs": {
                "content_type": content_type,
                "message_expiry_interval": 5,
                "qos": 1,
                "user_property": [
                    ("protocol_version", MQTT_PROTOCOL_VERSION),
                    ("content_type", content_type),
                    ("sig", self._Hash.sha256_compact(encoded_body)),  # TODO: convert to HMAC or something.
                ],
            }
        }
        if publish is True:
            self.publish_message(message)
            return
        return message

    def publish_message(self, message):
        """
        Publishes a message created by `publish_*()`.

        :param message:
        :return:
        """
        self.log_outgoing.append({"sent": time(), "topic": message["topic"], "message": message["body"]})
        # print(f"mqtt sending message: {message}")
        # print("topic:")
        # print(message["topic"])
        # print("body:")
        # print(message["body"])
        # print("kwargs:")
        # print(message["kwargs"])
        self.mqtt.publish(message["topic"], payload=message["body"], **message["kwargs"])

        self._Gateways.gateways[self._gateway_id].last_communications.append({
            "time": time(),
            "direction": "sent",
            "topic": f"{message['topic']}",
            })




    # @inlineCallbacks
    # def mqtt_incoming(self, topic, raw_message, qos, retain):
    #     """
    #     All incoming items for these topics are delivered here:
    #     yombo_gw/+/["all", "cluster", or local gateway] - Broadcasts to al, or gw to gw coms
    #     ybo_req/+/["all", "cluster", or local gateway] - Other gateways requesting info
    #
    #     All incoming
    #     :param topic:
    #     :param raw_message:
    #     :param qos:
    #     :param retain:
    #     :return:
    #     """
    #     # ybo_req/src_gwid/dest_gwid
    #     topic_parts = topic.split("/", 10)
    #     if topic_parts[0] not in ("ybo_req", "yombo_gw"):  # this shouldn"t ever happen.
    #         logger.info("Received a message, but it's has the wrong topic type.")
    #         return
    #
    #     try:
    #         message = self.decode_message(topic, raw_message)
    #     except YomboWarning as e:
    #         logger.info("Could not decode inter-gateway coms message: {e}", e=e)
    #         return
    #
    #     gateway_id = self._gateway_id
    #     body = message["body"]
    #     if body["source_id"] == gateway_id:
    #         logger.debug("discarding message that I sent: %s." % body["source_id"])
    #         return
    #     if body["destination_id"] not in (gateway_id, "all", "cluster"):
    #         logger.info("MQTT message doesn't list us as a target, dropping")
    #         return
    #
    #     # logger.debug("got mqtt in: {topic} - {message}", topic=topic, message=message)
    #
    #     if body["source_id"] in self._Gateways.gateways:
    #         self._Gateways.gateways[body["source_id"]].last_seen = time()
    #         self._Gateways.gateways[body["source_id"]].last_communications.append({
    #             "time": body["time_received"],
    #             "direction": "received",
    #             "topic": f"{topic}/{body['component_type']}/{body['component_name']}",
    #         })
    #     else:
    #         raise YomboWarning("Received an mqtt gw-coms message from an unknown gateway. Dropping.")
    #
    #     self.log_incoming.append({"received": time(), "topic": topic, "message": message})
    #     if topic_parts[0] == "yombo_gw":
    #         yield self.mqtt_incoming_gw(topic_parts, message)
    #     elif topic_parts[0] == "ybo_req":
    #         yield self.mqtt_incoming_request(topic_parts, message)
    #
    # @inlineCallbacks
    # def mqtt_incoming_request(self, topics, message):
    #     # ybo_req/src_gwid/dest_gwid
    #
    #     body = message["body"]
    #     source_id = body["source_id"]
    #     component_type = body["component_type"]
    #     component_name = body["component_name"]
    #     payload = body["payload"]
    #
    #     if component_type not in ("lib", "module"):
    #         logger.info("Gateway COMS received invalid component type: {component_type}", component_type=component_type)
    #         return False
    #
    #     if component_type == "module":
    #         try:
    #             module = self._Modules[component_name]
    #         except Exception:
    #             logger.info("Received inter-gateway MQTT coms for module {module}, but module not found. Dropping.",
    #                         module=component_name)
    #             return False
    #         try:
    #             yield maybeDeferred(module._inter_gateway_mqtt_req_, topics, message)
    #         except Exception:
    #             logger.info("Received inter-gateway MQTT coms for module {module}, but module doesn't have function '_inter_gateway_mqtt_req_' Dropping.",
    #                         module=component_name)
    #             return False
    #
    #     elif component_type == "lib":
    #         # return_topic = source_id + "/" + component_type + "/"+ component_name
    #         if component_name == "system_ping":
    #             self.publish_data(destination_id=source_id,
    #                               component_type="lib", component_name="system_ping_response",
    #                               payload=time(), reply_to=body["message_id"])
    #         elif component_name == "atoms":
    #             item_requested = payload
    #             self.send_atoms(destination_id=source_id, atom_id=item_requested)
    #         elif component_name == "device_commands":
    #             item_requested = payload
    #             self.send_device_commands(destination_id=source_id, device_command_id=item_requested)
    #         elif component_name == "device_states":
    #             item_requested = payload
    #             self.send_device_states(destination_id=source_id, device_id=item_requested)
    #         elif component_name == "states":
    #             item_requested = payload
    #             self.send_states(destination_id=source_id, state_id=item_requested)
    #         # elif component_name == "scenes":
    #         #     self.send_scenes(destination_id=source_id, scene_id=item_request_id)
    #     return True
    #
    # @inlineCallbacks
    # def mqtt_incoming_gw(self, topics, message):
    #     # yombo_gw/src_gwid/dest_gwid
    #
    #     body = message["body"]
    #     source_id = body["source_id"]
    #     component_type = body["component_type"]
    #     component_name = body["component_name"]
    #     payload = body["payload"]
    #     if component_type == "module":
    #         try:
    #             module = self._Modules[component_name]
    #         except Exception as e:
    #             logger.info("Received inter-gateway MQTT coms for module {module}, but module not found. Dropping.", module=component_name)
    #             return False
    #         try:
    #             yield maybeDeferred(module._inter_gateway_mqtt_, topics, message)
    #         except Exception as e:
    #             logger.info("Received inter-gateway MQTT coms for module {module}, but module doesn't have function '_inter_gateway_mqtt_' Dropping.", module=component_name)
    #             return False
    #     elif component_type == "lib":
    #         try:
    #             if component_name == "system_ping_response":
    #                 reply_to = body["reply_to"]
    #                 if reply_to is None:
    #                     raise YomboWarning("lib.system_ping requires a reply_id, but not found. Dropping.")
    #                 if source_id in self._Gateways.gateways and \
    #                         self._Gateways.gateways[source_id].ping_request_id == reply_to:
    #                     gateway = self._Gateways.gateways[source_id]
    #                     gateway.ping_roundtrip = round(
    #                         (body["payload"] - gateway.ping_request_at) * 100, 2)
    #                     gateway.ping_response_at = body["time_received"]
    #                     gateway.ping_time_offset = round(body["payload"] - body["time_received"], 2)
    #             elif component_name == "atoms_set":
    #                 for name, value in payload.items():
    #                     self._Atoms.set_from_gateway_communications(name, value, self)
    #             elif component_name == "device_command":
    #                 yield self.incoming_data_device_command(body)
    #             elif component_name == "device_command_status":
    #                 self.incoming_data_device_command_status(body)
    #             elif component_name == "device_states":
    #                 self.incoming_data_device_states(body)
    #             elif component_name == "notification":
    #                 self.incoming_data_notification(body)
    #             elif component_name == "states_set":
    #                 for name, value in payload.items():
    #                     self._States.set_from_gateway_communications(name, value, self)
    #             # elif component_name == "scenes":
    #             #     for name, value in message["payload"].items():
    #             #         self._Scenes.set_from_gateway_communications(name, value, self)
    #             elif component_name == "system_state":
    #                 if payload == "online":
    #                     self._Gateways.gateways[source_id].com_status = "online"
    #                     reactor.callLater(random_int(2, .8), self.send_all_info, destination_id=source_id)
    #                 if payload == "offline":
    #                     self._Gateways.gateways[source_id].com_status = "offline"
    #         except Exception as e:  # catch anything here...so can display details.
    #             logger.error("---------------==(Traceback)==--------------------------")
    #             logger.error("{trace}", trace=traceback.format_exc())
    #             logger.error("--------------------------------------------------------")
    #     return True
