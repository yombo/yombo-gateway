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
from copy import deepcopy
from time import time
import socket
import traceback

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.lib.gateways.gateway import Gateway
from yombo.lib.gateways.mqtt import mqtt_incoming, publish_data, send_all_info
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import do_search_instance, global_invoke_all, random_int, sleep, random_string
from yombo.constants import VERSION

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
        return "Yombo gateway library"

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
                'fqdn': '127.0.0.1',
                'version': VERSION,
            })
        self.import_gateway({
            'id': 'cluster',
            'is_master': False,
            'master_gateway': '',
            'machine_label': 'cluster',
            'label': 'Cluster',
            'description': 'All gateways in a cluster.',
            'fqdn': '127.0.0.1',
            'version': VERSION,
        })
        yield self._load_gateways_from_database()

        # now local the master, on or off network.
        self.master_mqtt_host = None
        self.master_mqtt_ssl = None
        self.master_mqtt_port = None
        self.master_websock_ssl = None
        self.master_websock_port = None

        if self._Loader.operating_mode == 'run':
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

    def _start_(self, **kwargs):
        self.library_phase = 3
        if self._States['loader.operating_mode'] != 'run':
            return
        self.mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming_wrapper,
                                   client_id='Yombo-gateways-%s' % self.gateway_id)
        self.mqtt.subscribe("ybo_gw_req/+/all/#")
        self.mqtt.subscribe("ybo_gw_req/+/%s/#" % self.gateway_id)
        self.mqtt.subscribe("ybo_gw/+/all/#")
        self.mqtt.subscribe("ybo_gw/+/%s/#" % self.gateway_id)
        self.mqtt.subscribe("to_yombo/#")

    def _started_(self, **kwargs):
        self.library_phase = 4
        if self._States['loader.operating_mode'] != 'run':
            return
        publish_data(self, 'gw', "all", "lib/gateway/online", "")
        reactor.callLater(3, send_all_info, self, set_ok_to_publish_updates=True)

        self.ping_gateways_loop = LoopingCall(self.ping_gateways)
        self.ping_gateways_loop.start(random_int(120, .1), False)

    @inlineCallbacks
    def _stop_(self, **kwargs):
        """
        Cleans up any pending deferreds.
        """
        if hasattr(self, 'mqtt'):
            if self.mqtt is not None:
                publish_data(self, 'gw', "all", "lib/gateway/offline", "")
                yield sleep(0.05)
        if hasattr(self, 'load_deferred'):
            if self.load_deferred is not None and self.load_deferred.called is False:
                self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    # def _configuration_set_(self, **kwargs):
    #     """
    #     Receive configuration updates and adjust as needed.
    #
    #     :param kwargs: section, option(key), value
    #     :return:
    #     """
    #     section = kwargs['section']
    #     option = kwargs['option']
    #     value = kwargs['value']
    #
    #     if section == 'core':
    #         if option == 'label':
    #             self.gateways['local'] = value
    #             if self.gateway_id != 'local':
    #                 self.gateways[self.gateway_id] = value

    def mqtt_incoming_wrapper(self, topic, raw_payload, qos, retain):
        """ Simple wrapper to add reference to this library."""
        mqtt_incoming(self, topic, raw_payload, qos, retain)

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
            request_id = publish_data(self, 'req', gateway_id, "system/ping", message)
            self.gateways[gateway_id].ping_request_id = request_id
            self.gateways[gateway_id].ping_request = current_time

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
        if gateway_id == self.gateway_id:
            gateway['version'] = VERSION
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

        message = deepcopy(kwargs['value_full'])
        message['key'] = kwargs['key']
        publish_data(self, 'gw', 'all', "lib/atom/" + kwargs['key'], message)

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
        if device_command['source_gateway_id'] != self.gateway_id:
            return

        message = {
            'state': 'new',
            'device_command': device_command
        }

        topic = "lib/device_command"
        publish_data(self, 'gw', 'all', topic, message)

    def _device_command_status_(self, **kwargs):
        """
        A device command has changed status. Update everyone else.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return

        device_command = kwargs['device_command']
        if self.gateway_id != device_command.source_gateway_id:
            return

        history = device_command.last_history()
        message = {
            'request_id': kwargs['device_command'].request_id,
            'log_time': history['time'],
            'status': history['status'],
            'message': history['msg'],
        }

        topic = "lib/device_command_status/" + device_command.request_id
        # print("sending _device_command_: %s -> %s" % (topic, message))
        publish_data(self, 'gw', 'all', topic, message)

    def _device_status_(self, **kwargs):
        """
        Publish a new state, if it's from ourselves.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return
        device = kwargs['device']
        device_id = device.device_id

        if self.gateway_id != device.gateway_id:
            return

        topic = "lib/device_status"
        msg = {device_id: kwargs['event']}
        publish_data(self, 'gw', 'all', topic, kwargs['event'])

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

        # print("checking if i should send this device_status.  %s != %s" % (self.gateway_id, device.gateway_id))
        if self.gateway_id != notice.gateway_id:
            return

        message = {
            'action': 'add',
            'notice': kwargs['event'],
        }

        topic = "lib/notification/" + notice.notification_id
        # print("sending _device_status_: %s -> %s" % (topic, message))
        publish_data(self, 'gw', 'all', topic, message)

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
            'notice': kwargs['event'],
        }

        topic = "lib/notification/" + notice.notification_id
        # print("sending _device_status_: %s -> %s" % (topic, message))
        publish_data(self, 'gw', 'all', topic, message)

    def _states_set_(self, **kwargs):
        """
        Publish a new state, if it's from ourselves.

        :param kwargs:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return

        gateway_id = kwargs['gateway_id']
        if gateway_id != self.gateway_id and gateway_id not in ('global', 'cluster'):
            return

        message = deepcopy(kwargs['value_full'])
        message['key'] = kwargs['key']
        publish_data(self, 'gw', 'all', "lib/state/" + kwargs['key'], message)

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

        if api_data['machine_label'].lower() == 'cluster':
            return {
                'status': 'failed',
                'msg': "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
                'apimsg': "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
                'apimsghtml': "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
            }
        if api_data['label'].lower() == 'cluster':
            return {
                'status': 'failed',
                'msg': "Couldn't add gateway: label cannot be 'cluster' or 'all'",
                'apimsg': "Couldn't add gateway: label cannot be 'cluster' or 'all'",
                'apimsghtml': "Couldn't add gateway: label cannot be 'cluster' or 'all'",
            }
        if source != 'amqp':
            try:
                if 'session' in kwargs:
                    session = kwargs['session']
                else:
                    session = None

                gateway_results = yield self._YomboAPI.request('POST', '/v1/gateway',
                                                               api_data,
                                                               session=session)
            except YomboWarning as e:
                return {
                    'status': 'failed',
                    'msg': "Couldn't add gateway: %s" % e.message,
                    'apimsg': "Couldn't add gateway: %s" % e.message,
                    'apimsghtml': "Couldn't add gateway: %s" % e.html_message,
                }
            gateway_id = gateway_results['data']['id']

        new_gateway = gateway_results['data']
        self.import_gateway(new_gateway)
        return {
            'status': 'success',
            'msg': "Gateway added.",
            'gateway_id': gateway_id,
        }

    @inlineCallbacks
    def edit_gateway(self, gateway_id, api_data, called_from_gateway=None, source=None, **kwargs):
        """
        Edit a gateway at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        if api_data['machine_label'].lower() == 'cluster':
            return {
                'status': 'failed',
                'msg': "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
                'apimsg': "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
                'apimsghtml': "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
            }
        if api_data['label'].lower() == 'cluster':
            return {
                'status': 'failed',
                'msg': "Couldn't add gateway: label cannot be 'cluster' or 'all'",
                'apimsg': "Couldn't add gateway: label cannot be 'cluster' or 'all'",
                'apimsghtml': "Couldn't add gateway: label cannot be 'cluster' or 'all'",
            }
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            gateway_results = yield self._YomboAPI.request('PATCH', '/v1/gateway/%s' % (gateway_id),
                                                           api_data,
                                                           session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't edit gateway: %s" % e.message,
                'apimsg': "Couldn't edit gateway: %s" % e.message,
                'apimsghtml': "Couldn't edit gateway: %s" % e.html_message,
            }

        gateway = self.gateways[gateway_id]
        if called_from_gateway is not True:
            gateway.update_attributes(api_data)
            gateway.save_to_db()

        return {
            'status': 'success',
            'msg': "Device type edited.",
            'gateway_id': gateway_results['data']['id'],
        }

    @inlineCallbacks
    def delete_gateway(self, gateway_id, **kwargs):
        """
        Delete a gateway at the Yombo server level, not at the local gateway level.

        :param gateway_id: The gateway ID to delete.
        :param kwargs:
        :return:
        """
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            yield self._YomboAPI.request('DELETE', '/v1/gateway/%s' % gateway_id,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't delete gateway: %s" % e.message,
                'apimsg': "Couldn't delete gateway: %s" % e.message,
                'apimsghtml': "Couldn't delete gateway: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Gateway deleted.",
            'gateway_id': gateway_id,
        }

    @inlineCallbacks
    def enable_gateway(self, gateway_id, **kwargs):
        """
        Enable a gateway at the Yombo server level, not at the local gateway level.

        :param gateway_id: The gateway ID to enable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 1,
        }

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            yield self._YomboAPI.request('PATCH', '/v1/gateway/%s' % gateway_id,
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't enable gateway: %s" % e.message,
                'apimsg': "Couldn't enable gateway: %s" % e.message,
                'apimsghtml': "Couldn't enable gateway: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Gateway enabled.",
            'gateway_id': gateway_id,
        }

    @inlineCallbacks
    def disable_gateway(self, gateway_id, **kwargs):
        """
        Enable a gateway at the Yombo server level, not at the local gateway level.

        :param gateway_id: The gateway ID to disable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 0,
        }

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            yield self._YomboAPI.request('PATCH', '/v1/gateway/%s' % gateway_id,
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't disable gateway: %s" % e.message,
                'apimsg': "Couldn't disable gateway: %s" % e.message,
                'apimsghtml': "Couldn't disable gateway: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Gateway disabled.",
            'gateway_id': gateway_id,
        }

    def full_list_gateways(self):
        """
        Return a list of dictionaries representing all known commands to this gateway.
        :return:
        """
        items = []
        for gateway_id, gateway in self.gateways.items():
            if gateway.machine_label in ('cluster', 'all'):
                continue
            items.append(gateway.asdict())
        return items
