# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
A shell for module developers to get basic items configured for modules.

All modules should extend this module.  See the class documentation for
additional details.

Modules have 3 phases of startup: _init, _load, _start.
    - Init - Get the basics of the module running.  All libraries are
      loaded and available.  Not all modules have been through init
      this stage.  A deferred can be returned if the :ref:`Loader`
      should wait until the module has completed it's init phase.
    - Load - All modules have completed init phase.  Now it's time to get the
      module ready to receive messages. By the time Load() finishes, the
      module should be able to recieve messages - even if it queue for later.
      A deferred can be returned if the :ref:`Loader`
      should wait until the module has completed it's load phase.
    - Start - The module should already be running by now. The module can 
      now start sending messages to other components for processing.

.. warning::

   It's highly suggested to **NOT** use the __init__ function for your module's
   class. If you *must* use the __init__ function, be sure to call the parent
   __init__ function before any actions take place within your local __init__.

Modules have 2 phases of shutdown: _stop, _unload
    - Stop - The gateway is on the first phase of shutting down. The module
      should no longer send messages.  It can still receive them after this
      function ends.
    - Unload - This module should stop everything, close connections, close
      files, save any work. The module will no longer recieve any messages
      during this phase of shutdown.

**Usage**:

.. code-block:: python

   from yombo.core.module import YomboModule
    
   class ExampleModule(YomboModule):
       def _init_(self):
           self._ModDescription = "Insteon API command interface"
           self._ModAuthor = "Mitch Schwenk @ Yombo"
           self._ModUrl = "https://yombo.net/SomeUrlForDetailsAboutThisModule"

           self._RegisterDistributions = ['cmd'] # register to get all CMD messages.
           self._RegisterVoiceCommands = [
             {'voiceCmd': "insteon [reset]", 'order' : 'nounverb'}
             ]
            
       def _load_(self):
           pass    #do stuff on loading of the module.
                   #modules can't send messages at this point, but after load completes
                   #it should be able to receive messages for processing.

        def _start_(self):
            pass    #do stuff when module can now send and receive messages.
            
        def _stop_(self):
            pass    # the first phase of module gateway shut down. Should no longer
                    # send messages to other modules/components like normal run time
                    # but can still technically do so if desired while inside this
                    # call.  After this function completes, should no longer send
                    # messages, but is required to continue to process messages
                    # until the unload() function is called.

        def _unload_(self):
            pass    #the gateway is on final phase of shutdown. Must quit now!

        def message(self, message):
            pass    #process an incoming message.
            

