from yombo.constants.commands import COMMAND_ON, COMMAND_OFF, COMMAND_STOP, COMMAND_PAUSE, COMMAND_START
from yombo.constants.platforms import PLATFORM_BASE_MEDIA_PLAYER, PLATFORM_MEDIAPLAYER

from yombo.lib.devices._device import Device


class Media_Player(Device):
    """
    A generic TV device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = PLATFORM_BASE_MEDIA_PLAYER
        self.PLATFORM = PLATFORM_MEDIAPLAYER
        self.TOGGLE_COMMANDS = [COMMAND_START, COMMAND_PAUSE]

    def toggle(self):
        if self.status_history[0].machine_status == 0:
            return self.command(COMMAND_ON)
        else:
            return self.command(COMMAND_OFF)

    def turn_on(self, **kwargs):
        return self.command(COMMAND_ON, **kwargs)

    def stop(self, **kwargs):
        return self.command(COMMAND_STOP, **kwargs)

    def start(self, **kwargs):
        return self.command(COMMAND_START, **kwargs)

    def pause(self, **kwargs):
        return self.command(COMMAND_PAUSE, **kwargs)
