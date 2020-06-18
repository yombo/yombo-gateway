# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. warning::

   This library is not intended to be accessed by module developers or end users. These functions, variables,
   and classes were not intended to be accessed directly by modules. These are documented here for completeness.

.. note::

  * For library documentation, see: `MQTTYombo @ Library Documentation <https://yombo.net/docs/libraries/mqttyombo>`_

Responsible for parsing the top level MQTT topic: yombo_gw

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/mqttyombo/incoming_yombo_gw.html>`_
"""

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred, ensureDeferred

# Import Yombo libraries
from yombo.core.log import get_logger

logger = get_logger("library.mqttyombo.incoming_yombo_gw")


class IncomingGwMixin:

    @inlineCallbacks
    def incoming_yombo_gw_base(self, topic, body, qos, properties):
        """
        Called on any incoming 'yombo_gw/#' messages.

                                  (req)     (req)   (req)   (optional)
        Example topic: yombo_gw/source_gw/dest_gw/platform/id/someid
        :return:
        """
        # logger.debug("mqttyombo, incoming_parse: topic={topic}", topic=topic)
        # logger.debug("mqttyombo, incoming_parse: body={body}", body=body)
        # logger.debug("mqttyombo, incoming_parse: properties={properties}", properties=properties)

        topic_parts = topic.split("/")

        if len(topic_parts) < 3:
            logger.debug("Dropping mqttyombo payload - invalid topic")
            return

        topic_source = topic_parts[1]
        topic_destination = topic_parts[2]

        if topic_source == self._gateway_id:
            logger.debug("Dropping mqttyombo payload - source is us.")
            return

        if topic_source not in self._Gateways.gateways:
            logger.debug("Dropping mqttyombo payload - source gateway is unknown.")
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

        platform_handler = f"incoming_{topic_parts[2]}"
        if hasattr(self, platform_handler) is False:
            return
        yield maybeDeferred(getattr(self, platform_handler), topic=topic, payload=payload, headers=headers,
                            properties=properties)

    # @inlineCallbacks
    def incoming_yombo_base(self, topic, body, qos, properties):
        pass

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
