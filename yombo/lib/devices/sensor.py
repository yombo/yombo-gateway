"""
Various sensors. A sensor is considered high if the machine status is 1, other low is 0.
"""
from yombo.constants.features import (FEATURE_NUMBER_OF_STEPS, FEATURE_ALL_ON, FEATURE_ALL_OFF, FEATURE_PINGABLE,
                                      FEATURE_POLLABLE, FEATURE_ALLOW_IN_SCENES, FEATURE_CONTROLLABLE,
                                      FEATURE_ALLOW_DIRECT_CONTROL)
from yombo.constants.commands import COMMAND_HIGH, COMMAND_LOW

from yombo.lib.devices._device import Device


class Sensor(Device):
    """
    A generic Sensor
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = "sensor"
        self.PLATFORM = "sensor"
        self.TOGGLE_COMMANDS = False  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            FEATURE_ALL_ON: False,
            FEATURE_ALL_OFF: False,
            FEATURE_PINGABLE: False,
            FEATURE_POLLABLE: True,
            FEATURE_NUMBER_OF_STEPS: 2,
            FEATURE_ALLOW_IN_SCENES: False,
            FEATURE_CONTROLLABLE: False,
            FEATURE_ALLOW_DIRECT_CONTROL: False,
        })

    @property
    def is_high(self):
        """
        If the status is 1, then it's high. 0 when it's not. If it's unknown, then None.

        :return:
        """
        if self.machine_status > 0:
            return True
        elif self.machine_status == 0:
            return False
        return None

    @property
    def is_low(self):
        """
        If the status is 1, then it's high. 0 when it's not. If it's unknown, then None.

        :return:
        """
        if self.machine_status > 0:
            return False
        elif self.machine_status == 0:
            return True
        return None

    def command_from_status(self, machine_status, machine_status_extra=None):
        """
        Attempt to find a command based on the status of a device.
        :param machine_status:
        :param machine_status_extra:
        :return:
        """
        # print("attempting to get command_from_status - Sensor: %s - %s" % (machine_status, machine_status_extra))
        if machine_status == int(1):
            return self._Parent._Commands[COMMAND_HIGH]
        elif machine_status == int(0):
            return self._Parent._Commands[COMMAND_LOW]
        return None


class Digital_Sensor(Sensor):
    """
    A sensor that will be either high or low.
    """
    def _init_(self):
        super()._init_()
        self.PLATFORM = "digital_sensor"

    @property
    def is_high(self):
        """
        If the status is 1, then it's high. 0 when it's not. If it's unknown, then None.

        :return:
        """
        if self.machine_status == 1:
            return True
        elif self.machine_status == 0:
            return False
        return None

    @property
    def is_low(self):
        """
        If the status is 1, then it's high. 0 when it's not. If it's unknown, then None.

        :return:
        """
        if self.machine_status == 1:
            return False
        elif self.machine_status == 0:
            return True
        return None

class Thermometer(Device):
    """
    A generic thermometer sensor
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "thermometer"
        self.temperature_unit = 'c'  # what temperature unit the device works in.

    @property
    def temperature(self):
        """
        Return the temperatures of this thermometer.
        """
        if len(self.status_history) > 0:
            return self.status_history[0].machine_status
        return None

    def command_from_status(self, machine_status, machine_status_extra=None):
        """
        Attempt to find a command based on the status of a device.
        :param machine_status:
        :return:
        """
        return None

