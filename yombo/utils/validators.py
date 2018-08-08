"""
Provides basic validators
"""
from datetime import (timedelta, datetime as datetime_sys,
                      time as time_sys, date as date_sys)
import pytz
import os
from typing import Any, Union, TypeVar, Callable, Sequence, Dict
from urllib.parse import urlparse
import voluptuous as vol

from yombo.lib.template import JinjaTemplate
from yombo.core.exceptions import YomboWarning
import yombo.utils.datetime as dt

TIME_PERIOD_ERROR = "offset {} should be format 'HH:MM' or 'HH:MM:SS'"
# typing typevar
T = TypeVar('T')

#####################################################
# Basic types
def boolean(value: Any) -> bool:
    """Validate and coerce a boolean value."""
    if isinstance(value, str):
        value = value.lower()
        if value in ('1', 'true', 'yes', 'on', 'enable'):
            return True
        if value in ('0', 'false', 'no', 'off', 'disable'):
            return False
        raise vol.Invalid('invalid boolean value {}'.format(value))
    elif isinstance(value, bool):
        return value
    raise vol.Invalid("invalid boolean value {}".format(value))


def string(value: Any) -> str:
    """Coerce value to string, except for None."""
    if value is not None:
        return str(value)
    raise vol.Invalid('string value is None')


