"""
A cover can be a window blind, garage door, shed door, a door.

A cover is considered open if the status is 0, close if it's 1.
"""

from yombo.constants.commands import COMMAND_OPEN, COMMAND_CLOSE
from yombo.constants.features import FEATURE_ALLOW_IN_SCENES
from yombo.constants.status_extra import STATUS_EXTRA_PERCENT

from yombo.lib.devices._device import Device


class Cover(Device):
    """
    A generic cover device. This device shouldn't be used directly when possible.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = "cover"
        self.PLATFORM = "cover"
        # Put two command machine_labels in a list to enable toggling.
        self.TOGGLE_COMMANDS = [COMMAND_OPEN, COMMAND_CLOSE]
        self.FEATURES[FEATURE_ALLOW_IN_SCENES] = False
        self.STATUS_EXTRA[STATUS_EXTRA_PERCENT] = True

    def toggle(self, **kwargs):
        if self.status_history[0].machine_status == 0:
            return self.command(COMMAND_OPEN)
        else:
            return self.command(COMMAND_CLOSE)

    def close(self, **kwargs):
        return self.command(COMMAND_OPEN, **kwargs)

    def open(self, **kwargs):
        return self.command(COMMAND_CLOSE, **kwargs)

    def is_closed(self):
        if self.machine_status == 1:
            return True
        elif self.machine_status == 0:
            return False
        return None

    def is_open(self):
        if self.machine_status == 1:
            return False
        elif self.machine_status == 0:
            return True
        return None

    def generate_human_status(self, machine_status, machine_status_extra):
        if machine_status == 1:
            return "Opened"
        return "Closed"

    def generate_human_message(self, machine_status, machine_status_extra):
        human_status = self.generate_human_status(machine_status, machine_status_extra)
        return "%s is now %s" % (self.area_label, human_status)


class Door(Cover):
    """
    A door that can be controlled.
    """
    def _init_(self):
        super()._init_()
        self.PLATFORM = "door"


class Garage_Door(Cover):
    """
    A garage door cover type.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "garage_door"
        # Put two command machine_labels in a list to enable toggling.
        self.TOGGLE_COMMANDS = [COMMAND_OPEN, COMMAND_CLOSE]

    def toggle(self, **kwargs):
        if self.status_history[0].machine_status == 0:
            return self.command(COMMAND_OPEN)
        else:
            return self.command(COMMAND_CLOSE)

    def turn_on(self, **kwargs):
        return self.command(COMMAND_OPEN, **kwargs)

    def turn_off(self, **kwargs):
        return self.command(COMMAND_CLOSE, **kwargs)

    def is_closed(self):
        if self.status_history[0].machine_status == 1:
            return True
        elif self.status_history[0].machine_status == 0:
            return False
        return None

    def is_unlocked(self):
        return not self.is_closed()

    def generate_human_status(self, machine_status, machine_status_extra):
        if machine_status == 1:
            return "Opened"
        return "Closed"

    def generate_human_message(self, machine_status, machine_status_extra):
        human_status = self.generate_human_status(machine_status, machine_status_extra)
        return "%s is now %s" % (self.area_label, human_status)


class Window(Cover):
    """
    A window that can be controlled.
    """
    def _init_(self):
        super()._init_()
        self.PLATFORM = "window"