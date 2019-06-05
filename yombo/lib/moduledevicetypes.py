# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `module device types @ Library Documentation <https://yombo.net/docs/libraries/module_device_types>`_

Maps what modules have what device types. Used by the module library primarily.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/moduledevicetypes.html>`_
"""
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.core.log import get_logger
from yombo.mixins.sync_to_everywhere import SyncToEverywhere
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.module_device_types")


class ModuleDeviceTypes(YomboLibrary, LibrarySearchMixin):
    """
    Manages module device types.
    """
    module_device_types = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_attribute_name = "module_device_types"
    _class_storage_fields = [
        "device_type_id", "command_id"
    ]
    _class_storage_sort_key = "device_type_id"

    def __contains__(self, module_device_type_requested):
        """
        Checks to if a provided module id or device type id exists.

            >>> if "0kas02j1zss349k1" in self._ModuleDeviceTypes =:

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param module_device_type_requested: The module id to search for.
        :type module_device_type_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            if len(self.get(module_device_type_requested)) > 0:
                return True
        except:
            pass
        return False

    def __getitem__(self, module_device_type_requested):
        """
        Gets all device types for a provided module id.

            >>> module_device_type = self._ModuleDeviceTypes =["0kas02j1zss349k1"]  # by id

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param module_device_type_requested: The module ID to search for.
        :type module_device_type_requested: string
        :return: A pointer to the module device type instance.
        :rtype: instance
        """
        return self.get(module_device_type_requested)

    def __setitem__(self, **kwargs):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, **kwargs):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter module device types. """
        return self.module_device_types.__iter__()

    def __len__(self):
        """
        Returns an int of the number of module device types configured.

        :return: The number of module device types configured.
        :rtype: int
        """
        return len(self.module_device_types)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo module device types library"

    def keys(self):
        """
        Returns the keys (module device type ID's) that are configured.

        :return: A list of module device type IDs.
        :rtype: list
        """
        return list(self.module_device_types.keys())

    def items(self):
        """
        Gets a list of tuples representing the module device types configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.module_device_types.items())

    def values(self):
        return list(self.module_device_types.values())

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self._started = False
        yield self._load_module_device_types_from_database()

    def _start_(self, **kwargs):
        self._started = True

    @inlineCallbacks
    def _load_module_device_types_from_database(self):
        """
        Loads module device types from database and sends them to
        :py:meth:`_load_module_device_types_into_memory <ModuleDeviceTypes._load_module_device_types_into_memory>`

        This can be triggered either on system startup or when new/updated module_device_type have been saved to the
        database and we need to refresh existing items.
        """
        module_device_types = yield self._LocalDB.get_module_device_types()
        for item in module_device_types:
            self._load_module_device_types_into_memory(item.__dict__, "database")

    def _load_module_device_types_into_memory(self, module_device_type, source=None):
        """
        Add a new module device types to memory or update an existing.

        **Hooks called**:

        * _module_device_type_before_import_ : When this function starts.
        * _module_device_type_imported_ : When this function finishes.
        * _module_device_type_before_load_ : If added, sends DTC dictionary as "module_device_type"
        * _module_device_type_before_update_ : If updated, sends DTC dictionary as "module_device_type"
        * _module_device_type_loaded_ : If added, send the DTC instance as "module_device_type"
        * _module_device_type_updated_ : If updated, send the DTC instance as "module_device_type"

        :param module_device_type: A dictionary of items required to either setup a new module_device_type or update
          an existing one.
        :type module_device_type: dict
        """

        module_device_type_id = module_device_type["id"]
        # Stop here if not in run mode.
        if self._started is True:
            global_invoke_all("_module_device_type_before_import_",
                              called_by=self,
                              module_device_type_id=module_device_type_id,
                              module_device_type=module_device_type,
                              )
        if module_device_type_id not in self.module_device_types:
            if self._started is True:
                global_invoke_all("_module_device_type_before_load_",
                                  called_by=self,
                                  module_device_type_id=module_device_type_id,
                                  module_device_type=module_device_type,
                                  )
            self.module_device_types[module_device_type_id] = ModuleDeviceType(self,
                                                                                 module_device_type,
                                                                                 source=source)
            if self._started is True:
                global_invoke_all("_module_device_type_loaded_",
                                  called_by=self,
                                  module_device_type_id=module_device_type_id,
                                  module_device_type=self.module_device_types[module_device_type_id],
                                  )

        elif module_device_type_id not in self.module_device_types:
            if self._started is True:
                global_invoke_all("_module_device_type_before_update_",
                                  called_by=self,
                                  module_device_type_id=module_device_type_id,
                                  module_device_type=self.module_device_types[module_device_type_id],
                                  )
            self.module_device_types[module_device_type_id].update_attributes(module_device_type, source=source)
            if self._started is True:
                global_invoke_all("_module_device_type_updated_",
                                  called_by=self,
                                  module_device_type_id=module_device_type_id,
                                  module_device_type=self.module_device_types[module_device_type_id],
                                  )
        if self._started is True:
            global_invoke_all("_module_device_type_imported_",
                              called_by=self,
                              module_device_type_id=module_device_type_id,
                              module_device_type=self.module_device_types[module_device_type_id],
                              )
        return self.module_device_types[module_device_type_id]

    def get(self, module_id):
        """
        Returns a dictionary of device types available to a module for the provided module_id.

        :param module_id:
        :return:
        """
        results = {}
        for item_id, mdt in self.module_device_types.items():
            if mdt.module_id == module_id:
                try:
                    device_type = self._DeviceTypes.get(mdt.device_type_id)
                    if device_type.device_type_id not in results:
                        results[device_type.device_type_id] = []
                    results[device_type.device_type_id].append(device_type)
                except:
                    raise KeyError(f"Error getting device type '{mdt.device_type_id}' for a module device type.")
        return results

    def get_by_device_type_id(self, device_type_id):
        """
        Returns a dictionary of modules that are associated with a provided device type id.

        :param device_type_id:
        :return:
        """
        results = {}
        for item_id, mdt in self.module_device_types.items():
            if mdt.device_type_id == device_type_id:
                try:
                    module = self._modules.get(mdt.module_id)
                    if module.module_id not in results:
                        results[module.module_id] = []
                    results[module.module_id].append(module)
                except:
                    logger.warning("Error getting module id '{module_id}' for a module device type.",
                                   module_id=mdt.module_id)
                    pass
        return results

    @inlineCallbacks
    def add_module_device_type(self, data, **kwargs):
        """
        Add a module device type at the Yombo server level. We'll also request that the new item be loaded
        into memory.

        :param data:
        :param kwargs:
        :return:
        """
        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            api_results = yield self._YomboAPI.request("POST", "/v1/module_device_types",
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't add module device type: {e.message}",
                "apimsg": f"Couldn't add module device type: {e.message}",
                "apimsghtml": f"Couldn't add module device type: {e.html_message}",
            }

        data["id"] = api_results["data"]["id"]
        data["updated_at"] = time()
        data["created_at"] = time()
        dtc = self._load_module_device_types_into_memory(data, source="amqp")

        return {
            "status": "success",
            "msg": "module device type added.",
            "module_device_type_id": api_results["data"]["id"],
        }

    @inlineCallbacks
    def edit_module_device_type(self, module_device_type_id, data, **kwargs):
        """
        Edit the module device type at the Yombo API level as well as the local level.

        :param data:
        :param kwargs:
        :return:
        """
        if data["machine_label"] == "none":
            raise YomboWarning(
                {
                    "title": "Error editing module device type",
                    "detail": "Machine label is missing or was set to 'none'.",
                },
                component="module_device_types",
                name="edit_module_device_type")

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            api_results = yield self._YomboAPI.request("PATCH", f"/v1/module_device_types/{module_device_type_id}",
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            raise YomboWarning(
                {
                    "title": "Error editing module device type",
                    "detail": e.message,
                },
                component="module_device_types",
                name="edit_module_device_type")

        if module_device_type_id in self.module_device_types:
            self.module_device_types[module_device_type_id].update_attributes(data,
                                                                                source="amqp",
                                                                                session=session)  # Simulate AMQP

        global_invoke_all("_module_device_type_updated_",
                          called_by=self,
                          module_device_type_id=module_device_type_id,
                          module_device_type=self.module_device_types[module_device_type_id],
                          )

        return {
            "status": "success",
            "msg": "Device type edited.",
            "module_device_type_id": api_results["data"]["id"],
        }

    @inlineCallbacks
    def delete_module_device_type(self, module_device_type_id, **kwargs):
        """
        Delete a module device type at the Yombo server level, not at the local gateway level.

        :param module_device_type_id: The module device type ID to delete.
        :param kwargs:
        :return:
        """
        module_device_type = self.get(module_device_type_id)
        if module_device_type["machine_label"] == "none":
            raise YomboWarning(
                {
                    "title": "Error deleting module device type",
                    "detail": "Machine label is missing or was set to 'none'.",
                },
                component="module_device_types",
                name="delete_module_device_type")

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            yield self._YomboAPI.request("DELETE", f"/v1/module_device_types/{module_device_type.module_device_type_id}",
                                         session=session)
        except YomboWarning as e:
            raise YomboWarning(
                {
                    "title": "Error deleting module device type",
                    "detail": e.message,
                },
                component="module_device_types",
                name="delete_module_device_type")

        if module_device_type_id in self.module_device_types:
            del self.module_device_types[module_device_type_id]

        global_invoke_all("_module_device_type_deleted_",
                          called_by=self,
                          module_device_type_id=module_device_type_id,
                          module_device_type=self.module_device_types[module_device_type_id],
                          )

        self._LocalDB.delete_module_device_types(module_device_type)
        return {
            "status": "success",
            "msg": "Location deleted.",
            "module_device_type_id": module_device_type_id,
        }


class ModuleDeviceType(Entity, SyncToEverywhere):
    """
    A class to manage a single module device type.
    """

    def __init__(self, parent, module_device_type, source=None):
        """
        Setup the module device type object using information passed in.

        :param module_device_type: An module device type with all required items to create the class.
        :type module_device_type: dict
        """
        self._internal_label = "module_device_types"  # Used by mixins
        super().__init__(parent)

        #: str: ID for the module_device_type.
        self.module_device_type_id = module_device_type["id"]

        # below are configured in update_attributes()
        self.module_id = None
        self.command_id = None
        self.created_at = None
        self.update_attributes(module_device_type, source=source)
        self.start_data_sync()

    def __str__(self):
        """
        Print a string when printing the class.  This will return the module device type id so that
        the module device type can be identified and referenced easily.
        """
        return self.machine_label
