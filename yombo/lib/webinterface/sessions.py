"""
Handles session information for th webinterface.


Components and inspiration from web.py: https://github.com/webpy/webpy
web.py is in the public domain; it can be used for whatever purpose with absolutely no restrictions.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import os
from time import time
import datetime
import random
import base64
import os.path
from copy import deepcopy
try:
    import cPickle as pickle
except ImportError:
    import pickle

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.utils.dictobject import DictObject
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import get_component, random_string

logger = get_logger("library.webconfig.session")

class Sessions(object):
    """
    Session management.
    """
    def __init__(self, loader):
        self.loader = loader
        self._FullName = "yombo.gateway.lib.webinterface.sessions"
        self._Configs = self.loader.loadedLibraries['configuration']

        self.config = DictObject({
            'cookie_name': 'yombo_' + self._Configs.get('webinterface', 'cookie_suffix', random_string(length=30)),
            'cookie_domain': None,
            'cookie_path' : '/',
            'max_session': 15552000,  # How long session can be good for: 180 days
            'max_idle': 5184000,  # Max idle timeout: 60 days
            'max_session_no_auth': 600,  # If not auth in 10 mins, delete session
            'ignore_expiry': True,
            'ignore_change_ip': True,
            'expired_message': 'Session expired',
            'httponly': True,
            'secure': False,  # will change to true after SSL system/dns complete. - Mitch
        })
        self._data = None

    @inlineCallbacks
    def init(self):
        self._data = yield self.loader.loadedLibraries['SQLDict'].get(self, 'sessions')
        self._periodic_clean_sessions = LoopingCall(self.clean_sessions)
        self._periodic_clean_sessions.start(3600)  # every hour, clean expired sessions

    def blank_session(self):
        """
        Returns a dictionary.

        :return:
        """
        return {
            "session_id" : None,
            "auth_pin": None,
            "auth_pin_time": None,
            "auth": None,
            "auth_id": None,
            "auth_time": None,
            "last_access": None,
            "created": int(time()),

        }

    def __delitem__(self, key):
        del self._data[key]

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self):
        return len(self._data)

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        if key in self._data:
            return True
        return False

    def has_session(self, request):
        """
        Checks the correct cookie exists and has a valid session if it does. Doesn't create session if doesn't
        exist.

        :param cookies: All the cookies that were sent in.
        :return:
        """
        cookie_name = self.config.cookie_name
        cookies = request.received_cookies
        if cookie_name in cookies:
            if self._valid_session_id(cookies[cookie_name]) is False:
#                print "has_session::no valid cookie name"
                return False
        else:
            return False

#        print "cookis: %s" % cookies
        session_id = cookies[cookie_name]
#        print 'sessionid:%s' % session_id
#        print self._data
        if session_id not in self._data:
            return False
#        return True

        session_delete_time = int(time()) - self.config.max_session
        idle_delete_time = int(time()) - self.config.max_idle

#        print self._data[session_id]
#        print self._data[session_id]['last_access']
        if self._data[session_id]['last_access'] < idle_delete_time:
            del self._data[session_id]
            return False
        if self._data[session_id]['created'] < session_delete_time:
            del self._data[session_id]
            return False
        return True

    def close_session(self, request):
        if self.has_session(request):
            cookie_name = self.config.cookie_name
            session_id = request.received_cookies[cookie_name]
            try:
                del self._data[session_id]
            except:
                pass
            request.addCookie(cookie_name, 'LOGOFF', domain=self.config.cookie_domain,
                          path=self.config.cookie_path, expires='Thu, 01 Jan 1970 00:00:00 GMT',
                          secure=self.config.secure, httpOnly=self.config.httponly)

    def load(self, request):
        """
        Loads the session information based on the request. If cookie doesn't exist, it will create a new cookie and
        start the session.

        :param cookies: All the cookies that were sent in.
        :return:
        """
        print "load session: %s" % request
        cookie_name = self.config.cookie_name
        cookies = request.received_cookies
#        print self._data
        if self.has_session(request):
            session_id = cookies[cookie_name]
            return self._data[session_id]
        return None

    def create(self, request):
        # Doesn't exist or is not valid...session id is invalid, create new...
        cookie_name = self.config.cookie_name
        session_id = self._generate_session_id()
        self._data[session_id] = self.blank_session()
        self._data[session_id]['session_id'] = session_id
        request.addCookie(cookie_name, session_id, domain=self.config.cookie_domain,
                          path=self.config.cookie_path, max_age=self.config.max_session,
                          secure=self.config.secure, httpOnly=self.config.httponly)

        # self._check_expiry()
        self._data[session_id]['last_access'] = int(time())
#        self._validate_ip()
        return self._data[session_id]

    def set(self, request, name, value):
        """
        Set a session variable...if session exists.
        :param name:
        :param value:
        :return:
        """
        if self.has_session(request):
            try:
                self._data[request.received_cookies[self.config.cookie_name]][name] = value
                return True
            except:
                return False
        return None

    def get(self, request, name):
        """
        Set a session variable...if session exists.
        :param name:
        :param value:
        :return:
        """
        if self.has_session(request):
            try:
                return self._data[request.received_cookies[self.config.cookie_name]][name]
            except:
                return None
        return None

    def delete(self, request, name):
        """
        Set a session variable...if session exists.
        :param name:
        :param value:
        :return:
        """
        if self.has_session(request):
            try:
                del self._data[request.received_cookies[self.config.cookie_name]][name]
                return True
            except:
                return False
        return None

    def _check_expiry(self):
        # check for expiry
        if self.session_id and self.session_id not in self.store:
            if self.config.ignore_expiry:
                self.session_id = None
            else:
                return self.expired()

    # def _validate_ip(self):
    #     # check for change of IP
    #     if self.session_id and self.get('ip', None) != web.ctx.ip:
    #         if not self._config.ignore_change_ip:
    #            return self.expired()
    #

    def _generate_session_id(self):
        """Generate a random id for session"""
        return random_string(length=96)

    def _valid_session_id(self, session_id):
        if session_id.isalnum() is False:
            return False
        if len(session_id) != 96:
            return False

    def clean_sessions(self):
        """
        Called by loopingcall.

        Cleanup the stored sessions
        """
        count = 0
        session_delete_time = int(time()) - self.config.max_session
        idle_delete_time = int(time()) - self.config.max_idle
        max_session_no_auth_time = int(time()) - self.config.max_session_no_auth
        for session_id in self._data.keys():
            if self._data[session_id]['last_access'] < idle_delete_time:
                del self._data[session_id]
                count += 1
                continue
            if self._data[session_id]['created'] < max_session_no_auth_time and self._data[session_id]['auth'] is not True:
                del self._data[session_id]
                count += 1
                continue
            if self._data[session_id]['created'] < session_delete_time:
                del self._data[session_id]
                count += 1
    #
    # def expired(self):
    #     """Called when an expired session is atime"""
    #     self._killed = True
    #     self._save()
    #     raise SessionExpired(self._config.expired_message)
    #
    # def kill(self):
    #     """Kill the session, make it no longer available"""
    #     del self.store[self.session_id]
    #     self._killed = True

