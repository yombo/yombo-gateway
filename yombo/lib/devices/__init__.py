# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/modules/devices/>`_

The devices library is primarily responsible for:
 
* Keeping track of all devices.
* Maintaining device state.
* Routing commands to modules for processing.
* Managing delay commands to send later.

The device (singular) class represents one device. This class has many functions
that help with utilizing the device. When possible, this class should be used for
controlling devices and getting/setting/querying status. The device class maintains
the current known device state.  Any changes to the device state are periodically
saved to the local database.

To send a command to a device is simple.

*Usage**:

.. code-block:: python

   # Three ways to send a command to a device. Going from easiest method, but less assurance of correct command
   # to most assurance.

   # Lets turn on every device this module manages.
   for device in self._Devices:
       self.Devices[device].command(cmd='off')

   # Lets turn off every every device, using a very specific command id.
   for device in self._Devices:
       self.Devices[device].command(cmd='js83j9s913')  # Made up id, but can be same as off

   # Turn off the christmas tree.
   self._Devices.command('christmas tree', 'off')

   # Get devices by device type:
   deviceList = self._Devices.search(device_type='x10_appliance')  # Can search on any device attribute

   # Turn on all x10 lights off (regardless of house / unit code)
   allX10Lamps = self._DeviceTypes.devices_by_device_type('x10_light')
   # Turn off all x10 lamps
   for lamp in allX10Lamps:
       lamp.command('off')

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries

try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from hashlib import sha1
from time import time
from collections import OrderedDict

# Import 3rd-party libs
import yombo.ext.six as six

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from ._device import Device
from ._device_command import Device_Command
from yombo.core.exceptions import YomboDeviceError, YomboWarning, YomboHookStopProcessing
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import split, global_invoke_all, search_instance, do_search_instance, random_int, get_public_gw_id
logger = get_logger('library.devices')


