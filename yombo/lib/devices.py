# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
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
       self.Devices[item].get_message(self, cmd='off')

   # Lets turn off every every device, using a very specific command uuid.
   for item in self._Devices:
       self.Devices[item].get_message(self, cmd='js83j9s913')  # Made up number, but can be same as off

   # Lets turn off every every device, using the command object itself.

   off_commands = self._Commands['off']  # Lets search for the command itself, we'll get an object back.
   # Now, lets just pass that command object in. In this demo, this is basically the same as verions 1 above,
   # but is shown as an example.
   for item in self._Devices:
       self.Devices[item].get_message(self, cmd='js83j9s913')  # Made up number, but can be same as off


   if self._Atom['os'] != None:
       logger.debug("Running on operating system: {operatingsystem}", operatingsystem=self._Atom['os'])

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import copy
from collections import deque, namedtuple
from time import time

# Import 3rd-party libs
import yombo.ext.six as six

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, Deferred

# Import Yombo libraries
from yombo.core.exceptions import YomboPinCodeError, YomboDeviceError, YomboFuzzySearchError, YomboWarning
from yombo.utils.fuzzysearch import FuzzySearch
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
from yombo.core.message import Message
from yombo.utils import random_string


logger = getLogger('library.devices')

class Devices(YomboLibrary):
    """
    Manages all devices and provides the primary interaction interface. The
    primary functions developers should use are:
        - :func:`get_device` - Get a pointer to all devices.
        - :func:`get_devices_by_device_type` - Get all device for a certain deviceType (UUID or MachineLabel)
        - :func:`search` - Get a pointer to a device, using device_id or device label.
    """
    def __contains__(self, deviceRequested):
        """
        Checks to if a provided device name or device uuid exists.

        Simulate a dictionary when requested with:
            >>> if '137ab129da9318' in self._Devices['137ab129da9318']:  #by uuid
        or:
            >>> if 'living room light' in self._Devices['137ab129da9318']:  #by uuid

        See: :func:`yombo.utils.get_devices` for full usage example.

        :param deviceRequested: The device UUID or device label to search for.
        :type deviceRequested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get_device(deviceRequested)
            return True
        except:
            return False

    def __getitem__(self, deviceRequested):
        """
        Attempts to find the device requested using a couple of methods.

        Simulate a dictionary when requested with:
            >>> self._Devices['137ab129da9318']  #by uuid
        or:
            >>> self._Devices['living room light']  #by name

        See: :func:`yombo.utils.get_devices` for full usage example.

        :raises YomboDeviceError: Raised when device cannot be found.
        :param deviceRequested: The device UUID or device label to search for.
        :type deviceRequested: string
        :return: Pointer to array of all devices.
        :rtype: dict
        """
        return self.get_device(deviceRequested)

    def __iter__(self):
        return self._devicesByUUID.__iter__()

    def _init_(self, loader):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        :param loader: A pointer to the :mod:`yombo.lib.loader`
        library.
        :type loader: Instance of Loader
        """
        self.loader = loader
        self._MessageLibrary = self.loader.loadedLibraries['messages']
        self._ModulesLibrary = self.loader.loadedLibraries['modules']
        self._AutomationLibrary = self.loader.loadedLibraries['automation']
        self._VoiceCommandsLibrary = self.loader.loadedLibraries['voicecmds']
        self._LocalDBLibrary = self._Libraries['localdb']

        self._devicesByUUID = FuzzySearch({}, .99)
        self._devicesByName = FuzzySearch({}, .89)
        self._devicesByDeviceTypeByUUID = {}
        self._devicesByDeviceTypeByName = FuzzySearch({}, .94)
        self._status_updates_to_save = {}
        self._saveStatusLoop = None

    def _load_(self):
        pass

    def _start_(self):
        """
        Load devices, and load some of the device history. Setup looping
        call to periodically save any updated device status.
        """
        self.__load_devices()
        self.loadDefer = Deferred()

        self._saveStatusLoop = LoopingCall(self._save_status)
        self._saveStatusLoop.start(120, False)

        return self.loadDefer

    def _stop_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        if hasattr(self, '_saveStatusLoop') and self._saveStatusLoop is not None and self._saveStatusLoop.running is True:
            self._saveStatusLoop.stop()

    def _unload_(self):
        """
        Stop periodic loop, save status updates.
        """
        self._save_status()

    def _reload_(self):
        return self.__load_devices()

    @inlineCallbacks
    def __load_devices(self):
        """
        Load the devices into memory. Set up various dictionaries to manage
        devices. This also setups all the voice commands for all the devices.
        """
        devices = yield self._Libraries['LocalDB'].get_devices()
        self.__do_load_devices(devices)

    def gotException(self, failure):
       print "Exception: %r" % failure
       return 100  # squash exception, use 0 as value for next stage

    @inlineCallbacks
    def __do_load_devices(self, records):
        """
        Load the devices into memory. Set up various dictionaries to manage
        devices. This also setups all the voice commands for all the devices.
        """
        logger.debug("Loading devices:::: {records}", records=records)
        if len(records) > 0:
            for record in records:
                logger.debug("Loading device: {record}", record=record)
                try:
                    self._VoiceCommandsLibrary.add(record["voice_cmd"], "", record["id"], record["voice_cmd_order"])
                except:
                    pass
                d = yield self._add_device(record)

        self.loadDefer.callback(10)

    def _add_device(self, record, testDevice=False):
        """
        Add a device based on data from a row in the SQL database.

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :returns: Pointer to new device. Only used during unittest
        """
        device_id = record["id"]
        self._devicesByUUID[device_id] = Device(record, self)
        d = self._devicesByUUID[device_id]._init_()
        self._devicesByName[record["label"]] = device_id

        logger.debug("_add_device: {record}", record=record)
        if record['device_type_id'] not in self._devicesByDeviceTypeByUUID:
            self._devicesByDeviceTypeByUUID[record['device_type_id']] = {}
        if device_id not in self._devicesByDeviceTypeByUUID[record['device_type_id']]:
            self._devicesByDeviceTypeByUUID[record['device_type_id']][device_id] = self._devicesByUUID[device_id]

        if record['device_type_machine_label'] not in self._devicesByDeviceTypeByName:
            self._devicesByDeviceTypeByName[record['device_type_machine_label']] = record['device_type_id']

        return d
