# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Device Command Inputs @ Library Documentation <https://yombo.net/docs/libraries/device_command_inputs>`_

Stores device command inputs in memory. Used by device types to determine what inputs are needed or accepted for
various commands.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devicecommandinputs.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import DeviceCommandInputSchema
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

logger = get_logger("library.device_command_inputs")


class DeviceCommandInput(Entity, LibraryDBChildMixin):
    """
    A class to manage a single device command input.
    """
    _Entity_type: ClassVar[str] = "Device command input"
    _Entity_label_attribute: ClassVar[str] = "machine_label"


class DeviceCommandInputs(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages device type command inputs.
    """
    device_command_inputs: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "device_command_input_id"
    _storage_attribute_name: ClassVar[str] = "device_command_inputs"
    _storage_label_name: ClassVar[str] = "device_command_input"
    _storage_class_reference: ClassVar = DeviceCommandInput
    _storage_schema: ClassVar = DeviceCommandInputSchema()
    _storage_search_fields: ClassVar[List[str]] = [
        "device_command_input_id", "device_type_id", "machine_label", "label", "command_id", "input_type_id",
    ]
    _storage_attribute_sort_key: ClassVar[str] = "machine_label"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Loads device command inputs from the database and imports them.
        """
        yield self.load_from_database()

    def get_by_ids(self, device_type_id, command_id):
        """
        Returns a dictionary of device command inputs by searching through items looking for ones that match the
        device_type_id and command_id.

        :param device_type_id:
        :param command_id:
        :return:
        """
        results = {}
        for item_id, dci in self.device_command_inputs.items():
            if dci.device_type_id == device_type_id and dci.command_id == command_id:
                results[item_id] = dci
        return results
