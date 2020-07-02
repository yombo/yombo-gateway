# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_

All possible device attributes and tools to manage those attributes.

This class in inherited by _device.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devices/device_attributes_mixin.html>`_
"""
# Import python libraries
from __future__ import annotations
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Yombo Constants
from yombo.constants.features import (FEATURE_ALL_OFF, FEATURE_ALL_ON, FEATURE_PINGABLE, FEATURE_POLLABLE,
                                      FEATURE_SEND_UPDATES, FEATURE_POWER_CONTROL, FEATURE_ALLOW_IN_SCENES,
                                      FEATURE_SCENE_CONTROLLABLE, FEATURE_ALLOW_DIRECT_CONTROL)

# Import Yombo libraries
from yombo.core.library_child import YomboLibraryChild
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.utils import is_true_false

logger = get_logger("library.devices.device_attributes_mixin")


class DeviceAttributesMixin(YomboLibraryChild, LibraryDBChildMixin):
    """
    This base class is the main bootstrap and is responsible for settings up all core attributes.

    The primary functions developers should use are:
        * :py:meth:`available_commands <Device.available_commands>` - List available commands for a device.
        * :py:meth:`command <Device.command>` - Send a command to a device.
        * :py:meth:`device_command_received <Device.device_command_received>` - Called by any module processing a command.
        * :py:meth:`device_command_pending <Device.device_command_pending>` - When a module needs more time.
        * :py:meth:`device_command_failed <Device.device_command_failed>` - When a module is unable to process a command.
        * :py:meth:`device_command_done <Device.device_command_done>` - When a command has completed..
        * :py:meth:`energy_get_usage <Device.energy_get_usage>` - Get current energy being used by a device.
        * :py:meth:`get_state <Device.get_state>` - Get a latest device state object.
        * :py:meth:`set_state <Device.set_state>` - Set the device state.
    """
    def __str__(self) -> str:
        """
        Print a string when printing the class.  This will return the device_id so that
        the device can be identified and referenced easily.
        """
        return f"Device: {self.device_id}:{self.label}"

    def __getitem__(self, key):
        return self.__dict__[key]

    def __repr__(self) -> str:
        # return "some random device....repr"
        return f"<Device {self.device_id}:{self.machine_label}>"

    def __len__(self) -> int:
        return len(self.__dict__)

    def has_key(self, k) -> bool:
        return k in self.__dict__

    def keys(self):
        return list(self.__dict__.keys())

    def values(self):
        return list(self.__dict__.values())

    def items(self):
        return list(self.__dict__.items())

    def __contains__(self, item):
        return item in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)

    @property
    def area(self) -> str:
        """
        Returns the label for the device's area_id.

        :return:
        """
        locations = self._Parent._Locations.locations
        try:
            area = locations[self.area_id].label
            if area.lower() == "none":
                return ""
            else:
                return area
        except Exception:
            return ""

    @property
    def location(self) -> str:
        """
        Returns the label for the device location_id.

        :return:
        """
        locations = self._Parent._Locations.locations
        try:
            location = locations[self.location_id].label
            if location.lower() == "none":
                return ""
            else:
                return location
        except Exception:
            return ""

    @property
    def area_label_lower(self) -> str:
        """
        Used for searching, or when lower case is desired. Simply applies lower() to area_label
        :return:
        """
        return self.area_label.lower()

    @property
    def area_label(self) -> str:
        """
        Returns the device's area label + device label.
        :return:
        """
        locations = self._Parent._Locations.locations
        try:
            area = locations[self.area_id].label
            if area.lower() == "none":
                area = ""
            else:
                area = area + " "
        except Exception:
            area = ""
        return f"{area}{self.label}"

    @property
    def full_label_lower(self) -> str:
        """
        Used for searching, or when lower case is desired. Simply applies lower() to full_label
        :return:
        """
        return self.full_label.lower()

    @property
    def full_label(self) -> str:
        """
        Returns the device's location + area + device label.
        :return:
        """
        locations = self._Parent._Locations.locations
        try:
            location = locations[self.location_id].label
            if location.lower() == "none":
                location = ""
            else:
                location = location + " "
        except Exception as e:
            location = ""

        try:
            area = locations[self.area_id].label
            if area.lower() == "none":
                area = ""
            else:
                area = area + " "
        except Exception as e:
            area = ""
        return "%s%s%s" % (location, area, self.label)

    @property
    def statistic_label_slug(self) -> str:
        """
        Get statistics label. Use the user defined version or create one if doesn't exist.

        :return:
        """
        if self.statistic_label in (None, "", "None", "none"):
            locations = self._Parent._Locations.locations
            new_label = ""
            if self.location_id in locations:
                location = locations[self.location_id].label
                if location.lower() != "none":
                    new_label = self._Validate.slugify(location)

            if self.area_id in locations:
                area = locations[self.area_id].label
                if area.lower() != "none":
                    if len(new_label) > 0:
                        new_label = new_label + "." + self._Validate.slugify(location)
                    else:
                        new_label = self._Validate.slugify(location)
            if len(new_label) > 0:
                new_label = new_label + "." + self._Validate.slugify(self.machine_label)
            else:
                new_label = self._Validate.slugify(self.machine_label)
            return new_label
        else:
            return self.statistic_label

    @property
    def state(self) -> Union[int, float]:
        """
        Return the machine state of the device.
        """
        return self.state_all.machine_state

    @property
    def machine_state(self) -> Union[int, float]:
        """
        Get the current machine state for a device. This is an alias for 'state' property.

        :return:
        """
        return self.state_all.machine_state

    @property
    def machine_state_extra(self) -> Dict[str, Any]:
        """
        Get the current machine state extra details for a device.

        :return:
        """
        return self.state_all.machine_state_extra

    @property
    def human_state(self) -> str:
        """
        Get the current human state.

        :return:
        """
        return self.state_all.human_state

    @property
    def human_message(self) -> str:
        """
        Get the current human message..

        :return:
        """
        return self.state_all.human_message

    @property
    def state_all(self) -> "yombo.lib.devicestates._device_state.DeviceState":
        """
        Return the device's current state. Will return fake state of
        there is no current state which basically says the state is unknown.
        """
        if len(self.state_history) == 0:
            return self._default_state
        return self.state_history[0]

    @property
    def features(self) -> list:
        """
        Return a list of features this device supports.
        """
        features = {}
        for feature, value in self.FEATURES.items():
            if value is not False:
                features[feature] = value
        return features

    def has_feature(self, feature) -> bool:
        if feature.lower() in self.FEATURES:
            return self.FEATURES[feature]
        else:
            return False

    @property
    def is_direct_controllable(self) -> bool:
        """
        Return true if this device can be directly controlled. This is usually True, except for instances
        like relays that control garage doors, etc.
        :return:
        """
        if self.has_device_feature(FEATURE_ALLOW_DIRECT_CONTROL) and \
                is_true_false(self.allow_direct_control):
            return True
        return False

    @property
    def is_scene_controllable(self) -> bool:
        """
        Returns True if the device can be controlled. This will be False for input type devices, like motion sensors.
        :return:
        """
        if self.has_device_feature(FEATURE_SCENE_CONTROLLABLE) and \
                    is_true_false(self.scene_controllable):
            return True
        return False

    @property
    def is_allowed_in_scenes(self) -> bool:
        """
        True if device is allowed to be used in scenes or automation rules.

        :return:
        """
        if self.has_device_feature(FEATURE_ALLOW_IN_SCENES) and self.is_scene_controllable:
            return True
        return False

    @property
    def percent(self) -> Union[int, float]:
        """
        This should be overridden by the device types themselves. This is simply a fallback.

        If the machine_state is 0, returns. Otherwise returns 100.
        """
        if len(self.state_history) > 0:
            machine_state = self.state_history[0].machine_state
            return self.calc_percent(machine_state, self.machine_state_extra)
        return 0

    @property
    def device_variables(self) -> Dict[str, dict]:
        return self._VariableData.data("device", self.device_id)

    @property
    def device_variable_fields(self) -> Dict[str, Any]:
        return self._VariableGroups.fields("device_type", self.device_type_id)

    @property
    def is_on(self):
        if isinstance(self.machine_state, int) is False:
            return False
        if int(self.machine_state) > 0:
            return True
        else:
            return False

    @property
    def is_off(self):
        if hasattr(self, "is_on") and callable(self.is_on):
            return not self.is_on()
        if isinstance(self.machine_state, int) is False:
            return False
        return not self.is_on()

    @property
    def debug_data(self):
        return {}

    @property
    def current_mode(self):
        """
        Return the current mode of operation for the device.
        """
        machine_state_extra = self.machine_state_extra
        if "mode" in machine_state_extra.machine_state_extra:
            return machine_state_extra.machine_state_extra["mode"]
        return None

    @property
    def unit_of_measurement(self):
        """
        Return the unit of measurement of this device, if any.
        """
        return None

    def to_dict_postprocess(self, incoming_data, meta, to_external: Optional[bool] = None, to_database: Optional[bool] = None,
                            **kwargs) -> None:
        """
        Updates to_dict results to include additional module items.
        """
        # print(f"(1) to_dict_postprocess 1, to_database: {to_database}")
        if to_database is False:
            if len(self.state_history) > 0:
                state_current = self.state_history[0].to_dict()
            else:
                state_current = None

            if len(self.state_history) > 1:
                state_previous = self.state_history[1].to_dict()
            else:
                state_previous = None

            def clean_device_variables(device_variables):
                results = {}
                if self.system_disabled is True:
                    return results
                for label, variable_data in device_variables.items():
                    print(f'data["ref"]: {variable_data["ref"]}')
                    results[label] = []
                    for variable in variable_data["ref"]:
                        print(f'data["ref"] data: {variable.__dict__}')
                        results[label].append({
                            "variable_data_id": variable.variable_data_id,
                            "data": variable.data,
                            "decrypted": variable.decrypted,
                            "display": variable.display,
                            "updated_at": variable.updated_at,
                        })
                    # del data["data"]
                    # data["values"] = data["values_orig"]
                    # del data["values_orig"]
                return results

            incoming_data.update({
                # "area_id": self.area_id,
                # "location_id": self.location_id,
                "full_label": self.full_label,
                "area_label": self.area_label,
                "area": self.area,
                "location": self.location,
                "device_type_label": self._DeviceTypes[self.device_type_id].machine_label,
                # "device_commands": list(self.device_commands),
                # "state_current": state_current,
                # "state_previous": state_previous,
                # "controllable": self.controllable,
                "device_features": self.FEATURES,
                "device_mfg": self.device_mfg,
                "device_model": self.device_model,
                "device_platform": self.PLATFORM,
                "device_serial": self.device_serial,
                "device_sub_platform": self.SUB_PLATFORM,
                # "device_variables": clean_device_variables(self.device_variables),
                "system_disabled": self.system_disabled,
                "system_disabled_reason": self.system_disabled_reason,
                "is_direct_controllable": self.is_direct_controllable,
                "is_allowed_in_scenes": self.is_allowed_in_scenes,

                # "energy_tracker_source_id": self.energy_tracker_source_id,
                # "energy_tracker_source_type": self.energy_tracker_source_type,
                # "energy_type": self.energy_type,
                # "energy_map": self.energy_map,
                # "status": self.status,
                }
            )
            # print(f"(1) to_dict_postprocess z: {incoming_data}")
            incoming_data["pin_code"] = "********"

    def load_attribute_values_pre_process(self, incoming: Dict[str, Any]) -> None:
        """ Setup basic class attributes based on incoming data. """
        self.update_attributes_pre_process(incoming)

    def update_attributes_pre_process(self, incoming: Dict[str, Any]) -> None:
        """
        Change some basic values before the input is processed.

        :param incoming:
        :return:
        """
        if "pin_timeout" in incoming:
            try:
                incoming["pin_timeout"] = int(incoming["pin_timeout"])
            except:
                incoming["pin_timeout"] = 0

        if "energy_map" in incoming:
            if incoming["energy_map"] is not None:
                # create an energy map from a dictionary
                energy_map_final = {0.0: 0, 1.0: 0}
                if isinstance(incoming["energy_map"], dict) is False:
                    incoming["energy_map"] = energy_map_final

                for percent, rate in incoming["energy_map"].items():
                    energy_map_final[self._InputTypes.check("percent", percent)] = self._Parent._InputTypes.check("float", rate)
                energy_map_final = dict(sorted(list(energy_map_final.items()), key=lambda x_y: float(x_y[0])))
                incoming["energy_map"] = energy_map_final
            else:
                incoming["energy_map"] = {0.0: 0, 1.0: 0}

