from yombo.constants.commands import (COMMAND_ON, COMMAND_OFF, COMMAND_CHANNEL_SET, COMMAND_CHANNEL_DOWN,
                                      COMMAND_CHANNEL_UP)
from yombo.constants.features import FEATURE_INPUT_CONTROL, FEATURE_CHANNEL_CONTROL

from yombo.lib.devices._device import Device


class TV(Device):
    """
    A generic TV device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = "tv"
        self.PLATFORM = "tv"
        self.TOGGLE_COMMANDS = [COMMAND_ON, COMMAND_OFF]
        self.FEATURES[FEATURE_INPUT_CONTROL] = True
        self.FEATURES[FEATURE_CHANNEL_CONTROL] = True

    def toggle(self):
        if self.status_history[0].machine_status == 0:
            return self.command(COMMAND_ON)
        else:
            return self.command(COMMAND_OFF)

    def turn_on(self, **kwargs):
        return self.command(COMMAND_ON, **kwargs)

    def turn_off(self, **kwargs):
        return self.command(COMMAND_OFF, **kwargs)

    def channel_up(self, **kwargs):
        return self.command(COMMAND_CHANNEL_UP, **kwargs)

    def channel_down(self, **kwargs):
        return self.command(COMMAND_CHANNEL_DOWN, **kwargs)

    def set_channel(self, channel, **kwargs):
        if 'inputs' not in kwargs:
            kwargs['inputs'] = {}
        kwargs['channel'] = channel
        return self.command(COMMAND_CHANNEL_SET, **kwargs)

    def set_input(self, input, **kwargs):
        if 'inputs' not in kwargs:
            kwargs['inputs'] = {}
        kwargs['input'] = input
        return self.command(COMMAND_CHANNEL_SET, **kwargs)
