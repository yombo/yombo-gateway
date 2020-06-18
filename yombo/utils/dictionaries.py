"""
Various utilities to manipulate dictionaries.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2016-2020 by Yombo.
:license: See LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/dictionaries.html>`_
"""

# Import python libraries
import itertools
from collections import Mapping
from typing import Any, Callable, Dict, Optional, Union
from collections.abc import Mapping


def dict_len(incoming: dict) -> int:
    """
    Return the size of the keys + values of the dictionary.

    :param incoming: Incomig dictionary.
    :return:
    """
    size = 0
    for key, value in incoming.items():
        size += len(str(key)) + len(str(value))
    return size


def dict_find_key(search_dictionary: dict, val: Any) -> Any:
    """
    Find a key of a dictionary for a given value.

    :param search_dictionary: The dictionary to search.
    :param val: The value to search for.
    :return: The key of dictionary dic given the value
    """
    return [k for k, v in search_dictionary.items() if v == val][0]


def recursive_dict_merge(original: dict, changes: dict):
    """
    Recursively merges a dictionary with any changes. Sub-dictionaries won't be overwritten - just updated.

    *Usage**:

    .. code-block:: python

        my_information = {
            "name": "Mitch"
            "phone: {
                "mobile": "4155551212"
            }
        }

        updated_information = {
            "phone": {
                "home": "4155552121"
            }
        }

        print(recursive_dict_merge(my_information, updated_information))

    # Output:

    .. code-block:: none

        {
            "name": "Mitch"
            "phone: {
                "mobile": "4155551212",
                "home": "4155552121"
            }
        }
    """
    for key, value in changes.items():
        if (key in original and isinstance(original[key], dict)
                and isinstance(changes[key], Mapping)):
            recursive_dict_merge(original[key], changes[key])
        else:
            original[key] = changes[key]
    return original


def dict_diff(dict1: dict, dict2: dict):
    """
    Returns the differences between two dictionaries.

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


def dict_filter(input_dict: dict, key_list: list):
    """
    Returns a new dictionary with only the supplied list of keys.

    :param input_dict:
    :param key_list:
    :return:
    """
    return dict((key, input_dict[key]) for key in key_list if key in input_dict)


# def clean_dict(input_dict: dict, start: Optional[str, List[str]] = None, end: Optional[str, List[str]] = None):
def clean_dict(input_dict: dict, start = None, end=None):
    """
    Returns a dictionary without any keys starting with kwargs["start"] (default "_" underscore).

    :param input_dict: The dictionary to work with.
    :param start: A str or list of string to filter out for keys that start with these values.
    :param end: A str or list of string to filter out for keys that end with these values.
    """
    data = {}
    if isinstance(start, list) is False:
        start = [start, ]
    if isinstance(end, list) is False:
        end = [end, ]
    for key, val in input_dict.items():
        if start is not None:
            dictionary = dictionary[len(filter(dictionary.startswith, start + [''])[0]):]
        if end is not None:
            dictionary = dictionary[len(filter(dictionary.startswith, end + [''])[0]):]
    return data


# from: https://stackoverflow.com/questions/32935232/python-apply-function-to-values-in-nested-dictionary
def map_nested_dicts(item: Any, func: Callable):
    """
    Applies a function to a all keys of a dictionary, including it's nested keys.

    :param ob:
    :param func:
    :return:
    """
    if isinstance(item, Mapping):
        return {k: map_nested_dicts(v, func) for k, v in item.items()}
    else:
        return func(item)


# Based on: https://stackoverflow.com/questions/2352181/how-to-use-a-dot-to-access-members-of-dictionary
# Modified to use either list of strings.
def access_dict(accessor: Union[str, list], input_dict: dict):
    """ Gets data from a dictionary using a dotted accessor-string. """
    current_data = input_dict
    good_path = []
    current_path = []
    if isinstance(accessor, str):
        accessor = accessor.split(".")
    for chunk in accessor:
        current_path.append(chunk)
        try:
            current_data = current_data[chunk]
        except KeyError:
            raise KeyError(f'Last good config path: "{".".join(good_path)}", failed: "{".".join(current_path)}"')
        good_path.append(chunk)
    return current_data


def access_dict_set(accessor: Union[str, list], input_dict: dict, value: Any):
    """ Gets data from a dictionary using a dotted accessor-string """
    current_data = input_dict
    current_path = []

    if isinstance(accessor, str):
        accessor = accessor.split(".")

    for idx, chunk in enumerate(accessor):
        current_path.append(chunk)
        if chunk not in current_path:
            if len(accessor) > len(current_path):
                current_data[chunk] = {}
                current_data = current_data[chunk]
            else:
                current_data[chunk] = value

        # try:
        #     current_data = current_data[chunk]
        # except KeyError:
        #     if idx+1 != len(accessor):
        #         current_data[chunk] = {}
        #         current_data = current_data[chunk]
        #     else:
        #         current_data[chunk] = value
    # return current_data


def slice_dict(input_dict: dict, start: int, stop: int = None, step: int = None):
    """
    Slices a dictionary.
    Usage:
    >>> new_dict = slice_dict(input_dict, stop)  # start = 0 if not specificed
    >>> new_dict = slice_dict(input_dict, start, stop)
    >>> new_dict = slice_dict(input_dict, start, stop, step)

    Examples:
    >>> new_dict = slice_dict(input_dict, 1)  # equiv for a list: some_list[0:1]
    >>> new_dict = slice_dict(input_dict, 2, 4)  # equiv for a list: some_list[2:4]
    >>> new_dict = slice_dict(input_dict, 2, 6)  # Start at 2, end at 6, skiping every other one.

    :param input_dict:
    :param start: Place to start slicing, default is 0
    :param stop: Where to stop slicing
    :param step: Used to skep items, like every other one
    :return:
    """
    if stop is None:
        return dict(itertools.islice(input_dict.items(), start))

    return dict(itertools.islice(input_dict.items(), start, stop, step))


def flatten_dict(input_dict: dict, prefix: Optional[str] = None) -> Dict[str, Any]:
    """
    Flatten out a dictionary, the keys will be in dot notation for nested dicts.

    :param input_dict: The dictionary to flatten.
    :param prefix: Append a prefix to the
    """
    output = {}
    prefix = prefix if isinstance(prefix, str) else ""
    for key, value in input_dict.items():
        if prefix == "":
            key_name = key
        else:
            key_name = f"{prefix}.{key}"
        if isinstance(value, dict):
            output.update(flatten_dict(value, key_name))
        else:
            output[key_name] = value
    return output


def ordereddict_to_dict(input_dict: dict):
    """
    Convert an ordered dict to a regular dict, recursive.

    :param input_dict:
    :return:
    """
    for k, v in input_dict.items():
        if isinstance(v, dict):
            input_dict[k] = ordereddict_to_dict(v)
    return dict(input_dict)
