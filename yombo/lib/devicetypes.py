# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For developer documentation, see: `Device Type @ Module Development <https://yombo.net/docs/libraries/device_types>`_

This is a simple helper library to manage device type mapping. This is a mapping between modules, device types,
and commands.

This library keeps track of what modules can access what device types, and what commands those device types can perform.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2016-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/devicetypes.html>`_
"""
from collections import Callable
from functools import reduce
import os
from pyclbr import readmodule

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.sync_to_everywhere_mixin import SyncToEverywhereMixin
from yombo.mixins.library_db_model_mixin import LibraryDBModelMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.utils import do_search_instance

logger = get_logger("library.devicetypes")


class DeviceType(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
    """
    A class to manage a single device type.
    :ivar label: Device type label
    :ivar description: The description of the device type.
    :ivar inputTypeID: The type of input that is required as a variable.
    """
    _primary_column = "device_type_id"  # Used by mixins

    def __init__(self, parent, incoming, source=None):
        """
        A device type object used to lookup more information. Any changes to this record will be updated
        into the database.

        :cvar device_type_id: (string) The id of the device type.

        :param incoming: A device type as passed in from the device types class. This is a
            dictionary with various device type attributes.
        """
        self._Entity_type = "Device type"
        self._Entity_label_attribute = "machine_label"

        super().__init__(parent)
        self._setup_class_model(incoming, source=source)

    @property
    def commands(self):
        """
        Gets available commands for the device type.
        Loads available commands from the database. This should only be called when a device type is loaded,
        notification that device type has been updated, or when device type commands have changed.
        :return:
        """
        return self._Parent._DeviceTypeCommands.get_commands(self.device_type_id)
        # logger.debug("Device type received command ids: {commands}", commands=commands)
        # for command_id, command in commands.items():
        #     try:
        #         self.commands[command_id] = {
        #             "command": self._Parent._Commands[command_id],
        #             "inputs": {}
        #         }
        #     except KeyError:
        #         logger.warn("Device type '{label}' is unable to find command: {command_id}",
        #                     label=self.label, command_id=command_id)
        #         continue
        #     inputs = self._Parent._DeviceCommandInputs.get_by_ids(self.device_type_id, command_id)
        #     for dci_id, dci in inputs.items():
        #         self.commands[command_id]["inputs"][dci.machine_label] = dci

    def update_attributes_preprocess(self, incoming):
        """
        Modify the incoming values before its saved.

        :param device_type:
        :return:
        """
        if "platform" in incoming:
            if incoming["platform"] is None or incoming["platform"] == "":
                incoming["platform"] = "all"

    @property
    def variable_fields(self):
        """
        Get variable fields for the current device type.

        :return: Dictionary of dicts containing variable fields.
        """
        return self._VariableGroups.fields(
            group_relation_type="device",
            group_relation_id=self.device_type_id
        )

    def get_devices(self, gateway_id=None):
        """
        Return a dictionary of devices for a given device_type. Can be restricted to a specific gateway_id
        if it's provided.

        :return:
        """
        # if gateway_id is None:
        #     gateway_id = self.gateway_id

        search_attributes = [
            {
                "field": "device_type_id",
                "value": self.device_type_id,
                "limiter": 1,
            }
        ]

        try:
            results = do_search_instance(search_attributes,
                                         self._Parent._Devices.devices,
                                         self._Parent._class_storage_search_fields)

            if results["was_found"]:
                devices = {}
                for device_id, device in results['values'].items():
                    if gateway_id is not None:
                        if device.gateway_id != gateway_id:
                            continue
                    devices[device_id] = device
                return devices
            else:
                return {}
        except YomboWarning as e:
            raise KeyError(f"Get devices had problems: {e}")

    def get_modules(self, return_value="id"):
        """
        Return a list of modules for a given device_type
        :return:
        """
        if return_value == "id":
            return list(self.registered_modules.keys())
        elif return_value == "label":
            return list(self.registered_modules.values())
        else:
            raise YomboWarning("get_modules requires either 'id' or 'label'")


class DeviceTypes(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Manages device type database tabels. Just simple update a module"s device types or device type"s available commands
    and any required database tables are updated. Also maintains a list of module device types and device type commands
    in memory for access.
    """
    device_types = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "device_type"
    _class_storage_load_db_class = DeviceType
    _class_storage_attribute_name = "device_types"
    _class_storage_search_fields = [
        "device_type_id", "machine_label", "label", "category_id", "description", "platform"
    ]
    _class_storage_sort_key = "machine_label"

    def _init_(self, **kwargs):
        """
        Sets up basic attributes.
        """
        self.platforms = {}  # This is filled in lib.modules::do_import_modules

    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Loads device types from the database and imports them.
        
        :return: 
        """
        # Search the devices directory for devicetypes (I know, wrong location) and
        # generate a list of all default device types.
        device_type_platforms = {"yombo.lib.devices._device": ["Device"]}
        working_dir = self._Atoms.get("app_dir")
        files = os.listdir(f"{working_dir}/yombo/lib/devices")
        for file in files:
            if file.startswith("_") or file.endswith(".py") is False:
                continue
            file_parts = file.split(".", 2)
            filename = file_parts[0]

            try:
                file_path = f"yombo.lib.devices.{filename}"
                possible_file = __import__(file_path, globals(), locals(), [], 0)
                module_tail = reduce(lambda p1, p2: getattr(p1, p2),
                                     [possible_file, ] + file_path.split(".")[1:])
                classes = readmodule(file_path)
                for name, file_class_name in classes.items():
                    if file_path not in device_type_platforms:
                        device_type_platforms[file_path] = []
                    device_type_platforms[file_path].append(name)
            except Exception as e:
                logger.debug("D: Unable to import magic file {file_path}, reason: {e}", file_path=file_path, e=e)
                pass

        yield self._class_storage_load_from_database()
        self.load_platforms(device_type_platforms)

    def load_platforms(self, platforms):
        """
        Device type platforms, like light, fan, switch, etc. These can be included in modules, system device
        type platforms are located in the lib/devices.

        :param platforms: 
        :return: 
        """
        for path, items in platforms.items():
            for item in items:
                item_key = item.lower()
                if item_key.startswith("_"):
                    item_key = item_key

                module_root = __import__(path, globals(), locals(), [], 0)
                module_tail = reduce(lambda p1, p2: getattr(p1, p2), [module_root, ] + path.split(".")[1:])
                klass = getattr(module_tail, item)
                if not isinstance(klass, Callable):
                    logger.warn("Unable to load device platform '{name}', it's not callable.", name=item)
                    continue
                self.platforms[item_key] = klass

    @inlineCallbacks
    def addable_device_types(self):
        """
        Get a list of addable device types.

        :return:
        """
        device_types = yield self._LocalDB.get_addable_device_types()
        return device_types

    def devices_by_device_type(self, requested_device_type, gateway_id=None):
        """
        A list of devices for a given device type.

        :raises YomboWarning: Raised when module_id is not found.
        :param requested_device_type: A device type by either ID or Label.
        :return: A dictionary of devices for a given device type.
        :rtype: list
        """
        device_type = self.get(requested_device_type)
        return device_type.get_devices(gateway_id=gateway_id)

    def device_type_commands(self, device_type_id):
        """
        A list of commands for a given device type.

        :raises YomboWarning: Raised when device_type_id is not found.
        :param device_type_id: The Device Type ID to return device types for.
        :return: A list of command id's.
        :rtype: list
        """
        if device_type_id in self.device_types:
            return self.device_types[device_type_id].commands
        else:
            raise YomboWarning(f"Device type id doesn't exist: {device_type_id}", 200,
                "device_type_commands", "DeviceTypes")

    def get_local_devicetypes(self):
        """
        Return a dictionary with all the public device types.

        :return:
        """
        results = {}
        for item_id, item in self.device_types.items():
            if item.public <= 1:
                results[item_id] = item
        return results

    def get_public_devicetypes(self):
        """
        Return a dictionary with all the public device types.

        :return:
        """
        results = {}
        for item_id, item in self.device_types.items():
            if item.public == 2:
                results[item_id] = item
        return results

    def validate_command_input(self, device_type_id, command_id, dtc_machine_label, value):
        """
        Validates an input value.
        :param device_type_id:
        :param command_id:
        :param dtc_machine_label: 
        :return:
        """
        if device_type_id not in self.device_types:
            raise KeyError("Device Type Id not found.")
        if command_id not in self.device_types[device_type_id].commands:
            raise KeyError("Command ID not found in specified device type id.")
        if dtc_machine_label not in self.device_types[device_type_id].commands[command_id]["inputs"]:
            raise KeyError("machine label not found in specified command_id for the provided device type id.")

        input_type_id = self.device_types[device_type_id].commands[command_id]["inputs"][dtc_machine_label]["input_type_id"]
        return self._InputTypes[input_type_id].validate(value)
