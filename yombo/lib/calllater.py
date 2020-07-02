# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Call Later @ Library Documentation <https://yombo.net/docs/libraries/calllater>`_

Tracks reactor callLater items. Primarily used for debugging and quickly creating callLater items without
having to import twisted reactor.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2017-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/calllater.html>`_
"""
from random import randint
from time import time
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.library_child import YomboLibraryChild
from yombo.core.log import get_logger
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.mixins.child_storage_accessors_mixin import ChildStorageAccessorsMixin
from yombo.mixins.parent_storage_accessors_mixin import ParentStorageAccessorsMixin
from yombo.utils import random_string
from yombo.utils.datetime import get_next_time

logger = get_logger("library.callater")


class CallLaterItem(YomboLibraryChild, ChildStorageAccessorsMixin):
    """ Holds the reactor (task) and other data. """
    _Entity_type: ClassVar[str] = "Call later item"
    _Entity_label_attribute: ClassVar[str] = "task_id"

    @property
    def _primary_field_id(self):
        """ Get the ID for the object. """
        return self.__dict__[self._Parent._storage_primary_field_name]

    def __init__(self, parent, task_id: str, delay: Union[int, float], func: Callable,
                 args: dict, kwargs: dict, description: str,
                 load_source: str, request_context: str,
                 authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None) -> None:
        super().__init__(parent)
        self.task_id = task_id
        self.func = func
        self.description = description
        self.load_source = load_source
        self.request_context = request_context
        self.args = args
        self.kwargs = kwargs

        self.task = reactor.callLater(delay, self.func, *self.args, **self.kwargs)
        self.created_at = round(time(), 4)
        self.call_time = self.task.getTime()

    def cancel(self, request_context: Optional[str] = None,
               authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None) -> None:
        """
        Cancel the call later, then delete this id.

        :param request_context: Context about the request. Such as an IP address of the source.
        :param authentication: An auth item such as a websession or authkey.
        """
        self.check_authorization(authentication, "cancel")
        if self.task is not None and self.task.active():
            self.task.cancel()
        del self._Parent.calllater[self.task_id]

    def reset(self, seconds_from_now: Union[int, float], request_context: Optional[str] = None,
              authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None) -> None:
        """
        Reschedule the calllater with a new delay time. It will reset the call time in seconds from
        the current time.

        :param seconds_from_now: Number of seconds (or fraction of) from now to reschedule.
        :param request_context: Context about the request. Such as an IP address of the source.
        :param authentication: An auth item such as a websession or authkey.
        """
        self.check_authorization(authentication, "modify")
        if self.task is not None and self.task.active():
            self.task.reset(seconds_from_now)
        else:
            raise YomboWarning("Unable to reschedule call_later item, it's not active or already called.")


class CallLater(YomboLibrary, ParentStorageAccessorsMixin, LibrarySearchMixin):
    """
    Tracks callLater calls.
    """
    calllater: ClassVar[Dict[str, Any]] = {}
    _storage_attribute_name: ClassVar[str] = "calllater"
    _storage_attribute_sort_key: ClassVar[str] = "task_id"
    _storage_primary_field_name: ClassVar[str] = "task_id"
    _storage_fields: ClassVar[list] = ["task_id", "description", "call_time", "created_at"]
    _storage_class_reference: ClassVar = CallLaterItem

    def _init_(self, **kwargs) -> None:
        """
        Setup CallLater library by first getting existing delayedCalls. Then, setup the cleanup expired loop.
        """
        self.all_calls = reactor._delayedCalls  # used by the web interface to list all unregistered call later's.

        self.cleanup_expired_loop = LoopingCall(self.cleanup_expired)
        self.cleanup_expired_loop.start(randint(120, 180), False)

    def cleanup_expired(self) -> None:
        """
        Removed called/expired call later
        :return:
        """
        for task_id in list(self.calllater.keys()):
            task = self.calllater[task_id].task
            if task.active() is False:
                del self.calllater[task_id]

    def new(self, delay: Union[int, float], func: Callable, *args, _task_description=None,
            _load_source: Optional[str] = None, _request_context: Optional[str] = None,
            _authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None, **kwargs):
        """
        A wrapper around twisted's callLater. This keeps track of call later events for debugging.

        :param delay: How to delay the call later, in seconds or float.
        :param func: The callable to call.
        :param args: Args to send to the function.
        :param _task_description: A description for the calllater.
        :param _load_source: Where the data originated from. One of: local, database, yombo, system
        :param _request_context: Context about the request. Such as an IP address of the source.
        :param _authentication: An auth item such as a websession or authkey.
        :param kwargs: kwargs are sent to the function.
        :return:
        """
        self.check_authorization(_authentication, "create")
        call_later_id = random_string(length=12)
        self.calllater[call_later_id] = CallLaterItem(self, call_later_id, delay, func, args, kwargs,
                                                      _task_description, _load_source, _request_context,
                                                      _authentication
                                                      )
        return self.calllater[call_later_id].task

    def run_at(self, timestring: str, func: Callable, *args, _task_description=None,
               _load_source: Optional[str] = None, _request_context: Optional[str] = None,
               _authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None, **kwargs):
        """
        Like new(), but accepts a string with a time to call. If the time has already passed, it will run at
        the next day.

        Acceptable format for "timestring" value.

          * "HH:MM" (24 hour). EG: 21:10 (9:10pm)
          * "h:mAM" EG: 1:14pm, 6:30am
          * "h:m AM" EG: 1:14 pm, 6:30 am
          * "tomorrow 10pm"
          * "in 1 hour"

        :param timestring: String to parse to get hour:minute from
        :param func: The callable to call.
        :param args: Args to send to the function.
        :param _task_description: A description for the calllater.
        :param _load_source: Where the data originated from. One of: local, database, yombo, system
        :param _request_context: Context about the request. Such as an IP address of the source.
        :param _authentication: An auth item such as a websession or authkey.
        :param kwargs: kwargs are sent to the function.
        :return:
        """
        self.check_authorization(_authentication, "create")
        next_time = get_next_time(timestring)
        delay = next_time[0] - time()

        call_later_id = random_string(length=12)
        self.calllater[call_later_id] = CallLaterItem(self, call_later_id, delay, func, args, kwargs,
                                                      _task_description, _load_source, _request_context,
                                                      _authentication
                                                      )
        return self.calllater[call_later_id].task

    def cancel(self, task_id: str, request_context: Optional[str] = None,
               authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None) -> None:
        """
        Stop/cancel a call later task.

        :param task_id: The id to cancel.
        :param request_context: Context about the request. Such as an IP address of the source.
        :param authentication: An auth item such as a websession or authkey.
        :return:
        """
        if task_id not in self.calllater:
            raise KeyError(f"'task_id' not found: {task_id}")

        self.calllater[task_id].cancel(request_context=request_context, authentication=authentication)

    def reset(self, task_id: str, seconds_from_now: Union[int, float], request_context: Optional[str] = None,
              authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None) -> None:
        """
        Reschedule the calllater with a new delay time. It will reset the call time in seconds from
        the current time.

        :param task_id: The id to cancel.
        :param seconds_from_now: Number of seconds (or fraction of) from now to reschedule.
        :param request_context: Context about the request. Such as an IP address of the source.
        :param authentication: An auth item such as a websession or authkey.
        :return:
        """
        if task_id not in self.calllater:
            raise KeyError(f"'task_id' not found: {task_id}")

        self.calllater[task_id].reset(seconds_from_now=seconds_from_now, request_context=request_context,
                                      authentication=authentication)