#        if testDevice:
#            returnValue(self._devicesByUUID[device_id])

    def _save_status(self):
        """
        Function that does actual work. Saves items in the self._toStaveStatus
        queue to the SQLite database.
        """
        if len(self._status_updates_to_save) == 0:
            return

        logger.info("Saving device status to disk.")
        for key in self._status_updates_to_save.keys():
            ss = self._status_updates_to_save[key]
            self._LocalDBLibrary.save_device_status(**ss.__dict__)
            del self._status_updates_to_save[key]

    def _clear_(self):
        """
        Clear all devices. Should only be called by the loader module
        during a reconfiguration event. **Do not call this function!**
        """
        self._save_status()
        self._devicesByUUID.clear()
        self._devicesByName.clear()
        self._devicesByDeviceTypeByUUID.clear()
        self._devicesByDeviceTypeByName.clear()

    def listDevices(self):
        return list(self._devicesByName.keys())

    def get_device(self, device_requested, limiter_override=.99):
        """
        Performs the actual device search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find commands: `self._Devices['8w3h4sa']`

        See: :func:`yombo.core.helpers.get_device` for full usage example.

        :raises YomboDeviceError: Raised when device cannot be found.
        :param device_requested: The device UUID or device label to search for.
        :type deviceRequested: string
        :return: Pointer to array of all devices.
        :rtype: dict
        """
        logger.debug("looking for: {device_id}", device_id=device_requested)
        if device_requested in self._devicesByUUID:
            logger.debug("found by device id! {device_id}", device_id=device_requested)
            return self._devicesByUUID._search(self, device_requested, limiter_override)
        else:
            try:
                requestedUUID = self._devicesByName[device_requested]
                logger.debug("found by device name! {device_id}", device_id=device_requested)
                return self._devicesByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
                raise YomboDeviceError('Searched for %s, but no good matches found.' % e.searchFor, searchFor=e.searchFor, key=e.key, value=e.value, ratio=e.ratio, others=e.others)

    def get_devices_by_device_type(self, device_type_requested):
        """
        Returns list of devices by deviceType. Will search by DeviceType UUID or MachineLabel.

        :raises YomboDeviceError: Raised when function encounters an error.
        :param device_type_requested: The device UUID or device label to search for.
        :type device_type_requested: string
        :return: Pointer to array of all devices for requested device type
        :rtype: dict
        """
        logger.debug("## _devicesByDeviceTypeByUUID: {devicesByDeviceTypeByUUID}", devicesByDeviceTypeByUUID=self._devicesByDeviceTypeByUUID)
