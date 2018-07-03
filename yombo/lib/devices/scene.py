"""
Scene devices are used when a scene resides on another automation controller. Yombo
can trigger that scene mode using a module.
"""
from yombo.constants.features import (FEATURE_ALL_ON, FEATURE_ALL_OFF, FEATURE_PINGABLE,
                                      FEATURE_POLLABLE, FEATURE_ALLOW_IN_SCENES)
from yombo.constants.commands import COMMAND_ENABLE, COMMAND_DISABLE, COMMAND_TRIGGER
from yombo.constants.platforms import PLATFORM_BASE_SCENE, PLATFORM_SCENE
from yombo.lib.devices._device import Device


class Scene(Device):
    """
    A generic fan device.
    """
    TOGGLE_COMMANDS = []  # Put two command machine_labels in a list to enable toggling.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = PLATFORM_BASE_SCENE
        self.PLATFORM = PLATFORM_SCENE
        self.TOGGLE_COMMANDS = None  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            FEATURE_ALL_ON: False,
            FEATURE_ALL_OFF: False,
            FEATURE_PINGABLE: False,
            FEATURE_POLLABLE: False,
            FEATURE_ALLOW_IN_SCENES: True,
        })

    def toggle(self):
        return

    def disable(self, **kwargs):
        return self.command(COMMAND_DISABLE, **kwargs)

    def enable(self, **kwargs):
        return self.command(COMMAND_ENABLE, **kwargs)

    def trigger(self, **kwargs):
        return self.command(COMMAND_TRIGGER, **kwargs)
