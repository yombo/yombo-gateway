from yombo.constants.commands import COMMAND_ON, COMMAND_OFF, COMMAND_CHANNEL_CONTROL, COMMAND_INPUT_CONTROL

from yombo.lib.devices._device import Device


class TV(Device):
    """
    A generic TV device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "tv"
        self.TOGGLE_COMMANDS = [COMMAND_ON, COMMAND_OFF]
        self.FEATURES[COMMAND_CHANNEL_CONTROL] = True
        self.FEATURES[COMMAND_INPUT_CONTROL] = True

    def toggle(self):
        if self.status_history[0].machine_status == 0:
            return self.command(COMMAND_ON)
        else:
            return self.command(COMMAND_OFF)

    def turn_on(self, **kwargs):
        return self.command(COMMAND_ON, **kwargs)

    def turn_off(self, **kwargs):
        return self.command(COMMAND_OFF, **kwargs)
