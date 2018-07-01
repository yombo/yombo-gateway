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

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import bytes_to_unicode, random_int, data_pickle, data_unpickle, random_string

logger = get_logger('library.gateways.mqtt')


@inlineCallbacks
def mqtt_incoming(gateways, topic, raw_payload, qos, retain):
    # ybo_gw_req/src_gwid/dest_gwid|all/lib/devices/get - payload is blank - get all device information
    topic_parts = topic.split('/', 10)

    try:
        message = decode_message(raw_payload)
    except Exception:
        return

    if topic_parts[0] == "to_yombo":
        return mqtt_incoming_to_yombo(gateways, topic_parts, message)

    if len(topic_parts) < 5 == gateways.gateway_id:
        logger.debug("Gateway COMS received too short of a topic (discarding): {topic}", topic=topic)
        return
    if topic_parts[1] == gateways.gateway_id:
        logger.debug("discarding message that I sent.")
        return
    if topic_parts[2] not in (gateways.gateway_id, 'all', 'cluster'):
        logger.debug("MQTT message doesn't list us as a target, dropping")
        return

    if topic_parts[1] in gateways.gateways:
        gateways.gateways[topic_parts[1]].last_scene = time()
        gateways.gateways[topic_parts[1]].last_communications.append({
            'time': time(),
            'direction': 'received',
            'topic': topic,
        })

    if len(message) == 0 or message is None:
        logger.warn("Empty payloads for inter gateway coms are not allowed!")
        return

    if topic_parts[0] == "ybo_gw":
        yield gateways.mqtt_incomming_data(gateways, topic_parts, message)
    elif topic_parts[0] == "ybo_gw_req":
        yield gateways.mqtt_incomming_request(gateways, topic_parts, message)


def mqtt_incoming_to_yombo(gateways, topics, message):
    if topics[1] == "device_command":
        device_search = topics[2]
        command_search = topics[3]
        if len(device_search) > 200 or isinstance(device_search, str) is False:
            logger.debug("Dropping MQTT device command request, device_id is too long or invalid.")
            return
        if device_search in gateways._Devices:
            device = gateways._Devices[device_search]
            if device.gateway_id != gateways.gateway_id:
                logger.debug("Dropping MQTT device command request, i'm not the controlling gateway.: {device}",
                            device=device_search)
        else:
            logger.debug("Dropping MQTT device command request, device_id is not found: {device}",
                        device=device_search)
            return

        if len(command_search) > 200 or isinstance(command_search, str) is False:
            logger.debug("Dropping MQTT device command request, command_id is too long or invalid.")
            return
        if command_search in gateways._Commands:
            command = gateways._Commands[command_search]
        else:
            logger.debug("Dropping MQTT device command request, command_id is not found: {command}",
                        command=command_search)
            return

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
                requested_by={
                    'user_id': None,
                    'component': 'yombo.gateway.lib.gateways.mqtt',
                    'gateway': gateways.gateway_id
                },
                pin=pin_code,
                delay=delay,
                max_delay=max_delay,
                not_before=not_before,
                not_after=not_after,
                inputs=inputs,
                idempotence=idempotence,
            )
        except KeyError as e:
            return
        except YomboWarning as e:
            return


@inlineCallbacks
def mqtt_incomming_request(gateways, topics, message):
    # ybo_gw_req/src_gwid/dest_gwid|all/lib/devices/get - 'request_id' can be in the payload section of the message.
    # ybo_gw_req/src_gwid/dest_gwid|all/lib/devices/update/device_id - payload is full device, including meta and state
    # ybo_gw_req/src_gwid/dest_gwid|all/lib/states/get - payload is blank
    # ybo_gw_req/src_gwid/dest_gwid|all/lib/states/get/section/option - payload is blank
    # ybo_gw_req/src_gwid/dest_gwid|all/lib/states/update/section/option - payload is all details
    # ybo_gw_req/src_gwid/dest_gwid|all/lib/atoms/get/name - payload is blank
    # ybo_gw_req/src_gwid/dest_gwid|all/lib/atoms/update/name - payload is all details
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
    # print("gateway received content: %s" % message)

    if component_type not in ('lib', 'module', 'system'):
        logger.info("Gateway COMS received invalid component type: {component_type}", component_type=component_type)
        return

    if component_type == 'module':
        try:
            module = gateways._Modules[component_name]
        except Exception:
            logger.info("Received inter-gateway MQTT coms for module {module}, but module not found. Dropping.",
                        module=component_name)
            return
        try:
            yield maybeDeferred(module._inter_gateway_mqtt_req_, topics, message)
        except Exception:
            logger.info("Received inter-gateway MQTT coms for module {module}, but module doesn't have function '_inter_gateway_mqtt_req_' Dropping.",
                        module=component_name)
            return

    elif component_type == 'lib':
        # return_topic = source_id + "/" + component_type + "/"+ component_name
        if opt1 == 'get':
            if 'item_request_id' in message['payload']:
                item_request_id = message['item_request_id']
            else:
                item_request_id = None

            if component_name == 'atoms':
                send_atoms(gateways, destination_id=source_id, atom_id=item_request_id)
            elif component_name == 'device_status':
                send_device_status(gateways, destination_id=source_id, device_id=item_request_id)
            elif component_name == 'device_commands':
                send_device_commands(gateways, destination_id=source_id, device_command_id=item_request_id)
            elif component_name == 'states':
                send_states(gateways, destination_id=source_id, state_id=item_request_id)

    elif component_type == 'system':
        if opt1 == 'ping':
            message = {'response_id': message['message_id'], 'gateway_id': gateways.gateway_id, 'time': time()}
            publish_data(gateways, 'gw', source_id, 'system/ping')


