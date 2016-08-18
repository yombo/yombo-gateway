"""
Handles session information for th webinterface.

Currently, all sessions are loaded into memory.  Yes, not a good practice. Will tackle lazy loading later. Kept running
into issues with the new auth decorators, inlinecallbacks, and yields.

The number of sessions should be small, it's for a single family/business. Most use cases should be using the mobile
app, this is only for configuration.

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
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from random import randint

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, Deferred

from yombo.ext.expiringdict import ExpiringDict

# Import Yombo libraries
from yombo.utils.dictobject import DictObject
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import random_string

logger = get_logger("library.webconfig.session")

class Sessions(object):
    """
    Session management.
    """
    def __init__(self, loader):  # we do some simulation of a Yombo Library...
        self.loader = loader
        self._FullName = "yombo.gateway.lib.webinterface.sessions"
        self._Configs = self.loader.loadedLibraries['configuration']

        self.config = DictObject({
            'cookie_session': 'yombo_' + self._Configs.get('webinterface', 'cookie_session', random_string(length=randint(60,80))),
            'cookie_pin': 'yombo_' + self._Configs.get('webinterface', 'cookie_pin', random_string(length=randint(60,80))),
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
        self.localdb = self.loader.loadedLibraries['localdb']
        self.active_sessions = {}
        self.active_sessions_cache = ExpiringDict(200, 1)  # keep 200 entries, for at most 1 second

    @inlineCallbacks
    def init(self):
        db_sessions = yield self.localdb.get_dbitem_by_id_dict('Sessions')
        for session in db_sessions:
            session['session_data'] = json.loads(session['session_data'])
            self.active_sessions[session['id']] = Session(session['session_data'])
            self.active_sessions[session['id']].load(self, session)

        # print "active:sessions: %s" % self.active_sessions
        self._periodic_clean_sessions = LoopingCall(self.clean_sessions)
        self._periodic_clean_sessions.start(300)  # Every 5 mintes, save sessions to disk, remove stale ones from RAM.

    def _unload_(self):
        logger.debug("sessions:_unload_")
        self.unload_deferred = Deferred()
        self.clean_sessions(True)
        return self.unload_deferred

    def __delitem__(self, key):
        self.active_sessions[key].expire_session()

    def __getitem__(self, key):
        return self.active_sessions[key]

    def __len__(self):
        return len(self.active_sessions)

    def __setitem__(self, key, value):
        raise YomboWarning("Cannot set a session using this method.")

    def __contains__(self, key):
        if key in self.active_sessions:
            return True
        return False

    def has_session(self, request):
        """
        Checks the correct cookie exists and has a valid session. Returns True if it does, otherwise False.
        Doesn't create session if doesn't exist.

        :param request: The request instance.
        :return: bool
        """
        cookie_session = self.config.cookie_session
        cookies = request.received_cookies
        if cookie_session in cookies:
            session_id = cookies[cookie_session]
            try:
                if self.active_sessions_cache[session_id] == True:
                    return True
            except:
                pass
            if session_id in self.active_sessions:
                return self.active_sessions[session_id].check_valid()

    def close_session(self, request):
        if self.has_session(request):
            cookie_session = self.config.cookie_session
            session_id = request.received_cookies[cookie_session]
            self.active_sessions[session_id].expire_session()

            request.addCookie(cookie_session, 'LOGOFF', domain=self.config.cookie_domain,
                          path=self.config.cookie_path, expires='Thu, 01 Jan 1970 00:00:00 GMT',
                          secure=self.config.secure, httpOnly=self.config.httponly)

    # @inlineCallbacks
    def load(self, request):
        """
        Loads the session information based on the request. If cookie doesn't exist, it will create a new cookie and
        start the session.

        :param cookies: All the cookies that were sent in.
        :return:
        """
        logger.debug("load session: {request}", request=request)
        cookie_session = self.config.cookie_session
        cookies = request.received_cookies
        has_session = self.has_session(request)
        logger.debug("has session: {has_session}", has_session=has_session)
        if has_session:
            session_id = cookies[cookie_session]
            return self.active_sessions[session_id]
        return False

    def create(self, request):
        """
        Creates a new session.
        :param request:
        :return:
        """

        session_id = random_string(length=20)
        self.active_sessions[session_id] = Session()
        self.active_sessions[session_id].init(self, session_id)

        request.addCookie(self.config.cookie_session, session_id, domain=self.config.cookie_domain,
                          path=self.config.cookie_path, max_age=self.config.max_session,
                          secure=self.config.secure, httpOnly=self.config.httponly)

        return self.active_sessions[session_id]

    def set(self, request, name, value):
        """
        Set a session variable...if session exists.
        :param name:
        :param value:
        :return:
        """
        if self.has_session(request):
            try:
                self._data[request.received_cookies[self.config.cookie_session]][name] = value
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
                return self._data[request.received_cookies[self.config.cookie_session]][name]
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
                del self._data[request.received_cookies[self.config.cookie_session]][name]
                return True
            except:
                return False
        return None



    # def _validate_ip(self):
    #     # check for change of IP
    #     if self.session_id and self.get('ip', None) != web.ctx.ip:
    #         if not self._config.ignore_change_ip:
    #            return self.expired()
    #


    def _valid_session_id(self, session_id):
        if session_id.isalnum() is False:
            return False
        if len(session_id) != 96:
            return False

    @inlineCallbacks
    def clean_sessions(self, close_deferred=None):
        """
        Called by loopingcall.

        Cleanup the stored sessions
        """
        # print "active:sessions: %s" % self.active_sessions
        logger.debug("clean_sessions()")
        count = 0
        # session_delete_time = int(time()) - self.config.max_session
        # idle_delete_time = int(time()) - self.config.max_idle
        # max_session_no_auth_time = int(time()) - self.config.max_session_no_auth
        for session_id in self.active_sessions.keys():
            if self.active_sessions[session_id].check_valid() is False:
                del self.active_sessions[session_id]
                yield self.localdb.delete_session(session_id)
                count += 1
        logger.debug("Deleted {count} sessions from the session store.", count=count)

        for session_id, session in self.active_sessions.iteritems():
            db_session = yield self.localdb.get_session(session_id)
            # print "db session ons aving: %s" % db_session
            if db_session is None:
                # print "creating new db session record"
                yield self.localdb.save_session(session_id, json.dumps(session), session.created, session.last_access,
                                      session.updated)
            else:
                # print "updating old db record"
                yield self.localdb.update_session(session_id, json.dumps(session), session.last_access, session.updated)

        if close_deferred:
            self.unload_deferred.callback(1)

class Session(dict):
    """
    A single session.
    """
    def __init__(self,*arg,**kw):
        super(Session, self).__init__(*arg, **kw)
        self.__invalid = False

    def load(self, Sessions, session):
        self.Sessions = Sessions
        self.session_id = session['id']
        self.last_access = session['last_access']
        self.created = session['created']
        self.updated = session['updated']

    def init(self, Sessions, session_id):
        self.Sessions = Sessions
        self.session_id = session_id
        self['auth_pin'] = None
        self['auth_pin_time'] = None
        self['auth'] = None
        self['auth_id'] = None
        self['auth_time'] = None

        self.last_access = int(time())
        self.created = int(time())
        self.updated = int(time())

    def __getitem__(self, key):
        self.last_access = int(time())
        return dict.__getitem__(self, key)

    def __setitem__(self, key, val):
        if key not in ('last_access', 'created', 'updated'):
            self.updated = int(time())
        dict.__setitem__(self, key, val)

        return dict.__getitem__(self, key)

    def touch(self):
        self.last_access = int(time())

    def check_valid(self):
        # print "checking session valid!!! %s" % self.__invalid
        # print "time: %s" % time()
        if self.__invalid == True:
            return True

        if self.created < (int(time() - self.Sessions.config.max_session)):
            self.expire_session()
            # print "session invalid - created too old: %s" % self.created
            return False

        if self.last_access < (int(time()- self.Sessions.config.max_idle)):
            # print "session invalid - last access - idle too long"
            self.expire_session()
            return False

        if 'auth_id' in self:
            if self['auth_id'] is None and self.last_access < (int(time() - self.Sessions.config.max_session_no_auth)):
                # print "session invalid - last access - idle too long without auth"
                self.expire_session()
                return False
        else:
            if self.last_access < (int(time() - self.Sessions.config.max_session_no_auth)):
                # print "session invalid - last access - idle too long without auth"
                self.expire_session()
        return True

    def expire_session(self):
        self.__invalid = True
