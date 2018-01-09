from yombo.lib.devices.switch import Switch

#TODO: rename to switch
class Appliance(Switch):
    """
    A generic appliance device, acts like a switch.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "appliance"

