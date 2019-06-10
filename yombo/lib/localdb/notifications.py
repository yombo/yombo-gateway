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
from yombo.lib.localdb import Notification
from yombo.utils import instance_properties, data_pickle, data_unpickle

PICKLED_COLUMNS = [
    "meta", "targets"
]


class DB_Notifications(object):
    @inlineCallbacks
    def select_notifications(self, where):
        find_where = dictToWhere(where)
        records = yield Notification.find(where=find_where)
        items = []
        for record in records:
            items.append(instance_properties(record, "_"))

        return items
