"""
Anything dealing with data types, such as floats, ints, strings, decimals, etc.

"""
import math
from decimal import Decimal

def magnitude(value):
    """
    From: https://gist.github.com/pyrtsa/10009826

    Decimal magnitude of abs(value) as int, or float('-inf') if value == 0.
    Example:

        >>> [magnitude(x) for x in [1.314234123412345678e-9, 124.355, -1000, 0]]
        [-9, 2, 3, -inf]
    """
    return int(math.floor(math.log10(abs(value)))) if value else float('-inf')


def approximate(value, digits=4):
    """
    From: https://gist.github.com/pyrtsa/10009826

    Convert value to Decimal keeping the given number of digits after the
    leading number.

        >>> [approx(x) for x in [1.314234123412345678e-9, 124.355, -1000, 0]]
        [Decimal('1.3142E-9'), Decimal('124.36'), Decimal('-1000.0'), Decimal('0')]
    """
    if not isinstance(value, Decimal):
        value = Decimal(value)
    return round(value, digits - magnitude(value)) if value != 0 else value


def decstring(x):
    """
    From: https://gist.github.com/pyrtsa/10009826

    Convert (float) number x to string with sufficient precision
    for converting it back to float but without using the engineering
    notation. Example:

        >>> [decstring(x) for x in [1.314234123412345678e-9, 124.355, -1000, 0]]
        ['0.0000000013142341234123457', '124.355', '-1000', '0']
    """
    return format(Decimal(str(x)), 'f')