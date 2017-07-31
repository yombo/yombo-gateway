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
from random import randint
import hashlib
# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, Deferred

# from yombo.ext.expiringdict import ExpiringDict

# Import Yombo libraries
from yombo.utils.dictobject import DictObject
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import random_string, random_int, sleep
# from yombo.utils.decorators import memoize_ttl

logger = get_logger("library.webconfig.session")

class Sessions(object):
    """
    Session management.
    """
    def __init__(self, loader):  # we do some simulation of a Yombo Library...
        self.loader = loader
        self._FullName = "yombo.gateway.lib.webinterface.sessions"
        self._Configs = self.loader.loadedLibraries['configuration']
        self._LocalDB = self.loader.loadedLibraries['localdb']
        self._Gateways = self.loader.loadedLibraries['gateways']
        self.gateway_id = self._Configs.get('core', 'gwid', 'local', False)
        cookie_id = hashlib.sha224( str(self._Gateways.get_master_gateway_id()).encode('utf-8') ).hexdigest()
        # print("session-cookie_id, get_master_gateway_id: %s = %s" % (self._Gateways.get_master_gateway_id(), cookie_id))

        self.config = DictObject({
            'cookie_session': 'yombo_' + cookie_id,
            'cookie_pin': 'yombo_' + cookie_id,
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
        self.active_sessions = {}
        # self.active_sessions_cache = ExpiringDict(200, 5)  # keep 200 entries, for at most 1 second...???

    # @inlineCallbacks
    def init(self):
        # print "active:sessions: %s" % self.active_sessions
        self._periodic_clean_sessions = LoopingCall(self.clean_sessions)
        self._periodic_clean_sessions.start(random_int(60, .7))  # Every 60-ish seconds. Save to disk, or remove from memory.

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

    @inlineCallbacks
    def has_session(self, request):
        """
        Checks the correct cookie exists and has a valid session. Returns True if it does, otherwise False.
        Doesn't create session if doesn't exist. Does load session informaiton into memory if it exists.

        :param request: The request instance.
        :return: bool
        """
        cookie_session = self.config.cookie_session
        cookies = request.received_cookies
        # logger.debug("has_session is looking for cookie: {cookie_session}", cookie_session=cookie_session)
        # logger.debug("has_session found cookies: {cookies}", cookies=cookies)

        if cookie_session in cookies:
            session_id = cookies[cookie_session]
            logger.debug("has_session found session_id in cookie: {session_id}", session_id=session_id)
            if self.validate_session_id(session_id) is False:
                raise YomboWarning("Invalid session id.")
            if session_id in self.active_sessions:
                return True
            else:
                logger.debug("has_session is looking in database for session...")
                db_session = yield self._LocalDB.get_session(session_id)
                logger.debug("has_session found db_session: {db_session}", db_session=db_session)
                if db_session is None:
                    return False
                # logger.debug("has_session - found in DB! {db_session}", db_session=db_session)
                self.active_sessions[db_session.id] = Session(self,
                                                              db_session.id,
                                                              db_session.gateway_id,
                                                              db_session.session_data,
                                                              source='database')
                return True
        return False

    def get_cookie_domain(self, request):
        fqdn = self._Configs.get("dns", 'fqdn', None, False)
        host = "%s" % request.getRequestHostname().decode();
        # print("get_cookie_domain...fqdn: %s" % fqdn)
        # print("get_cookie_domain...host: %s" % host)

        if fqdn is None:
            return host

        if host.endswith(fqdn):
            return fqdn
        else:
            return host

    def close_session(self, request):
        if self.has_session(request):
            cookie_session = self.config.cookie_session
            session_id = request.received_cookies[cookie_session]
            self.active_sessions[session_id].expire_session()

            request.addCookie(cookie_session, 'LOGOFF', domain=self.get_cookie_domain(request),
                          path=self.config.cookie_path, expires='Thu, 01 Jan 1970 00:00:00 GMT',
                          secure=self.config.secure, httpOnly=self.config.httponly)

    # @memoize_ttl(30)  # memoize for 5 seconds
    @inlineCallbacks
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
        has_session = yield self.has_session(request)
        logger.debug("has session: {has_session}", has_session=has_session)
        if has_session is False:
            return False
        session_id = cookies[cookie_session]
        if self.validate_session_id(session_id) is False:
            raise YomboWarning("Invalid session id.")
        return self.active_sessions[session_id]
        # return False

    def create(self, request=None, make_active=None, session_data=None, gateway_id=None):
        """
        Creates a new session.
        :param request:
        :param make_active: If True or None (default), then store sesion in memory.
        :return:
        """
        if session_data is None:
            session_data = {}
        if 'gateway_id' in session_data:
            gateway_id = session_data['gateway_id']
            if gateway_id is None:
                gateway_id = self.gateway_id
                session_data['gateway_id'] = gateway_id
        else:
            session_data['gateway_id'] = self.gateway_id

        if 'id' in session_data:
            session_id = session_data['id']
            del session_data['id']
        else:
            session_id = random_string(length=randint(19, 25))

        if gateway_id is None:
            gateway_id = self.gateway_id

        if request is not None:
            request.addCookie(self.config.cookie_session, session_id, domain=self.get_cookie_domain(request),
                              path=self.config.cookie_path, max_age=self.config.max_session,
                              secure=self.config.secure, httpOnly=self.config.httponly)

        if make_active is True or make_active is None:
            self.active_sessions[session_id] = Session(self, session_id, gateway_id, session_data)
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
                # print "name: %s" % name
                # print "self.config.cookie_session: %s" % self.config.cookie_session
                # print "data: %s" % self.active_sessions
                # print "request.received_cookies[self.config.cookie_session]: %s" % request.received_cookies[self.config.cookie_session]
                self.active_sessions[request.received_cookies[self.config.cookie_session]][name] = value
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
                return self.active_sessions[request.received_cookies[self.config.cookie_session]][name]
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
                del self.active_sessions[request.received_cookies[self.config.cookie_session]][name]
                return True
            except:
                return False
        return None

    def validate_session_id(self, session_id):
        """
        Validate the session id to make sure it's reasonable.
        :param session_id: 
        :return: 
        """
        if session_id.isalnum() is False:
            return False
        if len(session_id) < 15:
            return False
        if len(session_id) > 40:
            return False
        return True

    @inlineCallbacks
    def clean_sessions(self, close_deferred=None):
        """
        Called by loopingcall.

        Cleanup the stored sessions
        """
        # logger.debug("clean_sessions()")
        count = 0
        # session_delete_time = int(time()) - self.config.max_session
        # idle_delete_time = int(time()) - self.config.max_idle
        # max_session_no_auth_time = int(time()) - self.config.max_session_no_auth
        for session_id in list(self.active_sessions.keys()):
            if self.active_sessions[session_id].check_valid() is False or self.active_sessions[session_id].is_valid is False:
                del self.active_sessions[session_id]
                yield self._LocalDB.delete_session(session_id)
                count += 1
        # logger.debug("Deleted {count} sessions from the session store.", count=count)

        for session_id in list(self.active_sessions):
            session = self.active_sessions[session_id]
            # print "session.data['last_access']: %s" % session.data['last_access']
            # print "time: %s" % int(time() - (60*60*3))
            if session.is_dirty >= 200 or close_deferred is not None or session.data['last_access'] < int(time() - (60*5)):
                if session.in_db:
                    # session.in_db = True
                    logger.debug("updating old db session record: {id}", id=session_id)
                    yield self._LocalDB.update_session(session.session_id, session.data)
                else:
                    logger.debug("creating new db session record: {id}", id=session_id)
                    yield self._LocalDB.save_session(session.session_id, session.gateway_id, session.data)
                    session.in_db = True
                session.is_dirty = 0
                if session.data['last_access'] < int(time() - (60*60*3)):   # delete session from memory after 3 hours
                    logger.debug("Deleting session from memory: {session_id}", session_id=session_id)
                    del self.active_sessions[session_id]

        if close_deferred is not None:
            yield sleep(0.1)
            self.unload_deferred.callback(1)

class Session(object):
    """
    A single session.
    """

    def __contains__(self, data_requested):
        """
        Checks to if a provided data item is in the session.

        :raises YomboWarning: Raised when request is malformed.
        :param data_requested: The data item.
        :type data_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(data_requested)
            # print "aa 22"
            return True
        except Exception as e:
            return False

    def __setitem__(self, key, val):
        return self.set(key, val)

    def __getitem__(self, data_requested):
        """

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param data_requested: The command ID, label, or machine_label to search for.
        :type data_requested: string
        :return: The data.
        :rtype: mixed
        """
        return self.get(data_requested)

    def __setitem__(self, data_requested, value):
        """
        Set new value

        :raises Exception: Always raised.
        """
        return self.set(data_requested, value)

    def __delitem__(self, data_requested):
        """
        Delete value from session

        :raises Exception: Always raised.
        """
        self.delete(data_requested)

    def keys(self):
        """
        Get keys for a session.
        """
        return self.data.keys()

    def __init__(self, Sessions, session_id, gateway_id, session_data, source=None):
        self._Sessions = Sessions
        self.is_valid = True
        self.is_dirty = 0
        if source == 'dataabase':
            self.in_db = True
        else:
            self.in_db = False

        self.gateway_id = gateway_id
        self.session_id = session_id
        self.data = {
            'auth_pin': None,
            'auth_pin_time': None,
            'auth': None,
            'auth_id': None,
            'auth_time': None,
            'last_access': int(time()),
            'created': int(time()),
            'updated': int(time()),
            'is_valid': self.is_valid,
        }
        # print("sessions....data: %s" % self.data)
        self.update_attributes(session_data)
        # print("sessions....data: %s" % self.data)

    def update_attributes(self, session_data=None):
        """
        Load a session from a DB record.
        
        :param session_data:
        :return: 
        """
        # print("session update_attrs: %s" % session_data)
        if isinstance(session_data, dict):
            self.data.update(session_data)

    def get(self, key, default="BRFEqgdgLgI0I8QM2Em2nWeJGEuY71TTo7H08uuT"):
        # if key in self:
        #     print "zzz"
        if key in self.data:
            self.data['last_access'] = int(time())
            return self.data[key]
        if default != "BRFEqgdgLgI0I8QM2Em2nWeJGEuY71TTo7H08uuT":
            return default
        else:
            # return None
            raise KeyError("Cannot find session key: %s" % key)

    def set(self, key, val):
        if key == 'is_valid':
            raise YomboWarning("Use expire_session() method to expire this session.")
        if key == 'id':
            raise YomboWarning("Cannot change the ID of this session.")
        if key not in ('last_access', 'created', 'updated'):
            self.data['updated'] = int(time())
            self.data[key] = val
            self.is_dirty = 200
            return val
        raise KeyError("Session doesn't have key: %s" % key)

    def delete(self, key):
        if key in self:
            self.last_access = int(time())
            try:
                del self.data[key]
                self.data['updated'] = int(time())
                self.is_dirty = 200
            except:
                pass

    def touch(self):
        self.data['last_access'] = int(time())
        self.is_dirty += 1

    def check_valid(self):
        # print "checking session valid!!! %s" % self.__invalid
        # print "time: %s" % time()
        if self.is_valid is False:
            return False

        if self.data['created'] < (int(time() - self._Sessions.config.max_session)):
            self.expire_session()
            # print "session invalid - created too old: %s" % self.created
            return False

        if self.data['last_access'] < (int(time()- self._Sessions.config.max_idle)):
            # print "session invalid - last access - idle too long"
            self.expire_session()
            return False

        if 'auth_id' in self:
            if self.data['auth_id'] is None and self.data['last_access'] < (int(time() - self._Sessions.config.max_session_no_auth)):
                # print "session invalid - last access - idle too long without auth"
                self.expire_session()
                return False
        else:
            if self.data['last_access'] < (int(time() - self._Sessions.config.max_session_no_auth)):
                # print "session invalid - last access - idle too long without auth"
                self.expire_session()
        return True

    def expire_session(self):
        self.is_valid = False
        self.data['is_valid'] = False
        self.is_dirty = 20000
