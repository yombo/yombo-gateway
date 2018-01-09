from yombo.lib.devices._device import Device
from yombo.core.exceptions import YomboWarning
import yombo.utils.color as color_util


class Scene(Device):
    """
    A generic fan device.
    """

    PLATFORM = "scene"

    TOGGLE_COMMANDS = []  # Put two command machine_labels in a list to enable toggling.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "scene"
        self.TOGGLE_COMMANDS = ['on', 'off']  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            'all_on': False,
            'all_off': False,
            'pingable': False,
            'pollable': False,
            'sends_updates': False
        })

    def can_toggle(self):
        return True

    def toggle(self):
        return

    def turn_on(self, cmd, **kwargs):
        return self.command('on', **kwargs)

    def turn_off(self, cmd, **kwargs):
        return self.command('off', **kwargs)
