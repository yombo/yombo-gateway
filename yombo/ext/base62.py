# -*- coding: utf-8 -*-
"""
base62
~~~~~~
https://github.com/suminb/base62/blob/develop/base62.py

Copyright (c) 2014, Sumin Byeon
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those
of the authors and should not be interpreted as representing official policies,
either expressed or implied, of the FreeBSD Project.

This version has been modified for Yombo to use the correct charset order.
"""

__title__ = 'base62'
__author__ = 'Sumin Byeon'
__email__ = 'suminb@gmail.com'
__version__ = '0.3.2'

CHARSET = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
BASE = 62


def bytes_to_int(s, byteorder='big', signed=False):
    """Converts a byte array to an integer value.

    Python 3 comes with a built-in function to do this, but we would like to
    keep our code Python 2 compatible.
    """

    try:
        return int.from_bytes(s, byteorder, signed=signed)
    except AttributeError:
        # For Python 2.x
        if byteorder != 'big' or signed:
            raise NotImplementedError()

        # NOTE: This won't work if a generator is given
        n = len(s)
        ds = (x << (8 * (n - 1 - i)) for i, x in enumerate(bytearray(s)))

        return sum(ds)


def encode(n, minlen=1):
    """Encodes a given integer ``n``."""

    chs = []
    while n > 0:
        r = n % BASE
        n //= BASE

        chs.append(CHARSET[r])

    if len(chs) > 0:
        chs.reverse()
    else:
        chs.append('0')

    s = ''.join(chs)
    s = CHARSET[0] * max(minlen - len(s), 0) + s
    return s


def encodebytes(s):
    """Encodes a bytestring into a base62 string.

    :param s: A byte array
    """

    _check_bytes_type(s)
    return encode(bytes_to_int(s))


def decode(b):
    """Decodes a base62 encoded value ``b``."""

    if b.startswith('0z'):
        b = b[2:]

    l, i, v = len(b), 0, 0
    for x in b:
        v += _value(x) * (BASE ** (l - (i + 1)))
        i += 1

    return v


def decodebytes(s):
    """Decodes a string of base62 data into a bytes object.

    :param s: A string to be decoded in base62
    :rtype: bytes
    """

    decoded = decode(s)
    buf = bytearray()
    while decoded > 0:
        buf.append(decoded & 0xff)
        decoded //= 256
    buf.reverse()

    return bytes(buf)


def _value(ch):
    """Decodes an individual digit of a base62 encoded string."""

    try:
        return CHARSET.index(ch)
    except ValueError:
        raise ValueError('base62: Invalid character (%s)' % ch)


def _check_bytes_type(s):
    """Checks if the input is in an appropriate type."""

    if not isinstance(s, bytes):
        msg = 'expected bytes-like object, not %s' % s.__class__.__name__
        raise TypeError(msg)