from yombo.lib.devices._device import Device


class Thermometer(Device):
    """
    A generic Sensor
    """

    PLATFORM = "thermometer"

    SUPPORT_ALL_ON = False
    SUPPORT_ALL_OFF = False

    TOGGLE_COMMANDS = []

    # Features this device can support
    FEATURES = {
        'all_on': False,
        'all_off': False,
        'pingable': False,
        'pollable': True,
        'sends_updates': False
    }

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
