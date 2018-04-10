"""
Various utilities used to perform common functions to help speed development.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2017 by Yombo.
:license: See LICENSE for details.
"""
# Import python libraries
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    # fcntl is not available on windows
    HAS_FCNTL = False
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from datetime import datetime
from docutils.core import publish_parts
import base64
import binascii
from difflib import SequenceMatcher
import inspect
import markdown
import math
import msgpack
import netifaces
import netaddr
import os
import pkg_resources
from pkg_resources import DistributionNotFound, VersionConflict
import random
import re
import socket
import string
from struct import pack as struct_pack, unpack as struct_unpack
import sys
from time import strftime, localtime
import zlib

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import deferLater
from twisted.internet.defer import Deferred
from twisted.internet.fdesc import readFromFD, writeToFD, setNonBlocking

# Import 3rd-party libs
from yombo.ext.hashids import Hashids

from yombo.core.log import get_logger
from yombo.utils.decorators import deprecated, memoize_ttl, memoize_

logger = get_logger('utils.__init__')

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning


def get_python_package_info(package_name):
    """
    Checks if a given python package name is installed. If so, returns it's info, otherwise returns None.

    :param package_name:
    :return:
    """
    try:
        return pkg_resources.require([package_name])[0]
    except DistributionNotFound as e:
        return None

@inlineCallbacks
def read_file(filename, convert_to_unicode=None):
    """
    Read a file, non-blocking.
    Based from: https://stackoverflow.com/questions/1720816/non-blocking-file-access-with-twisted

    :param filename:
    :return:
    """
    def getFile(filename):
        with open(filename) as f:
            d = Deferred()
            fd = f.fileno()
            setNonBlocking(fd)
            readFromFD(fd, d.callback)
            return d

    contents = yield getFile(filename)
    if convert_to_unicode is True:
        return bytes_to_unicode(contents)
    return contents

def save_file(filename, content, mode=None):
    """
    A quick function to save data to a file. Defaults to overwrite, us mode 'a' to append.

    Don't use this for saving large files.

    :param filename: Full path to save to.
    :param content: Content to save.
    :param mode: File open mode, default to 'w'.
    :return:
    """
    def writeFile(filename, content, mode):
        if mode is None:
            mode = 'w'
        with open(filename, mode) as f:
            fd = f.fileno()
            setNonBlocking(fd)
            writeToFD(fd, content)
    writeFile(filename, unicode_to_bytes(content), mode)

def get_nested_dict(data_dict, map_list):
    """
    Get a dictionary value using keys as a list.
    From: https://stackoverflow.com/questions/14692690/access-nested-dictionary-items-via-a-list-of-keys

    :param dic:
    :param map_list:
    :return:
    """
    for k in map_list: data_dict = data_dict[k]
    return data_dict
    # return reduce(operator.getitem, dic, keys)

def set_nested_dict(dic, keys, value):
    """
    For a given dic(t) and keys, set a value.
    From:https://stackoverflow.com/questions/14692690/access-nested-dictionary-items-via-a-list-of-keys

    >>> d = {}
    >>> set_nested_dict(d, ['computer', 'folder', 'file'], 'yombo.txt')
    >>> d
    {'computer': {'folder': {'file': 'yombo.txt'}}}

    :param dic:
    :param keys:
    :param value:
    :return:
    """
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value

def data_pickle(data, encoder=None, zip_level=None):
    """
    Encodes data with an encoder type. The default is "msgpack_base85". This allows data to be sent to
    databases or nearly everywhere.

    :param data: String, list, or dictionary to be encoded.
    :param encoder: Optional encode method. One of: json, msgpack, msgpack_zip, msgpack_base85, msgpack_base85_zip
    :param zip: True or a compression number from 1 to 9. Only works with msgpack_base85, and converts it to a
      msgpack_base85_zip.

    :return: bytes (not string) of the encoded data that can be used with data_unpickle.
    """
    if zip_level is True:
        zip_level = 5

    if encoder is None:
        if isinstance(zip_level, int):
            if zip_level < 1 or zip_level > 9:
                zip_level=5
            encoder = 'msgpack_base85_zip'
        else:
            encoder = 'msgpack_base85'

    if encoder == 'json':
        try:
            return json.dumps(data, separators=(',', ':'))
        except:
            pass
    elif encoder == 'msgpack':
        try:
            return msgpack.packb(data)
        except:
            pass
    elif encoder == 'msgpack_zip':
        try:
            return zlib.compress(msgpack.packb(data), zip_level)
        except:
            pass
    elif encoder == 'msgpack_base85':
        try:
            return base64.b85encode(msgpack.packb(data))
        except:
            pass
    elif encoder == 'msgpack_base85_zip':
        if isinstance(zip_level, int) is False:
            zip_level = 5
        try:
            return base64.b85encode(zlib.compress(msgpack.packb(data), zip_level))
        except:
            pass
    elif encoder == 'zip':
        if isinstance(zip_level, int) is False:
            zip_level = 5
        try:
            return base64.b85encode(zlib.compress(data))
        except:
            pass
    return data

def data_unpickle(data, encoder=None, zip_level=None):
    """
    Unpack data packed with data_pickle.

    :param data:
    :param encoder:
    :param zip_level:
    :return:
    """
    if encoder is None:
        if zip_level is True or isinstance(zip_level, int):
            encoder = 'msgpack_base85_zip'
        else:
            encoder = 'msgpack_base85'

    if encoder == 'json':
        try:
            return json.loads(data)
        except:
            pass
    elif encoder == 'msgpack':
        try:
            return msgpack.unpackb(data, encoding='utf-8')
        except:
            pass
    elif encoder == 'msgpack_zip':
        try:
            return zlib.decompress(msgpack.unpackb(data, encoding='utf-8'))
        except:
            pass
    elif encoder == 'msgpack_base85':
        try:
            return msgpack.unpackb(base64.b85decode(data), encoding='utf-8')
        except:
            pass
    elif encoder == 'msgpack_base85_zip':
        try:
            return msgpack.unpackb(zlib.decompress(base64.b85decode(data)), encoding='utf-8')
        except:
            pass
    elif encoder == 'zip':
        try:
            return zlib.decompress(base64.b85decode(data))
        except:
            pass
    return data

