# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Module Core @ Module Development <https://yombo.net/docs/core/module>`_


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
           pass    #do stuff when first being loaded
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
           return ["cmd"] # register to get all CMD messages.
        def message(self, message):
            pass    #process an incoming message.

The module can register to any distribution that is a valid message type as
well "all" to receive all message types. See
*msgType* details in the :py:meth:`yombo.core.message.Message.__init__`
documentation.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/module.html>`_
"""
from twisted.internet.defer import inlineCallbacks


# Import Yombo libraries
from yombo.core.entity import Entity
# from yombo.utils.decorators import cached


class YomboModule(Entity):
    """
    This class quickly integrates user developed modules into the Yombo framework. It also sets up various
    predefined various and functions.

    Variables that can be set:

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
    :ivar _Modules: (object/dict) The Modules Library, can be access as dictionary or object. Returns a pointer.
    :ivar _ModuleType: (string) Type of module (Interface, Command, Logic, Other).
    :ivar module_variables: (dict) Live dictionary of the module level variables as defined online
      and set as per the user.
    :ivar _States: (object/dict) The Yombo States library, but can accessed as a dictionary or object.
    """
    def __init__(self, *args, **kwargs):
        try:  # Some exceptions not being caught. So, catch, display and release.
            if hasattr(self, '_import_init_'):
                self._import_init_(**kwargs)
            self._Entity_type = "module"
            super().__init__(self, **kwargs)
        except Exception as e:
            print(f"YomboLibrary caught init exception: {e}")
            raise e

    @property
    def module_variables(self):
        """
        Gets all fields with data.

        :return:
        """
        return self._VariableGroups.data("module", self._module_id)
        # fields = {}
        # field_map = {}
        # for variable_id, variable in variables.items():
        #     if variable.variable_field_id not in field_map:
        #         field_map[variable.variable_field_id] = self._Variables.field_by_id(variable.variable_field_id)
        #     field_name = field_map[variable.variable_field_id].field_machine_label
        #
        #     if field_name not in fields:
        #         fields[field_name] = {"data": [], "decrypted": [], "display": [], "ref": []}
        #
        #     fields[field_name]["data"].append(variable.data)
        #     fields[field_name]["decrypted"].append(variable.decrypted)
        #     fields[field_name]["display"].append(variable.display)
        #     fields[field_name]["ref"].append(variable)
        # return fields

    @property
    def module_variable_fields(self):
        """
        Returns all variable fields for the current module.
        :return:
        """
        return self._VariableGroups.fields("module", self._module_id)
        # fields = {}
        # field_map = {}
        # for variable_id, variable in variables.items():
        #     if variable.variable_field_id not in field_map:
        #         field_map[variable.variable_field_id] = self._Variables.field_by_id(variable.variable_field_id)
        #     field_name = field_map[variable.variable_field_id].field_machine_label
        #
        #     if field_name not in fields:
        #         fields[field_name] = {"data": [], "decrypted": [], "display": [], "ref": []}
        #
        #     fields[field_name]["data"].append(variable.data)
        #     fields[field_name]["decrypted"].append(variable.decrypted)
        #     fields[field_name]["display"].append(variable.display)
        #     fields[field_name]["ref"].append(variable)
        # return fields

    # @cached(1)
    @property
    def module_devices(self, gateway_id=None):
        """
        A list of devices for a given module id.

        :raises YomboWarning: Raised when module_id is not found.
        :param gateway_id: Restrict what gateway the devices should belong to.
        :return: A dictionary of devices for a given module id.
        :rtype: list
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        devices = {}
        for module_device_type_id, module_device_type in self.module_device_types.items():
            device_type_id = module_device_type.device_type_id
            devices.update(self._DeviceTypes[device_type_id].get_devices(gateway_id=gateway_id))
        return devices

    @property
    def module_device_types(self):
        return self._ModuleDeviceTypes.search(self._module_id)

    def _is_my_device(self, device):
        if device.device_id in self.module_devices and device.gateway_id == self._Devices.gateway_id:
            return True
        else:
            return False

    def __str__(self):
        """
        Print a string when printing the class.  This will return the cmdUUID so that
        the command can be identified and referenced easily.
        """
        return f"{self._label}.{self._module_id}"

    def _init_(self, **kwargs):
        """
        Phase 1 of 3 for statup - configure basic variables, etc. Like __init__.
        """
        pass

    def _load_yombo_internal_(self, **kwargs):
        """
        Load some internal items.
        """
        pass
        # self._devices = partial(self._Modules.module_devices, self._module_id)

    def _start_(self, **kwargs):
        """
        Phase 3 of 3 for statup - Called when this module should start processing and is
        now able to send messages to other components.
        """
        pass

    def _stop_(self, **kwargs):
        """
        Phase 1 of 2 for shutdown - Stop sending messages, but can still accept incoming
        messages for processing.
        """
        pass

    def _unload_(self, **kwargs):
        """
        Phase 2 of 2 for shutdown - By the time this is called, no messages will be sent
        to this module. Close all connections/items. Once this function ends, it's
        possible that the process will terminate.
        """
        pass

    def amqp_incoming(self, headers, **kwargs):
        """
        Basic routing of incoming AQMP message packagets to a module. Sends requests to "amqp_incoming_request"
        and responses to "amqp_incoming_response".
        """
        if headers["message_type"] == "request":
            self.amqp_incoming_request(headers=headers, **kwargs)
        if headers["message_type"] == "response":
            self.amqp_incoming_response(headers=headers, **kwargs)

    def amqp_incoming_request(self, headers, body, **kwargs):
        """
        This method should be implemented by any modules expecting to receive amqp incoming requests.
        """
        pass

    def amqp_incoming_response(self, headers, body, **kwargs):
        """
        This method should be implemented by any modules expecting to receive amqp incoming responses.
        """
        pass

    @inlineCallbacks
    def asdict(self):
        """
        Returns a dictionary of core attributes about this module.

        :return: A dictionary of core attributes.
        :rtype: dict
        """
        module_device_types = yield self._module_device_types()
        module_devices = yield self.module_devices
        devices = {}
        for device_id, device in module_devices.items():
            devices[device_id] = {
                "device_id": device_id,
                "label": device.label,
                "machine_label": device.machine_label,
            }
        return {
            "_Name": self._Name,
            "_FullName": self._FullName,
            "_module_id": str(self._module_id),
            "_module_type": str(self._module_type),
            "_install_count": self._install_count,
            "_issue_tracker_link": self._issue_tracker_link,
            "_label": str(self._label),
            "_machine_label": str(self._machine_label),
            "_short_description": str(self._short_description),
            "_medium_description": str(self._medium_description),
            "_description": str(self._description),
            "_see_also": self._see_also,
            "_doc_link": str(self._doc_link),
            "_git_link": str(self._git_link),
            "_repository_link": self._repository_link,
            "_install_branch": str(self._install_branch),
            "_require_approved": int(self._require_approved),
            "_public": int(self._public),
            "_status": int(self._status),
            "_created_at": int(self._created_at),
            "_updated_at": int(self._updated_at),
            "_load_source": str(self._load_source),
            "_device_types": module_device_types,
            "_module_variables": self.module_variables,
            "_module_devices": devices,
        }
