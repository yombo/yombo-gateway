from yombo.lib.devices._device import Device
from yombo.core.exceptions import YomboWarning
import yombo.utils.color as color_util


class Lock(Device):
    """
    A generic fan device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "Lock"
        self.TOGGLE_COMMANDS = ['lock', 'unlock']  # Put two command machine_labels in a list to enable toggling.

    def toggle(self):
        if self.status_history[0].machine_state == 0:
            return self.command('lock')
        else:
            return self.command('unlock')

    def turn_on(self, cmd, **kwargs):
        return self.command('lock', **kwargs)

    def turn_off(self, cmd, **kwargs):
        return self.command('unlock', **kwargs)
