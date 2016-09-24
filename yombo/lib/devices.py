# cython: embedsignature=True
# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at http://yombo.net
"""
.. rst-class:: floater

.. note::

  For more information see: `Devices @ Projects.yombo.net <https://projects.yombo.net/projects/modules/wiki/Devices>`_

The devices library is primarily responsible for: maintaining device state and
sending commands to devices.

The device (singular) class represents one device.  This class has many functions
that help with utilizing the device.  When possible, this class should be used to
send Yombo Messages for controlling, and getting/setting/querying status. The
device class maintains the current known device state.  Any changes to the device
state are saved to the local database.

To send a command to a device is simple.

*Usage**:

.. code-block:: python

   # Three ways to send a command to a device. Going from easiest method, but less assurance of correct command
   # to most assurance.

   # Lets turn on every device this module manages.
   for item in self._Devices:
       self.Devices[item].do_command(cmd='off')

   # Lets turn off every every device, using a very specific command uuid.
   for item in self._Devices:
       self.Devices[item].do_command(cmd='js83j9s913')  # Made up number, but can be same as off


   # Turn off the christmas tree.
   self._Devices.do_command('christmas tree', 'off')

   # Get devices by device type:
   deviceList = self._DeviceTypes.devices_by_device_type('137ab129da9318')  # This is a function.

   # A simple all x10 lights off (regardless of house / unit code)
   allX10Lamps = self._DeviceTypes.devices_by_device_type('137ab129da9318')
   # Turn off all x10 lamps
   for lamp in allX10Lamps:
       self._Devices.do_command(lamp, 'off')

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from __future__ import print_function
from hashlib import sha1
import copy
from collections import deque, namedtuple
from time import time
import cPickle
from sqlite3 import Binary as sqlite3Binary
from collections import OrderedDict

# Import 3rd-party libs
import yombo.ext.six as six

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, Deferred

# Import Yombo libraries
from yombo.core.exceptions import YomboPinCodeError, YomboDeviceError, YomboFuzzySearchError, YomboWarning
from yombo.utils.fuzzysearch import FuzzySearch
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import random_string, split, global_invoke_all
from yombo.lib.commands import Command  # used only to determine class type
logger = get_logger('library.devices')


class Devices(YomboLibrary):
    """
    Manages all devices and provides the primary interaction interface. The
    primary functions developers should use are:
        - :func:`get_all` - Get a pointer to all devices.
        - :func:`get_devices_by_device_type` - Get all device for a certain deviceType (UUID or MachineLabel)
        - :func:`search` - Get a pointer to a device, using device_id or device label.
    """

    def __contains__(self, device_requested):
        """
        Checks to if a provided device name or device uuid exists.

        Simulate a dictionary when requested with:

            >>> if '137ab129da9318' in self._Devices['137ab129da9318']:  #by uuid

        or:

            >>> if 'living room light' in self._Devices['137ab129da9318']:  #by uuid

        :param device_requested: The device UUID or device label to search for.
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
        Attempts to find the device requested using a couple of methods.

        Simulate a dictionary when requested with:

            >>> self._Devices['137ab129da9318']  #by uuid

        or:

            >>> self._Devices['living room light']  #by name

        :raises YomboDeviceError: Raised when device cannot be found.
        :param device_requested: The device UUID or device label to search for.
        :type device_requested: string
        :return: Pointer to array of all devices.
        :rtype: dict
        """
        return self.get(device_requested)

    def __iter__(self):
        return self._devicesByUUID.__iter__()

    def __len__(self):
        return len(self.self._devicesByUUID)

    def __str__(self):
        return self._devicesByUUID

    def keys(self):
        return self._devicesByUUID.keys()
    def items(self):
        return self._devicesByUUID.items()
    def iteritems(self):
        return self._devicesByUUID.iteritems()
    def iterkeys(self):
        return self._devicesByUUID.iterkeys()
    def itervalues(self):
        return self._devicesByUUID.itervalues()
    def values(self):
        return self._devicesByUUID.values()
    def has_key(self):
        return self._devicesByUUID.has_key()

    def _init_(self):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        :param loader: A pointer to the :mod:`yombo.lib.loader`
        library.
        :type loader: Instance of Loader
        """
        self._AutomationLibrary = self._Loader.loadedLibraries['automation']
        self._VoiceCommandsLibrary = self._Loader.loadedLibraries['voicecmds']
        self._LocalDBLibrary = self._Libraries['localdb']

        self._devicesByUUID = FuzzySearch({}, .99)
        self._devicesByName = FuzzySearch({}, .89)
        self._saveStatusLoop = None
        self.run_state = 1

        # used to store delayed queue for restarts. It'll be a bare, dehydrated version.
        # store the above, but after hydration.
        self.delay_queue_active = {}
        self.delay_queue_unique = {}  # allows us to only create delayed commands for unique instances.

        self.startup_queue = {}  # Place device commands here until we are ready to process device commands
        self.delay_deviceList = {} # list of devices that have pending messages.
        self.processing_commands = False
        # self.init_deferred = Deferred()
        # return self.init_deferred

    def _load_(self):
        self.run_state = 2
        self.start_deferred = Deferred()
        self.__load_devices()
        return self.start_deferred

    def _start_(self):
        self.run_state = 3

        if self._Atoms['loader.operation_mode'] == 'run':
            self.mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming, client_id='devices')
            self.mqtt.subscribe("yombo/devices/+/get")
            self.mqtt.subscribe("yombo/devices/+/cmd")


    def _started_(self):
        self.run_state = 4
        # print("devices: %s" % self._devicesByUUID)

    def _stop_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass

    def _unload_(self):
        """
        Stop periodic loop, save status updates.
        """
        pass

    def _reload_(self):
        return self.__load_devices()

    @inlineCallbacks
    def _load_delay_queue(self):
        self.delay_queue_storage = yield self._Libraries['SQLDict'].get(self, 'delay_queue')
        # Now check to existing delayed messages.  If not too old, send otherwise delete them.  If time is in
        #  future, setup a new reactor to send in future.
        logger.debug("module_started: delayQueue: {delay}", delay=self.delay_queue_storage)
        for request_id in self.delay_queue_storage.keys():
            if self.delay_queue_storage[request_id]['unique_hash'] is not None:
                self.delay_queue_unique[self.delay_queue_storage[request_id]['unique_hash']] = request_id
            if request_id in self.delay_queue_active:
                logger.debug("Message already scheduled for delivery later. Possible from an automation rule. Skipping.")
                continue
            request = self.delay_queue_storage[request_id]
            # print("loading delayed command: %s" % request)
            if float(request['not_before']) < time(): # if delay message time has past, maybe process it.
                if time() - float(request['not_before']) > float(request['max_delay']):
                    # we're too late, just delete it.
                    del self.delay_queue_storage[request_id]
                    continue
                else:
                    #we're good, lets hydrate the request and send it.
                    self.do_command(request['device_id'], request['command_id'], request['kwargs'])

            else: # Still good, but still in the future. Set them up.
                self.do_command(request['device_id'], request['command_id'], request_id=request_id,
                        not_before=request['not_before'],max_delay=request['max_delay'], **request['kwargs'])
        # self.init_deferred.callback(10)
        self.start_deferred.callback(10)


    def _module_started_(self):
        """
        On start, sends all queued messages. Then, check delayed messages for any messages that were missed. Send
        old messages and prepare future messages to run.
        """
        self.processing_commands = True
        for command, request in self.startup_queue.iteritems():
            self.do_command(request['device_id'], request['command_id'], not_before=request['not_before'],
                    max_delay=request['max_delay'], **request['kwargs'])
        self.startup_queue.clear()

    def do_command(self, device, cmd, pin=None, request_id=None, not_before=None, delay=None, max_delay=None, **kwargs):
        """
        Forwarder function to the actual device object for processing.

        :param device: Device ID or Label.
        :param cmd: Command ID or Label to send.
        :param pin: A pin to check.
        :param request_id: A request ID for tracking.
        :param delay: How many seconds to delay sending the command.
        :param kwargs: If a command is not sent at the delay sent time, how long can pass before giving up. For example, Yombo Gateway not running.
        :return:
        """
        return self.get(device).do_command(cmd, pin, request_id, not_before, delay, max_delay, **kwargs)

    @inlineCallbacks
    def __load_devices(self):
        """
        Load the devices into memory. Set up various dictionaries to manage
        devices. This also setups all the voice commands for all the devices.

        This also loads all the device routing. This helps messages and modules determine how to route
        commands between command modules and interface modules.
        """
        devices = yield self._Libraries['LocalDB'].get_devices()
        logger.debug("Loading devices:::: {devices}", devices=devices)
        if len(devices) > 0:
            for record in devices:
                if record['energy_map'] is not None:
                    map = cPickle.loads(str(record['energy_map']))
                    map = OrderedDict(sorted(map.items(), key=lambda (x,y):float(x)))
                    record['energy_map'] = map

                logger.debug("Loading device: {record}", record=record)
                d = yield self.load_device(record)
        yield self._load_delay_queue()

    def load_device(self, record, test_device=False):  # load ore re-load if there was an update.
        """
        Instantiate (load) a new device. Doesn't update database, must call add_update_delete isntead of this.

        **Hooks called**:

        * _device_loaded_ : Sends kwargs: *id* - The new device id.

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :returns: Pointer to new device. Only used during unittest
        """
        device_id = record["id"]
        self._devicesByUUID[device_id] = Device(record, self)
        d = self._devicesByUUID[device_id]._init_()
        self._devicesByName[record["label"]] = device_id

        # print("load_device: %s" % record)
        self._VoiceCommandsLibrary.add_by_string(record["voice_cmd"], None, record["id"], record["voice_cmd_order"])
        # try:
        #     # todo: refactor voicecommands. Need to be able to update/delete them later.
        # except Exception, e:
        #     logger.warn("Error while adding voice command for device: {err}", err=e)


        logger.debug("_add_device: {record}", record=record)

        global_invoke_all('_device_loaded_', **{'id': record['id']})  # call hook "devices_add" when adding a new device.
        return d
