from yombo.lib.devices._device import Device


class Thermometer(Device):
    """
    A generic Sensor
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "thermometer"
        self.TOGGLE_COMMANDS = []
        self.FEATURES.update({
            'all_on': False,
            'all_off': False,
            'pingable': False,
            'pollable': True,
            'sends_updates': False
        })

    def can_toggle(self):
        return False

    def toggle(self):
        return

    def command_from_status(self, machine_status, machine_status_extra=None):
        """
        Attempt to find a command based on the status of a device.
        :param machine_status:
        :return:
        """
        return None
