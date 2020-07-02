#!/usr/bin/env python3
"""
Make a compact sha hash.
"""
from hashlib import sha224, sha256, sha384, sha512
import sys
import os
from time import time

sys.path.append(os.getcwd() + '/../../..')

import yombo.ext.base62 as base62

def bytes_to_unicode(value):
    """
    Converts strings, lists, and dictionarys to unicode. Handles nested items too. Non-strings are untouched.
    Inspired by: http://stackoverflow.com/questions/13101653/python-convert-complex-dictionary-of-strings-from-unicode-to-ascii

    :param value: Convert strings to unicode.
    :type value: dict, list, str
    :return:
    """
    if isinstance(value, dict):
        return dict((bytes_to_unicode(key), bytes_to_unicode(value)) for key, value in value.items())
    elif isinstance(value, list):
        return [bytes_to_unicode(element) for element in value]
    elif isinstance(value, bytes) or isinstance(value, bytearray):
        try:
            return value.decode("utf-8")
        except Exception:
            return value
    else:
        return value


def unicode_to_bytes(value):
    """
    Converts strings, lists, and dictionarys to strings. Handles nested items too. Non-strings are untouched.
    Inspired by: http://stackoverflow.com/questions/13101653/python-convert-complex-dictionary-of-strings-from-unicode-to-ascii

    :param value:
    :return:
    """
    if isinstance(value, dict):
        return dict((unicode_to_bytes(key), unicode_to_bytes(value)) for key, value in value.items())
    elif isinstance(value, list):
        return [unicode_to_bytes(element) for element in value]
    elif isinstance(value, str):
        return value.encode()
    else:
        return value


def sha224_compact(value):
    """
    Returns a shorter sha224 - 38 characters long instead of 56.

    This uses a base62 encoding which uses the entire alphabet, with mixed case.

    Returned length is 38 characters.

    :param value:
    :return:
    """
    return base62.encodebytes(sha224(unicode_to_bytes(value)).digest())


def sha256_compact(value):
    """
    Returns a shorter sha256 - 43 characters long instead of 64.

    This uses a base62 encoding which uses the entire alphabet, with mixed case.

    Returned length is 43 characters.

    :param value:
    :return:
    """
    return base62.encodebytes(sha256(unicode_to_bytes(value)).digest())


def sha384_compact(value):
    """
    Returns a shorter sha384 - 64 characters long instead of 96.

    This uses a base62 encoding which uses the entire alphabet, with mixed case.

    Returned length is 64 characters.

    :param value:
    :return:
    """
    return base62.encodebytes(sha384(unicode_to_bytes(value)).digest())


def sha512_compact(value):
    """
    Returns a shorter sha512 - 86 characters long instead of 128.

    This uses a base62 encoding which uses the entire alphabet, with mixed case.

    Returned length is 86 characters.

    :param value:
    :return:
    """
    return base62.encodebytes(sha512(unicode_to_bytes(value)).digest())


to_encode = "Encoding this data: " + str(time())
sha224_compact_data = sha224_compact(to_encode)
sha256_compact_data = sha256_compact(to_encode)
sha384_compact_data = sha384_compact(to_encode)
sha512_compact_data = sha512_compact(to_encode)

sha224_data = sha224(unicode_to_bytes(to_encode)).hexdigest()
sha256_data = sha256(unicode_to_bytes(to_encode)).hexdigest()
sha384_data = sha384(unicode_to_bytes(to_encode)).hexdigest()
sha512_data = sha512(unicode_to_bytes(to_encode)).hexdigest()

print(f"Data that was encoded: {to_encode}")
print(f"sha224 size: {len(sha224_data)} - {sha224_data}")
print(f"sha256 size: {len(sha256_data)} - {sha256_data}")
print(f"sha384 size: {len(sha384_data)} - {sha384_data}")
print(f"sha512 size: {len(sha512_data)} - {sha512_data}")

print(f"sha224_compact size: {len(sha224_compact_data)} - {sha224_compact_data}")
print(f"sha256_compact size: {len(sha256_compact_data)} - {sha256_compact_data}")
print(f"sha384_compact size: {len(sha384_compact_data)} - {sha384_compact_data}")
print(f"sha512_compact size: {len(sha512_compact_data)} - {sha512_compact_data}")
