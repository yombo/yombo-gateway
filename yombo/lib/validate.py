# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Validate @ Module Development <https://yombo.net/docs/libraries/validate>`_


Validates various items. In many causes, it tries to coerce the correct value type and return that. If the item
is valid, it returns the item. If the item is invalid, and YomboInvalidValidation.

For most items, this just wraps the yombo.utils.validators and changes the exception from MultipleInvalid to
YomboInvalidValidation.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.14.0

:copyright: Copyright 2017-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/validate.html>`_
"""
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from datetime import timedelta, datetime as datetime_sys
import msgpack
import re
from socket import _GLOBAL_DEFAULT_TIMEOUT
from typing import Any, Union, TypeVar, Callable, Sequence, Dict
from unicodedata import normalize
import voluptuous as vol

# Import Yombo libraries
from yombo.core.exceptions import Invalid, YomboInvalidValidation
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.constants import \
    TEMP_FAHRENHEIT, TEMP_CELSIUS, MISC_UNIT_SYSTEM_METRIC, MISC_UNIT_SYSTEM_IMPERIAL, WEEKDAYS
import yombo.utils.datetime as dt
import yombo.utils.validators as val

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
    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo validate library"

    def _init_(self, **kwargs):
        pass

    #####################################################
    # Basic types
    def boolean(self, value: Any) -> bool:
        """Validate and coerce a boolean value."""
        try:
            return val.boolean(value)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    def string(self, value: Any) -> str:
        """Coerce value to string, except for None."""
        try:
            return val.string(value)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    def ensure_list(self, value: Union[T, Sequence[T]]) -> Sequence[T]:
        """Wrap value in list if it is not one."""
        try:
            return val.ensure_list(value)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    def basic_string(self, string, min=1, max=255):
        """ A short string with alphanumberic, spaces, and periods. """
        try:
            return val.ensure_list(string)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    def basic_word(self, string, min=1, max=45):
        """ A single word. """
        try:
            return val.ensure_list(string)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    # Adapted from:
    # https://github.com/alecthomas/voluptuous/issues/115#issuecomment-144464666
    def has_at_least_one_key(*keys: str) -> Callable:
        """Validate that at least one key exists."""
        try:
            return val.has_at_least_one_key(keys)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    def has_at_least_one_key_value(*items: list) -> Callable:
        """Validate that at least one (key, value) pair exists."""
        try:
            return val.time_zone(items)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    #####################################################
    # OS / File system items
    def is_device(value):
        """ Validate that value is a real device. """
        try:
            return val.is_device(value)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    def is_dir(value: Any) -> str:
        """Validate that the value is an existing dir."""
        try:
            return val.is_dir(value)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    def is_file(value: Any) -> str:
        """Validate that the value is an existing file."""
        try:
            return val.is_file(value)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    #####################################################
    # Time related items
    def time_zone(self, value):
        """Validate timezone."""
        try:
            return val.time_zone(value)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    def time(self, value):
        """Validate timezone."""
        try:
            return val.time(value)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    def date(self, value):
        """Validate timezone."""
        try:
            return val.date(value)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    def time_period_str(self, value: str) -> timedelta:
        """Validate and transform time offset."""
        try:
            return val.time_period_str(value)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    def time_period_seconds(self, value: Union[int, str]) -> timedelta:
        """Validate and transform seconds to a time offset."""
        try:
            return timedelta(seconds=int(value))
        except (ValueError, TypeError):
            raise Invalid('Expected seconds, got {}'.format(value))


    #####################################################
    # Yombo items
    def id_string(self, string, min=4, max=100):
        """ Ensure value is a string, with at least 4 characters and max of 100."""
        try:
            return val.id_string(string, min, max)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))

    #####################################################
    # Misc
    def template(value):
        """Validate a jinja2 template."""
        try:
            return val.template(value)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))


    def url(self, url_in, protocols=None):
        try:
            return val.url(url_in, protocols)
        except vol.MultipleInvalid as e:
            raise YomboInvalidValidation(str(e))


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
        # print("going to try to slugify: %s" % value)
        if value is None:
            raise Invalid('Slug should not be None')
        slg = self._slugify(str(value))
        if slg:
            return slg
        # print("can't make slug: %s" % slg)
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
            return dt.time_from_string(value)[0]
        except Exception:
            raise Invalid('Invalid time specified: {}'.format(value))

    def datetime(self, value):
        """Validate datetime."""
        if isinstance(value, datetime_sys):
            return value

        try:
            return dt.time_from_string(value)[0]
        except Exception:
            raise Invalid('Invalid datetime specified: {}'.format(value))

    def time_zone(self, value):
        """Validate timezone."""
        if dt.get_time_zone(value) is not None:
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

    def string(value: Any) -> str:
        """Coerce value to string, except for None."""
        if value is not None:
            return str(value)
        raise vol.Invalid('string value is None')

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
