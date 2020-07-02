# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Create various exceptions to be used throughout the Yombo gateway.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/exceptions.html>`_
"""
from copy import deepcopy
import inspect
import sys
from typing import Dict, List, Optional, Type, Union
from twisted.internet.error import ReactorNotRunning
from uuid import uuid4

from yombo.constants import RESTART_EXIT_CODE, QUIT_EXIT_CODE, QUIT_ERROR_EXIT_CODE
from yombo.constants.exceptions import ERROR_CODES


class YomboException(Exception):
    """
    Extends *Exception* - A non-fatal generic gateway exception that is used for minor errors.

    Accepts a list of errors and will generate both text mesasge and html output. The raw
    error will also be made available.

    The meta variable is a dict to provide any additional details about the error.
    """
    # errors: List[Dict[str, Union[str, int]]]
    message: str = ""
    html: str = ""
    errors: Union[str, List[Dict[str, Union[str, int, dict]]]]
    error_code: Union[str, int]
    response_code: int
    links: dict
    component_name: str
    component_type: str
    component_function: str

    def __init__(self,
                 errors: Union[str, dict, List[Dict[str, Union[str, int, dict]]]],
                 error_code: Optional[Union[str, int]] = 101,
                 component_name: Optional[str] = None,
                 component_type: Optional[str] = None,
                 component_function: Optional[str] = None,
                 meta: Optional[dict] = None,
                 title: Optional[str] = None,
                 response_code: Optional[int] = None):
        """
        :param errors: List of errors with additional details. Can be used by others to format more detailed responses.
        :param error_code: The error number to log/display.
        :param component_name: Name of the library, component, or module raising the exception.
        :param component_type: Library, core, module, etc.
        :param component_function: Name of the function that raised the error.
        :param meta: Any additional items for reference.
        :type meta: dict
        :param title: Use a default title for errors.
        :param response_code: Response code to send to the web browser.
        """
        calling_frame = sys._getframe(2)
        mod = inspect.getmodule(calling_frame)
        if "self" in calling_frame.f_locals:
            component_details = {
                "file": mod.__name__,
                "class": calling_frame.f_locals['self'].__class__.__name__,
                "method": calling_frame.f_code.co_name
            }
        else:
            component_details = {
                "file": mod.__name__,
                "class": None,
                "method": calling_frame.f_code.co_name,
            }

        if component_type is None:
            item_path = component_details["file"]
            if item_path.startswith("yombo.lib"):
                component_type = "library"
            if item_path.startswith("yombo."):
                item_parts = item_path.split(".")
                component_type = item_parts[1]
        if component_name is None:
            component_name = component_details["file"]

        if isinstance(errors, str):
            errors: List[Dict[str, Union[str, int, dict]]] = [{'detail': errors}]
        if isinstance(errors, dict):
            errors: List[Dict[str, Union[str, int, dict]]] = [errors]

        if response_code is None or isinstance(response_code, int) is False or response_code not in ERROR_CODES:
            response_code = 400
        if title is None:
            title = ERROR_CODES[response_code]["title"]

        self.response_code = response_code
        for error in errors:
            missing = ERROR_CODES[response_code]

            if "code" not in error:
                error["code"] = error_code
            if "title" not in error:
                error["title"] = title
            if "detail" not in error:
                error["detail"] = "No details about exception was provided."
            if "links" not in error:
                error["links"] = missing["links"]
            else:
                temp_links = deepcopy(missing["links"])
                if error["links"] is None:
                    error["links"] = temp_links
                else:
                    temp_links.update(error["links"])
                    error["links"] = temp_links

            if isinstance(meta, dict):
                error["meta"] = meta

        message: str = ""
        messages = []
        html: str = ""
        for error in errors:
            if len(message) > 0:
                message += ",+ "
            messages.append(f"{error['detail']}")
            html += f"<li>{error['title']}<ul><li>{error['detail']}</li><li>{error['code']}</li></ul></li>"
        message = ", ".join(messages)
        if len(message) == 0:
            message = "Unknown error"

        self.errors = errors
        self.message = message
        self.html = html

        Exception.__init__(self, self.message)

        self.error_code = error_code
        self.component_name = component_name
        self.component_type = component_type
        self.component_function = component_function
        self.meta = meta
        self.title = title

    def __str__(self) -> str:
        """
        Formats the exception for logging to text.

        :return: A formatted string of the error message.
        :rtype: string
        """
        results = f"{self.error_code}: {self.message}"
        if self.component_name is not None:
            results += f" in {self.component_name}"
        results2 = ""
        if self.component_type is not None:
            results2 = str(self.component_type)
        if self.component_function is not None:
            results2 += f" {str(self.component_type)}"
        if len(results2) > 0:
            results += f" ({results2.strip()})"
        return results


class YomboWarning(YomboException):
    """
    Extends *Exception* - A non-fatal warning gateway exception that is used for items needing user attention.
    """
    def __init__(self,
                 errors: Union[str, dict, List[Dict[str, Union[str, int]]]],
                 error_code: Optional[Union[str, int]] = 102,
                 component_name: Optional[str] = None,
                 component_type: Optional[str] = None,
                 component_function: Optional[str] = None,
                 meta: Optional[dict] = None,
                 title: Optional[str] = None,
                 response_code: Optional[int] = None):
        """
        Setup the YomboWarning and then pass everying to YomboException
        
        :param errors: List of errors with additional details. Can be used by others to format more detailed responses.
        :param error_code: The error number to log/display.
        :param component_name: Name of the library, component, or module raising the exception.
        :param component_type: Library, core, module, etc.
        :param component_function: Name of the function that raised the error.
        :param meta: Any additional items for reference.
        :param title: Use a default title for errors.
        :param response_code: Response code to send to the web browser.
        """
        YomboException.__init__(self, errors, error_code, component_name, component_type, component_function, meta,
                                title, response_code)


class IntentError(YomboWarning):
    """
    Base class for intent related errors.
    """


class IntentHandleError(IntentError):
    """
    Error while handling intent.
    """


class IntentUnexpectedError(IntentError):
    """
    Unexpected error while handling intent.
    """


class UnknownIntent(IntentError):
    """
    When the intent is not registered.
    """
    def __init__(self,
                 errors: Union[str, List[Dict[str, Union[str, int]]]],
                 error_code: Optional[Union[str, int]] = 1359,
                 component_name: Optional[str] = None,
                 component_type: Optional[str] = None,
                 component_function: Optional[str] = None,
                 meta: Optional[dict] = None):
        YomboException.__init__(self, errors, error_code, component_name, component_type, component_function, meta)


class InvalidSlotInfo(IntentError):
    """
    When the slot data is invalid or missing components.
    """


class YomboMarshmallowValidationError(YomboException):
    """
    Takes a Marshmallow ValidationError and converts to Yombo format.
    """
    def __init__(self, validation_error,
                 error_code: Optional[Union[str, int]] = 101,
                 component_name: Optional[str] = None,
                 component_type: Optional[str] = None,
                 component_function: Optional[str] = None,
                 meta: Optional[dict] = None,
                 title: Optional[str] = None,
                 response_code: Optional[int] = None):

        print(f"YomboMarshmallowValidationError: validation_error: {validation_error}")
        messages = validation_error.messages
        print(f"YomboMarshmallowValidationError: message: {messages}")
        errors = []
        for field, message in messages.items():
            errors.append({
                "title": field,
                "detail": " ".join(message),  # Comes in as a list of messages. Lets just make one string.
            })
        YomboException.__init__(self, errors, error_code, component_name, component_type, component_function, meta,
                                title, response_code)


class YomboInvalidValidation(YomboException):
    """
    Occurs when asked to validate something and it fails. Primary use cases are: 1) validating user inputs to
    the web interface, or 2) validating variable types within the framework or modules.
    """
    def __init__(self,
                 errors: Union[str, List[Dict[str, Union[str, int]]]],
                 error_code: Optional[Union[str, int]] = 1873,
                 component_name: Optional[str] = None,
                 component_type: Optional[str] = None,
                 component_function: Optional[str] = None,
                 meta: Optional[dict] = None):
        """
        Setup the YomboWarning and then pass everying to YomboException

        :param errors: List of errors with additional details. Can be used by others to format more detailed responses.
        :param error_code: The error number to log/display.
        :param component_name: Name of the library, component, or module raising the exception.
        :param component_type: Library, core, module, etc.
        :param component_function: Name of the function that raised the error.
        :param meta: Any additional items for reference.
        """
        YomboException.__init__(self, errors, error_code, component_name, component_type, component_function, meta)


class YomboWebinterfaceError(YomboException):
    """
    Raised when somewhere within the webinterface. Collects various items to be displayed via template or to
    output in JSON/MSGPACK.
    """
    def __init__(self,
                 errors: Optional[Union[str, List[Dict[str, Union[str, int]]]]] = None,
                 error_code: Optional[Union[str, int]] = "error_3102",
                 title: Optional[str] = None,
                 links: Optional[dict] = None,
                 response_code: Optional[int] = None,
                 component_name: Optional[str] = None,
                 component_type: Optional[str] = None,
                 component_function: Optional[str] = None,
                 meta: Optional[dict] = None):
        """

        Setup the YomboWarning and then pass everying to YomboException

        :param errors: List of errors with additional details. Can be used by others to format more detailed responses.
        :param error_code: The error number to log/display.
        :param component_name: Name of the library, component, or module raising the exception.
        :param component_type: Library, core, module, etc.
        :param component_function: Name of the function that raised the error.
        :param meta: Any additional items for reference.
        """
        if response_code is None or isinstance(response_code, int) is False or response_code not in ERROR_CODES:
            response_code = 400

        self.response_code = response_code

        missing = ERROR_CODES[response_code]
        # print(f"return_error: {errors}")
        if title is None:
            self.title = missing["title"]
        if errors is None:
            errors = missing["details"]

        if error_code is None:
            error_code = missing["error_code"]

        temp_links = deepcopy(missing["links"])
        if links is None:
            self.links = temp_links
        else:
            temp_links.update(links)
            self.links = temp_links

        YomboException.__init__(self, errors, error_code, component_name, component_type, component_function, meta)


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
    def __init__(self,
                 errors: Union[str, List[Dict[str, Union[str, int]]]],
                 error_code: Optional[Union[str, int]] = 9854,
                 component_name: Optional[str] = None,
                 component_type: Optional[str] = None,
                 component_function: Optional[str] = None,
                 meta: Optional[dict] = None):
        """
        Setup the YomboWarning and then pass everything to YomboException

        :param errors: List of errors with additional details. Can be used by others to format more detailed responses.
        :param error_code: The error number to log/display.
        :param component_name: Name of the library, component, or module raising the exception.
        :param component_type: Library, core, module, etc.
        :param component_function: Name of the function that raised the error.
        :param meta: Any additional items for reference.
        """
        YomboException.__init__(self, errors, error_code, component_name, component_type, component_function, meta)


# class YomboCritical(RuntimeWarning):
#     """
#     Extends *RuntimeWarning* - A **fatal error** gateway exception - **forces the gateway to quit**.
#     """
#     def __init__(self,
#                  message: str,
#                  error_code: Optional[int] = 9999,
#                  exit_code: Optional[int] = None,
#                  component_name: Optional[str] = None,
#                  component_type: Optional[str] = None,
#                  component_function: Optional[str] = None
#                  ):
#         """
#         Setup the YomboCritical. When caught, call the exit function of this exception to
#         exit the gateway.
#
#         :param message: The error message to log/display.
#         :param error_code: The error number to log/display.
#         :param component_name: Name of the library, component, or module raising the exception.
#         :param component_type: Library, core, module, etc.
#         :param component_function: Name of the function that raised the error.
#         """
#         if exit_code is None:
#             exit_code = QUIT_ERROR_EXIT_CODE
#         self.exit_code = exit_code
#         self.message = message
#         self.error_code = error_code
#         self.component_name = component_name
#         self.component_type = component_type
#         self.component_function = component_function
#         self.exit()
#
#     def __str__(self) -> str:
#         """
#         Formats the exception for logging to text.
#
#         :return: A formatted string of the error message.
#         :rtype: string
#         """
#         return f"{self.error_code}: {self.message} in {self.component_name} ({self.component_type} - " \
#                f"{self.component_function})"
#
#     def exit(self):
#         """
#         Kills the gateway, won't be restarted.
#         """
#         from twisted.internet import reactor
#         import os
#         print("Yombo critical stopping......")
#         reactor.addSystemEventTrigger("after", "shutdown", os._exit, self.exit_code)
#         try:
#             reactor.stop()
#         except ReactorNotRunning as e:
#             print(f"Unable to stop reactor....{e}")
#             pass


