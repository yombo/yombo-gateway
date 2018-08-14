# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Gateways @ Module Development <https://yombo.net/docs/libraries/gateways>`_

Handles inter-gateway communications and provides information about other gateways within the cluster.
Any gateway within an account can communicate with another gateway using any master gateway's mqtt broker service.

Slave gateways will connect to it's master's mqtt broker. All slave gateways will report device status, states, and
atoms to the master. Scenes and automation rules can fire on any gateway, however, if status is required from
a remote gateway, that automation rule should only fire on the master server.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.14.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/gateways.html>`_
"""
from time import time
import traceback
from collections import deque

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import bytes_to_unicode, random_int, data_pickle, data_unpickle, random_string

logger = get_logger('library.gateways.mqtt')


class Gateway_Coms(object):
    def __init__(self, parent):
        self._Parent = parent  # reference to the gateway library
        self.gateway_id = self._Parent.gateway_id
        self.log_incoming = deque([], 200)
        self.log_outgoing = deque([], 200)

    @inlineCallbacks
    def mqtt_incoming(self, topic, raw_message, qos, retain):
        # ybo_gw_req/src_gwid/dest_gwid|all/lib/devices/get - payload is blank - get all device information
        try:
            message = data_unpickle(raw_message, 'json')
            message['time_received'] = time()
        except Exception:
            return
        topic_parts = topic.split('/', 10)

        if topic_parts[0] == "to_yombo":
            return self.mqtt_incoming_to_yombo(topic_parts, message)

        # required_keys = ('payload', 'time_sent', 'source_id', 'destination_id', 'message_id')
        # if all(required in message for required in required_keys) is False:
        #     logger.info("MQTT Gateway is dropping message, missing a required field.")
        #     return

        if len(topic_parts) < 5:
            logger.debug("Gateway COMS received too short of a topic (discarding): {topic}", topic=topic)
            return
        if topic_parts[1] == self.gateway_id():
            logger.debug("discarding message that I sent.")
            return
        if topic_parts[2] not in (self.gateway_id(), 'all', 'cluster'):
            logger.debug("MQTT message doesn't list us as a target, dropping")
            return

        logger.debug("got mqtt in: {topic} - {message}", topic=topic, message=message)

        if topic_parts[1] in self._Parent.gateways:
            self._Parent.gateways[topic_parts[1]].last_scene = time()
            self._Parent.gateways[topic_parts[1]].last_communications.append({
                'time': time(),
                'direction': 'received',
                'topic': topic,
            })

        self.log_incoming.append({'received': time(), 'topic': topic, 'message': message})

        if len(message) == 0 or message is None:
            logger.warn("Empty payloads for inter gateway coms are not allowed!")
            return

        if topic_parts[0] == "ybo_gw":
            yield self.mqtt_incomming_data(topic_parts, message)
        elif topic_parts[0] == "ybo_req":
            yield self.mqtt_incomming_request(topic_parts, message)

    def mqtt_incoming_to_yombo(self, topics, message):
        if topics[1] == "device_command":
            device_search = topics[2]
            command_search = topics[3]
            if len(device_search) > 200 or isinstance(device_search, str) is False:
                logger.debug("Dropping MQTT device command request, device_id is too long or invalid.")
                return False
            if device_search in self._Parent._Devices:
                device = self._Parent._Devices[device_search]
                if device.gateway_id != self.gateway_id():
                    logger.debug("Dropping MQTT device command request, i'm not the controlling gateway.: {device}",
                                 device=device_search)
            else:
                logger.debug("Dropping MQTT device command request, device_id is not found: {device}",
                             device=device_search)
                return False

            if len(command_search) > 200 or isinstance(command_search, str) is False:
                logger.debug("Dropping MQTT device command request, command_id is too long or invalid.")
                return False
            if command_search in self._Parent._Commands:
                command = self._Parent._Commands[command_search]
            else:
                logger.debug("Dropping MQTT device command request, command_id is not found: {command}",
                             command=command_search)
                return False

            pin_code = message.get('pin_code', None)
            delay = message.get('delay', None)
            max_delay = message.get('max_delay', None)
            not_before = message.get('not_before', None)
            not_after = message.get('not_after', None)
            inputs = message.get('inputs', None)
            idempotence = message.get('idempotence', None)
            try:
                device.command(
                    cmd=command,
                    user_id='TO_BE_IMPLETMENTED:MQTT',
                    user_type='TO_BE_IMPLETMENTED:MQTT',
                    pin=pin_code,
                    delay=delay,
                    max_delay=max_delay,
                    not_before=not_before,
                    not_after=not_after,
                    inputs=inputs,
                    idempotence=idempotence,
                )
            except KeyError as e:
                return False
            except YomboWarning as e:
                return False
            return True

    @inlineCallbacks
    def mqtt_incomming_request(self, topics, message):
        # ybo_req/src_gwid/dest_gwid|all/lib/devices/get - 'request_id' can be in the payload section of the message.
        # ybo_req/src_gwid/dest_gwid|all/lib/devices/update/device_id - payload is full device, including meta and state
        # ybo_req/src_gwid/dest_gwid|all/lib/states/get - payload is blank
        # ybo_req/src_gwid/dest_gwid|all/lib/states/get/section/option - payload is blank
        # ybo_req/src_gwid/dest_gwid|all/lib/states/update/section/option - payload is all details
        # ybo_req/src_gwid/dest_gwid|all/lib/atoms/get/name - payload is blank
        # ybo_req/src_gwid/dest_gwid|all/lib/atoms/update/name - payload is all details
        source_id = topics[1]
        dest_id = topics[2]
        component_type = topics[3]
        component_name = topics[4]
        if len(topics) == 6:
            opt1 = topics[5]
        else:
            opt1 = None
        if len(topics) == 7:
            opt2 = topics[6]
        else:
            opt2 = None

        if component_type not in ('lib', 'module', 'system'):
            logger.info("Gateway COMS received invalid component type: {component_type}", component_type=component_type)
            return False

        if component_type == 'module':
            try:
                module = self._Parent._Modules[component_name]
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

        elif component_type == 'lib':
            # return_topic = source_id + "/" + component_type + "/"+ component_name
            if opt1 == 'get':
                if 'item_request_id' in message['payload']:
                    item_request_id = message['item_request_id']
                else:
                    item_request_id = None

                if component_name == 'atoms':
                    self.send_atoms(destination_id=source_id, atom_id=item_request_id)
                elif component_name == 'device_status':
                    self.send_device_status(destination_id=source_id, device_id=item_request_id)
                elif component_name == 'device_commands':
                    self.send_device_commands(destination_id=source_id, device_command_id=item_request_id)
                elif component_name == 'states':
                    self.send_states(destination_id=source_id, state_id=item_request_id)

        elif component_type == 'system':
            if component_name == 'ping':
                message = {'response_id': message['message_id'], 'gateway_id': self.gateway_id(), 'time': time()}
                self.publish_data('gw', source_id, 'system/ping', message)

        return True

    @inlineCallbacks
    def mqtt_incomming_data(self, topics, message):
        current_time = time()
        # ybo_gw/src_gwid/dest_gwid|all/lib/atoms
        source_mqtt_id = topics[1]
        # dest_id = topics[2]
        component_type = topics[3]
        component_name = topics[4]
        if len(topics) == 6:
            opt1 = topics[5]
        else:
            opt1 = None
        if len(topics) == 7:
            opt2 = topics[6]
        else:
            opt2 = None

        if component_type == 'module':
            try:
                module = self._Parent._Modules[component_name]
            except Exception as e:
                logger.info("Received inter-gateway MQTT coms for module {module}, but module not found. Dropping.", module=component_name)
                return False
            try:
                yield maybeDeferred(module._inter_gateway_mqtt_, topics, message)
            except Exception as e:
                logger.info("Received inter-gateway MQTT coms for module {module}, but module doesn't have function '_inter_gateway_mqtt_' Dropping.", module=component_name)
                return False
        elif component_type == 'lib':
            try:
                if component_name == 'atoms':
                    for name, value in message['payload'].items():
                        self._Parent._Atoms.set_from_gateway_communications(name, value)
                elif component_name == 'device_command':
                    self.incoming_data_device_command(source_mqtt_id, message)
                elif component_name == 'device_command_status':
                    self.incoming_data_device_command_status(source_mqtt_id, message)
                elif component_name == 'device_status':
                    self.incoming_data_device_status(source_mqtt_id, message)
                elif component_name == 'notification':
                    self.incoming_data_notification(source_mqtt_id, message)
                elif component_name == 'states':
                    for name, value in message['payload'].items():
                        self._Parent._States.set_from_gateway_communications(name, value)
                elif component_name == 'gateway':
                    if opt1 == 'online':
                        self._Parent.gateways[source_mqtt_id].com_status = 'online'
                        reactor.callLater(random_int(2, .8), self.send_all_info, destination_id=source_mqtt_id)
                    elif opt1 == 'offline':
                        self._Parent.gateways[source_mqtt_id].com_status = 'offline'
            except Exception as e:  # catch anything here...so can display details.
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.format_exc())
                logger.error("--------------------------------------------------------")
        elif component_type == 'system':
            if component_name == 'ping':
                if 'gateway_id' in message['payload']:
                    gateway_id = message['payload']['gateway_id']
                    response_id = message['payload']['response_id']
                    gateway =self._Parent.gateways[gateway_id]
                    if gateway_id in self._Parent.gateways and gateway.ping_request_id == response_id:
                        gateway.ping_roundtrip = round((message['time_received'] - gateway.ping_request_at) * 100)
                        gateway.ping_response_at = message['time_received']
                        gateway.ping_time_offset = message['time_received'] - message['payload']['time']
        return True

    def incoming_data_device_command(self, source_mqtt_id, message):
        """
        Handles incoming device commands. Only the master node will store device command information for
        other gateways.

        :param message:
        :return:
        """
        # print("got device_commands")
        payload = message['payload']

        def do_device_command(parent, device_command):
            device = parent._Parent._Devices.get(device_command['device_id'])
            print("do_device_command")
            if device.gateway_id != parent.gateway_id() and parent._Parent.is_master() is not True:  # if we are not a master, we don't care!
                print("do_device_command..skipping due to not local gateway and not a master: %s" % parent._Parent.is_master())
                # print("dropping device command..  dest gw: %s" % device_command['gateway_id'])
                # print("dropping device command..  self.gateway_id: %s" % self.gateway_id)
                return False
            device_command['broadcast_at'] = None
            device_command['device'] = device
            device_command['source_gateway_id'] = source_mqtt_id
            parent._Parent._Devices.add_device_command(device_command)

        if isinstance(payload['device_command'], list):
            for device_command in payload['device_command']:
                do_device_command(device_command)
        else:
            do_device_command(self, payload['device_command'])
        return True

    def incoming_data_device_command_status(self, source_mqtt_id, message):
        """
        Handles incoming device commands.

        :param message:
        :return:
        """
        payload = message['payload']

        for request_id, data in payload.items():
            if request_id not in self._Parent._Devices.device_commands:
                msg = {'request_id': request_id}
                self.publish_data('req', source_mqtt_id, 'lib/device_commands', msg)
            else:
                self._Parent._Devices.update_device_command(
                    request_id,
                    data['status'],
                    data['message'],
                    data['log_time'],
                    source_mqtt_id,
                )
        return True

    def incoming_data_notification(self, source_mqtt_id, message):
        """
        Handles incoming device status.

        Todo: Complete this method.

        :param message:
        :return:
        """
        return True
        payload = message['payload']
        payload['status_source'] = 'gateway_coms'

    def incoming_data_device_status(self, source_mqtt_id, message):
        """
        Handles incoming device status.

        :param message:
        :return:
        """
        for device_id, status in message['payload'].items():
            if device_id not in self._Parent._Devices:
                logger.info("MQTT Received device status for a device that doesn't exist, dropping: {device_id}",
                            device_id=device_id)
                continue
            device = self._Parent._Devices[device_id]
            status['source'] = 'gateway_coms'
            device.set_status_internal(status)
        return True

    def encode_message(self, payload, destination_id=None):
        """
        Creates a basic dictionary to represent the message and then pickles it using JSON.

        :param payload: Dictionary to send.
        :param destination_id:
        :return:
        """
        if destination_id is None:
            destination_id = 'all'
        message_id = random_string(length=20)
        message = {
            'payload': payload,
            'time_sent': time(),
            'source_type': 'gateway',
            'source_id': self.gateway_id(),
            'destination_id': destination_id,
            'message_id': message_id
        }
        return message_id, message, data_pickle(message, 'json')

    def publish_data(self, msg_type, destination_id, topic, dict_message):
        final_topic = 'ybo_%s/%s/%s/%s' % (msg_type, self.gateway_id(), destination_id, topic)
        message_id, message, outgoing_data = self.encode_message(dict_message)
        self.log_outgoing.append({'sent': time(), 'topic': topic, 'message': message})
        self._Parent.mqtt.publish(final_topic, outgoing_data)

        logger.debug("gateways publish data: {topic} {data}", topic=final_topic, data=outgoing_data)
        self._Parent.gateways[self.gateway_id()].last_communications.append({
            'time': time(),
            'direction': 'sent',
            'topic': final_topic,
        })
        if destination_id in self._Parent.gateways:
            self._Parent.gateways[destination_id].last_communications.append({
                'time': time(),
                'direction': 'sent',
                'topic': final_topic,
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
        if set_ok_to_publish_updates is True:
            self._Parent.ok_to_publish_updates = True

    def send_atoms(self, destination_id=None, atom_id=None):
        return_gw = self.get_return_destination(destination_id)
        if atom_id is None or atom_id == '#':
            self.publish_data('gw', return_gw, 'lib/atoms', self._Parent._Atoms.get('#', full=True))
        else:
            atom = {atom_id: self._Parent._Atoms.get(atom_id, full=True)}
            self.publish_data('gw', return_gw, 'lib/atoms', atom)

    def send_device_commands(self, destination_id=None, device_command_id=None):
        return_gw = self.get_return_destination(destination_id)
        if return_gw == 'all' and device_command_id is None:
            logger.debug("device commands request must have device_command_id or return gateway id.")
            return
        if device_command_id is None:
            found_device_commands = self._Parent._Devices.get_gateway_device_commands(self.gateway_id())
        elif device_command_id in self._Parent._Devices.device_commands:
            if self._Parent._Devices.device_commands[device_command_id].gateway_id == self.gateway_id():
                found_device_commands = {device_command_id: self._Parent._Devices.device_commands[device_command_id].asdict()}
        self.publish_data('gw', return_gw, "lib/device_commands", found_device_commands)

    def send_device_status(self, destination_id=None, device_id=None):
        gateway_id = self.gateway_id()
        return_gw = self.get_return_destination(destination_id)
        message = {}
        if device_id is None:
            for device_id, device in self._Parent._Devices.devices.items():
                if device.gateway_id == gateway_id or device.status != 1:
                    continue
                message[device_id] = device.status_all.asdict()
        else:
            if device_id in self._Parent._Devices:
                device = self._Parent._Devices[device_id]
                if device.gateway_id == gateway_id or device.status != 1:
                    return
                message[device_id] = device.status_all.asdict()
        self.publish_data('gw', return_gw, 'lib/device_status', message)

    def send_states(self, destination_id=None, state_id=None):
        return_gw = self.get_return_destination(destination_id)
        if state_id is None or state_id == '#':
            self.publish_data('gw', return_gw, 'lib/states', self._Parent._States.get('#', full=True))
        else:
            state = {state_id: self._Parent._Atoms.get(state_id, full=True)}
            self.publish_data('gw', return_gw, 'lib/states', state)

    def get_return_destination(self, destination_id=None):
        if destination_id is None or destination_id is '':
            return 'all'
        return destination_id
