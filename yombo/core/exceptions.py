# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Create various exceptions to be used throughout the Yombo gateway.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/exceptions.html>`_
"""
from twisted.internet.error import ReactorNotRunning

from yombo.constants import RESTART_EXIT_CODE, QUIT_ERROR_EXIT_CODE


class YomboException(Exception):
    """
    Extends *Exception* - A non-fatal generic gateway exception that is used for minor errors.
    """
    def __init__(self, message, errorno=1, name="unknown", component="component", html_message=None):
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
        Exception.__init__(self, message)
        self.message = message
        if html_message is None:
            self.html_message = message
        else:
            self.html_message = html_message
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
    def __init__(self, message, errorno=101, name="unknown", component="component", html_message=None, details=None):
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
        YomboException.__init__(self, message, errorno, name, component, html_message)
        self.details = details


class IntentError(YomboWarning):
    """
    Base class for intent related errors.
    """


class UnknownIntent(IntentError):
    """
    When the intent is not registered.
    """
    def __init__(self, message, errorno=1359, name="unknown", component="unknown"):
        YomboException.__init__(self, message, errorno, name, component)


class InvalidSlotInfo(IntentError):
    """
    When the slot data is invalid or missing components.
    """


class IntentHandleError(IntentError):
    """
    Error while handling intent.
    """


class IntentUnexpectedError(IntentError):
    """
    Unexpected error while handling intent.
    """


class YomboInvalidValidation(YomboException):
    """
    Occurs when asked to validate something and it fails. Primary use cases are: 1) validating user inputs to
    the web interface, or 2) validating variable types within the framework or modules.
    """

    def __init__(self, message, errorno=119, name="unknown", component="validate"):
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
        YomboException.__init__(self, message, errorno, name, component)


class YomboInvalidArgument(ValueError):
    """
    Raised when an argument to a function is invalid.
    """
    pass


class YomboAPICredentials(YomboException):
    """
    Extends *YomboException* - A non-fatal warning gateway exception that is used when the YomboAPI library
    ran into an authentication issue and cannot process the request.
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
        YomboException.__init__(self, message, errorno, name, component)


class YomboAutomationWarning(YomboWarning):
    """
    Extends *Exception* - A non-fatal warning when an automation rule into a problem. Typically, the user needs
    to adjust their automation rule.
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
        YomboWarning.__init__(self, message, errorno, name, component)


class YomboCritical(RuntimeWarning):
    """
    Extends *RuntimeWarning* - A **fatal error** gateway exception - **forces the gateway to quit**.
    """
    def __init__(self, message, errorno=101, name="unknown", component="component", exit_code=None):
        """
        Setup the YomboCritical. When caught, call the exit function of this exception to
        exit the gateway.

        :param message: The error message to log/display.
        :type message: string
        :param errorno: The error number to log/display.
        :type errorno: int
        :param name: Name of the library, component, or module rasing the exception.
        :type name: string
        :param component: What type of ojbect is calling: component, library, or module
        :type component: string
        """
        if exit_code is None:
            exit_code = QUIT_ERROR_EXIT_CODE
        self.exit_code = exit_code
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
        print("Yombo critical stopping......")
        reactor.addSystemEventTrigger('after', 'shutdown', os._exit, self.exit_code)
        try:
            reactor.stop()
        except ReactorNotRunning as e:
            print("Unable to stop reactor....%s" % e)
            pass


class YomboRestart(RuntimeWarning):
    """
    Extends *RunningWarning* - Restarts the gateway, not a fatal exception.  
    """
    message = ""

    def __init__(self, message):
        """
        :param message: The error message to log/display.
        :type message: string
        """
        self.message = message
        self.exit()

    def __str__(self):
        """
        Formats the exception for logging to text.

        @return: A formated string of the error message.
        @rtype: string
        """
        output = "Restarting Yombo Gateway. Reason: %s." % self.message
        return repr(output)

    def exit(self):
        """
        Exists the daemon with exit status 127 so that the wrapper script knows to restart the gateway.
        """
        from twisted.internet import reactor
        import os
        reactor.addSystemEventTrigger('after', 'shutdown', os._exit, RESTART_EXIT_CODE)
        reactor.stop()


class YomboNoAccess(YomboWarning):
    """
    Extends :class:`YomboWarning` - Resource accessed without required permissions.
    """

    def __init__(self, item_permissions=None, roles=None, platform=None, item=None, action=None,
                 message="No access", name="unknown", component="component", html_message=None):
        """
        Setup the YomboWarning and then pass everying to YomboException

        :param message: The error message to log/display.
        :type message: string
        :param name: Name of the library, component, or module rasing the exception.
        :type name: string
        :param component: What type of ojbect is calling: component, library, or module
        :type component: string
        """
        YomboException.__init__(self, message=message, errorno=403, name=name, component=component,
                                html_message=html_message)
        # print("Request refused: %s - %s - %s" % (platform, item, action))
        self.item_permissions = item_permissions
        self.roles = roles
        self.platform = platform
        self.action = action


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
        YomboWarning.__init__(self, message, errorno, module_obj._Name, "module")


class YomboFileError(YomboWarning):
    """
    Extends :class:`YomboWarning` - A missing configuration or improperly configured option.
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


class YomboCronTabError(Exception):
    """
    Exceptions related to crontab errors.
    """
    pass


class YomboHookStopProcessing(YomboWarning):
    """
    Raise this during a hook call to stop processing any remain hook calls and to stop further processing
    of the remaining request.
    """
    def __init__(self, message, errorno=101, name="unknown", component="component", collected=None, by_who=None):
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
