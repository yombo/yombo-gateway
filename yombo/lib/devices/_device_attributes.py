# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_

This is the root of the device class. It's responsible for all attributes and bootstrapping.

This class in inherited by _device_base, which is inherited by _device.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from collections import deque, OrderedDict
from copy import deepcopy
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Yombo Constants
from yombo.constants.features import (FEATURE_ALL_OFF, FEATURE_ALL_ON, FEATURE_PINGABLE, FEATURE_POLLABLE,
                                      FEATURE_SEND_UPDATES, FEATURE_POWER_CONTROL, FEATURE_ALLOW_IN_SCENES,
                                      FEATURE_CONTROLLABLE, FEATURE_ALLOW_DIRECT_CONTROL)

# Import Yombo libraries
from yombo.utils import is_true_false
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import global_invoke_all, do_search_instance

from ._device_command import Device_Command
from ._device_status import Device_Status
logger = get_logger('library.devices.device_attributes')

class Device_Attributes(object):
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
        * :py:meth:`get_status <Device.get_status>` - Get a latest device status object.
        * :py:meth:`set_status <Device.set_status>` - Set the device status.
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
        return "%s%s" % (area, self.label)

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
    def status(self):
        """
        Return the machine status of the device.
        """
        return self.machine_status

    @property
    def machine_status(self):
        """
        Get the current machine status for a device.

        :return:
        """
        return self.status_all.machine_status

    @property
    def machine_status_extra(self):
        """
        Get the current machine status extra details for a device.

        :return:
        """
        return self.status_all.machine_status_extra

    @property
    def status_all(self):
        """
        Return the device's current status. Will return fake status of
        there is no current status which basically says the status is unknown.
        """
        if len(self.status_history) == 0:
            requested_by = {
                'user_id': 'Unknown',
                'component': 'Unknown',
            }
            return Device_Status(self._Parent, self, {
                'device_id': self.device_id,
                'set_at': time(),
                'energy_usage': 0,
                'energy_type': self.energy_type,
                'human_status': 'Unknown',
                'human_message': 'Unknown status for device',
                'machine_status': None,
                'machine_status_extra': {},
                'gateway_id': self.gateway_id,
                'requested_by': requested_by,
                'reported_by': None,
                'request_id': None,
                'uploaded': 0,
                'uploadable': 1,
                'fake_data': True,
            })
        return self.status_history[0]

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
        if self.has_device_feature(FEATURE_CONTROLLABLE) and \
                    self.has_device_feature(FEATURE_ALLOW_DIRECT_CONTROL) and \
                    is_true_false(self.allow_direct_control) and \
                    is_true_false(self.controllable):
            return True
        return False

    @property
    def is_controllable(self):
        if self.has_device_feature(FEATURE_ALLOW_DIRECT_CONTROL) and \
                    is_true_false(self.controllable):
            return True
        return False

    @property
    def is_allowed_in_scenes(self):
        if self.has_device_feature(FEATURE_ALLOW_IN_SCENES) and self.is_controllable:
            return True
        return False

    def __str__(self):
        """
        Print a string when printing the class.  This will return the device_id so that
        the device can be identified and referenced easily.
        """
        return self.device_id

    def __getitem__(self, key):
        return self.__dict__[key]

    def __repr__(self):
        return repr(self.__dict__)

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

    def __init__(self, _Parent, device, test_device=None):
        """
        :param device: *(list)* - A device as passed in from the devices class. This is a
            dictionary with various device attributes.
        :ivar callBeforeChange: *(list)* - A list of functions to call before this device has it's status
            changed. (Not implemented.)
        :ivar callAfterChange: *(list)* - A list of functions to call after this device has it's status
            changed. (Not implemented.)
        :ivar device_id: *(string)* - The UUID of the device.
        :type device_id: string
        :ivar device_type_id: *(string)* - The device type UUID of the device.
        :ivar label: *(string)* - Device label as defined by the user.
        :ivar description: *(string)* - Device description as defined by the user.
        :ivar pin_required: *(bool)* - If a pin is required to access this device.
        :ivar pin_code: *(string)* - The device pin number.
            system to deliver commands and status update requests.
        :ivar created_at: *(int)* - When the device was created; in seconds since EPOCH.
        :ivar updated_at: *(int)* - When the device was last updated; in seconds since EPOCH.
        :ivar status_history: *(dict)* - A dictionary of strings for current and up to the last 30 status values.
        :ivar device_variables_cached: *(dict)* - The device variables as defined by various modules, with
            values entered by the user.
        :ivar available_commands: *(list)* - A list of command_id's that are valid for this device.
        """
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
        self.MACHINE_STATUS_EXTRA_FIELDS = {}  # Track what fields in status extra are allowed.
        self.TOGGLE_COMMANDS = False  # Put two command machine_labels in a list to enable toggling.

        self._FullName = 'yombo.gateway.lib.Devices.Device'
        self._Name = 'Devices.Device'
        self._Parent = _Parent
        self.call_before_command = []
        self.call_after_command = []
        self._security_send_device_status = self._Configs.get2("security", "amqpsenddevicestatus", True)

        self.device_id = device["id"]
        if test_device is None:
            self.test_device = False
        else:
            self.test_device = test_device

        memory_sizing = {
            'x_small': {'other_device_commands': 2,  #less then 256mb
                           'other_status_history': 2,
                           'local_device_commands': 5,
                           'local_status_history': 5},
            'small': {'other_device_commands': 5,  #About 512mb
                           'other_status_history': 5,
                           'local_device_commands': 25,
                           'local_status_history': 25},
            'medium': {'other_device_commands': 25,  # About 1024mb
                      'other_status_history': 25,
                      'local_device_commands': 75,
                      'local_status_history': 75},
            'large': {'other_device_commands': 50,  # About 2048mb
                       'other_status_history': 50,
                       'local_device_commands': 125,
                       'local_status_history': 125},
            'x_large': {'other_device_commands': 100,  # About 4092mb
                      'other_status_history': 100,
                      'local_device_commands': 250,
                      'local_status_history': 250},
            'xx_large': {'other_device_commands': 200,  # About 8000mb
                        'other_status_history': 200,
                        'local_device_commands': 500,
                        'local_status_history': 500},
        }

        sizes = memory_sizing[self._Parent._Atoms['mem.sizing']]
        self.device_commands = deque({}, sizes['other_device_commands'])
        self.status_history = deque({}, sizes['other_status_history'])

        self.device_variables_cached = {}
        self.device_variable_fields_cached = {}

        self.device_type_id = None
        self.gateway_id = None
        self.location_id = None
        self.area_id = None
        self.machine_label = None
        self.label = None
        self.description = None
        self.pin_required = None
        self.pin_code = None
        self.pin_timeout = None
        self.voice_cmd = None
        self.voice_cmd_order = None
        self.statistic_label = None
        self.statistic_type = None
        self.statistic_bucket_size = None
        self.statistic_lifetime = None
        self.enabled_status = None  # not to be confused for device state. see status_history
        self.created_at = None
        self.updated_at = None
        self.energy_tracker_device = None
        self.energy_tracker_source = None
        self.energy_map = None
        self.energy_type = None
        self.allow_direct_control = None
        self.controllable = None
        self.energy_type = None
        self.device_is_new = True
        self.device_serial = device["id"]
        self.device_mfg = "Yombo"
        self.device_model = "Yombo"

        self.update_attributes(device, source='parent')
        if device["gateway_id"] != self.gateway_id:
            self.device_commands = deque({}, sizes['other_device_commands'])
            self.status_history = deque({}, sizes['other_status_history'])
        else:
            self.device_commands = deque({}, sizes['local_device_commands'])
            self.status_history = deque({}, sizes['local_status_history'])

    @inlineCallbacks
    def _init0_(self, **kwargs):
        """
        Performs items that require deferreds. This is for system use only.

        :return:
        """
        yield self.device_variables()
        self.device_variables_cached = yield self.device_variables()
        self.device_variable_fields_cached = yield self.device_variable_fields()
        if self.test_device is None or self.test_device is False:
            self.meta = yield self._SQLDict.get('yombo.lib.device', 'meta_' + self.device_id)
        else:
            self.meta = {}

        yield self._Parent._DeviceTypes.ensure_loaded(self.device_type_id)

        if self.test_device is False and self.device_is_new is True:
            self.device_is_new = False
            yield self.load_status_history(35)
            yield self.load_device_commands_history(35)

    def _init_(self, **kwargs):
        """
        Used by devices to run their init. This is called after the system _init0_ is called.

        :return:
        """
        pass

    def _start0_(self, **kwargs):
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
        About to unload. Lets save all the device status items.

        :param kwargs:
        :return:
        """
        for status in self.status_history:
            status.save_to_db()

    def asdict(self):
        """
        Export device variables as a dictionary.
        """
        if len(self.status_history) > 0:
            status_current = self.status_history[0].asdict()
        else:
            status_current = None

        if len(self.status_history) > 1:
            status_previous = self.status_history[1].asdict()
        else:
            status_previous = None

        def clean_device_variables(device_variables):
            variables = deepcopy(device_variables)
            for label, data in variables.items():
                del data['data']
                data['values'] = data['values_orig']
                del data['values_orig']
            return variables

        return {
            'gateway_id': self.gateway_id,
            'area': self.area,
            'location': self.location,
            'area_label': self.area_label,
            'full_label': self.full_label,
            'device_id': str(self.device_id),
            'device_type_id': str(self.device_type_id),
            'device_type_label': self._DeviceTypes[self.device_type_id].machine_label,
            'machine_label': str(self.machine_label),
            'label': str(self.label),
            'description': str(self.description),
            'statistic_label': str(self.statistic_label),
            'statistic_type': str(self.statistic_type),
            'statistic_bucket_size': str(self.statistic_bucket_size),
            'statistic_lifetime': str(self.statistic_lifetime),
            'pin_code': "********",
            'pin_required': int(self.pin_required),
            'pin_timeout': self.pin_timeout,
            'voice_cmd': str(self.voice_cmd),
            'voice_cmd_order': str(self.voice_cmd_order),
            'created_at': int(self.created_at),
            'updated_at': int(self.updated_at),
            'device_commands': list(self.device_commands),
            'status_current': status_current,
            'status_previous': status_previous,
            'device_serial': self.device_serial,
            'device_mfg': self.device_mfg,
            'device_model': self.device_model,
            'device_platform': self.PLATFORM,
            'device_sub_platform': self.SUB_PLATFORM,
            'device_features': self.FEATURES,
            'device_variables': clean_device_variables(self.device_variables_cached),
            'device_variable_fields': self.device_variable_fields_cached,
            'enabled_status': self.enabled_status,
            }

    def update_attributes(self, device, source=None):
        """
        Sets various values from a device dictionary. This can be called when the device is first being setup or
        when being updated by the AMQP service.

        This does not set any device state or status attributes.

        :param device:
        :return:
        """
        if 'device_type_id' in device:
            self.device_type_id = device["device_type_id"]
        if 'gateway_id' in device:
            self.gateway_id = device["gateway_id"]
        if 'location_id' in device:
            self.location_id = device["location_id"]
        if 'area_id' in device:
            self.area_id = device["area_id"]
        if 'machine_label' in device:
            self.machine_label = device["machine_label"]
        if 'label' in device:
            self.label = device["label"]
        if 'description' in device:
            self.description = device["description"]
        if 'pin_required' in device:
            self.pin_required = int(device["pin_required"])
        if 'pin_code' in device:
            self.pin_code = device["pin_code"]
        if 'pin_timeout' in device:
            try:
                self.pin_timeout = int(device["pin_timeout"])
            except:
                self.pin_timeout = None
        if 'voice_cmd' in device:
            self.voice_cmd = device["voice_cmd"]
        if 'voice_cmd_order' in device:
            self.voice_cmd_order = device["voice_cmd_order"]
        if 'statistic_label' in device:
            self.statistic_label = device["statistic_label"]  # 'myhome.groundfloor.kitchen'
        if 'statistic_type' in device:
            self.statistic_type = device["statistic_type"]
        if 'statistic_bucket_size' in device:
            self.statistic_bucket_size = device["statistic_bucket_size"]
        if 'statistic_lifetime' in device:
            self.statistic_lifetime = device["statistic_lifetime"]
        if 'status' in device:
            self.enabled_status = int(device["status"])
        if 'created_at' in device:
            self.created_at = int(device["created_at"])
        if 'updated_at' in device:
            self.updated_at = int(device["updated_at"])
        if 'energy_tracker_device' in device:
            self.energy_tracker_device = device['energy_tracker_device']
        if 'energy_tracker_source' in device:
            self.energy_tracker_source = device['energy_tracker_source']
        if 'energy_type' in device:
            self.energy_type = device['energy_type']

        if 'energy_map' in device:
            if device['energy_map'] is not None:
                # create an energy map from a dictionary
                energy_map_final = {}
                if isinstance(device['energy_map'], dict) is False:
                    device['energy_map'] = {"0.0":0,"1.0":0}

                for percent, rate in device['energy_map'].items():
                    energy_map_final[self._Parent._InputTypes.check('percent', percent)] = self._Parent._InputTypes.check('number' , rate)
                energy_map_final = OrderedDict(sorted(list(energy_map_final.items()), key=lambda x_y: float(x_y[0])))
                self.energy_map = energy_map_final
            else:
                self.energy_map = None

        if 'controllable' in device:
            self.controllable = device['controllable']
        if 'allow_direct_control' in device:
            self.allow_direct_control = device['allow_direct_control']

        if self.device_is_new is True:
            global_invoke_all('_device_updated_',
                              called_by=self,
                              id=self.device_id,
                              device=self,
                              )

        if source != "parent" and source != "webinterface":
            self._Parent.edit_device(device, source="node")

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

    def get_status_extra(self, property_name):
        """
        Lookup a status extra value by property
        :param property_name:
        :return:
        """
        if len(self.status_history) > 0:
            status_current = self.status_history[0]
            if property_name in status_current.machine_status_extra:
                return status_current.machine_status_extra[property_name]
            raise KeyError("Property name not in machine status extra.")
        else:
            raise KeyError("Device has no status.")

    @inlineCallbacks
    def device_variables(self):
        """
        Gets all device variables, non-cached version. Will update the cached version.

        :return:
        """
        self.device_variables_cached = yield self._Parent._Variables.get_variable_fields_data(
            group_relation_type='device_type',
            group_relation_id=self.device_type_id,
            data_relation_id=self.device_id
        )
        return self.device_variables_cached

    @inlineCallbacks
    def device_variable_fields(self):
        """
        Get the device variable field

        :return:
        """
        self.device_variable_fields_cached = yield self._Parent._DeviceTypes[self.device_type_id].get_variable_fields()
        return self.device_variable_fields_cached

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
    def load_status_history(self, limit=40):
        """
        Loads device history into the device instance. This method gets the
         data from the db to actually set the values.

        :param limit: int - How many history items should be loaded. Default: 40
        :return:
        """
        if limit is None:
            limit = False

        where = {
            'device_id': self.device_id,
        }
        records = yield self._Parent._Libraries['LocalDB'].get_device_status(where, limit=limit)
        if len(records) > 0:
            for record in records:
                self.status_history.appendleft(Device_Status(self._Parent, self, record, source='database'))

    @inlineCallbacks
    def load_device_commands_history(self, limit=40):
        """
        Loads device command history into the device instance. This method gets the
        data from the db to actually set the values.

        :param limit: int - How many history items should be loaded. Default: 40
        :return:
        """
        if limit is None:
            limit = False

        where = {
            'id': self.device_id,
        }
        records = yield self._Parent._Libraries['LocalDB'].get_device_commands(where, limit=limit)
        if len(records) > 0:
            for record in records:
                if record['request_id'] not in self._Parent.device_commands:
                    self._Parent.add_device_command_by_object(Device_Command(record, self, start=False))

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

    def add_machine_status_fields(self, fields):
        """
        Adds machine status fields in bulks.

        :param fields: A string, list, or dictionary of additional fields.
        :return:
        """
        if isinstance(fields, list):
            for feature in fields:
                self.MACHINE_STATUS_EXTRA_FIELDS[feature] = True
        elif isinstance(fields, dict):
            for feature, value in fields:
                self.MACHINE_STATUS_EXTRA_FIELDS[feature] = value
        elif isinstance(fields, str):
            self.MACHINE_STATUS_EXTRA_FIELDS[fields] = True

    def remove_machine_status_fields(self, fields):
        """
        Removes features from a device. Accepts a list or a string for a single item.

        :param fields: A list of features to remove from device.
        :return:
        """
        def remove_field(fields):
            if feature in self.FEATURES:
                del self.FEATURES[feature]

        if isinstance(fields, list):
            for feature in fields:
                remove_field(feature)
        elif isinstance(fields, dict):
            for feature, value in fields:
                remove_field(feature)
        elif isinstance(fields, str):
            remove_field(fields)