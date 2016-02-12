"""
Various utilities to help the Yombo Gateway get things done.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    # fcntl is not available on windows
    HAS_FCNTL = False

import inspect
import random
import string
import sys
#import re

#from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import deferLater
from twisted.internet import reactor

# Import 3rd-party libs
from yombo.utils.decorators import memoize_
import yombo.ext.six as six

# Import Yombo libraries
from yombo.core.exceptions import YomboNoSuchLoadedComponentError, YomboWarning

def clean_kwargs(**kwargs):
    """
    Returns a dictionary without any keys starting with "__" (double underscore).
    """
    data = {}
    start = kwargs.get('start', '__')
    for key, val in six.iteritems(kwargs):
        if not key.startswith(start):
            data[key] = val
    return data

def clean_dict(dictionary, **kwargs):
    """
    Returns a dictionary without any keys starting with kwargs['start'] (default '_' underscore).
    """
    data = {}
    start = kwargs.get('start', '_')
    for key, val in six.iteritems(dictionary):
        if not key.startswith(start):
            data[key] = val
    return data

def dict_has_key(dictionary, keys):
    """
    Check if a dictionary has the given list of keys

    **Usage**:

    .. code-block:: python

       from yombo.utils import dict_has_key
       a_dictionary = {'identity': {'location': {'state': 'California'}}}
       a_list = ['identity', 'location', 'state']
       has_state = dict_has_value(a_dictionary, a_list)
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
             dictionary = dictionary[key]
    except KeyError:
        return False
    except TypeError:
        return False
    else:
        return True

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
       a_dictionary = {}
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
    for key, value in original.iteritems():
        if key not in changes:
            changes[key] = value
        elif isinstance(value, dict):
            dict_merge(value, changes[key])
    return changes

def fopen(*args, **kwargs):
    """
    A help function that wraps around python open() function.
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

def get_command(commandSearch):
    """
    Returns a pointer to a command.

    .. note::

       This shouldn't be used by modules, instead, use the pre-defined pointer
       *self._Commands*, see: :py:func:`get_commands`.

    :param commandSearch: Search for a given command, by cmdUUID or label. cmdUUID is preferred.
    :type commandSearch: string - Command UUID or Command Label.
    :return: The pointer to a single command.
    :rtype: object
    """
    return get_command('yombo.gateway.lib.commands')._search(commandSearch)

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

def get_device(deviceSearch):
    """
    Returns a pointer to device.

    .. note::

       This shouldn't be used by modules, instead, use the pre-set point of
       *self._Devices*, see: :py:func:`getDevices`.

    :param deviceSearch: Which device to search for.  device_id or Device Label. device_id preferred.
    :type deviceSearch: string - Device UUID or Device Label.
    :return: The pointer to the requested device.
    :rtype: object
    """
    return getComponent('yombo.gateway.lib.devices').get_device(deviceSearch)

def get_devices_by_device_type():
    """
    Returns a pointer to a **function** to get all devices for a given device_type_id or MachineLabel. Modules
    should use the built in function ``self._DevicesByDeviceType``.

    .. note::

       For modules, there is already a pre-defined function for getting all devices
       of a specific type. It's "self._DevicesByType".

    **Short Usage**:

        >>> deviceList = self._DevicesByDeviceType('137ab129da9318')  #by device_type_id, this is a function.

    **Usage**:

    .. code-block:: python

       # A simple all x10 lights off (regardless of house / unit code)
       allX10Lamps = self._DevicesByType('137ab129da9318')

       # Turn off all x10 lamps
       for lamp in allX10Lamps:
           lamp.sendCmd(self, array('skippincode':True, 'cmd': 'off'))

    :param deviceType: The deviceType to search for, either a UUID or Machinelabel
    :type device_type_id: string
    :return: Returns a pointer to function that can be called to fetch
        all devices belonging to a device type UUID.
    :rtype:
    """
    return getattr(getComponent('yombo.gateway.lib.devices'), "get_devices_by_device_type")

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

    :param hook: The hook name to call.
    :param kwargs: kwargs to send to the function.
    :return: a dictionary of results.
    """
    lib_results = get_component('yombo.gateway.lib.loader').library_invoke_all(hook, True)
    modules_results = get_component('yombo.gateway.lib.modules').module_invoke_all(hook, True)
    return dict_merge(modules_results, lib_results)

def is_string_bool(value=None):
    """
    Returns a True/False/None based on the string. If nothing is found, "YomboWarning" is raised.
    Returns a boolean value representing the "truth" of the value passed. The
    rules for what is a "True" value are:
        2. The string values "True" and "true"
    """
    if isinstance(value, six.string_types):
        if str(value).lower() == 'true':
            return True
        elif str(value).lower() == 'false':
            return False
        elif str(value).lower() == 'none':
            return None
    raise YomboWarning("String is not true, false, or none.")

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