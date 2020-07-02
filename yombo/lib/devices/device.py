"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_

The device class is the base class all devices should inherit from. This class inherits from Device_Base for
it's function processing and DeviceAttributes to setup the device attributes.

The attributes and functions in this class are intended to be overridden by subclasses, however, attributes from
the DeviceAttributes can also be overridden, but that is less common.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devices/device.html>`_
"""
# Import python libraries
from collections import deque
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks


# Yombo Constants
from yombo.constants import __version__ as YOMBOVERSION
from yombo.constants.commands import (COMMAND_TOGGLE, COMMAND_OPEN, COMMAND_ON, COMMAND_OFF, COMMAND_CLOSE,
                                      COMMAND_HIGH, COMMAND_LOW)
from yombo.constants.features import (FEATURE_ALL_OFF, FEATURE_ALL_ON, FEATURE_PINGABLE, FEATURE_POLLABLE,
                                      FEATURE_SEND_UPDATES, FEATURE_POWER_CONTROL, FEATURE_ALLOW_IN_SCENES,
                                      FEATURE_SCENE_CONTROLLABLE, FEATURE_ALLOW_DIRECT_CONTROL)
# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import instance_properties
from .device_attributes_mixin import DeviceAttributesMixin
from .device_command_mixin import DeviceCommandMixin
from .device_state_mixin import DeviceStateMixin

logger = get_logger("library.devices.device")


class Device(DeviceAttributesMixin, DeviceCommandMixin, DeviceStateMixin):
    """
    The parent to all child device types. This class has been broken up, see these additional mixins:

    * :ref:`Device attributes mixin <devices_device_attributes_mixin>` - Various attributes for a device.
    * :ref:`Device commands mixin <devices_device_command_mixin>` - Handles command processing.
    * :ref:`Device state mixin <devices_device_state_mixin>` - State information for a device.
    """
    _Entity_type: ClassVar[str] = "Device"
    _Entity_label_attribute: ClassVar[str] = "machine_label"
    _sync_to_api: ClassVar[bool] = True

    def __init__(self, parent, **kwargs) -> None:
        """
        :ivar callBeforeChange: *(list)* - A list of functions to call before this device has it's state
            changed. (Not implemented.)
        :ivar callAfterChange: *(list)* - A list of functions to call after this device has it's state
            changed. (Not implemented.)
        :ivar device_id: *(string)* - The id of the device.
        :type device_id: string
        :ivar device_type_id: *(string)* - The device type ID of the device.
        :ivar label: *(string)* - Device label as defined by the user.
        :ivar description: *(string)* - Device description as defined by the user.
        :ivar pin_required: *(bool)* - If a pin is required to access this device.
        :ivar pin_code: *(string)* - The device pin number.
            system to deliver commands and state update requests.
        :ivar created_at: *(int)* - When the device was created; in seconds since EPOCH.
        :ivar updated_at: *(int)* - When the device was last updated; in seconds since EPOCH.
        :ivar state_history: *(list)* - A list of state_history items, 0 being newest.
        :ivar available_commands: *(list)* - A list of command_id's that are valid for this device.
        """
        super().__init__(parent, **kwargs)
        self.system_disabled = False  # Set from devices/__init__ durring creation. If true, device cannot be used.
        self.system_disabled_reason = None

        self.PLATFORM_BASE: str = "device"
        self.PLATFORM: str = "device"
        self.SUB_PLATFORM: str = None
        # Features this device can support
        self.FEATURES: dict = {
            FEATURE_POWER_CONTROL: True,
            FEATURE_ALL_ON: False,
            FEATURE_ALL_OFF: False,
            FEATURE_PINGABLE: True,
            FEATURE_POLLABLE: True,
            FEATURE_SEND_UPDATES: True,
            FEATURE_ALLOW_IN_SCENES: True,
            FEATURE_SCENE_CONTROLLABLE: True,
            FEATURE_ALLOW_DIRECT_CONTROL: True,
        }
        self.MACHINE_STATE_EXTRA_FIELDS: dict = {}  # Track what fields in state extra are allowed.
        self.TOGGLE_COMMANDS = False  # Put two command machine_labels in a list to enable toggling.

        self.call_before_command: list = []
        self.call_after_command: list = []
        self._security_send_device_states: bool = self._Configs.get("security.amqp.send_device_states", True, instance=True)

        test_device = kwargs.get("test_device", None)
        if test_device is None:
            self.test_device = False
        else:
            self.test_device = test_device

        memory_sizing = {
            "x_small": {"other_device_commands": 5,  #less then 512mb
                        "other_state_history": 5,
                        "local_device_commands": 10,
                        "local_state_history": 10},
            "small": {"other_device_commands": 15,  #About 1024mb
                      "other_state_history": 15,
                      "local_device_commands": 40,
                      "local_state_history": 40},
            "medium": {"other_device_commands": 40,  # About 1536mb
                       "other_state_history": 40,
                       "local_device_commands": 80,
                       "local_state_history": 80},
            "large": {"other_device_commands": 75,  # About 2048mb
                      "other_state_history": 75,
                      "local_device_commands": 150,
                      "local_state_history": 150},
            "x_large": {"other_device_commands": 150,  # About 4096mb
                        "other_state_history": 150,
                        "local_device_commands": 300,
                        "local_state_history": 300},
            "xx_large": {"other_device_commands": 300,  # More than 4096mb
                         "other_state_history": 300,
                         "local_device_commands": 600,
                         "local_state_history": 600},
        }

        # misc other attributes
        self.device_is_new = True
        # self.device_serial = incoming["id"]
        self.device_mfg = "Yombo"
        self.device_model = "Yombo"
        self.device_serial = f"ybo-{YOMBOVERSION}"
        self.state_delayed = {}
        self.state_delayed_calllater = None
        self.device_parent = None  # Only set if this device is a child to anther device.
        self.auxiliary_device = None  # Set by modules for to map their device to yombo device.

        sizes = memory_sizing[self._Parent._Atoms["system.memory_sizing"]]
        if self.gateway_id != self._gateway_id:
            self.device_commands = deque([], sizes["other_device_commands"])
            self.state_history = deque([], sizes["other_state_history"])
        else:
            self.device_commands = deque([], sizes["local_device_commands"])
            self.state_history = deque([], sizes["local_state_history"])

        if self.test_device is False and self.device_is_new is True:
            self.device_is_new = False

    @inlineCallbacks
    def _system_init_(self) -> None:
        """
        Creates a default state to use when the device has not device states.

        :return:
        """
        self._default_state = yield self._DeviceStates.new(
            self,
            command=None,
            machine_state=0,
            human_state="Unknown",
            human_message="Unknown state for device",
            energy_usage=0,
            energy_type=self.energy_type,
            gateway_id=self.gateway_id,
            reporting_source="devices_attributes_system_init",
            device_command=None,
            created_at=time(),
            uploaded=0,
            uploadable=0,
            _fake_data=True,
            _load_source="system",
            _request_context="devices_attributes_system_init",
            _authentication=self._Parent.AUTH_USER,
        )

    def _init_(self, **kwargs) -> None:
        """
        Used by devices to run their init.

        :return:
        """
        pass

    def _load_(self, **kwargs) -> None:
        """
        This is called by the devices library when a new device is loaded for system use only.

        :param kwargs:
        :return:
        """
        pass

    def _start_(self, **kwargs) -> None:
        """
        This is called by the devices library when a new device is loaded and is used by devices that need
        to run any start up items.

        :param kwargs:
        :return:
        """
        pass

    def _unload_(self, **kwargs) -> None:
        """
        About to unload. Lets save all the device state items.

        :param kwargs:
        :return:
        """
        pass
        # for state in self.state_history:
        #     state.save_to_db()

    # def load_attribute_values_post_process(self, incoming: Dict[str, Any]) -> None:
    #     """
    #     Add "machine_label_class" that is basically the class
    #     :param incoming:
    #     :return:
    #     """

    def calc_percent(self, machine_state, machine_state_extra) -> Union[int, float]:
        """
        Like percent property, but accepts machine_state as input

        machine_state_extra is not used here, but might be used elsewhere.
        """
        if machine_state == 0:
            return 0
        elif machine_state <= 1:
            return round(machine_state*100)
        else:
            return 100

    def generate_human_state(self, machine_state, machine_state_extra):
        if machine_state == 1:
            return "On"
        return "Off"

    def generate_human_message(self, machine_state, machine_state_extra):
        human_state = self.generate_human_state(machine_state, machine_state_extra)
        return f"{self.area_label} is now {human_state}"

    def available_state_modes_values(self):
        return instance_properties(self, startswith_filter="STATE_MODES_")

    def available_state_extra_attributes(self):
        return instance_properties(self, startswith_filter="STATE_EXTRA_")

    def energy_calc(self, **kwargs):
        """
        Returns the energy being used based on a percentage the device is on.  Inspired by:
        http://stackoverflow.com/questions/1969240/mapping-a-range-of-values-to-another

        Supply the machine_state, machine_state_extra,and last command. If these are not supplied, it will
        be taken from teh device history.

        :param machine_state:
        :param map:
        :return:
        """
        # map = {
        #     0: 1,
        #     0.5: 100,
        #     1: 400,
        # }

        if "machine_state" in kwargs:
            machine_state = kwargs["machine_state"]
        else:
            machine_state = self.state_history[0]["machine_state"]

        if machine_state is None:
            machine_state = 0
        else:
            machine_state = float(machine_state)

        if "machine_state_extra" in kwargs:
            machine_state_extra = kwargs["machine_state_extra"]
        else:
            machine_state_extra = self.state_history[0]["machine_state_extra"]

        # print("energy_calc: machine_state: %s" % machine_state)
        # print("energy_calc: machine_state_extra: %s" % machine_state_extra)

        percent = self.calc_percent(machine_state, machine_state_extra) / 100
        # print("energy_calc: percent: %s" % percent)

        if self.energy_tracker_source_type != "calculated":
            return [0, self.energy_type]

        energy_map = self.energy_map
        if energy_map is None:
            return [0, self.energy_type]  # if no map is found, we always return 0

        items = list(energy_map.items())
        # print("energy_calc: percent: %s" % percent)
        # print("energy_calc: energy_map items(): %s" % items)
        for i in range(0, len(energy_map) - 1):
            if items[i][0] <= percent <= items[i + 1][0]:
                value = self.energy_translate(percent, items[i][0], items[i + 1][0], items[i][1],
                                              items[i + 1][1])
                return [value, self.energy_type]
        raise ValueError("Unable to determine energy usage.")

    def has_device_feature(self, feature_name: str, value=None) -> bool:
        """
        Tests if a provided feature is enabled.

        if feature is a list, returns True.

        If value is provided, and feature is a list, it will check if value is included within the feature.

        :param feature_name: Check if a feature_name is listed as an enabled feature.
        :param value: Value to check for if feature is a list.
        :return:
        """
        if feature_name not in self.FEATURES:
            return False
        value = self.FEATURES[feature_name]
        if isinstance(value, bool):
            return value
        if isinstance(value, dict) or isinstance(value, list):
            if value is not None:
                return value in self.FEATURES[feature_name]
            return True
        return False

    def get_state_extra(self, property_name: str) -> Any:
        """
        Lookup a state extra value by property.

        :param property_name: Name within the machine_state_extra to fetch.

        :return:
        """
        if len(self.state_history) > 0:
            state_current = self.state_history[0]
            if state_current.machine_state_extra is None or len(state_current.machine_state_extra) == 0:
                raise KeyError("Device has no machine state extra values.")
            if property_name in state_current.machine_state_extra:
                return state_current.machine_state_extra[property_name]
            raise KeyError("Property name not in machine state extra.")
        else:
            raise KeyError("Device has no state.")

    def available_commands(self) -> Dict[str, "yombo.lib.commands.Command"]:
        """
        Returns available commands for the current device.
        :return:
        """
        return self._Parent._DeviceTypes.device_type_commands(self.device_type_id)

    def in_available_commands(self, command: Union["yombo.lib.commands.Command", str]) -> bool:
        """
        Checks if a command label, machine_label, or command_id is a possible command for the given device.

        :param command:
        :return:
        """
        try:
            command = self._Parent._Commands.get(command)
        except KeyError:
            return False

        return command.comamnd_id in self.available_commands()

    def add_device_features(self, features: Union[dict, list, str]) -> None:
        """
        Adds additional features to a device.

        :param features: A string, list, or dictionary of additional features.
        :return:
        """
        if isinstance(features, list):
            for feature in features:
                self.FEATURES[feature] = True
        elif isinstance(features, dict):
            for feature, value in features:
                self.FEATURES[feature] = value
        elif isinstance(features, str):
            self.FEATURES[features] = True

    def remove_device_features(self, features: Union[dict, list, str]) -> None:
        """
        Removes features from a device. Accepts a list or a string for a single item.

        :param features: A list of features to remove from device.
        :return:
        """
        def remove_feature(feaure):
            if feature in self.FEATURES:
                del self.FEATURES[feature]

        if isinstance(features, list):
            for feature in features:
                remove_feature(feature)
        elif isinstance(features, dict):
            for feature, value in features:
                remove_feature(feature)
        elif isinstance(features, str):
            remove_feature(features)

    def add_machine_state_fields(self, fields: Union[dict, list, str]) -> None:
        """
        Adds machine state fields in bulks.

        :param fields: A string, list, or dictionary of additional fields.
        :return:
        """
        if isinstance(fields, list):
            for field in fields:
                self.MACHINE_STATE_EXTRA_FIELDS[field] = True
        elif isinstance(fields, dict):
            for field, value in fields:
                self.MACHINE_STATE_EXTRA_FIELDS[field] = value
        elif isinstance(fields, str):
            self.MACHINE_STATE_EXTRA_FIELDS[fields] = True

    def remove_machine_state_fields(self, features: Union[dict, list, str]) -> None:
        """
        Removes features from a device. Accepts a list or a string for a single item.

        :param features: A list of features to remove from device.
        :return:
        """
        def remove_field(field):
            if field in self.FEATURES:
                del self.FEATURES[feature]

        if isinstance(features, list):
            for feature in features:
                remove_field(feature)
        elif isinstance(features, dict):
            for feature, value in features:
                remove_field(feature)
        elif isinstance(features, str):
            remove_field(features)

    def command_from_state(self, machine_state, machine_state_extra=None):
        """
        Attempt to find a command based on the state of a device.
        :param machine_state:
        :param machine_state_extra:
        :return:
        """
        # print("attempting to get command_from_state - device: %s - %s" % (machine_state, machine_state_extra))
        if machine_state == int(1):
            for item in (COMMAND_ON, COMMAND_OPEN, COMMAND_HIGH):
                try:
                    command = self.in_available_commands(item)
                    return command
                except Exception:
                    pass
        elif machine_state == int(0):
            for item in (COMMAND_OFF, COMMAND_CLOSE, COMMAND_LOW):
                try:
                    command = self.in_available_commands(item)
                    return command
                except Exception:
                    pass
        return None

    def can_toggle(self):
        """
        If a device is toggleable, return True. It's toggleable if a device only has two commands.
        :return:
        """
        if self.TOGGLE_COMMANDS is False or self.TOGGLE_COMMANDS is None:
            return False
        if isinstance(self.TOGGLE_COMMANDS, list) is False:
            return False
        if len(self.TOGGLE_COMMANDS) == 2:
            return True
        return False

    def get_toggle_command(self):
        """
        If a device is toggleable, return True. It's toggleable if a device only has two commands.
        :return:
        """
        if self.can_toggle():
            if len(self.device_commands) > 0:
                device_command_id = self.device_commands[0]
                device_command = self._Parent.device_commands[device_command_id]
                command_id = device_command.command.command_id
                for toggle_command_id in self.TOGGLE_COMMANDS:
                    if toggle_command_id == command_id:
                        continue
                    return self._Parent._Commands[toggle_command_id]
            else:
                raise YomboWarning("Device cannot be toggled, device is in unknown state.")
        raise YomboWarning("Device cannot be toggled, it's not enabled for this device.")

    def toggle(self):
        if self.can_toggle() is False:
            return
        return self.command(COMMAND_TOGGLE)

    def turn_on(self, **kwargs):
        for item in (COMMAND_ON, COMMAND_OPEN):
            try:
                command = self.in_available_commands(item)
                return self.command(command, **kwargs)
            except Exception:
                pass
        raise YomboWarning("Unable to turn on device. Device doesn't have any of these commands: on, open")

    def turn_off(self, cmd, **kwargs):
        for item in (COMMAND_OFF, COMMAND_CLOSE):
            try:
                command = self.in_available_commands(item)
                return self.command(command, **kwargs)
            except Exception:
                pass
        raise YomboWarning("Unable to turn off device. Device doesn't have any of these commands: off, close")
