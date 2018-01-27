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
            'all_on': False,
            'all_off': False,
            'pingable': True,
            'pollable': True,
            'sends_updates': False,
            'number_of_steps': 2  # 0 = off, 1 = on
        })

    def can_toggle(self):
        return True

    def toggle(self):
        if self.status_history[0].machine_state == 0:
            return self.command('on')
        else:
            return self.command('off')

    def turn_on(self, cmd, **kwargs):
        return self.command('on', **kwargs)

    def turn_off(self, cmd, **kwargs):
        return self.command('off', **kwargs)

    def command_from_status(self, machine_status, machine_status_extra=None):
        """
        Attempt to find a command based on the status of a device.
        :param machine_status:
        :return:
        """
        # print("attempting to get command_from_status - relay: %s - %s" % (machine_status, machine_status_extra))
        if machine_status == int(1):
            return self._Commands['on']
        elif machine_status == int(0):
            return self._Commands['off']
        return None


class Relay(Switch):
    """
    A generic relay device.
    """
    # Features this device can support
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "relay"
        self.TOGGLE_COMMANDS = ['open', 'close']  # Put two command machine_labels in a list to enable toggling.

    def toggle(self):
        if self.status_history[0].machine_state == 0:
            return self.command('open')
        else:
            return self.command('close')