@inlineCallbacks
def mqtt_incomming_data(gateways, topics, message):
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

    # print("gateway received content: %s" % message)

    if component_type == 'module':
        try:
            module = gateways._Modules[component_name]
        except Exception as e:
            logger.info("Received inter-gateway MQTT coms for module {module}, but module not found. Dropping.", module=component_name)
            return
        try:
            yield maybeDeferred(module._inter_gateway_mqtt_, topics, message)
        except Exception as e:
            logger.info("Received inter-gateway MQTT coms for module {module}, but module doesn't have function '_inter_gateway_mqtt_' Dropping.", module=component_name)
            return
    elif component_type == 'lib':
        try:
            if component_name == 'atoms':
                for name, value in message['payload'].items():
                    gateways._Atoms.set_from_gateway_communications(name, value)
            elif component_name == 'devices':
                pass
                # for name, value in message['payload'].items():
                #     gateways._Atoms.set_from_gateway_communications(name, value)
            elif component_name == 'device_command':
                incoming_data_device_command(gateways, source_mqtt_id, message)
            elif component_name == 'device_command_status':
                incoming_data_device_command_status(gateways, source_mqtt_id, message)
            elif component_name == 'device_status':
                incoming_data_device_status(gateways, source_mqtt_id, message)
            elif component_name == 'notification':
                incoming_data_notification(gateways, source_mqtt_id, message)
            elif component_name == 'states':
                for name, value in message['payload'].items():
                    gateways._States.set_from_gateway_communications(name, value)
            elif component_name == 'state':
                gateways._States.set_from_gateway_communications(opt1, message['payload'])
            elif component_name == 'gateway':
                if opt1 == 'online':
                    gateways.gateways[source_mqtt_id].com_status = 'online'
                    reactor.callLater(random_int(2, .8), send_all_info, gateways, destination_id=source_mqtt_id)
                elif opt1 == 'offline':
                    gateways.gateways[source_mqtt_id].com_status = 'offline'
        except Exception as e:  # catch anything here...so can display details.
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.format_exc())
            logger.error("--------------------------------------------------------")
    elif component_type == 'system':
        if component_name == 'ping':
            if 'gateway_id' in message['payload']:
                gateway_id = message['gateway_id']
                response_id = message['payload']['response_id']
                if gateway_id in gateways.gateways and gateways.gateways[gateway_id].ping_request_id == response_id:
                    gateways.gateways[gateway_id].ping_response = current_time
                    gateways.gateways[gateway_id].ping_time_offset = current_time - message['payload']['time']

def incoming_data_device_command(gateways, destination_id, message):
    """
    Handles incoming device commands. Only the master node will store device command information for
    other gateways.

    :param message:
    :return:
    """
    # print("got device_commands")
    payload = message['payload']

    def do_device_command(gateways, device_command):
        device = gateways._Devices.get(device_command['device_id'])
        # print("do_device_command")
        if device.gateway_id != gateways.gateway_id and gateways.is_master is not True:  # if we are not a master, we don't care!
            # print("do_device_command..skipping due to not local gateway and not a master: %s" % self.is_master)
            # print("dropping device command..  dest gw: %s" % device_command['gateway_id'])
            # print("dropping device command..  self.gateway_id: %s" % self.gateway_id)
            return
        device_command['device'] = device
        device_command['_source'] = 'gateway_coms'
        gateways._Devices.add_device_command(device_command)

    if isinstance(payload['device_command'], list):
        for device_command in payload['device_command']:
            do_device_command(gateways, device_command)
    else:
        do_device_command(gateways, payload['device_command'])


def incoming_data_device_command_status(gateways, destination_id, message):
    """
    Handles incoming device commands.

    :param message:
    :return:
    """
    payload = message['payload']

    if payload['request_id'] not in gateways._Devices.device_commands:
        msg = {'request_id': payload['request_id']}
        publish_data(gateways, 'req', destination_id, 'lib/device_commands', msg)
    else:
        gateways._Devices.update_device_command(destination_id,
                                                payload['request_id'],
                                                payload['log_time'],
                                                payload['status'],
                                                payload['message'])


