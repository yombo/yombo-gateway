"""
A cover can be a window blind, garage door, shed door, a door.

A cover is considered open if the state is 0, close if it's 1.
"""

from yombo.constants.commands import COMMAND_OPEN, COMMAND_CLOSE
from yombo.constants.features import FEATURE_ALLOW_IN_SCENES
from yombo.constants.platforms import (PLATFORM_BASE_COVER, PLATFORM_COVER, PLATFORM_DOOR, PLATFORM_GARAGE_DOOR,
    PLATFORM_WINDOW)
from yombo.constants.status_extra import STATUS_EXTRA_PERCENT

from yombo.lib.devices._device import Device


class Cover(Device):
    """
    A generic cover device. This device shouldn't be used directly when possible.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = PLATFORM_BASE_COVER
        self.PLATFORM = PLATFORM_COVER
        # Put two command machine_labels in a list to enable toggling.
        self.TOGGLE_COMMANDS = [COMMAND_OPEN, COMMAND_CLOSE]
        self.FEATURES[FEATURE_ALLOW_IN_SCENES] = False
        self.MACHINE_STATUS_EXTRA_FIELDS[STATUS_EXTRA_PERCENT] = True

    def toggle(self, **kwargs):
        if self.machine_state == 0:
            return self.command(COMMAND_OPEN)
        else:
            return self.command(COMMAND_CLOSE)

    def close(self, **kwargs):
        return self.command(COMMAND_OPEN, **kwargs)

    def open(self, **kwargs):
        return self.command(COMMAND_CLOSE, **kwargs)

    @property
    def is_closed(self):
        if self.machine_state == 1:
            return True
        elif self.machine_state == 0:
            return False
        return None

    @property
    def is_open(self):
        if self.machine_state == 1:
            return False
        elif self.machine_state == 0:
            return True
        return None

    def generate_human_state(self, machine_state, machine_state_extra):
        if machine_state == 1:
            return "Opened"
        return "Closed"


class Door(Cover):
    """
    A door that can be controlled.
    """
    def _init_(self):
        super()._init_()
        self.PLATFORM = PLATFORM_DOOR


class Garage_Door(Cover):
    """
    A garage door cover type.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = PLATFORM_GARAGE_DOOR


class Window(Cover):
    """
    A window that can be controlled.
    """
    def _init_(self):
        super()._init_()
        self.PLATFORM = PLATFORM_WINDOW
