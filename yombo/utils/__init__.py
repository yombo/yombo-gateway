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
#from yombo.utils.decorators import memoize_

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

def get_component(name):
    """
    Return loaded component (module or library). This can be used to find
    other modules or libraries. The getComponent uses the :ref:`FuzzySearch <fuzzysearch>`
    class to make searching easier, but can only be off one or two letters
    due to importance of selecting the correct library or module.

    All component names are stored in lower case, the search will convert
    requests to lower case.

    **Usage**:

    .. code-block:: python

       from yombo.core.helpers import getComponent
       someOtherModule = getComponent("Yombo.Gateway.module.someOtherModule")
       someOtherModule.setDisplay("Hello world.") # this module would set the
                                                  # display and send a device
                                                  # status message

    :raises YomboNoSuchLoadedComponentError: When the requested component cannot be found.
    :param name: The name of the component (library or module) to find.  Returns a
        pointer to the object so it's functions and attributes can be accessed.
    :type name: string
    :return: Pointer to requested library or module.
    :rtype: Object reference
    """
    if not hasattr(get_component, 'components'):
        from yombo.lib.loader import getTheLoadedComponents
        get_component.components = getTheLoadedComponents()
    try:
        return get_component.components[name.lower()]
    except KeyError:
        raise YomboNoSuchLoadedComponentError("No such loaded component:" + str(name))

def get_method_definition_level(meth):
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

def global_invoke_all(hook, **kwargs):
    """
    Call all hooks in libraries and modules. Basically a shortcut for calling module_invoke_all and libraries_invoke_all
    methods.

    :param hook: The hookname to call.
    :param kwargs: kwargs to send to the function.
    :return: a dictionary of results.
    """

    modules_results = get_component('yombo.gateway.lib.modules').module_invoke_all(hook)
    return modules_results

    # we cut this off here for now...
#    lib_results = get_component('yombo.gateway.lib.loader').library_invoke_all(hook)
    return dict_merge(modules_results, lib_results)
