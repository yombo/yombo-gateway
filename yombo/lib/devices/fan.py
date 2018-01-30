from yombo.lib.devices._device import Device
from yombo.core.exceptions import YomboWarning
import yombo.utils.color as color_util

# Brightness of the light, 0..255 or percentage
ATR_BRIGHTNESS = "brightness"
ATR_BRIGHTNESS_PCT = "brightness_pct"

# Integer that represents transition time in seconds to make change.
ATR_TRANSITION = "transition"

class Fan(Device):
    """
    A generic fan device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "fan"
        self.TOGGLE_COMMANDS = ['on', 'off']  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES['brightness'] = True
        self.FEATURES['color_temp'] = False
        self.FEATURES['effect'] = False
        self.FEATURES['rgb_color'] = False
        self.FEATURES['xy_color'] = False
        self.FEATURES['transition'] = False
        self.FEATURES['white_value'] = False
        self.FEATURES['number_of_steps'] = 4  # 0 = off, 4 = high

    def toggle(self):
        if self.status_history[0].machine_status == 0:
            if 'previous_on_speed' in self.meta:
                return self.command('on', inputs={'speed': self.meta['previous_on_speed']})
            else:
                return self.command('on', inputs={'speed': 4})
        else:
            return self.command('off')

    def turn_on(self, cmd, **kwargs):
        return self.command('on', **kwargs)

    def turn_off(self, cmd, **kwargs):
        return self.command('off', **kwargs)
