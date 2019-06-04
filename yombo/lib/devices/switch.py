from yombo.constants.features import (FEATURE_NUMBER_OF_STEPS, FEATURE_ALL_ON, FEATURE_ALL_OFF, FEATURE_PINGABLE,
                                      FEATURE_POLLABLE, FEATURE_SEND_UPDATES, FEATURE_ALLOW_IN_SCENES)
from yombo.constants.commands import COMMAND_ON, COMMAND_OFF, COMMAND_OPEN, COMMAND_CLOSE
from yombo.constants.devicetypes.light import ATR_BRIGHTNESS, ATR_TRANSITION
from yombo.constants.platforms import PLATFORM_BASE_SWITCH, PLATFORM_SWITCH, PLATFORM_RELAY, PLATFORM_APPLIANCE

from yombo.lib.devices._device import Device
from yombo.core.exceptions import YomboWarning
import yombo.utils.color as color_util


class Switch(Device):
    """
    A generic switch device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = PLATFORM_BASE_SWITCH
        self.PLATFORM = PLATFORM_SWITCH
        self.TOGGLE_COMMANDS = [COMMAND_ON, COMMAND_OFF]  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            FEATURE_ALL_ON: False,
            FEATURE_ALL_OFF: False,
            FEATURE_PINGABLE: True,
            FEATURE_POLLABLE: True,
            FEATURE_SEND_UPDATES: False,
            FEATURE_NUMBER_OF_STEPS: 2,  # 0 = off, 1 = on
        })

    def can_toggle(self):
        return True

    def toggle(self):
        if self.status_history[0].machine_state == 0:
            return self.command(COMMAND_ON)
        else:
            return self.command(COMMAND_OFF)

    def turn_on(self, **kwargs):
        return self.command(COMMAND_ON, **kwargs)

    def turn_off(self, **kwargs):
        return self.command(COMMAND_OFF, **kwargs)

    def command_from_status(self, machine_state, machine_state_extra=None):
        """
        Attempt to find a command based on the status of a device.
        :param machine_state:
        :return:
        """
        # print("attempting to get command_from_status - relay: %s - %s" % (machine_state, machine_state_extra))
        if machine_state == int(1):
            return self._Commands[COMMAND_ON]
        elif machine_state == int(0):
            return self._Commands[COMMAND_OFF]
        return None


class Relay(Switch):
    """
    A generic relay device.
    """
    # Features this device can support
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = PLATFORM_RELAY
        self.TOGGLE_COMMANDS = [COMMAND_OPEN, COMMAND_CLOSE]  # Put two command machine_labels in a list to enable toggling.

    def toggle(self):
        if self.status_history[0].machine_state == 0:
            return self.command(COMMAND_OPEN)
        else:
            return self.command(COMMAND_CLOSE)


class Appliance(Switch):
    """
    An appliance shouldn't be used in scenes.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = PLATFORM_APPLIANCE
        self.FEATURES[FEATURE_ALLOW_IN_SCENES] = False
