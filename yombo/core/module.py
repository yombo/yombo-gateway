# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Module developers must use the *YomboModule* class as their base class. This class
gets their module setup and running with basic functions, predefined variables,
and functions.

.. warning::

   It's highly suggested to **NOT** use the __init__ (double underscore)function for
   your module's class. If you *must* use the __init__ function, be sure to call the
   parent __init__ function before any actions take place within your local __init__.

Modules have 3 primary phases of startup: _init_, _load_, _start_ (single underscores,
not double. This have been extended to include additional phases and can be used as needed.
The primary phases:

    - *_init_* - Get the basics of the module running.  All libraries are
      loaded and available.  Not all modules have been through init
      this stage.  A deferred can be returned if the :ref:`Loader`
      should wait until the module has completed it's init phase.
    - *_load_* - All modules have completed init phase.  Now it's time to get the
      module ready to receive messages. By the time _load_() finishes, the
      module should be able to receive messages and process them, even if this means
      it needs to queue sending messages until _start_() is called. A deferred can be
      returned if the :ref:`Loader` should wait until the module has completed it's
      load phase.
    - *_start_* - The module should already be running by now. The module can
      now start sending messages to other components for processing.
      A _prestart_ function exists and will be called before _start_.

Additional phases:

    - *_preload_* - This will be called before _load_.
    - *_prestart_* - Called just before _start_.
    - *_started_* - Caled after _start_.


Modules have 2 phases of shutdown: _stop, _unload
    - *_stop_* - The gateway is on the first phase of shutting down. The module
      should no longer send messages.  It can still receive them after this
      function ends, but should only process them if it's able. Not expected
      to perform after it's called, only if able.
    - *_unload_* - This module should stop everything, close connections, close
      files, save any work. The module will no longer receive any messages
      during this phase of shutdown.

**Hooks**

Yombo's module system also implements a concept of "hooks". A hook is a
python function that is can be called from other libraries or modules.

See :ref:`Hooks <hooks>` for details on usage and examples.

**Usage**:

.. code-block:: python

   from yombo.core.module import YomboModule
   class ExampleModule(YomboModule):
       def _init_(self):
           self._ModDescription = "Insteon API command interface"
           self._ModAuthor = "Mitch Schwenk @ Yombo"
           self._ModUrl = "https://yombo.net/SomeUrlForDetailsAboutThisModule"
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
        def ExampleModule_message_subscriptions(self, **kwargs):
           return ['cmd'] # register to get all CMD messages.
        def ExampleModule_voicecmds(self, **kwargs):
           return [ {'voiceCmd': "homevision [reset]", 'order' : 'nounverb'} ] # register new voice commands
        def message(self, message):
            pass    #process an incoming message.

The module can register to any distribution that is a valid message type as
well "all" to receive all message types. See
*msgType* details in the :py:meth:`yombo.core.message.Message.__init__`
documentation.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import Yombo libraries

from yombo.core.log import get_logger

logger = get_logger('core.module')


class YomboModule:
    """
    This class quickly integrates user developed modules into the Yombo framework. It also sets up various
    predefined various and functions.

    Variables that can be set:

    :ivar _ModDescription: (string) Description, needs to be set in the module's init() function.
    :ivar _ModAuthor: (string) Module author, needs to be set in the module's init() function.
    :ivar _ModUrl: (string) URL for additional information about this
      module, needs to be set in the module's init() function.

    These variables are defined by this class and should be defined by the module developer.

    :ivar _Name: (string) Name of the class (aka module name). EG: x10api
    :ivar _FullName: (string) Name **full** of the class for routing. EG: yombo.modules.x10api
    :ivar _Atoms: (object/dict) The Yombo Atoms library, but can accessed as a dictionary or object.
    :ivar _Commands: preloaded pointer to all configured commands.
    :ivar _Commands: Pointer to configuration options. Use self._Configs.get("section", "key") to use.
    :ivar _DevicesLibrary: (dict) The devices library acts like a dictionary to *ALL* devices.
    :ivar _Devices: (dict) A dictionary of devices that this module controls based of device types this module manages.
    :ivar _DevicesByType: (callback) A function to quickly get all devices for a specific device type.
    :ivar _DeviceTypes: (list) List of device types that are registered for this module.
    :ivar _Libraries: (dict) A dictionary of all modules. Returns pointers.
    :ivar _Modules: (object/dict) The Modules Library, can be access as dictionary or object. Returns a pointer.
    :ivar _ModuleType: (string) Type of module (Interface, Command, Logic, Other).
    :ivar _ModuleID: (string) The UUID of the module.
    :ivar _ModuleVariables: (dict) Dictionary of the module level variables as defined online
      and set as per the user.
    :ivar _States: (object/dict) The Yombo States library, but can accessed as a dictionary or object.
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
        self._ModUrl = "NA"
        self._ModuleType = None
        self._ModuleID = None

        self._Devices = None
        self._DeviceTypes = None

        self._ModuleVariables = None
        self._ModulesLibrary = None

    def _GetDeviceTypes(self):
        return self._Modules.module_device_types(self._ModuleID)

    def _GetDevices(self):
        return self._DevicesTypes.module_devices(self._ModuleID)

    def __str__(self):
        """
        Returns a string of this module's UUID.

        :return: A dictionary of core attributes.
        :rtype: dict
        """
        return self._ModuleID

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
        pass

    def _start_(self):
        """
        Phase 3 of 3 for statup - Called when this module should start processing and is
        now able to send messages to other components.
        """
        pass

    def _stop_(self):
        """
        Phase 1 of 2 for shutdown - Stop sending messages, but can still accept incomming
        messages for processing.
        """
        pass

    def _unload_(self):
        """
        Phase 2 of 2 for shutdown - By the time this is called, no messages will be sent
        to this module. Close all connections/items. Once this function ends, it's
        possible that the process will terminate.
        """
        pass

    def _dump(self):
        """
        Returns a dictionary of core attributes about this module. Usually used for debugging.

        :return: A dictionary of core attributes.
        :rtype: dict
        """
        return {
            '_Name': self._Name,
            '_FullName': self._FullName,
            '_ModDescription': self._ModDescription,
            '_ModAuthor': self._ModAuthor,
            '_ModuleType': self._ModuleType,
            '_ModuleID': self._ModuleID,
            '_ModUrl': self._ModUrl,
            '_Devices': self._Devices,
            '_DevicesByType': self._DevicesByType,
            '_DeviceTypes': self._DeviceTypes,
            '_ModuleVariables': self._ModuleVariables,
            '_ModulesLibrary': self._ModulesLibrary,
        }

    def amqp_incoming(self, deliver, properties, message):
        """
        Basic routing of incoming AQMP message packagets to a module. Sends requests to 'amqp_incoming_request'
        and responses to 'amqp_incoming_response'.

        :param deliver:
        :param properties:
        :param message:
        """
#        logger.info("deliver (%s), props (%s), message (%s)" % (deliver, properties, message,))
#        logger.info("headers... {headers}", headers=properties.headers)
        if properties.headers['type'] == 'request':
            if message['data_type'] == 'object': # a single response
                self.amqp_incoming_request(deliver, properties, message['request'])
            elif message['data_type'] == 'objects': # An array of responses
                for response in message['request']:
                    self.amqp_incoming_request(deliver, properties, response)
        elif properties.headers['type'] == "response":
            if message['data_type'] == 'object': # a single response
                self.amqp_incoming_response(deliver, properties, message['response'])
            elif message['data_type'] == 'objects': # An array of responses
                for response in message['response']:
                    self.amqp_incoming_response(deliver, properties, response)