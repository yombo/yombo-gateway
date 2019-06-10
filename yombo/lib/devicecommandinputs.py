# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Device Command Inputs @ Library Documentation <https://yombo.net/docs/libraries/device_command_inputs>`_

Stores device command inputs in memory. Used by device types to determine what inputs are needed or accepted for
various commands.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/devicecommandinputs.html>`_
"""
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

logger = get_logger("library.device_command_inputs")


class DeviceCommandInput(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
    """
    A class to manage a single device command input.
    """
    _primary_column = "device_command_input_id"  # Used by mixins

    def __init__(self, parent, incoming, source=None):
        """
        Setup the device command input object using information passed in.

        :param incoming: An device command input with all required items to create the class.
        :type incoming: dict
        :return: None
        """
        self._Entity_type = "Device command input"
        self._Entity_label_attribute = "machine_label"
        super().__init__(parent)
        self._setup_class_model(incoming, source=source)


class DeviceCommandInputs(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Manages device type command inputs.
    """
    device_command_inputs = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "device_command_input"
    _class_storage_load_db_class = DeviceCommandInput
    _class_storage_attribute_name = "device_command_inputs"
    _class_storage_search_fields = [
        "device_command_input_id", "device_type_id", "machine_label", "label", "command_id", "input_type_id",
    ]
    _class_storage_sort_key = "machine_label"

    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Loads device command inputs from the database and imports them.
        """
        yield self._class_storage_load_from_database()

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
