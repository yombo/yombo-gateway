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

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/module.html>`_
"""
from copy import deepcopy
import sys
import traceback
from typing import Any, ClassVar, Dict, List, Optional, Union

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.entity import Entity
from yombo.core.log import get_logger
from yombo.mixins.child_storage_accessors_mixin import ChildStorageAccessorsMixin
# from yombo.utils.decorators import cached

logger = get_logger("core.entity")


class YomboModule(Entity, ChildStorageAccessorsMixin):
    """
    This class quickly integrates user developed modules into the Yombo framework. It also sets up various
    predefined various and functions.
    """
    _Entity_type: ClassVar[str] = "module"

    def __init__(self, parent, *args, **kwargs) -> None:
        try:  # Some exceptions not being caught. So, catch, display and release.
            super().__init__(parent, **kwargs)
        except Exception as e:
            print(e)
            print(f"{traceback.print_exc(file=sys.stdout)}")
            print(f"YomboModule caught init exception in {self._Name}: {e}")
            raise e

    @property
    def module_variables(self):
        """
        Gets all fields with data.

        :return:
        """
        return self._VariableData.data("module", self._module_id)

    @property
    def module_variable_fields(self):
        """
        Returns all variable fields for the current module.
        :return:
        """
        return self._VariableGroups.fields("module", self._module_id)

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
            gateway_id = self._gateway_id
        devices = {}
        # print(f"core.module: module device types: {self.module_device_types}")
        for module_device_type_id, module_device_type in self.module_device_types.items():
            # print(f"core.module: module device type: {module_device_type.device_type_id}")
            device_type_id = module_device_type.device_type_id
            try:
                devices.update(self._DeviceTypes[device_type_id].get_devices(gateway_id=gateway_id))
            except Exception as e:
                print(f"module_device: caught: {e}")
        # print(f"module: module_devices done: {devices}")
        return devices

    @property
    def module_device_types(self):
        return self._ModuleDeviceTypes.search(self._module_id)

    def _is_my_device(self, device):
        if device.device_id in self.module_devices and device.gateway_id == self._gateway_id:
            return True
        else:
            return False

    def __str__(self):
        """
        Print a string when printing the class.
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

    def to_dict(self, to_database: Optional[bool] = None, to_external: Optional[bool] = None,
                include_meta: Optional[bool] = None, incoming_data: Optional[dict] = None):
        """
        Represents the current child class as a dictionary. Depending on the final destination, the output can be
        altered as needed.

        Do not set to_database and to_event to true at same time.

        :param to_database: If true, only the database fields will be returned.
        :param to_external: If true, the dict will be formated for JSONAPI format.
        :param include_meta: If true, will include additional details, typically used internally.
        :param incoming_data: Use this data instead of the class data. Used for testing and Yombo API sync.
        :return:
        """
        if to_database is None:
            to_database = False
        if to_external is None:
            to_external = False
        if include_meta is None:
            include_meta = False

        if to_database is True and to_external is True:
            raise YomboWarning("to_dict() cannot have both to_database and to_external as true.")

        data = {}
        if include_meta is True and hasattr(self, "_meta"):
            meta = self._meta
        else:
            meta = {}

        fields = {
            "id": "_module_id",
            "user_id": "_user_id",
            "original_user_id": "_original_user_id",
            "module_type": "_module_type",
            "machine_label": "_machine_label",
            "label": "_label",
            "short_description": "_short_description",
            "medium_description": "_medium_description",
            "description": "_description",
            "medium_description_html": "_medium_description_html",
            "description_html": "_description_html",
            "see_also": "_see_also",
            "repository_link": "_repository_link",
            "issue_tracker_link": "_issue_tracker_link",
            "install_count": "_install_count",
            "doc_link": "_doc_link",
            "git_link": "_git_link",
            "git_auto_approve": "_git_auto_approve",
            "public": "_public",
            "status": "_status",
            "install_branch": "_install_branch",
            "require_approved": "_require_approved",
            "created_at": "_created_at",
            "updated_at": "_updated_at",
            "load_source": "_load_source",
        }

        try:
            for key, field in fields.items():
                data[key] = getattr(self, field)
        except Exception as e:
            logger.warn("Error generating to_dict() data: {e}", e=e)

        if hasattr(self, "to_dict_postprocess"):  # allow children to have final say in content.
            try:
                self.to_dict_postprocess(data, meta, to_external=to_external, to_database=to_database,
                                         include_meta=include_meta)
            except Exception as e:
                logger.warn("(1) Error generating to_dict postprocess: {e}", e=e)

        if include_meta is False:
            return deepcopy(data)
        else:
            return {"data": deepcopy(data), "meta": deepcopy(meta)}

    def search_for_device(self, search_variable: Union[str, List[str]], value: Any,
                          ignore_case: Optional[bool] = None, all_devices: Optional[bool] = None,
                          value_position: Optional[int] = None):
        """
        Looks for a device based on a device's variable value. This allows modules to quickly find a specific device
        that it manages.

        :param search_variable: Name of the variable to look for. Either a string or a list of strings.
        :param value: The value to match with.
        :param ignore_case: If True (default:True), casing for values will be ignored.
        :param all_devices: If True (default:False), all devices will be searched instead of only this module's devices.
        :param value_position: What position within the list of values to use. Use negative number to search for all.
        :return:
        """
        if all_devices is True:
            devices = self._Devices.devices
        else:
            devices = self.module_devices

        def match_value(value_to_check):
            """
            Does the actual matching of the value.

            :param value_to_check: The value to check 'value' against.
            :return:
            """
            if ignore_case:
                if value_to_check.lower() == value_to_check.lower():
                    return True
            if value_to_check == value_to_check:
                return True
            return False

        if value_position is None:
            value_position = 0

        for device_id, device in devices.items():
            variables = device.device_variables
            if search_variable in variables and len(variables[search_variable]["data"]):
                if isinstance(value_position, int):
                    if value_position > 0:
                        for check_value in variables[search_variable]["data"]:
                            results = match_value(check_value)
                            if results is True:
                                return device

                    if value_position > 0:
                        for check_value in variables[search_variable]["data"]:
                            results = match_value(check_value)
                            if results is True:
                                return device
                    else:
                        results = match_value(variables[search_variable]["data"][value_position])
                        if results is True:
                            return device
        return None

    def to_dict_postprocess(self, data, meta, to_database: Optional[bool] = None,
                            **kwargs) -> None:
        """
        Updates to_dict results to include additional module items.
        """
        if to_database is False:
            module_device_types = yield self._module_device_types()
            module_devices = yield self.module_devices
            devices = {}
            for device_id, device in module_devices.items():
                devices[device_id] = {
                    "device_id": device_id,
                    "label": device.label,
                    "machine_label": device.machine_label,
                }
            data.update({
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
                })
