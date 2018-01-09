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

    def toggle(self):
        if self.status_history[0].machine_state == 0:
            return self.command('on')
        else:
            return self.command('off')

    def turn_on(self, cmd, **kwargs):
        return self.command('on', **kwargs)

    def turn_off(self, cmd, **kwargs):
        return self.command('off', **kwargs)