#        if test_device:
#            returnValue(self._devicesByUUID[device_id])

    def enable_device(self, device_id):
        """
        Enables a given device id.

        :param device_id:
        :return:
        """
        if device_id not in self._devicesByUUID:
            raise YomboWarning("device_id doesn't exist. Nothing to do.", 300, 'enable_device', 'Devices')
        # self._devicesByUUID[device_id].enable()

    def disable_device(self, device_id):
        """
        Disables a given device id.

        :param device_id:
        :return:
        """
        if device_id not in self._devicesByUUID:
            raise YomboWarning("device_id doesn't exist. Nothing to do.", 300, 'disable_device', 'Devices')
        # self._devicesByUUID[device_id].disable()

    def delete_device(self, device_id):
        """
        Deletes a given device id.

        Behind the scenes, it just updates the database status record

        :param device_id:
        :return:
        """
        if device_id not in self._devicesByUUID:
            raise YomboWarning("device_id doesn't exist. Nothing to do.", 300, 'delete_device', 'Devices')
        # self._devicesByUUID[device_id].delete()

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
        if record['device_id'] not in self._devicesByUUID:
            raise YomboWarning("device_id doesn't exist. Nothing to do.", 300, 'delete_device', 'Devices')
        # self._devicesByUUID[record['device_id']].update(record)

    def delete_device(self, device_id, testDevice=False):
        """
        Delete a device. Not so fun, but life is goes on.

        id, uri, label, notes, description, gateway_id, device_type_id, voice_cmd, voice_cmd_order,
        Voice_cmd_src, pin_code, pin_timeout, created, updated, device_class

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :returns: Pointer to new device. Only used during unittest
        """
        logger.debug("delete_device: {device_id}", device_id=device_id)
        if device_id not in self._devicesByUUID:
            raise YomboWarning("device_id doesn't exist. Nothing to do.", 300, 'delete_device', 'Devices')
        # self._devicesByUUID[device_id].delete()

