# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `module device types @ Library Documentation <https://yombo.net/docs/libraries/module_device_types>`_

Maps what modules have what device types. Used by the module library primarily.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/moduledevicetypes.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import ModuleDeviceTypeSchema
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

logger = get_logger("library.module_device_types")


class ModuleDeviceType(Entity, LibraryDBChildMixin):
    """
    A class to manage a single module device type.
    """
    _Entity_type: ClassVar[str] = "Module device type"
    _Entity_label_attribute: ClassVar[str] = "module_device_type_id"


class ModuleDeviceTypes(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages module device types.
    """
    module_device_types: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "module_device_type_id"
    _storage_label_name: ClassVar[str] = "module_device_type"
    _storage_class_reference: ClassVar = ModuleDeviceType
    _storage_schema: ClassVar = ModuleDeviceTypeSchema()
    _storage_attribute_name: ClassVar[str] = "module_device_types"
    _storage_search_fields: ClassVar[List[str]] = [
        "module_device_type_id", "module_id", "device_type_id"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "machine_label"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        yield self.load_from_database()

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
