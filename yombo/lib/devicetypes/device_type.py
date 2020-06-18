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
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devicetypes/devicetype.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Type, Union


# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.utils import do_search_instance

logger = get_logger("library.devicetypes")


class DeviceType(Entity, LibraryDBChildMixin):
    """
    A class to manage a single device type.
    :ivar label: Device type label
    :ivar description: The description of the device type.
    :ivar inputTypeID: The type of input that is required as a variable.
    """
    _Entity_type: ClassVar[str] = "Device type"
    _Entity_label_attribute: ClassVar[str] = "machine_label"

    @property
    def commands(self):
        """
        Gets available commands for the device type.
        Loads available commands from the database. This should only be called when a device type is loaded,
        notification that device type has been updated, or when device type commands have changed.
        :return:
        """
        return self._Parent._DeviceTypeCommands.get_commands(self.device_type_id)

    def update_attributes_pre_process(self, incoming):
        """
        Modify the incoming values before its saved.

        :param incoming:
        :return:
        """
        if "platform" in incoming:
            if incoming["platform"] is None or incoming["platform"] == "":
                incoming["platform"] = "device"

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

    def to_dict_postprocess(self, data, to_database: Optional[bool] = None, **kwargs):
        """
        Add 'is_usable' attribute if not sending to the database.

        :param to_database:
        :return:
        """
        if to_database in (True, None):
            return
        data["is_usable"] = self.is_usable

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
                                         self._Parent._storage_search_fields)

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
