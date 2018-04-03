from yombo.constants.features import (FEATURE_NUMBER_OF_STEPS, FEATURE_ALL_ON, FEATURE_ALL_OFF, FEATURE_PINGABLE,
    FEATURE_POLLABLE, FEATURE_SEND_UPDATES)
from yombo.constants.commands import COMMAND_ON, COMMAND_OFF, COMMAND_OPEN, COMMAND_CLOSE

from yombo.lib.devices._device import Device
from yombo.core.exceptions import YomboWarning
import yombo.utils.color as color_util

# Brightness of the light, 0..255 or percentage
ATR_BRIGHTNESS = "brightness"
ATR_BRIGHTNESS_PCT = "brightness_pct"

# Integer that represents transition time in seconds to make change.
ATR_TRANSITION = "transition"


class Switch(Device):
    """
    A generic switch device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "switch"
        self.TOGGLE_COMMANDS = ['on', 'off']  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            FEATURE_ALL_ON: False,
            FEATURE_ALL_OFF: False,
            FEATURE_PINGABLE: True,
            FEATURE_POLLABLE: True,
            FEATURE_SEND_UPDATES: False,
            FEATURE_NUMBER_OF_STEPS: 2  # 0 = off, 1 = on
        })

    def can_toggle(self):
        return True

    def toggle(self):
        if self.status_history[0].machine_status == 0:
            return self.command(COMMAND_ON)
        else:
            return self.command(COMMAND_OFF)

    def turn_on(self, **kwargs):
        return self.command(COMMAND_ON, **kwargs)

    def turn_off(self, **kwargs):
        return self.command(COMMAND_OFF, **kwargs)

    def command_from_status(self, machine_status, machine_status_extra=None):
        """
        Attempt to find a command based on the status of a device.
        :param machine_status:
        :return:
        """
        # print("attempting to get command_from_status - relay: %s - %s" % (machine_status, machine_status_extra))
        if machine_status == int(1):
            return self._Commands[COMMAND_ON]
        elif machine_status == int(0):
            return self._Commands[COMMAND_OFF]
        return None


class Relay(Switch):
    """
    A generic relay device.
    """
    # Features this device can support
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "relay"
        self.TOGGLE_COMMANDS = [COMMAND_OPEN, COMMAND_CLOSE]  # Put two command machine_labels in a list to enable toggling.

    def toggle(self):
        if self.status_history[0].machine_status == 0:
            return self.command(COMMAND_OPEN)
        else:
            return self.command(COMMAND_CLOSE)
