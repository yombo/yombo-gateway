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
:copyright: Copyright 2012-2015 by Yombo.
:license: LICENSE for details.
"""

from collections import deque, namedtuple
from itertools import izip
from time import time
import copy
import cPickle
import json

from twisted.internet.task import LoopingCall

from yombo.lib.commands import Command # used to test if isinstance
from yombo.core.db import get_dbconnection, get_dbtools
from yombo.core.fuzzysearch import FuzzySearch
from yombo.core.exceptions import YomboPinCodeError, YomboDeviceError, YomboFuzzySearchError
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
from yombo.core.message import Message
from yombo.core.helpers import getCommand, getComponent, sleep

logger = getLogger('library.devices')

class Devices(YomboLibrary):
    """
    Manages all devices and provides the primary interaction interface. The
    primary functions developers should use are:
        - :func:`getDevices` - Get a pointer to all devices.
        - :func:`getDevicesByDeviceType` - Get all device for a certain deviceType (UUID or MachineLabel)
        - :func:`search` - Get a pointer to a device, using deviceUUID or device label.
    """

    def __getitem__(self, key):
        """
        Attempts to find the device requested using a couple of methods.

        Simulate a dictionary when requested with:
            >>> self._Devices['137ab129da9318']  #by uuid
        or:
            >>> self._Devices['living room light']  #by name

        See: :func:`yombo.core.helpers.getDevices` for full usage example.

        :raises YomboDeviceError: Raised when device cannot be found.
        :param deviceRequested: The device UUID or device label to search for.
        :type deviceRequested: string
        :return: Pointer to array of all devices.
        :rtype: dict
        """
        return self._search(key)

    def __iter__(self):
        return self._yomboDevicesByUUID.__iter__()

    def _init_(self, loader):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        :param loader: A pointer to the :mod:`yombo.lib.loader`
        library.
        :type loader: Instance of Loader
        """
        self.libMessages = getComponent('yombo.gateway.lib.messages')
        self.loader = loader
        self._yomboDevicesByUUID = {}
        self._yomboDevicesByName = FuzzySearch({}, .89)
        self._yomboDevicesByDeviceTypeByUUID = {}
        self._yomboDevicesByDeviceTypeByName = FuzzySearch({}, .93)
        self._toSaveStatus = {}
        self._saveStatusLoop = None

    def _load_(self):
        """
        Get pointer to voice commands, get db connection.
        """
        self.__dbpool = get_dbconnection()
        self.voiceCmds = self.loader.loadedLibraries['yombo.gateway.lib.voicecmds']
        self.__loadDevices()

    def _start_(self):
        """
        Load devices, and load some of the device history. Setup looping
        call to periodically save any updated device status.
        """
        self._saveStatusLoop = LoopingCall(self._saveStatus)
        self._saveStatusLoop.start(120, False)
        pass

    def _stop_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        if hasattr(self, '_saveStatusLoop') and self._saveStatusLoop != None and self._saveStatusLoop.running == True:
            self._saveStatusLoop.stop()

    def _unload_(self):
        """
        Stop periodic loop, save status updates.
        """
        self._saveStatus()

    def _saveStatus(self):
        """
        Function that does actual work. Saves items in the self._toStaveStatus
        queue to the SQLite database.
        """
        if len(self._toSaveStatus) == 0:
            return

        logger.info("Saving device status to disk.")
        c = self.__dbpool.cursor()
        for key in self._toSaveStatus.keys():
            ss = self._toSaveStatus[key]
            statusExtra = cPickle.dumps(ss.statusextra)
            logger.trace("INSERT INTO devicestatus (deviceuuid, status, statusextra, settime, source) values (%s, %s, %s, %s, %s)" %  (key, ss.status, statusExtra, ss.time, ss.source) )
            c.execute("""INSERT INTO devicestatus (deviceuuid, status, statusextra, settime, source) values (?, ?, ?, ?, ?)""",
                ( key, ss.status, statusExtra, ss.time, ss.source) )
            del self._toSaveStatus[key]
        self.__dbpool.pool.commit()

    def _clear_(self):
        """
        Clear all devices. Should only be called by the loader module
        during a reconfiguration event. **Do not call this function!**
        """
        self._saveStatus()
        self._yomboDevicesByUUID.clear()
        self._yomboDevicesByName.clear()
        self._yomboDevicesByDeviceTypeByUUID.clear()
        self._yomboDevicesByDeviceTypeByName.clear()

    def _reload_(self):
        self.__loadDevices()

    def _search(self, deviceRequested):
        """
        Performs the actual device search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find commands: `self._Devices['8w3h4sa']`

        See: :func:`yombo.core.helpers.getDevices` for full usage example.

        :raises YomboDeviceError: Raised when device cannot be found.
        :param deviceRequested: The device UUID or device label to search for.
        :type deviceRequested: string
        :return: Pointer to array of all devices.
        :rtype: dict
        """
        if deviceRequested in self._yomboDevicesByUUID:
            return self._yomboDevicesByUUID[deviceRequested]
        else:
            try:
                requestedUUID = self._yomboDevicesByName[deviceRequested]
                return self._yomboDevicesByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
                raise YomboDeviceError('Searched for %s, but no good matches found.' % e.searchFor, searchFor=e.searchFor, key=e.key, value=e.value, ratio=e.ratio, others=e.others)

    def __loadDevices(self):
        """
        Load the devices into memory. Set up various dictionaries to manage
        devices. This also setups all the voice commands for all the devices.
        """
        logger.info("Loading devices")

        c = self.__dbpool.cursor()
        c.execute("select devices.*, moduleDeviceTypes.*, deviceTypes.machineLabel as deviceTypeMachineLabel from devices " +
                "join moduleDeviceTypes on devices.deviceTypeUUID = moduleDeviceTypes.deviceTypeUUID " +
                "join deviceTypes on devices.deviceTypeUUID = deviceTypes.deviceTypeUUID")

        row = c.fetchone()
        if row == None:
            return None
        field_names = [d[0].lower() for d in c.description]
        while row is not None:
            record = (dict(izip(field_names, row)))
            try:
                self.voiceCmds.add(record["voicecmd"], record["modulelabel"], record["deviceuuid"], record["voicecmdorder"])
            except:
                pass
            self._addDevice(record)
            row = c.fetchone()

    def _addDevice(self, record, testDevice = False):
        """
        Add a device based on data from a row in the SQL database.

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :returns: Pointer to new device. Only used during unittest
        """
        deviceUUID = record["deviceuuid"]
        self._yomboDevicesByUUID[deviceUUID] = Device(record, self)
        self._yomboDevicesByName[record["label"]] = deviceUUID

        if record['devicetypeuuid'] not in self._yomboDevicesByDeviceTypeByUUID:
            self._yomboDevicesByDeviceTypeByUUID[record['devicetypeuuid']] = {}
        if deviceUUID not in self._yomboDevicesByDeviceTypeByUUID[record['devicetypeuuid']]:
            self._yomboDevicesByDeviceTypeByUUID[record['devicetypeuuid']][deviceUUID] = self._yomboDevicesByUUID[deviceUUID]

        if record['devicetypemachinelabel'] not in self._yomboDevicesByDeviceTypeByName:
            self._yomboDevicesByDeviceTypeByName[record['devicetypemachinelabel']] = {}
        if deviceUUID not in self._yomboDevicesByDeviceTypeByName[record['devicetypemachinelabel']]:
            self._yomboDevicesByDeviceTypeByName[record['devicetypemachinelabel']][deviceUUID] = deviceUUID

        logger.trace("_addDevice::_yomboDevicesByTypeUUID=%s" % self._yomboDevicesByDeviceTypeByUUID)
        if testDevice:
            return self._yomboDevicesByUUID[deviceUUID]

    def getDevicesByDeviceType(self, deviceTypeRequested):
        """
        Returns list of devices by deviceType. Will search by DeviceType UUID or MachineLabel.

        :raises YomboDeviceError: Raised when function encounters an error.
        :param deviceTypeRequested: The device UUID or device label to search for.
        :type deviceRequested: string
        :return: Pointer to array of all devices for requested device type
        :rtype: dict
        """
        logger.trace("## _yomboDevicesByDeviceTypeByUUID: %s " % self._yomboDevicesByDeviceTypeByUUID)
        logger.trace("## deviceTypeRequested: %s" % deviceTypeRequested)
        if deviceTypeRequested in self._yomboDevicesByDeviceTypeByUUID:
            logger.trace("## %s" % self._yomboDevicesByDeviceTypeByUUID[deviceTypeRequested])
            return self._yomboDevicesByDeviceTypeByUUID[deviceTypeRequested]
        else:
            try:
                requestedUUID = self._yomboDevicesByDeviceTypeByName[deviceTypeRequested]
                logger.trace("## requestedUUID: %s" % requestedUUID)
                return self._yomboDevicesByDeviceTypeByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
                raise YomboDeviceError('Searched for device type %s, but no good matches found.' % e.searchFor, searchFor=e.searchFor, key=e.key, value=e.value, ratio=e.ratio, others=e.others)

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
        :ivar deviceUUID: *(string)* - The UUID of the device.
        :ivar deviceTypeUUID: *(string)* - The device type UUID of the device.
        :type deviceUUID: string
        :ivar label: *(string)* - Device label as defined by the user.
        :ivar description: *(string)* - Device description as defined by the user.
        :ivar enabled: *(bool)* - If the device is enabled - can send/receive command and/or
            status updates.
        :ivar pinrequired: *(bool)* - If a pin is required to access this device.
        :ivar pincode: *(string)* - The device pin number.
        :ivar moduleLabel: *(string)* - The module that handles this devices. Used by the message
            system to deliver commands and status update requests.
        :ivar created: *(int)* - When the device was created; in seconds since EPOCH.
        :ivar updated: *(int)* - When the device was last updated; in seconds since EPOCH.
        :ivar lastCmd: *(dict)* - A dictionary of up to the last 30 command messages.
        :ivar status: *(dict)* - A dictionary of strings for current and up to the last 30 status values.
        :ivar deviceVariables: *(dict)* - The device variables as defined by various modules, with
            values entered by the user.
        :ivar availableCommands: *(list)* - A list of cmdUUID's that are valid for this device.
        """
        logger.trace("New device - info: %s", device)
        self.__dbpool = get_dbconnection()

        self.Status = namedtuple('Status', "time, status, statusextra, source")
        self.Command = namedtuple('Command', "time, cmduuid, source")
        self.callBeforeChange = []
        self.callAfterChange = []
        self.deviceUUID = device["deviceuuid"]
        self.deviceTypeUUID = device["devicetypeuuid"]
        self.label = device["label"]
        self.description = device["description"]
        self.enabled = int(device["status"])
        self.pinrequired = int(device["pinrequired"])
        self.pincode = device["pincode"]
        self.pintimeout = int(device["pintimeout"])
        self.moduleLabel = device["modulelabel"]
        self.voiceCmd = device["voicecmd"]
        self.voiceCmdOrder = device["voicecmdorder"]
        self.created = int(device["created"])
        self.updated = int(device["updated"])
        self.lastCmd = deque({}, 30)
        self.status = deque({}, 30)
        self._allDevices = allDevices

        dbtools = get_dbtools()
        self.deviceVariables = dbtools.getVariableDevices(self.deviceUUID)
        self.availableCommands = dbtools.getCommandsForDeviceType(self.deviceTypeUUID)
        self.testDevice = testDevice
        if self.testDevice == False:
            self.loadHistory(10)

    def __str__(self):
        """
        Print a string when printing the class.  This will return the deviceUUID so that
        the device can be identified and referenced easily.
        """
        return self.deviceUUID

    def dump(self):
        """
        Export device variables as a dictionary.
        """
        return {'deviceUUID'     : str(self.deviceUUID),
                'deviceTypeUUID' : str(self.deviceTypeUUID),
                'label'          : str(self.label),
                'description'    : str(self.description),
                'enabled'        : int(self.enabled),
                'pinrequired'    : int(self.pinrequired),
                'pintimeout'     : int(self.pintimeout),
                'moduleLabel'    : str(self.moduleLabel),
                'voiceCmd'       : str(self.voiceCmd),
                'voiceCmdOrder'  : str(self.voiceCmdOrder),
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

        If a pincode is required, "pincode" must be included as one of
        the arguments otherwise. All **kwargs are sent to the 'module'.

        :raises YomboDeviceError: Raised when:

            - pincode is required but not sent it; skippincode overrides. Errorno: 100
            - pincode is required and pincode submitted is invalid and
              skippincode is missing. Errorno: 101
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
            - pincode *(string)* - Required if device requries a pin.
            - skippincode *(True)* - Bypass pin checking (use wisely).
            - cmdobj (instance), cmd  or cmduuid *(string)* - Needs to include either a "cmdobj", "cmd" or "cmduuid";
              *cmdobj* is always preferred, followed by *cmdUUID*, then cmd.
            - payload *(dict)* - Payload attributes to include. cmdobj and deviceobj are
              already set.
        :return: the msgUUID
        :rtype: string
        """
        if self.pinrequired == 1:
            if "skippincode" not in kwargs:
                if "pincode" not in kwargs:
                    raise YomboPinCodeError("'pincode' is required, but missing.")
                else:
                    if self.pincode != kwargs["pincode"]:
                        raise YomboPinCodeError("'pincode' supplied is incorrect.")

        logger.debug("device kwargs: %s", kwargs)
        cmdobj = None
        try:
          if 'cmdobj' in kwargs:
            if isinstance(kwargs['cmdobj'], Command):
              cmdobj = kwargs['cmdobj']
            else:
              raise YomboDeviceError("Invalid 'cmdobj'.", errorno=103)
          elif 'cmdUUID' in kwargs:
              cmdobj = getCommand(kwargs['cmdUUID'])
          elif 'cmd' in kwargs:
            cmdobj = getCommand(kwargs['cmd'])
          else:
            raise YomboDeviceError("Missing 'cmdobj', 'cmd', or 'cmdUUID'; what to do?", errorno=103)
        except:
            raise YomboDeviceError("Invalid 'cmdobj', 'cmd', or 'cmdUUID'; what to do??", errorno=103)

        if self.validateCommand(cmdobj.cmdUUID) != True:
            raise YomboDeviceError("Invalid command requested for device.", errorno=103)

        payloadValues = {}
        if 'payload' in kwargs:
            if isinstance(kwargs['payload'], dict):
                payloadValues = kwargs['payload']
            else:
                raise YomboDeviceError("Payload in kwargs must be a dict. Received: %s" % type(kwargs['payload']), errorno=102)

        payload = {"cmdobj" : cmdobj, "deviceobj" : self}

        payload.update(payloadValues)

        msg = {
               'msgOrigin'      : sourceComponent._FullName.lower(),
               'msgDestination' : "yombo.gateway.modules.%s" % (self.moduleLabel),
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
        logger.info("setStatus called...: %s", kwargs)
        self._setStatus(**kwargs)
        if 'silent' not in kwargs:
            self.sendStatus(**kwargs)

    def _setStatus(self, **kwargs):
        logger.trace("_setStatus called...")
        status = None
        statusExtra = None
        if 'status' in kwargs:
            status = kwargs['status']
        else:
            raise YomboDeviceError("setStatus was called without a real status!", errorno=120)

        statusExtra = kwargs.get('statusExtra', {})

        source = kwargs.get('source', 'unknown')

        logger.trace("_setStatus is saving status...")
        newStatus = self.Status(time(), status, statusExtra, source.lower())
        self.status.appendleft(newStatus)
        if self.testDevice == False:
            self._allDevices._toSaveStatus[self.deviceUUID] = newStatus
            if len(self._allDevices._toSaveStatus) > 60:
                self._allDevices._saveStatus()

    def sendStatus(self, **kwargs):
        logger.trace("sendStatus called...")
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
        self._allDevices.libMessages.deviceDelayCancel(self.deviceUUID)

    def getDelayed(self):
        """
        Remove any messages that might be set to be called later that
        relates to this device.  Easy, just tell the messages library to 
        do that for us.
        """
        self._allDevices.libMessages.deviceDelayList(self.deviceUUID)

    def loadHistory(self, howmany=15):
        c = self.__dbpool.cursor()
        logger.debug("loading device history...")
        c.execute("SELECT * FROM devicestatus WHERE deviceuuid = ? ORDER BY settime LIMIT ?",
            (self.deviceUUID, howmany))
        row = c.fetchone()
        if row == None:  #lets set at least one status, it can be blank!
            logger.debug("No device history found for %s,  deviceUUID: %s" % (self.label, self.deviceUUID))
            self.status.append(self.Status(0, '', {}, ''))
            return
        field_names = [d[0].lower() for d in c.description]
        tempStatus = deque((), 20)
        counter = 0
        while row is not None:
            counter = counter + 1
            record = (dict(izip(field_names, row)))
            for k, v in record.iteritems():
                if v is None:
                    record[k] = ''
            self.status.appendleft(self.Status(record['settime'], record['status'], cPickle.loads(str(record['statusextra'])), record['source']))
            row = c.fetchone()

        logger.trace("Device load history: %s -- %s" % (self.deviceUUID, self.status) )

    def getHistory(self, history=0):
        return {"status": self.status[history]}

    def validateCommand(self, cmdUUID):
        if cmdUUID in self.availableCommands:
            return True
        else:
            return False
