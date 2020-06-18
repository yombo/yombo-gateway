"""
Various utilities used to perform common functions to help speed development.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2020 by Yombo.
:license: See LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/utils.html>`_
"""
# Import python libraries
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False  # fcntl is not available on windows
import base64
from difflib import SequenceMatcher
from docutils.core import publish_parts
import inspect
import markdown
import math
import os
import random
import re
import string
import textwrap
from typing import Any, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.task import deferLater

# Import 3rd-party libs
import yombo.ext.base62 as base62

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.module import YomboModule
from yombo.utils.decorators import cached, memoize_

logger = None  # This is set by the set_twisted_logger function.
_Yombo = None  # Set by setup_yombo_reference()


def setup_yombo_reference(loader):
    """
    Setup global references to Yombo libraries. This is called by loader::import_libraries()

    :param loader: Pointer to the loader instance.
    :return:
    """
    global _Yombo
    _Yombo = Entity(loader)


def set_twisted_logger(the_logger):
    """
    Called by core.gwservice::start() to setup the utils logger.
    :param logger:
    :return:
    """
    global logger
    logger = the_logger


def dequote(input):
    """
    Removes quotes from a string if it leads and trails with a single or double quote. The leading and trailing string
    must be the same quote type.
    """
    if (input[0] == input[-1]) and input.startswith(("'", '"')):
        return input[1:-1]
    return input


def search_for_executable(executable):
    """
    Searches the user's path for an executable.

    This is blocking, this should be called in a thread using threads.deferToThread()

    :param executable: string - Name of program to find.
    :return: string - path and file
    """
    path = os.environ['PATH']
    paths = path.split(os.pathsep)
    for p in paths:
        f = os.path.join(p, executable)
        if os.path.isfile(f):
            return f
    return None


def get_yombo_instance_type(value):
    """
    Determine what type of Yombo instance is being since, it's it name.

    :param value: An instance of some sort. Returns False if it's not a Yombo instance.
    :return:
    """
    if isinstance(value, YomboLibrary):
        return "library", value._FullName
    elif isinstance(value, YomboModule):
        return "module", value._FullName
    elif isinstance(value, str):
        return "unknown", value
    return None, None


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
        if not name.startswith("__") and not inspect.ismethod(value):
            if startswith_filter is not None:
                if name.startswith(startswith_filter) is False:
                    continue
            if endwith_filter is not None:
                if name.endswith(endwith_filter) is False:
                    continue
            pr[name] = value
    return pr


def pattern_search(look_for, items):
    """
    Allows searching thru a list of items (a dict or list). For example, a list of:

    ["yombo.status.hello", "yombo.status.bye", "visitor.livingroom.hello"]

    You can search using #'s for wildcards consuming ay number of spaces between or +'s
    as a wildcard for only on work.  For example, a search of "#.hello" would result in:

    ["yombo.status.hello", "visitor.livingroom.hello"]

    While a search of "yombo.status.+" would result in:

    ["yombo.status.hello", "yombo.status.bye"]

    :param look_for:
    :param items:
    :return:
    """
    regex = re.compile(look_for.replace("#", ".*").replace("$", "\$").replace("+", "[/\$\s\w\d]+"))
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


def split(the_string, delimiter=","):
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
    start = kwargs.get("start", "__")
    for key, val in kwargs.items():
        if not key.startswith(start):
            data[key] = val
    return data


