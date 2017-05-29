"""
Validation of NoneType or string with "none" or string that's empty.
"""
from yombo.lib.inputtypes._input_type import Input_Type


class _None(Input_Type):

    def validate(self, value, **kwargs):
        if isinstance(value, None):
            return value
        if isinstance(value, str) and value == "":
            return value
        raise AssertionError("Value is not NoneType or empty.")