#        global_invoke_all('devices_delete', **{'id': record['id']})  # call hook "devices_add" when adding a new device.

    def gotException(self, failure):
       print("Exception: %r" % failure)
       return 100  # squash exception, use 0 as value for next stage

    def mqtt_incoming(self, topic, payload, qos, retain):
        """
        Processes incoming MQTT requests. It understands:

        * yombo/devices/DEVICEID|DEVICEMACHINELABEL/get Value - Get some attribute
          * Value = state, human, machine, extra
        * yombo/devices/DEVICEID|DEVICEMACHINELABEL/cmd/CMDID|CMDMACHINELABEL Options - Send a command
          * Options - Either a string for a single variable, or json for multiple variables

        Examples: /yombo/devices/get/christmas_tree/cmd on

        :param topic:
        :param payload:
        :param qos:
        :param retain:
        :return:
        """
        #  0       1       2       3        4
        # yombo/devices/DEVICEID/get|cmd/option
        parts = topic.split('/', 10)
        print("Yombo Devices got this: %s / %s" % (topic, parts))

        try:
            device = self.get(parts[2].replace("_", " "))
        except YomboDeviceError, e:
            logger.info("Received MQTT request for a device that doesn't exist")
            return

#Status = namedtuple('Status', "device_id, set_time, human_status, machine_status, machine_status_extra, source, uploaded, uploadable")

        if parts[3] == 'get':
            status = device.get_status()
            if payload == 'human':
                self.mqtt.publish('yombo/devices/%s/state/human' % device.label.replace(" ", "_"), str(status.human_status))
            elif payload == 'machine':
                self.mqtt.publish('yombo/devices/%s/state/machine' % device.label.replace(" ", "_"), str(status.machine_status))
            elif payload == 'extra':
                self.mqtt.publish('yombo/devices/%s/state/extra' % device.label.replace(" ", "_"), str(status.machine_status_extra))
            elif payload == 'last':
                self.mqtt.publish('yombo/devices/%s/state/last' % device.label.replace(" ", "_"), str(status.set_time))
            elif payload == 'source':
                self.mqtt.publish('yombo/devices/%s/state/source' % device.label.replace(" ", "_"), str(status.source))
        elif parts[3] == 'cmd':
            device.do_command(self, cmd=parts[4])
            if len(parts) > 5:
                status = device.get_status()
                if parts[5] == 'human':
                    self.mqtt.publish('yombo/devices/%s/state/human' % device.label.replace(" ", "_"), str(status.human_status))
                elif parts[5] == 'machine':
                    self.mqtt.publish('yombo/devices/%s/state/machine' % device.label.replace(" ", "_"), str(status.machine_status))
                elif parts[5] == 'extra':
                    self.mqtt.publish('yombo/devices/%s/state/extra' % device.label.replace(" ", "_"), str(status.machine_status_extra))
                elif parts[5] == 'last':
                    self.mqtt.publish('yombo/devices/%s/state/last' % device.label.replace(" ", "_"), str(status.set_time))
                elif parts[5] == 'source':
                    self.mqtt.publish('yombo/devices/%s/state/source' % device.label.replace(" ", "_"), str(status.source))

    def _clear_(self):
        """
        Clear all devices. Should only be called by the loader module
        during a reconfiguration event. **Do not call this function!**
        """
        self._devicesByUUID.clear()
        self._devicesByName.clear()
        self._devicesByDeviceTypeByUUID.clear()

    def list_devices(self):
        return list(self._devicesByName.keys())

    def get(self, device_requested, limiter_override=.99):
        """
        Performs the actual device search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find commands: `self._Devices['8w3h4sa']`

        :raises YomboDeviceError: Raised when device cannot be found.
        :param device_requested: The device UUID or device label to search for.
        :type deviceRequested: string
        :return: Pointer to array of all devices.
        :rtype: dict
        """
        logger.debug("looking for: {device_id}", device_id=device_requested)
        if device_requested in self._devicesByUUID:
            logger.debug("found by device id! {device_id}", device_id=device_requested)
            return self._devicesByUUID.search2(device_requested, limiter_override)
        else:
            try:
                requestedUUID = self._devicesByName[device_requested]
                logger.debug("found by device name! {device_id}", device_id=device_requested)
                return self._devicesByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
                raise YomboDeviceError('Searched for %s, but no good matches found.' % e.searchFor, searchFor=e.searchFor, key=e.key, value=e.value, ratio=e.ratio, others=e.others)

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
            { 'platform': 'devices',
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
#                print "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$  00011"
                device = self.get(portion['source']['device'], .89)
#                print "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$  00022"
                portion['source']['device_pointers'] = device
#                print "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$  00033"
                return portion
            except Exception, e:
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
              'do_action_callback': self.devices_do_action_callback  # function to be called to perform an action
            }
         ]

    def devices_validate_action_callback(self, rule, action, **kwargs):
        """
        A callback to check if a provided action is valid before being added as a possible action.

        :param rule: The potential rule being added.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
#        print "devices - kwargs: %s" % action
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
            except:
                raise YomboWarning("Error while searching for device, could not be found: %s" % action['device'],
                               104, 'devices_validate_action_callback', 'lib.devices')
        else:
            raise YomboWarning("For platform 'devices' as an 'action', must have 'device' and can be either device ID or device label.",
                               105, 'devices_validate_action_callback', 'lib.devices')

    def devices_do_action_callback(self, rule, action, options={}, **kwargs):
        """
        A callback to perform an action.

        :param rule: The complete rule being fired.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        logger.error("firing device rule: {rule}", rule=rule)
        logger.error("rule options: {options}", options=options)
        for device in action['device_pointers']:
            delay = None
            if 'delay' in options and options['delay'] is not None:
                logger.debug("setting up a delayed command for {seconds} seconds in the future.", seconds=options['delay'])
                delay=options['delay']

                if 'max_delay' in options:
                    max_delay=options['max_delay']
                else:
                    max_delay=60  # allow up to 60 seconds to pass...
            else:
                delay = None
                max_delay = None

            # def do_command(self, cmd, pin=None, request_id=None, not_before=None, delay=None, max_delay=None, **kwargs):

            unique_hash = sha1('automation' + rule['name'] + action['command'] + device.label).hexdigest()
            device.do_command(cmd=action['command'], delay=delay, max_delay=max_delay, **{'unique_hash': unique_hash})


