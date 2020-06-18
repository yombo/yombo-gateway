# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `device type commands @ Library Documentation <https://yombo.net/docs/libraries/device_type_commands>`_

Device type commands provides a mapping between what commands each device type can perform.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devicetypecommands.html>`_
"""
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import DeviceTypeCommandSchema
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

logger = get_logger("library.device_type_commands")


class DeviceTypeCommand(Entity, LibraryDBChildMixin):
    """
    A class to manage a single device type command.
    """
    _Entity_type: ClassVar[str] = "Device type command"
    _Entity_label_attribute: ClassVar[str] = "device_type_command_id"


class DeviceTypeCommands(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages device type commands.
    """
    device_type_commands: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "device_type_command_id"
    _storage_label_name: ClassVar[str] = "device_type_command"
    _storage_class_reference: ClassVar = DeviceTypeCommand
    _storage_schema: ClassVar = DeviceTypeCommandSchema()
    _storage_attribute_name: ClassVar[str] = "device_type_commands"
    _storage_search_fields: ClassVar[List[str]] = [
        "device_type_command_id", "device_type_id", "command_id"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "device_type_id"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Loads device type commands from the database and imports them.
        """
        yield self.load_from_database()

    def get_commands(self, device_type_id):
        """
        Returns a dictionary of commands the specified device type can send.

        :param device_type_id:
        :return:
        """
        results = {}
        for item_id, dtc in self.device_type_commands.items():
            if dtc.device_type_id == device_type_id:
                try:
                    command = self._Commands.get(dtc.command_id)
                    results[command.command_id] = command
                except:
                    logger.warn("Error getting command '{command_id}' for a device type.",
                                command_id=dtc.command_id)
                    pass
        return results

    def get_by_command_id(self, command_id):
        """
        Returns a dictionary of device types a specified command id belongs to.

        :param command_id:
        :return:
        """
        results = {}
        for item_id, dtc in self.device_type_commands.items():
            if dtc.command_id == command_id:
                try:
                    device_type = self._DeviceTypes.get(dtc.device_type_id)
                    if device_type.device_type_id not in results:
                        results[device_type.device_type_id] = []
                    results[device_type.device_type_id].append(device_type)
                except:
                    logger.warn("Error getting command '{command_id}' for a device type.",
                                command_id=dtc.command_id)
                    pass

        for item_id, dtc in self.device_type_commands.items():
            if dtc.command_id == command_id:
                results[item_id] = dtc
        return results
