"""
Adds support for basic alarm types.
"""
from yombo.constants.features import FEATURE_ALLOW_IN_SCENES
from yombo.constants.commands import COMMAND_ARM, COMMAND_DISARM

from yombo.lib.devices._device import Device


class Alarm(Device):
    """
    A generic fan device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = "alarm"
        self.PLATFORM = "alarm"
        # Put two command machine_labels in a list to enable toggling.
        self.TOGGLE_COMMANDS = [COMMAND_ARM, COMMAND_DISARM]
        self.FEATURES[FEATURE_ALLOW_IN_SCENES] = False

    def toggle(self, **kwargs):
        if self.status_history[0].machine_status == 1:
            return self.command(COMMAND_DISARM)
        else:
            return self.command(COMMAND_ARM)

    def arm(self, **kwargs):
        return self.command(COMMAND_ARM, **kwargs)

    def disarm(self, **kwargs):
        return self.command(COMMAND_DISARM, **kwargs)

    def is_armed(self):
        if self.status_history[0].machine_status == 1:
            return True
        elif self.status_history[0].machine_status == 0:
            return False
        return None

    def is_unarmed(self):
        if self.status_history[0].machine_status == 0:
            return True
        elif self.status_history[0].machine_status == 1:
            return False
        return None

    def generate_human_status(self, machine_status, machine_status_extra):
        if machine_status == 1:
            return "Unarmed"
        return "Disarmed"

    def generate_human_message(self, machine_status, machine_status_extra):
        human_status = self.generate_human_status(machine_status, machine_status_extra)
        return "%s is now %s" % (self.area_label, human_status)