def ensure_list(value: Union[T, Sequence[T]]) -> Sequence[T]:
    """Wrap value in list if it is not one."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def basic_string(string, min=1, max=255):
    """ A short string with alphanumberic, spaces, and periods. """
    s = vol.Schema(vol.All(
            str,
            vol.Length(min=min, max=max),
            vol.Match(r"^[a-zA-Z_0-9. ]+$")
    ))
    try:
        return s(string)
    except:
        raise vol.Invalid("Provided ID contains invalid characters.")


def basic_word(string, min=1, max=45):
    """ A single word. """
    s = vol.Schema(vol.All(
        str,
        vol.Length(min=min, max=max),
        vol.Match(r"^[a-zA-Z_0-9]+$")
    ))
    try:
        return s(string)
    except:
        raise vol.Invalid("Provided ID contains invalid characters.")


# Adapted from:
# https://github.com/alecthomas/voluptuous/issues/115#issuecomment-144464666
def has_at_least_one_key(*keys: str) -> Callable:
    """Validate that at least one key exists."""
    def validate(obj: Dict) -> Dict:
        """Test keys exist in dict."""
        if not isinstance(obj, dict):
            raise vol.Invalid('expected dictionary')

        for k in obj.keys():
            if k in keys:
                return obj
        raise vol.Invalid('must contain one of {}.'.format(', '.join(keys)))

    return validate


def has_at_least_one_key_value(*items: list) -> Callable:
    """Validate that at least one (key, value) pair exists."""
    def validate(obj: Dict) -> Dict:
        """Test (key,value) exist in dict."""
        if not isinstance(obj, dict):
            raise vol.Invalid('expected dictionary')

        for item in obj.items():
            if item in items:
                return obj
        raise vol.Invalid('must contain one of {}.'.format(str(items)))

    return validate


#####################################################
# OS / File system items
def is_device(value):
    """ Validate that value is a real device. """
    try:
        os.stat(value)
        return str(value)
    except OSError:
        raise vol.Invalid('No device at {} found'.format(value))


def is_dir(value: Any) -> str:
    """Validate that the value is an existing dir."""
    if value is None:
        raise vol.Invalid('not a directory')
    dir_in = os.path.expanduser(str(value))

    if not os.path.isdir(dir_in):
        raise vol.Invalid('not a directory')
    if not os.access(dir_in, os.R_OK):
        raise vol.Invalid('directory not readable')
    return dir_in


def is_file(value: Any) -> str:
    """Validate that the value is an existing file."""
    if value is None:
        raise vol.Invalid('None is not file')
    file_in = os.path.expanduser(str(value))

    if not os.path.isfile(file_in):
        raise vol.Invalid('not a file')
    if not os.access(file_in, os.R_OK):
        raise vol.Invalid('file not readable')
    return file_in


#####################################################
# Time related items
def time_zone(value):
    """Validate timezone."""
    try:
        return pytz.timezone(input)
    except pytz.exceptions.UnknownTimeZoneError:
        raise vol.Invalid("Invalid time zone passed in. Valid options can be found here: "
            "http://en.wikipedia.org/wiki/List_of_tz_database_time_zones")

time_period_dict = vol.All(
    dict, vol.Schema({
        'days': vol.Coerce(int),
        'hours': vol.Coerce(int),
        'minutes': vol.Coerce(int),
        'seconds': vol.Coerce(int),
        'milliseconds': vol.Coerce(int),
    }),
    has_at_least_one_key('days', 'hours', 'minutes',
                         'seconds', 'milliseconds'),
    lambda value: timedelta(**value))


def time(value) -> time_sys:
    """Validate and transform a time."""
    if isinstance(value, time_sys):
        return value

    try:
        time_val = dt.parse_time(value)
    except TypeError:
        raise vol.Invalid('Not a parseable type')

    if time_val is None:
        raise vol.Invalid('Invalid time specified: {}'.format(value))

    return time_val


def date(value) -> date_sys:
    """Validate and transform a date."""
    if isinstance(value, date_sys):
        return value

    try:
        date_val = dt.parse_date(value)
    except TypeError:
        raise vol.Invalid('Not a parseable type')

    if date_val is None:
        raise vol.Invalid("Could not parse date")

    return date_val


def time_period_str(value: str) -> timedelta:
    """Validate and transform time offset."""
    if isinstance(value, int):
        raise vol.Invalid('Make sure you wrap time values in quotes')
    elif not isinstance(value, str):
        raise vol.Invalid(TIME_PERIOD_ERROR.format(value))

    negative_offset = False
    if value.startswith('-'):
        negative_offset = True
        value = value[1:]
    elif value.startswith('+'):
        value = value[1:]

    try:
        parsed = [int(x) for x in value.split(':')]
    except ValueError:
        raise vol.Invalid(TIME_PERIOD_ERROR.format(value))

    if len(parsed) == 2:
        hour, minute = parsed
        second = 0
    elif len(parsed) == 3:
        hour, minute, second = parsed
    else:
        raise vol.Invalid(TIME_PERIOD_ERROR.format(value))

    offset = timedelta(hours=hour, minutes=minute, seconds=second)

    if negative_offset:
        offset *= -1

    return offset


def time_period_seconds(value: Union[int, str]) -> timedelta:
    """Validate and transform seconds to a time offset."""
    try:
        return timedelta(seconds=int(value))
    except (ValueError, TypeError):
        raise vol.Invalid('Expected seconds, got {}'.format(value))


time_period = vol.Any(time_period_str, time_period_seconds, timedelta,
                      time_period_dict)


#####################################################
# Yombo items
def id_string(string, min=4, max=100):
    """ Ensure value is a string, with at least 4 characters and max of 100."""
    s = vol.Schema(vol.All(
        str,
        vol.Length(min=min, max=max),
        vol.Match(r"^[a-zA-Z_0-9. ]+$")
    ))
    try:
        return s(string)
    except:
        raise vol.Invalid("Provided ID contains invalid characters.")


#####################################################
# Misc
def template(value):
    """Validate a jinja2 template."""
    if value is None:
        raise vol.Invalid('template value is None')
    elif isinstance(value, str) is False:
        raise vol.Invalid('template value should be a string')

    value = JinjaTemplate(str(value))

    try:
        value.ensure_valid()
        return value
    except YomboWarning as e:
        raise vol.Invalid('invalid template ({})'.format(e))


def url(url_in, protocols=None):
    if protocols is None:
        protocols = ['http', 'https', 'sftp', 'ftp']

    if urlparse(url_in).scheme in protocols:
        try:
            return vol.Schema(vol.Url())(url_in)
        except:
            pass
    raise vol.Invalid("Invalid URL.")


