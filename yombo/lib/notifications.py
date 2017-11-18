# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Notifications @ Module Development <https://docs.yombo.net/Libraries/Notifications>`_


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

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://docs.yombo.net/gateway/html/current/_modules/yombo/lib/notifications.html>`_
"""
from collections import OrderedDict
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time
from itertools import islice

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboHookStopProcessing
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import random_string, is_true_false, global_invoke_all

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

        # root = self._OrderedDict__root
        # first = root[1]
        #
        # if key in self:
        #     link = self._OrderedDict__map[key]
        #     link_prev, link_next, _ = link
        #     link_prev[1] = link_next
        #     link_next[0] = link_prev
        #     link[0] = root
        #     link[1] = first
        #     root[1] = first[0] = link
        # else:
        #     root[1] = first[0] = self._OrderedDict__map[key] = [root, first, key]
        #     dict_setitem(self, key, value)

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

    @property
    def always_show_count(self) -> int:
        always_show_count = 0
        for id, notif in self.notifications.items():
            if notif.always_show:
                always_show_count += 1
        return always_show_count

    def iteritems(self, start=None, stop=None):
        return iter(self.notifications.items())

    def _init_(self, **kwargs):
        """
        Setups up the basic framework.
        """
        # self.init_deferred = Deferred()  # Prevents loader from moving on past _load_ until we are done.
        self.notifications = SlicableOrderedDict()
        self.gateway_id = 'local'
        # return self.init_deferred

    def _load_(self, **kwargs):
        self.gateway_id = self._Configs.get('core', 'gwid', 'local', False)

    # def _start_(self, **kwargs):
        self._checkExpiredLoop = LoopingCall(self.check_expired)
        self._checkExpiredLoop.start(self._Configs.get('notifications', 'check_expired', 121, False), False)
        self.load_notifications()

    def _stop_(self, **kwargs):
        if self.init_deferred is not None and self.init_deferred.called is False:
            self.init_deferred.callback(1)  # if we don't check for this, we can't stop!

    def _reload_(self):
        self.notifications.clear()
        self.load_notifications()

    def get_important(self):
        items = {}
        for notification_id, notification in self.notifications.items():
            if notification.priority in ('high', 'urgent'):
                items[notification_id] = notification
        return items

    def get_unreadbadge_count(self):
        count = 0
        for notification_id, notification in self.notifications.items():
            if notification.priority in ('high', 'urgent') and notification.acknowledged in (None, False):
                count += 1
        return count

    def check_expired(self):
        """
        Called by looping call to periodically purge expired notifications.
        :return:
        """
        cur_time = time()
        for id in list(self.notifications.keys()):
            if self.notifications[id].expire_at == "Never":
                continue
            if cur_time > self.notifications[id].expire_at:
                del self.notifications[id]
        self._LocalDB.delete_expired_notifications()

    @inlineCallbacks
    def load_notifications(self):
        """
        Load the last few notifications into memory.
        """
        notifications = yield self._LocalDB.get_notifications()
        for notice in notifications:
            notice = notice.__dict__
            if notice['expire_at'] < time():
                continue
            notice['meta'] = json.loads(notice['meta'])
            self.add(notice, from_db=True)
        logger.debug("Done load_notifications: {notifications}", notifications=self.notifications)
        # self.init_deferred.callback(10)

    def ack(self, notice_id, acknowledged_at=None, new_ack=None):
        """
        Acknowledge a notice id.

        :param notice_id:
        :return:
        """
        if notice_id not in self.notifications:
            raise KeyError('Notification not found: %s' % notice_id)

        if new_ack is None:
            new_ack = True

        if acknowledged_at is None:
            acknowledged_at = time()
        self.notifications[notice_id].set_ack(acknowledged_at, new_ack)

    def add(self, notice, from_db=None, create_event=None):
        """
        Add a new notice.

        :param notice: A dictionary containing notification details.
        :type record: dict
        :returns: Pointer to new notice. Only used during unittest
        """
        if 'title' not in notice:
            raise YomboWarning("New notification requires a title.")
        if 'message' not in notice:
            raise YomboWarning("New notification requires a message.")

        if 'id' not in notice:
            notice['id'] = random_string(length=16)
        else:
            if notice['id'] in self.notifications:
                self.notifications[notice['id']].update(notice)
                return notice['id']

        if 'type' not in notice:
            notice['type'] = 'notice'
        if 'gateway_id' not in notice:
            notice['gateway_id'] = self.gateway_id
        if 'priority' not in notice:
            notice['priority'] = 'normal'
        if 'source' not in notice:
            notice['source'] = ''
        if 'always_show' not in notice:
            notice['always_show'] = False
        else:
            notice['always_show'] = is_true_false(notice['always_show'])
        if 'always_show_allow_clear' not in notice:
            notice['always_show_allow_clear'] = True
        else:
            notice['always_show_allow_clear'] = is_true_false(notice['always_show_allow_clear'])
        if 'persist' not in notice:
            notice['persist'] = False
        if 'meta' not in notice:
            notice['meta'] = {}
        if 'user' not in notice:
            notice['user'] = None
        if 'local' not in notice:
            notice['local'] = False

        if notice['persist'] is True and 'always_show_allow_clear' is True:
            YomboWarning("New notification cannot have both 'persist' and 'always_show_allow_clear' set to true.")

        if 'expire_at' not in notice:
            if 'timeout' in notice:
                notice['expire_at'] = time() + notice['timeout']
            else:
                notice['expire_at'] = time() + 60*60*24*30 # keep persistent notifications for 30 days.
        else:
            if notice['expire_at'] == None:
                if notice['persist'] == True:
                    YomboWarning("Cannot persist a non-expiring notification")
            elif notice['expire_at'] > time():
                YomboWarning("New notification is set to expire before current time.")
        if 'created_at' not in notice:
            notice['created_at'] = time()

        if 'acknowledged' not in notice:
            notice['acknowledged'] = False
        else:
            if notice['acknowledged'] not in (True, False):
                YomboWarning("New notification 'acknowledged' must be either True or False.")

        if 'acknowledged_at' not in notice:
            notice['acknowledged_at'] = None

        logger.debug("notice: {notice}", notice=notice)
        if from_db is None and notice['persist'] is True:
            self._LocalDB.add_notification(notice)

        self.notifications.prepend(notice['id'], Notification(self, notice))

        # Call any hooks
        try:
            global_invoke_all('_notification_add_',
                              called_by=self,
                              notification=self.notifications[notice['id']],
                              stoponerror=False,
                              )
        except YomboHookStopProcessing:
            pass

        return notice['id']

    def delete(self, notice_id):
        """
        Deletes a provided notification.

        :param notice_id:
        :return:
        """
        # Call any hooks
        try:
            global_invoke_all('_notification_delete_',
                              called_by=self,
                              notification=self.notifications[notice['id']],
                              stoponerror=False,
                              )
        except YomboHookStopProcessing:
            pass

        try:
            del self.notifications[notice_id]
            self._LocalDB.delete_notification(notice_id)
        except:
            pass

    def get(self, notice_id, get_all=None):
        """
        Performs the actual search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find notification: `self._Notifications['8w3h4sa']`

        :raises YomboWarning: Raised when notifcation cannot be found.
        :param notice_id: The input type ID or input type label to search for.
        :type notice_id: string
        :return: A dict containing details about the notification
        :rtype: dict
        """
        if notice_id in self.notifications:
            return self.notifications[notice_id]
        else:
            raise YomboWarning('Notification not found: %s' % notice_id)

    @inlineCallbacks
    def select(self, criteria):
        """
        Select notifications based on various criteria.

        :param criteria: A dictionary containing field names and expected values.
        :return: List of dictionaries.
        """
        results = yield self._LocalDB.select_notifications(criteria)
        return results


class Notification:
    """
    A class to manage a notification.

    :ivar label: Command label
    :ivar description: The description of the command.
    :ivar inputTypeID: The type of input that is required as a variable.
    :ivar voice_cmd: The voice command of the command.
    """

    def __init__(self, parent, notice):
        """
        Setup the notification object using information passed in.
        """
        logger.debug("notice info: {notice}", notice=notice)

        self._Parent = parent
        self.notification_id = notice['id']
        self.gateway_id = notice['gateway_id']
        self.type = notice['type']
        self.priority = notice['priority']
        self.source = notice['source']
        if notice['expire_at'] == 0:
            self.expire_at = "None"
        else:
            self.expire_at = notice['expire_at']

        self.acknowledged = notice['acknowledged']
        self.acknowledged_at = notice['acknowledged_at']
        self.user = notice['user']
        self.title = notice['title']
        self.message = notice['message']
        self.meta = notice['meta']
        self.always_show = notice['always_show']
        self.always_show_allow_clear = notice['always_show_allow_clear']
        self.persist = notice['persist']
        self.local = notice['local']
        self.created_at = notice['created_at']

    def __str__(self):
        """
        Print a string when printing the class.  This will return the command_id so that
        the command can be identified and referenced easily.
        """
        return "%s: %s" % (self.notification_id, self.message)

    def set_ack(self, acknowledged_at=None, new_ack=None):
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

    def dump(self):
        """
        Export command variables as a dictionary.
        """
        return {
            'notification_id': str(self.notification_id),
            'gateway_id' : str(self.gateway_id),
            'type' : str(self.type),
            'priority': str(self.priority),
            'source': str(self.source),
            'expire_at': str(self.expire_at),
            'acknowledged': self.acknowledged,
            'acknowledged_at': float(self.acknowledged_at),
            'title': str(self.title),
            'message': str(self.message),
            'meta': str(self.meta),
            'always_show': str(self.always_show),
            'always_show_allow_clear': str(self.always_show_allow_clear),
            'persist': str(self.persist),
            'local': self.local,
            'created_at': str(self.created_at),
        }
