import re
from typing import Any, Union, TypeVar, Callable, Sequence, Dict
from urllib.parse import urlparse
import voluptuous as vol

from yombo.lib.inputtypes.input_type import Input_Type


class Email(Input_Type):
    MIN = 5
    MAX = 128

    def validate(self, value, **kwargs) -> str:
        if re.match("[\w\.\-]*@[\w\.\-]*\.\w+", str(value)) is False:
            raise AssertionError("Invalid email address")

        self.check_min_max(value, **kwargs)
        return str(value)


class URI(Input_Type):
    MIN = 5
    MAX = 196
    # pylint: disable=no-value-for-parameter
    def url(value: Any, **kwargs) -> str:
        """Validate an URL."""
        url_in = str(value)

        if urlparse(url_in).scheme in ['http', 'https']:
            return vol.Schema(vol.Url())(url_in)

        raise AssertionError('Invalid url')


class URL(Input_Type):
    MIN = 5
    MAX = 196
    # pylint: disable=no-value-for-parameter
    def url(value: Any, **kwargs) -> str:
        """Validate an URL."""
        url_in = str(value)

        if urlparse(url_in).scheme in ['http', 'https']:
            return vol.Schema(vol.Url())(url_in)

        raise AssertionError('Invalid url')