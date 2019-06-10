# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_

All possible device attributes and tools to manage those attributes.

This class in inherited by _device.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from collections import deque, OrderedDict
from copy import deepcopy
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred, Deferred

# Yombo Constants
from yombo.constants.features import (FEATURE_ALL_OFF, FEATURE_ALL_ON, FEATURE_PINGABLE, FEATURE_POLLABLE,
                                      FEATURE_SEND_UPDATES, FEATURE_POWER_CONTROL, FEATURE_ALLOW_IN_SCENES,
                                      FEATURE_CONTROLLABLE, FEATURE_ALLOW_DIRECT_CONTROL)

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.sync_to_everywhere_mixin import SyncToEverywhereMixin
from yombo.utils import is_true_false
from yombo.utils.hookinvoke import global_invoke_all

from ._device_state import Device_State
logger = get_logger("library.devices.device_attributes")


class Device_Attributes(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
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
    def statistic_label_slug(self):
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
    def state(self):
        """
        Return the machine state of the device.
        """
        return self.state_all.machine_state

    @property
    def machine_state(self):
        """
        Get the current machine state for a device. This is an alias for 'state' property.

        :return:
        """
        return self.state_all.machine_state

    @property
    def human_state(self):
        """
        Get the current human state.

        :return:
        """
        return self.state_all.human_state

    @property
    def human_message(self):
        """
        Get the current human message..

        :return:
        """
        return self.state_all.human_message

    @property
    def machine_state_extra(self):
        """
        Get the current machine state extra details for a device.

        :return:
        """
        return self.state_all.machine_state_extra

    @property
    def state_all(self):
        """
        Return the device's current state. Will return fake state of
        there is no current state which basically says the state is unknown.
        """
        if len(self.state_history) == 0:
            return Device_State(self._Parent, self, {
                "command": None,
                "set_at": time(),
                "energy_usage": 0,
                "energy_type": self.energy_type,
                "human_state": "Unknown",
                "human_message": "Unknown state for device",
                "machine_state": None,
                "machine_state_extra": {},
                "gateway_id": self.gateway_id,
                "auth_id": "unknown",
                "reporting_source": "unknown",
                "request_id": None,
                "uploaded": 0,
                "uploadable": 1,
                "_fake_data": True,
            })
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

    def has_feature(self, feature):
        if feature.lower() in self.FEATURES:
            return self.FEATURES[feature]
        else:
            return False

    @property
    def device_type(self):
        """
        Returns the device type object for the device.
        :return:
        """
        return self._Parent._DeviceTypes[self.device_type_id]

    @property
    def is_direct_controllable(self):
        """
        Return true if this device can be directly controlled. This is usally True, except for instances
        like relays that control garage doors, etc.
        :return:
        """
        if self.has_device_feature(FEATURE_CONTROLLABLE) and \
                    self.has_device_feature(FEATURE_ALLOW_DIRECT_CONTROL) and \
                    is_true_false(self.allow_direct_control) and \
                    is_true_false(self.controllable):
            return True
        return False

    @property
    def is_controllable(self):
        """
        Returns True if the device can be controlled. This will be False for input type devices, like motion sensors.
        :return:
        """
        if self.has_device_feature(FEATURE_ALLOW_DIRECT_CONTROL) and \
                    is_true_false(self.controllable):
            return True
        return False

    @property
    def is_allowed_in_scenes(self):
        """
        True if device is allowed to be used in scenes or automation rules.

        :return:
        """
        if self.has_device_feature(FEATURE_ALLOW_IN_SCENES) and self.is_controllable:
            return True
        return False

    @property
    def percent(self):
        """
        This should be overridden by the device types themselves. This is simply a fallback.

        If the machine_state is 0, returns. Otherwise returns 100.
        """
        if len(self.state_history) > 0:
            machine_state = self.state_history[0].machine_state
            return self.calc_percent(machine_state, self.machine_state_extra)
        return 0

    def calc_percent(self, machine_state, machine_state_extra):
        """
        Like percent property, but accepts machine_state as input
        """
        if machine_state == 0:
            return 0
        elif machine_state <= 1:
            return round(machine_state*100)
        else:
            return 100

    # def __str__(self):
    #     """
    #     Print a string when printing the class.  This will return the device_id so that
    #     the device can be identified and referenced easily.
    #     """
    #     return f"Device: {self.label}"

    def __getitem__(self, key):
        return self.__dict__[key]

    def __repr__(self):
        return f"<Device {self.device_id}:{self.machine_label}>"

    def __len__(self):
        return len(self.__dict__)

    def has_key(self, k):
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

    # @cached(5)
    @property
    def device_variables(self):
        return self._VariableGroups.data("device", self.device_id)

    @property
    def device_variable_fieldss(self):
        return self._VariableGroups.fields("device", self.device_id)

    def __init__(self, parent, incoming, source=None, **kwargs):
        """
        :param incoming: *(dict)* - A device as passed in from the devices class. This is a
            dictionary with various device attributes.
        :ivar callBeforeChange: *(list)* - A list of functions to call before this device has it's state
            changed. (Not implemented.)
        :ivar callAfterChange: *(list)* - A list of functions to call after this device has it's state
            changed. (Not implemented.)
        :ivar device_id: *(string)* - The UUID of the device.
        :type device_id: string
        :ivar device_type_id: *(string)* - The device type UUID of the device.
        :ivar label: *(string)* - Device label as defined by the user.
        :ivar description: *(string)* - Device description as defined by the user.
        :ivar pin_required: *(bool)* - If a pin is required to access this device.
        :ivar pin_code: *(string)* - The device pin number.
            system to deliver commands and state update requests.
        :ivar created_at: *(int)* - When the device was created; in seconds since EPOCH.
        :ivar updated_at: *(int)* - When the device was last updated; in seconds since EPOCH.
        :ivar state_history: *(dict)* - A dictionary of strings for current and up to the last 30 state values.
        :ivar device_variables: *(dict)* - The device variables as defined by various modules, with
            values entered by the user.
        :ivar available_commands: *(list)* - A list of command_id's that are valid for this device.
        """
        self._Entity_type = "Device"
        self._Entity_label_attribute = "machine_label"
        super().__init__(parent)
        self.PLATFORM_BASE = "device"
        self.PLATFORM = "device"
        self.SUB_PLATFORM = None
        # Features this device can support
        self.FEATURES = {
            FEATURE_POWER_CONTROL: True,
            FEATURE_ALL_ON: False,
            FEATURE_ALL_OFF: False,
            FEATURE_PINGABLE: True,
            FEATURE_POLLABLE: True,
            FEATURE_SEND_UPDATES: True,
            FEATURE_ALLOW_IN_SCENES: True,
            FEATURE_CONTROLLABLE: True,
            FEATURE_ALLOW_DIRECT_CONTROL: True,
        }
        self.MACHINE_STATUS_EXTRA_FIELDS = {}  # Track what fields in state extra are allowed.
        self.TOGGLE_COMMANDS = False  # Put two command machine_labels in a list to enable toggling.

        self.call_before_command = []
        self.call_after_command = []
        self._security_send_device_states = self._Configs.get2("security", "amqpsenddevicestate", True)

        self.device_id = incoming["id"]
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
        self.device_serial = incoming["id"]
        self.device_mfg = "Yombo"
        self.device_model = "Yombo"
        self.state_delayed = {}
        self.state_delayed_calllater = None
        self.source = source
        self.parent = None  # Only set if this device is a child to anther device.
        self.parent_id = None  # Only set if this device is a child to anther device.

        sizes = memory_sizing[self._Parent._Atoms["mem.sizing"]]
        if incoming["gateway_id"] != self.gateway_id:
            self.device_commands = deque({}, sizes["other_device_commands"])
            self.state_history = deque({}, sizes["other_state_history"])
        else:
            self.device_commands = deque({}, sizes["local_device_commands"])
            self.state_history = deque({}, sizes["local_state_history"])

        self._setup_class_model(incoming, source=source)

    @inlineCallbacks
    def _system_init_(self, device, source):
        """
        Performs items that require deferreds'. This is for system use only.

        :return:
        """
        yield self.update_attributes(device, source=source, broadcast=False)
        self.start_data_sync()

        if self.test_device is None or self.test_device is False:
            self.meta = yield self._SQLDict.get("yombo.lib.device", "meta_" + self.device_id)
        else:
            self.meta = {}

        if self.test_device is False and self.device_is_new is True:
            self.device_is_new = False
            device_history = self._Configs.get("devices", "load_history_depth", 30)

            yield self.load_state_history(device_history)
            yield self.load_device_commands_history(device_history)

    def _init_(self, **kwargs):
        """
        Used by devices to run their init.

        :return:
        """
        pass

    def _load_(self, **kwargs):
        """
        This is called by the devices library when a new device is loaded for system use only.

        :param kwargs:
        :return:
        """
        pass

    def _start_(self, **kwargs):
        """
        This is called by the devices library when a new device is loaded and is used by devices that need
        to run any start up items.

        :param kwargs:
        :return:
        """
        pass

    def _unload_(self, **kwargs):
        """
        About to unload. Lets save all the device state items.

        :param kwargs:
        :return:
        """
        for state in self.state_history:
            state.save_to_db()

    def asdict(self):
        """
        Export device variables as a dictionary.
        """
        if len(self.state_history) > 0:
            state_current = self.state_history[0].asdict()
        else:
            state_current = None

        if len(self.state_history) > 1:
            state_previous = self.state_history[1].asdict()
        else:
            state_previous = None

        def clean_device_variables(device_variables):
            variables = deepcopy(device_variables)
            for label, data in variables.items():
                del data["data"]
                data["values"] = data["values_orig"]
                del data["values_orig"]
            return variables

        return {
            "gateway_id": self.gateway_id,
            "area": self.area,
            "location": self.location,
            "area_id": self.area_id,
            "location_id": self.location_id,
            "area_label": self.area_label,
            "full_label": self.full_label,
            "device_id": str(self.device_id),
            "device_type_id": str(self.device_type_id),
            "device_type_label": self._DeviceTypes[self.device_type_id].machine_label,
            "machine_label": str(self.machine_label),
            "label": str(self.label),
            "notes": str(self.notes),
            "description": str(self.description),
            "statistic_label": str(self.statistic_label),
            "statistic_type": str(self.statistic_type),
            "statistic_bucket_size": str(self.statistic_bucket_size),
            "statistic_lifetime": str(self.statistic_lifetime),
            "pin_code": "********",
            "pin_required": int(self.pin_required),
            "pin_timeout": self.pin_timeout,
            "intent_allow": int(self.intent_allow) if self.intent_allow is not None else 1,
            "intent_text": str(self.intent_text) if self.intent_text is not None else self.area_label,
            "created_at": int(self.created_at),
            "updated_at": int(self.updated_at),
            "device_commands": list(self.device_commands),
            "state_current": state_current,
            "state_previous": state_previous,
            "controllable": self.controllable,
            "allow_direct_control": self.allow_direct_control,
            "device_serial": self.device_serial,
            "device_mfg": self.device_mfg,
            "device_model": self.device_model,
            "device_platform": self.PLATFORM,
            "device_sub_platform": self.SUB_PLATFORM,
            "device_features": self.FEATURES,
            "device_variables": clean_device_variables(self.device_variables),
            "energy_tracker_device": self.energy_tracker_device,
            "energy_tracker_source": self.energy_tracker_source,
            "energy_type": self.energy_type,
            "energy_map": self.energy_map,
            "status": self.status,
            }

    def asdict_short(self):
        """
        Returns a dictionary that can be used to create children devices.
        """
        return {
            "gateway_id": self.gateway_id,
            "area_id": self.area_id,
            "location_id": self.location_id,
            "device_id": str(self.device_id),
            "device_type_id": str(self.device_type_id),
            "machine_label": str(self.machine_label),
            "label": str(self.label),
            "notes": str(self.notes),
            "description": str(self.description),
            "statistic_label": str(self.statistic_label),
            "statistic_type": str(self.statistic_type),
            "statistic_bucket_size": str(self.statistic_bucket_size),
            "statistic_lifetime": str(self.statistic_lifetime),
            "pin_code": self.pin_code,
            "pin_required": int(self.pin_required),
            "pin_timeout": self.pin_timeout,
            "intent_allow": int(self.intent_allow) if self.intent_allow is not None else 1,
            "intent_text": str(self.intent_text) if self.intent_text is not None else self.area_label,
            "controllable": self.controllable,
            "allow_direct_control": self.allow_direct_control,
            "status": self.status,

        }

    def update_attributes_preprocess(self, incoming):
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

        elif "energy_map" in incoming:
            if incoming["energy_map"] is not None:
                # create an energy map from a dictionary
                energy_map_final = {}
                if isinstance(incoming["energy_map"], dict) is False:
                    incoming["energy_map"] = {"0.0": 0, "1.0": 0}

                for percent, rate in incoming["energy_map"].items():
                    energy_map_final[self._InputTypes.check("percent", percent)] = self._Parent._InputTypes.check("number", rate)
                energy_map_final = OrderedDict(sorted(list(energy_map_final.items()), key=lambda x_y: float(x_y[0])))
                incoming["energy_map"] = energy_map_final
            else:
                incoming["energy_map"] = {"0.0": 0, "1.0": 0}

    def has_device_feature(self, feature_name, value=None):
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

    def get_state_extra(self, property_name):
        """
        Lookup a state extra value by property
        :param property_name:
        :return:
        """
        if len(self.state_history) > 0:
            state_current = self.state_history[0]
            if property_name in state_current.machine_state_extra:
                return state_current.machine_state_extra[property_name]
            raise KeyError("Property name not in machine state extra.")
        else:
            raise KeyError("Device has no state.")

    def available_commands(self):
        """
        Returns available commands for the current device.
        :return:
        """
        return self._Parent._DeviceTypes.device_type_commands(self.device_type_id)

    def in_available_commands(self, command):
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

    @inlineCallbacks
    def load_state_history(self, limit=None):
        """
        Loads device history into the device instance. This method gets the
         data from the db to actually set the values.

        :param limit: int - How many history items should be loaded. Default: 40
        :return:
        """
        if limit is None:
            limit = 40

        where = {
            "device_id": self.device_id,
        }
        records = yield self._Parent._LocalDB.generic_item_get("device_states", where=where, limit=limit)
        if len(records) > 0:
            for record in records:
                self.state_history.append(Device_State(self._Parent, self, record, source="database"))

    @inlineCallbacks
    def load_device_commands_history(self, limit=None):
        """
        Loads device command history into the device instance. This method gets the
        data from the db to actually set the values.

        :param limit: int - How many history items should be loaded. Default: 40
        :return:
        """
        if limit is None:
            limit = 40

        where = {
            "id": self.device_id,
        }
        records = yield self._Parent._LocalDB.generic_item_get("device_type_commands", where=where, limit=limit)
        if len(records) > 0:
            for record in records:
                if record["request_id"] not in self._Parent.device_commands:
                    self._Parent._DeviceCommands.add_device_command_by_object(record, start=False)

    def add_device_features(self, features):
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

    def remove_device_features(self, features):
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

    def add_machine_state_fields(self, fields):
        """
        Adds machine state fields in bulks.

        :param fields: A string, list, or dictionary of additional fields.
        :return:
        """
        if isinstance(fields, list):
            for field in fields:
                self.MACHINE_STATUS_EXTRA_FIELDS[field] = True
        elif isinstance(fields, dict):
            for field, value in fields:
                self.MACHINE_STATUS_EXTRA_FIELDS[field] = value
        elif isinstance(fields, str):
            self.MACHINE_STATUS_EXTRA_FIELDS[fields] = True

    def remove_machine_state_fields(self, features):
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
