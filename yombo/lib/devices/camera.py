from yombo.lib.devices._device import Device


class Camera(Device):
    """
    A generic camera device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "camera"
        self.TOGGLE_COMMANDS = ['on', 'off']  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            'all_on': False,
            'all_off': False,
            'pingable': True,
            'pollable': True,
            'sends_updates': False,
            'detects_motion': False,
        })

        # self.STATUS_EXTRA['mode'] = ['idle', 'streaming', 'recording']

    def toggle(self):
        if self.status_history[0].machine_status == 'idle':
            return self.command('record')
        elif self.status_history[0].machine_status == 'recording':
            return self.command('stop')

    def turn_on(self, **kwargs):
        return self.command('record', **kwargs)

    def turn_off(self, **kwargs):
        return self.command('stop', **kwargs)

    @property
    def motion_detection(self):
        return self.FEATURES['detects_motion']

    @motion_detection.setter
    def motion_detection(self, val):
        self.FEATURES['detects_motion'] = val