def instance_properties(obj, startswith_filter=None, endwith_filter=None):
    """
    Get the attributes of an instance and return a dictionary.

    Modified from: https://stackoverflow.com/questions/61517/python-dictionary-from-an-objects-fields
    :param obj:
    :return:
    """
    pr = {}
    for name in dir(obj):
        value = getattr(obj, name)
        if not name.startswith('__') and not inspect.ismethod(value):
            if startswith_filter is not None:
                if name.startswith(startswith_filter) is False:
                    continue
            if endwith_filter is not None:
                if name.endswith(endwith_filter) is False:
                    continue
            pr[name] = value
    return pr

def translate_int_value(value, leftMin, leftMax, rightMin, rightMax):
    """
    Used to translate one scale to another. For example, a light can have 255 steps, but
    we want to display this in percent to a human. This function would return 50:
    .. code-block:: python

       human_status = translate_int_value(127.5, 0, 255, 0, 100)

    From: https://stackoverflow.com/questions/1969240/mapping-a-range-of-values-to-another
    :param value: The value to translate
    :param leftMin: The 'from' range, starting position.
    :param leftMax: The 'from' range, ending position.
    :param rightMin: The 'to' range, starting position.
    :param rightMax: The 'to' range, ending position.
    :return:
    """
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return int(round(rightMin + (valueScaled * rightSpan)))

def convert_temp(i_temp):
    """
    Convert a temperature from celsius to fahrenheit and back. Just input a number followed by C or F.

    Example: 32F  returns a tuple of (0,C)

    Useful when you're too lazy to to use unit_convert below.

    :param temp: A temperature to convert
    :type temp: str
    :return: A tuple containing the value and new unit type
    :rtype: tuple
    """
    degree = float(i_temp[:-1])
    i_convention = i_temp[-1]

    if i_convention.upper() == "C":
        return unit_convert('c_f', degree)
    elif i_convention.upper() == "F":
        return unit_convert('f_c', degree)
    else:
        raise YomboWarning("Invalid temperature requested.")

def pattern_search(look_for, items):
    """
    Allows searching thru a list of items (a dict or list). For example, a list of:

    ['yombo.status.hello', 'yombo.status.bye', 'visitor.livingroom.hello']

    You can search
    using #'s for whilecards consuming any number of spaces between or +'s as a wildcard for only
    on work.  For example, a search of "#.hello" would result in:

    ['yombo.status.hello', 'visitor.livingroom.hello']

    While a search of "yombo.status.+" would result in:

    ['yombo.status.hello', 'yombo.status.bye']

    :param look_for:
    :param items:
    :return:
    """
    regex = re.compile(look_for.replace('#', '.*').replace('$', '\$').replace('+', '[/\$\s\w\d]+'))
    out_list = []
    if isinstance(items, dict):
        for item, data in items.items():
            result = regex.match(item)
            if result is not None:
                out_list.append(item)
    elif isinstance(items, list):
        for item in items:
            result = regex.match(item)
            if result is not None:
                out_list.append(item)
    return out_list


def status_to_string(status):
    if status == 0:
        return 'Disabled'
    elif status == 1:
        return 'Enabled'
    elif status == 2:
        return 'Deleted'
    else:
        return 'Unknown'


def public_to_string(pubic_value):
    pubic_value = int(pubic_value)
    if pubic_value == 0:
        return 'Private'
    elif pubic_value == 1:
        return 'Public Pending'
    elif pubic_value == 2:
        return 'Public'
    else:
        return 'Unknown'


def epoch_to_string(the_time, format_string=None):
    if the_time is None:
        return "None"
    if isinstance(the_time, str):
        try:
            the_time = int(the_time)
        except:
            try:
                the_time = float(the_time)
            except:
                return the_time

    if format_string is None:
        format_string = '%b %d %Y %H:%M:%S %Z'
    return strftime(format_string, localtime(the_time))


def convert_to_seconds(s):
    seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    return int(s[:-1]) * seconds_per_unit[s[-1]]


def split(the_string, delimiter=','):
    """
    Pass in a string, and get back a list. This also ignore white spaces padding the delimiter.

    :param the_string: The string to parse
    :param delimiter: Default: , (commad).
    :return:
    """
    return [x.strip() for x in the_string.split(delimiter)]


def clean_kwargs(**kwargs):
    """
    Returns a dictionary without any keys starting with "__" (double underscore).
    """
    data = {}
    start = kwargs.get('start', '__')
    for key, val in kwargs.items():
        if not key.startswith(start):
            data[key] = val
    return data


def clean_dict(dictionary, **kwargs):
    """
    Returns a dictionary without any keys starting with kwargs['start'] (default '_' underscore).
    """
    data = {}
    start = kwargs.get('start', '_')
    for key, val in dictionary.items():
        if not key.startswith(start):
            data[key] = val
    return data


def bytes_to_unicode(input):
    """
    Converts strings, lists, and dictionarys to unicde. Handles nested items too. Non-strings are untouched.
    Inspired by: http://stackoverflow.com/questions/13101653/python-convert-complex-dictionary-of-strings-from-unicode-to-ascii

    :param input: Convert strings to unicode.
    :type input: dict, list, str
    :return:
    """
    if isinstance(input, dict):
        return dict((bytes_to_unicode(key), bytes_to_unicode(value)) for key, value in input.items())
    elif isinstance(input, list):
        return [bytes_to_unicode(element) for element in input]
    elif isinstance(input, bytes):
        try:
            return input.decode("utf-8")
        except Exception:
            return input
    else:
        return input