class Device:
    """
    A class to manage a single device.  This clas contains various attributes
    about a device and can perform function on behalf of a device.  Can easily
    send a Yombo :ref:`Message` using a device instance.

    The self.status attribute stores the last 30 states the device has been in.

    Device: An item which was specified by a user or module that can be
    controlled and/or queried for status.  Examples include a lamp
    module, curtains, Plex client, rain sensor, etc.
    """
    def __init__(self, device, _DevicesLibrary, testDevice=False):
        """
        :param device: *(list)* - A device as passed in from the devices class. This is a
            dictionary with various device attributes.
        :ivar callBeforeChange: *(list)* - A list of functions to call before this device has it's status
            changed. (Not implemented.)
        :ivar callAfterChange: *(list)* - A list of functions to call after this device has it's status
            changed. (Not implemented.)
        :ivar device_id: *(string)* - The UUID of the device.
        :type device_id: string
        :ivar device_type_id: *(string)* - The device type UUID of the device.
        :ivar label: *(string)* - Device label as defined by the user.
        :ivar description: *(string)* - Device description as defined by the user.
        :ivar enabled: *(bool)* - If the device is enabled - can send/receive command and/or
            status updates.
        :ivar pin_required: *(bool)* - If a pin is required to access this device.
        :ivar pin_code: *(string)* - The device pin number.
            system to deliver commands and status update requests.
        :ivar created: *(int)* - When the device was created; in seconds since EPOCH.
        :ivar updated: *(int)* - When the device was last updated; in seconds since EPOCH.
        :ivar last_command: *(dict)* - A dictionary of up to the last 30 command messages.
        :ivar status_history: *(dict)* - A dictionary of strings for current and up to the last 30 status values.
        :ivar device_variables: *(dict)* - The device variables as defined by various modules, with
            values entered by the user.
        :ivar available_commands: *(list)* - A list of command_id's that are valid for this device.
        """
        self._DevicesLibrary = _DevicesLibrary
        logger.debug("New device - info: {device}", device=device)

        self.StatusTuple = namedtuple('Status', "device_id, set_time, energy_usage, human_status, machine_status, machine_status_extra, source, uploaded, uploadable")
        self.Command = namedtuple('Command', "time, cmduuid, source")

        self.call_before_command = []
        self.call_after_command = []

        self.device_id = device["id"]
        self.device_type_id = device["device_type_id"]
        self.label = device["label"]
        self.description = device["description"]
        self.enabled = int(device["status"])  # status from database means enabled or not.
        self.pin_required = int(device["pin_required"])
        self.pin_code = device["pin_code"]
        self.pin_timeout = int(device["pin_timeout"])
        self.voice_cmd = device["voice_cmd"]
        self.voice_cmd_order = device["voice_cmd_order"]
        self.location_label = device["location_label"]  # 'myhome.groundfloor.kitchen'
        self.created = int(device["created"])
        self.updated = int(device["updated"])
        self.updated_srv = int(device["updated_srv"])


        self.energy_type = None  # electric, gas, etc.
        self.energy_tracker_source = None  # Source of tracking: None, calc, device
        self.energy_tracker_device = None  # Only required if above is 'device'
        self.energy_map = None  # Used to calculate energy usage

        if 'energy_type' in device:
            self.energy_type = device['energy_type']
        if 'energy_tracker_source' in device:
            self.energy_tracker_source = device['energy_tracker_source']
            if self.energy_tracker_source == 'calc':
                self.energy_map = {float(k):v for k,v in device['energy_map'].items()}  # fix for JSON
            elif self.energy_tracker_source == 'device':
                self.energy_tracker_device = device['energy_tracker_device']

        self.last_command = deque({}, 30)
        self.status_history = deque({}, 30)
        self.testDevice = testDevice
        self.device_variables = {'asdf':'qwer'}
        self.device_route = {}  # Destination module to send commands to
        self._helpers = {}  # Helper class provided by route module that can provide additional features.
        self._CommandsLibrary = self._DevicesLibrary._Libraries['commands']

        # this registers the device's device type so others know what kind of device this is.
        self._registered_device_type = self._DevicesLibrary._DeviceTypes.add_registered_device(self)

        if device['status'] == 1:
            self.enabled = True
        else:
            self.enabled = False

    def __str__(self):
        """
        Print a string when printing the class.  This will return the device_id so that
        the device can be identified and referenced easily.
        """
        return self.device_id

    def _init_(self):
        """
        Performs items that required deferreds.
        :return:
        """
        # def set_commands(commands):
        #     for command in commands:
        #         self.available_commands.append(str(command.command_id))

        def set_variables(vars):
            # print("GOT DEVICE VARS!!!!! %s" % vars)
            self.device_variables = vars

        def gotException(failure):
           print("Exception : %r" % failure)
           return 100  # squash exception, use 0 as value for next stage

        # d = self._DevicesLibrary._Libraries['localdb'].get_commands_for_device_type(self.device_type_id)
        # d.addCallback(set_commands)
        # d.addErrback(gotException)
        # d.addCallback(lambda ignored: self._DevicesLibrary._Libraries['localdb'].get_variables('device', self.device_id))

        d = self._DevicesLibrary._Libraries['localdb'].get_variables('device', self.device_id)
        d.addErrback(gotException)
        d.addCallback(set_variables)
        d.addErrback(gotException)

        if self.testDevice is False:
            d.addCallback(lambda ignored: self.load_history(35))
        return d

    def available_commands(self):
        # print("getting available_commands for devicetypeid: %s" % (self.device_type_id, ))
        return self._DevicesLibrary._DeviceTypes.device_type_commands(self.device_type_id)

    def dump(self):
        """
        Export device variables as a dictionary.
        """
        return {'device_id': str(self.device_id),
                'device_type_id': str(self.device_type_id),
                'label': str(self.label),
                'description': str(self.description),
                'enabled': int(self.enabled),
                'pin_code': "********",
                'pin_required':  int(self.pin_required),
                'pin_timeout': int(self.pin_timeout),
                'voice_cmd': str(self.voice_cmd),
                'voice_cmd_order': str(self.voice_cmd_order),
                'created': int(self.created),
                'updated': int(self.updated),
                'status_history': copy.copy(self.status_history),
               }

    def do_command(self, cmd, pin=None, request_id=None, not_before=None, delay=None, max_delay=None, **kwargs):
        """
        Do a command. Will call _do_command_ hook so modules can process the request.

        If a pin is required, "pin" must be included as one of the arguments. All **kwargs are sent with the
        hook call.

        :raises YomboDeviceError: Raised when:

            - cmd doesn't exist
            - delay or max_delay is not a float or int.

        :raises YomboPinCodeError: Raised when:

            - pin is required but not recieved one.

        :param cmd: Command ID or Label to send.
        :param pin: A pin to check.
        :param request_id: Request ID for tracking.
        :param delay: How many seconds to delay sending the command.
        :param kwargs: If a command is not sent at the delay sent time, how long can pass before giving up. For example, Yombo Gateway not running.
        :return:
        """
        if self.pin_required == 1:
                if pin is None:
                    raise YomboPinCodeError("'pin' is required, but missing.")
                else:
                    if self.pin_code != pin:
                        raise YomboPinCodeError("'pin' supplied is incorrect.")

        logger.debug("device kwargs: {kwargs}", kwargs=kwargs)

        if isinstance(cmd, Command):
            cmdobj = cmd
        else:
            cmdobj = self._CommandsLibrary.get_command(cmd)

        # print("cmdobj is: %s" % cmdobj)

