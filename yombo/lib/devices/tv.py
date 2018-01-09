from yombo.lib.devices._device import Device
from yombo.core.exceptions import YomboWarning
import yombo.utils.color as color_util


class TV(Device):
    """
    A generic TV device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "tv"
        self.TOGGLE_COMMANDS = ['on', 'off']
        self.FEATURES['channel_control'] = True
        self.FEATURES['input_control'] = True

    def toggle(self):
        if self.status_history[0].machine_state == 0:
            return self.command('on')
        else:
            return self.command('off')

    def turn_on(self, cmd, **kwargs):
        return self.command('on', **kwargs)

    def turn_off(self, cmd, **kwargs):
        return self.command('off', **kwargs)
