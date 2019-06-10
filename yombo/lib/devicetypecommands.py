# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `device type commands @ Library Documentation <https://yombo.net/docs/libraries/device_type_commands>`_

Device type commands provides a mapping between what commands each device type can perform.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/devicetypecommands.html>`_
"""
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.sync_to_everywhere_mixin import SyncToEverywhereMixin
from yombo.mixins.library_db_model_mixin import LibraryDBModelMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

logger = get_logger("library.device_type_commands")


class DeviceCommandInput(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
    """
    A class to manage a single device type command.
    """
    _primary_column = "device_type_command_id"  # Used by mixins

    def __init__(self, parent, incoming, source=None):
        """
        Setup the device type command object using information passed in.

        :param incoming: An device type command with all required items to create the class.
        :type incoming: dict
        """
        self._Entity_type = "Device type command"
        self._Entity_label_attribute = "device_type_command_id"
        super().__init__(parent)
        self._setup_class_model(incoming, source=source)


class DeviceTypeCommands(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Manages device type commands.
    """
    device_type_commands = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "device_type_command"
    _class_storage_load_db_class = DeviceCommandInput
    _class_storage_attribute_name = "device_type_commands"
    _class_storage_search_fields = [
        "device_type_command_id", "device_type_id", "command_id"
    ]
    _class_storage_sort_key = "device_type_id"

    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Loads device type commands from the database and imports them.
        """
        yield self._class_storage_load_from_database()

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
                    if command.command_id not in results:
                        results[command.command_id] = []
                    results[command.command_id].append(command)
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
