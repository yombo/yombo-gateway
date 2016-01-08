"""
Various utilities to help the Yombo Gateway get things done.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries

import inspect
import random
import string
import re

# Import 3rd-party libs
import yombo.ext.six as six


# Import Yombo libraries

def clean_kwargs(**kwargs):
    """
    Returns a dictionary without any keys starting with "__" (double underscore).
    """
    data = {}
    for key, val in six.iteritems(kwargs):
        if not key.startswith('__'):
           data[key] = val
    return data

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
    for key, value in original.iteritems():
        if key not in changes:
            changes[key] = value
        elif isinstance(value, dict):
            dict_merge(value,changes[key])
    return changes

def get_method_definition_level(self, meth):
    for cls in inspect.getmro(meth.im_class):
        if meth.__name__ in cls.__dict__: return str(cls)
    return None

def random_string(**kwargs):
    """
    Generate a random alphanumeric string. *All arguments are kwargs*.

    **Usage**:

    .. code-block:: python

       from yombo.core.helpers import generateRandom
       someRandonness = generateRandom(letters="abcdef0123456") #make a hex value

    :param length: Length of the output string. Default: 32
    :type length: int
    :param letters: A string of characters to to create the new string from.
        Default: letters upper and lower, numbers 0-9
    :type letters: string
    :return: A random string that contains choices from `letters`.
    :rtype: string
    """
    length = kwargs.get('length', 32)
    letters = kwargs.get('letters', None)

    if not hasattr(random_string, 'randomStuff'):
        random_string.randomStuff = random.SystemRandom()

    if letters is None:
        lst = [random_string.randomStuff.choice(string.ascii_letters + string.digits) for n in xrange(length)]
        return "".join(lst)
    else:
        lst = [random_string.randomStuff.choice(letters) for n in xrange(length)]
        return "".join(lst)
