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

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/notifications.html>`_
"""
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.classes.sliceableordereddict import SliceableOrderedDict
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning, YomboHookStopProcessing
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.utils import random_string, is_true_false
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.notifications")


class Notification(Entity, LibraryDBChildMixin):
    """
    A class to manage a notification.
    """
    _Entity_type: ClassVar[str] = "Notification"
    _Entity_label_attribute: ClassVar[str] = "title"

    def __init__(self, parent, **kwargs):
        """
        Setup the notification object using information passed in.
        """
        super().__init__(parent, **kwargs)
        self.persist: bool = kwargs["incoming"].get("persist", False)

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


class Notifications(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages all notifications.

    """
    notifications = SliceableOrderedDict()
    notification_targets: dict = {}  # tracks available notification targets. This allows subscribers to know whats possible.

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "notification_id"
    _storage_primary_length: int = 16
    _storage_label_name: ClassVar[str] = "notification"
    _storage_class_reference: ClassVar = Notification
    _storage_attribute_name: ClassVar[str] = "notifications"
    _storage_pickled_fields: ClassVar[Dict[str, str]] = {
        "meta": "msgpack",
        "targets": "msgpack"}
    _storage_search_fields: ClassVar[List[str]] = [
        "notification_id", "gateway_id", "type", "title"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "created_at"

    @inlineCallbacks
    def _init_(self, **kwargs):
        yield self.load_from_database()

    def _load_(self, **kwargs):
        self._checkExpiredLoop = LoopingCall(self.check_expired)
        self._checkExpiredLoop.start(self._Configs.get("notifications.check_expired", 121, False), False)

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
        self._LocalDB.database.db_cleanup("notifications")

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
                              arguments={
                                  "notification": self.notifications[notice_id],
                                  "event": {
                                    "notification_id": notice_id,
                                    },
                                  }
                              )
        except YomboHookStopProcessing:
            pass

    @inlineCallbacks
    def new(self, title: str, message: str, gateway_id: Optional[str] = None,
            priority: Optional[str] = None, persist: Optional[bool] = None,
            timeout: Optional[Union[int, float]] = None, expire_at: Optional[Union[int, float]] = None,
            always_show: Optional[bool] = None, always_show_allow_clear: Optional[bool] = None,
            notice_type: Optional[str] = None, notice_id: Optional[str] = None, local: Optional[bool] = None,
            targets: Optional[List[str]] = None,
            request_by: Optional[str] = None, request_by_type: Optional[str] = None,
            request_context: Optional[str] = None,
            meta: Optional[dict] = None,
            acknowledged: Optional[bool] = None, acknowledged_at: Optional[int] = None,
            created_at: Optional[Union[int, float]] = None,
            # gateway_id: Optional[str] = None,
            create_event: Optional[bool] = None):
        """
        Add a new notice.

        :param title: Title, or label, for the not
        :returns: Pointer to new notice. Only used during unittest
        """
        if gateway_id is None:
            gateway_id = self._gateway_id
        if priority not in ("low", "normal", "high", "urgent"):
            priority = "normal"
        if persist is None:
            persist = False
        if always_show is None:
            always_show = False
        else:
            always_show = is_true_false(always_show)
        if isinstance(always_show, bool) is False:
            raise YomboWarning(f"always_show must be True or False, got: {always_show}")
        if always_show_allow_clear is None:
            always_show_allow_clear = False
        else:
            always_show_allow_clear = is_true_false(always_show_allow_clear)
        if isinstance(always_show_allow_clear, bool) is False:
            raise YomboWarning("always_show must be True or False.")
        if notice_type is None:
            notice_type = "notice"
        if notice_type not in ("notice"):
            raise YomboWarning("Invalid notification type.")
        if notice_id is None:
            notice_id = random_string(length=50)
        notice_id = self._Hash.sha224_compact(notice_id)
        if local is None:
            local = True
        else:
            local = is_true_false(local)

        if persist is True and always_show_allow_clear is False:
            raise YomboWarning(f"New notification cannot be 'persist'=True and 'always_show_allow_clear'=False..{title}")

        if isinstance(expire_at, int) or isinstance(expire_at, float):
            expire_at = time() + expire_at
        elif isinstance(timeout, int) or isinstance(timeout, float):
            expire_at = time() + timeout
        elif expire_at is not None:
            raise YomboWarning("expire_at must be int or float.")
        elif timeout is not None:
            raise YomboWarning("timeout must be int or float.")
        if persist is True and expire_at is None:
                expire_at = time() + 60*60*24*30  # keep persistent notifications for 30 days.

        if targets is not None:  # tags on where to send notifications
            if isinstance(targets, list) is False:
                if isinstance(targets, str):
                    targets = [targets]
                else:
                    raise YomboWarning("targets argument must be a list of strings.")
            for target in targets:
                if isinstance(target, str) is False:
                    raise YomboWarning("targets argument must be a list of strings.")

        if created_at is None:
            created_at = time()

        if acknowledged is None:
            acknowledged = False
        else:
            acknowledged = is_true_false(acknowledged)

        if isinstance(acknowledged_at, float):
            acknowledged_at = int(acknowledged_at)
        if acknowledged is True and acknowledged_at is None:
            acknowledged_at = int(time)

        notice = {
            "id": notice_id,
            "title": title,
            "message": message,
            "gateway_id": gateway_id,
            "priority": priority,
            "persist": persist,
            "always_show": always_show,
            "always_show_allow_clear": always_show_allow_clear,
            "type": notice_type,
            "local": local,
            "targets": targets,
            "request_by": request_by,
            "request_by_type": request_by_type,
            "request_context": request_context,
            "meta": meta,
            "acknowledged": acknowledged,
            "acknowledged_at": acknowledged_at,
            "expire_at": expire_at,
            "created_at": created_at,
        }
        if notice_id in self.notifications:
            del notice["id"]
            self.notifications[notice_id].update(notice)
            return self.notifications[notice_id]

        logger.debug("notice: {notice}", notice=notice)

        notification = yield self.load_an_item_to_memory(notice, load_source="local")

        reactor.callLater(.0001,
                          global_invoke_all,
                          "_notification_new_",
                          called_by=self,
                          arguments={
                              "notification": notification,
                              "target": targets,
                              "event": notification.to_dict(),
                              }
                          )
        return notification

    def delete(self, notice_id):
        """
        Deletes a provided notification.

        :param notice_id:
        :return:
        """
        notice_id = self._Hash.sha224_compact(notice_id)
        try:
            notice = self.notifications[notice_id]
        except KeyError:
            return

        try:
            global_invoke_all("_notification_delete_",
                              called_by=self,
                              arguments={
                                  "notification": notice,
                                  "event": {
                                    "notification_id": notice_id,
                                    }
                                  }
                              )
        except YomboHookStopProcessing:
            pass

        try:
            del self.notifications[notice_id]
            self._LocalDB.delete_notification(notice_id)
        except:
            pass

