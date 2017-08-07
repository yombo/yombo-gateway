from yombo.lib.devices._device import Device


class Sensor(Device):
    """
    A generic Sensor
    """

    PLATFORM = "sensor"

    SUPPORT_ALL_ON = False
    SUPPORT_ALL_OFF = False

    TOGGLE_COMMANDS = []

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
        print("attempting to get command_from_status - Sensor: %s - %s" % (machine_status, machine_status_extra))
        # print("attempting to get command_from_status - Sensor machine status: %s" % (machine_status, type(machine_status)))
        if machine_status == int(1):
            return self._Parent._Commands['high']
        elif machine_status == int(0):
            return self._Parent._Commands['low']
        return None

class DigitalSensor(Sensor):
    """
    A sensor that will be either high or low.
    """

    SUB_PLATFORM = "digital_sensor"