def bytes_to_unicode(value):
    """
    Converts strings, lists, and dictionariess to unicode (strings). Handles nested items too. Non-strings are
    untouched. Inspired by:
    http://stackoverflow.com/questions/13101653/python-convert-complex-dictionary-of-strings-from-unicode-to-ascii

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
    Converts strings, lists, and dictionaries to bytes. Handles nested items too. Non-strings are untouched.
    Inspired by:
    http://stackoverflow.com/questions/13101653/python-convert-complex-dictionary-of-strings-from-unicode-to-ascii

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


def snake_case(value):
    return value.replace(" ", "_").lower()


def percentage(part, whole):
    """
    Return a float representing a percentage of part against the whole.

    For example: percentage(7, 12) returns: 58.333333333333336

    :param part:
    :param whole:
    :return:
    """
    return 100 * float(part)/float(whole)


def encode_binary(data, encoder: Optional[str] = None, convert_to_unicode: Optional[bool] = True):
    """Converts to text."""
    if encoder is None:
        encoder = "base62"

    if encoder == "base62":
        data = base62.encodebytes(data)
    elif encoder == "base64":
        data = base64.b64encode(data)
    elif encoder == "base85":
        data = base64.b85encode(data)
    else:
        raise YomboWarning("Base compactor type: {encoder}")
    if convert_to_unicode in (None, True):
        return bytes_to_unicode(data)
    return data


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


def do_search_instance(attributes, haystack, allowed_keys, limiter=None, max_results=None,
                       required_field=None, required_value=None,
                       ignore_field=None, ignore_value=None):
    """
    Does the actual search of the devices. It scans through each item in haystack, and searches for any
    supplied attributes using fuzzy logic. The limiter (either specified in the attributes or the limiter
    argument if not supplied in teh attributes) controls how much of a string much match to be included in
    the results.

    Scan through the dictionary (or list), and match keys. Returns the value of
    the best matching key.

    :param attributes: Either a list of dictionaries containing: field, value, limiter or a dictionary
      containing field:values to match.
    :type attributes: list of dictionaries, or a dictionary of attributes/value.
    :param operation: Set weather to all matching, or highest matching. Either "any" or "highest".
    """
    if limiter is None:
        limiter = .90
    if limiter > .99999999:
        limiter = .99
    elif limiter < .10:
        limiter = .10

    if isinstance(attributes, dict):
        new_attributes = []
        for field, value in attributes.items():
            new_attributes.append({
                "field": field,
                "value": value,
                "limiter": limiter,
            })
        attributes = new_attributes
        del new_attributes
    elif isinstance(attributes, list) is False:
        raise YomboWarning("Attributes must be a list.")

    # print(f"do_search_attrs: {attributes}")
    for attr in attributes:
        if isinstance(attr, dict) is False:
            raise YomboWarning("Attribute items must be dictionaries")
        if all(k in ("field", "value") for k in attr):
            raise YomboWarning("Attribute dictionary doesn't have required keys.")
        if attr["field"] not in allowed_keys:
            raise YomboWarning(f"Field is not a valid searchable item: {attr['field']}")

        if "limiter" not in attr:
            attr["limiter"] = limiter
        else:
            if attr["limiter"] is None:
                attr["limiter"] = limiter
            if attr["limiter"] > .99999999999:
                attr["limiter"] = .99
            elif attr["limiter"] < .10:
                attr["limiter"] = .10

    # Prepare the minion
    stringDiff = SequenceMatcher()

    # used when return highest
    best_ratio = 0
    best_limiter = 0

    key_list = []

    for item_id, item in haystack.items():
        if ignore_field is not None:
            if getattr(item, ignore_field) == ignore_value:
                continue
        if required_field is not None:
            if getattr(item, required_field) != required_value:
                continue
        for attr in attributes:
            stringDiff.set_seq1(str(attr["value"]))
            stringDiff.set_seq2(str(getattr(item, attr["field"])))
            ratio = stringDiff.ratio()

            if ratio < limiter:
                continue
            # if this is the best ratio so far - save it and the value
            if ratio > best_ratio:
                best_ratio = ratio
                best_limiter = attr["limiter"]

            key_list.append({"key": item_id, "value": item, "ratio": ratio})

    key_list = sorted(key_list, key=lambda k: k["ratio"], reverse=True)
    result_values = {}
    result_ratios = {}
    for item in key_list:
        if item["key"] in result_values:
            if item["ratio"] > result_ratios[item["key"]]:
                result_ratios[item["key"]] = item["ratio"]
            continue
        result_values[item["key"]] = item["value"]
        result_ratios[item["key"]] = item["ratio"]

        if isinstance(max_results, int) and (len(result_values) == max_results and max_results > 0):
            break

    if best_ratio is None:
        raise KeyError("No items found above the cut off limit.")

    return {
        "was_found": best_ratio >= best_limiter,  # the part that does the actual check.
        "best_ratio": best_ratio,
        "values": result_values,
        "ratios": result_ratios,
    }


def get_method_definition_level(meth):
    for cls in inspect.getmro(meth.__self__.__class__):
        if meth.__name__ in cls.__dict__:
            return str(cls)
    return None


def random_string(**kwargs):
    """
    Generate a random alphanumeric string. *All arguments are kwargs*.

    **Usage**:

    .. code-block:: python

       from yombo.utils import random_string
       someRandonness = random_string(letters="ABCDEF0123456789") #make a hex value

    :param length: Length of the output string. Default: 32
    :type length: int
    :param letters: A string of characters to to create the new string from.
        Default: letters upper and lower, numbers 0-9
    :type letters: string
    :return: A random string that contains choices from `letters`.
    :rtype: string
    """
    length = kwargs.get("length", 32)
    letters = None
    if "char_set" in kwargs:
        char_set = kwargs["char_set"]
        if char_set == "extended":
            letters = "abcdefghijklmnopqrstuvwxyABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!()*-;<>^-{}~"
        else:
            letters = kwargs["char_set"]
    else:
        letters = kwargs.get("letters", None)

    if not hasattr(random_string, "randomStuff"):
        random_string.randomStuff = random.SystemRandom()

    if letters is None:
        lst = [random_string.randomStuff.choice(string.ascii_letters + string.digits) for n in range(length)]
        return "".join(lst)
    else:
        lst = [random_string.randomStuff.choice(letters) for n in range(length)]
        return "".join(lst)


def random_int(middle, percent, **kwargs):
    """
    Generate random integer based on a middle number and percent range.

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
        return textwrap.shorten(value, length)
    return value


