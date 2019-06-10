# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_

The device class is the base class all devices should inherit from. This class inherits from Device_Base for
it's function processing and Device_Attributes to setup the device attributes.

The attributes and functions in this class are intended to be overridden by subclasses, however, attributes from
the Device_Attributes can also be overridden, but that is less common.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2018 by Yombo.
:license: LICENSE for details.
"""
# Yombo Constants
from yombo.constants.commands import (COMMAND_TOGGLE, COMMAND_OPEN, COMMAND_ON, COMMAND_OFF, COMMAND_CLOSE,
                                      COMMAND_HIGH, COMMAND_LOW)
# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import instance_properties
from ._device_attributes import Device_Attributes
from ._device_base import Device_Base

logger = get_logger("library.devices.device")


class Device(Device_Attributes, Device_Base):
    """
    The parent to all child device types.
    """
    _primary_column = "device_id"  # Used by mixins

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

    def generate_human_state(self, machine_state, machine_state_extra):
        if machine_state == 1:
            return "On"
        return "Off"

    def generate_human_message(self, machine_state, machine_state_extra):
        human_state = self.generate_human_state(machine_state, machine_state_extra)
        return f"{self.area_label} is now {human_state}"

    def available_state_modes_values(self):
        return instance_properties(self, startswith_filter="STATUS_MODES_")

    def available_state_extra_attributes(self):
        return instance_properties(self, startswith_filter="STATUS_EXTRA_")

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
            machine_state = float(kwargs["machine_state"])
        else:
            machine_state = float(self.state_history[0]["machine_state"])

        if "machine_state_extra" in kwargs:
            machine_state_extra = kwargs["machine_state_extra"]
        else:
            machine_state_extra = self.state_history[0]["machine_state_extra"]

        # print("energy_calc: machine_state: %s" % machine_state)
        # print("energy_calc: machine_state_extra: %s" % machine_state_extra)

        percent = self.calc_percent(machine_state, machine_state_extra) / 100
        # print("energy_calc: percent: %s" % percent)

        if self.energy_tracker_source != "calculated":
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
