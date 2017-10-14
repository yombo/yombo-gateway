# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Validate @ Module Development <https://docs.yombo.net/Libraries/Validate>`_


Validates various items. In many causes, it tries to coerce the correct value type and return that. If the item
is valid, it returns the item. If the item is invalid, and error will be raised.

This file is comprised of various code samples scattered around the internet. Many of functions below are
a derivative from: home assistant's helper file: config_validation.py

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.14.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://docs.yombo.net/gateway/html/current/_modules/yombo/lib/validate.html>`_
"""
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
import msgpack
from datetime import timedelta, datetime as datetime_sys
import os
import re
from socket import _GLOBAL_DEFAULT_TIMEOUT
from unicodedata import normalize
from typing import Any, Union, TypeVar, Callable, Sequence, Dict
import voluptuous as vol


# from twisted.internet.defer import inlineCallbacks, Deferred
# from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import Invalid
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.constants import \
    TEMP_FAHRENHEIT, TEMP_CELSIUS, MISC_UNIT_SYSTEM_METRIC, MISC_UNIT_SYSTEM_IMPERIAL, WEEKDAYS

logger = get_logger('library.validate')

# typing typevar
T = TypeVar('T')


TIME_PERIOD_ERROR = "offset {} should be format 'HH:MM' or 'HH:MM:SS'"

RE_SANITIZE_FILENAME = re.compile(r'(~|\.\.|/|\\)')
RE_SANITIZE_PATH = re.compile(r'(~|\.(\.)+)')
RE_SLUGIFY = re.compile(r'[^a-z0-9_]+')
TBL_SLUGIFY = {
    ord('ß'): 'ss'
}

class Validate(YomboLibrary):
    """
    Performs various tasks at startup.

    """
    def _init_(self, **kwargs):
        pass

    # Adapted from:
    # https://github.com/alecthomas/voluptuous/issues/115#issuecomment-144464666
    def has_at_least_one_key(self, *keys: str) -> Callable:
        """Validate that at least one key exists."""
        def validate(obj: Dict) -> Dict:
            """Test keys exist in dict."""
            if not isinstance(obj, dict):
                raise Invalid('expected dictionary')

            for k in obj.keys():
                if k in keys:
                    return obj
            raise Invalid('must contain one of {}.'.format(', '.join(keys)))

        return validate

    def is_device(self, value):
        """Validate that value is a real device."""
        try:
            os.stat(value)
            return str(value)
        except OSError:
            raise Invalid('No device at {} found'.format(value))

    def is_file(self, value: Any) -> str:
        """Validate that the value is an existing file."""
        if value is None:
            raise Invalid('None is not file')
        file_in = os.path.expanduser(str(value))

        if not os.path.isfile(file_in):
            raise Invalid('not a file')
        if not os.access(file_in, os.R_OK):
            raise Invalid('file not readable')
        return file_in

    def ensure_list(self, value: Union[T, Sequence[T]]) -> Sequence[T]:
        """Wrap value in list if it is not one."""
        if value is None:
            return []
        return value if isinstance(value, list) else [value]

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

    def time_period_str(self, value: str) -> timedelta:
        """Validate and transform time offset."""
        if isinstance(value, int):
            raise Invalid('Make sure you wrap time values in quotes')
        elif not isinstance(value, str):
            raise Invalid(TIME_PERIOD_ERROR.format(value))

        negative_offset = False
        if value.startswith('-'):
            negative_offset = True
            value = value[1:]
        elif value.startswith('+'):
            value = value[1:]

        try:
            parsed = [int(x) for x in value.split(':')]
        except ValueError:
            raise Invalid(TIME_PERIOD_ERROR.format(value))

        if len(parsed) == 2:
            hour, minute = parsed
            second = 0
        elif len(parsed) == 3:
            hour, minute, second = parsed
        else:
            raise Invalid(TIME_PERIOD_ERROR.format(value))

        offset = timedelta(hours=hour, minutes=minute, seconds=second)

        if negative_offset:
            offset *= -1

        return offset

    def time_period_seconds(self, value: Union[int, str]) -> timedelta:
        """Validate and transform seconds to a time offset."""
        try:
            return timedelta(seconds=int(value))
        except (ValueError, TypeError):
            raise Invalid('Expected seconds, got {}'.format(value))

    time_period = vol.Any(time_period_str, time_period_seconds, timedelta,
                          time_period_dict)

    def match_all(self, value):
        """Validate that matches all values."""
        return value

    def positive_timedelta(self, value: timedelta) -> timedelta:
        """Validate timedelta is positive."""
        if value < timedelta(0):
            raise Invalid('Time period should be positive')
        return value

    def _slugify(self, text: str) -> str:
        """Slugify a given text."""
        text = normalize('NFKD', text)
        text = text.lower()
        text = text.replace(" ", "_")
        text = text.translate(TBL_SLUGIFY)
        text = RE_SLUGIFY.sub("", text)
        return text

    def slug(self, value):
        """Validate value is a valid slug (aka: machine_label)"""
        if value is None:
            raise Invalid('Slug should not be None')
        value = str(value)
        slg = self._slugify(value)
        if value == slg:
            return value
        raise Invalid('invalid slug {} (try {})'.format(value, slg))

    def slugify(self, value):
        """Coerce a value to a slug."""
        if value is None:
            raise Invalid('Slug should not be None')
        slg = self._slugify(str(value))
        if slg:
            return slg
        raise Invalid('Unable to slugify {}'.format(value))

    def temperature_unit(self, value) -> str:
        """Validate and transform temperature unit."""
        value = str(value).upper()
        if value == 'C':
            return TEMP_CELSIUS
        elif value == 'F':
            return TEMP_FAHRENHEIT
        raise Invalid('invalid temperature unit (expected C or F)')

    unit_system = vol.All(vol.Lower, vol.Any(MISC_UNIT_SYSTEM_METRIC,
                                             MISC_UNIT_SYSTEM_IMPERIAL))

    def time(self, value):
        """Validate time."""
        try:
            return self._Times.time_from_string(value)[0]
        except Exception:
            raise Invalid('Invalid time specified: {}'.format(value))

    def datetime(self, value):
        """Validate datetime."""
        if isinstance(value, datetime_sys):
            return value

        try:
            return self._Times.time_from_string(value)[0]
        except Exception:
            raise Invalid('Invalid datetime specified: {}'.format(value))

    def time_zone(self, value):
        """Validate timezone."""
        if self._Times.get_time_zone(value) is not None:
            return value
        raise Invalid(
            'Invalid time zone passed in. Valid options can be found here: '
            'http://en.wikipedia.org/wiki/List_of_tz_database_time_zones')

    weekdays = vol.All(ensure_list, [vol.In(WEEKDAYS)])

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
                raise Invalid('Invalid socket timeout value.'
                                  ' float > 0.0 required.')
            except Exception as _:
                raise Invalid('Invalid socket timeout: {err}'.format(err=_))



    def x10_address(value):
        """Validate an x10 address."""
        regex = re.compile(r'([A-Pa-p]{1})(?:[2-9]|1[0-6]?)$')
        if not regex.match(value):
            raise Invalid('Invalid X10 Address')
        return str(value).lower()

    def ensure_list(self, value: Union[T, Sequence[T]]) -> Sequence[T]:
        """Wrap value in list if it is not one."""
        if value is None:
            return []
        return value if isinstance(value, list) else [value]

    def ensure_list_csv(self, value: Any) -> Sequence:
        """Ensure that input is a list or make one from comma-separated string."""
        if isinstance(value, str):
            return [member.strip() for member in value.split(',')]
        return self.ensure_list(value)

    def is_json(self, value):
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

    def is_msgpack(self, value):
        """
        Helper function to determine if data is msgpack or not.

        :param mymsgpack:
        :return:
        """
        try:
            json_object = msgpack.loads(value)
        except:
            return False
        return True

    # Validator helpers

    def key_dependency(self, key, dependency):
        """Validate that all dependencies exist for key."""

        def validator(value):
            """Test dependencies."""
            if not isinstance(value, dict):
                raise Invalid('key dependencies require a dict')
            if key in value and dependency not in value:
                raise Invalid('dependency violation - key "{}" requires '
                                  'key "{}" to exist'.format(key, dependency))

            return value

        return validator

