# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

Responsible for receiving and distributing notifications. Typically, they are system messages that need
attention by the user, this includes alerts for devices, or system settings that need updating.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

.. versionadded:: 0.12.0

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
from collections import OrderedDict
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboFuzzySearchError, YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import random_string

logger = get_logger('library.notifications')

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
        x = SlicableOrderedDict()
        for idx, key in enumerate(self.keys()):
            if k.start <= idx < k.stop:
                x[key] = self[key]
        return x

    def prepend(self, key, value, dict_setitem=dict.__setitem__):

        root = self._OrderedDict__root
        first = root[1]

        if key in self:
            link = self._OrderedDict__map[key]
            link_prev, link_next, _ = link
            link_prev[1] = link_next
            link_next[0] = link_prev
            link[0] = root
            link[1] = first
            root[1] = first[0] = link
        else:
            root[1] = first[0] = self._OrderedDict__map[key] = [root, first, key]
            dict_setitem(self, key, value)

class Notifications(YomboLibrary):
    """
    Manages all notifications.

    """
    def __getitem__(self, notification_requested):
        """
        Return a notification by ID.

            >>> self._Notifications['137ab129da9318']  #by id

        :param notification_requested: The notification ID to search for.
        :type input_type_requested: string
        """
        return self.get(notification_requested)

    def __iter__(self):
        return self.notifications.__iter__()

    def __len__(self):
        return len(self.notifications)

    def __contains__(self, notification_requested):
        try:
            self.get(notification_requested)
            return True
        except:
            return False

    def iteritems(self, start=None, stop=None):
        return self.notifications.iteritems()

    def _init_(self):
        """
        Setups up the basic framework.
        """
        # self.init_deferred = Deferred()  # Prevents loader from moving on past _load_ until we are done.
        self.notifications = SlicableOrderedDict()
        # return self.init_deferred

    def _load_(self):
        self._LocalDB = self._Libraries['localdb']
        self._checkExpiredLoop = LoopingCall(self.check_expired)
        self._checkExpiredLoop.start(self._Configs.get('notifications', 'check_expired', 121, False))
        self.load_notifications()


    def _stop_(self):
        if self.init_deferred is not None and self.init_deferred.called is False:
            self.init_deferred.callback(1)  # if we don't check for this, we can't stop!

    def _clear_(self):
        """
        Clear all devices. Should only be called by the loader module
        during a reconfiguration event. B{Do not call this function!}
        """
        self.notifications.clear()

    def _reload_(self):
        self._clear_()
        self.load_notifications()

    def check_expired(self):
        """
        Called by looping call to periodically purge expired notifications.
        :return:
        """
        cur_time = time()
        for id, notice in self.notifications.iteritems():
            if cur_time > notice.expire:
                del self.notifications[id]
        self._LocalDB.delete_expired_notifications()

    def get(self, notification_requested):
        """
        Performs the actual search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find notification: `self._Notifications['8w3h4sa']`

        :raises YomboWarning: Raised when notifcation cannot be found.
        :param notification_requested: The input type ID or input type label to search for.
        :type notification_requested: string
        :return: A dict containing details about the notification
        :rtype: dict
        """
        if notification_requested in self.notifications:
            return self.notifications[notification_requested]
        else:
            raise YomboWarning('Notification not found: %s' % notification_requested)

    def delete(self, notification_requested):
        """
        Deletes a provided notification.

        :param notification_requested:
        :return:
        """
        try:
            del self.notifications[notification_requested]
        except:
            pass
        self._LocalDB.delete_notification(notification_requested)

    @inlineCallbacks
    def load_notifications(self):
        """
        Load the last few notifications into memory.
        """
        notifications = yield self._LocalDB.get_notifications()
        for notice in notifications:
            notice = notice.__dict__
            if notice['expire'] < time():
                continue
            notice['meta'] = json.loads(notice['meta'])
            self.add(notice, from_db=True)
        logger.debug("Done load_notifications: {notifications}", notifications=self.notifications)
        # self.init_deferred.callback(10)

    def add(self, notice, from_db=False, persist=True, create_event=False):
        """
        Add a new notice.

        :param notice: A dictionary containing notification details.
        :type record: dict
        :returns: Pointer to new notice. Only used during unittest
        """
        if 'id' not in notice:
            notice['id'] = random_string(length=16)
        if 'type' not in notice:
            notice['type'] = 'system'
        if 'priority' not in notice:
            notice['priority'] = 'normal'
        if 'source' not in notice:
            notice['source'] = ''

        if 'expire' not in notice:
            if 'timeout' in notice:
                notice['expire'] = time() + notice['timeout']
            else:
                notice['expire'] = time() + 3600
        else:
            if notice['expire'] > time():
                YomboWarning("New notification is set to expire before current time.")
        if 'created' not in notice:
            notice['created'] = time()

        if 'acknowledged' not in notice:
            notice['acknowledged'] = False
        else:
            if notice['acknowledged'] not in (True, False):
                YomboWarning("New notification 'acknowledged' must be either True or False.")

        if 'title' not in notice:
            raise YomboWarning("New notification requires a title.")
        if 'message' not in notice:
            raise YomboWarning("New notification requires a message.")
        if 'meta' not in notice:
            notice['meta'] = {}

        logger.debug("notice: {notice}", notice=notice)
        if from_db is False:
            self._LocalDB.add_notification(notice)
            self.notifications.prepend(notice['id'], Notification(notice))
        else:
            self.notifications[notice['id']] = Notification(notice)
            # self.notifications = OrderedDict(sorted(self.notifications.iteritems(), key=lambda x: x[1]['created']))
            pass
        return notice['id']


class Notification:
    """
    A class to manage a notification.

    :ivar label: Command label
    :ivar description: The description of the command.
    :ivar inputTypeID: The type of input that is required as a variable.
    :ivar voice_cmd: The voice command of the command.
    """

    def __init__(self, notice):
        """
        Setup the notification object using information passed in.
        """
        logger.debug("notice info: {notice}", notice=notice)

        self.notification_id = notice['id']
        self.type = notice['type']
        self.priority = notice['priority']
        self.source = notice['source']
        self.expire = notice['expire']
        self.acknowledged = notice['acknowledged']
        self.title = notice['title']
        self.message = notice['message']
        self.meta = notice['meta']
        self.created = notice['created']

    def __str__(self):
        """
        Print a string when printing the class.  This will return the command_id so that
        the command can be identified and referenced easily.
        """
        return "%s: %s" % (self.notification_id, self.message)

    def dump(self):
        """
        Export command variables as a dictionary.
        """
        return {
            'notification_id': str(self.notification_id),
            'type' : str(self.type),
            'priority': str(self.priority),
            'source': str(self.source),
            'expire': str(self.expire),
            'acknowledged': str(self.acknowledged),
            'title': str(self.title),
            'message': str(self.message),
            'meta': str(self.meta),
            'created': str(self.created),
        }