#        if self.validate_command(cmdobj) is not True:
        if str(cmdobj.command_id) not in self.available_commands():
            logger.warn("Requested command: {cmduuid}, but only have: {ihave}",
                        cmduuid=cmdobj.command_id, ihave=self.available_commands())
            raise YomboDeviceError("Invalid command requested for device.", errorno=103)

        cur_time = time()
        # print("in device do_command: request_id: %s" % request_id)
        # print("in device do_command: kwargs: %s" % kwargs)
        # print("in device do_command: self._DevicesLibrary.delay_queue_unique: %s" % self._DevicesLibrary.delay_queue_unique)

        if request_id is None:
            if 'unique_hash' in kwargs:
                unique_hash = kwargs['unique_hash']
            else:
                unique_hash = None
            if unique_hash in self._DevicesLibrary.delay_queue_unique:
                request_id = self._DevicesLibrary.delay_queue_unique[unique_hash]
            else:
                request_id = random_string(length=16)
        # print("in device do_command: rquest_id 2: %s" % request_id)

        if delay is not None or not_before is not None:  # if we have a delay, make sure we have required items
            if max_delay is None:
                    raise YomboDeviceError("'max_delay' Is required when delay or not_before is set!")
            if isinstance(max_delay, six.integer_types) or isinstance(max_delay, float):
                if max_delay < 0:
                    raise YomboDeviceError("'max_delay' should be positive only.")

        if not_before is not None:
            if isinstance(not_before, six.integer_types) or isinstance(not_before, float):
                if not_before < cur_time:
                    raise YomboDeviceError("'not_before' time should be epoch second in the future, not the past.")

                when = not_before - time()
                if request_id not in self._DevicesLibrary.delay_queue_storage:  # condition incase it's a reload
                    self._DevicesLibrary.delay_queue_storage[request_id] = {
                        'command_id': cmdobj.command_id,
                        'device_id': self.device_id,
                        'not_before': not_before,
                        'max_delay': max_delay,
                        'unique_hash': unique_hash,
                        'request_id': request_id,
                        'kwargs': kwargs,
                    }
                self._DevicesLibrary.delay_queue_active[request_id] = {
                    'command': cmdobj,
                    'device': self,
                    'not_before': not_before,
                    'max_delay': max_delay,
                    'kwargs': kwargs,
                    'request_id': request_id,
                    'reactor': None,
                }
                self._DevicesLibrary.delay_queue_active[request_id]['reactor'] = reactor.callLater(when, self.do_command_delayed, request_id)
            else:
                raise YomboDeviceError("not_before' must be a float or int.")

        elif delay is not None:
            # print("delay = %s" % delay)
            if isinstance(delay, six.integer_types) or isinstance(delay, float):
                if delay < 0:
                    raise YomboDeviceError("'delay' should be positive only.")

                when = time() + delay
                if request_id not in self._DevicesLibrary.delay_queue_storage:  # condition incase it's a reload
                    self._DevicesLibrary.delay_queue_storage[request_id] = {
                        'command_id': cmdobj.command_id,
                        'device_id': self.device_id,
                        'not_before': when,
                        'max_delay': max_delay,
                        'kwargs': kwargs,
                        'unique_hash': unique_hash,
                        'request_id': request_id,
                    }
                self._DevicesLibrary.delay_queue_active[request_id] = {
                    'command': cmdobj,
                    'device': self,
                    'not_before': when,
                    'max_delay': max_delay,
                    'kwargs': kwargs,
                    'request_id': request_id,
                    'reactor': None,
                }
                self._DevicesLibrary.delay_queue_unique[unique_hash] = request_id
                self._DevicesLibrary.delay_queue_active[request_id]['reactor'] = reactor.callLater(when, self.do_command_delayed, request_id)
            else:
                raise YomboDeviceError("'not_before' must be a float or int.")

        else:
            kwargs['request_id'] = request_id
            self.do_command_hook(cmdobj, kwargs)
        return request_id

    def do_command_delayed(self, request_id):
        request = self._DevicesLibrary.delay_queue_active[request_id]
        request['kwargs']['request_id'] = request_id
        self.do_command_hook(request['command'], request['kwargs'])
        del self._DevicesLibrary.delay_queue_storage[request_id]
        del self._DevicesLibrary.delay_queue_active[request_id]

    def do_command_hook(self, cmdobj, kwargs):
        """
        Performs the actual sending of a device command. It does this through the hook system. This allows any module
        to setup any monitoring, or perfom the actual action.

        When a device changes state, whatever module changes the state of a device, or is responsible for reporting
        those changes, it *must* call "self._Devices['devicename/deviceid'].set_state()

        **Hooks called**:

        * _devices_command_ : Sends kwargs: *device*, the device object and *command*. This receiver will be
          responsible for obtaining whatever information it needs to complete the action being requested.

        :param cmdobj:
        :param kwargs:
        :return:
        """
        kwargs['command'] = cmdobj
        kwargs['device'] = self
        global_invoke_all('_device_command_', **kwargs)
        self._DevicesLibrary._Statistics.increment("lib.devices.commands_sent", anon=True)

    def energy_get_usage(self, machine_status):
        """
        Determine the current energy usage.  Currently only support energy maps.

        :param machine_status: New status
        :return:
        """
        if self.energy_tracker_source == 'calc':
            return self.energy_calc(machine_status)
        return 0

    def energy_calc(self, machine_status):
        """
        Returns the energy being used based on a percentage the device is on.  Inspired by:
        http://stackoverflow.com/questions/1969240/mapping-a-range-of-values-to-another

        :param machine_status:
        :param map:
        :return:
        """
        # map = {
        #     0: 1,
        #     0.5: 100,
        #     1: 400,
        # }

        if self.energy_map == None:
            return 0   # if no map is found, we always return 0

        items = self.energy_map.items()
        for i in range(0, len(self.energy_map)-1):
            if items[i][0] <= machine_status <= items[i+1][0]:
                # print "translate(key, items[counter][0], items[counter+1][0], items[counter][1], items[counter+1][1])"
                # print "%s, %s, %s, %s, %s" % (key, items[counter][0], items[counter+1][0], items[counter][1], items[counter+1][1])
                return self.energy_translate(machine_status, items[i][0], items[i+1][0], items[i][1], items[i+1][1])
        raise KeyError("Cannot find map value for: %s  Must be between 0 and 1" % machine_status)

    def energy_translate(self, value, leftMin, leftMax, rightMin, rightMax):
        """
        Calculates the energy consumed based on the energy_map.

        :param value:
        :param leftMin:
        :param leftMax:
        :param rightMin:
        :param rightMax:
        :return:
        """
        # Figure out how 'wide' each range is
        leftSpan = leftMax - leftMin
        rightSpan = rightMax - rightMin
        # Convert the left range into a 0-1 range (float)
        valueScaled = float(value - leftMin) / float(leftSpan)
        # Convert the 0-1 range into a value in the right range.
        return rightMin + (valueScaled * rightSpan)

    def get_status(self, history=0):
        """
        Gets the history of the device status.

        :param history: How far back to go. 0 = previoius, 1 - the one before that, etc.
        :return:
        """
        return self.status_history[history]

    def set_status(self, **kwargs):
        """
        Usually called by the device's command/logic module to set/update the
        device status. This can also be called externally as needed.

        :raises YomboDeviceError: Raised when:

            - If no valid status sent in. Errorno: 120
            - If statusExtra was set, but not a dictionary. Errorno: 121
            - If payload was set, but not a dictionary. Errorno: 122
        :param kwargs: key/value dictionary with the following keys-

            - human_status *(int or string)* - The new status.
            - machine_status *(int or string)* - The new status.
            - machine_status_extra *(dict)* - Extra status as a dictionary.
            - source *(string)* - The source module or library name creating the status.
            - silent *(any)* - If defined, will not broadcast a status update
              message; atypical.
            - payload *(dict)* - a dict to be appended to the payload portion of the
              status message.
        """
        logger.debug("set_status called...: {kwargs}", kwargs=kwargs)
        self._set_status(**kwargs)
        if 'silent' not in kwargs:
            self.send_status(**kwargs)

    def _set_status(self, **kwargs):
        logger.debug("_set_status called...")
        machine_status = None
        if 'machine_status' not in kwargs:
            raise YomboDeviceError("set_status was called without a real machine_status!", errorno=120)

        human_status = kwargs.get('human_status', machine_status)
        machine_status = kwargs['machine_status']
        machine_status_extra = kwargs.get('machine_status_extra', '')
        energy_usage = self.energy_get_usage(machine_status)
        source = kwargs.get('source', 'unknown')
        uploaded = kwargs.get('uploaded', 0)
        uploadable = kwargs.get('uploadable', 0)
        set_time = time()

        new_status = self.StatusTuple(self.device_id, set_time, energy_usage, human_status, machine_status, machine_status_extra, source, uploaded, uploadable)
        self.status_history.appendleft(new_status)
        if self.testDevice is False:
            self._DevicesLibrary._LocalDBLibrary.save_device_status(**new_status.__dict__)
        self._DevicesLibrary.check_trigger(self.device_id, new_status)

    def send_status(self, **kwargs):
        """
        Tell the message system to broadcast the current status of a device. This
        is typically only called internally when a device status changes. Shouldn't
        need to call this from a module. Just send a command to the device and
        this function will be called automatically as needed.

        :param kwargs:
        :return:
        """
        return  #todo: convert to hook
        logger.debug("send_status called...")
        if 'dest' in kwargs:
            dest = kwargs['dest']
        else:
            dest = 'yombo.gateway.all'
        if 'src' in kwargs:
            src = kwargs['src']
        else:
            src = 'yombo.gateway.core.device'
        if 'payloadAddon' in kwargs:
            payloadAddon = kwargs['payloadAddon']
        else:
            payloadAddon = {}

        payload = {"deviceobj" : self,
                   "status" : self.status_history[0],
                   "previous_status" : self.status_history[1],
                  }
        try:
            payload.update(payloadAddon)
        except:
            pass
        self._DevicesLibrary._Statistics.increment("lib.devices.status_change", anon=True)
        msg = {
               'msgOrigin'     : src,
               'msgDestination': dest,
               'msgType'       : "status",
               'msgStatus'     : "new",
               'msgStatusExtra': "",
               'uuidtype'      : "APDS",
               'payload'       : payload,
              }
        message = Message(**msg)
        message.send()

    def remove_delayed(self):
        """
        Remove any messages that might be set to be called later that
        relates to this device.  Easy, just tell the messages library to 
        do that for us.
        """
        self._DevicesLibrary._MessageLibrary.device_delay_cancel(self.device_id)

    def get_delayed(self):
        """
        List messages that are to be sent at a later time.
        """
        self._DevicesLibrary._MessageLibrary.device_delay_list(self.device_id)

    def load_history(self, howmany=35):
        """
        Loads device history into the device instance. This method gets the data from the db and adds a callback
        to _do_load_history to actually set the values.

        :param howmany:
        :return:
        """
        d =  self._DevicesLibrary._Libraries['LocalDB'].get_device_status(id=self.device_id, limit=howmany)
        d.addCallback(self._do_load_history)
        return d

    def _do_load_history(self, records):
        if len(records) == 0:
            self.status_history.append(self.StatusTuple(self.device_id, 0, 0, 'NA', 'NA', {}, '', 0, 0))
        else:
            for record in records:
                self.status_history.appendleft(self.StatusTuple(record['device_id'], record['set_time'], record['energy_usage'], record['human_status'], record['machine_status'],record['machine_status_extra'], record['source'], record['uploaded'], record['uploadable']))
