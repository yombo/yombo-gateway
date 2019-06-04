"""
Adds support for basic alarm types.
"""
from yombo.constants.features import FEATURE_ALLOW_IN_SCENES
from yombo.constants.devicetypes.alarm import (COMMAND_ARM_AWAY, COMMAND_ARM_CUSTOM_BYPASS, COMMAND_ARM_HOME,
                                               COMMAND_ARM_NIGHT, COMMAND_DISARM, INPUT_BYPASS)
from yombo.constants.commands import COMMAND_COMPONENT_INPUTS
from yombo.constants.platforms import PLATFORM_BASE_ALARM, PLATFORM_ALARM

from yombo.lib.devices._device import Device


class Alarm(Device):
    """
    A generic fan device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = PLATFORM_BASE_ALARM
        self.PLATFORM = PLATFORM_ALARM
        # Put two command machine_labels in a list to enable toggling.
        self.TOGGLE_COMMANDS = [COMMAND_ARM_AWAY, COMMAND_DISARM]
        self.FEATURES[FEATURE_ALLOW_IN_SCENES] = False

    def toggle(self, **kwargs):
        if self.status_history[0].machine_status == 1:
            return self.command(COMMAND_DISARM)
        else:
            return self.command(COMMAND_ARM_AWAY)

    def arm_away(self, **kwargs):
        return self.command(COMMAND_ARM_AWAY, **kwargs)

    def arm_home(self, **kwargs):
        return self.command(COMMAND_ARM_HOME, **kwargs)

    def arm_night(self, **kwargs):
        return self.command(COMMAND_ARM_NIGHT, **kwargs)

    def disarm(self, **kwargs):
        return self.command(COMMAND_DISARM, **kwargs)

    def bypass(self, zones, **kwargs):
        """
        Bypass (disable) zones of an alarm system.

        :param zones:
        :param kwargs:
        :return:
        """
        if COMMAND_COMPONENT_INPUTS not in kwargs:
            kwargs[COMMAND_COMPONENT_INPUTS] = {}
        kwargs[COMMAND_COMPONENT_INPUTS][INPUT_BYPASS] = zones
        return self.command(COMMAND_ARM_CUSTOM_BYPASS, **kwargs)

    @property
    def is_armed(self):
        if self.status_history[0].machine_status == 1:
            return True
        elif self.status_history[0].machine_status == 0:
            return False
        return None

    @property
    def is_unarmed(self):
        if self.status_history[0].machine_status == 0:
            return True
        elif self.status_history[0].machine_status == 1:
            return False
        return None

    def generate_human_state(self, machine_status, machine_status_extra):
        if machine_status == 1:
            return _("state::alarm_control_panel::armed", "Armed")
        return _("state::alarm_control_panel::disarmed", "Disarmed")