class YomboCritical(RuntimeWarning):
    """
    Extends *RuntimeWarning* - A **fatal error** gateway exception - **forces the gateway to quit**.

    Used to exit the gateway with a return status code representing something went wrong.
    """
    message = ""

    def __init__(self, message: str):
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
        return f"Restarting Yombo Gateway. Reason: {self.message}."

    def exit(self):
        """
        Exists the daemon with exit status 127 so that the wrapper script knows to restart the gateway.
        """
        from twisted.internet import reactor
        import os
        reactor.addSystemEventTrigger("after", "shutdown", os._exit, QUIT_ERROR_EXIT_CODE)
        reactor.stop()


class YomboQuit(RuntimeWarning):
    """
    Extends *RuntimeWarning* - A **fatal error** gateway exception - **forces the gateway to quit**.

    Used to exit the gateway with a return status code representing everything is good.
    """
    message = ""

    def __init__(self, message: str):
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
        return f"Restarting Yombo Gateway. Reason: {self.message}."

    def exit(self):
        """
        Exists the daemon with exit status 127 so that the wrapper script knows to restart the gateway.
        """
        from twisted.internet import reactor
        import os
        reactor.addSystemEventTrigger("after", "shutdown", os._exit, QUIT_EXIT_CODE)
        reactor.stop()


