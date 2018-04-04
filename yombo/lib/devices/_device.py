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
from ._base_device import Base_Device
logger = get_logger('library.devices.device')

# Yombo Constants
from yombo.constants.commands import (COMMAND_TOGGLE, COMMAND_OPEN, COMMAND_ON, COMMAND_OFF, COMMAND_CLOSE,
                                      COMMAND_HIGH, COMMAND_LOW)


class Device(Base_Device):
    """
    The parent to all child device types.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def device_feature_is_active(self, feature_name):
        if feature_name not in self.FEATURES:
            return False
        value = self.FEATURES[feature_name]
        if value is False:
            return False
        if value is True:
            return True
        if isinstance(value, dict) or isinstance(value, list):
            return True
        return False

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
        if self.TOGGLE_COMMANDS is False or self.TOGGLE_COMMANDS is None:
            return False
        if isinstance(self.TOGGLE_COMMANDS, list) is False:
            return False
        if len(self.TOGGLE_COMMANDS) == 2:
            return True
        return False

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

    def command_from_status(self, machine_status, machine_status_extra=None):
        """
        Attempt to find a command based on the status of a device.
        :param machine_status:
        :param machine_status_extra:
        :return:
        """
        # print("attempting to get command_from_status - device: %s - %s" % (machine_status, machine_status_extra))
        if machine_status == int(1):
            for item in (COMMAND_ON, COMMAND_OPEN, COMMAND_HIGH):
                try:
                    command = self.in_available_commands(item)
                    return command
                except Exception:
                    pass
        elif machine_status == int(0):
            for item in (COMMAND_OFF, COMMAND_CLOSE, COMMAND_LOW):
                try:
                    command = self.in_available_commands(item)
                    return command
                except Exception:
                    pass
        return None