#        logger.debug("## deviceTypeRequested: {deviceTypeRequested}", deviceTypeRequested=deviceTypeRequested)
        if device_type_requested in self._devicesByDeviceTypeByUUID:
            logger.debug("## {devicesByDeviceTypeByUUID}", devicesByDeviceTypeByUUID=self._devicesByDeviceTypeByUUID[device_type_requested])
            return self._devicesByDeviceTypeByUUID[device_type_requested]
        else:
            try:
                requestedUUID = self._devicesByDeviceTypeByName[device_type_requested]
#                logger.debug("## _devicesByDeviceTypeByUUID: {requestedUUID}", requestedUUID=self._devicesByDeviceTypeByUUID)
#                logger.debug("## _devicesByDeviceTypeByName: {requestedUUID}", requestedUUID=self._devicesByDeviceTypeByName)
#                logger.debug("## deviceTypeRequested: {deviceTypeRequested}", deviceTypeRequested=deviceTypeRequested)
#                logger.debug("## requestedUUID: {requestedUUID}", requestedUUID=requestedUUID)
                return self._devicesByDeviceTypeByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
#                logger.debug("e={e}", e=e)
                return {}

    # The remaining functions implement automation hooks. These should not be called by anything other than the
    # automation library!

    def check_trigger(self, key, value):
        """
        Called by the devices.set function when a new value is set. It asks the automation library if this key is
        trigger, and if so, fire any rules.

        True - Rules fired, fale - no rules fired.
        """

        results = self._AutomationLibrary.triggers_check('devices', key, value)

    def Devices_automation_source_list(self, **kwargs):
        """
        hook_automation_source_list called by the automation library to get a list of possible sources.

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
        A callback to check if a provided source is valid before being added as a possible source.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the portion of rule being fired. Includes source, filter, etc.
        :return:
        """
        if 'platform' not in portion['source']:
            raise YomboWarning("'platform' must be in 'source' section.")

        if 'device' in portion['source']:
            try:
#                print "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$  00011"
                device = self.get_device(portion['source']['device'], .89)
#                print "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$  00022"
                portion['source']['device_pointer'] = device
