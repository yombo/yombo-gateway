# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * End user documentation: `Notifications @ User Documentation <https://yombo.net/docs/gateway/web_interface/notifications>`_
  * For library documentation, see: `Notifications @ Library Documentation <https://yombo.net/docs/libraries/notifications>`_

Responsible for receiving and distributing notifications. Typically, they are system messages that need
attention by the user, this includes alerts for devices, or system settings that need updating.

Priority levels:

* debug
* low
* normal
* high
* urgent

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2016-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/notifications.html>`_
"""
from collections import OrderedDict
import json
from time import time
from itertools import islice

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning, YomboHookStopProcessing
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.sync_to_everywhere_mixin import SyncToEverywhereMixin
from yombo.mixins.library_db_model_mixin import LibraryDBModelMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.utils import random_string, is_true_false
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.notifications")

class SlicableOrderedDict(OrderedDict):
    """
    Allows an ordereddict to be called with:  thisdict[1:2]

    Source: http://stackoverflow.com/questions/30975339/slicing-a-python-ordereddict
    Author: http://stackoverflow.com/users/1307905/anthon

    and

    Source: http://stackoverflow.com/questions/16664874/how-can-i-add-an-element-at-the-top-of-an-ordereddict-in-python
    Author: http://stackoverflow.com/users/846892/ashwini-chaudhary
    """
    def __getitem__(self, k):
        if not isinstance(k, slice):
            return OrderedDict.__getitem__(self, k)
        return SlicableOrderedDict(islice(self.items(), k.start, k.stop))

    def prepend(self, key, value, dict_setitem=dict.__setitem__):
        """
        Add an element to the front of the dictionary.
        :param key: 
        :param value: 
        :param dict_setitem: 
        :return: 
        """
        self.update({key: value})
        self.move_to_end(key, last=False)


class Notification(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
    """
    A class to manage a notification.
    """
    _primary_column = "notification_id"  # Used by mixins

    def __init__(self, parent, incoming, source=None):
        """
        Setup the notification object using information passed in.
        """
        self._Entity_type = "Notification"
        self._Entity_label_attribute = "title"
        super().__init__(parent)

        self.persist = incoming.get("persist", False)
        self._setup_class_model(incoming, source=source)

    def ack(self, acknowledged_at=None, new_ack=None):
        if acknowledged_at is None:
            acknowledged_at = time()
        if new_ack is None:
            new_ack = True
        self.acknowledged = new_ack
        self.acknowledged_at = acknowledged_at
        if self.always_show_allow_clear is True:
            self.always_show = False
        self._Parent._LocalDB.update_notification(self)

    def update(self, notice):
        """
        Uodates a notice values.

        :param notice:
        :return:
        """
        for key, value in notice.items():
            if key == 'id':
                continue
            setattr(self, key, value)


class Notifications(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Manages all notifications.

    """
    notifications = SlicableOrderedDict()
    notification_targets = {}  # tracks available notification targets. This allows subscribers to know whats possible.

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "notification"
    _class_storage_load_db_class = Notification
    _class_storage_attribute_name = "notifications"
    _class_storage_search_fields = [
        "notification_id", "gateway_id", "type", "title"
    ]
    _class_storage_sort_key = "created_at"

    @inlineCallbacks
    def _load_(self, **kwargs):
        self._checkExpiredLoop = LoopingCall(self.check_expired)
        self._checkExpiredLoop.start(self._Configs.get("notifications", "check_expired", 121, False), False)

        yield self._class_storage_load_from_database()

        results = yield global_invoke_all("_notification_get_targets_",
                                          called_by=self,
                                          )

        for component_name, data in results.items():
            logger.debug("Adding notification target: {component_name}", component_name=component_name)
            if isinstance(data, dict) is False:
                continue
            for target, description in data.items():
                if target not in self.notification_targets:
                    self.notification_targets[target] = []

                self.notification_targets[target].append({
                    "description": description,
                    "component": component_name,
                    }
                )

    def _notification_get_targets_(self, **kwargs):
        """ Hosting here since loader isn't properly called... """
        return {
            "system_startup_complete": "System startup complete",
        }

    def get_important(self):
        items = {}
        for notification_id, notification in self.notifications.items():
            if notification.priority in ("high", "urgent"):
                items[notification_id] = notification
        return items

    def get_unreadbadge_count(self):
        count = 0
        for notification_id, notification in self.notifications.items():
            if notification.priority in ("high", "urgent") and notification.acknowledged in (None, False):
                count += 1
        return count

    def check_expired(self):
        """
        Called by looping call to periodically purge expired notifications.
        :return:
        """
        self._LocalDB.cleanup_database("notifications")

    def ack(self, notice_id, acknowledged_at=None, new_ack=None):
        """
        Acknowledge a notice id.

        :param notice_id:
        :return:
        """
        if notice_id not in self.notifications:
            raise KeyError(f"Notification not found: {notice_id}")

        if new_ack is None:
            new_ack = True

        if acknowledged_at is None:
            acknowledged_at = int(time())
        self.notifications[notice_id].ack(acknowledged_at, new_ack)
        try:
            global_invoke_all("_notification_acked_",
                              called_by=self,
                              notification=self.notifications[notice_id],
                              event={
                                  "notification_id": notice_id,
                              }
                              )
        except YomboHookStopProcessing:
            pass

    def add(self, notice, from_db=None, create_event=None):
        """
        Add a new notice.

        :param notice: A dictionary containing notification details.
        :type record: dict
        :returns: Pointer to new notice. Only used during unittest
        """
        if "title" not in notice:
            raise YomboWarning("New notification requires a title.")
        if "message" not in notice:
            raise YomboWarning("New notification requires a message.")

        if "id" not in notice:
            notice["id"] = random_string(length=16)
        else:
            if notice["id"] in self.notifications:
                self.notifications[notice["id"]].update(notice)
                return notice["id"]

        if "type" not in notice:
            notice["type"] = "notice"
        if "gateway_id" not in notice:
            notice["gateway_id"] = self.gateway_id
        if "priority" not in notice:
            notice["priority"] = "normal"
        if "source" not in notice:
            notice["source"] = ""
        if "always_show" not in notice:
            notice["always_show"] = False
        else:
            notice["always_show"] = is_true_false(notice["always_show"])
        if "always_show_allow_clear" not in notice:
            notice["always_show_allow_clear"] = True
        else:
            notice["always_show_allow_clear"] = is_true_false(notice["always_show_allow_clear"])
        if "persist" not in notice:
            notice["persist"] = False
        if "meta" not in notice:
            notice["meta"] = {}
        if "user" not in notice:
            notice["user"] = None
        if "targets" not in notice:  # tags on where to send notifications
            notice["targets"] = []
        if isinstance(notice["targets"], str):
            notice["targets"] = [notice["targets"]]
        if "local" not in notice:
            notice["local"] = False

        if notice["persist"] is True and "always_show_allow_clear" is True:
            YomboWarning("New notification cannot have both 'persist' and 'always_show_allow_clear' set to true.")

        if "expire_at" not in notice:
            if "timeout" in notice:
                notice["expire_at"] = time() + notice["timeout"]
            else:
                notice["expire_at"] = time() + 60*60*24*30  # keep persistent notifications for 30 days.
        else:
            if notice["expire_at"] == None:
                if notice["persist"] == True:
                    YomboWarning("Cannot persist a non-expiring notification")
            elif notice["expire_at"] > time():
                YomboWarning("New notification is set to expire before current time.")
        if "created_at" not in notice:
            notice["created_at"] = time()

        if "acknowledged" not in notice:
            notice["acknowledged"] = False
        else:
            if notice["acknowledged"] not in (True, False):
                YomboWarning("New notification 'acknowledged' must be either True or False.")

        if "acknowledged_at" not in notice:
            notice["acknowledged_at"] = None

        logger.debug("notice: {notice}", notice=notice)

        self.notifications.prepend(notice["id"], Notification(self, notice))

        for target in notice["targets"]:
            reactor.callLater(.0001,
                              global_invoke_all,
                              "_notification_target_",
                              called_by=self,
                              notification=self.notifications[notice["id"]],
                              target=target,
                              event=self.notifications[notice["id"]].asdict()
                              )
        return notice["id"]

    def delete(self, notice_id):
        """
        Deletes a provided notification.

        :param notice_id:
        :return:
        """
        # Call any hooks
        try:
            global_invoke_all("_notification_delete_",
                              called_by=self,
                              notification=self.notifications[notice_id],
                              event={
                                  "notification_id": notice_id,
                              })
        except YomboHookStopProcessing:
            pass

        try:
            del self.notifications[notice_id]
            self._LocalDB.delete_notification(notice_id)
        except:
            pass

