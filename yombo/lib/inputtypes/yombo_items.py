"""
Various checks to ensure inputs are various Yombo based items. All validators
will return the id of the item unless either: 

1) An instance was passed it. This instance is checked for proper class type and it's returned
2) The argument "get_object" is set to True.

"""
import inspect
from yombo.lib.inputtypes.input_type import Input_Type


from yombo.lib.commands import Command
class Yombo_Command(Input_Type):

    def validate(self, value, get_object=None, **kwargs):
        """Validate that value is a real yombo command."""
        if inspect.isclass(value):
            if isinstance(value, Command):
                return value
            else:
                raise ValueError("Passed in an unknown object")

        try:
            the_item = self._Parent._Commands.get(value)
            if get_object is True:
                return the_item
            else:
                return the_item.device_id
        except Exception as e:
            raise AssertionError("Value is not a valid yombo command.")


from yombo.lib.devicetypes import DeviceType
class Yombo_Device_Type(Input_Type):

    def validate(self, value, get_object=None, **kwargs):
        """Validate that value is a real yombo device type."""
        if inspect.isclass(value):
            if isinstance(value, DeviceType):
                return value
            else:
                raise ValueError("Passed in an unknown object")

        try:
            the_item = self._Parent._DeviceTypes.get(value)
            if get_object is True:
                return the_item
            else:
                return the_item.device_id
        except Exception as e:
            raise AssertionError("Value is not a valid yombo device type.")



from yombo.lib.devices._device import Device
class Yombo_Device(Input_Type):
    """
    Validate requested value is a device. Will return
    """
    def validate(self, value, get_object=None, **kwargs):
        """Validate that value is a real device."""
        if inspect.isclass(value):
            if isinstance(value, Device):
                return value
            else:
                raise ValueError("Passed in an unknown object")

        try:
            the_item = self._Parent._Devices.get(value)
            if get_object is True:
                return the_item
            else:
                return the_item.device_id
        except Exception as e:
            raise AssertionError("Value is not a valid yombo device (%s)." % e)


from yombo.core.module import YomboModule
class Yombo_Module(Input_Type):

    def validate(self, value, get_object=None, **kwargs):
        """Validate that value is a real yombo device type."""
        if inspect.isclass(value):
            if isinstance(value, YomboModule):
                return value
            else:
                raise ValueError("Passed in an unknown object")

        try:
            the_item = self._Parent._Modules.get(value)
            if get_object is True:
                return the_item
            else:
                return the_item.device_id
        except Exception as e:
            raise AssertionError("Value is not a valid yombo module.")


class Voice_Command(Input_Type):

    def validate(self, value, **kwargs):
        if value in self._Parent._VoiceCmds:
            return value
        raise AssertionError("Invalid voice command input.")
