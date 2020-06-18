# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Validate @ Library Documentation <https://yombo.net/docs/libraries/validate>`_

Validates various items. In many causes, it tries to coerce the correct value type and return that. If the item
is valid, it returns the item. If the item is invalid, and YomboInvalidValidation.

For most items, this just wraps the yombo.utils.validators and changes the exception from MultipleYomboInvalidValidation to
YomboInvalidValidation.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.14.0

:copyright: Copyright 2017-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/variable.html>`_
"""
from datetime import time as time_sys, date as date_sys
import json
from datetime import timedelta, datetime as datetime_sys
import msgpack
import os
import pytz
import re
from slugify import slugify
from socket import _GLOBAL_DEFAULT_TIMEOUT
from typing import Any, Union, TypeVar, Callable, Sequence, Dict
from urllib.parse import urlparse
import voluptuous as vol

# Import Yombo libraries
from yombo.core.exceptions import YomboInvalidValidation, YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.constants import \
    TEMP_FAHRENHEIT, TEMP_CELSIUS, MISC_UNIT_SYSTEM_METRIC, MISC_UNIT_SYSTEM_IMPERIAL, WEEKDAYS
from yombo.lib.template import JinjaTemplate
import yombo.utils.datetime as dt

logger = get_logger("library.validate")

# typing typevar
T = TypeVar("T")


TIME_PERIOD_ERROR = "offset {} should be format 'HH:MM' or 'HH:MM:SS'"

RE_SANITIZE_FILENAME = re.compile(r"(~|\.\.|/|\\)")
RE_SANITIZE_PATH = re.compile(r"(~|\.(\.)+)")


class Validate(YomboLibrary):
    """
    Handles common validation tasks.
    """
    #####################################################
    # Basic types
    @staticmethod
    def boolean(value: Any, coerce: Union[None, bool] = None) -> bool:
        """Validate and maybe coerce a boolean value."""
        if isinstance(value, bool):
            return value
        if coerce in (None, True):
            if isinstance(value, int):
                value = str(int)
            if isinstance(value, str):
                value = value.lower()
                if value in ("1", "true", "yes", "on", "enable"):
                    return True
                if value in ("0", "false", "no", "off", "disable"):
                    return False
        raise YomboInvalidValidation("Value is not a boolean and cannot be coerced.")

    @staticmethod
    def string(value: Any) -> str:
        """Coerce value to string, except for None."""
        if value is not None:
            try:
                return str(value)
            except:
                pass
        raise YomboInvalidValidation("Couldn't make value a string.")

    @staticmethod
    def basic_list(value: Union[T, Sequence[T]]) -> Sequence[T]:
        """Wrap value in list if it is not one."""
        if value is None:
            return []
        return value if isinstance(value, list) else [value]

    @staticmethod
    def basic_string(value, minimum: int = 1, maximum: int = 255):
        """ A short string with alphanumberic, spaces, and periods. """
        if isinstance(value, str) and len(value) >= minimum and len(value) <= maximum:
            return value
        raise YomboInvalidValidation("Value is not a string, or doesn't fit within the required lengths.")

    @staticmethod
    def basic_word(value):
        """ A single word. """
        if value.strip().count(' ') == 1:
            return value
        raise YomboInvalidValidation("Value is not a single word.")

    # Adapted from:
    # https://github.com/alecthomas/voluptuous/issues/115#issuecomment-144464666
    @staticmethod
    def has_at_least_one_key(*keys: str) -> Callable:
        """Validate that at least one key exists."""

        def validate(obj: Dict) -> Dict:
            """Test keys exist in dict."""
            if not isinstance(obj, dict):
                raise YomboInvalidValidation("expected dictionary")

            for k in obj.keys():
                if k in keys:
                    return obj
            raise YomboInvalidValidation(f"must contain one of {', '.join(keys)}.")
        return validate

    @staticmethod
    def has_at_least_one_key_value(*items: list) -> Callable:
        """Validate that at least one (key, value) pair exists."""

        def validate(obj: Dict) -> Dict:
            """Test (key,value) exist in dict."""
            if not isinstance(obj, dict):
                raise YomboInvalidValidation("Expected dictionary")

            for item in obj.items():
                if item in items:
                    return obj
            raise YomboInvalidValidation(f"must contain one of {str(items)}.")
        return validate

    #####################################################
    # OS / File system items
    def is_device(value):
        """ Validate that value is a real device. """
        try:
            os.stat(value)
            return str(value)
        except OSError:
            raise YomboInvalidValidation(f"No device at {value} found")

    @staticmethod
    def is_dir(value: Any) -> str:
        """Validate that the value is an existing dir."""
        if value is None:
            raise YomboInvalidValidation("not a directory")
        dir_in = os.path.expanduser(str(value))

        if not os.path.isdir(dir_in):
            raise YomboInvalidValidation("not a directory")
        if not os.access(dir_in, os.R_OK):
            raise YomboInvalidValidation("directory not readable")
        return dir_in

    @staticmethod
    def is_file(value: Union[str, None]) -> str:
        """Validate that the value is an existing file."""
        if value is None:
            raise YomboInvalidValidation("None is not file")
        file_in = os.path.expanduser(str(value))

        if not os.path.isfile(file_in):
            raise YomboInvalidValidation("not a file")
        if not os.access(file_in, os.R_OK):
            raise YomboInvalidValidation("file not readable")
        return file_in

    #####################################################
    # Time related items
    @staticmethod
    def time_zone(value):
        """Validate timezone."""
        try:
            return pytz.timezone(input)
        except pytz.exceptions.UnknownTimeZoneError:
            raise YomboInvalidValidation("Invalid time zone passed in. Valid options can be found here: "
                              "http://en.wikipedia.org/wiki/List_of_tz_database_time_zones")

    @staticmethod
    def time(value) -> time_sys:
        """Validate and transform a time."""
        if isinstance(value, time_sys):
            return value

        try:
            time_val = dt.parse_time(value)
        except TypeError:
            raise YomboInvalidValidation("Not a parseable type")

        if time_val is None:
            raise YomboInvalidValidation(f"Invalid time specified: {value}")

        return time_val

    @staticmethod
    def date(value) -> date_sys:
        """Validate and transform a date."""
        if isinstance(value, date_sys):
            return value

        try:
            date_val = dt.parse_date(value)
        except TypeError:
            raise YomboInvalidValidation("Not a parseable type")

        if date_val is None:
            raise YomboInvalidValidation("Could not parse date")

        return date_val

    @staticmethod
    def time_period_str(value: str) -> timedelta:
        """Validate and transform time offset."""
        if isinstance(value, int):
            raise YomboInvalidValidation("Make sure you wrap time values in quotes")
        elif not isinstance(value, str):
            raise YomboInvalidValidation(TIME_PERIOD_ERROR.format(value))

        negative_offset = False
        if value.startswith("-"):
            negative_offset = True
            value = value[1:]
        elif value.startswith("+"):
            value = value[1:]

        try:
            parsed = [int(x) for x in value.split(":")]
        except ValueError:
            raise YomboInvalidValidation(TIME_PERIOD_ERROR.format(value))

        if len(parsed) == 2:
            hour, minute = parsed
            second = 0
        elif len(parsed) == 3:
            hour, minute, second = parsed
        else:
            raise YomboInvalidValidation(TIME_PERIOD_ERROR.format(value))

        offset = timedelta(hours=hour, minutes=minute, seconds=second)

        if negative_offset:
            offset *= -1

        return offset

    @staticmethod
    def time_period_seconds(value: Union[int, str]) -> timedelta:
        """Validate and transform seconds to a time offset."""
        try:
            return timedelta(seconds=int(value))
        except (ValueError, TypeError):
            raise YomboInvalidValidation(f"Expected seconds, got {value}")

    #####################################################
    # Yombo items
    @staticmethod
    def id_string(string, minimum: int = 1, maximum: int = 200):
        """ Ensure value is a string, with at least 4 characters and maximum of 100."""
        s = vol.Schema(vol.All(
            str,
            vol.Length(min=minimum, max=maximum),
            vol.Match(r"^[a-zA-Z_0-9. ]+$")
        ))
        try:
            return s(string)
        except Exception as e:
            raise YomboInvalidValidation("Provided ID contains invalid characters.")

    #####################################################
    # Misc
    @staticmethod
    def template(value):
        """Validate a jinja2 template."""
        if value is None:
            raise YomboInvalidValidation("template value is None")
        elif isinstance(value, str) is False:
            raise YomboInvalidValidation("template value should be a string")

        value = JinjaTemplate(str(value))

        try:
            value.ensure_valid()
            return value
        except YomboWarning as e:
            raise YomboInvalidValidation(f"invalid template ({e})")

    @staticmethod
    def url(url_in, protocols=None):
        if protocols is None:
            protocols = ["http", "https", "sftp", "ftp"]

        if urlparse(url_in).scheme in protocols:
            try:
                return vol.Schema(vol.Url())(url_in)
            except:
                pass
        raise YomboInvalidValidation("Invalid URL.")

    @staticmethod
    def match_all(self, value):
        """Validate that matches all values."""
        return value

    @staticmethod
    def positive_timedelta(value: timedelta) -> timedelta:
        """Validate timedelta is positive."""
        if value < timedelta(0):
            raise YomboInvalidValidation("Time period should be positive")
        return value

    @staticmethod
    def _slugify(text: str) -> str:
        """Slugify a given text."""
        return slugify(text, separator="_")

    def slug(self, value):
        """Validate value is a valid slug (aka: machine_label)"""
        if value is None:
            raise YomboInvalidValidation("Slug should not be None")
        value = str(value)
        slg = self._slugify(value)
        if value == slg:
            return value
        raise YomboInvalidValidation(f"invalid slug {value} (try {slg})")

    @classmethod
    def slugify(cls, value):
        """Coerce a value to a slug."""
        # print("going to try to slugify: %s" % value)
        if value is None:
            raise YomboInvalidValidation("Slug should not be None")
        slg = cls._slugify(str(value))
        if slg:
            return slg
        # print("can't make slug: %s" % slg)
        raise YomboInvalidValidation(f"Unable to slugify {value}")

    @classmethod
    def temperature_unit(cls, value) -> str:
        """Validate and transform temperature unit."""
        value = str(value).upper()
        if value == "C":
            return TEMP_CELSIUS
        elif value == "F":
            return TEMP_FAHRENHEIT
        raise YomboInvalidValidation("invalid temperature unit (expected C or F)")

    unit_system = vol.All(vol.Lower, vol.Any(MISC_UNIT_SYSTEM_METRIC,
                                             MISC_UNIT_SYSTEM_IMPERIAL))

    @staticmethod
    def time(value):
        """Validate time."""
        try:
            return dt.time_from_string(value)[0]
        except Exception:
            raise YomboInvalidValidation(f"YomboInvalidValidation time specified: {value}")

    @staticmethod
    def datetime(self, value):
        """Validate datetime."""
        if isinstance(value, datetime_sys):
            return value

        try:
            return dt.time_from_string(value)[0]
        except Exception:
            raise YomboInvalidValidation(f"YomboInvalidValidation datetime specified: {value}")

    @staticmethod
    def time_zone(value):
        """Validate timezone."""
        if dt.get_time_zone(value) is not None:
            return value
        raise YomboInvalidValidation(
            "YomboInvalidValidation time zone passed in. Valid options can be found here: "
            "http://en.wikipedia.org/wiki/List_of_tz_database_time_zones")

    weekdays = vol.All(basic_list, [vol.In(WEEKDAYS)])

    @staticmethod
    def socket_timeout(value):
        """Validate timeout float > 0.0.

        None coerced to socket._GLOBAL_DEFAULT_TIMEOUT bare object.
        """
        if value is None:
            return _GLOBAL_DEFAULT_TIMEOUT
        else:
            try:
                float_value = float(value)
                if float_value > 0.0:
                    return float_value
                raise YomboInvalidValidation("YomboInvalidValidation socket timeout value."
                                  " float > 0.0 required.")
            except Exception as e:
                raise YomboInvalidValidation(f"YomboInvalidValidation socket timeout: {e}")

    @staticmethod
    def x10_address(value):
        """Validate an x10 address."""
        regex = re.compile(r"([A-Pa-p]{1})(?:[2-9]|1[0-6]?)$")
        if not regex.match(value):
            raise YomboInvalidValidation("YomboInvalidValidation X10 Address")
        return str(value).lower()

    @staticmethod
    def basic_list(value: Union[T, Sequence[T]]) -> Sequence[T]:
        """Wrap value in list if it is not one."""
        if value is None:
            return []
        return value if isinstance(value, list) else [value]

    @classmethod
    def basic_list_csv(cls, value: Any) -> Sequence:
        """Ensure that input is a list or make one from comma-separated string."""
        if isinstance(value, str):
            return [member.strip() for member in value.split(",")]
        return cls.basic_list(value)

    @staticmethod
    def is_json(value):
        """
        Determine if data is json or not.

        :param value:
        :return:
        """
        try:
            json_object = json.loads(value)
        except:
            return False
        return True

    @staticmethod
    def is_msgpack(value):
        """
        Helper function to determine if data is msgpack or not.

        :param mymsgpack:
        :return:
        """
        try:
            json_object = msgpack.unpackb(value)
        except:
            return False
        return True

    # Validator helpers
    @staticmethod
    def key_dependency(key, dependency):
        """Validate that all dependencies exist for key."""

        def validator(value):
            """Test dependencies."""
            if not isinstance(value, dict):
                raise YomboInvalidValidation("key dependencies require a dict")
            if key in value and dependency not in value:
                raise YomboInvalidValidation(f'dependency violation - key "{key}" requires key "{dependency}" to exist')

            return value

        return validator

    @classmethod
    def time_period_dict(cls):
        return vol.All(
            dict, vol.Schema({
                "days": vol.Coerce(int),
                "hours": vol.Coerce(int),
                "minutes": vol.Coerce(int),
                "seconds": vol.Coerce(int),
                "milliseconds": vol.Coerce(int),
            }),
            cls.has_at_least_one_key("days", "hours", "minutes", "seconds", "milliseconds"),
            lambda value: timedelta(**value))

    @classmethod
    def time_period(cls):
        return vol.Any(cls.time_period_str, cls.time_period_seconds, timedelta, cls.time_period_dict)
