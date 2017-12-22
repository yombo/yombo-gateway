from typing import Any, Union, TypeVar, Callable, Sequence, Dict

from yombo.lib.inputtypes.input_type import Input_Type


class _Any(Input_Type):
    """
    Always returns the value provided.
    """
    def validate(self, value, **kwargs):
        return value


class _Bool(Input_Type):
    """
    Validation of a bool. Tries to coerce to bool if it's not.
    """
    MIN = None
    MAX = None

    def validate(self, value: Any, **kwargs) -> bool:
        """Validate and coerce a boolean value."""
        if isinstance(value, bool):
            return value
        if self.CONVERT is False:
            raise AssertionError("Value is not a boolean.")

        value = value.lower()
        if value in (1, '1', 'true', 'yes', 'on', 'enable'):
            return True
        if value in (0, '0', 'false', 'no', 'off', 'disable'):
            return False
        raise AssertionError("Value is not a boolean.")


class _Checkbox(Input_Type):
    """
    AKA bool, but for people.
    """
    MIN = None
    MAX = None

    def validate(self, value: Any, **kwargs) -> bool:
        """Validate and coerce a boolean value."""
        if isinstance(value, bool):
            return value
        if self.CONVERT is False:
            raise AssertionError("Value is not a boolean.")

        value = value.lower()
        if value in (1, '1', 'true', 'yes', 'on', 'enable'):
            return True
        if value in (0, '0', 'false', 'no', 'off', 'disable'):
            return False
        raise AssertionError("Value is not a boolean.")


class _Integer(Input_Type):
    """
    Validation if integers. Will try to coerce to int if it's not.
    """
    MIN = None
    MAX = None

    def validate(self, value, **kwargs):
        if isinstance(value, int) is False:
            if self.CONVERT is True:
                try:
                    value = int(value)
                except:
                    if value == "":
                        return None
                    raise AssertionError("Input is not an int.")
        self.check_min_max(value, **kwargs)
        return value

class Filename(Input_Type):
    """
    Very basic filename validator.
    """
    MIN = 3
    MAX = 256

    def validate(self, value, **kwargs):
        if isinstance(value, bytes) is True:
            if self.CONVERT is False:
                raise AssertionError("Input is bytes, only strings allowed.")
            else:
                try:
                    value = value.decode("utf-8")
                except:
                    raise AssertionError("Unable to convert input to string, from bytes.")
        if isinstance(value, str) is False:
            raise AssertionError("Input must be string.")
        valid_chars = "-_.() /%s%s" % (string.ascii_letters, string.digits)
        for char in value:
            if char not in valid_chars:
                raise AssertionError("Input has invalid character: %s" % char)
        self.check_min_max(value, **kwargs)
        return value

class _Float(Input_Type):
    """
    Validation of floats. Optionally, will try to convert the input to a float if allowed.
    """
    def validate(self, value, **kwargs):
        if isinstance(value, float) is False:
            if self.CONVERT is True:
                try:
                    value = float(value)
                except:
                    raise AssertionError("Input is not a float.")
        self.check_min_max( value, **kwargs)
        return value


class _None(Input_Type):
    """
    Validation of NoneType or string with "none" or string that's empty.
    """
    def validate(self, value, **kwargs):
        if isinstance(value, None):
            return value
        if self.CONVERT is False:
            raise AssertionError("Value is not NoneType or empty.")
        if isinstance(value, str):
            if value.lower() == 'none' or value == "":
                return None
        raise AssertionError("Value is not NoneType or empty.")


class Number(_Integer):
    """
    Anything that can be represented as either an int or a float.
    """
    def validate(self, value, **kwargs):
        if isinstance(value, int) is False and isinstance(value, float) is False:
            if self.CONVERT is False:
                raise AssertionError("Input is not a percent, must be an int or float.")
            try:
                value = int(value)
            except:
                try:
                    value = float(value)
                except:
                    raise AssertionError("Input is not a percent, must be an int or float.")
        self.check_min_max(value, **kwargs)
        return value


class Percent(Input_Type):
    """
    Validate that a value is an int or float and between 0 and 100. Will attempt to convert a string to
    a percent.
    """
    MIN = 0
    MAX = 100

    def validate(self, value, **kwargs):
        if isinstance(value, int) is False and isinstance(value, float) is False:
            if self.CONVERT is False:
                raise AssertionError("Input is not a percent, must be an int or float.")

            try:
                value = int(value)
            except:
                try:
                    value = float(value)
                except:
                    raise AssertionError("Input is not a percent, must be an int or float.")

        self.check_min_max(value, **kwargs)
        return value


class _String(Input_Type):
    """
    Will ensure that the value is a string.
    """
    ALLOW_NONE = True

    def validate(self, value, **kwargs):
        if isinstance(value, str) is False:
            if self.ALLOW_NONE is True or 'allow_none' in kwargs:
                return "None"
            if self.CONVERT is True:
                try:
                    value = str(value)
                except:
                    raise AssertionError("Input is not a string.")
        self.check_min_max(value, **kwargs)
        return value


class Filename(_String):
    MIN = 1
    MAX = 256

    def validate(self, value, **kwargs):
        return super(Filename, self).validate(value, **kwargs)


class Password(_String):
    MIN = 3
    MAX = 64

    def validate(self, value, **kwargs):
        return super(Password, self).validate(value, **kwargs)

