"""
Various checks to ensure inputs are various Yombo based items. All validators
will return the id of the item unless either: 

1) An instance was passed it. This instance is checked for proper class type and it's returned
2) The argument "instance" is set to True.

"""
import inspect

from yombo.lib.inputtypes.input_type import InputType
from yombo.lib.inputtypes.platforms.basic_types import String_
from yombo.lib.commands import Command


class VoiceCommand(String_):
    pass


class YomboCommand(InputType):

    def validate(self, value, instance=None, **kwargs):
        """Validate that value is a real yombo command."""
        if inspect.isclass(value):
            if isinstance(value, Command):
                return value
            else:
                raise ValueError("Passed in an unknown object")

        try:
            the_item = self._Parent._Commands.get(value)
            if instance is True:
                return the_item
            else:
                return the_item.device_id
        except Exception as e:
            raise AssertionError("Value is not a valid yombo command.")


class YomboDeviceType(InputType):

    def validate(self, value, instance=None, **kwargs):
        """Validate that value is a real yombo device type."""
        if inspect.isclass(value):
            from yombo.lib.devicetypes import DeviceType
            if isinstance(value, DeviceType):
                return value
            else:
                raise ValueError("Passed in an unknown object")

        try:
            the_item = self._Parent._DeviceTypes.get(value)
            if instance is True:
                return the_item
            else:
                return the_item.device_id
        except Exception as e:
            raise AssertionError("Value is not a valid yombo device type.")


class YomboDevice(InputType):
    """
    Validate requested value is a device. Will return
    """
    def validate(self, value, instance=None, **kwargs):
        """Validate that value is a real device."""
        if inspect.isclass(value):
            from yombo.lib.devices.device import Device
            if isinstance(value, Device):
                return value
            else:
                raise ValueError("Passed in an unknown object")

        try:
            the_item = self._Parent._Devices.get(value)
            if instance is True:
                return the_item
            else:
                return the_item.device_id
        except Exception as e:
            raise AssertionError(f"Value is not a valid yombo device ({e}).")


class YomboModule(InputType):

    def validate(self, value, instance=None, **kwargs):
        """Validate that value is a real yombo device type."""
        if inspect.isclass(value):
            from yombo.core.module import YomboModule
            if isinstance(value, YomboModule):
                return value
            else:
                raise ValueError("Passed in an unknown object")

        try:
            the_item = self._Parent._Modules.get(value)
            if instance is True:
                return the_item
            else:
                return the_item.device_id
        except Exception as e:
            raise AssertionError("Value is not a valid yombo module.")
