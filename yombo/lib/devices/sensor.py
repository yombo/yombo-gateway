from yombo.lib.devices._device import Device


class Sensor(Device):
    """
    A generic Sensor
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "sensor"
        self.TOGGLE_COMMANDS = []  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            'all_on': False,
            'all_off': False,
            'pingable': False,
            'pollable': True,
            'number_of_steps': 2,
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
        # print("attempting to get command_from_status - Sensor: %s - %s" % (machine_status, machine_status_extra))
        if machine_status == int(1):
            return self._Parent._Commands['high']
        elif machine_status == int(0):
            return self._Parent._Commands['low']
        return None

class Digital_Sensor(Sensor):
    """
    A sensor that will be either high or low.
    """
    def _init_(self):
        super()._init_()
        self.PLATFORM = "digital_sensor"


class Door(Sensor):
    """
    A sensor that will be either high or low.
    """
    def _init_(self):
        super()._init_()
        self.PLATFORM = "door"

class Thermometer(Device):
    """
    A generic Sensor
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "thermometer"
        self.temperature_unit = 'c'  # what temperature unit the device works in.

    @property
    def temperature(self):
        """
        Return the temperatures of this thermometer.
        """
        if len(self.status_history) > 0:
            return self.status_history[0].machine_status
        return None

    def command_from_status(self, machine_status, machine_status_extra=None):
        """
        Attempt to find a command based on the status of a device.
        :param machine_status:
        :return:
        """
        return None

class Window(Sensor):
    """
    A sensor that will be either high or low.
    """
    def _init_(self):
        super()._init_()
        self.PLATFORM = "window"