def make_link(link, link_text, target=None, options=None):
    if options is None:
        options = ""
    if link == "" or link is None or link.lower() == "None":
        return "None"
    if target is None:
        target = "_self"
    return f'<a href="{link}" target="{target}" {options}>{link_text}</a>'


def format_markdown(input_text, formatting=None):
    if formatting == "restructured" or formatting is None:
        return publish_parts(input_text, writer_name="html")["html_body"]
    elif formatting == "markdown":
        return markdown.markdown(input_text, extensions=["markdown.extensions.nl2br", "markdown.extensions.codehilite"])
    return input_text


def display_hide_none(value, allow_string=None, default=None):
    """
    Changes type None to display "".

    :param value:
    :param allow_string:
    :return:
    """
    if value is None:
        if default is not None:
            return default
        else:
            return ""
    if isinstance(value, str):
        if allow_string is True:
            return value
        if value.lower() == "none":
            return ""
    return value


def human_alphabet():
    """ A subset of the alphabet, but with 1 (one), l (ele) removed."""
    return "ABCDEFGHJKLMNPQRTSUVWXYZabcdefghkmnopqrstuvwxyz23456789"


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
    if not hasattr(get_component, "components"):
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
    provided is "true/True/trUE, etc".

    :param value: String of either "true" or "false" (case insensitive), returns bool or raises YomboWarning.
    """
    if isinstance(value, str):
        if str(value).lower() == "true":
            return True
        elif str(value).lower() == "false":
            return False
        elif str(value).lower() == "none":
            return None
        else:
            raise YomboWarning(f"String is not true, false, or none: {value}")
    if isinstance(value, bool):
        return value
    raise YomboWarning(f"1 String is not true, false, or none: {value}")


def is_true_false(value: Union[str, int, bool], only_bool: Optional[bool] = None) -> bool:
    """
    Used by various utils to determine if an input is high or low. Other functions like is_one_zero and is_yes_no will
    return the results in different ways based on results from here

    :param value: A string, bool, int to test
    :param only_bool: If true, will only return bools. Otherwise, None will be returned if indeterminate input.
    :return:
    """
    only_bool = only_bool or True

    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        value = value.lower()
        if value in (1, "true", "1", "open", "opened", "on", "running", "alive"):
            return True
        if value in (0, "false", "0", "close", "closed", "off", "stopped", "dead"):
            return False
    elif isinstance(value, int):
            if value >= 1:
                return True
            elif value == 0:
                return False
    else:
        if only_bool:
            return False
        else:
            return None


def is_yes_no(value):
    """
    Tries to guess if input is a positive value (1, "1", True, "On", etc). If it is, returns "Yes", otherwise,
    returns "No". Useful to convert something to human Yes/No.
    :param value:
    :return: String on either "Yes" or "No".
    """
    if is_true_false(value, True):
        return "Yes"
    else:
        return "No"


def is_one_zero(value):
    """
    Like is_yes_no, but returns 1 for yes/true/on/open/running, 0 for otherwise.

    Tries to guess if input is a positive value (1, "1", True, "On", etc). If it is, returns "Yes", otherwise,
    returns "No". Useful to convert something to human Yes/No.
    :param value:
    :return:
    """
    if is_true_false(value, True):
        return 1
    else:
        return 0


def is_none(value):
    """
    Returns None type if the input is None type, or a string saying "none". If it"s not, will return the input.

    :param value:
    :return:
    """
    if value is None:
        return None
    elif isinstance(value, str):
        if value.lower() == "none":
            return None
    return value


def forgiving_float(value):
    """
    Primarily used for templates as a filter. Tries to convert input to a float. Doesn"t die if it fails.

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


def test_bit(int_type, offset):
    """
    Tests whether a specific bit is on or off for a given int.

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
           logger.info("I"m refreshed.")

    :param secs: Number of seconds (whole or partial) to sleep for.
    :type secs: int of float
    """
    return deferLater(reactor, secs, lambda: None)
