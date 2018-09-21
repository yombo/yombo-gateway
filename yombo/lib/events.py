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

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/events.html>`_
"""
from collections import OrderedDict
from copy import deepcopy
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.constants.events import SYSTEM_EVENT_TYPES
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import data_pickle, generate_source_string

logger = get_logger('library.events')

MAX_DURATION = 300

class Events(YomboLibrary):
    """
    A common location to collect system events. Not to be confused with notifications to display to users
    as a push notification. However, it may be common to create an event and a notification if it's urgent.
    """
    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo events library"

    def _init_(self, **kwargs):
        """
        Setup the queue so events can be saved right away.
        :param kwargs:
        :return:
        """
        self.event_queue = {}  # Save events in bulk.
        self.event_types = deepcopy(SYSTEM_EVENT_TYPES)
        self.db_save_event_queue = self._LocalDB.save_events_bulk
        self.save_event_queue_loop = LoopingCall(self.save_event_queue)
        self.save_event_queue_loop.start(21, False)

    @inlineCallbacks
    def _unload_(self, **kwargs):
        """
        Save remaining events on gateways shutdown.

        :return:
        """
        yield self.save_event_queue()

    def new(self, event_type, event_subtype, attributes, priority=None, user_id=None, user_type=None,
            created_at=None):

        if created_at is None:
            created_at = time()
        if priority is None:
            priority = 'normal'

        source_label = generate_source_string()  # get the module/class/function name of caller

        if event_type not in self.event_types:
            raise YomboWarning("Invalid event type: %s" % event_type)
        if event_subtype not in self.event_types[event_type]:
            raise YomboWarning("Invalid event sub-type: %s" % event_subtype)

        event = OrderedDict({
            'event_type': event_type,
            'event_subtype': event_subtype,
            'priority': priority,
            'source': source_label,
            'user_id': user_id,
            'user_type': user_type,
            'created_at': created_at,
            })
        event.update( OrderedDict({"attr%s" % (v + 1): k for v, k in enumerate(attributes)}) )
        length = str(len(event))
        if length not in self.event_queue:
            self.event_queue[length] = []

        self.event_queue[length].append(event)

    def new_type(self, event_type, event_subtype, description, attributes):
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
            'descrption': description,
            'attributes': attributes,
        }

    @inlineCallbacks
    def save_event_queue(self):
        if len(self.event_queue) == 0:
            return

        event_queue = deepcopy(self.event_queue)
        self.event_queue = {}
        for key, data in event_queue.items():
            yield self.db_save_event_queue(data)
