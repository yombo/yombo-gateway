from yombo.lib.devices._device import Device
from yombo.constants.commands import COMMAND_OFF, COMMAND_ON


class Scene(Device):
    """
    A generic fan device.
    """

    PLATFORM = "scene"

    TOGGLE_COMMANDS = []  # Put two command machine_labels in a list to enable toggling.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "scene"
        self.TOGGLE_COMMANDS = [COMMAND_ON, COMMAND_OFF]  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            'all_on': False,
            'all_off': False,
            'pingable': False,
            'pollable': False,
            'sends_updates': False,
            'supports_deactivation': False,
        })

    def can_toggle(self):
        return True

    def toggle(self):
        return

    def turn_on(self, **kwargs):
        return self.command(COMMAND_ON, **kwargs)

    def turn_off(self, **kwargs):
        return self.command(COMMAND_OFF, **kwargs)
