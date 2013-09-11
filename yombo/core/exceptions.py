#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at U{http://www.yombo.net}
"""
Create various exceptions to be used throughout the Yombo
gateway.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""

class GWException(Exception):
    """
    Extends *Exception* - A non-fatal generic gateway exception that is used for minor errors.
    """
    def __init__(self, message, errorno=1, name="unknown", component="component"):
        """
        :param message: The error message to log/display.
        :type message: string
        :param errorno: The error number to log/display.
        :type errorno: int
        :param name: Name of the library, component, or module rasing the exception.
        :type name: string
        :param component: What type of ojbect is calling: component, library, or module
        :type component: string
        """
        Exception.__init__(self)
        self.message = message
        self.errorno = errorno
        self.component = component
        self.name = name

    def __str__(self):
        """
        Formats the exception for logging to text.

        :return: A formated string of the error message.
        :rtype: string
        """
        output = "%d: %s  In %s '%s'." % (self.errorno, self.message, self.component, self.name)
        return repr(output)

class GWWarning(GWException):
    """
    Extends *Exception* - A non-fatal warning gateway exception that is used for items needing user attention.
    """
    def __init__(self, message, errorno, name="unknown", component="component"):
        """
        Setup the GWWarning and then pass everying to GWException
        
        :param message: The error message to log/display.
        :type message: string
        :param errorno: The error number to log/display.
        :type errorno: int
        :param name: Name of the library, component, or module rasing the exception.
        :type name: string
        :param component: What type of ojbect is calling: component, library, or module
        :type component: string
        """
        GWException.__init__(self, message, errorno, component, name)

class GWCritical(RuntimeWarning):
    """
    Extends *RuntimeWarning* - A **fatal error** gateway exception - **forces the gateway to quit**.
    """
    def __init__(self, message, errorno, name="unknown", component="component"):
        """
        Setup the GWCritical. When caught, call the exit function of this exception to
        exit the gateway.

        :todo: Add to logging once the logging library is completed.
        :param message: The error message to log/display.
        :type message: string
        :param errorno: The error number to log/display.
        :type errorno: int
        :param name: Name of the library, component, or module rasing the exception.
        :type name: string
        :param component: What type of ojbect is calling: component, library, or module
        :type component: string
        """
        self.message = message
        self.errorno = errorno
        self.component = component
        self.name = name
        self.exit()

    def __str__(self):
        """
        Formats the exception for logging to text.

        :return: A formated string of the error message.
        :rtype: string
        """

        output = "%d: %s  In '%s' (type:%s)." % (self.errorno, self.message, self.component, self.name)
        return repr(output)

    def exit(self):
        """
        Kills the gateway, won't be restarted.
        """
        from twisted.internet import reactor
        import os
        reactor.addSystemEventTrigger('after', 'shutdown', os._exit, 1)
        reactor.stop()

class GWRestart(RuntimeWarning):
    """
    Extends *RunningWarning* - Restarts the gateway, not a fatal exception.  
    """
    def __init__(self, message):
        """
        :param message: The error message to log/display.
        :type message: string
        """
        self.name = name
        self.exit()

    def __str__(self):
        """
        Formats the exception for logging to text.

        @return: A formated string of the error message.
        @rtype: string
        """
        output = "Restarting Yombo Gateway. Reason: %s." % (self.message)
        return repr(output)

    def exit(self):
        """
        Exists the daemon with exit status 127 so that the wrapper script knows to restart the gateway.
        """
        from twisted.internet import reactor
        import os
        reactor.addSystemEventTrigger('after', 'shutdown', os._exit, 127)
        reactor.stop()

class ImproperlyConfigured(GWWarning):
    """
    Extends :class:`GWWarning` - A missing configuration or improperly configured option.
    """
    pass

class SuspiciousOperation(GWWarning):
    """
    Extends :class:`GWWarning` - Service detected something suspicious and stopped that activity.
    """
    pass

class ModuleWarning(GWWarning):
    """
    Extends :class:`GWWarning` - Same as calling GWWarning, but sets component type to "module".
    """
    def __init__(self, message, errorno, moduleObj):
        """
        :param message: The error message to log/display.
        :type message: string
        :param errorno: The error number to log/display.
        :type errorno: int
        :param moduleObj: The module instance.
        :type moduleObj: Module
        """
        GWWarning.__init__(self, message, errorno, "module", moduleObj._Name)

class ModuleCritical(GWCritical):
    """
    Extends :class:`GWCritical` - Same as calling GWCritical, but sets the component type to 
    "module" - **this forces the gateway to quit**.
    """
    def __init__(self, message, errorno, moduleObj):
        """
        :param message: The error message to log/display.
        :type message: string
        :param errorno: The error number to log/display.
        :type errorno: int
        :param moduleObj: Name of the library, component, or module rasing the exception.
        :type moduleObj: string
        """
        GWCritical.__init__(self, message, errorno, "module", moduleObj._Name)

class LibraryWarning(GWWarning):
    """
    Extends :class:`GWWarning` - Same as calling GWWarning, but sets component type to "library".
    """
    def __init__(self, message, errorno, moduleObj):
        GWWarning.__init__(self, message, errorno, "library", moduleObj._Name)

class LibraryCritical(GWCritical):
    """
    Extends :class:`GWCritical` - Same as calling GWCritical, but sets the component type to 
    "library" - **this forces the gateway to quit**.
    """
    def __init__(self, message, errorno, moduleObj):
        GWCritical.__init__(self, message, errorno, "library", moduleObj._Name)

class MessageError(Exception):
    """
    Extends *Exception* - A non-fatal message exception used to catch message errors.

    :cvar message: (message) The message object.
    :cvar name: (string) Name of the library, component, or module rasing the exception.
    """
    def __init__(self, message, name="unknown"):
        """
        :param message: The error message to log/display.
        :type message: string
        :param name: Name of the library, component, or module rasing the exception.
        :type name: string
        """

        Exception.__init__(self)
        self.message = message
        self.name = name

    def __str__(self):
        """
        Formats the exception for logging to text.

        :return: A formated string of the error message.
        :rtype: string
        """
        output = "Message API Error: '%s' Raised from: '%s'." % (self.message, self.name)
        return repr(output)

class FileError(Exception):
    """
    Extends *Exception* - A non-fatal message exception used to catch file errors.

    :cvar message: (message) The message object.
    :cvar name: (string) Name of the library, component, or module rasing the exception.
    """
    def __init__(self, message, name="unknown"):
        """
        :param message: The error message to log/display.
        :type message: string
        :param name: Name of the library, component, or module rasing the exception.
        :type name: string
        """

        Exception.__init__(self)
        self.message = message
        self.name = name

    def __str__(self):
        """
        Formats the exception for logging to text.

        :return: A formated string of the error message.
        :rtype: string
        """
        output = "File API Error: '%s' Raised from: '%s'." % (self.message, self.name)
        return repr(output)

class DeviceError(Exception):
    """
    Extends *Exception* - A non-fatal device exception used to catch device errors.

    Depending on where the error was caused, this expection will have varying
    amounts of information.
        
    kwargs accepts and processes the following:
        
        - deviceUUID - The deviceUUID the error is about.
        - errorno - An error number for further sorting/processing.
        
    Additionally, if this is the result of a search exception, it may also
    contain some of the error components of the :class:`FuzzySearchError`,
    such as:
        
        - key: The best matching key, in this case would be the deviceUUID (string).
        - value: The best matchin value, in this case would be the device instance (object).
        - ratio: The ratio as a percent of closeness. IE: .32
        - others: Other top 5 choices in a dictionary to choose from.  Each with the
          key, value, and ratio values as above.  The key for each dictionary is the match ratio.

    :cvar deviceUUID: (string) The deviceUUID if known, otherwise will be None.
    :cvar errorno: (int) An error number for further error sorting/handling.
    :cvar key: (string) If from a fuzzy search exception, will be the best possible deviceUUID.
    :cvar others: (dict) If from a fuzzy search exception, will be a dictionary of other alternatives.
    :cvar searchFor: (string) If from a fuzzy search exception, will be the requested search key.
    :cvar ratio: (float) If from a fuzzy search exception, the match confidence in percent as .80 for 80%.
    :cvar value: (device) If from a fuzzy search exception, will be the best possible device instance.
    """
    def __init__(self, message, **kwargs):
        """
        :param message: The error message to log/display.
        :type message: string
        :param kwargs: Various key/value pair arguments.

        """
        Exception.__init__(self)
        self.message = message
        if 'errorno' in kwargs:
            self.errorno = kwargs['errorno']
        else:
            self.errorno = None

        if 'deviceUUID' in kwargs:
            self.deviceUUID = kwargs['deviceUUID']
        else:
            self.deviceUUID = None

        if 'key' in kwargs:
            self.searchFor = kwargs['searchFor']
        else:
            self.key = None

        if 'key' in kwargs:
            self.key = kwargs['key']
        else:
            self.key = None

        if 'value' in kwargs:
            self.value = kwargs['value']
        else:
            self.value = None

        if 'ratio' in kwargs:
            self.ratio = kwargs['ratio']
        else:
            self.ratio = None
        
        if 'others' in kwargs:
            self.others = kwargs['others']
        else:
            self.others = None

    def __str__(self):
        """
        Formats the exception for logging to text.

        @return: A formated string of the error message.
        @rtype: C{string}
        """
        output = "Device API Error: '%s'" % (self.message)
        return repr(output)

    def dump(self):
        """
        Returns the exception components as a dictionary.

        @returns: The exception components as a diction.
        @rtype: C{dict}
        """
        return {'message'     : self.message,
                'name'        : self.name}


class AuthError(GWCritical):
    """
    Extends :class:`GWCritical` - Called when the gateway cannot auth to the
    server.  **This forces the gateway to quit.**
    """
    def __init__(self, message, errorno):
        """
        :param message: The error message to log/display.
        :type message: C{string}
        :param errorno: The error number to log/display.
        :type errorno: C{int}
        """
        GWCritical.__init__(self, message, errorno, "library", "gatewaycontrol")
        self.exit()
        
class NoSuchLoadedComponentError(Exception):
    """
    Extends *Exception* - Raised when a request for a loaded module or library
   (aka component), is not found.
    """
    pass

class FuzzySearchError(Exception):
    """
    Extends *Exception* - A non-fatal FuzzySearch error. Occurs when something happened
    with a fuzzy search.

    :cvar deviceUUID: (string) The deviceUUID if known, otherwise will be None.
    :cvar errorno: (int) An error number for further error sorting/handling.
    :cvar key: (string) If from a fuzzy search exception, will be the best possible deviceUUID.
    :cvar others: (dict) If from a fuzzy search exception, will be a dictionary of other alternatives.
    :cvar searchFor: (string) If from a fuzzy search exception, will be the requested search key.
    :cvar ratio: (float) If from a fuzzy search exception, the match confidence in percent as .80 for 80%.
    :cvar value: (device) If from a fuzzy search exception, will be the best possible device instance.
    """
    def __init__(self, searchFor, key, value, ratio, others):
        """
        :param searchfor: The requestd search key.
        :type searchfor: string
        :param key: The best matching key.
        :type key: string
        :param value: The best matchin value.
        :type value: int
        :param ratio: The ratio as a percent of closeness. IE: .32
        :type ratio: flaot
        :param others: Other top 5 choices to choose from.
        :type others: dict
        """
        Exception.__init__(self)
        self.searchFor = searchFor
        self.key = key
        self.value = value
        self.ratio = ratio
        self.others = others

    def __str__(self):
        """
        Formats the exception for logging to text.

        :return: A formated string of the error message.
        :rtype: string
        """
        output = "Key (%s) not found above the cutoff limit. Closest key found: %s with ratio of: %.3f." % (self.searchFor, self.key, self.ratio)
        return repr(output)

class PinNumberError(Exception):
    """
    Raised when the pin number is invalid.
    """
    pass
        
class CommandError(Exception):
    """
    If commands class has an error.
    """
    pass

class CronTabError(Exception):
    """
    If crontab class has an error.
    """
    pass

class TimeError(Exception):
    """
    If :py:mod:`yombo.lib.times` class has an error.
    """
    pass

class InputValidationError(Exception):
    """
    If a value input doesn't match the allowed input type id.
    """
    pass
