# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_

A device class to be inherited by all device types.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from time import time

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import instance_properties
from ._device_status import Device_Status
from ._base_device import Base_Device
logger = get_logger('library.devices.device')

class Device(Base_Device):
    """
    The parent to all child device types.
    """
    def __init__(self, *args, **kwargs):
        # Features this device can support
        self.FEATURES = {
            'power_control': True,
            'all_on': False,
            'all_off': False,
            'pingable': True,
            'pollable': True,
            'sends_updates': True
        }

        self.PLATFORM = "device"
        self.SUB_PLATFORM = None
        self.TOGGLE_COMMANDS = False  # Put two command machine_labels in a list to enable toggling.

        self.STATUS_EXTRA = {}
        # self.STATUS_EXTRA = {
        #     'mode': ['auto', 'on', 'off'],
        #     'running': ['auto', 'on', 'off'],
        # }
        super().__init__(*args, **kwargs)

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
        except Exception as e:
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
        except Exception as e:
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
        except Exception as e:
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
    def should_poll(self) -> bool:
        """
        Return True if the device needs to be polled to get current status.
        False if devices push status updates.

        In most cases, the module handling the device will automatically poll the device periodically. For these
        devices and for devices that don't send updates or are not polled, should return True.
        """
        return True

    @property
    def current_mode(self):
        """
        Return the current mode of operation for the device.
        """
        machine_status_extra = self.machine_status_extra
        if 'mode' in machine_status_extra.machine_status_extra:
            return machine_status_extra.machine_status_extra['mode']
        return None

    @property
    def status(self):
        """
        Return the machine status of the device.
        """
        # print("load history (%s): %s" % (self.label, len(self.status_history)))
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
    def unit_of_measurement(self):
        """
        Return the unit of measurement of this device, if any.
        """
        return None

    @property
    def icon(self):
        """
        Return the icon to use in the frontend, if any.
        """
        return None

    @property
    def icon_on_click(self):
        """
        Return the icon to use when icon is clicked, if any.
        """
        return None

    @property
    def device_picture(self):
        """
        Return the device picture to use in the frontend, if any.
        """
        return None

    @property
    def hidden(self) -> bool:
        """
        Return True if the device should be hidden from UIs.
        """
        return False

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

    @property
    def device_type(self):
        """
        Returns the device type object for the device.
        :return:
        """
        return self._Parent._DeviceTypes[self.device_type_id]

    def generate_human_status(self, machine_status, machine_status_extra):
        if machine_status == 1:
            return "On"
        return "Off"

    def generate_human_message(self, machine_status, machine_status_extra):
        human_status = self.generate_human_status(machine_status, machine_status_extra)
        return "%s is now %s" % (self.area_label, human_status)

    def get_toggle_command(self):
        """
        If a device is toggleable, return True. It's toggleable if a device only has two commands.
        :return: 
        """
        if self.can_toggle():
            if self.device_commands > 0:
                request_id = self.device_commands[0]
                request = self._Parent.device_commands[request_id]
                command_id = request.command.command_id
                for toggle_command_id in self.TOGGLE_COMMANDS:
                    if toggle_command_id == command_id:
                        continue
                    return self._Parent._Commands[toggle_command_id]
            else:
                raise YomboWarning("Device cannot be toggled, device is in unknown state.")
        raise YomboWarning("Device cannot be toggled, it's not enabled for this device.")

    def available_status_modes_values(self):
        return instance_properties(self, startswith_filter='STATUS_MODES_')

    def available_status_extra_attributes(self):
        return instance_properties(self, startswith_filter='STATUS_EXTRA_')

    def energy_calc(self, **kwargs):
        """
        Returns the energy being used based on a percentage the device is on.  Inspired by:
        http://stackoverflow.com/questions/1969240/mapping-a-range-of-values-to-another

        Supply the machine_status, machine_status_extra,and last command. If these are not supplied, it will
        be taken from teh device history.

        :param machine_status:
        :param map:
        :return:
        """
        # map = {
        #     0: 1,
        #     0.5: 100,
        #     1: 400,
        # }

        if 'machine_status' in kwargs:
            machine_status = kwargs['machine_status']
        else:
            machine_status = self.status_history[0]['machine_status']

        if machine_status is None:
            raise ValueError("Machine status cannot be none.")

        if self.energy_tracker_source != 'calc':
            return [0, self.energy_type]

        if self.energy_map == None:
            return [0, self.energy_type]  # if no map is found, we always return 0

        items = list(self.energy_map.items())
        for i in range(0, len(self.energy_map) - 1):
            if items[i][0] <= machine_status <= items[i + 1][0]:
                value = self.energy_translate(machine_status, items[i][0], items[i + 1][0], items[i][1],
                                              items[i + 1][1])
                return [value, self.energy_type]
        raise ValueError("Unable to determine enery usage.")


    def can_toggle(self):
        """
        If a device is toggleable, return True. It's toggleable if a device only has two commands.
        :return:
        """
        if isinstance(self.TOGGLE_COMMANDS, list) is False:
            return False
        if len(self.TOGGLE_COMMANDS) == 2:
            return True
        return False

    def is_dimmable(self):
        return self.SUPPORT_BRIGHTNESS

    def is_on(self):
        if self.status_history[0].machine_status > 0:
            return True
        else:
            return False

    def is_off(self):
        return not self.is_on()

    def toggle(self):
        return self.command('toggle')

    def turn_on(self, **kwargs):
        for item in ('on', 'open'):
            try:
                command = self.in_available_commands(item)
                return self.command(command, **kwargs)
            except Exception:
                pass
        raise YomboWarning("Unable to turn on device. Device doesn't have any of these commands: on, open")

    def turn_off(self, cmd, **kwargs):
        for item in ('off', 'close'):
            try:
                command = self.in_available_commands(item)
                return self.command(command, **kwargs)
            except Exception:
                pass
        raise YomboWarning("Unable to turn off device. Device doesn't have any of these commands: off, close")

    def command_from_status(self, machine_status, machine_status_extra=None):
        """
        Attempt to find a command based on the status of a device.
        :param machine_status:
        :return:
        """
        # print("attempting to get command_from_status - device: %s - %s" % (machine_status, machine_status_extra))
        if machine_status == int(1):
            for item in ('on', 'open', 'high'):
                try:
                    command = self.in_available_commands(item)
                    return command
                except Exception:
                    pass
        elif machine_status == int(0):
            for item in ('off', 'close', 'low'):
                try:
                    command = self.in_available_commands(item)
                    return command
                except Exception:
                    pass
        return None