def unicode_to_bytes(input):
    """
    Converts strings, lists, and dictionarys to strings. Handles nested items too. Non-strings are untouched.
    Inspired by: http://stackoverflow.com/questions/13101653/python-convert-complex-dictionary-of-strings-from-unicode-to-ascii

    :param input:
    :return:
    """
    if isinstance(input, dict):
        return dict((unicode_to_bytes(key), unicode_to_bytes(value)) for key, value in input.items())
    elif isinstance(input, list):
        return [unicode_to_bytes(element) for element in input]
    elif isinstance(input, str):
        return input.encode()
    else:
        return input


def dict_has_key(dictionary, keys):
    """
    Check if a dictionary has the given list of keys

    **Usage**:

    .. code-block:: python

       from yombo.utils import dict_has_key
       a_dictionary = {'identity': {'location': {'state': 'California'}}}
       a_list = ['identity', 'location', 'state']
       has_state = dict_has_key(a_dictionary, a_list)
       #has_state is now: True

    :param dictionary: A dictionary to check
    :type dictionary: dict
    :param key: A list of keys
    :type key: list
    """
    if not isinstance(keys, list):
        keys = [keys]
    try:
        for key in keys:
             tossaway = dictionary[key]
    except KeyError:
        return False
    except TypeError:
        return False
    else:
        return True


def dict_find_key(symbol_dic, val):
    """
    Find a key of a dictionary for a given key.

    :param symbol_dic: The dictionary to search.
    :type symbol_dic: dict
    :param val: The value to search for.
    :type val: any valid dict key type
    :return: The key of dictionary dic given the value
    :rtype: any valid dict key type
    """
    return [k for k, v in symbol_dic.items() if v == val][0]


def dict_has_value(dictionary, keys, value):
    """
    Check if a dictionary has the value based on a given list of keys

    **Usage**:

    .. code-block:: python

       from yombo.utils import dict_has_value
       a_dictionary = {'identity': {'location': {'state': 'California'}}}
       a_list = ['identity', 'location', 'state']
       has_california = dict_has_value(a_dictionary, a_list, 'California')
       #has_california is now: True

    :param dictionary: A dictionary to check
    :type dictionary: dict
    :param key: A list of keys
    :type key: list
    :param value: The value to test for
    :type value: Any value a dictionary can hold.
    """
    if not isinstance(keys, list):
        keys = [keys]
    try:
        for key in keys[:-1]:
             dictionary = dictionary[key]
        if dictionary[keys[-1]] == value:
            return True
    except KeyError:
        return False
    except TypeError:
        return False
    else:
        return False


def dict_set_value(dictionary, keys, value):
    """
    Set dictionary value based on a given list of keys

    **Usage**:

    .. code-block:: python

       from yombo.utils import dict_set_value
       a_dictionary = {}
       a_list = ['identity', 'location', 'state']
       dict_set_value(a_dictionary, a_list, 'California')
       #a_dictionary now: {'identity': {'location': {'state': 'California'}}}

    :param dictionary: A dictionary to update
    :type dictionary: dict
    :param key: A list of keys
    :type key: list
    :param value: The value to set
    :type value: Any value a dictionary can hold.
    """
    if not isinstance(keys, list):
        keys = [keys]
    for key in keys[:-1]:
         dictionary = dictionary.setdefault(key, {})
    dictionary[keys[-1]] = value


def dict_get_value(dictionary, keys):
    """
    Get dictionary value based on a given list of keys

    **Usage**:

    .. code-block:: python

       from yombo.utils import dict_get_value
       a_dictionary  = {'identity': {'location': {'state': 'California'}}}
       a_list = ['identity', 'location', 'state']
       value = dict_get_value(a_dictionary, a_list)
       #value = 'California'

    :param dictionary: A dictionary to update
    :type dictionary: dict
    :param key: A list of keys
    :type key: list
    """
    if not isinstance(keys, list):
        keys = [keys]
    for key in keys[:-1]:
         dictionary = dictionary.setdefault(key, {})
    return dictionary[keys[-1]]


def dict_merge(original, changes):
    """
    Recursively merges a dictionary with any changes. Sub-dictionaries won't be overwritten - just updated.

    *Usage**:

    .. code-block:: python

        my_information = {
            'name': 'Mitch'
            'phone: {
                'mobile': '4155551212'
            }
        }

        updated_information = {
            'phone': {
                'home': '4155552121'
            }
        }

        print dict_merge(my_information, updated_information)

    # Output:

    .. code-block:: none

        {
            'name': 'Mitch'
            'phone: {
                'mobile': '4155551212',
                'home': '4155552121'
            }
        }
    """
    for key, value in original.items():
        if key not in changes:
            changes[key] = value
        elif isinstance(value, dict):
            dict_merge(value, changes[key])
    return changes


def dict_diff(dict2, dict1):
    """
    Returns the differences between two dictionarys.

    **Usage**:

    .. code-block:: python

       from yombo.utils import dict_diff
       aa = dict(a=1, b=2)
       bb = dict(a=2, b=2)
       added, removed, modified, same = dict_diff(aa, bb)

    :param dict1:
    :param dict2:
    :return:
    """
    dict1_keys = set(dict1.keys())
    dict2_keys = set(dict2.keys())
    intersect_keys = dict1_keys.intersection(dict2_keys)
    added = dict1_keys - dict2_keys
    removed = dict2_keys - dict1_keys
    modified = {o : (dict1[o], dict2[o]) for o in intersect_keys if dict1[o] != dict2[o]}
    same = set(o for o in intersect_keys if dict1[o] == dict2[o])
    return added, removed, modified, same


def fopen(*args, **kwargs):
    """
    A help function that wraps around python open() function. Makes handling files a across platforms easier.

    Modules that are looking to keep files open for reading, such as file monitoring, should use the the
    :py:mod:`yombo.utils.filereader` class.
    """
    # For windows, always use binary mode.
    if kwargs.pop('binary', True):
        if is_windows():
            if len(args) > 1:
                args = list(args)
                if 'b' not in args[1]:
                    args[1] += 'b'
            elif kwargs.get('mode', None):
                if 'b' not in kwargs['mode']:
                    kwargs['mode'] += 'b'
            else:
                # the default is to read
                kwargs['mode'] = 'rb'

    fhandle = open(*args, **kwargs)
    if is_fcntl_available():
        # modify the file descriptor on systems with fcntl
        # unix and unix-like systems only
        try:
            FD_CLOEXEC = fcntl.FD_CLOEXEC   # pylint: disable=C0103
        except AttributeError:
            FD_CLOEXEC = 1                  # pylint: disable=C0103
        old_flags = fcntl.fcntl(fhandle.fileno(), fcntl.F_GETFD)
        fcntl.fcntl(fhandle.fileno(), fcntl.F_SETFD, old_flags | FD_CLOEXEC)
    return fhandle


