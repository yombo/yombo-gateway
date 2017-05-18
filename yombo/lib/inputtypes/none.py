"""
Validation of floats. Optionally, will try to convert the input to a float if allowed.
"""
from yombo.ext.six import string_types

from yombo.lib.inputtypes._input_type import Input_Type


class _None(Input_Type):

    def validate(self, value, **kwargs):
        if isinstance(value, None):
            return value
        if isinstance(value, string_types) and value == "":
            return value
        raise AssertionError("Value is not NoneType or empty.")
