"""
File created by Mitch Schwenk for Yombo.
"""
import re
from .between import between
from .utils import validator


@validator
def password(value, min=3, max=64):
    """
    Check if the string supplied is a potential password.

    Examples::

        >>> password('MyPass%^@!@#', min=2)
        True

        >>> length("so'mething", min=9, max=9)
        ValidationFailure(func=password, ...)

        >>> length('som"ething', max=5)
        ValidationFailure(func=password, ...)

    :param value:
        The string to validate as a password.
    :param min:
        The minimum required length of the string. Default=3
    :param max:
        The maximum length of the string. Default=64 (that's secure!)
    """
    if (min is not None and min < 0) or (max is not None and max < 0):
        raise AssertionError(
            '`min` and `max` need to be greater than zero.'
        )

    if re.match(r'[A-Za-z0-9@#$%^&+=]{3,}', value):
        return True
    else:
        raise AssertionError(
            'Password has invalid characters.'
        )
