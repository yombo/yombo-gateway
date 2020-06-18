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

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devicetypes/__init__.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import DeviceTypeSchema
from yombo.lib.devicetypes.device_type import DeviceType
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

logger = get_logger("library.devicetypes")


class DeviceTypes(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages device type database tabels. Just simple update a module"s device types or device type"s available commands
    and any required database tables are updated. Also maintains a list of module device types and device type commands
    in memory for access.
    """
    device_types = {}
    platforms = {}  # Device type platforms - the bare classes used to create device_type instances.

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "device_type_id"
    _storage_attribute_name: ClassVar[str] = "device_types"
    _storage_label_name: ClassVar[str] = "device_type"
    _storage_class_reference: ClassVar = DeviceType
    _storage_schema: ClassVar = DeviceTypeSchema()
    _storage_search_fields: ClassVar[List[str]] = [
        "device_type_id", "machine_label", "label", "category_id", "description"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "machine_label"
    _storage_primary_field_name_extra: ClassVar[list] = ["is_usable"]

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Sets up basic attributes.
        """
        # load base device type.
        classes = yield self._Files.extract_classes_from_files("yombo/lib/devices/device.py")
        self.platforms.update(classes)

        # load system device types
        files = yield self._Files.search_path_for_files("yombo/lib/devicetypes/platforms/*.py")
        logger.debug("device types - files, system: {files}", files=files)
        classes = yield self._Files.extract_classes_from_files(files)
        logger.debug("device types - classes, device types - files: {classes}", classes=classes)
        self.platforms.update(classes)

        # load module device types
        files = yield self._Modules.search_modules_for_files("devicetypes/*.py")
        logger.debug("device types - files, modules: {files}", files=files)
        classes = yield self._Files.extract_classes_from_files(files)
        logger.debug("device types - classes, modules: {classes}", classes=classes)
        self.platforms.update(classes)
        self.platforms = dict((k.lower(), v) for k, v in self.platforms.items())

        logger.debug("device type platforms: {platforms}", platforms=self.platforms)
        yield self.load_from_database()  # have to load after we have all device type platforms.
        logger.debug("device types: {device_types}", device_types=self.device_types)

    def load_an_item_to_memory_pre_check(self, incoming, load_source):
        """ Checks if the given input item should be loaded into memory. """
        platform = incoming["machine_label"].replace("_", "")
        incoming["is_usable"] = True
        if platform not in self.platforms:
            incoming["is_usable"] = False
            logger.warn("Trouble loading device type, platform '{platform}' isn't found."
                        " Will return generic device type.", platform=platform)

    def get_platform(self, item_requested):
        """
        Get a device type class reference. Non-alphanumeric characters are removed and then converted to lowercase.

        :param item_requested: Platform name to retrieve.
        :return:
        """
        item_requested_filtered = "".join(filter(str.isalnum, item_requested)).lower()

        if item_requested_filtered in self.platforms:
            return self.platforms[item_requested_filtered]
        logger.warn("Device type platform missing '{platform}', returing generic device.",
                    item_requested_filtered=item_requested_filtered)
        return self.platforms["device"]

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

        input_type_id = self.device_types[device_type_id].commands[command_id]["inputs"][dtc_machine_label][
            "input_type_id"]
        return self._InputTypes[input_type_id].validate(value)
