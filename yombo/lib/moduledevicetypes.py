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

logger = get_logger("library.module_device_types")


class ModuleDeviceType(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
    """
    A class to manage a single module device type.
    """
    _primary_column = "module_device_type_id"  # Used by mixins

    def __init__(self, parent, incoming, source=None):
        """
        Setup the module device type object using information passed in.

        :param module_device_type: An module device type with all required items to create the class.
        :type module_device_type: dict
        """
        self._Entity_type = "Module device type"
        self._Entity_label_attribute = "module_device_type_id"

        super().__init__(parent)
        self._setup_class_model(incoming, source=source)


class ModuleDeviceTypes(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Manages module device types.
    """
    module_device_types = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "module_device_type"
    _class_storage_load_db_class = ModuleDeviceType
    _class_storage_attribute_name = "module_device_types"
    _class_storage_search_fields = [
        "module_device_type_id", "module_id", "device_type_id"
    ]
    _class_storage_sort_key = "machine_label"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        yield self._class_storage_load_from_database()

    def get_by_module_id(self, module_id):
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
                except:
                    raise KeyError(f"Error getting device type '{mdt.device_type_id}' for a module device type.")
                if device_type.device_type_id not in results:
                    results[device_type.device_type_id] = []
                results[device_type.device_type_id].append(device_type)
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
                except:
                    logger.warn("Error getting module '{module_id}' for a module device type.",
                                module_id=mdt.module_id)
                    pass
                if module.module_id not in results:
                    results[module.module_id] = []
                results[module.module_id].append(module)
        return results
