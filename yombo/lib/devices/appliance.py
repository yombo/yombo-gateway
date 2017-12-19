from yombo.lib.devices._device import Device

#TODO: rename to switch
class Appliance(Device):
    """
    A generic appliance device.
    """

    PLATFORM = "appliance"

    TOGGLE_COMMANDS = ['on', 'off']  # Put two command machine_labels in a list to enable toggling.

    def can_toggle(self):
        return True

    def toggle(self):
        if self.status_history[0].machine_state == 0:
            return self.command('on')
        else:
            return self.command('off')