class Devices(YomboLibrary):
    """
    Manages all devices and provides the primary interaction interface. The
    primary functions developers should use are:
        * :py:meth:`__getitem__ <Devices.__getitem__>` - Get a pointer to a device, using self._Devices as a dictionary of objects.
        * :py:meth:`command <Devices.command>` - Send a command to a device.
        * :py:meth:`search <Devices.search>` - Get a pointer to a device, using device_id or device label.
    """

    def __contains__(self, device_requested):
        """
        .. note:: The device must be enabled to be found using this method. Use :py:meth:`get <Devices.get>`
           to set status allowed.

        Checks to if a provided device label, device machine label, or device id exists.

            >>> if '137ab129da9318' in self._Devices:  #by id

        or:

            >>> if 'living room light' in self._Devices:  #by label

        :raises YomboWarning: Raised when request is malformed.
        :param device_requested: The device ID or label to search for.
        :type device_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(device_requested)
            return True
        except:
            return False

    def __getitem__(self, device_requested):
        """
        .. note:: The device must be enabled to be found using this method. Use :py:meth:`get <Devices.get>`
           to set status allowed.

        Finds the device requested by device label, device machine label, or device id exists.

            >>> my_light = self._Devices['137ab129da9318']  #by id

        or:

            >>> my_light = self._Devices['living room light']  #by name

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param device_requested: The device ID, machine_label, or label to search for.
        :type device_requested: string
        :return: A pointer to the device type instance.
        :rtype: instance
        """
        return self.get(device_requested)

    def __setitem__(self, device_requested, value):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        :param device_requested: The atom key to replace the value for.
        :type device_requested: string
        """
        raise Exception("Not allowed.")

    def __delitem__(self, device_requested):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        :param device_requested: 
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter devices. """
        return self.devices.__iter__()

    def __len__(self):
        """
        Returns an int of the number of device configured.
        
        :return: The number of devices configured.
        :rtype: int
        """
        return len(self.devices)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo devices library"

    def keys(self):
        """
        Returns the keys (device ID's) that are configured.
        
        :return: A list of device IDs. 
        :rtype: list
        """
        return list(self.devices.keys())

    def items(self):
        """
        Gets a list of tuples representing the devices configured.
        
        :return: A list of tuples.
        :rtype: list
        """
        return list(self.devices.items())

    def iteritems(self):
        return iter(self.devices.items())

    def iterkeys(self):
        return iter(self.devices.keys())

    def itervalues(self):
        return iter(self.devices.values())

    def values(self):
        return list(self.devices.values())

    def _init_(self):
        """
        Sets up basic attributes.
        """
        self._AutomationLibrary = self._Loader.loadedLibraries['automation']
        self._VoiceCommandsLibrary = self._Loader.loadedLibraries['voicecmds']

        self.devices = {}
        self.device_search_attributes = ['device_id', 'device_type_id', 'machine_label', 'label', 'description',
            'pin_required', 'pin_code', 'pin_timeout', 'voice_cmd', 'voice_cmd_order', 'statistic_label', 'status',
            'created', 'updated', 'updated_srv']

        self.gwid = self._Configs.get("core", "gwid")

        # used to store delayed queue for restarts. It'll be a bare, dehydrated version.
        # store the above, but after hydration.
        self.device_commands = {}  # tracks commands being sent to devices. Also tracks if a command is delayed
        self.device_commands_persistent = {}  # tracks if a request should update any existing commands. For example
        self.clean_device_commands_loop = None
        # the automation system can always request the same command to be performed but ensure only one is
          # is n the queue between restarts.

        self.startup_queue = {}  # Place device commands here until we are ready to process device commands
        self.processing_commands = False

    @inlineCallbacks
    def _started_(self):
        """
        Loads devices from the database and imports them.
        :return: 
        """
        yield self._load_devices_from_database()
        yield self._load_device_commands()

        self.clean_device_commands_loop = LoopingCall(self.clean_device_commands)
        self.clean_device_commands_loop.start(random_int(3600, .15))

        if self._Atoms['loader.operation_mode'] == 'run':
            self.mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming, client_id='devices')
            self.mqtt.subscribe("yombo/devices/+/get")
            self.mqtt.subscribe("yombo/devices/+/cmd")

    def _modules_started_(self):
        for request_id, device_command in self.device_commands.items():
            device_command.start()

    def _unload_(self):
        """
        Save any device commands that need to be saved.
        :return: 
        """
        for request_id, device_command in self.device_commands.items():
            device_command.save_to_db(True)

    def _reload_(self):
        return self._load_()

    def _modules_prestarted_(self):
        """
        On start, sends all queued messages. Then, check delayed messages for any messages that were missed. Send
        old messages and prepare future messages to run.
        """
        self.processing_commands = True
        for command, request in self.startup_queue.items():
            self.command(request['device_id'], request['command_id'], not_before=request['not_before'],
                    max_delay=request['max_delay'], **request['kwargs'])
        self.startup_queue.clear()

    # def _statistics_lifetimes_(self, **kwargs):
    #     """
    #     For devices, we track statistics down to the nearest 5 minutes, and keep for 1 year.
    #     """
    #     return {'devices.#': {'size': 300, 'lifetime': 365},
    #             'energy.#': {'size': 300, 'lifetime': 365}}
    #     # we don't keep 6h averages.

    @inlineCallbacks
    def _load_devices_from_database(self):
        """
        Loads devices from database and sends them to :py:meth:`import_device <Devices.import_device>`
        
        This can be triggered either on system startup or when new/updated devices have been saved to the
        database and we need to refresh existing devices.
        """
        devices = yield self._LocalDB.get_devices()
        # logger.debug("Loading devices:::: {devices}", devices=devices)
        if len(devices) > 0:
            for record in devices:
                record = record.__dict__
                if record['energy_map'] is not None:
                    record['energy_map'] = json.loads(str(record['energy_map']))
                logger.debug("Loading device: {record}", record=record)
                yield self.import_device(record)

    def sorted(self, key=None):
        """
        Returns an OrderedDict, sorted by key.  If key is not set, then default is 'label'.

        :param key: Attribute contained in a device to sort by.
        :type key: str
        :return: All devices, sorted by key.
        :rtype: OrderedDict
        """
        if key is None:
            key = 'label'
        return OrderedDict(sorted(iter(self.devices.items()), key=lambda i: i[1][key]))

    @inlineCallbacks
    def import_device(self, device, test_device=None):  # load or re-load if there was an update.
        """
        Add a new device to memory or update an existing device.

        **Hooks called**:

        * _device_before_load_ : If added, sends device dictionary as 'device'
        * _device_before_update_ : If updated, sends device dictionary as 'device'
        * _device_loaded_ : If added, send the device instance as 'device'
        * _device_updated_ : If updated, send the device instance as 'device'

        :param device: A dictionary of items required to either setup a new device or update an existing one.
        :type device: dict
        :param test_device: Used for unit testing.
        :type test_device: bool
        :returns: Pointer to new device. Only used during unittest
        """
        if test_device is None:
            test_device = False

        device_id = device["id"]
        if device_id not in self.devices:
            import_state = 'new'
            global_invoke_all('_device_before_load_',
                              **{'device': device})
            device_type = self._DeviceTypes[device['device_type_id']]

            if device_type.platform is None or device_type.platform == "":
                device_type.platform = 'device'
            class_names = device_type.platform.lower()

            class_names = "".join(class_names.split())  # we don't like spaces
            class_names = class_names.split(',')

            # logger.debug("Loading device ({device}), platforms: {platforms}",
            #             device=device['label'],
            #             platforms=class_names)

            class_set = False
            for class_name in class_names:
                if class_name in self._DeviceTypes.platforms:
                    klass = self._DeviceTypes.platforms[class_name]
                    class_set = True
            if class_set is False:
                klass = self._DeviceTypes.platforms['device']
                logger.warn("Using base device class for device '{label}' cannot find any of these requested classes: {class_names}",
                            label=device['label'],
                            class_names=class_names)

            self.devices[device_id] = klass(device, self)

        else:
            import_state = 'update'
            global_invoke_all('_device_before_update_',
                              **{'device': device})
            self.devices[device_id].update_attributes(device)

        yield self.devices[device_id]._init_()

        try:
            self._VoiceCommandsLibrary.add_by_string(device["voice_cmd"], None, device["id"],
                                                     device["voice_cmd_order"])
        except YomboWarning:
            logger.debug("Device {label} has an invalid voice_cmd {voice_cmd}", label=device["label"],
                         voice_cmd=device["voice_cmd"])

        # logger.debug("_add_device: {device}", device=device)

        if import_state == 'new':
            global_invoke_all('_device_loaded_',
                          **{'device': self.devices[device_id]})
        elif import_state == 'update':
            global_invoke_all('_device_updated_',
                              **{'device': self.devices[device_id]})
        # if test_device:
        #            returnValue(self.devices[device_id])

    @inlineCallbacks
    def _load_device_commands(self):
        where = {
            'finished_time': None,
        }

        device_commands = yield self._LocalDB.get_device_commands(where)
        for device_command in device_commands:
            self.device_commands[device_command['request_id']] = Device_Command(device_command, self, start=False)
        returnValue(None)

    @inlineCallbacks
    def clean_device_commands(self):
        """
        Remove old device command requests.
        :return: 
        """
        cur_time = time()
        for request_id in list(self.device_commands.keys()):
            device_command = self.device_commands[request_id]
            if device_command.finished_time > cur_time - (60*45):  # keep 45 minutes worth.
                yield device_command.save_to_db()
                del self.device_commands[request_id]

        # This is split up to incase a new request_id was created....
        for persistent_request_id in list(self.device_commands_persistent.keys()):
            request_id = self.device_commands_persistent[persistent_request_id]
            if request_id not in self.device_commands:
                del self.device_commands_persistent[persistent_request_id]


    def command(self, device, cmd, pin=None, request_id=None, not_before=None, delay=None, max_delay=None, requested_by=None, input=None, **kwargs):
        """
        Tells the device to a command. This in turn calls the hook _device_command_ so modules can process the command
        if they are supposed to.

        If a pin is required, "pin" must be included as one of the arguments. All **kwargs are sent with the
        hook call.

        :raises YomboDeviceError: Raised when:

            - cmd doesn't exist
            - delay or max_delay is not a float or int.

        :raises YomboPinCodeError: Raised when:

            - pin is required but not recieved one.

        :param device: Device ID, machine_label, or Label.
        :type device: str
        :param cmd: Command ID, machine_label, or Label to send.
        :type cmd: str
        :param pin: A pin to check.
        :type pin: str
        :param request_id: Request ID for tracking. If none given, one will be created.
        :type request_id: str
        :param delay: How many seconds to delay sending the command. Not to be combined with 'not_before'
        :type delay: int or float
        :param not_before: An epoch time when the command should be sent. Not to be combined with 'delay'.
        :type not_before: int or float
        :param max_delay: How many second after the 'delay' or 'not_before' can the command be send. This can occur
            if the system was stopped when the command was supposed to be send.
        :type max_delay: int or float
        :param inputs: A list of dictionaries containing the 'input_type_id' and any supplied 'value'.
        :type input: list of dictionaries
        :param kwargs: Any additional named arguments will be sent to the module for processing.
        :type kwargs: named arguments
        :return: The request id.
        :rtype: str
        """
        return self.get(device).command(cmd, pin, request_id, not_before, delay, max_delay, **kwargs)

    def mqtt_incoming(self, topic, payload, qos, retain):
        """
        Processing any incoming MQTT messages we have subscribed to. This allows IoT type connections
        from various external sources.

        * yombo/devices/DEVICEID|DEVICEMACHINELABEL/get Value - Get some attribute
          * Value = state, human, machine, extra
        * yombo/devices/DEVICEID|DEVICEMACHINELABEL/cmd/CMDID|CMDMACHINELABEL Options - Send a command
          * Options - Either a string for a single variable, or json for multiple variables

        Examples: /yombo/devices/get/christmas_tree/cmd/on

        :param topic:
        :param payload:
        :param qos:
        :param retain:
        :return:
        """
        #  0       1       2       3        4
        # yombo/devices/DEVICEID/get|cmd/option
        parts = topic.split('/', 10)
        logger.debug("Yombo Devices got this: {topic} / {parts}", topic=topic, parts=parts)
        payload = payload.lower().strip()

        try:
            device_label = self.get(parts[2].replace("_", " "))
            device = self.get(device_label)
        except YomboDeviceError as e:
            logger.info("Received MQTT request for a device that doesn't exist: %s" % parts[2])
            return
        if parts[3] == 'get':
            status = device.status_history[0]

            if payload == '' or payload == 'all':
                self.mqtt.publish('yombo/devices/%s/status' % device.machine_label, json.dumps(device.status_history[0]))
            elif payload in status:
                self.mqtt.publish('yombo/devices/%s/status/%s' % (device.machine_label, payload), str(getattr(payload, status)))

        # elif parts[3] == 'cmd':
        #     try:
        #         device.command(cmd=parts[4], reported_by='yombo.gateway.lib.devices.mqtt_incoming')
        #
        #     except Exception as e:
        #         logger.warn("Device received invalid command request for command: %s  Reason: %s" % (parts[4], e))
        #
        #     if len(parts) > 5:
        #         status = device.status_history[0]
        #         if payload == '' or payload == 'all':
        #             self.mqtt.publish('yombo/devices/%s/status' % device.machine_label,
        #                               json.dumps(device.status_history[0]))
        #         elif payload in status:
        #             self.mqtt.publish('yombo/devices/%s/status/%s' % (device.machine_label, payload),
        #                               str(getattr(payload, status)))

    def list_devices(self, field=None):
        """
        Return a list of devices, returning the value specified in field.
        
        :param field: A string referencing an attribute of a device.
        :type field: string
        :return: 
        """
        if field is None:
            field = 'machine_label'

        if field not in self.device_search_attributes:
            raise YomboWarning('Invalid field for device attribute: %s' % field)

        devices = []
        for device_id, device in self.devices.items():
            devices.append(getattr(device, field))
        return devices

    def get(self, device_requested, limiter=None, status=None):
        """
        Performs the actual search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find devices:
           
            >>> self._Devices['8w3h4sa']
        
        or:
        
            >>> self._Devices['porch light']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param device_requested: The device ID, machine_label, or device label to search for.
        :type device_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the device to check for.
        :type status: int
        :return: Pointer to requested device.
        :rtype: dict
        """
        # logger.debug("looking for: {device_requested}", device_requested=device_requested)
        if limiter is None:
            limiter = .89

        if limiter > .99999999:
            limiter = .99
        elif limiter < .10:
            limiter = .10

        if device_requested in self.devices:
            item = self.devices[device_requested]
            if status is not None and item.status != status:
                raise KeyError("Requested device found, but has invalid status: %s" % item.status)
            return item
        else:
            attrs = [
                {
                    'field': 'device_id',
                    'value': device_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'machine_label',
                    'value': device_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'label',
                    'value': device_requested,
                    'limiter': limiter,
                }
            ]
            try:
                # logger.debug("Get is about to call search...: %s" % device_requested)
                found, key, item, ratio, others = do_search_instance(attrs, self.devices,
                                                                     self.device_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest")
                # logger.debug("found device by search: {device_id}", device_id=key)
                if found:
                    return self.devices[key]
                else:
                    raise KeyError("Device not found: %s" % device_requested)
            except YomboWarning as e:
                raise KeyError('Searched for %s, but had problems: %s' % (device_requested, e))

    def search(self, _limiter=None, _operation=None, **kwargs):
        """
        Search for devices based on attributes for all devices.
        
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the device to check for.
        :return: 
        """
        return search_instance(kwargs,
                               self.devices,
                               self.device_search_attributes,
                               _limiter,
                               _operation)

    @inlineCallbacks
    def add_device(self, data, **kwargs):
        """
        Add a new device. This will also make an API request to add device at the server too.

        :param data:
        :param kwargs:
        :return:
        """
        logger.debug("Add new device.  Data: {data}", data=data)
        api_data = {
            'gateway_id': self.gwid,
        }

        try:
            for key in list(data.keys()):
                if data[key] == "":
                    data[key] = None
                elif key in ['statistic_lifetime', 'pin_timeout']:
                    if data[key] is None or (isinstance(data[key], str) and data[key].lower() == "none"):
                        del data[key]
                    else:
                        data[key] = int(data[key])
        except Exception as e:
            results = {
                'status': 'failed',
                'msg': "Couldn't add device",
                'apimsg': e,
                'apimsghtml': e,
                'device_id': '',
            }
            returnValue(results)

        for key, value in data.items():
            if key == 'energy_map':
                api_data['energy_map'] = json.dumps(data['energy_map'], separators=(',',':'))
            else:
                api_data[key] = data[key]

        # print("apidata: %s" % api_data)
        try:
            global_invoke_all('_device_before_add_', **{'called_by': self, 'device': data})
        except YomboHookStopProcessing as e:
            raise YomboWarning("Adding device was halted by '%s', reason: %s" % (e.name, e.message))

        if 'device_id' not in api_data:
            logger.debug("POSTING device. api data: {api_data}", api_data=api_data)
            device_results = yield self._YomboAPI.request('POST', '/v1/device', api_data)
            logger.debug("add new device results: {device_results}", device_results=device_results)
        else:
            logger.debug("PATCHING device. api data: {api_data}", api_data=api_data)
            del api_data['gateway_id']
            del api_data['device_type_id']
            device_results = yield self._YomboAPI.request('PATCH', '/v1/device/%s' % data['device_id'], api_data)
            logger.debug("edit device results: {device_results}", device_results=device_results)

        if device_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't add device",
                'apimsg': device_results['content']['message'],
                'apimsghtml': device_results['content']['html_message'],
                'device_id': '',
            }
            returnValue(results)

        if 'variable_data' in data:
            # print("data['variable_data']: %s", data['variable_data'])
            variable_results = yield self.set_device_variables(device_results['data']['id'], data['variable_data'])
            # print("variable_results: %s" % variable_results)
            if variable_results['code'] > 299:
                results = {
                    'status': 'failed',
                    'msg': "Device saved, but had problems with saving variables: %s" % variable_results['msg'],
                    'apimsg': variable_results['apimsg'],
                    'apimsghtml': variable_results['apimsghtml'],
                    'device_id': device_results['data']['id'],
                }
                returnValue(results)

        logger.debug("device edit results: {device_results}", device_results=device_results)
        results = {
            'status': 'success',
            'msg': "Device added.",
            'device_id': device_results['data']['id']
        }
        returnValue(results)

    #todo: convert to use a deferred semaphore
    @inlineCallbacks
    def set_device_variables(self, device_id, variables):
        # print("set variables: %s" % variables)
        for field_id, data in variables.items():
            # print("devices.set_device_variables.data: %s" % data)
            for data_id, value in data.items():
                if value == "":
                    continue
                if data_id.startswith('new_'):
                    post_data = {
                        'gateway_id': self.gwid,
                        'field_id': field_id,
                        'relation_id': device_id,
                        'relation_type': 'device',
                        'data_weight': 0,
                        'data': value,
                    }
                    # print("Posting new variable: %s" % post_data)
                    var_data_results = yield self._YomboAPI.request('POST', '/v1/variable/data', post_data)
                    if var_data_results['code'] > 299:
                        results = {
                            'status': 'failed',
                            'msg': "Couldn't add device variables",
                            'apimsg': var_data_results['content']['message'],
                            'apimsghtml': var_data_results['content']['html_message'],
                            'device_id': device_id
                        }
                        returnValue(results)
                else:
                    post_data = {
                        'data_weight': 0,
                        'data': value,
                    }
                    # print("PATCHing variable: %s" % post_data)
                    var_data_results = yield self._YomboAPI.request(
                        'PATCH',
                        '/v1/variable/data/%s' % data_id,
                        post_data
                    )
                    # print("var_data_results: %s" % var_data_results)
                    if var_data_results['code'] > 299:
                        results = {
                            'status': 'failed',
                            'msg': "Couldn't add device variables",
                            'apimsg': var_data_results['content']['message'],
                            'apimsghtml': var_data_results['content']['html_message'],
                            'device_id': device_id
                        }
                        returnValue(results)
        # print("var_data_results: %s" % var_data_results)
        returnValue({
            'status': 'success',
            'code': var_data_results['code'],
            'msg': "Device added.",
            'variable_id': var_data_results['data']['id']
        })

    @inlineCallbacks
    def delete_device(self, device_id):
        """
        So sad to delete, but life goes one. This will delete a device by calling the API to request the device be
        deleted.

        :param device_id: Device ID to delete. Will call API
        :type device_id: string
        :returns: Pointer to new device. Only used during unittest
        """
        if device_id not in self.devices:
            raise YomboWarning("device_id doesn't exist. Nothing to delete.", 300, 'delete_device', 'Devices')

        device_results = yield self._YomboAPI.request('DELETE', '/v1/device/%s' % device_id)
        # print("deleted device: %s" % device_results)
        if device_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete device",
                'apimsg': device_results['content']['message'],
                'apimsghtml': device_results['content']['html_message'],
                'device_id': device_id,
            }
            returnValue(results)

        self.devices[device_id].delete()

        results = {
            'status': 'success',
            'msg': "Device deleted.",
            'device_id': device_id
        }
        returnValue(results)

    @inlineCallbacks
    def edit_device(self, device_id, data, **kwargs):
        """
        Edit device settings. Accepts a list of items to change. This will also make an API request to update
        the server too.

        :param device_id: The device to edit
        :param data: a dict of items to update.
        :param kwargs:
        :return:
        """
        if device_id not in self.devices:
            raise YomboWarning("device_id doesn't exist. Nothing to delete.", 300, 'edit_device', 'Devices')

        device = self.devices[device_id]

        try:
            for key in list(data.keys()):
                if data[key] == "":
                    data[key] = None
                elif key in ['statistic_lifetime', 'pin_timeout']:
                    if data[key] is None or (isinstance(data[key], str) and data[key].lower() == "none"):
                        del data[key]
                    else:
                        data[key] = int(data[key])
        except Exception as e:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit device",
                'apimsg': e,
                'apimsghtml': e,
                'device_id': '',
            }
            returnValue(results)

        api_data = {}
        for key, value in data.items():
            # print("key (%s) is of type: %s" % (key, type(value)))
            if isinstance(value, str) and len(value) > 0 and hasattr(device, key):
                if key == 'energy_map':
                    api_data['energy_map'] = json.dumps(value, separators=(',',':'))
                    # print("energy map json: %s" % json.dumps(value, separators=(',',':')))
                else:
                    api_data[key] = value

        # print("send this data to api: %s" % api_data)
        device_results = yield self._YomboAPI.request('PATCH', '/v1/device/%s' % device_id, api_data)
        # print("got this data from api: %s" % device_results)
        if device_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit device",
                'apimsg': device_results['content']['message'],
                'apimsghtml': device_results['content']['html_message'],
                'device_id': device_id,
            }
            returnValue(results)

        if 'variable_data' in data:
            variable_results = yield self.set_device_variables(device_results['data']['id'], data['variable_data'])
            if variable_results['code'] > 299:
                results = {
                    'status': 'failed',
                    'msg': "Device saved, but had problems with saving variables: %s" % variable_results['msg'],
                    'apimsg': variable_results['apimsg'],
                    'apimsghtml': variable_results['apimsghtml'],
                    'device_id': device_id,
                }
                returnValue(results)

        device.update_attributes(data)

        results = {
            'status': 'success',
            'msg': "Device edited.",
            'device_id': device_results['data']['id']
        }
        global_invoke_all('devices_edit', **{'id': device_id})  # call hook "devices_delete" when deleting a device.
        returnValue(results)

    @inlineCallbacks
    def enable_device(self, device_id):
        """
        Enables a given device id.

        :param device_id:
        :return:
        """
        if device_id not in self.devices:
            raise YomboWarning("device_id doesn't exist. Nothing to delete.", 300, 'enable_device', 'Devices')

        api_data = {
            'status': 1,
        }

        device_results = yield self._YomboAPI.request('PATCH', '/v1/device/%s' % device_id, api_data)
        if device_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable device",
                'apimsg': device_results['content']['message'],
                'apimsghtml': device_results['content']['html_message'],
                'device_id': device_id,
            }
            returnValue(results)

        self.devices[device_id].enable()

        results = {
            'status': 'success',
            'msg': "Device disabled.",
            'device_id': device_results['data']['id']
        }
        global_invoke_all('devices_disabled', **{'id': device_id})  # call hook "devices_delete" when deleting a device.
        returnValue(results)

    @inlineCallbacks
    def disable_device(self, device_id):
        """
        Disables a given device id.

        :param device_id:
        :return:
        """
        if device_id not in self.devices:
            raise YomboWarning("device_id doesn't exist. Nothing to delete.", 300, 'disable_device', 'Devices')

        api_data = {
            'status': 0,
        }

        device_results = yield self._YomboAPI.request('PATCH', '/v1/device/%s' % device_id, api_data)
        if device_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable device",
                'apimsg': device_results['content']['message'],
                'apimsghtml': device_results['content']['html_message'],
                'device_id': device_id,
            }
            returnValue(results)

        self.devices[device_id].disable()

        results = {
            'status': 'success',
            'msg': "Device disabled.",
            'device_id': device_results['data']['id']
        }
        global_invoke_all('devices_disabled', **{'id': device_id})  # call hook "devices_delete" when deleting a device.
        returnValue(results)

    def update_device(self, record, test_device=False):
        """
        Add a new device. Record must contain:

        id, uri, label, notes, description, gateway_id, device_type_id, voice_cmd, voice_cmd_order,
        Voice_cmd_src, pin_code, pin_timeout, created, updated, device_class

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :returns: Pointer to new device. Only used during unittest
        """
        logger.debug("update_device: {record}", record=record)
        if record['device_id'] not in self.devices:
            raise YomboWarning("device_id doesn't exist. Nothing to do.", 300, 'update_device', 'Devices')
            # self.devices[record['device_id']].update(record)


    ##############################################################################################################
    # The remaining functions implement automation hooks. These should not be called by anything other than the  #
    # automation library!                                                                                        #
    ##############################################################################################################

    def check_trigger(self, device_id, new_status):
        """
        Called by the devices.set function when a device changes state. It just sends this to the automation
        library for checking and firing any rules as needed.

        True - Rules fired, fale - no rules fired.
        :param device_id: Device ID
        :type device_id: str
        :param new_status: New device state
        :type new_status: str
        """
        self._AutomationLibrary.triggers_check('devices', device_id, new_status)

    def _automation_source_list_(self, **kwargs):
        """
        Adds 'devices' to the list of source platforms (triggers)as a platform for rule sources (triggers).

        :param kwargs: None
        :return:
        """
        return [
            {
              'platform': 'devices',
              'platform_description': 'Allows devices to be used as triggers for rules or macros.',
              'validate_source_callback': self.devices_validate_source_callback,  # function to call to validate a trigger
              'add_trigger_callback': self.devices_add_trigger_callback,  # function to call to add a trigger
              'get_value_callback': self.devices_get_value_callback,  # get a value
              }
         ]

    def devices_validate_source_callback(self, rule, portion, **kwargs):
        """
        Used to check a rule's source for 'devices'. It makes sure rule source is valid before being added.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the rule being checked. Includes source, filter, etc.
        :return: None. Raises YomboWarning if invalid.
        """
        if 'platform' not in portion['source']:
            raise YomboWarning("'platform' must be in 'source' section.")

        if 'device' in portion['source']:
            try:
                device = self.get(portion['source']['device'], .89)
                portion['source']['device_pointers'] = device
                return portion
            except Exception as e:
                raise YomboWarning("Error while searching for device, could not be found: %s" % portion['source']['device'],
                                   101, 'devices_validate_source_callback', 'lib.devices')
        else:
            raise YomboWarning("For platform 'devices' as a 'source', must have 'device' and can be either device ID or device label.  Source:%s" % portion,
                               102, 'devices_validate_source_callback', 'lib.devices')

    def devices_add_trigger_callback(self, rule, **kwargs):
        """
        Called to add a trigger.  We simply use the automation library for the heavy lifting.

        :param rule: The potential rule being added.
        :param kwargs: None
        :return:
        """
        logger.error("triggers_add")
        self._AutomationLibrary.triggers_add(rule['rule_id'], 'devices', rule['trigger']['source']['device_pointers'].device_id)

    def devices_get_value_callback(self, rule, portion, **kwargs):
        """
        A callback to the value for platform "states". We simply just do a get based on key_name.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the portion of rule being fired. Includes source, filter, etc.
        :return:
        """
        return portion['source']['device_pointers'].machine_status

    def _automation_action_list_(self, **kwargs):
        """
        hook_automation_action_list called by the automation library to list possible actions this module can
        perform.

        This implementation allows autoamtion rules set easily set Atom values.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'devices',
              'validate_action_callback': self.devices_validate_action_callback,  # function to call to validate an action is possible.
              'do_action_callback': self.devices_do_action_callback,  # function to be called to perform an action
              'get_available_items_callback': self.devices_get_available_devices_callback,  # get a value
              'get_available_options_for_item_callback': self.devices_get_device_options_callback,  # get a value
              }
         ]

    def devices_get_available_devices_callback(self, **kwargs):

        # iterate enabled devices
        # for each device, list available commands (device type commnads)
        # for each command, list any additional inputs (device type command inputs)

        devices = []
        for device_id, device in self.devices.items():
            devices.append({
                'id': device.device_id,
                'machine_label': device.machine_label,
            })
        return devices

    def devices_get_device_options_callback(self, **kwargs):
        device_id = kwargs['id']
        return self.get(device_id).available_commands()

    def devices_validate_action_callback(self, rule, action, **kwargs):
        """
        A callback to check if a provided action is valid before being added as a possible action.

        :param rule: The potential rule being added.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        if 'command' not in action:
            raise YomboWarning("For platform 'devices' as an 'action', must have 'comand' and can be either command uuid or command label.",
                               103, 'devices_validate_action_callback', 'lib.devices')

        if 'device' in action:
            try:
                devices_text = split(action['device'])
                devices = []
                for device_text in devices_text:
                    devices.append(self.get(action['device']))
                action['device_pointers'] = devices
                return action
            except Exception as e:
                raise YomboWarning("Error while searching for device, could not be found: %s  Rason: %s" % (action['device'], e),
                               104, 'devices_validate_action_callback', 'lib.devices')
        else:
            raise YomboWarning("For platform 'devices' as an 'action', must have 'device' and can be either device ID, device machine_label, or device label.",
                               105, 'devices_validate_action_callback', 'lib.devices')

    def devices_do_action_callback(self, rule, action, **kwargs):
        """
        A callback to perform an action.

        :param rule: The complete rule being fired.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        logger.info("firing device rule: {rule}", rule=rule['name'])
        for device in action['device_pointers']:
            logger.info("Doing command '{command}' to device: {device}", command=action['command'], device=device.label)
            persistent_request_id = sha1('automation' + rule['name'] + action['command'] + device.machine_label).hexdigest()
            try:
                requested_by = {
                    'user_id': 'Automation rule: %s' % rule['name'],
                    'component': 'yombo.gateway.lib.devices',
                    'gateway': get_public_gw_id()
                }
                device.command(cmd=action['command'],
                               requested_by=requested_by,
                               persistent_request_id=persistent_request_id,
                               **kwargs)
            except YomboWarning as e:
                logger.warn("Unable to process device automation rule: {e}", e=e)



