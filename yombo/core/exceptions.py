# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Create various exceptions to be used throughout the Yombo
gateway.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""


class YomboException(Exception):
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


class YomboWarning(YomboException):
    """
    Extends *Exception* - A non-fatal warning gateway exception that is used for items needing user attention.
    """
    def __init__(self, message, errorno=101, name="unknown", component="component"):
        """
        Setup the YomboWarning and then pass everying to YomboException
        
        :param message: The error message to log/display.
        :type message: string
        :param errorno: The error number to log/display.
        :type errorno: int
        :param name: Name of the library, component, or module rasing the exception.
        :type name: string
        :param component: What type of ojbect is calling: component, library, or module
        :type component: string
        """
        YomboException.__init__(self, message, errorno, component, name)


class YomboAutomationWarning(YomboWarning):
    """
    Extends *Exception* - A non-fatal warning gateway exception that is used for items needing user attention.
    """
    def __init__(self, message, errorno=101, name="unknown", component="component"):
        """
        Setup the YomboWarning and then pass everying to YomboException

        :param message: The error message to log/display.
        :type message: string
        :param errorno: The error number to log/display.
        :type errorno: int
        :param name: Name of the library, component, or module rasing the exception.
        :type name: string
        :param component: What type of ojbect is calling: component, library, or module
        :type component: string
        """
        YomboWarning.__init__(self, message, errorno, component, name)


class YomboStateNotFound(YomboWarning):
    """
    Extends *YomboWarning* - When a state is not found.
    """
    def __init__(self, message, errorno=101, name="States", component="library"):
        """
        Setup the YomboWarning and then pass everying to YomboException

        :param message: The error message to log/display.
        :type message: string
        :param errorno: The error number to log/display.
        :type errorno: int
        :param name: Name of the library, component, or module rasing the exception.
        :type name: string
        :param component: What type of ojbect is calling: component, library, or module
        :type component: string
        """
        YomboWarning.__init__(self, message, errorno, component, name)


class YomboStateNoAccess(YomboWarning):
    """
    Extends *YomboWarning* - When access to the state is restricted. Must supply password.
    """
    def __init__(self, message, errorno=101, name="States", component="library"):
        """
        Setup the YomboWarning and then pass everying to YomboException

        :param message: The error message to log/display.
        :type message: string
        :param errorno: The error number to log/display.
        :type errorno: int
        :param name: Name of the library, component, or module rasing the exception.
        :type name: string
        :param component: What type of ojbect is calling: component, library, or module
        :type component: string
        """
        YomboWarning.__init__(self, message, errorno, component, name)


