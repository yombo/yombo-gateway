from yombo.lib.devices._device import Device


class Fan(Device):
    """
    A generic fan device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "fan"
        self.TOGGLE_COMMANDS = ['on', 'off']  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            'all_on': False,
            'all_off': False,
            'pingable': True,
            'pollable': True,
            'sends_updates': False,
            'number_of_steps': 4  # # 0 = off, 4 = high
        })

    def toggle(self, **kwargs):
        if self.status_history[0].machine_status == 0:
            if 'previous_on_speed' in self.meta:
                return self.command('on', inputs={'speed': self.meta['previous_on_speed']})
            else:
                return self.command('on', inputs={'speed': 4})
        else:
            return self.command('off')

    def turn_on(self, **kwargs):
        return self.command('on', **kwargs)

    def turn_off(self, **kwargs):
        return self.command('off', **kwargs)
