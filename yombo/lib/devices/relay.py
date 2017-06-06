from yombo.lib.devices.appliance import Appliance


class Relay(Appliance):
    """
    A generic relay device.
    """

    PLATFORM = "relay"

    SUPPORT_ALL_ON = False
    SUPPORT_ALL_OFF = False

    TOGGLE_COMMANDS = ['open', 'close']  # Put two command machine_labels in a list to enable toggling.

    def can_toggle(self):
        return True

    def toggle(self):
        if self.status_history[0].machine_state == 0:
            return self.command('open')
        else:
            return self.command('close')