#                              self.StatusTuple = namedtuple('Status',  "device_id,           set_time,          energy_usage,           human_status,           machine_status,                             machine_status_extra,             source,           uploaded,           uploadable")

        #logger.debug("Device load history: {device_id} - {status_history}", device_id=self.device_id, status_history=self.status_history)

    def validate_command(self, command_id):
#        print "checking cmdavail for %s, looking for '%s': %s" % (self.label, command_id, self.available_commands)
        if str(command_id) in self.available_commands():
            return True
        else:
            return False

    def update(self, record):
                # try:
        #     # todo: refactor voicecommands. Need to be able to update/delete them later.
        #     self._VoiceCommandsLibrary.add(record["voice_cmd"], "", record["id"], record["voice_cmd_order"])
        # except:
        #     pass

        if 'label' in record:
            self._DevicesLibrary._devicesByName[record['label']] = self._devicesByName.pop(record["label"])  # Update label searching
            self.label = record['label']

        # check if device_type_id changes.
        if 'device_type_id' in record:
            if record['device_type_id'] != self.device_type_id:
                del self._DevicesLibrary._DeviceTypes. _devicesByDeviceTypeByUUID[self.device_type_id][self.device_id]
                self.device_type_id = record['device_type_id']
                self._DevicesLibrary._devicesByDeviceTypeByUUID[self.device_type_id][self.device_id]

        # global_invoke_all('_devices_update_', **{'id': record['id']})  # call hook "device_update" when adding a new device.
