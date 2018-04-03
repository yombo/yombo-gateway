# Yombo Constants
from yombo.constants.commands import COMMAND_LOCK, COMMAND_UNLOCK

from yombo.lib.devices._device import Device


class Lock(Device):
    """
    A generic fan device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "lock"
        # Put two command machine_labels in a list to enable toggling.
        self.TOGGLE_COMMANDS = [COMMAND_LOCK, COMMAND_UNLOCK]

    def toggle(self, **kwargs):
        if self.status_history[0].machine_status == 0:
            return self.command(COMMAND_LOCK)
        else:
            return self.command(COMMAND_UNLOCK)

    def turn_on(self, **kwargs):
        return self.command(COMMAND_LOCK, **kwargs)

    def turn_off(self, **kwargs):
        return self.command(COMMAND_UNLOCK, **kwargs)

    def is_locked(self):
        if self.status_history[0].machine_status == 1:
            return True
        elif self.status_history[0].machine_status == 0:
            return False
        return None

    def is_unlocked(self):
        if self.status_history[0].machine_status == 0:
            return True
        elif self.status_history[0].machine_status == 1:
            return False
        return None

    def generate_human_status(self, machine_status, machine_status_extra):
        if machine_status == 1:
            return "Locked"
        return "Unlocked"

    def generate_human_message(self, machine_status, machine_status_extra):
        human_status = self.generate_human_status(machine_status, machine_status_extra)
        return "%s is now %s" % (self.area_label, human_status)
