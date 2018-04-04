from yombo.constants.features import FEATURE_ALLOW_IN_SCENES
from yombo.constants.commands import COMMAND_LOCK, COMMAND_UNLOCK

from yombo.lib.devices._device import Device


class Lock(Device):
    """
    A generic fan device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = "lock"
        self.PLATFORM = "lock"
        # Put two command machine_labels in a list to enable toggling.
        self.TOGGLE_COMMANDS = [COMMAND_LOCK, COMMAND_UNLOCK]
        self.FEATURES[FEATURE_ALLOW_IN_SCENES] = False

    def toggle(self, **kwargs):
        if self.status_history[0].machine_status == 0:
            return self.command(COMMAND_LOCK)
        else:
            return self.command(COMMAND_UNLOCK)

    def lock(self, **kwargs):
        return self.command(COMMAND_LOCK, **kwargs)

    def unlock(self, **kwargs):
        return self.command(COMMAND_UNLOCK, **kwargs)

    @property
    def is_locked(self):
        if self.status_history[0].machine_status == 1:
            return True
        elif self.status_history[0].machine_status == 0:
            return False
        return None

    @property
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