class YomboRestart(RuntimeWarning):
    """
    Extends *RunningWarning* - Restarts the gateway, not a fatal exception.  
    """
    message = ""

    def __init__(self, message: str):
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
        return f"Restarting Yombo Gateway. Reason: {self.message}."

    def exit(self):
        """
        Exists the daemon with exit status 127 so that the wrapper script knows to restart the gateway.
        """
        from twisted.internet import reactor
        import os
        reactor.addSystemEventTrigger("after", "shutdown", os._exit, RESTART_EXIT_CODE)
        reactor.stop()


class YomboNoAccess(YomboWarning):
    """
    Extends :class:`YomboWarning` - Resource accessed without required permissions.
    """
    def __init__(self,
                 action: str,
                 platform: str,
                 item_id: Union[str, int],
                 authentication: Type["yombo.mixins.auth_mixin.AuthMixin"],
                 request_context: str,
                 error_code: Optional[Union[str, int]] = None,
                 message: Optional[str] = None,
                 component_name: Optional[str] = None,
                 component_type: Optional[str] = None,
                 component_function: Optional[str] = None,
                 meta: Optional[dict]=None):
        """
        Setup the YomboWarning and then pass everying to YomboException

        :param action: The action requested, such as edit, view, create, etc.
        :param platform: The platform, such as yombo.lib.atoms
        :param item_id: The id requested, such as a command_id, device_id.
        :param request_by: The id of the requester.
        :param request_by_type: The type of requester, such as authkey, user.
        :param request_context: Context about the request. Such as an IP address of the source.
        :param error_code: An error code for the no access, typically the request_id.
        :param message: Message to return to the requester.
        :param component_name: Name of the library, component, or module raising the exception.
        :param component_type: Library, core, module, etc.
        :param component_function: Name of the function that raised the error.
        """
        if error_code is None:
            error_code = uuid4()
        if message is None:
            message = "No access"

        errors = [
            {
                "code": 403,
                "id": error_code,
                "title": "Access denied",
                "details": message,
            }
        ]
        YomboException.__init__(self,
                                errors=errors,
                                error_code=403,
                                component_name=component_name,
                                component_type=component_type,
                                component_function=component_function,
                                meta=meta)
        self.action = action
        self.platform = platform
        self.item_id = item_id
        self.request_by = authentication.accessor_id
        self.request_by_type = authentication.accessor_type
        self.request_context = request_context


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
    :cvar error_code: (int) An error number for further error sorting/handling.
    :cvar key: (string) If from a fuzzy search exception, will be the best possible device_id.
    :cvar others: (dict) If from a fuzzy search exception, will be a dictionary of other alternatives.
    :cvar search_for: (string) If from a fuzzy search exception, will be the requested search key.
    :cvar ratio: (float) If from a fuzzy search exception, the match confidence in percent as .80 for 80%.
    :cvar value: (device) If from a fuzzy search exception, will be the best possible device instance.
    """
    def __init__(self, search_for, key, value, ratio, others):
        """
        :param search_for: The requestd search key.
        :param key: The best matching key.
        :param value: The best matchin value.
        :param ratio: The ratio as a percent of closeness. IE: .32
        :param others: Other top 5 choices to choose from.
        """
        Exception.__init__(self)
        self.search_for = search_for
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
        return "Key (%s) not found above the cutoff limit. Closest key found: %s with ratio of: %.3f." %\
                 (self.search_for, self.key, self.ratio)


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
    def __init__(self,
                 message: str,
                 error_code: Union[str, int] = 19348,
                 component_name: Optional[str] = None,
                 component_type: Optional[str] = None,
                 component_function: Optional[str] = None
                 ):
        """
        Setup the YomboWarning and then pass everying to YomboException

        :param message: The error message to log/display.
        :param error_code: The error number to log/display.
        :param component_name: Name of the library, component, or module raising the exception.
        :param component_type: Library, core, module, etc.
        :param component_function: Name of the function that raised the error.
        """
        errors = [
            {
                "title": "Yombo Hook Stop Processing",
                "detail": message
            }
        ]
        YomboWarning.__init__(self, errors, error_code=error_code, component_name=component_name,
                              component_type=component_type, component_function=component_function)