The module can register to any distribution that is a valid message type as
well "all" to recieve all message types. See
*msgType* details in the :py:meth:`yombo.core.message.Message.__init__`
documentation.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2015 by Yombo.
:license: LICENSE for details.
"""
# Import Yombo libraries
#from yombo.core.component import IModule
from yombo.core.helpers import getModuleVariables, getDevicesByDeviceType, getCommands, getCronTab, getTimes, getComponent
from yombo.core.fuzzysearch import FuzzySearch
from yombo.core.exceptions import YomboWarning


class YomboModule:
    """
    Defines basic items for all modules and helps with consistency.

    :cvar _Name: (string) Name of the class (aka module name). EG: x10api
    :cvar _FullName: (string) Name **full** of the class for routing. EG: yombo.modules.x10api
    :cvar _Description: (string) Description, needs to be set in the module's init() function.
    :cvar _ModAuthor: (string) Module author, needs to be set in the module's init() function.
    :cvar _ModUrl: (string) URL for additional information about this
      module, needs to be set in the module's init() function.
    :cvar _ModVariables: (dict) Dictionary of the module level variables as defined online
      and set as per the user.
    :cvar _ModType: (string) Type of module (interface, command, logic, other). Defined here,
      but set in _Loader(), which is called just before the module's init().
    :cvar _ModuleUUID (string) UUID of this module.
    :cvar _LocalDevices: (dict) Dictionary to all devices this module controls.
    :cvar _LocalDeviceTypes: (list) List of device types that are registered for this module.
    :cvar _LocalDevicesByType: (dict) Dictionary of devices this module controls, broken down by device type
    :cvar _Commands: preloaded pointer to all configured commands.
    :cvar _Devices: preloaded pointer to all configured devices.
    :cvar _DevicesByType: preloaded pointer to all configured devices by type.
    :cvar _RegisterDistributions: (list) Defined by the module author. Used to subscribe
      to any message distribution lists. Typically use for "cmd" and "status" distros.
    :cvar _RegisterVoiceCommands: (list) Register voice commands to be used to send
      commands to the module.
    """

    def __init__(self):
        """
        Setup basic class items. See variables list for specific information
        variable information.
        """
        self._Name = self.__class__.__name__
        self._FullName = "yombo.gateway.modules.%s" % (self.__class__.__name__)
        self._ModDescription = "NA"
        self._ModAuthor = "NA"
        self._ModURL = "NA"
        self._ModuleUUID = ""
        self._ModVariables = getModuleVariables(self._Name)
        self._Commands = getCommands()
        self._CronTab = getCronTab()
        self._Times = getTimes()

        self._ModuleLibrary = getComponent('yombo.gateway.lib.modules')

        self._DevicesByType = getDevicesByDeviceType()  # returns a callable (function)

        self._LocalDevicesByUUID = {}
        self._LocalDeviceTypesByUUID = {}
        self._LocalDeviceTypesByName = FuzzySearch({}, .95)
        self._LocalDevicesByDeviceTypeUUID = {}

    def _Loader(self, moduleDetails):
        """
        Called by the loader to set some module details.
        
        :param moduleDetails: Various details about the module, which was stored in the database
          and set online.
        :type moduleDetails: dict
        """
        self._ModType = moduleDetails['moduletype']
        self._ModuleUUID = moduleDetails['moduleuuid']

        self._Devices = self._ModuleLibrary.getModuleDevices(self._ModuleUUID) # returns an array of pointers to devices
        self._DevicesByName = {}
        self._DeviceTypes = self._ModuleLibrary.getModuleDeviceTypes(self._ModuleUUID)
        for device in self._Devices:
            self._DevicesByName[self._Devices[device].label] = self._Devices[device].deviceUUID

    def _UpdateDeviceTypes(self, oldDeviceType, newDeviceType):
        """
        Updates the local module pointers to devicetypes when an updates/deleted/new device type is registered. This
        would happen when a new an update is made from the server.

        :param oldDeviceType: If not new, this would be the information from the old deviceType information
        :param newDeviceType: Updated or new device type. If deleted, this would be None.
        """

        #TODO This entire thing is broken. DTYPE is not defined. What's up with that?

        #Handle updated first
        if oldDeviceType is not None and newDeviceType is None:
            self._LocalDeviceTypesByUUID[oldDeviceType['devicetypeuuid']] = newDeviceType['label']
            del self._LocalDeviceTypesByName[oldDeviceType['label']]
            self._LocalDeviceTypesByName[newDeviceType['label']] = newDeviceType['devicetypeuuid']

        #handle new deviceTypes
        elif oldDeviceType is None and newDeviceType is not None:
            self._LocalDeviceTypesByUUID[newDeviceType['devicetypeuuid']] = newDeviceType['label']
            self._LocalDeviceTypesByName[newDeviceType['label']] = newDeviceType['devicetypeuuid']
            self._LocalDevicesByDeviceTypeUUID[newDeviceType['devicetypeuuid']] = \
                self._DevicesByType(deviceTypeUUID=dtype['devicetypeuuid'])

        #handle deleting a device type
        elif oldDeviceType is not None and newDeviceType is None:
            del self._LocalDeviceTypesByUUID[oldDeviceType['devicetypeuuid']]
            del self._LocalDeviceTypesByName[oldDeviceType['label']]
            del self._LocalDevicesByDeviceTypeUUID[oldDeviceType['devicetypeuuid']]

        #Some Error
        else:
            raise YomboWarning("Error updating device type in module: %s" % self._FullName)

        self._UpdateDeviceTypes_(oldDeviceType, newDeviceType)

    def _UpdateDevice(self, oldDevice, newDevice):
        """
        Updates the local module pointers to devices when an updates/deleted/new device is registered. This
        would happen when a new an update is made from the server.

        :param oldDevice: If not new, this would be the information from the old deviceType information
        :param newDevice: Updated or new device. If deleted, this would be Non.
        """
        #Handle updated first
        if oldDevice is not None and newDevice is not None:
            self._LocalDevicesByUUID[newDevice.deviceUUID] = newDevice

        #handle new  (same as updating in this use case)
        elif oldDevice is None and newDevice is not None:
            self._LocalDevicesByUUID[newDevice.deviceUUID] = newDevice

        #handle deleting
        elif oldDevice is not None and newDevice is None:
            del self._LocalDevicesByUUID[oldDevice.deviceUUID]

#        self._UpdateDevice_(oldDevice, newDevice)

    def _UpdateDeviceTypes_(self, oldDeviceType, newDeviceType):
        """
        When device types are updated, let the module know that it should handle any updates itself.
        """
        pass

    def _UpdateDeviceTypes_(self, oldDeviceType, newDeviceType):
        """
        When devices are updated, let the module know that it should handle any updates itself.
        """
        pass

    def _init_(self):
        """
        Phase 1 of 3 for statup - configure basic variables, etc. Like __init__.
        """
        raise NotImplementedError()

    def _load_(self):
        """
        Phase 2 of 3 for statup - Called when module should load anything else. After this
        function completes, it should be able to accept and process messages. Doesn't send
        messages at this stage.
        """
        raise NotImplementedError()

    def _start_(self):
        """
        Phase 3 of 3 for statup - Called when this module should start processing and is
        now able to send messages to other components.
        """
        raise NotImplementedError()

    def _stop_(self):
        """
        Phase 1 of 2 for shutdown - Stop sending messages, but can still accept incomming
        messages for processing.
        """
        raise NotImplementedError()

    def _unload_(self):
        """
        Phase 2 of 2 for shutdown - By the time this is called, no messages will be sent
        to this module. Close all connections/items. Once this function ends, it's
        possible that the process will terminate.
        """
        raise NotImplementedError()

    def message(self, message):
        """
        Incoming messeages from other components (internal and external to the gateway) will
        be sent to this method.
        """
        raise NotImplementedError()