class YomboCritical(RuntimeWarning):
    """
    Extends *RuntimeWarning* - A **fatal error** gateway exception - **forces the gateway to quit**.
    """
    def __init__(self, message, errorno=101, name="unknown", component="component"):
        """
        Setup the YomboCritical. When caught, call the exit function of this exception to
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


class YomboRestart(RuntimeWarning):
    """
    Extends *RunningWarning* - Restarts the gateway, not a fatal exception.  
    """
    def __init__(self, message):
        """
        :param message: The error message to log/display.
        :type message: string
        """
        self.name = message
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


class YomboImproperlyConfigured(YomboWarning):
    """
    Extends :class:`YomboWarning` - A missing configuration or improperly configured option.
    """
    pass


class YomboSuspiciousOperation(YomboWarning):
    """
    Extends :class:`YomboWarning` - Service detected something suspicious and stopped that activity.
    """
    pass


class YomboAPIWarning(YomboWarning):
    """
    Extends :class:`YomboWarning` - Service detected something suspicious and stopped that activity.
    """
    pass


class YomboModuleWarning(YomboWarning):
    """
    Extends :class:`YomboWarning` - Same as calling YomboWarning, but sets component type to "module".
    """
    def __init__(self, message, errorno, module_obj):
        """
        :param message: The error message to log/display.
        :type message: string
        :param errorno: The error number to log/display.
        :type errorno: int
        :param module_obj: The module instance.
        :type module_obj: Module
        """
        YomboWarning.__init__(self, message, errorno, "module", module_obj._Name)


class YomboModuleCritical(YomboCritical):
    """
    Extends :class:`YomboCritical` - Same as calling YomboCritical, but sets the component type to
    "module" - **this forces the gateway to quit**.
    """
    def __init__(self, message, errorno, module_obj):
        """
        :param message: The error message to log/display.
        :type message: string
        :param errorno: The error number to log/display.
        :type errorno: int
        :param module_obj: Name of the library, component, or module rasing the exception.
        :type module_obj: string
        """
        YomboCritical.__init__(self, message, errorno, "module", module_obj._Name)


class YomboLibraryWarning(YomboWarning):
    """
    Extends :class:`YomboWarning` - Same as calling YomboWarning, but sets component type to "library".
    """
    def __init__(self, message, errorno, module_obj):
        YomboWarning.__init__(self, message, errorno, "library", module_obj._Name)


class YomboLibraryCritical(YomboCritical):
    """
    Extends :class:`YomboCritical` - Same as calling YomboCritical, but sets the component type to
    "library" - **this forces the gateway to quit**.
    """
    def __init__(self, message, errorno, module_obj):
        YomboCritical.__init__(self, message, errorno, "library", module_obj._Name)


class YomboMessageError(Exception):
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


class YomboFileError(YomboWarning):
    """
    Extends :class:`YomboWarning` - A missing configuration or improperly configured option.
    """
    pass


class YomboDeviceError(Exception):
    """
    Extends *Exception* - A non-fatal device exception used to catch device errors.

    Depending on where the error was caused, this expection will have varying
    amounts of information.
        
    kwargs accepts and processes the following:
        
        - device_id - The device_id the error is about.
        - errorno - An error number for further sorting/processing.
        
    Additionally, if this is the result of a search exception, it may also
    contain some of the error components of the :class:`YomboFuzzySearchError`,
    such as:
        
        - key: The best matching key, in this case would be the device_id (string).
        - value: The best matchin value, in this case would be the device instance (object).
        - ratio: The ratio as a percent of closeness. IE: .32
        - others: Other top 5 choices in a dictionary to choose from.  Each with the
          key, value, and ratio values as above.  The key for each dictionary is the match ratio.

    :cvar device_id: (string) The device_id if known, otherwise will be None.
    :cvar errorno: (int) An error number for further error sorting/handling.
    :cvar key: (string) If from a fuzzy search exception, will be the best possible device_id.
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

        if 'device_id' in kwargs:
            self.device_id = kwargs['device_id']
        else:
            self.device_id = None

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
        output = "Device API Error: '%s'" % self.message
        return repr(output)

    def dump(self):
        """
        Returns the exception components as a dictionary.

        @returns: The exception components as a diction.
        @rtype: C{dict}
        """
        return {'message': self.message,
                'name': self.name}

        
class YomboNoSuchLoadedComponentError(Exception):
    """
    Extends *Exception* - Raised when a request for a loaded module or library
    (aka component), is not found.
    """
    pass


class YomboFuzzySearchError(Exception):
    """
    Extends *Exception* - A non-fatal FuzzySearch error. Occurs when something happened
    with a fuzzy search.

    :cvar device_id: (string) The device_id if known, otherwise will be None.
    :cvar errorno: (int) An error number for further error sorting/handling.
    :cvar key: (string) If from a fuzzy search exception, will be the best possible device_id.
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


class YomboPinCodeError(Exception):
    """
    Raised when the pin number is invalid.
    """
    pass


class YomboCommandError(Exception):
    """
    If commands class has an error.
    """
    pass


class YomboCronTabError(Exception):
    """
    If crontab class has an error.
    """
    pass


class YomboTimeError(Exception):
    """
    If :py:mod:`yombo.lib.times` class has an error.
    """
    pass


class YomboInputValidationError(Exception):
    """
    If a value input doesn't match the allowed input type id.
    """
    pass


class YomboHookStopProcessing(YomboWarning):
    """
    Raise this during a hook call to stop processing any remain hook calls and to stop further processing
    of the remaining request.
    """
    def __init__(self, message, errorno=101, name="unknown", component="component"):
        """
        Setup the YomboWarning and then pass everying to YomboException

        :param message: The error message to log/display.
        :type message: string
        :param errorno: The error number to log/display.
        :type errorno: int
        :param name: Name of the library, component, or module rasing the exception.
        :type name: string
        :param component: What type of ojbect is calling: component, library, or module
        :type component: string
        """
        YomboWarning.__init__(self, message, errorno, component, name)

