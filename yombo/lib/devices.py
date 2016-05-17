# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
"""
Classes to maintain device state, control devices, and query devices.

The devices (plural) class is a wrapper class and contains all
the individual devices as an individual class.  The devices class
is responsible for loading individual device classes.

The device (singular) class represents one device.  This class
has many functions that help with utilizing the device.  When possible,
this class should be used to send Yombo Messages for controlling, and
getting/setting/querying status.  The device class maintains the
current known device state.  Any changes to the device state are
saved to the local database.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from collections import deque, namedtuple
from time import time
import copy
import cPickle
import json

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, returnValue, gatherResults, DeferredList, Deferred


# Import Yombo libraries
from yombo.lib.commands import Command # used to test if isinstance
from yombo.core.exceptions import YomboPinCodeError, YomboDeviceError, YomboFuzzySearchError
from yombo.core.fuzzysearch import FuzzySearch
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
        self.voice_cmds = self.loader.loadedLibraries['voicecmds']

        self._devicesByUUID = {}
        self._devicesByName = FuzzySearch({}, .89)
        self._devicesByDeviceTypeByUUID = {}
        self._devicesByDeviceTypeByName = FuzzySearch({}, .94)
        self._toSaveStatus = {}
        self._saveStatusLoop = None

    def _load_(self):
        """
        Get pointer to voice commands, get db connection.
        """
        self.__load_devices()
        self.loadDefer = Deferred()

        return self.loadDefer

    def __loadFinish(self, nextSteps):
        """
        Called when all the configurations have been received from the Yombo servers.
        """
        return 1

    def _start_(self):
        """
        Load devices, and load some of the device history. Setup looping
        call to periodically save any updated device status.
        """
        self._saveStatusLoop = LoopingCall(self._save_status)
        self._saveStatusLoop.start(120, False)

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
#        print "777 %s" % records
        logger.debug("Loading devices:::: {records}", records=records)
        if len(records) > 0:
            for record in records:
                logger.debug("Loading device: {record}", record=record)
                try:
                    self.voice_cmds.add(record["voice_cmd"], "", record["id"], record["voice_cmd_order"])
                except:
                    pass
                d = yield self._add_device(record)

        self.loadDefer.callback(10)

#    @inlineCallbacks
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
        if len(self._toSaveStatus) == 0:
            return

        logger.info("Saving device status to disk.")
        for key in self._toSaveStatus.keys():
            ss = self._toSaveStatus[key]
            ss.machine_status_extra = cPickle.dumps(ss.machine_status_extra)
            self._ModulesLibrary['localdb'].set_device_status(**ss.__dict__)
            del self._toSaveStatus[key]

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

    def get_device(self, deviceRequested):
        """
        Performs the actual device search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find commands: `self._Devices['8w3h4sa']`

        See: :func:`yombo.core.helpers.get_device` for full usage example.

        :raises YomboDeviceError: Raised when device cannot be found.
        :param deviceRequested: The device UUID or device label to search for.
        :type deviceRequested: string
        :return: Pointer to array of all devices.
        :rtype: dict
        """
        logger.debug("looking for: {device_id}", device_id=deviceRequested)
        if deviceRequested in self._devicesByUUID:
            return self._devicesByUUID[deviceRequested]
        else:
            try:
                requestedUUID = self._devicesByName[deviceRequested]
                return self._devicesByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
                raise YomboDeviceError('Searched for %s, but no good matches found.' % e.searchFor, searchFor=e.searchFor, key=e.key, value=e.value, ratio=e.ratio, others=e.others)

    def get_devices_by_device_type(self, deviceTypeRequested):
        """
        Returns list of devices by deviceType. Will search by DeviceType UUID or MachineLabel.

        :raises YomboDeviceError: Raised when function encounters an error.
        :param deviceTypeRequested: The device UUID or device label to search for.
        :type deviceRequested: string
        :return: Pointer to array of all devices for requested device type
        :rtype: dict
        """
        logger.debug("## _devicesByDeviceTypeByUUID: {devicesByDeviceTypeByUUID}", devicesByDeviceTypeByUUID=self._devicesByDeviceTypeByUUID)
#        logger.debug("## deviceTypeRequested: {deviceTypeRequested}", deviceTypeRequested=deviceTypeRequested)
        if deviceTypeRequested in self._devicesByDeviceTypeByUUID:
            logger.debug("## {devicesByDeviceTypeByUUID}", devicesByDeviceTypeByUUID=self._devicesByDeviceTypeByUUID[deviceTypeRequested])
            return self._devicesByDeviceTypeByUUID[deviceTypeRequested]
        else:
            try:
                requestedUUID = self._devicesByDeviceTypeByName[deviceTypeRequested]
#                logger.debug("## _devicesByDeviceTypeByUUID: {requestedUUID}", requestedUUID=self._devicesByDeviceTypeByUUID)
#                logger.debug("## _devicesByDeviceTypeByName: {requestedUUID}", requestedUUID=self._devicesByDeviceTypeByName)
#                logger.debug("## deviceTypeRequested: {deviceTypeRequested}", deviceTypeRequested=deviceTypeRequested)
#                logger.debug("## requestedUUID: {requestedUUID}", requestedUUID=requestedUUID)
                return self._devicesByDeviceTypeByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
#                logger.debug("e={e}", e=e)
                return {}

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
        :ivar status: *(dict)* - A dictionary of strings for current and up to the last 30 status values.
        :ivar deviceVariables: *(dict)* - The device variables as defined by various modules, with
            values entered by the user.
        :ivar availableCommands: *(list)* - A list of cmdUUID's that are valid for this device.
        """
        logger.debug("New device - info: {device}", device=device)

        self.Status = namedtuple('Status', "device_id, set_time, device_state, human_status, machine_status, machine_status_extra, source, uploaded, uploadable")
        self.Command = namedtuple('Command', "time, cmduuid, source")
        self.callBeforeChange = []
        self.callAfterChange = []
        self.device_id = device["id"]
        self.device_type_id = device["device_type_id"]
        self.deviceTypeLabel = device["device_type_machine_label"]
        self.label = device["label"]
        self.deviceClass = device["device_class"]
        self.description = device["description"]
        self.enabled = int(device["status"])
        self.pin_required = int(device["pin_required"])
        self.pin_code = device["pin_code"]
        self.pin_timeout = int(device["pin_timeout"])
        self.voice_cmd = device["voice_cmd"]
        self.voice_cmd_order = device["voice_cmd_order"]
        self.created = int(device["created"])
        self.updated = int(device["updated"])
        self.lastCmd = deque({}, 30)
        self.status = deque({}, 30)
        self._allDevices = allDevices
        self.testDevice = testDevice
        self.availableCommands = []
        self.deviceVariables = {'asdf':'qwer'}

