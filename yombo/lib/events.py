# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `Events @ Library Documentation <https://yombo.net/docs/libraries/events>`_

Logs system events to the database. Events (or logs) are different than notifications since events don't generate
notifications.

This layout was inspired by:
https://stackoverflow.com/questions/2797592/best-practice-logging-events-general-and-changes-database

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.21.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/events.html>`_
"""
from collections import OrderedDict
from copy import deepcopy
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.constants.events import SYSTEM_EVENT_TYPES
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.auth_mixin import AuthMixin
from yombo.utils.caller import caller_string
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.events")



class Events(YomboLibrary):
    """
    A common location to collect system events. Not to be confused with notifications to display to users
    as a push notification. However, it may be common to create an event and a notification if it's urgent.
    """

    _storage_primary_field_name: ClassVar[str] = "device_command_id"
    _storage_primary_length: ClassVar[int] = 25
    _startup_queue = {}  # Any device commands sent before the system is ready will be stored here.

    # The remaining attributes are used by various mixins.
    _storage_attribute_name: ClassVar[str] = "device_commands"
    _storage_label_name: ClassVar[str] = "device_command"
    _storage_class_reference: ClassVar = None
    _storage_pickled_fields: ClassVar[Dict[str, str]] = {"meta": "msgpack"}
    _storage_attribute_sort_key: ClassVar[str] = "created_at"
    _storage_attribute_sort_key_order: ClassVar[str] = "desc"

    enabled: ClassVar[bool] = False

    def _init_(self, **kwargs):
        """
        Setup the queue so events can be saved right away.
        :param kwargs:
        :return:
        """
        self.enabled = self._Configs.get("events.enabled", True)
        self.event_queue = {}  # Save events in bulk.
        self.event_types = deepcopy(SYSTEM_EVENT_TYPES)
        self.save_event_queue_running = False
        self.save_event_queue_loop = LoopingCall(self.save_event_queue)
        self.save_event_queue_loop.start(47, False)

    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Asks libraries and modules if they have any additional event types. This calls
        the modules after they have been imported, but before their init is called.

        :return:
        """
        event_types = yield global_invoke_all("_event_types_", called_by=self)
        for component, options in event_types.items():
            for event_type, event_data in options.items():
                if event_type not in self.event_types:
                    self.event_types[event_type] = {}
                for event_subtype, event_subdata in event_data.items():
                    if event_subtype in self.event_types:
                        logger.warn("Cannot add event type, already exists: {event_type}:{event_subtype}",
                                    event_type=event_type, event_subtype=event_subtype)
                        continue
                    self.event_types[event_type][event_subtype] = event_subdata

    @inlineCallbacks
    def _unload_(self, **kwargs):
        """
        Save remaining events on gateways shutdown.

        :return:
        """
        if self.enabled is False:
            return

        yield self.save_event_queue()

    def new(self, event_type: str, event_subtype: str, attributes: list = None, priority: str = None,
            request_by: Union[None, str] = None, request_by_type: Union[None, str] = None,
            request_context: Union[None, str] = None, authentication: Union[None, Type[AuthMixin]] = None,
            created_at=None) -> None:

        if self.enabled is False:
            return

        if created_at is None:
            created_at = round(time(), 3)
        elif isinstance(created_at, float):
            created_at = round(created_at, 3)
        if priority is None:
            priority = "normal"

        if request_context is None:
            request_context = caller_string()  # get the module/class/function name of caller

        if event_type not in self.event_types:
            raise YomboWarning(f"Invalid event type: {event_type}")
        if event_subtype not in self.event_types[event_type]:
            raise YomboWarning(f"Invalid event sub-type: {event_subtype}")
        if isinstance(attributes, list) is False and isinstance(attributes, tuple) is False:
            attributes = [attributes, ]

        try:
            request_by, request_by_type = self._Permissions.request_by_info(
                authentication, request_by, request_by_type)
        except YomboWarning:
            request_by, request_by_type = self._Permissions.request_by_info(self._Users.system_user)
        if request_context is None:
            request_context = caller_string()  # get the module/class/function name of caller

        event = {
            "event_type": event_type,
            "event_subtype": event_subtype,
            "priority": priority,
            "request_by": request_by,
            "request_by_type": request_by_type,
            "request_context": request_context,
            "created_at": created_at,
            }
        event.update(OrderedDict({f"attr{v + 1}": k for v, k in enumerate(attributes)}))
        length = str(len(event))
        if length not in self.event_queue:
            self.event_queue[length] = []

        self.event_queue[length].append(event)

    def new_type(self, event_type: str, event_subtype: str, description: str, attributes: Union[list, tuple]) -> None:
        """
        Used by modules to create new event types.

        :param event_type:
        :param event_subtype:
        :param description:
        :param attributes:
        :return:
        """
        if event_type not in self.event_types:
            self.event_types[event_type] = {}
        if event_subtype in self.event_types[event_type]:
            raise YomboWarning("Event type & sub type combo already exists.")
        self.event_types[event_type][event_subtype] = {
            "descrption": description,
            "attributes": attributes,
        }

    @inlineCallbacks
    def save_event_queue(self):
        """
        Bulk save events into the database.
        :return:
        """
        if self.enabled is False:
            self.event_queue = {}
            return

        if self.save_event_queue_running is True:
            return
        self.save_event_queue_running = True

        if len(self.event_queue) == 0:
            return

        event_queue = deepcopy(self.event_queue)
        self.event_queue = {}
        for key, data in event_queue.items():
            yield self._LocalDB.database.db_insert("events", data)

        self.save_event_queue_running = False
