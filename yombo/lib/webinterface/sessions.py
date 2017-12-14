"""
Handles session information for the webinterface.

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
from yombo.utils.datatypes import coerce_value

logger = get_logger("library.webinterface.sessions")

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
            'cookie_session_name': 'yombo_' + cookie_id,
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
        self._periodic_clean_sessions = LoopingCall(self.clean_sessions)
        self._periodic_clean_sessions.start(random_int(60, .7))  # Every 60-ish seconds. Save to disk, or remove from memory.

    def _unload_(self):
        logger.debug("sessions:_unload_")
        self.unload_deferred = Deferred()
        self.clean_sessions(self.unload_deferred)
        return self.unload_deferred

    def __delitem__(self, key):
        if key in self.active_sessions:
            self.active_sessions[key].expire_session()
        return

    def __getitem__(self, key):
        if key in self.active_sessions:
            return self.active_sessions[key]
        else:
            raise KeyError("Cannot find api auth key: %s" % key)

    def __len__(self):
        return len(self.active_sessions)

    def __setitem__(self, key, value):
        raise YomboWarning("Cannot set a session using this method.")

    def __contains__(self, key):
        if key in self.active_sessions:
            return True
        return False

    def __delitem__(self, key):
        if key in self.active_sessions:
            self.active_sessions[key].expire_session()
        return

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
    def get_all(self):
        """
        Returns the api auths from DB.

        :return: A list of command IDs.
        :rtype: list
        """
        yield self.clean_sessions(True)
        sessions = yield self._LocalDB.get_session()
        return sessions

    @inlineCallbacks
    def get(self, request=None, session_id=None):
        """
        Checks the request for an x-api-auth header and then tries to validate it.

        Returns True if everything is good, otherwise raises YomboWarning with
        status reason.

        :param request: The request instance.
        :return: bool
        """
        if session_id is None and request is not None:
            cookie_session_name = self.config.cookie_session_name
            cookies = request.received_cookies
            # logger.debug("has_session is looking for cookie: {cookie_session_name}", cookie_session_name=cookie_session_name)
            # logger.debug("has_session found cookies: {cookies}", cookies=cookies)
            if cookie_session_name in cookies:
                session_id = cookies[cookie_session_name]
            else:
                raise YomboWarning("Session cookie not found.")
                # logger.debug("has_session found session_id in cookie: {session_id}", session_id=session_id)

        if session_id is None:
            raise YomboWarning("Session id is not valid.")

        if session_id == "LOGOFF":
            raise YomboWarning("Session has been logged off.")
        if self.validate_session_id(session_id) is False:
            raise YomboWarning("Invalid session id.")
        if session_id in self.active_sessions:
            if self.active_sessions[session_id].is_valid is True:
                return self.active_sessions[session_id]
            else:
                raise YomboWarning("Invalid session is no longer valid.")
        else:
            try:
                db_session = yield self._LocalDB.get_session(session_id)
            except Exception as e:
                raise YomboWarning("Cannot find session id.")
            self.active_sessions[session_id] = Session(self, db_session, source='database')
            return self.active_sessions[session_id]
        raise YomboWarning("Unknown session lookup error..")

    def get_cookie_domain(self, request):
        fqdn = self._Configs.get("dns", 'fqdn', None, False)
        host = "%s" % request.getRequestHostname().decode();

        if fqdn is None:
            return host

        if host.endswith(fqdn):
            return fqdn
        else:
            return host

    def close(self, request):
        if self.has_session(request):
            cookie_session_name = self.config.cookie_session_name
            session_id = request.received_cookies[cookie_session_name]
            self.active_sessions[session_id].expire_session()
            request.addCookie(cookie_session_name, 'LOGOFF', domain=self.get_cookie_domain(request),
                          path=self.config.cookie_path, expires='Thu, 01 Jan 1970 00:00:00 GMT',
                          secure=self.config.secure, httpOnly=self.config.httponly)

    # @memoize_ttl(30)  # memoize for 5 seconds
    @inlineCallbacks
    def load(self, request):
        """
        Loads the session information based on the request. If cookie doesn't exist, it will create a new cookie and
        start the session.

        :param request: All the cookies that were sent in.
        :return:
        """
        # logger.debug("load session: {request}", request=request)
        cookie_session_name = self.config.cookie_session_name
        cookies = request.received_cookies
        has_session = yield self.has_session(request)
        # logger.debug("has session: {has_session}", has_session=has_session)
        if has_session is False:
            return False
        session_id = cookies[cookie_session_name]
        if session_id == "LOGOFF":
            return False

        if self.validate_session_id(session_id) is False:
            logger.info("Invalid session id found.")
            return False
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        else:
            return False

    def create(self, request=None, data=None):
        """
        Creates a new session.
        :param request:
        :return:
        """
        if data is None:
            data = {}
        if 'gateway_id' not in data or data['gateway_id'] is None:
            data['gateway_id'] = self.gateway_id
        if 'id' not in data or data['id'] is None:
            data['id'] = random_string(length=randint(30, 35))
        if 'session_data' not in data:
            data['session_data'] = {}

        if request is not None:
            request.addCookie(self.config.cookie_session_name, data['id'], domain=self.get_cookie_domain(request),
                              path=self.config.cookie_path, max_age=self.config.max_session,
                              secure=self.config.secure, httpOnly=self.config.httponly)

        self.active_sessions[data['id']] = Session(self, data)
        return self.active_sessions[data['id']]

    def set(self, request, name, value):
        """
        Set a session variable...if session exists.
        :param name:
        :param value:
        :return:
        """
        if self.has_session(request):
            try:
                self.active_sessions[request.received_cookies[self.config.cookie_session_name]].session_data[name] = value
                return True
            except:
                return False
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
                del self.active_sessions[request.received_cookies[self.config.cookie_session_name]].session_data[name]
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
        if session_id == "LOGOFF":  # lets not raise an error.
            return True
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
        # session_delete_at = int(time()) - self.config.max_session
        # idle_delete_at = int(time()) - self.config.max_idle
        # max_session_no_auth_at = int(time()) - self.config.max_session_no_auth
        for session_id in list(self.active_sessions.keys()):
            if self.active_sessions[session_id].check_valid() is False or self.active_sessions[session_id].is_valid is False:
                del self.active_sessions[session_id]
                yield self._LocalDB.delete_session(session_id)
                count += 1
        # logger.debug("Deleted {count} sessions from the session store.", count=count)

        for session_id in list(self.active_sessions):
            session = self.active_sessions[session_id]
            if session.is_dirty >= 200 or close_deferred is not None or session.last_access < int(time() - (60*5)):
                if session.in_db:
                    # session.in_db = True
                    logger.debug("updating old db session record: {id}", id=session_id)
                    yield self._LocalDB.update_session(session)
                else:
                    logger.debug("creating new db session record: {id}", id=session_id)
                    yield self._LocalDB.save_session(session)
                    session.in_db = True
                session.is_dirty = 0
                if session.last_access < int(time() - (60*60*3)):   # delete session from memory after 3 hours
                    logger.debug("Deleting session from memory: {session_id}", session_id=session_id)
                    del self.active_sessions[session_id]

        if close_deferred is not None and close_deferred is not True and close_deferred is not False:
            yield sleep(0.1)
            close_deferred.callback(1)

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
        return self.session_data.keys()

    def __init__(self, Sessions, record, source=None):
        self._Sessions = Sessions
        self.is_valid = True
        self.is_dirty = 0
        if source == 'database':
            self.in_db = True
        else:
            self.in_db = False

        self.gateway_id = record['gateway_id']
        self.session_id = record['id']
        self.last_access = int(time())
        self.created_at = int(time())
        self.updated_at = int(time())
        self.session_data = {
            'auth_pin': None,
            'auth_pin_at': None,
            'auth': None,
            'auth_id': None,
            'auth_at': None,
        }
        self.update_attributes(record, True)

    def update_attributes(self, record=None, called_from_init=None):
        """
        Update various attributes
        
        :param session_data:
        :return: 
        """
        if record is None:
            return
        if 'is_valid' in record:
            self.is_valid = record['is_valid']
        if 'last_access' in record:
            self.last_access = record['last_access']
        if 'created_at' in record:
            self.created_at = record['created_at']
        if 'updated_at' in record:
            self.updated_at = record['updated_at']
        if 'session_data' in record:
            if isinstance(record, dict):
                self.session_data.update(record['session_data'])
        if called_from_init is not True:
            self.is_dirty = 2000

    def get(self, key, default="BRFEqgdgLgI0I8QM2Em2nWeJGEuY71TTo7H08uuT"):
        if key in self.session_data:
            self.last_access = int(time())
            return self.session_data[key]
        if default != "BRFEqgdgLgI0I8QM2Em2nWeJGEuY71TTo7H08uuT":
            return default
        else:
            # return None
            raise KeyError("Cannot find session key: %s" % key)

    def set(self, key, val):
        if key == 'is_valid':
            raise YomboWarning("Use expire_session() method to expire this session.")
        if key == 'id' or key == 'session_id':
            raise YomboWarning("Cannot change the ID of this session.")
        if key not in ('last_access', 'created_at', 'updated_at'):
            self.updated_at = int(time())
            self.session_data[key] = val
            self.is_dirty = 200
            return val
        raise KeyError("Session doesn't have key: %s" % key)

    def delete(self, key):
        if key in self:
            self.last_access = int(time())
            try:
                del self.session_data[key]
                self.session_data['updated_at'] = int(time())
                self.is_dirty = 200
            except:
                pass

    def touch(self):
        self.last_access = int(time())
        self.is_dirty += 1

    def check_valid(self):
        if self.is_valid is False:
            return False

        if self.created_at < (int(time() - self._Sessions.config.max_session)):
            self.expire_session()
            return False

        if self.last_access < (int(time() - self._Sessions.config.max_idle)):
            self.expire_session()
            return False

        if 'auth_id' in self.session_data:
            if self.session_data['auth_id'] is None and self.last_access < (int(time() - self._Sessions.config.max_session_no_auth)):
                self.expire_session()
                return False
        else:
            if self.last_access < (int(time() - self._Sessions.config.max_session_no_auth)):
                self.expire_session()
        return True

    def expire_session(self):
        logger.info("Expiring session: {session}", session=self.session_id)
        self.is_valid = False
        self.is_dirty = 20000
