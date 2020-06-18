from typing import Any, Union, TypeVar, Callable, Sequence, Dict
import string

from yombo.lib.inputtypes.input_type import InputType


class Any_(InputType):
    """
    Always returns the value provided.
    """
    def validate(self, value, **kwargs):
        return value


class Bool(InputType):
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
        if value in (1, "1", "true", "yes", "on", "enable"):
            return True
        if value in (0, "0", "false", "no", "off", "disable"):
            return False
        raise AssertionError("Value is not a boolean.")


class Checkbox(InputType):
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
        if value in (1, "1", "true", "yes", "on", "enable"):
            return True
        if value in (0, "0", "false", "no", "off", "disable"):
            return False
        raise AssertionError("Value is not a boolean.")


class Integer_(InputType):
    """
    Validation if integers. Will try to coerce to int if it's not.
    """
    MIN = None
    MAX = None

    def validate(self, value, **kwargs):
        if isinstance(value, int) is True:
            self.check_min_max(value, **kwargs)
            return value
        if self.CONVERT is False:
            raise AssertionError("Value is not an int.")
        try:
            value = int(value)
        except:
            if value == "":
                return None
            raise AssertionError("Input is not an int.")
        self.check_min_max(value, **kwargs)
        return value


class Filename(InputType):
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
        valid_chars = f"-_.() /{string.ascii_letters}{string.digits}"
        for char in value:
            if char not in valid_chars:
                raise AssertionError(f"Input has invalid character: {char}")
        self.check_min_max(value, **kwargs)
        return value


class Float_(InputType):
    """
    Validation of floats. Optionally, will try to convert the input to a float if allowed.
    """
    def validate(self, value, **kwargs):
        if isinstance(value, float) is True:
            self.check_min_max(value, **kwargs)
            return value
        if self.CONVERT is False:
            raise AssertionError("Input is not a float.")
        try:
            value = float(value)
        except:
            raise AssertionError("Input is not a float.")
        self.check_min_max(value, **kwargs)
        return value


class None_(InputType):
    """
    Validation of NoneType or string with "none" or string that's empty.
    """
    def validate(self, value, **kwargs):
        if isinstance(value, None):
            return value
        if self.CONVERT is False:
            raise AssertionError("Value is not NoneType or empty.")
        if isinstance(value, str):
            if value.lower() == "none" or value == "":
                return None
        raise AssertionError("Value is not NoneType or empty.")


class Number_(Integer_):
    """
    Anything that can be represented as either an int or a float.
    """
    def validate(self, value, **kwargs):
        if isinstance(value, int) is False and isinstance(value, float) is False:
            if self.CONVERT is False:
                raise AssertionError("Input is not an int or float.")
            try:
                value = int(value)
            except:
                try:
                    value = float(value)
                except:
                    raise AssertionError("Input is not a percent, must be an int or float.")
        self.check_min_max(value, **kwargs)
        return value


class Percent(InputType):
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


class String_(InputType):
    """
    Will ensure that the value is a string.
    """
    ALLOW_NONE = True

    def validate(self, value, **kwargs):
        if isinstance(value, str) is False:
            if self.ALLOW_NONE is True or "allow_none" in kwargs:
                return "None"
            if self.CONVERT is True:
                try:
                    value = str(value)
                except:
                    raise AssertionError("Input is not a string.")
        self.check_min_max(value, **kwargs)
        return value


class Password(String_):
    MIN = 3
    MAX = 64

    def validate(self, value, **kwargs):
        return super(Password, self).validate(value, **kwargs)

