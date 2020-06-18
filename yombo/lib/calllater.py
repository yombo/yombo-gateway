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
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.mixins.child_storage_accessors_mixin import ChildStorageAccessorsMixin
from yombo.mixins.parent_storage_accessors_mixin import ParentStorageAccessorsMixin
from yombo.utils import random_string

logger = get_logger("library.callater")


class CallLaterItem(Entity, ChildStorageAccessorsMixin):
    """ Holds the reactor (task) and other data. """
    _Entity_type: ClassVar[str] = "Call later item"
    _Entity_label_attribute: ClassVar[str] = "calllater_id"

    @property
    def _primary_field_id(self):
        """ Get the ID for the object. """
        return self.__dict__[self._Parent._storage_primary_field_name]

    def __init__(self, parent, calllater_id: str, description: str, task, func: Callable) -> None:
        super().__init__(parent)
        self.calllater_id = calllater_id
        self.description = description
        self.task = task
        self.created_at = round(time(), 4)
        self.func = str(func)
        self.call_time = task.getTime()

    def cancel(self) -> None:
        """ Cancel the call later, then delete this id. """
        if self.task is not None and self.task.active():
            self.task.cancel()
        del self._Parent.calllater[self.calllater_id]


class CallLater(YomboLibrary, ParentStorageAccessorsMixin, LibrarySearchMixin):
    """
    Tracks callLater calls.
    """
    calllater: ClassVar[Dict[str, Any]] = {}
    _storage_attribute_name: ClassVar[str] = "calllater"
    _storage_attribute_sort_key: ClassVar[str] = "calllater_id"
    _storage_primary_field_name: ClassVar[str] = "calllater_id"
    _storage_fields: ClassVar[list] = ["calllater_id", "description", "call_time", "created_at"]
    _storage_attribute_sort_key: ClassVar[str] = "calllater_id"
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
        for calllater_id in list(self.calllater.keys()):
            task = self.calllater[calllater_id].task
            if task.active() is False:
                del self.calllater[calllater_id]

    def new(self, delay: Union[int, float], func: Callable, *args, _task_description=None, **kwargs):
        """
        A wrapper around twisted's callLater. This keeps track of call later events for debugging.

        :param delay:
        :param func:
        :param args:
        :param _task_description:
        :param kw:
        :return:
        """
        calllater_id = random_string(length=12)
        self.calllater[calllater_id] = CallLaterItem(self, calllater_id, _task_description,
                                                     reactor.callLater(delay, func, *args, **kwargs),
                                                     func
                                                     )
        return self.calllater[calllater_id].task

    def cancel(self, calllater_id: str) -> None:
        """
        Stop/cancel a call later task.

        :param calllater_id:
        :return:
        """
        if calllater_id not in self.calllater:
            raise KeyError(f"'task_id' not found: {calllater_id}")

        self.calllater[calllater_id].cancel()