#                print "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$  00033"
                return portion
            except Exception, e:
                raise YomboWarning("Error while searching for device, could not be found: %s" % source['device'],
                                   101, 'devices_validate_source_callback', 'lib.devices')
        else:
            raise YomboWarning("For platform 'devices' as a 'source', must have 'device' and can be either device ID or device label.  Source:%s" % source,
                               102, 'devices_validate_source_callback', 'lib.devices')

    def devices_add_trigger_callback(self, rule, **kwargs):
        """
        Called to add a trigger.  We simply use the automation library for the heavy lifting.

        :param rule: The potential rule being added.
        :param kwargs: None
        :return:
        """
        self._AutomationLibrary.triggers_add(rule['rule_id'], 'devices', rule['trigger']['source']['device_pointer'].device_id)

    def devices_get_value_callback(self, rule, portion, **kwargs):
        """
        A callback to the value for platform "states". We simply just do a get based on key_name.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the portion of rule being fired. Includes source, filter, etc.
        :return:
        """

        return portion['source']['device_pointer'].machine_status

    def Devices_automation_action_list(self, **kwargs):
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
                device = self.get_device(action['device'])
                action['device_pointer'] = device
                return action
            except:
                raise YomboWarning("Error while searching for device, could not be found: %s" % action['device'],
                               104, 'devices_validate_action_callback', 'lib.devices')
        else:
            raise YomboWarning("For platform 'devices' as an 'action', must have 'device' and can be either device ID or device label.",
                               105, 'devices_validate_action_callback', 'lib.devices')

    def devices_do_action_callback(self, rule, action, **kwargs):
        """
        A callback to perform an action.

        :param rule: The complete rule being fired.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        device = action['device_pointer']
#        print "the_message = device.get_message(self, cmd=%s)" % action['command']
        the_message = device.get_message(self, cmd=action['command'])
#        print "the_message: %s" % the_message
        the_message.send()


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
    def __init__(self, device, allDevices, testDevice=False):
        """
        :param device: *(list)* - A device as passed in from the devices class. This is a
            dictionary with various device attributes.
        :ivar callBeforeChange: *(list)* - A list of functions to call before this device has it's status
            changed. (Not implemented.)
        :ivar callAfterChange: *(list)* - A list of functions to call after this device has it's status
            changed. (Not implemented.)
        :ivar device_id: *(string)* - The UUID of the device.
        :ivar device_type_id: *(string)* - The device type UUID of the device.
        :type device_id: string
        :ivar label: *(string)* - Device label as defined by the user.
        :ivar description: *(string)* - Device description as defined by the user.
        :ivar enabled: *(bool)* - If the device is enabled - can send/receive command and/or
            status updates.
        :ivar pin_required: *(bool)* - If a pin is required to access this device.
        :ivar pin_code: *(string)* - The device pin number.
            system to deliver commands and status update requests.
        :ivar created: *(int)* - When the device was created; in seconds since EPOCH.
        :ivar updated: *(int)* - When the device was last updated; in seconds since EPOCH.
        :ivar lastCmd: *(dict)* - A dictionary of up to the last 30 command messages.
        :ivar status_history: *(dict)* - A dictionary of strings for current and up to the last 30 status values.
        :ivar deviceVariables: *(dict)* - The device variables as defined by various modules, with
            values entered by the user.
        :ivar available_commands: *(list)* - A list of cmdUUID's that are valid for this device.
        """
        logger.debug("New device - info: {device}", device=device)

        self.Status = namedtuple('Status', "device_id, set_time, device_state, human_status, machine_status, machine_status_extra, source, uploaded, uploadable")
        self.Command = namedtuple('Command', "time, cmduuid, source")
        self.callBeforeChange = []
        self.callAfterChange = []
        self.device_id = device["id"]
        self.device_type_id = device["device_type_id"]
        self.device_type_machine_label = device["device_type_machine_label"]
        self.label = device["label"]
        self.deviceClass = device["device_class"]
        self.description = device["description"]
        self.enabled = int(device["status"])  # status from database means enabled or not.
        self.pin_required = int(device["pin_required"])
        self.pin_code = device["pin_code"]
        self.pin_timeout = int(device["pin_timeout"])
        self.voice_cmd = device["voice_cmd"]
        self.voice_cmd_order = device["voice_cmd_order"]
        self.created = int(device["created"])
        self.updated = int(device["updated"])
        self.lastCmd = deque({}, 30)
        self.status_history = deque({}, 30)
        self._allDevices = allDevices
        self.testDevice = testDevice
        self.available_commands = []
        self.deviceVariables = {'asdf':'qwer'}
        self._CommandsLibrary = self._allDevices._Libraries['commands']

    def _init_(self):
        """
        Performs items that required deferreds.
        :return:
        """
        def set_commands(commands):
            for command in commands:
                self.available_commands.append(str(command.command_id))

        def set_variables(vars):
            self.deviceVariables = vars

        def gotException(failure):
           print "Exception : %r" % failure
           return 100  # squash exception, use 0 as value for next stage

        d = self._allDevices._Libraries['localdb'].get_commands_for_device_type(self.device_type_id)
        d.addCallback(set_commands)
        d.addErrback(gotException)

        d.addCallback(lambda ignored: self._allDevices._Libraries['localdb'].get_variables('device', self.device_id))
        d.addErrback(gotException)
        d.addCallback(set_variables)
        d.addErrback(gotException)

        if self.testDevice is False:
            d.addCallback(lambda ignored: self.load_history(35))
        return d

    def __str__(self):
        """
        Print a string when printing the class.  This will return the device_id so that
        the device can be identified and referenced easily.
        """
        return self.device_id

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

    def get_message(self, sourceComponent, **kwargs):
        """
        Create a message with the required params and return a Message.

        Creates a new message with the device details completed.  Sends
        the message to the ' module' that handles this device. Send the
        command through a message so other 'subscribing modules'
        will also see the activity.

        If a pin_code is required, "pin_code" must be included as one of
        the arguments otherwise. All **kwargs are sent to the 'module'.

        *This doesn't send the message, it only creates it!* Use the send()
        funciton on the returned object to send it.

        :raises YomboDeviceError: Raised when:

            - pin_code is required but not sent it; skippin_code overrides. Errorno: 100
            - pin_code is required and pin_code submitted is invalid and
              skippin_code is missing. Errorno: 101
            - payload was submitted, but not a dict. Errorno: 102
            - cmd is not a valid command object or string. Errorno: 103
        :param sourceComponent: The library or module name that msgOrigin
            should be set to.
        :type sourceComponent: Reference to the Library or Core or Module (usually 'self')
        :param kwargs: Multiple key/value pairs.

            - delay *(int)* - How many second to delay before sending message.
              can not be used with notBefore.
            - notBefore *(int)* - Time in epoch to send the message.
            - maxDelay *(int)* - How late the message is allowed to be delivered.
            - pin_code *(string)* - Required if device requries a pin.
            - skippin_code *(True)* - Bypass pin checking (use wisely).
            - cmd *(instance or string)* - Must be either an instance of a command
              or a string to search for the command.
            - payload *(dict)* - Payload attributes to include. cmdobj and deviceobj are
              already set.
        :return: the msgUUID
        :rtype: string
        """
        if self.pin_required == 1:
            if "skippin_code" not in kwargs:
                if "pin_code" not in kwargs:
                    raise YomboPinCodeError("'pin_code' is required, but missing.")
                else:
                    if self.pin_code != kwargs["pin_code"]:
                        raise YomboPinCodeError("'pin_code' supplied is incorrect.")

        logger.debug("device kwargs: {kwargs}", kwargs=kwargs)
        cmdobj = None
        if 'cmd' not in kwargs:
            raise YomboDeviceError("Missing 'cmd' must be a valid command instance , 'cmd', or 'cmdUUID'; what to do?", errorno=103)

#        print "cmd is of type: %s" % type(kwargs['cmd'])
        if type(kwargs['cmd']) == 'instance':
            if kwargs['cmd'].__class__ != 'yombo.lib.commands.Command':
                raise YomboDeviceError("Object passed to get_message is not a command object.", errorno=103)
            cmdobj = kwargs['cmd']
        elif isinstance(kwargs['cmd'], six.string_types):
            try:
                cmdobj = self._CommandsLibrary.get_command(kwargs['cmd'])
            except Exception, e:
                raise YomboDeviceError("Cannot find command from string: %s" % kwargs['cmd'], errorno=103, )
        else:
            raise YomboDeviceError("'cmd' must be a string or instance of a command.", errorno=103)

#        if self.validate_command(cmdobj) is not True:
        if str(cmdobj.cmdUUID) not in self.available_commands:
            raise YomboDeviceError("Invalid command requested for device.", errorno=103)

        payloadValues = {}
        if 'payload' in kwargs:
            if isinstance(kwargs['payload'], dict):
                payloadValues = kwargs['payload']
            else:
                raise YomboDeviceError("Payload in kwargs must be a dict. Received: %s" % type(kwargs['payload']), errorno=102)

        payload = {"cmdobj" : cmdobj, "deviceobj" : self}

        payload.update(payloadValues)

        route = self._allDevices._ModulesLibrary.get_device_routing(self.device_type_id, 'Command', 'moduleLabel')

        msg = {
               'msgOrigin'      : sourceComponent._FullName.lower(),
               'msgDestination' : "yombo.gateway.modules.%s" % route,
               'msgType'        : "cmd",
               'msgStatus'      : "new",
               'uuidType'       : "1",
               'uuidSubType'    : "123",
               'payload'        : payload,
               }

        if 'notBefore' in kwargs:
            msg['notBefore'] = kwargs['notBefore']
        if  'maxDelay' in kwargs:
            msg['maxDelay'] = kwargs['maxDelay'],
        if  'delay' in kwargs:
            msg['delay'] = kwargs['delay'],

        message = Message(**msg)

#TODO: Move to lib/device.py to listen for cmd packets.
#TODO: Remember, we need to ignore our own broadcasts.
#        self.lastCmd.appendleft(cmd)
        return message

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

            - device_state *(float)* - Soemthing that can be used to graph. on = 1, off =0. Lamp at 50% = 0.5
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

        device_state = kwargs.get('device_state', 0)
        human_status = kwargs.get('human_status', machine_status)
        machine_status = kwargs['machine_status']
        machine_status_extra = kwargs.get('machine_status_extra', '')
        source = kwargs.get('source', 'unknown')
        uploaded = kwargs.get('uploaded', 0)
        uploadable = kwargs.get('uploadable', 0)
        set_time = time()

        new_status = self.Status(self.device_id, set_time, device_state, human_status, machine_status, machine_status_extra, source, uploaded, uploadable)
        self.status_history.appendleft(new_status)
        if self.testDevice is False:
            self._allDevices._status_updates_to_save[random_string(length=12)] = new_status
            if len(self._allDevices._status_updates_to_save) > 120:
                self._allDevices._save_status()
        self._allDevices.check_trigger(self.device_id, new_status)

    def send_status(self, **kwargs):
        """
        Tell the message system to broadcast the current status of a device. This
        is typically only called internally when a device status changes. Shouldn't
        need to call this from a module. Just send a command to the device and
        this function will be called automatically as needed.

        :param kwargs:
        :return:
        """
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
        msg = {
               'msgOrigin'      : src,
               'msgDestination' : dest,
               'msgType'        : "status",
               'msgStatus'      : "new",
               'msgStatusExtra' : "",
               'uuidtype'       : "APDS",
               'payload'        : payload,
              }
        message = Message(**msg)
        message.send()

    def remove_delayed(self):
        """
        Remove any messages that might be set to be called later that
        relates to this device.  Easy, just tell the messages library to 
        do that for us.
        """
        self._allDevices._MessageLibrary.device_delay_cancel(self.device_id)

    def get_delayed(self):
        """
        List messages that are to be sent at a later time.
        """
        self._allDevices._MessageLibrary.device_delay_list(self.device_id)

    def load_history(self, howmany=35):
        """
        Loads device history into the device instance. This method gets the data from the db and adds a callback
        to _do_load_history to actually set the values.

        :param howmany:
        :return:
        """
        d =  self._allDevices._Libraries['LocalDB'].get_device_status(id=self.device_id, limit=howmany)
        d.addCallback(self._do_load_history)
        return d

    def _do_load_history(self, records):
        if len(records) == 0:
            self.status_history.append(self.Status(self.device_id, 0, 0, 'NA', 'NA', {}, '', 0, 0))
        else:
            for record in records:
                self.status_history.appendleft(self.Status(record['device_id'], record['set_time'], record['device_state'], record['human_status'], record['machine_status'],record['machine_status_extra'], record['source'], record['uploaded'], record['uploadable']))
#                              self.Status = namedtuple('Status',  "device_id,           set_time,           device_state,           human_status,           machine_status,                             machine_status_extra,             source,           uploaded,           uploadable")

        logger.debug("Device load history: {device_id} - {status_history}", device_id=self.device_id, status_history=self.status_history)

    def validate_command(self, cmdUUID):
        print "checking cmdavail for %s, looking for '%s': %s" % (self.label, cmdUUID, self.available_commands)
        if str(cmdUUID) in self.available_commands:
            return True
        else:
            return False