def incoming_data_notification(gateways, destination_id, message):
    """
    Handles incoming device status.

    Todo: Complete this method.

    :param message:
    :return:
    """
    payload = message['payload']
    payload['status_source'] = 'gateway_coms'


def incoming_data_device_status(gateways, destination_id, message):
    """
    Handles incoming device status.

    :param message:
    :return:
    """
    for device_id, status in message['payload'].items():
        try:
            device = gateways._Devices[message['payload']['device_id']]
        except Exception:
            logger.warn("Local gateway doesn't have a local copy of the device. Perhaps reboot this gateway.")
            continue
        device.set_status_internal(status, source='gateway_mqtt')


def encode_message(gateways, payload, destination_id=None):
    """
    Creates a basic dictionary to represent the message and then pickles it using JSON.

    :param gateways: Reference to the gateway library
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
        'source_id': gateways.gateway_id,
        'destination_id': destination_id,
        'message_id': message_id
    }
    return message_id, data_pickle(message, 'json')


def decode_message(gateways, message):
    """
    :param gateways: Reference to the gateway library
    :param message: Incoming message to decode
    :return:
    """
    msg = data_unpickle(message, 'json')
    msg['time_received']: time()
    return bytes_to_unicode(msg)


def publish_data(gateways, msg_type, destination_id, topic, message):
    final_topic = 'ybo_%s/%s/%s/%s' % (msg_type, gateways.gateway_id, destination_id, topic)
    message_id, outgoing_data = encode_message(gateways, message)
    gateways.mqtt.publish(final_topic, outgoing_data)

    logger.debug("gateways publish data: {topic} {data}", topic=final_topic, data=outgoing_data)
    gateways.gateways[gateways.gateway_id].last_communications.append({
        'time': time(),
        'direction': 'sent',
        'topic': final_topic,
    })
    if destination_id in gateways.gateways:
        gateways.gateways[destination_id].last_communications.append({
            'time': time(),
            'direction': 'sent',
            'topic': final_topic,
        })

    return message_id


def send_all_info(gateways, destination_id=None, set_ok_to_publish_updates=None):
    """
    Called when this gateway starts up and when another gateway comes online.

    :param gateways: Reference to the gateway library
    :param destination_id:
    :param set_ok_to_publish_updates:
    :return:
    """
    send_atoms(gateways, destination_id)
    send_device_status(gateways, destination_id)
    send_states(gateways, destination_id)
    if set_ok_to_publish_updates is True:
        gateways.ok_to_publish_updates = True


def send_atoms(gateways, destination_id=None, atom_id=None):
    return_gw = get_return_destination(destination_id)
    if atom_id is None or atom_id == '#':
        publish_data(gateways, 'gw', return_gw, 'lib/atoms', gateways._Atoms.get('#', full=True))
    else:
        atom = {atom_id: gateways._Atoms.get(atom_id, full=True)}
        publish_data(gateways, 'gw', return_gw, 'lib/atoms', atom)


def send_device_commands(gateways, destination_id=None, device_command_id=None):
    return_gw = get_return_destination(destination_id)
    if return_gw == 'all' and device_command_id is None:
        logger.debug("device commands request must have device_command_id or return gateway id.")
        return
    if device_command_id is None:
        found_device_commands = gateways._Devices.get_gateway_device_commands(gateways.gateway_id)
        gateways.publish_data(gateways, 'gw', return_gw, "lib/device_commands", found_device_commands)
    elif device_command_id in gateways._Devices.device_commands:
        if gateways._Devices.device_commands[device_command_id].gateway_id == gateways.gateway_id:
            device_command = {device_command_id: gateways._Devices.device_commands[device_command_id].asdict()}
            publish_data(gateways, 'gw', return_gw, "lib/device_commands", device_command)


def send_device_status(gateways, destination_id=None, device_id=None):
    return_gw = get_return_destination(destination_id)
    if device_id is None:
        found_devices = gateways._Devices.search(**{"gateway_id": gateways.gateway_id, 'status': 1})
        message = {}
        for device in found_devices:
            message[device['key']] = device['value'].status_all.asdict()
    else:
        if device_id in gateways._Devices:
            device = gateways._Devices[device_id].status_all.asdict()
            message = {device.device_id: device.asdict()}
    publish_data(gateways, 'gw', return_gw, 'lib/devices', message)


def send_states(gateways, destination_id=None, state_id=None):
    return_gw = get_return_destination(destination_id)
    if state_id is None or state_id == '#':
        publish_data(gateways, 'gw', return_gw, 'lib/states', gateways._States.get('#', full=True))
    else:
        state = {state_id: gateways._Atoms.get(state_id, full=True)}
        publish_data(gateways, 'gw', return_gw, 'lib/atoms', state)


def get_return_destination(gateways, destination_id=None):
    if destination_id is None or destination_id is '':
        return 'all'
    return destination_id
