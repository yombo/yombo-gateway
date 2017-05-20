
from yombo.lib.devices._device import Device

class Light(Device):
    """
    A generic light device.
    """

    PLATFORM = "light"

    SUPPORT_BRIGHTNESS = True
    SUPPORT_ALL_ON = True
    SUPPORT_ALL_OFF = True
    SUPPORT_COLOR = False
    SUPPORT_COLOR_MODE = None  # rgb....
    SUPPORT_PINGABLE = True
    SUPPORT_BROADCASTS_UPDATES = True
    SUPPORT_NUMBER_OF_STEPS = 4096

    TOGGLE_COMMANDS = ['on', 'off']  # Put two command machine_labels in a list to enable toggling.

    def can_toggle(self):
        return True

    def toggle(self):
        if self.status_history[0].machine_state == 0:
            return self.command('on')
        else:
            return self.command('off')
