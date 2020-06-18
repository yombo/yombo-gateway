"""

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devicetypes/platforms/tv.html>`_
"""
from yombo.constants.devicetypes.tv import (COMMAND_CHANNEL_SET, COMMAND_CHANNEL_DOWN, COMMAND_CHANNEL_UP,
                                            INPUT_CHANNEL, INPUT_INPUT)
from yombo.constants.commands import COMMAND_ON, COMMAND_OFF
from yombo.constants.device_commands import DEVICE_COMMAND_INPUTS
from yombo.constants.features import FEATURE_INPUT_CONTROL, FEATURE_CHANNEL_CONTROL
from yombo.constants.platforms import PLATFORM_BASE_TV, PLATFORM_TV

from yombo.lib.devices.device import Device


class TV(Device):
    """
    A generic TV device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = PLATFORM_BASE_TV
        self.PLATFORM = PLATFORM_TV
        self.TOGGLE_COMMANDS = [COMMAND_ON, COMMAND_OFF]
        self.FEATURES[FEATURE_INPUT_CONTROL] = True
        self.FEATURES[FEATURE_CHANNEL_CONTROL] = True

    def toggle(self):
        if self.state_history[0].machine_state == 0:
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
        if DEVICE_COMMAND_INPUTS not in kwargs:
            kwargs[DEVICE_COMMAND_INPUTS] = {}
        kwargs[DEVICE_COMMAND_INPUTS][INPUT_CHANNEL] = channel
        return self.command(COMMAND_CHANNEL_SET, **kwargs)

    def set_input(self, input, **kwargs):
        if DEVICE_COMMAND_INPUTS not in kwargs:
            kwargs[DEVICE_COMMAND_INPUTS] = {}
        kwargs[DEVICE_COMMAND_INPUTS][INPUT_INPUT] = input
        return self.command(COMMAND_CHANNEL_SET, **kwargs)
