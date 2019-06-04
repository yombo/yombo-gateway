"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from time import time
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.ext.twistar.utils import dictToWhere

# Import Yombo libraries
from yombo.lib.localdb import Notifications
from yombo.utils import instance_properties, data_pickle


class DB_Notifications(object):

    #############################
    ###    Notifications    #####
    #############################
    @inlineCallbacks
    def get_notifications(self):
        cur_time = int(time())
        records = yield Notifications.find(where=["expire_at > ?", cur_time], orderby="created_at DESC")
        return records

    @inlineCallbacks
    def delete_notification(self, id):
        try:
            records = yield self.dbconfig.delete("notifications", where=["id = ?", id])
        except Exception as e:
            pass

    @inlineCallbacks
    def add_notification(self, notice, **kwargs):
        args = {
            "id": notice["id"],
            "gateway_id": notice["gateway_id"],
            "type": notice["type"],
            "priority": notice["priority"],
            "source": notice["source"],
            "expire_at": notice["expire_at"],
            "always_show": notice["always_show"],
            "always_show_allow_clear": notice["always_show_allow_clear"],
            "acknowledged": notice["acknowledged"],
            "acknowledged_at": notice["acknowledged_at"],
            "user": notice["user"],
            "title": notice["title"],
            "message": notice["message"],
            "local": notice["local"],
            "targets": data_pickle(notice["targets"], encoder="json"),
            "meta": data_pickle(notice["meta"], encoder="json"),
            "created_at": notice["created_at"],
        }
        results = yield self.dbconfig.insert("notifications", args, None, "OR IGNORE")
        return results

    @inlineCallbacks
    def update_notification(self, notice, **kwargs):
        args = {
            "type": notice.type,
            "priority": notice.priority,
            "source": notice.source,
            "expire_at": notice.expire_at,
            "always_show": notice.always_show,
            "always_show_allow_clear": notice.always_show_allow_clear,
            "acknowledged": notice.acknowledged,
            "acknowledged_at": notice.acknowledged_at,
            "user": notice.user,
            "title": notice.title,
            "message": notice.message,
            "meta": data_pickle(notice.meta, encoder="json"),
            "targets": data_pickle(notice.targets, encoder="json"),
        }
        results = yield self.dbconfig.update("notifications", args, where=["id = ?", notice.notification_id])
        return results

    @inlineCallbacks
    def select_notifications(self, where):
        find_where = dictToWhere(where)
        records = yield Notifications.find(where=find_where)
        items = []
        for record in records:
            items.append(instance_properties(record, "_"))

        return items
