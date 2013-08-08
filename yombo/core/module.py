# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
A shell for module developers to get basic items configured for modules.

All modules should extend this module.  See the class documentation for
additional details.

Modules have 3 phases of startup: init, load, start.
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

Modules have 2 phases of shutdown: stop, unload
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
       def init(self):
           self._ModDescription = "Insteon API command interface"
           self._ModAuthor = "Mitch Schwenk @ Yombo"
           self._ModUrl = "http://www.yombo.net/SomeUrlForDetailsAboutThisModule"

           self._RegisterDistributions = ['cmd'] # register to get all CMD messages.
           self._RegisterVoiceCommands = [
             {'voiceCmd': "insteon [reset]", 'order' : 'nounverb'}
             ]
            
       def load(self):
           pass    #do stuff on loading of the module.
                   #modules can't send messages at this point, but after load completes
                   #it should be able to receive messages for processing.

        def start(self):
            pass    #do stuff when module can now send and receive messages.
            
        def stop(self):
            pass    # the first phase of module gateway shut down. Should no longer
                    # send messages to other modules/components like normal run time
                    # but can still technically do so if desired while inside this
                    # call.  After this function completes, should no longer send
                    # messages, but is required to continue to process messages
                    # until the unload() function is called.

        def unload(self):
            pass    #the gateway is on final phase of shutdown. Must quit now!

        def message(self, message):
            pass    #process an incoming message.
            

The module can register to any distribution that is a valid message type as
well "all" to recieve all message types. See
*msgType* details in the :py:meth:`yombo.core.message.Message.__init__`
documentation.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""

#import zope.interface
from yombo.core.component import IModule
from yombo.core.helpers import getModuleVariables, getDevices, getCommands, getDevicesByType, getModuleDeviceTypes

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
    :cvar _Devices: preloaded pointer to all configured devices.
    :cvar _Commands: preloaded pointer to all configured commands.
    :cvar _DevicesByType: preloaded pointer to all configured devices by type.
    :cvar _DeviceTypes: (list) List of device types that are registered for this module.
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
        self._Devices = getDevices()
        self._Commands = getCommands()
        self._DevicesByType = getDevicesByType()
        self._DeviceTypes = []

    def _Loader(self, moduleDetails):
        """
        Called by the loader to set some module details.
        
        :param moduleDetails: Various details about the module, which was stored in the database
          and set online.
        :type moduleDetails: dict
        """
        self._ModType = moduleDetails['moduletype']
        self._ModuleUUID = moduleDetails['moduleuuid']
        deviceTypes = getModuleDeviceTypes(moduleDetails['moduleuuid'])
        for dtype in deviceTypes:
            self._DeviceTypes.append(dtype['devicetypeuuid'])
    
    def init(self):
        """
        Phase 1 of 3 for statup - configure basic variables, etc. Like __init__.
        """
        raise NotImplementedError()

    def load(self):
        """
        Phase 2 of 3 for statup - Called when module should load anything else. After this
        function completes, it should be able to accept and process messages. Doesn't send
        messages at this stage.
        """
        raise NotImplementedError()

    def start(self):
        """
        Phase 3 of 3 for statup - Called when this module should start processing and is
        now able to send messages to other components.
        """
        raise NotImplementedError()

    def stop(self):
        """
        Phase 1 of 2 for shutdown - Stop sending messages, but can still accept incomming
        messages for processing.
        """
        raise NotImplementedError()

    def unload(self):
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

