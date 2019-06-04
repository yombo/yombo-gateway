from yombo.constants.features import FEATURE_ALLOW_IN_SCENES
from yombo.constants.commands import COMMAND_LOCK, COMMAND_UNLOCK
from yombo.constants.platforms import PLATFORM_BASE_LOCK, PLATFORM_LOCK

from yombo.lib.devices._device import Device


class Lock(Device):
    """
    A generic fan device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = PLATFORM_BASE_LOCK
        self.PLATFORM = PLATFORM_LOCK
        # Put two command machine_labels in a list to enable toggling.
        self.TOGGLE_COMMANDS = [COMMAND_LOCK, COMMAND_UNLOCK]
        self.FEATURES[FEATURE_ALLOW_IN_SCENES] = False

    def toggle(self, **kwargs):
        if self.state_history[0].machine_state == 0:
            return self.command(COMMAND_LOCK)
        else:
            return self.command(COMMAND_UNLOCK)

    def lock(self, **kwargs):
        return self.command(COMMAND_LOCK, **kwargs)

    def unlock(self, **kwargs):
        return self.command(COMMAND_UNLOCK, **kwargs)

    @property
    def is_locked(self):
        if self.state_history[0].machine_state == 1:
            return True
        elif self.state_history[0].machine_state == 0:
            return False
        return None

    @property
    def is_unlocked(self):
        if self.state_history[0].machine_state == 0:
            return True
        elif self.state_history[0].machine_state == 1:
            return False
        return None

    def generate_human_state(self, machine_state, machine_state_extra):
        if machine_state == 1:
            return _("state::lock::locked", "Locked")
        return _("state::lock::unlocked", "Unlocked")

