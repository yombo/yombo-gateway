# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_

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

**Usage**:

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
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/devices.html>`_
"""
# Import python libraries

try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
import msgpack
import sys
import traceback

from hashlib import sha1
from time import time
from collections import OrderedDict

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred, Deferred
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

    def values(self):
        """
        Gets a list of values, or, a list of objects representing all the devices.

        :return:
        """
        return list(self.devices.values())

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Sets up basic attributes.
        """
        self._VoiceCommandsLibrary = self._Loader.loadedLibraries['voicecmds']

        self.devices = {}
        self.device_search_attributes = ['device_id', 'device_type_id', 'machine_label', 'label', 'description',
            'pin_required', 'pin_code', 'pin_timeout', 'voice_cmd', 'voice_cmd_order', 'statistic_label', 'status',
            'created', 'updated', 'location_id', 'area_id', 'gateway_id']

        self.gateway_id = self._Configs.get("core", "gwid", "local", False)
        self.is_master = self._Configs.get("core", "is_master", "local", False)
        self.master_gateway = self._Configs.get("core", "master_gateway", "local", False)

        # used to store delayed queue for restarts. It'll be a bare, dehydrated version.
        # store the above, but after hydration.
        self.device_commands = OrderedDict()  # tracks commands being sent to devices. Also tracks if a command is delayed
          # the automation system can always request the same command to be performed but ensure only one is
          # is n the queue between restarts.
        self.clean_device_commands_loop = None

        self.startup_queue = {}  # Place device commands here until we are ready to process device commands
        self.processing_commands = False

        self.mqtt = None

        self.idempotence = yield self._SQLDict.get('yombo.lib.device', 'idempotence')  # tracks if a request was already made

        self.clean_idempotence_ids_loop = LoopingCall(self.clean_idempotence_ids)
        self.clean_idempotence_ids_loop.start(3600)

    def _load_(self, **kwargs):
        """
        Loads the devices from the database and loads device commands.

        :param kwargs:
        :return:
        """
        # yield self._load_devices_from_database()
        # yield self._load_device_commands()
        pass

    @inlineCallbacks
    def _start_(self, **kwags):
        """
        Sets up the MQTT listener for IoT interactions.

        :param kwags:
        :return:
        """
        yield self._load_devices_from_database()
        yield self._load_device_commands()
        if self._States['loader.operating_mode'] == 'run':
            self.mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming, client_id='Yombo-devices-%s' %
                                                                                            self.gateway_id)

    def _started_(self, **kwargs):
        """
        Sets up the looping call to cleanup device commands. Also, subscribes to
        MQTT topics for IoT interactions.

        :return: 
        """
        self.clean_device_commands_loop = LoopingCall(self.clean_device_commands)
        self.clean_device_commands_loop.start(random_int(3600, .15))

        if self._States['loader.operating_mode'] == 'run':
            self.mqtt.subscribe("yombo/devices/+/get")
            self.mqtt.subscribe("yombo/devices/+/cmd")

    def _modules_started_(self, **kwargs):
        """
        Tells any applicable device commands to fire.

        :param kwargs:
        :return:
        """
        for request_id, device_command in self.device_commands.items():
            device_command.start()

    def _unload_(self, **kwargs):
        """
        Save any device commands that need to be saved.

        :return: 
        """
        for device_id, device in self.devices.items():
            device._unload_()
        for request_id, device_command in self.device_commands.items():
            device_command.save_to_db(True)

    def _reload_(self):
        return self._load_()

    def _modules_prestarted_(self, **kwargs):
        """
        On start, sends all queued messages. Then, check delayed messages for any messages that were missed. Send
        old messages and prepare future messages to run.
        """
        self.processing_commands = True
        for command, request in self.startup_queue.items():
            self.command(request['device_id'], request['command_id'], not_before=request['not_before'],
                    max_delay=request['max_delay'], **request['kwargs'])
        self.startup_queue.clear()

    @inlineCallbacks
    def _load_devices_from_database(self):
        """
        Loads devices from database and sends them to :py:meth:`import_device <Devices.import_device>`
        
        This can be triggered either on system startup or when new/updated devices have been saved to the
        database and we need to refresh existing devices.
        """
        devices = yield self._LocalDB.get_devices()
        if len(devices) > 0:
            for record in devices:
                record = record.__dict__
                if record['energy_map'] is None:
                    record['energy_map'] = {"0.0":0, "1.0":0}
                # print("record['energy_map']: %s" % record['energy_map'])
                # record['energy_map'] = json.loads(str(record['energy_map']))
                new_map = {}
                for key, value in record['energy_map'].items():
                    new_map[float(key)] = float(value)
                record['energy_map'] = new_map
                logger.debug("Loading device: {record}", record=record)
                device_id = yield self.import_device(record, source='database')
                d = Deferred()
                d.addCallback(lambda ignored: maybeDeferred(self.devices[device_id]._init0_))
                d.addErrback(self.import_device_failure, self.devices[device_id])
                d.addCallback(lambda ignored: maybeDeferred(self.devices[device_id]._init_))
                d.addErrback(self.import_device_failure, self.devices[device_id])
                d.addCallback(lambda ignored: maybeDeferred(self.devices[device_id]._start0_))
                d.addErrback(self.import_device_failure, self.devices[device_id])
                d.addCallback(lambda ignored: maybeDeferred(self.devices[device_id]._start_))
                d.addErrback(self.import_device_failure, self.devices[device_id])
                d.callback(1)
                yield d
                try:
                    global_invoke_all('_device_imported_',
                                      called_by=self,
                                      id=device_id,
                                      device=self.devices[device_id],
                                      )
                except YomboHookStopProcessing as e:
                    pass


                        # print("devices: %s" % self.devices )
        # for device_id, device in self.devices.items():
        #     d = Deferred()
        #     d.addCallback(lambda ignored: maybeDeferred(self.devices[device_id]._init_))
        #     d.addErrback(self.import_device_failure, device)
        #     # d.addCallback(lambda ignored: maybeDeferred(self.devices[device_id]._start_))
        #     # d.addErrback(self.import_device_failure, device)
        #     d.callback(1)
        #     yield d

    def clean_idempotence_ids(self):
        delete_time = int(time()) - 1800
        for key in self.idempotence.keys():
            if self.idempotence[key]['time'] < delete_time:
                del self.idempotence[key]

    def sorted(self, key=None):
        """
        Returns an OrderedDict, sorted by key.  If key is not set, then default is 'area_label'.

        :param key: Attribute contained in a device to sort by.
        :type key: str
        :return: All devices, sorted by key.
        :rtype: OrderedDict
        """
        if key is None:
            key = 'area_label'
        return OrderedDict(sorted(iter(self.devices.items()), key=lambda i: getattr(i[1], key)))

    def import_device(self, device, source=None, test_device=None):  # load or re-load if there was an update.
        """
        Add a new device to memory.

        **Hooks called**:

        * _device_before_update_ : If updated, sends device dictionary as 'device'
        * _device_updated_ : If updated, send the device instance as 'device'

        :param device: A dictionary of items required to either setup a new device or update an existing one.
        :type device: dict
        :param test_device: Used for unit testing.
        :type test_device: bool
        :returns: Pointer to new device. Only used during unittest
        """
        if test_device is None:
            test_device = False

        # logger.debug("loading device into memory: {device}", device=device)

        device_id = device["id"]
        if device_id not in self.devices:
            import_state = 'new'
            device_type = self._DeviceTypes[device['device_type_id']]

            if device_type.platform is None or device_type.platform == "":
                device_type.platform = 'device'
            class_names = device_type.platform.lower()

            class_names = "".join(class_names.split())  # we don't like spaces
            class_names = class_names.split(',')

            # logger.info("Loading device ({device}), platforms: {platforms}",
            #             device=device['label'],
            #             platforms=class_names)

            klass = None
            for class_name in class_names:
                if class_name in self._DeviceTypes.platforms:
                    klass = self._DeviceTypes.platforms[class_name]
                    break

            if klass is None:
                klass = self._DeviceTypes.platforms['device']
                logger.warn("Using base device class for device '{label}' cannot find any of these requested classes: {class_names}",
                            label=device['label'],
                            class_names=class_names)

            # setup some base items for the new device class.
            klass._Atoms = self._Loader.loadedLibraries['atoms']
            klass._Automation = self._Loader.loadedLibraries['automation']
            klass._AMQP = self._Loader.loadedLibraries['amqp']
            klass._AMQPYombo = self._Loader.loadedLibraries['amqpyombo']
            klass._Commands = self._Loader.loadedLibraries['commands']
            klass._Configs = self._Loader.loadedLibraries['configuration']
            klass._CronTab = self._Loader.loadedLibraries['crontab']
            klass._Devices = self
            klass._DeviceTypes = self._Loader.loadedLibraries['devicetypes']  # All device types.
            klass._Gateways = self._Loader.loadedLibraries['gateways']
            klass._GPG = self._Loader.loadedLibraries['gpg']
            klass._InputTypes = self._Loader.loadedLibraries['inputtypes']  # Input Types
            klass._Libraries = self._Loader.loadedLibraries
            klass._Libraries = self._Loader.loadedLibraries
            klass._Localize = self._Loader.loadedLibraries['localize']
            klass._Locations = self._Loader.loadedLibraries['locations']  # Basically, all devices
            klass._MQTT = self._Loader.loadedLibraries['mqtt']
            klass._Nodes = self._Loader.loadedLibraries['nodes']
            klass._Notifications = self._Loader.loadedLibraries['notifications']
            klass._Queue = self._Loader.loadedLibraries['queue']
            klass._Scenes = self._Loader.loadedLibraries['scenes']
            klass._SQLDict = self._Loader.loadedLibraries['sqldict']
            klass._SSLCerts = self._Loader.loadedLibraries['sslcerts']
            klass._States = self._Loader.loadedLibraries['states']
            klass._Statistics = self._Loader.loadedLibraries['statistics']
            klass._Tasks = self._Loader.loadedLibraries['tasks']
            klass._Template = self._Loader.loadedLibraries['template']
            klass._Times = self._Loader.loadedLibraries['times']
            klass._YomboAPI = self._Loader.loadedLibraries['yomboapi']
            klass._Variables = self._Loader.loadedLibraries['variables']
            klass._Validate = self._Loader.loadedLibraries['validate']
            klass._VoiceCmds = self._Loader.loadedLibraries['voicecmds']
            try:
                self.devices[device_id] = klass(device, self)
                # self.devices[device_id]._start_()
            except Exception as e:
                logger.error("Error while creating device instance: {e}", e=e)
                logger.error("-------==(Error: While saving new config data)==--------")
                logger.error("--------------------------------------------------------")
                logger.error("{error}", error=sys.exc_info())
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
                logger.error("--------------------------------------------------------")

        else:
            import_state = 'update'
            try:
                global_invoke_all('_device_before_import_',
                                  called_by=self,
                                  id=device_id,
                                  data=device,
                                  )
            except YomboHookStopProcessing as e:
                pass

            self.devices[device_id].update_attributes(device, source)

        try:
            self._VoiceCommandsLibrary.add_by_string(device["voice_cmd"], None, device["id"],
                                                     device["voice_cmd_order"])
        except Exception:
            logger.debug("Device {label} has an invalid voice_cmd {voice_cmd}", label=device["label"],
                         voice_cmd=device["voice_cmd"])

        # logger.debug("_add_device: {device}", device=device)
        if import_state == 'update':
            try:
                global_invoke_all('_device_updated_',
                                  called_by=self,
                                  id=device_id,
                                  device=self.devices[device_id],
                                  )
            except YomboHookStopProcessing as e:
                pass
        return device_id

                # if test_device:
        #            return self.devices[device_id]

    def import_device_failure(self, failure, device):
        print("ERRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR")
        logger.error("Got failure while creating device instance for '{label}': {failure}", failure=failure,
                     label=device['label'])

    @inlineCallbacks
    def _load_device_commands(self):
        """
        Actually loads the device commands from the database.
        :return:
        """
        where = {
            'created_at': [time() - 60*60*24, '>'],
        }
        device_commands = yield self._LocalDB.get_device_commands(where)
        for device_command in device_commands:
            if device_command['device_id'] not in self.devices:
                logger.warn("Seems a device id we were tracking is gone..{id}", id=device_command['device_id'])
                continue

            self.device_commands[device_command['request_id']] = Device_Command(device_command, self, start=False)
        return None

    @inlineCallbacks
    def clean_device_commands(self):
        """
        Remove old device command requests.
        :return: 
        """
        cur_time = time()
        for request_id in list(self.device_commands.keys()):
            device_command = self.device_commands[request_id]
            if device_command.finished_at is not None:
                if device_command.finished_at > cur_time - (60*60*24):  # keep 45 minutes worth.
                    found_dc = False
                    for device_id, device in self.devices.items():
                        if request_id in device.device_commands:
                            found_dc = True
                            break
                    if found_dc is False:
                        yield device_command.save_to_db()
                        del self.device_commands[request_id]

        # Lets delete any device status after 60 days. Long term data should be in the statistics.
        self._LocalDB.cleanup_device_status(days=60)

    def add_device_command_by_object(self, device_command):
        """
        Simply append a device command object to the list of tracked device commands.

        :param device_command:
        :return:
        """
        self.device_commands[device_command.request_id] = device_command
        self.device_commands.move_to_end(device_command.request_id, last=False)  # move to the front.

    def add_device_command(self, device_command):
        """
        Insert a new device command from a dictionary. Usually called by the gateways coms system.

        :param device_command:
        :return:
        """
        self.device_commands[device_command['request_id']] = Device_Command(device_command, self, start=True)
        self.device_commands.move_to_end(device_command['request_id'], last=False)  # move to the front.

    def update_device_command(self, src_gateway_id, request_id, log_time, status, message):
        """
        Update device command information based on dictionary items. Usually called by the gateway coms systems.

        :param device_command:
        :return:
        """
        if request_id in self.device_commands:
            self.device_commands[request_id].gw_coms_set_status(src_gateway_id, log_time, status, message)

    def get_gateway_device_commands(self, dest_gateway_id):
        """
        Gets all device commands for a gateway where the device's gateway is matches the requested.

        :param dest_gateway_id:
        :return:
        """
        results = []
        for device_command_id, device_command in self.device_commands.items():
            if device_command.device.gateway_id == dest_gateway_id:
                results.append(device_command.asdict())
        return results

    def get_delayed_commands(self):
        """
        Returns only device commands that are delayed.

        :return: 
        """
        items = {}
        for request_id, device_command in self.device_commands.items():
            if device_command.status == 'delayed':
                items[request_id] = device_command
        return items

    def command(self, device, cmd, pin=None, request_id=None, not_before=None, delay=None, max_delay=None, requested_by=None, inputs=None, **kwargs):
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
        return self.get(device).command(cmd, pin, request_id, not_before, delay, max_delay, requested_by=requested_by, inputs=inputs, **kwargs)

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
        logger.info("Yombo Devices got this: {topic} : {parts}", topic=topic, parts=parts)
        payload = payload.strip()
        content_type = 'string'
        try:
            payload = json.loads(payload)
            content_type = 'json'
        except Exception as e:
            try:
                payload = msgpack.loads(payload)
                content_type = 'msgpack'
            except Exception as e:
                pass

        try:
            device_label = self.get(parts[2].replace("_", " "))
            device = self.get(device_label)
        except YomboDeviceError as e:
            logger.info("Received MQTT request for a device that doesn't exist: %s" % parts[2])
            return

        if parts[3] == 'get':
            status = device.status_all

            if len(parts) == 5:
                if payload == 'all':
                    self.mqtt.publish('yombo/devices/%s/status' % device.machine_label, json.dumps(device.status_all))
                elif payload in status:
                    self.mqtt.publish('yombo/devices/%s/status/%s' % (device.machine_label, payload), str(getattr(payload, status)))
            else:
                self.mqtt.publish('yombo/devices/%s/status' % device.machine_label,
                                  json.dumps(device.status_all))

        elif parts[3] == 'cmd':
            try:
                requested_by = {
                    'user_id': 'Unknown',
                    'component': 'yombo.gateway.lib.devices.mqtt_incoming',
                    'gateway': 'Unknown'
                }
                device.command(cmd=parts[4], reported_by='yombo.gateway.lib.devices.mqtt_incoming')
            except Exception as e:
                logger.warn("Device received invalid command request for command: %s  Reason: %s" % (parts[4], e))

            if len(parts) == 6:
                status = device.status_all
                if parts[4] == 'all':
                    self.mqtt.publish('yombo/devices/%s/status' % device.machine_label,
                                      json.dumps(device.status_all))
                elif payload in status:
                    self.mqtt.publish('yombo/devices/%s/status/%s' % (device.machine_label, payload),
                                      str(getattr(payload, status)))
            else:
                self.mqtt.publish('yombo/devices/%s/status' % device.machine_label,
                                  json.dumps(device.status_all))

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

    def full_list_devices(self, gateway_id=None):
        """
        Return a list of dictionaries representing all known devices. Can be restricted to
        a single gateway by supplying a gateway_id, use 'local' for the local gateway.

        :param gateway_id: Filter selecting to a specific gateway. Use 'local' for the local gateway.
        :type gateway_id: string
        :return:
        """
        if gateway_id == 'local':
            gateway_id = self.gateway_id

        devices = []
        for device_id, device in self.devices.items():
            if gateway_id is None or device.gateway_id == gateway_id:
                devices.append(device.asdict())
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
                found, key, item, ratio, others = do_search_instance(attrs,
                                                                     self.devices,
                                                                     self.device_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest")
                logger.debug("found ({found}) device by search: {device_id}, ratio: {ratio}",
                             found=found, device_id=key, ratio=ratio)
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
        found, key, item, ratio, others = search_instance(kwargs,
                               self.devices,
                               self.device_search_attributes,
                               _limiter,
                               _operation)
        return others

    @inlineCallbacks
    def add_device(self, api_data, source=None, **kwargs):
        """
        Add a new device. This will also make an API request to add device at the server too.

        :param data:
        :param kwargs:
        :return:
        """
        results = None
        # logger.info("Add new device.  Data: {data}", data=data)
        if 'gateway_id' not in api_data:
            api_data['gateway_id'] = self.gateway_id

        try:
            for key, value in api_data.items():
                if value == "":
                    api_data[key] = None
                elif key in ['statistic_lifetime', 'pin_timeout']:
                    if api_data[key] is None or (isinstance(value, str) and value.lower() == "none"):
                        del api_data[key]
                    else:
                        api_data[key] = int(value)
        except Exception as e:
            return {
                'status': 'failed',
                'msg': "Couldn't add device",
                'apimsg': e,
                'apimsghtml': e,
                'device_id': None,
                'data': None,
            }

        try:
            global_invoke_all('_device_before_add_',
                              called_by=self,
                              data=api_data,
                              stoponerror=True,
                              )
        except YomboHookStopProcessing as e:
            raise YomboWarning("Adding device was halted by '%s', reason: %s" % (e.name, e.message))

        if source != 'amqp':
            logger.debug("POSTING device. api data: {api_data}", api_data=api_data)
            try:
                if 'session' in kwargs:
                    session = kwargs['session']
                else:
                    session = None

                device_results = yield self._YomboAPI.request('POST', '/v1/device',
                                                              api_data,
                                                              session=session)
            except YomboWarning as e:
                return {
                    'status': 'failed',
                    'msg': "Couldn't add device: %s" % e.message,
                    'apimsg': "Couldn't add device: %s" % e.message,
                    'apimsghtml': "Couldn't add device: %s" % e.html_message,
                }
            logger.debug("add new device results: {device_results}", device_results=device_results)

            if 'variable_data' in api_data and len(api_data['variable_data']) > 0:
                # print("data['variable_data']: %s", data['variable_data'])
                variable_results = yield self.set_device_variables(device_results['data']['id'],
                                                                   api_data['variable_data'],
                                                                   'add',
                                                                   source,
                                                                   session=session)
                # print("variable_results: %s" % variable_results)
                if variable_results['code'] > 299:
                    results = {
                        'status': 'failed',
                        'msg': "Device saved, but had problems with saving variables: %s" % variable_results['msg'],
                        'apimsg': variable_results['apimsg'],
                        'apimsghtml': variable_results['apimsghtml'],
                        'device_id': device_results['data']['id'],
                        'data': device_results['data'],
                    }

            device_id = device_results['data']['id']
            new_device = device_results['data']
            new_device['created'] = new_device['created_at']
            new_device['updated'] = new_device['updated_at']
        else:
            device_id = api_data['id']
            new_device = api_data

        logger.debug("device add results: {device_results}", device_results=device_results)

        self.import_device(new_device, source)
        self.devices[device_id].add_to_db()

        try:
            yield global_invoke_all('_device_changed_',
                                    change_type='added',
                                    called_by=self,
                                    id=device_id,
                                    device=self.devices[device_id],
                                    )
        except Exception as e:
            pass
        try:
            global_invoke_all('_device_added_',
                              called_by=self,
                              device=self.devices[device_id],
                              )
        except YomboHookStopProcessing as e:
            pass

        if results is None:
            return {
                'status': 'success',
                'msg': "Device added",
                'apimsg':  "Device added",
                'apimsghtml':  "Device added",
                'device_id': device_id,
                'data': new_device,
            }

    #todo: convert to use a deferred semaphore
    @inlineCallbacks
    def set_device_variables(self, device_id, variables, action_type=None, source=None, session=None):
        # print("set variables: %s" % variables)
        for field_id, data in variables.items():
            print("devices.set_device_variables.data: %s" % data)
            for data_id, value in data.items():
                if value == "":
                    continue
                if data_id.startswith('new_'):
                    post_data = {
                        'gateway_id': self.gateway_id,
                        'field_id': field_id,
                        'relation_id': device_id,
                        'relation_type': 'device',
                        'data_weight': 0,
                        'data': value,
                    }
                    # print("Posting new variable: %s" % post_data)
                    try:
                        var_data_results = yield self._YomboAPI.request('POST', '/v1/variable/data',
                                                                        post_data,
                                                                        session=session)
                    except YomboWarning as e:
                        return {
                            'status': 'failed',
                            'msg': "Couldn't add device variables: %s" % e.message,
                            'apimsg': "Couldn't add device variables: %s" % e.message,
                            'apimsghtml': "Couldn't add device variables: %s" % e.html_message,
                        }
                    data = var_data_results['data']
                    self._LocalDB.add_variable_data(data)
                else:
                    post_data = {
                        'data_weight': 0,
                        'data': value,
                    }
                    print("PATCHing variable: %s" % post_data)
                    try:
                        var_data_results = yield self._YomboAPI.request(
                            'PATCH',
                            '/v1/variable/data/%s' % data_id,
                            post_data,
                            session=session
                        )
                    except YomboWarning as e:
                        return {
                            'status': 'failed',
                            'msg': "Couldn't edit device variables: %s" % e.message,
                            'apimsg': "Couldn't edit device variables: %s" % e.message,
                            'apimsghtml': "Couldn't edit device variables: %s" % e.html_message,
                        }
                    self._LocalDB.edit_variable_data(data_id, value)

        if device_id in self.devices:  # Load device variable cache
            yield self.devices[device_id].device_variables()
        # print("var_data_results: %s" % var_data_results)
        try:
            global_invoke_all('_device_variables_updated_',
                              called_by=self,
                              id=device_id,
                              device=self.devices[device_id],
                              )
        except YomboHookStopProcessing as e:
            pass

        return {
            'status': 'success',
            'code': var_data_results['code'],
            'msg': "Device variable added.",
            'variable_id': var_data_results['data']['id'],
            'data': var_data_results['data'],
        }

    @inlineCallbacks
    def delete_device(self, device_id, called_from_device=None, **kwargs):
        """
        So sad to delete, but life goes on. This will delete a device by calling the API to request
        the device be deleted.

        :param device_id: Device ID to delete. Will call API
        :type device_id: string
        :returns: Pointer to new device. Only used during unittest
        """
        if device_id not in self.devices:
            raise YomboWarning("device_id doesn't exist. Nothing to delete.", 300, 'delete_device', 'Devices')

        try:
            global_invoke_all('_device_before_delete_',
                              called_by=self,
                              id=device_id,
                              device=self.devices[device_id],
                              )
        except YomboHookStopProcessing as e:
            pass

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            yield self._YomboAPI.request('DELETE', '/v1/device/%s' % device_id,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't delete device: %s" % e.message,
                'apimsg': "Couldn't delete device: %s" % e.message,
                'apimsghtml': "Couldn't delete device: %s" % e.html_message,
            }

        if called_from_device is not True:
            self.devices[device_id].delete(True)
        try:
            yield global_invoke_all('_device_changed_',
                                    change_type='deleted',
                                    called_by=self,
                                    id=device_id,
                                    device=self.devices[device_id],
                                    )
        except Exception as e:
            pass
        try:
            yield global_invoke_all('_device_deleted_',
                                    called_by=self,
                                    id=self.device_id,
                                    )
        except Exception as e:
            pass

        del self.devices[device_id]

        return {
            'status': 'success',
            'msg': "Device deleted.",
            'device_id': device_id
        }

    @inlineCallbacks
    def edit_device(self, device_id, data, source=None, **kwargs):
        """
        Edit device settings. Accepts a list of items to change. This will also make an API request to update
        the server too.

        :param device_id: The device to edit
        :param data: a dict of items to update.
        :param kwargs:
        :return:
        """
        logger.debug("edit_device date: {data}", data=data)
        if device_id not in self.devices:
            raise YomboWarning("device_id doesn't exist. Nothing to edit.", 300, 'edit_device', 'Devices')

        device = self.devices[device_id]
        try:
            yield global_invoke_all('_device_before_edit_',
                                    called_by=self,
                                    id=device_id,
                                    data=data,
                                    device=device,
                                    )
        except Exception as e:
            pass

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
            return {
                'status': 'failed',
                'msg': "Couldn't edit device",
                'apimsg': e,
                'apimsghtml': e,
                'device_id': '',
            }

        api_data = {}
        for key, value in data.items():
            # print("key (%s) is of type: %s" % (key, type(value)))
            if hasattr(device, key):
                if isinstance(value, str) and len(value) == 0 :
                    # if key == 'energy_map':
                    #     api_data['energy_map'] = json.dumps(value, separators=(',',':'))
                    #     # print("energy map json: %s" % json.dumps(value, separators=(',',':')))
                    # else:
                    continue
                api_data[key] = value

        if source != 'amqp':
            # print("send this data to api: %s" % api_data)
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None
            device_results = yield self._YomboAPI.request('PATCH', '/v1/device/%s' % device_id,
                                                          api_data,
                                                          session=session)
            # print("got this data from api: %s" % device_results)
            if device_results['code'] > 299:
                return {
                    'status': 'failed',
                    'msg': "Couldn't edit device",
                    'apimsg': device_results['content']['message'],
                    'apimsghtml': device_results['content']['html_message'],
                    'device_id': device_id,
                }

            if 'variable_data' in data and len(api_data) > 0:
                variable_results = yield self.set_device_variables(device_results['data']['id'],
                                                                   data['variable_data'],
                                                                   session=session)
                if variable_results['code'] > 299:
                    return {
                        'status': 'failed',
                        'msg': "Device saved, but had problems with saving variables: %s" % variable_results['msg'],
                        'apimsg': variable_results['apimsg'],
                        'apimsghtml': variable_results['apimsghtml'],
                        'device_id': device_id,
                    }

        yield device.device_variables()  # Update device variables cache
        try:
            yield global_invoke_all('_device_changed_',
                                    change_type='edited',
                                    called_by=self,
                                    id=device_id,
                                    device=self.devices[device_id],
                                    )
        except Exception as e:
            pass
        try:
            yield global_invoke_all('_device_edited_',
                                    called_by=self,
                                    id=device_id,
                                    data=data,
                                    device=device,
                                    )
        except Exception as e:
            pass

        if source != 'node':
            device.update_attributes(data, source='parent')
            device.save_to_db()

        yield device.device_variables()

        return {
            'status': 'success',
            'msg': "Device edited.",
            'device_id': device_results['data']['id']
        }

    @inlineCallbacks
    def enable_device(self, device_id, source=None, **kwargs):
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

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            device_results = yield self._YomboAPI.request('PATCH', '/v1/device/%s' % device_id,
                                                          api_data,
                                                          session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't enable device: %s" % e.message,
                'apimsg': "Couldn't enable device: %s" % e.message,
                'apimsghtml': "Couldn't enable device: %s" % e.html_message,
            }

        if source != 'node':
            self.devices[device_id].enable(True)
        try:
            yield global_invoke_all('_device_changed_',
                                    change_type='enabled',
                                    called_by=self,
                                    id=device_id,
                                    device=self.devices[device_id],
                                    )
        except Exception as e:
            pass
        try:
            yield global_invoke_all('_device_enabled_',
                                    called_by=self,
                                    id=self.device_id,
                                    )
        except Exception as e:
            pass
        yield self.devices[device_id].device_variables()
        return {
            'status': 'success',
            'msg': "Device disabled.",
            'device_id': device_results['data']['id']
        }

    @inlineCallbacks
    def disable_device(self, device_id, source=None, **kwargs):
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

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            device_results = yield self._YomboAPI.request('PATCH', '/v1/device/%s' % device_id,
                                                          api_data,
                                                          session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't disable device: %s" % e.message,
                'apimsg': "Couldn't disable device: %s" % e.message,
                'apimsghtml': "Couldn't disable device: %s" % e.html_message,
            }

        if source != 'node':
            self.devices[device_id].disable(True)

        try:
            yield global_invoke_all('_device_changed_',
                                    change_type='disabled',
                                    called_by=self,
                                    id=device_id,
                                    device=self.devices[device_id],
                                    )
        except Exception as e:
            pass
        try:
            yield global_invoke_all('_device_disabled_',
                                    called_by=self,
                                    id=device_id,
                                    device=self.devices[device_id],
                                    )
        except Exception as e:
            pass
        return {
            'status': 'success',
            'msg': "Device disabled.",
            'device_id': device_results['data']['id']
        }