def save_file(filename, content, mode=None):
    """
    A quick function to save data to a file. Defaults to overwrite, us mode 'a' to append.

    Don't use this for saving large files.

    :param filename: Full path to save to.
    :param content: Content to save.
    :param mode: File open mode, default to 'w'.
    :return:
    """
    if mode is None:
        mode = 'w'
    content = bytes_to_unicode(content)
    f = fopen(filename, mode)
    f.write(content)
    f.close()


def file_last_modified(path_to_file):
    return os.path.getmtime(path_to_file)


def percentage(part, whole):
    """
    Return a float representing a percentage of part against the whole.

    For example: percentage(7, 12) returns: 58.333333333333336

    :param part:
    :param whole:
    :return:
    """
    return 100 * float(part)/float(whole)


def percentile(data_list, percent, key=lambda x:x):
    """
    Find the percentile of a list of values.

    I think this was found here:http://code.activestate.com/recipes/511478-finding-the-percentile-of-the-values/

    :param data_list: A list of values. Note N MUST BE already sorted.
    :param percent: A float value from 0.0 to 1.0.
    :param key: Optional key function to compute value from each element of N

    :return: The percentile of the values
    """
    if not data_list:
        return None
    k = (len(data_list)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(data_list[int(k)])
    d0 = key(data_list[int(f)]) * (c-k)
    d1 = key(data_list[int(c)]) * (k-f)
    return d0+d1



def search_instance(arguments, haystack, allowed_keys, limiter, operation):
    if limiter is None:
        limiter = .89

    if limiter > .99999999:
        limiter = .99
    elif limiter < .10:
        limiter = .10

    attrs = []
    for attr, value in arguments.items():
        if attr in allowed_keys:
            attrs.append(
                {
                    'field': attr,
                    'value': value,
                    'limiter': limiter,
                }
            )

    return do_search_instance(attrs,
                              haystack,
                              allowed_keys,
                              limiter=limiter,
                              operation=operation)


def do_search_instance(attributes, haystack, allowed_keys, limiter=None, operation=None, status_field=None, status_value=None):
    """
    Does the actual search of the devices. It scans through each item in haystack, and searches for any
    supplied attributes.

    Scan through the dictionary, and match keys. Returns the value of
    the best matching key.

    :param attributes: A list of dictionaries containing: field, value, limiter
    :type attributes: list of dictionaries
    :param operation: Set weather to all matching, or highest matching. Either "any" or "highest".
    """
    # logger.info("in do_search_instance...attributes: {attributes}", attributes=attributes)
    # logger.info("in do_search_instance...haystack: {haystack}", haystack=haystack)
    # logger.info("in do_search_instance...allowed_keys: {allowed_keys}", allowed_keys=allowed_keys)

    if limiter is None:
        limiter = .89
    if operation is None:
        operation = "any"
    if isinstance(attributes, list) is False:
        raise YomboWarning("Attributes must be a list.")
    for attr in attributes:
        if isinstance(attr, dict) is False:
            raise YomboWarning("Attribute items must be dictionaries")
        if all(k in ("field", "value") for k in attr):
            raise YomboWarning("Attribute dictionary doesn't have required keys.")
        if attr['field'] not in allowed_keys:
            raise YomboWarning("Field is not a valid searchable item: %s" % attr['field'])
        if "limiter" not in attr:
            attr["limiter"] = .90
        else:
            if attr["limiter"] > .99999999999:
                attr["limiter"] = .99
            elif attr["limiter"] < .10:
                attr["limiter"] = .10

    if status_field is None or status_value is None:
        status_field = None
        status_value = None

    # Prepare the minion
    stringDiff = SequenceMatcher()

    # used when return highest
    best_ratio = 0
    best_limiter = 0
    best_match = None
    best_key = None

    key_list = []
    # sorted_list = None

    for item_id, item in haystack.items():
        if status_value is not None:
            if getattr(item, status_field) != status_value:
                continue
        for attr in attributes:
            stringDiff.set_seq1(str(attr['value']))
            # try:
            stringDiff.set_seq2(str(getattr(item, attr['field'])))
            # except TypeError:
            #     continue  # might get here, even though it's not a string. Catch it!
            ratio = stringDiff.ratio()

            if operation == "any":
                if ratio > attr['limiter']:
                    key_list.append({'key': item_id, 'value': item, 'ratio': ratio})
                    # item[item_id] = item
            else:
                # if this is the best ratio so far - save it and the value
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_limiter = attr['limiter']
                    best_key = item_id
                    best_match = item

                key_list.append({'key': item_id, 'value': item, 'ratio': ratio})

    sorted_list = sorted(key_list, key=lambda k: k['ratio'], reverse=True)


    if operation == "any":
        return (
            best_ratio >= best_limiter,  # the part that does the actual check.
            best_key,
            best_match,
            best_ratio,
            sorted_list)
    else:
        return_list = []
        if best_ratio >= best_limiter:  # if we have one match, only return a list of matches.
            for item in sorted_list:
                if item['ratio'] >= limiter:
                    return_list.append(item)
                    # return (
                    #     best_ratio >= best_limiter,  # the part that does the actual check.
                    #     best_key,
                    #     best_match,
                    #     best_ratio,
                    #     return_list)

        if best_key is None:
            # logger.info("in do_search_instance...attributes: {attributes}", attributes=attributes)
            # logger.info("in do_search_instance...haystack: {haystack}", haystack=haystack)
            # logger.info("in do_search_instance...allowed_keys: {allowed_keys}", allowed_keys=allowed_keys)
            raise KeyError("No items found above the cut off limit.")
        return (
            best_ratio >= best_limiter,  # the part that does the actual check.
            best_key,
            best_match,
            best_ratio,
            sorted_list[:10])

#
# def get_command(commandSearch):
#     """
#     Returns a pointer to a command.
#
#     .. note::
#
#        This shouldn't be used by modules, instead, use the pre-defined pointer
#        *self._Commands*, see: :py:func:`get_commands`.
#
#     :param commandSearch: Search for a given command, by cmdUUID or label. cmdUUID is preferred.
#     :type commandSearch: string - Command UUID or Command Label.
#     :return: The pointer to a single command.
#     :rtype: object
#     """
#     return get_command('yombo.gateway.lib.commands')._search(commandSearch)


def get_method_definition_level(meth):
    for cls in inspect.getmro(meth.__self__.__class__):
        if meth.__name__ in cls.__dict__: return str(cls)
    return None


@memoize_ttl(3600)
def get_local_network_info(ethernet_name = None):
    """
    Collects various information about the local network.
    From: http://stackoverflow.com/questions/3755863/trying-to-use-my-subnet-address-in-python-code
    :return:
    """
    ifaces = netifaces.interfaces()
    # => ['lo', 'eth0', 'eth1']

    if ethernet_name is not None:
        myiface = ethernet_name
    else:
        gws = netifaces.gateways()
        myiface = gws['default'][netifaces.AF_INET][1]

    gws = netifaces.gateways()
    gateway_v4 = list(gws['default'].values())[0][0]

    addrs = netifaces.ifaddresses(myiface)
    # {2: [{'addr': '192.168.1.150',
    #             'broadcast': '192.168.1.255',
    #             'netmask': '255.255.255.0'}],
    #   10: [{'addr': 'fe80::21a:4bff:fe54:a246%eth0',
    #                'netmask': 'ffff:ffff:ffff:ffff::'}],
    #   17: [{'addr': '00:1a:4b:54:a2:46', 'broadcast': 'ff:ff:ff:ff:ff:ff'}]}

    # Get ipv4 stuff
    ipinfo = addrs[socket.AF_INET][0]
    address_v4 = ipinfo['addr']
    netmask_v4 = ipinfo['netmask']
    # Create ip object and get
    cidr_v4 = netaddr.IPNetwork('%s/%s' % (address_v4, netmask_v4))
    # => IPNetwork('192.168.1.150/24')
    network_v4 = cidr_v4.network

    ipinfo = addrs[socket.AF_INET6][0]
    address_v6 = ipinfo['addr'].split('%')[0]
    netmask_v6 = ipinfo['netmask']
    # Create ip object and get
    # cidr_v6 = netaddr.IPNetwork('%s/%s' % (address_v6, netmask_v6))
    # => IPNetwork('192.168.1.150/24')
    # network_v6 = cidr_v6.network


    # => IPAddress('192.168.1.0')
    return {'ipv4':
                {'address': str(address_v4), 'netmask': str(netmask_v4), 'cidr': str(cidr_v4),
                 'network': str(network_v4), 'gateway': str(gateway_v4)},
            'ipv6':
                {'address': str(address_v6), 'netmask': str(netmask_v6), 'gateway': str("")},
            }


@memoize_ttl(600)
def ip_addres_in_local_network(ip_address):
    local_network = get_local_network_info()
    try:
        if ip_address_in_network(ip_address, local_network['ipv4']['cidr']):
            return True
    except:
        pass
    try:
        if ip_address_in_network(ip_address, local_network['ipv6']['cidr']):
            return True
    except:
        pass
    return False


@memoize_ttl(600)
def ip_address_in_network(ip_address, subnetwork):
    """
    from: https://diego.assencio.com/?index=85e407d6c771ba2bc5f02b17714241e2

    Returns True if the given IP address belongs to the
    subnetwork expressed in CIDR notation, otherwise False.
    Both parameters are strings.

    Both IPv4 addresses/subnetworks (e.g. "192.168.1.1"
    and "192.168.1.0/24") and IPv6 addresses/subnetworks (e.g.
    "2a02:a448:ddb0::" and "2a02:a448:ddb0::/44") are accepted.
    """
    (ip_integer, version1) = ip_to_integer(ip_address)
    (ip_lower, ip_upper, version2) = subnetwork_to_ip_range(subnetwork)

    if version1 != version2:
        raise ValueError("incompatible IP versions")

    # print("lower: %s, ip: %s, upper: %s" % (ip_lower, ip_integer, ip_upper))
    # print(ip_lower <= ip_integer <= ip_upper)
    return (ip_lower <= ip_integer <= ip_upper)


def ip_to_integer(ip_address):
    """
    from: https://diego.assencio.com/?index=85e407d6c771ba2bc5f02b17714241e2

    Converts an IP address expressed as a string to its
    representation as an integer value and returns a tuple
    (ip_integer, version), with version being the IP version
    (either 4 or 6).

    Both IPv4 addresses (e.g. "192.168.1.1") and IPv6 addresses
    (e.g. "2a02:a448:ddb0::") are accepted.
    """

    # try parsing the IP address first as IPv4, then as IPv6
    for version in (socket.AF_INET, socket.AF_INET6):

        try:
            ip_hex = socket.inet_pton(version, ip_address)
            ip_integer = int(binascii.hexlify(ip_hex), 16)

            return (ip_integer, 4 if version == socket.AF_INET else 6)
        except:
            pass

    raise ValueError("invalid IP address")


def subnetwork_to_ip_range(subnetwork):
    """
    from: https://diego.assencio.com/?index=85e407d6c771ba2bc5f02b17714241e2

    Returns a tuple (ip_lower, ip_upper, version) containing the
    integer values of the lower and upper IP addresses respectively
    in a subnetwork expressed in CIDR notation (as a string), with
    version being the subnetwork IP version (either 4 or 6).

    Both IPv4 subnetworks (e.g. "192.168.1.0/24") and IPv6
    subnetworks (e.g. "2a02:a448:ddb0::/44") are accepted.
    """

    try:
        fragments = subnetwork.split('/')
        network_prefix = fragments[0]
        netmask_len = int(fragments[1])

        # try parsing the subnetwork first as IPv4, then as IPv6
        for version in (socket.AF_INET, socket.AF_INET6):

            ip_len = 32 if version == socket.AF_INET else 128

            try:
                suffix_mask = (1 << (ip_len - netmask_len)) - 1
                netmask = ((1 << ip_len) - 1) - suffix_mask
                ip_hex = socket.inet_pton(version, network_prefix)
                ip_lower = int(binascii.hexlify(ip_hex), 16) & netmask
                ip_upper = ip_lower + suffix_mask

                return (ip_lower,
                        ip_upper,
                        4 if version == socket.AF_INET else 6)
            except:
                pass
    except:
        pass

    raise ValueError("invalid subnetwork")

@inlineCallbacks
def get_external_ip_address_v4():
    """
    Get the IP address of this machine as seen from the outside world.  THis
    function is primarily used during various internal testing of the Yombo
    Gateway.  This information is reported to the Yombo Service, however, the
    Yombo Service already knows you're IP address during the process of
    downloading configuration files.

    Yombo servers will only use this information if server "getpeer.ip()" function
    results in a private IP address.  See: http://en.wikipedia.org/wiki/Private_network
    This assists in Yombo performing various tests internally, but still providing
    an ability to do further tests.

    Gives Yombo servers a hint of your external ip address from your view. This
    should be the same as what Yombo servers see when you connect.

    This is called only once during the startup phase.  Calling this function too
    often can result in the gateway being blocked by whatismyip.org

    .. warning::

       This is 100% blocking code. A replacement will be coming soon.

    :return: An ip address
    :rtype: string
    """
    import treq

    response = yield treq.get("https://api.ipify.org")
    content = yield treq.content(response)
    return content.decode().strip()


def ip_address_to_int(address):
    return struct_unpack("!I", socket.inet_aton(address))[0]


def int_to_ip_address(address):
    return socket.inet_ntoa(struct_pack("!I", address))


def random_string(**kwargs):
    """
    Generate a random alphanumeric string. *All arguments are kwargs*.

    **Usage**:

    .. code-block:: python

       from yombo.utils import random_string
       someRandonness = random_string(letters="abcdef0123456") #make a hex value

    :param length: Length of the output string. Default: 32
    :type length: int
    :param letters: A string of characters to to create the new string from.
        Default: letters upper and lower, numbers 0-9
    :type letters: string
    :return: A random string that contains choices from `letters`.
    :rtype: string
    """
    length = kwargs.get('length', 32)
    letters = None
    if 'char_set' in kwargs:
        char_set = kwargs['char_set']
        if char_set == 'extended':
            letters = "abcdefghijklmnopqrstuvwxyABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!%()*-;<=>^-{}~"
        else:
            letters = kwargs['char_set']
    else:
        letters = kwargs.get('letters', None)

    if not hasattr(random_string, 'randomStuff'):
        random_string.randomStuff = random.SystemRandom()

    if letters is None:
        lst = [random_string.randomStuff.choice(string.ascii_letters + string.digits) for n in range(length)]
        return "".join(lst)
    else:
        lst = [random_string.randomStuff.choice(letters) for n in range(length)]
        return "".join(lst)

def random_int(middle, percent, **kwargs):
    """
    Generate random integer based a middle number and percent range.

    **Usage**:

    .. code-block:: python

       from yombo.utils import random_int
       someRandonness = random_string(1000, .40)  # get a random number 600 and 1400

    :param middle: The middle number of the rang to get
    :type middle: int
    :param percent: A percentage to range from.
    :type percent: float
    :return: A random number
    :rtype: int
    """

    start = round(middle - (middle * percent))
    end = round(middle + (middle * percent))
    return random.randint(start, end)


def excerpt(value, length=None):
    if length is None:
        length = 25

    if isinstance(value, str):
        if len(value) > length:
            return "%s..." % value[:length]
    return value


def make_link(link, link_text, target = None):
    if link == '' or link is None or link.lower() == "None":
        return "None"
    if target is None:
        target = "_self"
    return '<a href="%s" target="%s">%s</a>' % (link, target, link_text)


def format_markdown(input_text, formatting=None):
    if formatting == 'restructured' or formatting is None:
        return publish_parts(input_text, writer_name='html')['html_body']
    elif formatting == 'markdown':
        return markdown.markdown(input_text, extensions=['markdown.extensions.nl2br', 'markdown.extensions.codehilite'])
    return input_text


def display_hide_none(input, allow_string=None):
    if input is None:
        return ""
    if isinstance(input, str):
        if allow_string is True:
            return input
        if input.lower() == "none":
            return ""
    return input


def human_alpabet():
    return "ABCDEFGHJKLMNPQRTSUVWXYZabcdefghkmnopqrstuvwxyz23456789"


def generate_uuid(**kwargs):
    """
    Create a 30 character UUID, where only 26 of the characters are random.
    The remaining 4 characters are used by developers to track where a
    UUID originated from.

    **All arguments are kwargs.**

    **Usage**:

    .. code-block:: python

       from yombo.utils import generate_uuid
       newUUID = generate_uuid(maintype='G', subtype='a2A')

    :param maintype: A single alphanumeric (0-9, a-z, A-Z) to note the uuid main type.
    :type maintype: char
    :param maintype: Up to 3 characters (0-9, a-z, A-Z) to note the uuid sub type.
    :type subtype: string
    :return: A random string, with source identifiers at the end, 30 bytes in length.
    :rtype: string
    """
    uuid = random_string(length=26)
    maintype= kwargs.get('maintype', 'z')
    subtype= kwargs.get('subtype', 'zzz')

    okPattern = re.compile(r'([0-9a-zA-Z]+)')

    m = re.search(okPattern, maintype)
    if m:
        pass
    else:
        maintype = "z"
        subtype = "zzz"

    m = re.search(okPattern, subtype)
    if m:
        pass
    else:
        subtype = "zzz"

    if len(maintype) != 1:
        type = "z";

    if len(subtype) == 1:
        subtype = "zz" + subtype
    elif len(subtype) == 2:
        subtype = "z" + subtype
    elif len(subtype) == 3:
        pass
    else:
        subtype = "zzz"

    tempit = uuid + subtype + maintype
    return tempit

@inlineCallbacks
def global_invoke_all(hook, **kwargs):
    """
    Call all hooks in libraries and modules. Basically a shortcut for calling module_invoke_all and libraries_invoke_all
    methods.

    :param hook: The hook name to call.
    :param kwargs: kwargs to send to the function.
    :return: a dictionary of results.
    """
    # print("global_invoke will call: %s" % hook)
    lib_results = yield get_component('yombo.gateway.lib.loader').library_invoke_all(hook, True, **kwargs)
    modules_results = yield get_component('yombo.gateway.lib.modules').module_invoke_all(hook, True, **kwargs)
    return dict_merge(modules_results, lib_results)

@inlineCallbacks
def global_invoke_libraries(hook, **kwargs):
    """
    Call all hooks in libraries and modules. Basically a shortcut for calling module_invoke_all and libraries_invoke_all
    methods.

    :param hook: The hook name to call.
    :param kwargs: kwargs to send to the function.
    :return: a dictionary of results.
    """
    lib_results = yield get_component('yombo.gateway.lib.loader').library_invoke_all(hook, True, **kwargs)
    return lib_results

@inlineCallbacks
def global_invoke_modules(hook, **kwargs):
    """
    Call all hooks in libraries and modules. Basically a shortcut for calling module_invoke_all and libraries_invoke_all
    methods.

    :param hook: The hook name to call.
    :param kwargs: kwargs to send to the function.
    :return: a dictionary of results.
    """
    modules_results = yield get_component('yombo.gateway.lib.modules').module_invoke_all(hook, True, **kwargs)
    return modules_results

@memoize_ttl(3600)
def get_public_gw_id():
    configs = get_component('yombo.gateway.lib.configuration')
    try:
        gwid = configs.get('core', 'gwid')[0:6] + ":" + configs.get('core', 'gwuuid')[0:5]
        return gwid
    except:
        return "unknown"

def get_component(name):
    """
    Return loaded component (module or library). This can be used to find
    other modules or libraries. The getComponent uses the :ref:`FuzzySearch <fuzzysearch>`
    class to make searching easier, but can only be off one or two letters
    due to importance of selecting the correct library or module.

    :raises KeyError: When the requested component cannot be found.
    :param name: The name of the component (library or module) to find.  Returns a
        pointer to the object so it's functions and attributes can be accessed.
    :type name: string
    :return: Pointer to requested library or module.
    :rtype: Object reference
    """
    if not hasattr(get_component, 'components'):
        from yombo.lib.loader import get_the_loaded_components
        get_component.components = get_the_loaded_components()
    try:
        return get_component.components[name.lower()]
    except KeyError:
        raise KeyError("No such loaded component:" + str(name))


def is_string_bool(value=None):
    """
    Returns a True/False/None based on the string. If nothing is found, "YomboWarning" is raised.
    Returns a boolean value representing the "truth" of the value passed. Returns true if the string
    provided is 'true/True/trUE, etc'.

    :param value: String of either "true" or "false" (case insensitive), returns bool or raises YomboWarning.
    """
    if isinstance(value, str):
        if str(value).lower() == 'true':
            return True
        elif str(value).lower() == 'false':
            return False
        elif str(value).lower() == 'none':
            return None
        else:
            raise YomboWarning("String is not true, false, or none.")
    if isinstance(value, bool):
        return value
    raise YomboWarning("String is not true, false, or none.")


def is_true_false(input, only_bool=False):
    """
    Used by various utils to determine if an input is high or low. Other functions like is_one_zero and is_yes_no will
    return the results in different ways based on results from here

    :param input: A string, bool, int to test
    :param only_bool: If true, will only return bools. Otherwise, None will be returned if indeterminate input.
    :return:
    """
    if isinstance(input, bool):
            return input
    elif isinstance(input, str):
        input = input.lower()
        if input in (1, "true", "1", "open", "on", "running"):
            return True
        if input in (0, "false", "0", "closed", "off", "stopped"):
            return False
    elif isinstance(input, int):
            if input == 1:
                return True
            elif input == 0:
                return False
    else:
        if only_bool:
            return False
        else:
            return None


def is_yes_no(input):
    """
    Tries to guess if input is a positive value (1, "1", True, "On", etc). If it is, returns "Yes", otherwise,
    returns "No". Useful to convert something to human Yes/No.
    :param input:
    :return: String on either "Yes" or "No".
    """
    if is_true_false(input, True):
        return "Yes"
    else:
        return "No"


def is_one_zero(input):
    """
    Like is_yes_no, but returns 1 for yes/true/on/open/running, 0 for otherwise.

    Tries to guess if input is a positive value (1, "1", True, "On", etc). If it is, returns "Yes", otherwise,
    returns "No". Useful to convert something to human Yes/No.
    :param input:
    :return:
    """
    if is_true_false(input, True):
        return 1
    else:
        return 0


def is_none(input):
    """
    Returns None type if the input is None type, or a string saying "none". If it's not, will return the input.

    :param input:
    :return:
    """
    if input is None:
        return None
    elif isinstance(input, str):
        if input.lower() == "none":
            return None
    return input


def forgiving_float(value):
    """
    Primarily used for templates as a filter. Tries to convert input to a float. Doesn't die if it fails.

    :param value:
    :return:
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return value


def forgiving_round(value, precision=0):
    """
    Primarily used for templates as a filter. Rounds string, int, or float Accepts a precision to
    determine number of decimals places.

    :param precision:
    """
    try:
        value = round(float(value), precision)
        return int(value) if precision == 0 else value
    except (ValueError, TypeError):
        return value  # return input if value cannot be rounded.


def multiply(value, amount):
    """
    Primarily used for templates as a filter. Takes an int, string, or float and multiplies it.

    :param value: Input
    :param amount: Multiplier
    """
    try:
        return float(value) * amount
    except (ValueError, TypeError):
        return value  # return input if value cannot be multiplied.


def logarithm(value, base=math.e):
    """
    Primarily used for templates as a filter. Performs logarithm math to a value.

    :param value:
    :param base:
    """
    try:
        return math.log(float(value), float(base))
    except (ValueError, TypeError):
        return value  # return input if value cannot be processed.

def strptime(string, fmt):
    """
    Primarily used for templates as a filter. Parse a time string to datetime.
    :param string:
    :param fmt:
    :return:
    """
    try:
        return datetime.strptime(string, fmt)
    except (ValueError, AttributeError):
        return string  # return input if value cannot be processed.


def fail_when_undefined(value):
    """Filter to force a failure when the value is undefined."""
    if isinstance(value, jinja2.Undefined):
        value()
    return value


def test_bit(int_type, offset):
    """
    Tests wether a specific bit is on or off for a given int.

    :param int_type: The given int to interrogate.
    :type int_type: int
    :param offset: The bit location to return, starting from lowest to highest.
    :type offset: int
    :return: If the bit is on or off
    """
    mask = 1 << offset
    if (int_type & mask) > 0:
        return 1
    else:
        return 0
    # return int_type & mask


class ViewAsObject(object):
    def __init__(self, d):
        self.__dict__ = d


def sleep(secs):
    """
    A simple non-blocking sleep function.  This generates a twisted
    deferred. You have to decorate your function to make the yield work
    properly.

    **Usage**:

    .. code-block:: python

       from twisted.internet import defer
       from yombo.core.helpers import sleep

       @defer.inlineCallbacks
       def myFunction(self):
           logger.info("About to sleep.")
           yield sleep(5.4) # sleep 5.4 seconds.
           logger.info("I'm refreshed.")

    :param secs: Number of seconds (whole or partial) to sleep for.
    :type secs: int of float
    """
    return deferLater(reactor, secs, lambda: None)


def hashid_encode(input_value, min_length=2, salt='', alphabet='ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvxyz234'):
    """
    Encodes an int and returns a string. This typically shortens the length and is great for
    showing users a better representation of a large int - if they don't care about the actual value.

    :param input_value: Int - Input value to encode to a string.
    :param min_length: Int - Minimum length string should be. Will pad if required.
    :param salt: String - A salt to mangle the value. This isn't secure!
    :param alphabet: String -
    :return:
    """
    hashid = Hashids(salt, min_length, alphabet)
    return hashid.encode(input_value)


def hashid_decode(input_value, min_length=2, salt='', alphabet='ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvxyz234'):
    hashid = Hashids(salt, min_length, alphabet)
    return hashid.decode(input_value)

# basic conversions

unit_converters = {
    'km_mi': lambda x: x*0.62137119,  # miles
    'mi_km': lambda x: x*1.6093,  # kilometers
    'm_ft': lambda x: x*3.28084,  # feet
    'ft_m': lambda x: x*0.3048,  # meters
    'cm_in': lambda x: x*0.39370079,  # inches
    'in_cm': lambda x: x*2.54,  # inches
    'oz_g': lambda x: x*28.34952,  # grams
    'g_oz': lambda x: x*0.03527396195,  # ounces
    'kg_lb': lambda x: x*2.20462262185,  # pounds
    'lb_kg': lambda x: x*0.45359237,  # pounds
    'f_c': lambda x: float((x - 32) * (5.0/9.0)),  # celsius
    'f_f': lambda x: x,
    'c_f': lambda x: float((x * (9.0/5.0)) + 32),  # fahrenheit
    'c_c': lambda x: x,
    'btu_kwh': lambda x: x*0.00029307107017,  # kilowatt-hour
    'btu_btu': lambda x: x,
    'kwh_btu': lambda x: x*3412.14163312794,  # btu
    'kwh_kwg': lambda x: x,
}


def unit_convert(unit_type, unit_size):
    """
    Converst various types of lenghts, masses, and temperatures. The format of the list below is: (from)_(to)
    For example, "g_oz" converts from grams to ounces.

    Usage: yombo.utils.unit_convert('km_mi', 10)  # returns 10 km in miles.

    Valid unit_types:
    'km_mi' - kilometers to miles
    'mi_km' - miles to kilometers
    'm_ft' - meters to feet
    'ft_m' - feet to meters
    'cm_in' - centimeter to inches
    'in_cm' - inches to centimeters
    'oz_g' - ounces to grames
    'g_oz' - grames to ounces
    'kg_lb' - kilograms to pounds
    'lb_kg' - pounts to kilograms
    'f_c' - fahrenheit to celsius
    'c_f' - celsius to fahrenheit
    'btu_kwh' - btu's to kilowatt-hours
    'kwh_btu' - kilowatt-hours to btu's

    :param unit_type: string - unit types to convert from_to
    :param unit_size: int or float - value to convert
    :return: float - converted unit
    """
    return unit_converters[unit_type](unit_size)


@memoize_
def is_freebsd():
    """
    Returns if the host is freebsd or not
    """
    return sys.platform.startswith('freebsd')


@memoize_
def is_linux():
    """
    Returns if the host is linus or not
    """
    return sys.platform.startswith('linux')


@memoize_
def is_windows():
    """
    Returns if the host is windows or not
    """
    return sys.platform.startswith('win')


@memoize_
def is_sunos():
    """
    Returns if the host is sunos or not
    """
    return sys.platform.startswith('sunos')


@memoize_
def is_fcntl_available(check_sunos=False):
    """
    Simple function to check if the `fcntl` module is available or not.

    If `check_sunos` is passed as `True` an additional check to see if host is
    SunOS is also made.
    """
    if check_sunos and is_sunos():
        return False
    return HAS_FCNTL
