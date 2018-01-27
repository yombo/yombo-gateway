import re
from string import hexdigits

from yombo.lib.inputtypes.input_type import Input_Type
from yombo.lib.inputtypes.basic_types import _Integer, _String


class X10_Address(Input_Type):
    """
    Always returns the value provided.
    """
    regex = re.compile(r'([A-Pa-p]{1})(?:[2-9]|1[0-6]?)$')

    def validate(self, value, **kwargs):
        if isinstance(value, str) is False:
            raise AssertionError("X10_Address was expecting a string")
        if not self.regex.match(value):
            raise AssertionError('Invalid X10 Address')
        return value


class X10_House(_String):
    """
    Always returns the value provided.
    """
    ALLOW_NONE = True

    regex = re.compile(r'([A-Pa-p]{1})$')

    def validate(self, value, **kwargs):
        if isinstance(value, str) is False:
            raise AssertionError("X10_House was expecting a string")
        if not self.regex.match(value):
            raise AssertionError('Invalid X10 House')
        return value


class X10_Unit(_Integer):
    """
    Returns the value provided as an int.
    """
    MIN = 1
    MAX = 16

    def validate(self, value, **kwargs):
        try:
            value = int(value)
        except Exception as e:
            raise AssertionError("X10_Unit expects a value between 1 and 16.")

        self.check_min_max(value, **kwargs)
        return value


class Insteon_Address(_String):
    MIN = 8
    MAX = 8
    CONVERT = False

    def validate(self, value, **kwargs):
        parts = value.split(".")
        if len(parts) != 3:
            AssertionError("Insteon address has three hex parts of 2 characters. Example: 5D.E1.93")
        for part in parts:
            if len(part) != 2:
                AssertionError("Insteon address has three hex parts of 2 characters. Example: 5D.E1.94")
            if all(c in hexdigits for c in part) is False:
                AssertionError("Insteon address has three hex parts of 2 characters, must be in hex range (0-F)")
        self.check_min_max(value, **kwargs)
        return value
