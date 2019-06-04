"""
Various sensors. A sensor is considered high if the machine state is 1, other low is 0.
"""
from yombo.constants.features import (FEATURE_NUMBER_OF_STEPS, FEATURE_ALL_ON, FEATURE_ALL_OFF, FEATURE_PINGABLE,
                                      FEATURE_POLLABLE, FEATURE_ALLOW_IN_SCENES, FEATURE_CONTROLLABLE,
                                      FEATURE_ALLOW_DIRECT_CONTROL)
from yombo.constants.commands import COMMAND_HIGH, COMMAND_LOW
from yombo.constants.platforms import (PLATFORM_BASE_SENSOR, PLATFORM_SENSOR, PLATFORM_BINARY_SENSOR,
                                       PLATFORM_MOTION_SENSOR, PLATFORM_NOISE_SENSOR, PLATFORM_THERMOMETER)

from yombo.lib.devices._device import Device


class Sensor(Device):
    """
    A generic Sensor
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = PLATFORM_BASE_SENSOR
        self.PLATFORM = PLATFORM_SENSOR
        self.TOGGLE_COMMANDS = False  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            FEATURE_ALL_ON: False,
            FEATURE_ALL_OFF: False,
            FEATURE_PINGABLE: False,
            FEATURE_POLLABLE: True,
            FEATURE_NUMBER_OF_STEPS: False,
            FEATURE_ALLOW_IN_SCENES: False,
            FEATURE_CONTROLLABLE: False,
            FEATURE_ALLOW_DIRECT_CONTROL: False,
        })

    @property
    def is_high(self):
        """
        If the state is 1, then it's high. 0 when it's not. If it's unknown, then None.

        :return:
        """
        if self.machine_state > 0:
            return True
        elif self.machine_state == 0:
            return False
        return None

    @property
    def is_low(self):
        """
        If the state is 1, then it's high. 0 when it's not. If it's unknown, then None.

        :return:
        """
        if self.machine_state > 0:
            return False
        elif self.machine_state == 0:
            return True
        return None

    def command_from_state(self, machine_state, machine_state_extra=None):
        """
        Attempt to find a command based on the state of a device.
        :param machine_state:
        :param machine_state_extra:
        :return:
        """
        # print("attempting to get command_from_state - Sensor: %s - %s" % (machine_state, machine_state_extra))
        if machine_state == int(1):
            return self._Parent._Commands[COMMAND_HIGH]
        elif machine_state == int(0):
            return self._Parent._Commands[COMMAND_LOW]
        return None


class Binary_Sensor(Sensor):
    """
    A sensor that will be either high or low.
    """
    def _init_(self):
        super()._init_()
        self.PLATFORM = PLATFORM_BINARY_SENSOR

    @property
    def is_high(self):
        """
        If the state is 1, then it's high. 0 when it's not. If it's unknown, then None.

        :return:
        """
        if self.machine_state == 1:
            return True
        elif self.machine_state == 0:
            return False
        return None

    @property
    def is_low(self):
        """
        If the state is 1, then it's high. 0 when it's not. If it's unknown, then None.

        :return:
        """
        if self.machine_state == 1:
            return False
        elif self.machine_state == 0:
            return True
        return None


class Motion_Sensor(Binary_Sensor):
    """
    A binary sensory, that's for motion.
    """
    def _init_(self):
        super()._init_()
        self.PLATFORM = PLATFORM_MOTION_SENSOR


class Noise_Sensor(Binary_Sensor):
    """
    A binary sensor that's for noise.
    """
    def _init_(self):
        super()._init_()
        self.PLATFORM = PLATFORM_NOISE_SENSOR


class Thermometer(Device):
    """
    A generic thermometer sensor
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = PLATFORM_THERMOMETER
        self.temperature_unit = "c"  # what temperature unit the device works in.

    @property
    def temperature(self):
        """
        Return the temperatures of this thermometer.
        """
        if len(self.state_history) > 0:
            return self.state_history[0].machine_state
        return None

    def command_from_state(self, machine_state, machine_state_extra=None):
        """
        Attempt to find a command based on the state of a device.
        :param machine_state:
        :return:
        """
        return None

