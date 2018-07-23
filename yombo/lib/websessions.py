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
from ratelimit import limits as ratelimits

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.utils.dictobject import DictObject
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import random_string, random_int, sleep
from yombo.utils.decorators import memoize_ttl

logger = get_logger("library.websessions")

class WebSessions(YomboLibrary):
    """
    Session management.
    """
    active_sessions = {}

    def __delitem__(self, key):
        if key in self.active_sessions:
            logger.info("Expiring session, delete request: {auth_id}", auth_id=self.active_sessions[key].auth_id)
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

    def keys(self):
        """
        Returns the keys (command ID's) that are configured.

        :return: A list of command IDs.
        :rtype: list
        """
        return list(self.active_sessions.keys())

    def items(self):
        """
        Gets a list of tuples representing the commands configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.active_sessions.items())

    def _init_(self, **kwargs):
        self.gateway_id = self._Configs.get('core', 'gwid', 'local', False)
        cookie_id = hashlib.sha224( str(self._Gateways.get_master_gateway_id()).encode('utf-8') ).hexdigest()

        self.config = DictObject({
            'cookie_session_name': 'yombo_' + cookie_id,
            'cookie_path': '/',
            'max_session': 15552000,  # How long session can be good for: 180 days
            'max_idle': 5184000,  # Max idle timeout: 60 days
            'max_session_no_auth': 600,  # If not auth in 10 mins, delete session
            'ignore_expiry': True,
            'ignore_change_ip': True,
            'expired_message': 'Session expired',
            'httponly': True,
            'secure': False,
        })
        self.clean_sessions_loop = LoopingCall(self.clean_sessions)
        self.clean_sessions_loop.start(random_int(30, .2), False)  # Every hour-ish. Save to disk, or remove from memory.

    def _stop_(self, **kwargs):
        self.unload_deferred = Deferred()
        self.clean_sessions(self.unload_deferred)
        return self.unload_deferred

    @inlineCallbacks
    def get_all(self):
        """
        Returns the sessions from DB.

        :return: A list of dictionaries containting the sessions
        :rtype: list
        """
        yield self.clean_sessions(True)
        sessions = yield self._LocalDB.get_web_session()
        return sessions

    def get(self, key):
        if key in self.active_sessions:
            return self.active_sessions[key]
        raise KeyError("Cannot find web session: %s" % key)

    def close_session(self, request):
        cookie_session_name = self.config.cookie_session_name
        cookies = request.received_cookies
        if cookie_session_name in cookies:
            request.addCookie(cookie_session_name, 'LOGOFF', domain=self.get_cookie_domain(request),
                          path=self.config.cookie_path, expires='Thu, 01 Jan 1970 00:00:00 GMT',
                          secure=self.config.secure, httpOnly=self.config.httponly)

        reactor.callLater(.01, self.do_close_session, request)

    @inlineCallbacks
    def do_close_session(self, request):
        try:
            session = yield self.get_session_from_request(request)
        except YomboWarning:
            return
        logger.info("Closing session: {auth_id} ", auth_id=session.auth_id)
        session.expire_session()

    @inlineCallbacks
    def get_session_from_request(self, request=None):
        """
        Checks the request for a valid session cookie and then tries to validate it.

        Returns True if everything is good, otherwise raises YomboWarning with
        status reason.

        :param request: The request instance.
        :return: bool
        """
        session_id = None
        if request is not None:
            cookie_session_name = self.config.cookie_session_name
            cookies = request.received_cookies
            if cookie_session_name in cookies:
                session_id = cookies[cookie_session_name]
            else:
                raise YomboWarning("Session cookie not found.")

        results = yield self.get_session_by_id(session_id)
        return results

    @inlineCallbacks
    def get_session_by_id(self, session_id=None):
        """
        Checks if the session ID is in the active session dictionary. If not, it queries the
        database and returns the session.

        :param session_id: The requested session id
        :return: session
        """
        if session_id is None:
            raise YomboWarning("Session id is not valid.")
        if session_id == "LOGOFF":
            raise YomboWarning("Session has been logged off.")
        if self.validate_session_id(session_id) is False:
            raise YomboWarning("Invalid session id.")
        if session_id in self.active_sessions:
            if self.active_sessions[session_id].check_valid(auth_id_missing_ok=True) is True:
                return self.active_sessions[session_id]
            else:
                raise YomboWarning("Session is no longer valid.")
        else:
            try:
                db_session = yield self._LocalDB.get_web_session(session_id)
            except Exception as e:
                raise YomboWarning("Cannot find session id: %s" % e)
            self.active_sessions[session_id] = Auth(self, db_session, source='database')
            if self.active_sessions[session_id].is_valid is True:
                return self.active_sessions[session_id]
            else:
                raise YomboWarning("Session is no longer valid.")
        raise YomboWarning("Unknown session lookup error.")

    def get_cookie_domain(self, request):
        fqdn = self._Configs.get("dns", 'fqdn', None, False)
        host = "%s" % request.getRequestHostname().decode()

        if fqdn is None:
            return host

        if host.endswith(fqdn):
            return fqdn
        else:
            return host

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

    @ratelimits(calls=15, period=60)
    def create_from_request(self, request=None, data=None):
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

        self.active_sessions[data['id']] = Auth(self, data)
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

        Cleanup the stored sessions from memory
        """
        count = 0
        current_time = int(time())
        for session_id in list(self.active_sessions.keys()):
            session = self.active_sessions[session_id]

            if session.check_valid() is False and session.created_at > current_time - 600 \
                    and session.last_access > current_time - 120:
                print("clean_sessions - deleting session - not valid and is old..: %s" % session.session_data)
                del self.active_sessions[session_id]
                yield self._LocalDB.delete_web_session(session_id)
                count += 1

            if session.is_dirty >= 200 or close_deferred is not None or session.last_access < int(time() - (60*60)):
                if session.in_db:
                    logger.debug("clean_sessions - syncing web session to DB: {id}", id=session_id)
                    yield self._LocalDB.update_web_session(session)
                    session.is_dirty = 0
                elif session.auth_id is not None:
                    logger.info("clean_sessions - adding web session to DB: {id}", id=session_id)
                    yield self._LocalDB.save_web_session(session)
                    session.in_db = True
                    session.is_dirty = 0
                if session.last_access < int(time() - (60*60*6)):
                    # delete session from memory after 6 hours
                    logger.debug("clean_sessions - Deleting session from memory only: {session_id}", session_id=session_id)
                    del self.active_sessions[session_id]

        logger.debug("Deleted {count} sessions from the session store.", count=count)

        if close_deferred is not None and close_deferred is not True and close_deferred is not False:
            yield sleep(0.1)
            close_deferred.callback(1)