#    @inlineCallbacks
    def _init_(self):
        """
        Performs items that required deferreds.
        :return:
        """
        def setCommands(commands):
#            print "wwww1 %s" % commands
            self.availableCommands = commands

        def setVariables(vars):
#            print "wwww2 %s" % vars
            self.deviceVariables = vars

        def gotException(failure):
           print "Exception : %r" % failure
           return 100  # squash exception, use 0 as value for next stage

        d = self._allDevices._Libraries['localdb'].get_commands_for_device_type(self.device_type_id)
        d.addCallback(setCommands)
        d.addErrback(gotException)

        d.addCallback(lambda ignored: self._allDevices._Libraries['localdb'].get_variables('device', self.device_id))
        d.addErrback(gotException)
        d.addCallback(setVariables)
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
        return {'device_id'     : str(self.device_id),
                'device_type_id' : str(self.device_type_id),
                'label'          : str(self.label),
                'description'    : str(self.description),
                'enabled'        : int(self.enabled),
                'pin_code'        : "********",
                'pin_required'    : int(self.pin_required),
                'pin_timeout'     : int(self.pin_timeout),
                'voice_cmd'       : str(self.voice_cmd),
                'voice_cmd_order'  : str(self.voice_cmd_order),
                'created'        : int(self.created),
                'updated'        : int(self.updated),
                'status'         : copy.copy(self.status),
               }

    def getMessage(self, sourceComponent, **kwargs):
        """
        Create a message with the required params and return a Message.

        Creates a new message with the device details completed.  Sends
        the message to the ' module' that handles this device. Send the
        command through a message so other 'subscribing modules'
        will also see the activity.

        If a pin_code is required, "pin_code" must be included as one of
        the arguments otherwise. All **kwargs are sent to the 'module'.

        :raises YomboDeviceError: Raised when:

            - pin_code is required but not sent it; skippin_code overrides. Errorno: 100
            - pin_code is required and pin_code submitted is invalid and
              skippin_code is missing. Errorno: 101
            - payload was submitted, but not a dict. Errorno: 102
            - cmdobj, cmduUUID, or cmd was not sent in. Errorno: 103
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
            - cmdobj (instance), cmd  or cmduuid *(string)* - Needs to include either a "cmdobj", "cmd" or "cmduuid";
              *cmdobj* is always preferred, followed by *cmdUUID*, then cmd.
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
        try:
          if 'cmdobj' in kwargs:
            if isinstance(kwargs['cmdobj'], Command):
              cmdobj = kwargs['cmdobj']
            else:
              raise YomboDeviceError("Invalid 'cmdobj'.", errorno=103)
          elif 'cmdUUID' in kwargs:
              cmdobj = self._allDevices._Libraries('commands').getCommand(kwargs['cmdUUID'])
          elif 'cmd' in kwargs:
              cmdobj = self._allDevices._Libraries('commands').getCommand(kwargs['cmd'])
#              cmdobj = getCommand(kwargs['cmd'])
          else:
            raise YomboDeviceError("Missing 'cmdobj', 'cmd', or 'cmdUUID'; what to do?", errorno=103)
        except:
            raise YomboDeviceError("Invalid 'cmdobj', 'cmd', or 'cmdUUID'; what to do??", errorno=103)

        if self.validateCommand(cmdobj.cmdUUID) is not True:
            raise YomboDeviceError("Invalid command requested for device.", errorno=103)

        payloadValues = {}
        if 'payload' in kwargs:
            if isinstance(kwargs['payload'], dict):
                payloadValues = kwargs['payload']
            else:
                raise YomboDeviceError("Payload in kwargs must be a dict. Received: %s" % type(kwargs['payload']), errorno=102)

        payload = {"cmdobj" : cmdobj, "deviceobj" : self}

        payload.update(payloadValues)

        route = self._allDevices._ModulesLibrary.getDeviceRouting(self.device_type_id, 'Command')

        msg = {
               'msgOrigin'      : sourceComponent._FullName.lower(),
               'msgDestination' : "yombo.gateway.modules.%s" % route['moduleLabel'],
               'msgType'        : "cmd",
               'msgStatus'      : "new",
               'uuidType'       : "1",
               'uuidSubType'    : "123",
               'payload'        : payload,
               }
        message = Message(**msg)

        if 'notbefore' in kwargs or 'delay' in kwargs:
          message.notBefore, message.maxDelay = self.getDelay(**kwargs)

#TODO: Move to lib/device.py to listen for cmd packets.
#TODO: Remember, we need to ignore our own broadcasts.
#        self.lastCmd.appendleft(cmd)
        return message

    def setDelay(self, **kwargs):
        """
        To be documentated later. Basically, just sets notBefore and maxDelay
        based on kwargs.
        """
        notBefore = 0.0
        maxDelay = 0.0

        if 'notBefore' in kwargs:
            try:
              notBefore = float(kwargs['notBefore'])
              if notBefore < time():
                raise YomboDeviceError("Cannot set 'notBefore' to a time in the past.", errorno=150)
            except:
                raise YomboDeviceError("notBefore is not an int or float.", errorno=151)
        elif 'delay' in kwargs:
            try:
              notBefore = time() + float(kwargs['delay'])
            except:
              raise YomboDeviceError("delay is not an int or float", errorno=152)
        else:
              raise YomboDeviceError("notBefore or delay not set.", errorno=153)

        if maxDelay in kwargs:
          try:
            maxDelay = float(kwargs['kwargs'])
            if maxDelay < 0:
              raise YomboDeviceError("Max delay cannot be less then 0.", errorno=154)
          except:
            raise YomboDeviceError("maxDelay is not an int or float.", errorno=151)

        return notBefore, maxDelay

    def setStatus(self, **kwargs):
        """
        Usually called by the device's command/logic module to set/update the
        device status.

        :raises YomboDeviceError: Raised when:

            - If no valid status sent in. Errorno: 120
            - If statusExtra was set, but not a dictionary. Errorno: 121
            - If payload was set, but not a dictionary. Errorno: 122
        :param kwargs: key/value dictionary with the following keys-

            - status *(int or string)* - The new status.
            - statusExtra *(dict)* - Extra status as a dictionary.
            - source *(string)* - The source module or library name creating the status.
            - silent *(any)* - If defined, will not broadcast a status update
              message; atypical.
            - payload *(dict)* - a dict to be appended to the payload portion of the
              status message.
        """
        logger.debug("setStatus called...: {kwargs}", kwargs=kwargs)
        self._setStatus(**kwargs)
        if 'silent' not in kwargs:
            self.sendStatus(**kwargs)

    def _setStatus(self, **kwargs):
        logger.debug("_setStatus called...")
        machine_status = None
        if 'machine_status' not in kwargs:
            raise YomboDeviceError("setStatus was called without a real machine_status!", errorno=120)

        device_state = kwargs.get('device_state', 0)
        machine_status = kwargs['machine_status']
        machine_status_extra = kwargs.get('machine_status_extra', '')
        human_status = kwargs.get('human_status', machine_status)
        source = kwargs.get('source', 'unknown')
        uploaded = kwargs.get('uploaded', 0)
        uploadable = kwargs.get('uploadable', 0)
        set_time = time()

        logger.debug("_setStatus is saving status...")

        newStatus = self.Status(self.device_id, set_time, device_state, human_status, machine_status, machine_status_extra, source, uploaded, uploadable)
        self.status.appendleft(newStatus)
        if self.testDevice is False:
            self._allDevices._toSaveStatus[random_string(length=12)] = newStatus
            if len(self._allDevices._toSaveStatus) > 60:
                self._allDevices._save_status()

    def sendStatus(self, **kwargs):
        logger.debug("sendStatus called...")
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
                   "status" : self.status[0],
                   "prevStatus" : self.status[1],
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

    def removeDelayed(self):
        """
        Remove any messages that might be set to be called later that
        relates to this device.  Easy, just tell the messages library to 
        do that for us.
        """
        self._allDevices._MessageLibrary.deviceDelayCancel(self.device_id)

    def getDelayed(self):
        """
        Remove any messages that might be set to be called later that
        relates to this device.  Easy, just tell the messages library to 
        do that for us.
        """
        self._allDevices._MessageLibrary.deviceDelayList(self.device_id)

    def load_history(self, howmany=35):
        d =  self._allDevices._Libraries['LocalDB'].get_device_status(id=self.device_id, limit=howmany)
        d.addCallback(self._do_load_history)
        return d

    def _do_load_history(self, records):
#        print records
        if len(records) == 0:
            self.status.append(self.Status(self.device_id, 0, 0, '', '', {}, '', 0, 0))
        else:
            for record in records:
                self.status.appendleft(self.Status(record['set_time'], record['human_status'], record['machine_status'], cPickle.loads(str(record['machine_status_extra'])), record['source'], record['uploaded'], record['uploadable']))
        logger.debug("Device load history: {device_id} - {status}", device_id=self.device_id, status=self.status)

    def get_history(self, history=0):
        return {"status": self.status[history]}

    def validateCommand(self, cmdUUID):
        if cmdUUID in self.availableCommands:
            return True
        else:
            return False
