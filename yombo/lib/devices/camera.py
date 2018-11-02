"""
Various camera type devices.
"""
from yombo.constants.features import (FEATURE_NUMBER_OF_STEPS, FEATURE_ALL_ON, FEATURE_ALL_OFF, FEATURE_PINGABLE,
                                      FEATURE_POLLABLE, FEATURE_ALLOW_IN_SCENES, FEATURE_DETECTS_MOTION)
from yombo.constants.commands import COMMAND_STOP, COMMAND_RECORD, COMMAND_ON, COMMAND_OFF
from yombo.constants.platforms import PLATFORM_BASE_CAMERA, PLATFORM_CAMERA
from yombo.constants.status_extra import SEVALUE_IDLE, SEVALUE_RECORDING
from yombo.lib.devices._device import Device
from yombo.utils.datatypes import coerce_value


class Camera(Device):
    """
    A generic camera device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = PLATFORM_BASE_CAMERA
        self.PLATFORM = PLATFORM_CAMERA
        self.TOGGLE_COMMANDS = [COMMAND_ON, COMMAND_OFF]  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            FEATURE_ALL_ON: False,
            FEATURE_ALL_OFF: False,
            FEATURE_PINGABLE: True,
            FEATURE_POLLABLE: True,
            FEATURE_NUMBER_OF_STEPS: 2,
            FEATURE_ALLOW_IN_SCENES: False,
            FEATURE_DETECTS_MOTION: False,
        })

        # self.MACHINE_STATUS_EXTRA_FIELDS["mode"] = ["idle", "streaming", "recording"]

    def toggle(self):
        if self.status_history[0].machine_status == SEVALUE_IDLE:
            return self.command(COMMAND_RECORD)
        elif self.status_history[0].machine_status == SEVALUE_RECORDING:
            return self.commandCOMMAND_STOP

    def turn_on(self, **kwargs):
        return self.command(COMMAND_RECORD, **kwargs)

    def turn_off(self, **kwargs):
        return self.command(COMMAND_STOP, **kwargs)

    @property
    def motion_detection(self):
        return self.FEATURES[FEATURE_DETECTS_MOTION]

    @motion_detection.setter
    def motion_detection(self, val):
        if isinstance(val, bool):
            self.FEATURES[FEATURE_DETECTS_MOTION] = val
        else:
            try:
                self.FEATURES[FEATURE_DETECTS_MOTION] = coerce_value(val, "boolean")
            except Exception:
                pass