class Auth(object):
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

    @property
    def auth_id(self):
        return self._auth_id

    @auth_id.setter
    def auth_id(self, val):
        self._auth_id = val
        self.auth_at = time()

    def __init__(self, WebSessions, record, source=None):
        self._Parent = WebSessions
        self.is_valid = True
        self.is_dirty = 0
        if source == 'database':
            self.in_db = True
        else:
            self.in_db = False

        self.session_type = "websession"

        self._auth_id = None
        self.auth_at = None
        self.auth_pin = None
        self.auth_pin_at = None
        self.created_by = None
        self.gateway_id = record['gateway_id']
        self.session_id = record['id']
        self.last_access = int(time())
        self.created_at = int(time())
        self.updated_at = int(time())
        self.session_data = {
            'yomboapi_session': None,
            'yomboapi_login_key': None,
            'create_type': None,
        }
        # self.roles = []
        self.update_attributes(record, True)

    def update_attributes(self, record=None, stay_clean=None):
        """
        Update various attributes
        
        :param session_data:
        :return: 
        """
        if record is None:
            return
        if 'auth_id' in record:
            self.auth_id = record['auth_id']
        if 'is_valid' in record:
            self.is_valid = record['is_valid']
        if 'last_access' in record:
            self.last_access = record['last_access']
        if 'created_at' in record:
            self.created_at = record['created_at']
        if 'updated_at' in record:
            self.updated_at = record['updated_at']
        if 'session_data' in record:
            if isinstance(record['session_data'], dict):
                self.session_data.update(record['session_data'])
        if 'yomboapi_session' not in self.session_data:
            self.session_data['yombo_session'] = None
            if 'yomboapi_login_key' not in self.session_data:
                self.session_data['yomboapi_login_key'] = None
        # if 'roles' in record:
        #     if isinstance(record['roles'], list):
        #         self.roles = record['roles']

        if stay_clean is not True:
            self.is_dirty = 2000

    @property
    def user_id(self) -> str:
        return self.auth_id

    @property
    def user(self) -> str:
        return self._Parent._Users.get(self.auth_id)

    # def set_roles(self, roles):
    #     if isinstance(roles, list) is False:
    #         return
    #     self.roles = roles
    #
    # def add_role(self, label):
    #     if isinstance(label, str) is False:
    #         return
    #     if label not in self.roles:
    #         self.roles.append(label)
    #
    # def remove_role(self, label):
    #     if isinstance(label, str) is False:
    #         return
    #     if label in self.roles:
    #         self.roles.remove(label)

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
        if key in self.session_data:
            self.last_access = int(time())
            try:
                del self.session_data[key]
                self.updated_at = int(time())
                self.is_dirty = 200
            except:
                pass

    def touch(self):
        self.last_access = int(time())
        self.is_dirty += 1

    @memoize_ttl(60)
    def has_access(self, path, action, raise_error=None):
        """
        Check if api auth has access  to a resource / access_type combination.

        :param path:
        :param action:
        :raise_error action:
        :return:
        """
        print("web session checking auth")
        return self._Parent._Users.has_access(self.user.roles, path, action, raise_error)

    def check_valid(self, auth_id_missing_ok=None):
        """
        Checks if a session is valid or not.

        :return:
        """
        if self.is_valid is False:
            logger.info("check_valid: is_valid is false, returning False")
            return False

        if self.created_at < (int(time() - self._Parent.config.max_session)):
            logger.info("check_valid: Expiring session, it's too old: {auth_id}", auth_id=self.auth_id)
            self.expire_session()
            return False

        if self.last_access < (int(time() - self._Parent.config.max_idle)):
            logger.info("check_valid: Expiring session, no recent access: {auth_id}", auth_id=self.auth_id)
            self.expire_session()
            return False

        if self.auth_id is None and self.last_access < (int(time() - self._Parent.config.max_session_no_auth)):
            logger.info("check_valid: Expiring session, no recent access and not authenticated: {auth_id}", auth_id=self.auth_id)
            # print("self.last_access: %s, time: %s" % (self.last_access, int(time())))
            self.expire_session()
            return False

        if self.auth_id is None and auth_id_missing_ok is not True:
            logger.info("check_valid: auth_id is None, returning False")
            return False

        return True

    def expire_session(self):
        logger.info("Expiring session: {session}", session=self.session_id)
        self.is_valid = False
        self.is_dirty = 20000

    def asdict(self):
        return {
            'auth_id': self.auth_id ,
            'gateway_id': self.gateway_id,
            'session_id': self.session_id,
            'last_access': self.last_access,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'session_data': self.session_data,
            'is_valid': self.is_valid,
            'is_dirty': self.is_dirty,
        }