from yombo.lib.devices._device import Device
from yombo.core.exceptions import YomboWarning
import yombo.utils.color as color_util


class ActivityTrigger(Device):
    """
    A generic activity trigger device. Basically calls a scene when something triggers this device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "activity_trigger"
        self.TOGGLE_COMMANDS = ['on', 'off']  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES['brightness'] = False
        self.FEATURES['number_of_steps'] = 2  # 0 = off, 1 = on

    def toggle(self):
        if self.status_history[0].machine_status == 0:
            return self.command('on')
        else:
            return self.command('off')

    def turn_on(self, cmd, **kwargs):
        return self.command('on', **kwargs)

    def turn_off(self, cmd, **kwargs):
        return self.command('off', **kwargs)
