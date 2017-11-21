# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Gateways @ Module Development <https://docs.yombo.net/Libraries/Gateways>`_

Handles inter-gateway communications. Any gateway within an account can communicate with another
gateway using any master gateway's mqtt broker service.

Slave gateways will connect to it's master's mqtt broker. All slave gateways will report device status, states, and
atoms to the master. Scenes and automation rules can fire on any gateway, however, if status is required from
a remote gateway, that automation rule should only fire on the master server.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.14.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://docs.yombo.net/gateway/html/current/_modules/yombo/lib/gateways.html>`_
"""
from collections import deque
import msgpack
from time import time
import socket
import traceback
import zlib

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred, maybeDeferred
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import do_search_instance, global_invoke_all, bytes_to_unicode, random_int, sleep

logger = get_logger('library.gateways')

class Gateways(YomboLibrary):
    """
    Manages information about gateways.
    """
    library_phase = 0
    ok_to_publish_updates = False

    @property
    def local(self):
        return self.gateways[self.gateway_id]

    @local.setter
    def local(self, val):
        return

    def __contains__(self, gateway_requested):
        """
        .. note:: The gateway must be enabled to be found using this method.

        Checks to if a provided gateway ID or machine_label exists.

            >>> if '0kas02j1zss349k1' in self._Gateways:

        or:

            >>> if 'some_gateway_name' in self._Gateways:

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param gateway_requested: The gateway id or machine_label to search for.
        :type gateway_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get_meta(gateway_requested)
            return True
        except:
            return False

    def __getitem__(self, gateway_requested):
        """
        .. note:: The gateway must be enabled to be found using this method.

        Attempts to find the device requested using a couple of methods.

            >>> gateway = self._Gateways['0kas02j1zss349k1']  #by uuid

        or:

            >>> gateway = self._Gateways['alpnum']  #by name

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param gateway_requested: The gateway ID or machine_label to search for.
        :type gateway_requested: string
        :return: A pointer to the device type instance.
        :rtype: instance
        """
        return self.get_meta(gateway_requested)

    def __setitem__(self, **kwargs):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, **kwargs):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter device types. """
        return self.device_types.__iter__()

    def __len__(self):
        """
        Returns an int of the number of device types configured.

        :return: The number of gateways configured.
        :rtype: int
        """
        return len(self.gateways)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return self.gateways.__str__()

    def keys(self):
        """
        Returns the keys (device type ID's) that are configured.

        :return: A list of device type IDs. 
        :rtype: list
        """
        return list(self.gateways.keys())

    def items(self):
        """
        Gets a list of tuples representing the device types configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.gateways.items())

    def values(self):
        return list(self.gateways.values())

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.library_phase = 1
        self.gateways = {}
        self.gateway_status = yield self._SQLDict.get(self, "gateway_status")
        self.ok_to_publish_updates = False
        self.mqtt = None
        self.gateway_id = self._Configs.get('core', 'gwid', 'local', False)
        self.is_master = self._Configs.get('core', 'is_master', True, False)
        self.master_gateway = self._Configs.get2('core', 'master_gateway', None, False)
        self.account_mqtt_key = self._Configs.get('core', 'account_mqtt_key', 'test', False)
        # self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.
        self.gateway_search_attributes = ['gateway_id', 'gateway_id', 'label', 'machine_label', 'status']
        # self.load_deferred = Deferred()
        if self._Loader.operating_mode != 'run':
            self.import_gateway({
                'id': 'local',
                'is_master': True,
                'master_gateway': '',
                'machine_label': 'local',
                'label': 'Local',
                'description': 'Local',
                'fqdn':'127.0.0.1',
            })

        yield self._load_gateways_from_database()

        # now local the master, on or off network.
        self.master_mqtt_host = None
        self.master_mqtt_ssl = None
        self.master_mqtt_port = None
        self.master_websock_ssl = None
        self.master_websock_port = None

        if self.is_master is True:
            self.master_mqtt_host = 'i.' + self.gateways[self.gateway_id].fqdn
            self.master_mqtt_ssl = False
            self.master_mqtt_port = self.gateways[self.gateway_id].internal_mqtt
            self.master_mqtt_port_ssl = self.gateways[self.gateway_id].internal_mqtt_le
            self.master_websock_ssl = False
            self.master_websock_port = self.gateways[self.gateway_id].internal_mqtt_ws
            self.master_websock_port_ssl = self.gateways[self.gateway_id].internal_mqtt_ws_le
        else:
            master = self.gateways[self.master_gateway()]
            # print("gateway is looking for master....")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('i.' + master.fqdn, master.internal_mqtt_ss))
            if result == 0:
                self.master_mqtt_host = 'i.' + master.fqdn
                self.master_mqtt_ssl = True
                self.master_mqtt_port = master.internal_mqtt_le
                self.master_mqtt_port_ssl = master.internal_mqtt_le
                self.master_websock_ssl = True
                self.master_websock_port = master.internal_mqtt_ws_le
                self.master_websock_port_ssl = master.internal_mqtt_ws_le
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('e.' + master.fqdn, master.external_mqtt_ss))
                if result == 0:
                    self.master_mqtt_host = 'e.' + master.fqdn
                    self.master_mqtt_ssl = True
                    self.master_mqtt_port = master.external_mqtt_le
                    self.master_mqtt_port_ssl = master.external_mqtt_le
                    self.master_websock_ssl = True
                    self.master_websock_port = master.external_mqtt_ws_le
                    self.master_websock_port_ssl = master.external_mqtt_ws_le
                else:
                    logger.warn("Cannot find an open MQTT port to the master gateway.")

        # save for later use.
        # self.encrypt = self._GPG.encrypt_aes
        # self.decrypt = self._GPG.decrypt_aes
        # self.encrypt = partial(self._GPG.encrypt_aes, self.account_mqtt_key)
        # self.decrypt = partial(self._GPG.decrypt_aes, self.account_mqtt_key)

    def _start_(self, **kwargs):
        self.library_phase = 3
        if self._States['loader.operating_mode'] != 'run':
            return
        self.mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming,
                                   client_id='Yombo-gateways-%s' % self.gateway_id)
        self.mqtt.subscribe("ybo_gw_req/+/all/#")
        self.mqtt.subscribe("ybo_gw_req/+/%s/#" % self.gateway_id)
        self.mqtt.subscribe("ybo_gw/+/all/#")
        self.mqtt.subscribe("ybo_gw/+/%s/#" % self.gateway_id)

    def _started_(self, **kwargs):
        self.library_phase = 4
        if self._States['loader.operating_mode'] != 'run':
            return
        self.publish_data("all", "lib/gateways/online", "")
        # print("!!!!!!!!!!!!!!!!!!gateways started!!!!!!!!!!!!!!!!1")
        reactor.callLater(5, self.send_all_info, set_ok_to_publish_updates=True)

        # self.test_send()

    @inlineCallbacks
    def _stop_(self, **kwargs):
        """
        Cleans up any pending deferreds.
        """
        if hasattr(self, 'mqtt'):
            if self.mqtt is not None:
                self.publish_data("all", "lib/gateways/offline", "")
                yield sleep(0.05)
        if hasattr(self, 'load_deferred'):
            if self.load_deferred is not None and self.load_deferred.called is False:
                self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    def _configuration_set_(self, **kwargs):
        """
        Receive configuruation updates and adjust as needed.

        :param kwargs: section, option(key), value
        :return:
        """
        section = kwargs['section']
        option = kwargs['option']
        value = kwargs['value']

        if section == 'core':
            if option == 'label':
                self.gateways['local'] = value
                if self.gateway_id != 'local':
                    self.gateways[self.gateway_id] = value

    def encrypt(self, data, destination_gateway_id=None):
        data = msgpack.packb(data)
        if len(data) > 800:
            # beforeZlib = len(data)
            data = zlib.compress(data, 3)  # 3 appears to be the best speed/compression ratio
            # afterZlib = len(data)
            # print("compression percent: %s -> %s : %s" % (beforeZlib, afterZlib, percentage(afterZlib, beforeZlib)))
            content_encoding = "zlib"
        else:
            content_encoding = "none"

        if destination_gateway_id is None:
            destination_gateway_id = 'all'
        message = {
            'payload': data,
            'time_sent': time(),
            'content_encoding': content_encoding,
            'source_gateway_id': self.gateway_id,
            'destination_gateway_id': destination_gateway_id,
        }

        return msgpack.packb(message)
        # results = yield self._GPG.encrypt_aes(self.account_mqtt_key, msgpack.packb(data))
        # return results

    def decrypt(self, incoming):
        # data = yield self._GPG.decrypt_aes(self.account_mqtt_key, data)
        message = msgpack.unpackb(incoming)
        data = message[b'payload']
        del message[b'payload']
        message = bytes_to_unicode(message)
        message['time_received']: time()
        if message['content_encoding'] == 'zlib':
            data = zlib.decompress(data)
        message['payload'] = msgpack.unpackb(data)
        return bytes_to_unicode(message)

    @inlineCallbacks
    def _load_gateways_from_database(self):
        """
        Loads gateways from database and sends them to
        :py:meth:`import_gateway <Gateways.import_gateway>`

        This can be triggered either on system startup or when new/updated gateways have been saved to the
        database and we need to refresh existing gateways.
        """
        gateways = yield self._LocalDB.get_gateways()
        for gateway in gateways:
            self.import_gateway(gateway)

    def import_gateway(self, gateway, test_gateway=False):
        """
        Add a new gateways to memory or update an existing gateways.

        **Hooks called**:

        * _gateway_before_load_ : If added, sends gateway dictionary as 'gateway'
        * _gateway_before_update_ : If updated, sends gateway dictionary as 'gateway'
        * _gateway_loaded_ : If added, send the gateway instance as 'gateway'
        * _gateway_updated_ : If updated, send the gateway instance as 'gateway'

        :param gateway: A dictionary of items required to either setup a new gateway or update an existing one.
        :type input: dict
        :param test_gateway: Used for unit testing.
        :type test_gateway: bool
        :returns: Pointer to new input. Only used during unittest
        """
        # logger.debug("importing gateway: {gateway}", gateway=gateway)

        gateway_id = gateway["id"]
        global_invoke_all('_gateways_before_import_',
                          called_by=self,
                          gateway_id=gateway_id,
                          gateway=gateway,
                          )
        if gateway_id not in self.gateways:
            global_invoke_all('_gateway_before_load_',
                              called_by=self,
                              gateway_id=gateway_id,
                              gateway=gateway,
                              )
            self.gateways[gateway_id] = Gateway(self, gateway)
            global_invoke_all('_gateway_loaded_',
                              called_by=self,
                              gateway_id=gateway_id,
                              gateway=self.gateways[gateway_id],
                              )
        elif gateway_id not in self.gateways:
            global_invoke_all('_gateway_before_update_',
                              called_by=self,
                              gateway_id=gateway_id,
                              gateway=self.gateways[gateway_id],
                              )
            self.gateways[gateway_id].update_attributes(gateway)
            global_invoke_all('_gateway_updated_',
                              called_by=self,
                              gateway_id=gateway_id,
                              gateway=self.gateways[gateway_id],
                              )

    @inlineCallbacks
    def mqtt_incoming(self, topic, raw_payload, qos, retain):
        # ybo_gw_req/src_gwid/dest_gwid|all/lib/devices/get - payload is blank - get all device information
        # ybo_gw_req/src_gwid/dest_gwid|all/lib/devices/get/device_id - payload is blank
        topic_parts = topic.split('/', 10)

        if len(topic_parts) < 5 == self.gateway_id:
            logger.debug("Gateway COMS received too short of a topic (discarding): {topic}", topic=topic)
            return
        if topic_parts[1] == self.gateway_id:
            logger.debug("discarding message that I sent.")
            return
        if topic_parts[1] not in self.gateways:
            logger.debug("Discarding message from gateway {gwid}, not in list of known gateways.", gwid=topic_parts[1])
            return
        # print("if %s == %s:" % (topic_parts[1], self.gateway_id))
        # print("got incoming: %s" % topic)
        self.gateways[topic_parts[1]].last_scene = time()
        self.gateways[topic_parts[1]].last_communications.append({
            'time': time(),
            'direction': 'received',
            'topic': topic,
        })

        if len(raw_payload) > 0:
            try:
                message = self.decrypt(raw_payload)
            except Exception as e:
                logger.warn("Gateways:MQTT received invalid data.")
                return
        else:
            logger.warn("Empty payloads for inter gateway coms are not allowed!")
            return

        if topic_parts[0] == "ybo_gw":
            yield self.mqtt_incomming_data(topic_parts, message)
        else:
            yield self.mqtt_incomming_request(topic_parts, message)

    @inlineCallbacks
    def mqtt_incomming_request(self, topics, message):
        # ybo_gw_req/src_gwid/dest_gwid|all/lib/devices/get - payload is blank - get all device information
        # ybo_gw_req/src_gwid/dest_gwid|all/lib/devices/get/device_id - payload is blank
        # ybo_gw_req/src_gwid/dest_gwid|all/lib/devices/update/device_id - payload is full device, including meta and state
        # ybo_gw_req/src_gwid/dest_gwid|all/lib/states/get - payload is blank
        # ybo_gw_req/src_gwid/dest_gwid|all/lib/states/get/section/option - payload is blank
        # ybo_gw_req/src_gwid/dest_gwid|all/lib/states/update/section/option - payload is all details
        # ybo_gw_req/src_gwid/dest_gwid|all/lib/atoms/get/name - payload is blank
        # ybo_gw_req/src_gwid/dest_gwid|all/lib/atoms/update/name - payload is all details
        source_gw_id = topics[1]
        dest_gw_id = topics[2]
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

        if component_type not in ('lib', 'module'):
            logger.info("Gateway COMS received invalid component type: {component_type}", component_type=component_type)
            return

        if source_gw_id not in self.gateways:
            logger.info("Dropping gw comms message, gwid is invalid to us. Perhaps we need a restart?")
            return

        self.gateways[source_gw_id].last_scene = time()
        if component_type == 'module':
            try:
                module = self._Modules[component_name]
            except Exception as e:
                logger.info("Received inter-gateway MQTT coms for module {module}, but module not found. Dropping.",
                            module=component_name)
                return
            try:
                yield maybeDeferred(module._inter_gateway_mqtt_req_, topics, message)
            except Exception as e:
                logger.info("Received inter-gateway MQTT coms for module {module}, but module doesn't have function '_inter_gateway_mqtt_req_' Dropping.",
                            module=component_name)
                return

        elif component_type == 'lib':
            return_topic = source_gw_id + "/" + component_type + "/"+ component_name
            if len(topics) == 5 and opt1 == 'get':
                all_requested = True
            else:
                all_requested = False

            if component_name == 'atoms':
                if opt1 == 'get':
                    if all_requested:
                        self.send_all_atoms(source_gw_id)
                    else:
                        self.send_all_atoms(source_gw_id, topics[5])
            elif component_name == 'devices':
                if opt1 == 'get':
                    if all_requested:
                        self.send_all_devices(source_gw_id)
                    else:
                        self.send_all_devices(source_gw_id, topics[5])
            elif component_name == 'device_commands':
                if opt1 == 'get':
                    if all_requested:
                        self.send_all_device_commands(source_gw_id)
                    else:
                        self.send_all_device_commands(source_gw_id, topics[5])
            elif component_name == 'states':
                if opt1 == 'get':
                    if all_requested:
                        self.send_all_states(source_gw_id)
                    else:
                        self.send_all_states(source_gw_id, topics[5])

    @inlineCallbacks
    def mqtt_incomming_data(self, topics, message):
        print("mqtt_incomming_data now. topics: %s" % topics)
        # print("mqtt_incomming_data now. message: %s" % message)
        # ybo_gw/src_gwid/dest_gwid|all/lib/atoms - all atoms from gateway
        # ybo_gw/src_gwid/dest_gwid|all/lib/atoms/name - single atom
        source_gw_id = topics[1]
        dest_gw_id = topics[2]
        component_type = topics[3]
        component_name = topics[4]
        # print("gateway received content: %s" % message)

        if component_type == 'module':
            try:
                module = self._Modules[component_name]
            except Exception as e:
                logger.info("Received inter-gateway MQTT coms for module {module}, but module not found. Dropping.", module=component_name)
                return
            try:
                yield maybeDeferred(module._inter_gateway_mqtt_, topics, message)
            except Exception as e:
                logger.info("Received inter-gateway MQTT coms for module {module}, but module doesn't have function '_inter_gateway_mqtt_' Dropping.", module=component_name)
                return
        elif component_type == 'lib':
            if len(topics) == 5:
                all_requested = True
            else:
                all_requested = False
            if len(topics) == 6:
                opt1 = topics[5]
            else:
                opt1 = None
            if len(topics) == 7:
                opt2 = topics[6]
            else:
                opt2 = None

            try:
                if component_name == 'atoms':
                    if all_requested:
                        for name, value in message['payload'].items():
                            self._Atoms.set_from_gateway_communications(name, value)
                    else:
                        print("got one atom...")
                        self._Atoms.set_from_gateway_communications(opt1, message['payload'])
                elif component_name == 'devices':
                    if all_requested:
                        pass
                        # print("all devices from %s message: %s" % (source_gw_id, message))
                    else:
                        pass
                        # print("single devices (%s) from %s message: %s" % (opt1, source_gw_id, message))
                elif component_name == 'device_commands':
                    self.incoming_data_device_command(source_gw_id, message)
                elif component_name == 'device_command_status':
                    self.incoming_data_device_command_status(source_gw_id, message)
                elif component_name == 'device_status':
                    self.incoming_data_device_status(source_gw_id, message)
                elif component_name == 'notification':
                    self.incoming_data_notification(source_gw_id, message)
                elif component_name == 'states':
                    if all_requested:
                        for name, value in message['payload'].items():
                            self._States.set_from_gateway_communications(name, value)
                    else:
                        self._States.set_from_gateway_communications(opt1, message['payload'])
                elif component_name == 'gateways':
                    if opt1 == 'online':
                        # print("setting gw %s as online" % source_gw_id)
                        self.gateways[source_gw_id].com_status = 'online'
                        reactor.callLater(random_int(2, .8), self.send_all_info, destination_gw=source_gw_id)
                    elif opt1 == 'offline':
                        self.gateways[source_gw_id].com_status = 'offline'
            except Exception as e:  # catch anything here...so can display details.
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.format_exc())
                logger.error("--------------------------------------------------------")

    def incoming_data_device_command(self, src_gateway_id, message):
        """
        Handles incoming device commands.

        :param message:
        :return:
        """
        # print("got device_commands")
        payload = message['payload']

        def do_device_command(self, device_command):
            device = self._Devices.get(device_command['device_id'])
            # print("do_device_command")
            if device.gateway_id != self.gateway_id and self.is_master is not True:  # if we are not a master, we don't care!
                # print("do_device_command..skipping due to not local gateway and not a master: %s" % self.is_master)
                # print("dropping device command..  dest gw: %s" % device_command['gateway_id'])
                # print("dropping device command..  self.gateway_id: %s" % self.gateway_id)
                return
            device_command['device'] = device
            device_command['_source'] = 'gateway_coms'
            self._Devices.add_device_command(device_command)

        if isinstance(payload['device_command'], list):
            for device_command in payload['device_command']:
                do_device_command(self, device_command)
        else:
            do_device_command(self, payload['device_command'])

    def incoming_data_device_command_status(self, src_gateway_id, message):
        """
        Handles incoming device commands.

        :param message:
        :return:
        """
        payload = message['payload']

        if payload['request_id'] not in self._Devices.device_commands:
            self.publish_request(src_gateway_id, 'lib/device_commands/%s' % payload['request_id'], "")
        self._Devices.update_device_command(src_gateway_id,
                                            payload['request_id'],
                                            payload['log_time'],
                                            payload['status'],
                                            payload['message'])

    def incoming_data_notification(self, src_gateway_id, message):
        """
        Handles incoming device status.

        :param message:
        :return:
        """
        payload = message['payload']
        payload['status_source'] = 'gateway_coms'

    def incoming_data_device_status(self, src_gateway_id, message):
        """
        Handles incoming device status.

        :param message:
        :return:
        """
        payload = message['payload']
        payload['status_source'] = 'gateway_coms'
        # print("gateawy got device status: %s" % payload)
        try:
            device = self._Devices[payload['device_id']]
        except Exception:
            logger.warn("Local gateway doesn't have a local copy of the device. Perhaps reboot this gateway.")
            return
        device.set_status_from_gateway_communications(payload)

    def _atoms_set_(self, **kwargs):
        """
        Publish a new atom, if it's from ourselves.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return

        if kwargs['gateway_id'] != self.gateway_id:
            return

        self.publish_data('all', "lib/atoms/" + kwargs['key'], kwargs['value_full'])

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
        if self.gateway_id != device_command['source_gateway_id']:
            return

        message = {
            'state': 'new',
            'device_command': device_command
        }

        topic = "lib/device_commands/" + device_command['request_id']
        # print("sending _device_command_: %s -> %s" % (topic, message))
        self.publish_data('all', topic, message)

    def _device_command_status_(self, **kwargs):
        """
        A new command for a device has been sent. This is used to tell other gateways that either a local device
        is about to do something, other another gateway should do something.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return

        device_command = kwargs['device_command']
        if self.gateway_id != device_command.source_gateway_id:
            return

        history = device_command.history[-1]
        message = {
            'request_id': kwargs['device_command'].request_id,
            'log_time': history[0],
            'status': history[1],
            'message': history[2],
        }

        topic = "lib/device_command_status/" + device_command.request_id
        # print("sending _device_command_: %s -> %s" % (topic, message))
        self.publish_data('all', topic, message)

    def _device_status_(self, **kwargs):
        """
        Publish a new state, if it's from ourselves.

        :param kwargs:
        :return:
        """
        # print("_device_status_: %s" % kwargs['command'])
        if self.ok_to_publish_updates is False:
            return
        device = kwargs['device']
        device_id = device.device_id

        # print("checking if i should send this device_status.  %s != %s" % (self.gateway_id, device.gateway_id))
        if self.gateway_id != device.gateway_id:
            return

        command = kwargs['command']
        # print("device status command: %s" % command)
        if command is not None:
            command_id = command.command_id
        else:
            command_id = None

        previous_status = kwargs['previous_status']
        if previous_status is not None:
            previous_status_out = previous_status.asdict()
        else:
            previous_status_out = None

        message = {
            'device_id': device_id,
            'command_id': command_id,
            'status': kwargs['status'].asdict(),
            'previous_status': previous_status_out,
            'request_id': kwargs['request_id'],
            'reported_by': kwargs['reported_by'],
            'gateway_id': kwargs['gateway_id']
        }

        topic = "lib/device_status/" + device_id
        # print("sending _device_status_: %s -> %s" % (topic, message))
        self.publish_data('all', topic, message)

    def _notification_add_(self, **kwargs):
        """
        Publish a new notification, if it's from ourselves.

        :param kwargs:
        :return:
        """
        # print("_device_status_: %s" % kwargs['command'])
        if self.ok_to_publish_updates is False:
            return

        notice = kwargs['notification']
        if notice.local is True:
            return

        # print("checking if i should send this device_status.  %s != %s" % (self.gateway_id, device.gateway_id))
        if self.gateway_id != notice.gateway_id:
            return

        message = {
            'action': 'add',
            'notice': notice,
        }

        topic = "lib/notification/" + notice['id']
        # print("sending _device_status_: %s -> %s" % (topic, message))
        self.publish_data('all', topic, message)

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

        # print("checking if i should send this device_status.  %s != %s" % (self.gateway_id, device.gateway_id))
        if self.gateway_id != notice['gateway_id']:
            return

        message = {
            'action': 'delete',
            'id': notice['id'],
        }

        topic = "lib/notification/" + notice['id']
        # print("sending _device_status_: %s -> %s" % (topic, message))
        self.publish_data('all', topic, message)

    def _states_set_(self, **kwargs):
        """
        Publish a new state, if it's from ourselves.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return

        gateway_id = kwargs['gateway_id']
        if gateway_id != self.gateway_id:
            return

        # print("gw sending states set: %s" % kwargs['key'])
        self.publish_data('all', "lib/states/" + kwargs['key'], kwargs['value_full'])

    def publish_request(self, dest_gw, topic, message):
        if dest_gw != 'all' and  dest_gw not in self.gateways:
            logger.info("Something requested gateway coms-request, but there's no gateway: {dest_gw}", dest_gw=dest_gw)
            return

        final_topic = '%s/%s' % (dest_gw, topic)
        self.gateways[self.gateway_id].last_communications.append({
            'time': time(),
            'direction': 'sent',
            'topic': final_topic,
        })
        if dest_gw != 'all':
            self.gateways[dest_gw].last_communications.append({
                'time': time(),
                'direction': 'sent',
                'topic': final_topic,
            })
        returnable = self.encrypt(message)
        self.mqtt.publish("ybo_gw_req/%s/%s" % (self.gateway_id, final_topic), returnable)

    def publish_data(self, destination_gw, topic, message):
        if destination_gw != 'all' and destination_gw not in self.gateways:
            logger.info("Something requested gateway coms-data, but there's no gateway: {destination_gw}",
                        destination_gw=destination_gw)
            return

        final_topic = '%s/%s' % (destination_gw, topic)
        self.gateways[self.gateway_id].last_communications.append({
            'time': time(),
            'direction': 'sent',
            'topic': final_topic,
        })
        if destination_gw != 'all':
            self.gateways[destination_gw].last_communications.append({
                'time': time(),
                'direction': 'sent',
                'topic': final_topic,
            })
        outgoing_data = self.encrypt(message)
        # print("gw sending publish data: final topic: ybo_gw/%s/%s" % (self.gateway_id, final_topic))
        self.mqtt.publish("ybo_gw/%s/%s" % (self.gateway_id, final_topic), outgoing_data)

    def send_all_info(self, destination_gw=None, set_ok_to_publish_updates=None):
        # print("gw sending !!!!!!!!!!!!!!!!!!gateways send_all_info: %s - %s" % (destination_gw, self.ok_to_publish_updates))

        self.send_all_atoms(destination_gw)
        self.send_all_devices(destination_gw)
        self.send_all_states(destination_gw)
        if set_ok_to_publish_updates is True:
            self.ok_to_publish_updates = True

    def send_all_atoms(self, destination_gw=None, name=None):
        return_gw = self.get_return_gw(destination_gw)
        # print("gw sending all atoms to: %s" % return_gw)
        if name is None or name == '#':
            self.publish_data(return_gw,  "lib/atoms", self._Atoms.get('#'))
        else:
            self.publish_data(return_gw + 'lib/atoms/%s' % name, self._Atoms.get(name, full=True))

    def send_all_device_commands(self, destination_gw=None, request_id=None):
        return_gw = self.get_return_gw(destination_gw)
        if request_id is None and return_gw == 'all':
            logger.debug("device commands request must have request_id or return gateway id.")
            return
        if request_id is None:
            found_device_commands = self._Devices.get_gateway_device_commands(destination_gw)
            self.publish_data(return_gw, "lib/device_commands", found_device_commands)
        else:
            if request_id in self._Devices.device_commands:
                self.publish_data(return_gw, "lib/device_commands", self._Devices.device_commands[request_id])

    def send_all_devices(self, destination_gw=None, name=None):
        return_gw = self.get_return_gw(destination_gw)
        if name is None:
            found_devices = self._Devices.search(**{"gateway_id": self.gateway_id, 'status': 1})
            devices = {}
            for device in found_devices:
                # print("device: %s" % device)
                devices[device['key']] = device['value'].to_mqtt_coms()
            # print("searching devices: %s" % devices)
            self.publish_data(return_gw, "lib/devices", devices)
        else:
            device = self._Devices[name].to_mqtt_coms()
            self.publish_data(return_gw, 'lib/devices/%s' % name, device)

    def send_all_states(self, destination_gw=None, name=None):
        return_gw = self.get_return_gw(destination_gw)
        if name is None or name == '#':
            self.publish_data(return_gw, 'lib/states', self._States.get('#'))
        else:
            self.publish_data(return_gw, 'lib/states/%s' % name, self._States.get(name, full=True))


    def get_return_gw(self, destination_gw=None):
        if destination_gw is None:
            return 'all'
        return destination_gw

    def test_send(self):
        data = {'hello': 'mom'}
        self.publish_data('all/lib/asdf', data)

    def get_mqtt_passwords(self):
        passwords = {}
        for gateway_id, gateway in self.gateways.items():
            if gateway.mqtt_auth is not None and gateway.mqtt_auth_next is not None:
                passwords[gateway_id] = {
                    'current': gateway.mqtt_auth,
                    'prev': gateway.mqtt_auth_prev,
                    'next': gateway.mqtt_auth_next,
                }
        return passwords

    def get_local(self):
        return self.gateways[self.gateway_id]

    def get_local_id(self):
        """
        For future...
        :return:
        """
        return self.gateway_id

    def get_master_gateway_id(self):
        """
        For future...
        :return:
        """
        if self.master_gateway() is None:
            return self.gateway_id
        return self.master_gateway()

    def get_gateways(self):
        """
        Returns a copy of the gateways list.
        :return:
        """
        return self.gateways.copy()

    def get_meta(self, gateway_requested, gateway=None, limiter=None, status=None):
        """
        Performs the actual search.

        .. note::

           Can use the built in methods below or use get_meta/get to include 'gateway_type' limiter:

            >>> self._Gateways['13ase45']

        or:

            >>> self._Gateways['numeric']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param gateway_requested: The gateway ID or gateway label to search for.
        :type gateway_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the gateway to check for.
        :type status: int
        :return: Pointer to requested gateway.
        :rtype: dict
        """
        if limiter is None:
            limiter = .89

        if limiter > .99999999:
            limiter = .99
        elif limiter < .10:
            limiter = .10

        if status is None:
            status = 1

        if gateway_requested in self.gateways:
            item = self.gateways[gateway_requested]
            # if item.status != status:
            #     raise KeyError("Requested gateway found, but has invalid status: %s" % item.status)
            return item
        else:
            attrs = [
                {
                    'field': 'gateway_id',
                    'value': gateway_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'machine_label',
                    'value': gateway_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'label',
                    'value': gateway_requested,
                    'limiter': limiter,
                }
            ]
            try:
                # logger.debug("Get is about to call search...: %s" % gateway_requested)
                # found, key, item, ratio, others = self._search(attrs, operation="highest")
                found, key, item, ratio, others = do_search_instance(attrs, self.gateways,
                                                                     self.gateway_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest")
                # logger.debug("found gateway by search: others: {others}", others=others)
                if found:
                    return item
                raise KeyError("Gateway not found: %s" % gateway_requested)
            except YomboWarning as e:
                raise KeyError('Searched for %s, but had problems: %s' % (gateway_requested, e))

    def get(self, gateway_requested, limiter=None, status=None):
        """
        Returns a deferred! Looking for a gateway id in memory.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find devices:

            >>> self._Gateways['13ase45']

        or:

            >>> self._Gateways['numeric']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param gateway_requested: The gateway ID or gateway label to search for.
        :type gateway_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the gateway to check for.
        :type status: int
        :return: Pointer to requested gateway.
        :rtype: dict
        """
        try:
            gateway = self.get_meta(gateway_requested, limiter, status)
        except Exception as e:
            logger.warn("Unable to find requested gateway: {gateway}.  Reason: {e}", gateway=gateway_requested, e=e)
            raise YomboWarning("Cannot find requested gateway...")
        return gateway
        #
        # try:
        #     data = yield self._LocalDB.get_gateway(gateway.gateway_id)
        #     return data
        # except YomboWarning as e:
        #     raise KeyError('Cannot find gateway (%s) in database: %s' % (gateway_requested, e))

    def search(self, criteria):
        """
        Search for gateways based on a dictionary of key=value pairs.

        :param criteria:
        :return:
        """
        results = {}
        for gateway_id, gateway in self.gateways.items():
            for key, value in criteria.items():
                if key not in self.gateway_search_attributes:
                    continue
                if value == getattr(gateway, key):
                    results[gateway_id] = gateway
        return results

    @inlineCallbacks
    def add_gateway(self, api_data, source=None, **kwargs):
        """
        Add a new gateway. Updates Yombo servers and creates a new entry locally.

        :param api_data:
        :param kwargs:
        :return:
        """
        if 'gateway_id' not in api_data:
            api_data['gateway_id'] = self.gateway_id

        if source != 'amqp':
            gateway_results = yield self._YomboAPI.request('POST', '/v1/gateway', api_data)

            if gateway_results['code'] > 299:
                results = {
                    'status': 'failed',
                    'msg': "Couldn't add gateway",
                    'apimsg': gateway_results['content']['message'],
                    'apimsghtml': gateway_results['content']['html_message'],
                }
                return results
            gateway_id = gateway_results['data']['id']

        results = {
            'status': 'success',
            'msg': "Gateway added.",
            'gateway_id': gateway_id,
        }
        new_gateway = gateway_results['data']
        self.import_gateway(new_gateway)
        return results

    @inlineCallbacks
    def edit_gateway(self, gateway_id, api_data, called_from_gateway=None, source=None, **kwargs):
        """
        Edit a gateway at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """

        gateway_results = yield self._YomboAPI.request('PATCH', '/v1/gateway/%s' % (gateway_id), api_data)
        # print("module edit results: %s" % module_results)

        if gateway_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit gateway",
                'apimsg': gateway_results['content']['message'],
                'apimsghtml': gateway_results['content']['html_message'],
            }
            return results

        results = {
            'status': 'success',
            'msg': "Device type edited.",
            'gateway_id': gateway_results['data']['id'],
        }

        gateway = self.gateways[gateway_id]
        if called_from_gateway is not True:
            gateway.update_attributes(api_data)
            gateway.save_to_db()
        return results

    @inlineCallbacks
    def delete_gateway(self, gateway_id, **kwargs):
        """
        Delete a gateway at the Yombo server level, not at the local gateway level.

        :param gateway_id: The gateway ID to delete.
        :param kwargs:
        :return:
        """
        gateway_results = yield self._YomboAPI.request('DELETE', '/v1/gateway/%s' % gateway_id)

        if gateway_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete gateway",
                'apimsg': gateway_results['content']['message'],
                'apimsghtml': gateway_results['content']['html_message'],
            }
            return results

        results = {
            'status': 'success',
            'msg': "Gateway deleted.",
            'gateway_id': gateway_id,
        }
        return results

    @inlineCallbacks
    def enable_gateway(self, gateway_id, **kwargs):
        """
        Enable a gateway at the Yombo server level, not at the local gateway level.

        :param gateway_id: The gateway ID to enable.
        :param kwargs:
        :return:
        """
        #        print "enabling gateway: %s" % gateway_id
        api_data = {
            'status': 1,
        }

        gateway_results = yield self._YomboAPI.request('PATCH', '/v1/gateway/%s' % gateway_id, api_data)

        if gateway_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't enable gateway",
                'apimsg': gateway_results['content']['message'],
                'apimsghtml': gateway_results['content']['html_message'],
            }
            return results

        results = {
            'status': 'success',
            'msg': "Gateway enabled.",
            'gateway_id': gateway_id,
        }
        return results

    @inlineCallbacks
    def disable_gateway(self, gateway_id, **kwargs):
        """
        Enable a gateway at the Yombo server level, not at the local gateway level.

        :param gateway_id: The gateway ID to disable.
        :param kwargs:
        :return:
        """
#        print "disabling gateway: %s" % gateway_id
        api_data = {
            'status': 0,
        }

        gateway_results = yield self._YomboAPI.request('PATCH', '/v1/gateway/%s' % gateway_id, api_data)
        # print("disable gateway results: %s" % gateway_results)

        if gateway_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable gateway",
                'apimsg': gateway_results['content']['message'],
                'apimsghtml': gateway_results['content']['html_message'],
            }
            return results

        results = {
            'status': 'success',
            'msg': "Gateway disabled.",
            'gateway_id': gateway_id,
        }
        return results

    def full_list_gateways(self):
        """
        Return a list of dictionaries representing all known commands to this gateway.
        :return:
        """
        items = []
        for gateway_id, gateway in self.gateways.items():
            items.append(gateway.asdict())
        return items


class Gateway:
    """
    A class to manage a single gateway.
    :ivar gateway_id: (string) The unique ID.
    :ivar label: (string) Human label
    :ivar machine_label: (string) A non-changable machine label.
    :ivar category_id: (string) Reference category id.
    :ivar input_regex: (string) A regex to validate if user input is valid or not.
    :ivar always_load: (int) 1 if this item is loaded at startup, otherwise 0.
    :ivar status: (int) 0 - disabled, 1 - enabled, 2 - deleted
    :ivar public: (int) 0 - private, 1 - public pending approval, 2 - public
    :ivar created_at: (int) EPOCH time when created
    :ivar updated: (int) EPOCH time when last updated
    """

    def __init__(self, parent, gateway):
        """
        Setup the gateway object using information passed in.

        :param gateway: An gateway with all required items to create the class.
        :type gateway: dict

        """
        logger.debug("gateway info: {gateway}", gateway=gateway)
        self._Parent = parent
        self.gateway_id = gateway['id']
        self.machine_label = gateway['machine_label']

        # below are configure in update_attributes()
        self.is_master = None
        self.master_gateway = None
        self.label = None
        self.description = None
        self.mqtt_auth = None
        self.mqtt_auth_prev = None
        self.mqtt_auth_next = None
        self.mqtt_auth_last_rotate = None
        self.fqdn = None
        self.internal_ipv4 = None
        self.external_ipv4 = None
        self.internal_port = None
        self.external_port = None
        self.internal_secure_port = None
        self.external_secure_port = None
        self.internal_mqtt = None
        self.internal_mqtt_le = None
        self.internal_mqtt_ss = None
        self.internal_mqtt_ws = None
        self.internal_mqtt_ws_le = None
        self.internal_mqtt_ws_ss = None
        self.external_mqtt = None
        self.external_mqtt_le = None
        self.external_mqtt_ss = None
        self.external_mqtt_ws = None
        self.external_mqtt_ws_le = None
        self.external_mqtt_ws_ss = None
        self.status = None
        self.updated_at = None
        self.created_at = None

        # communications information
        self.last_communications = deque([], 30)  # stores times and topics of the last few communications

        self.update_attributes(gateway)

    def update_attributes(self, gateway):
        """
        Sets various values from a gateway dictionary. This can be called when either new or
        when updating.

        :param gateway:
        :return: 
        """
        if 'gateway_id' in gateway:
            self.gateway_id = gateway['gateway_id']
        if 'is_master' in gateway:
            self.is_master = gateway['is_master']
        if 'master_gateway' in gateway:
            self.master_gateway = gateway['master_gateway']
        if 'label' in gateway:
            self.label = gateway['label']
        if 'description' in gateway:
            self.description = gateway['description']
        if 'mqtt_auth' in gateway:
            self.mqtt_auth = gateway['mqtt_auth']
        if 'mqtt_auth_next' in gateway:
            self.mqtt_auth_next = gateway['mqtt_auth_next']
        if 'internal_ipv4' in gateway:
            self.internal_ipv4 = gateway['internal_ipv4']
        if 'external_ipv4' in gateway:
            self.external_ipv4 = gateway['external_ipv4']
        if 'internal_port' in gateway:
            self.internal_port = gateway['internal_port']
        if 'external_port' in gateway:
            self.external_port = gateway['external_port']
        if 'fqdn' in gateway:
            self.fqdn = gateway['fqdn']
        if 'internal_secure_port' in gateway:
            self.internal_secure_port = gateway['internal_secure_port']
        if 'external_secure_port' in gateway:
            self.external_secure_port = gateway['external_secure_port']
        if 'internal_mqtt' in gateway:
            self.internal_mqtt = gateway['internal_mqtt']
        if 'internal_mqtt_le' in gateway:
            self.internal_mqtt_le = gateway['internal_mqtt_le']
        if 'internal_mqtt_ss' in gateway:
            self.internal_mqtt_ss = gateway['internal_mqtt_ss']
        if 'internal_mqtt_ws' in gateway:
            self.internal_mqtt_ws = gateway['internal_mqtt_ws']
        if 'internal_mqtt_ws_le' in gateway:
            self.internal_mqtt_ws_le = gateway['internal_mqtt_ws_le']
        if 'internal_mqtt_ws_ss' in gateway:
            self.internal_mqtt_ws_ss = gateway['internal_mqtt_ws_ss']
        if 'external_mqtt' in gateway:
            self.external_mqtt = gateway['external_mqtt']
        if 'external_mqtt_le' in gateway:
            self.external_mqtt_le = gateway['external_mqtt_le']
        if 'external_mqtt_ss' in gateway:
            self.external_mqtt_ss = gateway['external_mqtt_ss']
        if 'external_mqtt_ws' in gateway:
            self.external_mqtt_ws = gateway['external_mqtt_ws']
        if 'external_mqtt_ws_le' in gateway:
            self.external_mqtt_ws_le = gateway['external_mqtt_ws_le']
        if 'external_mqtt_ws_ss' in gateway:
            self.external_mqtt_ws_ss = gateway['external_mqtt_ws_ss']
        if 'status' in gateway:
            self.status = gateway['status']
        if 'created_at' in gateway:
            self.created_at = gateway['created_at']
        if 'updated_at' in gateway:
            self.updated_at = gateway['updated_at']

    def __str__(self):
        """
        Print a string when printing the class.  This will return the gateway id so that
        the gateway can be identified and referenced easily.
        """
        return self.gateway_id

    def asdict(self):
        """
        Export gateway variables as a dictionary.
        """
        return {
            'gateway_id': str(self.gateway_id),
            'fqdn': str(self.fqdn),
            'is_master': self.is_master,
            'master_gateway': str(self.master_gateway),
            'machine_label': str(self.machine_label),
            'label': str(self.label),
            'description': str(self.description),
            'status': int(self.status),
            'created_at': int(self.created_at),
            'updated_at': int(self.updated_at),
        }

    def __repl__(self):
        """
        Export gateway variables as a dictionary.
        """
        return {
            'gateway_id': str(self.gateway_id),
            'fqdn': str(self.fqdn),
            'is_master': self.is_master,
            'master_gateway': str(self.master_gateway),
            'machine_label': str(self.machine_label),
            'label': str(self.label),
            'description': str(self.description),
            'status': int(self.status),
            'created_at': int(self.created_at),
            'updated_at': int(self.updated_at),
        }

    @property
    def com_status(self):
        if self.gateway_id == self._Parent.gateway_id:
            return 'online'

        if self.gateway_id in self._Parent.gateway_status:
            return self._Parent.gateway_status[self.gateway_id]['com_status']
        else:
            return None

    @com_status.setter
    def com_status(self, val):
        if self.gateway_id == self._Parent.gateway_id:
            return

        if self.gateway_id not in self._Parent.gateway_status:
            self._Parent.gateway_status[self.gateway_id] = {
                'com_status': val,
                'last_scene': None,
            }
        else:
            self._Parent.gateway_status[self.gateway_id]['com_status'] = val

    @property
    def last_scene(self):
        if self.gateway_id == self._Parent.gateway_id:
            return time()

        if self.gateway_id in self._Parent.gateway_status:
            return self._Parent.gateway_status[self.gateway_id]['last_scene']
        else:
            return None

    @last_scene.setter
    def last_scene(self, val):
        if self.gateway_id == self._Parent.gateway_id:
            return

        if self.gateway_id not in self._Parent.gateway_status:
            self._Parent.gateway_status[self.gateway_id] = {
                'com_status': None,
                'last_scene': val,
            }
        else:
            self._Parent.gateway_status[self.gateway_id]['last_scene'] = val
