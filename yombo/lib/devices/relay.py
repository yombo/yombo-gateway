from yombo.lib.devices.appliance import Appliance


class Relay(Appliance):
    """
    A generic relay device.
    """

    PLATFORM = "relay"

    SUPPORT_ALL_ON = False
    SUPPORT_ALL_OFF = False

    TOGGLE_COMMANDS = ['open', 'close']  # Put two command machine_labels in a list to enable toggling.

    # Features this device can support
    FEATURES = {
        'all_on': False,
        'all_off': False,
        'pingable': False,
        'pollable': False,
        'sends_updates': False
    }

    def can_toggle(self):
        return True

    def toggle(self):
        if self.status_history[0].machine_state == 0:
            return self.command('open')
        else:
            return self.command('close')

    def command_from_status(self, machine_status, machine_status_extra=None):
        """
        Attempt to find a command based on the status of a device.
        :param machine_status:
        :return:
        """
        # print("attempting to get command_from_status - relay: %s - %s" % (machine_status, machine_status_extra))
        if machine_status == int(1):
            return self._Commands['on']
        elif machine_status == int(0):
            return self._Commands['off']
        return None
