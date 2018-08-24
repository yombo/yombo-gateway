# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. warning::

   This library is not intended to be accessed by module developers or end users. These functions, variables,
   and classes were not intended to be accessed directly by modules. These are documented here for completeness.

.. note::

  For more information see:
  `Gateway Communications @ Module Development <https://yombo.net/docs/libraries/gateway_communications>`_

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
import ssl
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
from yombo.utils import random_int, data_pickle, data_unpickle, random_string, sleep

logger = get_logger('library.gateway_communications')

class Gateway_Communications(YomboLibrary):
    ok_to_publish_updates = False

    def _init_(self, **kwargs):
        self.ok_to_publish_updates = False
        self.gateway_id = self._Configs.get2('core', 'gwid', 'local', False)
        self.log_incoming = deque([], 150)
        self.log_outgoing = deque([], 150)
        self.mqtt = None
        self.gateway_id = self._Configs.gateway_id
        self.is_master = self._Configs.is_master
        self.master_gateway_id = self._Configs.master_gateway_id

        local_gateway = self._Gateways.local
        master_gateway = self._Gateways.master

        # Internal here mean for internal use, for the framework only or modules making
        # connections to the MQTT broker for Yombo use.
        # The non-internal is used to show to external services/devics/webpages.
        self.client_default_host = None
        self.client_default_mqtt_port_internal = None
        self.client_default_mqtt_port_internal_ssl = None
        self.client_default_mqtt_port = None
        self.client_default_mqtt_port_ssl = None
        self.client_default_ws_port_internal = None
        self.client_default_ws_port_internal_ssl = None
        self.client_default_ws_port = None
        self.client_default_ws_port_ssl = None

        self.client_default_username = 'yombogw_' + self.gateway_id()
        self.client_default_password1 = local_gateway.mqtt_auth
        self.client_default_password2 = local_gateway.mqtt_auth_next

        if self._Loader.operating_mode == 'run':
            logger.warn("Gateway communications disabled when not in run mode.")

            return

        mqtt_hosts_internal = (
            'i.' + master_gateway.fqdn,
            master_gateway.internal_ipv4,
            )
        mqtt_hosts_external = (
            'e.' + master_gateway.fqdn,
            master_gateway.external_ipv4
          )

        mqtt_ports_internal = (
            {
                'port': master_gateway.internal_mqtt_le,
                'type': 'mqtt',
                'ssl': 'signed',
            },
            {
                'port': master_gateway.internal_mqtt_ss,
                'type': 'mqtt',
                'ssl': 'unsigned',
            },
            {
                'port': master_gateway.internal_mqtt,
                'type': 'mqtt',
                'ssl': 'none',
            },
            {
                'port': master_gateway.internal_mqtt_ws_le,
                'type': 'ws',
                'ssl': 'signed',
            },
            {
                'port': master_gateway.internal_mqtt_ws_ss,
                'type': 'ws',
                'ssl': 'unsigned',
            },
            {
                'port': master_gateway.internal_mqtt_ws,
                'type': 'ws',
                'ssl': 'none',
            },
        )

        mqtt_ports_external = (
            {
                'port': master_gateway.external_mqtt_le,
                'type': 'mqtt',
                'ssl': 'signed',
            },
            {
                'port': master_gateway.external_mqtt_ss,
                'type': 'mqtt',
                'ssl': 'unsigned',
            },
            {
                'port': master_gateway.external_mqtt_ws_le,
                'type': 'ws',
                'ssl': 'signed',
            },
            {
                'port': master_gateway.external_mqtt_ws_ss,
                'type': 'ws',
                'ssl': 'unsigned',
            },
        )

        # Now determine the optimal mqtt connection to the master gateway. Order or preference:
        # 1) We prefer localhost with no SSL since it's all internal - less CPU on low end devics.
        # 2) Local network, but with SSL preferred.
        # 3) Remote network, only SSL!


        def test_non_ssl_port(host, port):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            logger.debug("# Test non ssl host - port: {host} - {port}", host=host, port=port)
            return sock.connect_ex((host, port))

        def is_ssl(port_type):
            if port_type == 'none':
                return False
            return True

        # Test if we can connect to local host, for mqtt
        port = master_gateway.internal_mqtt
        result = test_non_ssl_port('127.0.0.1', port)
        logger.debug("-  Results: {result}", result=result)
        if result == 0:  # Able to connect to localhost using internal port
            self.client_default_host = '127.0.0.1'
            self.client_default_mqtt_port_internal = port
            self.client_default_mqtt_port_internal_ssl = False
            self.client_default_mqtt_port = port
            self.client_default_mqtt_port_ssl = False

            # Test if we can connect to local host, for mqtt
            port = master_gateway.internal_mqtt
            result = test_non_ssl_port('127.0.0.1', port)
            logger.debug("-  Results: {result}", result=result)
            if result == 0:  # Able to connect to localhost using internal port
                self.client_default_mqtt_port_internal = port
                self.client_default_mqtt_port_internal_ssl = False
                self.client_default_mqtt_port = port
                self.client_default_mqtt_port_ssl = False

            port = master_gateway.internal_mqtt_le
            result = test_non_ssl_port('127.0.0.1', port)
            logger.debug("-  Results: {result}", result=result)
            if result == 0:  # Able to connect to localhost using internal port
                self.client_default_mqtt_port = port
                self.client_default_mqtt_port_ssl = True

            port = master_gateway.internal_mqtt_ws
            result = test_non_ssl_port('127.0.0.1', port)
            logger.debug("-  Results: {result}", result=result)
            if result == 0:  # Able to connect to localhost using internal port
                self.client_default_ws_port_internal = port
                self.client_default_ws_port_internal_ssl = False
                self.client_default_ws_port = port
                self.client_default_ws_port_ssl = False

            port = master_gateway.internal_mqtt_ws_le
            result = test_non_ssl_port('127.0.0.1', port)
            logger.debug("-  Results: {result}", result=result)
            if result == 0:  # Able to connect to localhost using internal port
                self.client_default_ws_port = port
                self.client_default_ws_port_ssl = True

        def check_host_ports(host, ports):
            found_port_ws = None
            found_port_ws_ssl = None
            found_port_mqtt = None
            found_port_mqtt_ssl = None

            for port in mqtt_ports_internal:
                # if port['ssl'] in ('none', 'unsigned'):  # Yes, it's not NoneType
                results = test_non_ssl_port(host, port['port'])
                logger.debug("-  Results: {results}", results=results)
                if results == 0:  # Able to connect to localhost using internal port
                    if port['type'] == 'ws':
                        if found_port_ws is None:
                            found_port_ws = port['port']
                            found_port_ws_ssl = is_ssl(port['ssl'])
                    elif port['type'] == 'mqtt':
                        if found_port_ws is None:
                            found_port_mqtt = port['port']
                            found_port_mqtt_ssl = is_ssl(port['ssl'])

            if found_port_ws is not None:
                self.client_default_host = host
                self.client_default_mqtt_port_internal = found_port_mqtt
                self.client_default_mqtt_port_internal_ssl = found_port_mqtt_ssl
                self.client_default_mqtt_port = found_port_mqtt
                self.client_default_mqtt_port_ssl = found_port_mqtt_ssl
                self.client_default_ws_port_internal = found_port_ws
                self.client_default_ws_port_internal_ssl = found_port_ws_ssl
                self.client_default_ws_port = found_port_ws
                self.client_default_ws_port_ssl = found_port_ws_ssl
                return True
            return False

        # Lets look for an internal mqtt server running on a master gateway node.
        if self.client_default_host is None:
            for host in mqtt_hosts_internal:
                result = check_host_ports(host, mqtt_ports_internal)
                if result is True:
                    break

        # And last, we look for external connections
        if self.client_default_host is None:
            for host in mqtt_hosts_external:
                result= check_host_ports(host, mqtt_ports_external)
                if result is True:
                    break

        if self.client_default_host is None:
            logger.warn("Cannot find an open MQTT port to the master gateway.")

    def _start_(self, **kwargs):
        if self._Loader.operating_mode == 'run':
            return
        self.mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming,
                                   client_id='Yombo-gateways-%s' % self.gateway_id())
        # self.test()  # todo: move to unit tests..  Todo: Create unit tests.. :-)
        # Requests from other gateways
        self.mqtt.subscribe("ybo_req/+/all/#")
        self.mqtt.subscribe("ybo_req/+/cluster/#")
        self.mqtt.subscribe("ybo_req/+/%s/#" % self.gateway_id())

        # Data broadcasts or data responses to gateways
        self.mqtt.subscribe("ybo_gw/+/all/#")
        self.mqtt.subscribe("ybo_gw/+/cluster/#")
        self.mqtt.subscribe("ybo_gw/+/%s/#" % self.gateway_id())

        # Requests from IoT items. Each gateway will subscribe to this, but it will be
        # responsible to knowing if to response or act on the request.
        self.mqtt.subscribe("yombo/#")

    def _started_(self, **kwargs):
        if self._Loader.operating_mode == 'run':
            return
        self.publish_data('gw', "all", "lib/gateway/online", "")
        reactor.callLater(3, self.send_all_info, set_ok_to_publish_updates=True)

        if self.is_master is True:
            ping_interval = self._Configs.get('mqtt', 'ping_interval_master', 20, False)
        else:
            ping_interval = self._Configs.get('mqtt', 'ping_interval_members', 60, False)

        self.ping_gateways_loop = LoopingCall(self.ping_gateways)
        # self.ping_gateways_loop.start(random_int(ping_interval, .1), False)

    @inlineCallbacks
    def _stop_(self, **kwargs):
        """
        Cleans up any pending deferreds.
        """
        if self._Loader.operating_mode == 'run':
            return
        if hasattr(self, 'mqtt'):
            if self.mqtt is not None:
                self.publish_data('gw', "all", "lib/gateway/offline", "")
                yield sleep(0.05)

    def ping_gateways(self):
        """
        Pings all the known gateways.

        :return:
        """
        for gateway_id, gateway in self.gateways.items():
            if gateway_id in ('local', 'all', 'cluster') or len(gateway_id) < 13:
                continue
            current_time = time()
            message = {'time': current_time}
            request_id = self.publish_data('req', gateway_id, "system/ping", message)
            self.gateways[gateway_id].ping_request_id = request_id
            self.gateways[gateway_id].ping_request_at = current_time

    def _atoms_set_(self, **kwargs):
        """
        Publish a new atom, only if it's from ourselves.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return
        if 'source' in kwargs and kwargs['source'] == 'gateway_coms':
            return
        if kwargs['gateway_id'] != self.gateway_id():
            return

        atom = {kwargs['key']: kwargs['value_full']}
        self.publish_data('gw', 'all', "lib/atoms", atom)

    def _device_command_(self, **kwargs):
        """
        A new command for a device has been sent. This is used to tell other gateways that either a local device
        is about to do something, other another gateway should do something.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return

        device_command = kwargs['device_command'].asdict()
        if device_command['source_gateway_id'] != self.gateway_id():
            return

        message = {
            'state': 'new',
            'device_command': device_command
        }

        topic = "lib/device_command"
        self.publish_data('gw', 'all', topic, message)

    def _device_command_status_(self, **kwargs):
        """
        A device command has changed status. Update everyone else.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return
        if 'source' in kwargs and kwargs['source'] == 'gateway_coms':
            return

        device_command = kwargs['device_command']
        if device_command.source_gateway_id != self.gateway_id():
            return

        history = device_command.last_history()
        message = {
            device_command.request_id: {
                'request_id': kwargs['device_command'].request_id,
                'log_time': history['time'],
                'status': history['status'],
                'message': history['msg'],
            }
        }

        self.publish_data('gw', 'all', "lib/device_command_status", message)

    def _device_status_(self, **kwargs):
        """
        Publish a new state, if it's from ourselves.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return
        source = kwargs.get('source', None)
        if source == 'gateway_coms':
            return
        device = kwargs['device']
        device_id = device.device_id

        if self.gateway_id() != device.gateway_id:
            return

        topic = "lib/device_status"
        self.publish_data('gw', 'all', topic, device.status_all.asdict())

    def _notification_add_(self, **kwargs):
        """
        Publish a new notification, if it's from ourselves.

        :param kwargs:
        """
        # print("_device_status_: %s" % kwargs['command'])
        if self.ok_to_publish_updates is False:
            return

        notice = kwargs['notification']
        if notice.local is True:
            return

        # print("checking if i should send this device_status.  %s != %s" % (self.gateway_id(), device.gateway_id))
        if self.gateway_id() != notice.gateway_id:
            return

        message = {
            'action': 'add',
            'notice': kwargs['event'],
        }

        topic = "lib/notification/" + notice.notification_id
        # print("sending _device_status_: %s -> %s" % (topic, message))
        # self.publish_data('gw', 'all', topic, message)

    def _notification_delete_(self, **kwargs):
        """
        Delete a notification, if it's from ourselves.

        :param kwargs:
        :return:
        """
        # print("_device_status_: %s" % kwargs['command'])
        if self.ok_to_publish_updates is False:
            return

        notice = kwargs['notification']
        if notice.local is True:
            return

        # print("checking if i should send this device_status.  %s != %s" % (self.gateway_id(), device.gateway_id))
        if self.gateway_id() != notice.gateway_id:
            return

        message = {
            'action': 'delete',
            'notice': kwargs['event'],
        }

        topic = "lib/notification/" + notice.notification_id
        # print("sending _device_status_: %s -> %s" % (topic, message))
        # self.publish_data('gw', 'all', topic, message)

    def _states_set_(self, **kwargs):
        """
        Publish a new state, if it's from ourselves.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return
        if 'source' in kwargs and kwargs['source'] == "gateway_coms":
            return
        gateway_id = kwargs['gateway_id']
        if gateway_id != self.gateway_id() and gateway_id not in ('global', 'cluster'):
            return

        message = deepcopy(kwargs['value_full'])
        message['key'] = kwargs['key']

        state = {kwargs['key']: kwargs['value_full']}
        self.publish_data('gw', 'all', "lib/states", state)

    @inlineCallbacks
    def mqtt_incoming(self, topic, raw_message, qos, retain):
        # ybo_req/src_gwid/dest_gwid|all/lib/devices/get - payload is blank - get all device information
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

        if topic_parts[1] in self._Gateways.gateways:
            self._Gateways.gateways[topic_parts[1]].last_scene = time()
            self._Gateways.gateways[topic_parts[1]].last_communications.append({
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
            if device_search in self._Devices:
                device = self._Devices[device_search]
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
            if command_search in self._Commands:
                command = self._Commands[command_search]
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
                module = self._Modules[component_name]
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
                        self._Atoms.set_from_gateway_communications(name, value)
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
                        self._States.set_from_gateway_communications(name, value)
                elif component_name == 'gateway':
                    if opt1 == 'online':
                        self._Gateways.gateways[source_mqtt_id].com_status = 'online'
                        reactor.callLater(random_int(2, .8), self.send_all_info, destination_id=source_mqtt_id)
                    elif opt1 == 'offline':
                        self._Gateways.gateways[source_mqtt_id].com_status = 'offline'
            except Exception as e:  # catch anything here...so can display details.
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.format_exc())
                logger.error("--------------------------------------------------------")
        elif component_type == 'system':
            if component_name == 'ping':
                if 'gateway_id' in message['payload']:
                    gateway_id = message['payload']['gateway_id']
                    response_id = message['payload']['response_id']
                    gateway = self._Gateways.gateways[gateway_id]
                    if gateway_id in self._Gateways.gateways and gateway.ping_request_id == response_id:
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
            device = parent._Devices.get(device_command['device_id'])
            if device.gateway_id != parent.gateway_id() and parent.is_master() is not True:  # if we are not a master, we don't care!
                # print("do_device_command..skipping due to not local gateway and not a master: %s" % parent.is_master())
                # print("dropping device command..  dest gw: %s" % device_command['gateway_id'])
                # print("dropping device command..  self.gateway_id: %s" % self.gateway_id)
                return False
            device_command['broadcast_at'] = None
            device_command['device'] = device
            device_command['source_gateway_id'] = source_mqtt_id
            parent._Devices.add_device_command(device_command)

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
            if request_id not in self._Devices.device_commands:
                msg = {'request_id': request_id}
                self.publish_data('req', source_mqtt_id, 'lib/device_commands', msg)
            else:
                self._Devices.update_device_command(
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
            if device_id not in self._Devices:
                logger.info("MQTT Received device status for a device that doesn't exist, dropping: {device_id}",
                            device_id=device_id)
                continue
            device = self._Devices[device_id]
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
        self.log_outgoing.append({'sent': time(), 'topic': final_topic, 'message': message})
        self.mqtt.publish(final_topic, outgoing_data)

        logger.debug("gateways publish data: {topic} {data}", topic=final_topic, data=outgoing_data)
        self._Gateways.gateways[self.gateway_id()].last_communications.append({
            'time': time(),
            'direction': 'sent',
            'topic': final_topic,
        })
        if destination_id in self._Gateways.gateways:
            self._Gateways.gateways[destination_id].last_communications.append({
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
            self.ok_to_publish_updates = True

    def send_atoms(self, destination_id=None, atom_id=None):
        return_gw = self.get_return_destination(destination_id)
        if atom_id is None or atom_id == '#':
            self.publish_data('gw', return_gw, 'lib/atoms', self._Atoms.get('#', full=True))
        else:
            atom = {atom_id: self._Atoms.get(atom_id, full=True)}
            self.publish_data('gw', return_gw, 'lib/atoms', atom)

    def send_device_commands(self, destination_id=None, device_command_id=None):
        return_gw = self.get_return_destination(destination_id)
        if return_gw == 'all' and device_command_id is None:
            logger.debug("device commands request must have device_command_id or return gateway id.")
            return
        if device_command_id is None:
            found_device_commands = self._Devices.get_gateway_device_commands(self.gateway_id())
        elif device_command_id in self._Devices.device_commands:
            if self._Devices.device_commands[device_command_id].gateway_id == self.gateway_id():
                found_device_commands = {device_command_id: self._Devices.device_commands[device_command_id].asdict()}
        self.publish_data('gw', return_gw, "lib/device_commands", found_device_commands)

    def send_device_status(self, destination_id=None, device_id=None):
        gateway_id = self.gateway_id()
        return_gw = self.get_return_destination(destination_id)
        message = {}
        if device_id is None:
            for device_id, device in self._Devices.devices.items():
                if device.gateway_id == gateway_id or device.status != 1:
                    continue
                message[device_id] = device.status_all.asdict()
        else:
            if device_id in self._Devices:
                device = self._Devices[device_id]
                if device.gateway_id == gateway_id or device.status != 1:
                    return
                message[device_id] = device.status_all.asdict()
        self.publish_data('gw', return_gw, 'lib/device_status', message)

    def send_states(self, destination_id=None, state_id=None):
        return_gw = self.get_return_destination(destination_id)
        if state_id is None or state_id == '#':
            self.publish_data('gw', return_gw, 'lib/states', self._States.get('#', full=True))
        else:
            state = {state_id: self._Atoms.get(state_id, full=True)}
            self.publish_data('gw', return_gw, 'lib/states', state)

    def get_return_destination(self, destination_id=None):
        if destination_id is None or destination_id is '':
            return 'all'
        return destination_id

    def test(self):
        self.mqtt_test_connection = self.new(self.server_listen_ip,
            self.server_listen_port, 'yombo', self.default_client_mqtt_password1, False,
            self.test_mqtt_in, self.test_on_connect )

        self.mqtt_test_connection.subscribe("yombo/#")

        self.sendDataLoop = LoopingCall(self.test_send_data)
        self.sendDataLoop.start(5, True)

    def test_on_connect(self):
        print("in on connect in library...")
        self.test_send_data()

    def test_send_data(self):
        print("mqtt sending test package")
        self.mqtt_test_connection.publish("yombo/devices/asdf/asdf", 'open')

    def test_mqtt_in(self, topic, payload, qos, retain):
        print("i got this: %s / %s" % (topic, payload))
