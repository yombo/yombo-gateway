"""
.. note::

  * For library documentation, see: `Web Sessions @ Library Documentation <https://yombo.net/docs/libraries/web_sessions>`_

Handles session information for the webinterface.

Currently, all sessions are loaded into memory.  Yes, not a good practice. Will tackle lazy loading later. Kept running
into issues with the new auth decorators, inlinecallbacks, and yields.

The number of sessions should be small, it's for a single family/business. Most use cases should be using the mobile
app, this is only for configuration.

Components and inspiration from web.py: https://github.com/webpy/webpy
web.py is in the public domain; it can be used for whatever purpose with absolutely no restrictions.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016-2018 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from time import time
from random import randint
from ratelimit import limits as ratelimits

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor

# Import Yombo libraries
from yombo.constants import AUTH_TYPE_WEBSESSION
from yombo.core.library import YomboLibrary
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.authmixin import AuthMixin
from yombo.mixins.usermixin import UserMixin
from yombo.utils import random_string, random_int, sha224_compact
from yombo.utils.dictobject import DictObject

logger = get_logger("library.websessions")


class WebSessions(YomboLibrary):
    """
    Session management.
    """
    active_sessions = {}

    def __delitem__(self, key):
        if key in self.active_sessions:
            logger.info("Expiring session, delete request: {session_id}", session_id=self.active_sessions[key].session_id)
            self.active_sessions[key].expire()
        return

    def __getitem__(self, key):
        if key in self.active_sessions:
            return self.active_sessions[key]
        else:
            raise KeyError(f"Cannot find websession key: {key}")

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
        self.gateway_id = self._Configs.get("core", "gwid", "local", False)
        cookie_id = self._Configs.get("webinterface", "cookie_id",
                                      sha224_compact(random_string(length=randint(500, 1000))))

        self.config = DictObject({
            "cookie_session_name": "yombo_" + cookie_id,
            "cookie_path": "/",
            "max_session": 15552000,  # How long session can be good for: 180 days
            "max_idle": 5184000,  # Max idle timeout: 60 days
            "max_session_no_auth": 1200,  # If not auth in 20 mins, delete session
            "ignore_expiry": True,
            "ignore_change_ip": True,
            "expired_message": "Session expired",
            "httponly": True,
            "secure": False,
        })
        self.clean_sessions_loop = LoopingCall(self.clean_sessions)
        self.clean_sessions_loop.start(random_int(30, .2), False)  # Every hour-ish. Save to disk, or remove from memory.
        self.get_session_by_id_cache = {}  # temporary until full bootup.

    def _start_(self, **kwargs):
        self.get_session_by_id_cache = self._Cache.ttl(name="lib.websessions.get_session_by_id_cache", ttl=30, tags=("websession", "user"))

    @inlineCallbacks
    def _stop_(self, **kwargs):
        yield self.clean_sessions(force_save=True)

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
        raise KeyError(f"Cannot find web session: {key}")

    def close_session(self, request):
        cookie_session_name = self.config.cookie_session_name
        cookies = request.received_cookies
        if cookie_session_name in cookies:
            logger.debug("Closing session: {cookie_session_name}", cookie_session_name=cookie_session_name)
            request.addCookie(cookie_session_name, "LOGOFF", domain=self.get_cookie_domain(request),
                          path=self.config.cookie_path, expires="Thu, 01 Jan 1970 00:00:00 GMT",
                          secure=self.config.secure, httpOnly=self.config.httponly)

        reactor.callLater(.01, self.do_close_session, request)

    @inlineCallbacks
    def do_close_session(self, request):
        try:
            session = yield self.get_session_from_request(request)
        except YomboWarning:
            return
        logger.info("Closing session: {session_id} ", session_id=session.session_id)
        session.expire()

    @inlineCallbacks
    def get_session_from_request(self, request=None):
        """
        Checks the request for a valid session cookie and then tries to validate it.

        Returns True if everything is good, otherwise raises YomboWarning with
        status reason.

        :param request: The request instance.
        :return: bool
        """
        logger.debug("get_session_from_request: {request}", request=request)

        session_id = None
        if request is not None:
            cookie_session_name = self.config.cookie_session_name
            cookies = request.received_cookies
            if cookie_session_name in cookies:
                session_id = cookies[cookie_session_name]
            else:
                raise YomboWarning("Session cookie not found.")

        logger.debug("get_session_from_request: Found session_id: {session_id}", session_id=session_id)
        if session_id is None:
            raise YomboWarning("Session id is not valid.")

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
        logger.debug("get_session_by_id: session_id: {session_id}", session_id=session_id)
        def raise_error(message):
            """
            Sets the cache and raises an error.

            :param message:
            :return:
            """
            self.get_session_by_id_cache[compact_id] = message + " (cached)"
            raise YomboWarning(message)

        if session_id is None:
            raise_error("Session id is not valid.")
        if self.validate_session_id(session_id) is False:
            raise_error("Invalid session id.")

        compact_id = sha224_compact(session_id)
        logger.debug("get_session_by_id: compact_id: {compact_id}", compact_id=compact_id)

        if compact_id in self.get_session_by_id_cache:
            cache = self.get_session_by_id_cache[compact_id]
            if isinstance(cache, str):
                raise YomboWarning(cache)
            else:
                return self.get_session_by_id_cache[compact_id]

        if session_id == "LOGOFF":
            raise_error("Session has been logged off.")
        if compact_id in self.active_sessions:
            if self.active_sessions[compact_id].check_valid(auth_id_missing_ok=True) is True:
                self.get_session_by_id_cache[compact_id] = self.active_sessions[compact_id]
                return self.active_sessions[compact_id]
            else:
                raise_error("Session is no longer valid.")
        else:
            try:
                db_session = yield self._LocalDB.get_web_session(compact_id)
                # db_session["id"] = session_id
            except Exception as e:
                raise_error(f"Cannot find session id: {e}")
            try:
                db_session["user"] = self._Users.get(db_session["user_id"])
            except KeyError as e:
                raise_error("User in session wasn't found.")
            self.active_sessions[compact_id] = AuthWebsession(self, db_session, load_source="database")
            self.active_sessions[compact_id].auth_id_long = session_id

            if self.active_sessions[compact_id].enabled is True:
                return self.active_sessions[compact_id]
            else:
                raise_error("Session is no longer valid.")
        raise_error("Unknown session lookup error.")

    def get_cookie_domain(self, request):
        fqdn = self._Configs.get("dns", "fqdn", None, False)
        host = str(request.getRequestHostname().decode())

        if fqdn is None:
            return host

        if host.endswith(fqdn):
            return fqdn
        else:
            return host

    @ratelimits(calls=15, period=60)
    def create_from_web_request(self, request=None, data=None):
        """
        Creates a new session.

        :param request:
        :return:
        """
        if data is None:
            data = {}
        if "gateway_id" not in data or data["gateway_id"] is None:
            data["gateway_id"] = self.gateway_id
        if "auth_data" not in data:
            data["auth_data"] = {}

        session_id = random_string(length=randint(60, 70))
        compact_id = sha224_compact(session_id)

        data["id"] = compact_id

        if request is not None:
            request.addCookie(self.config.cookie_session_name, session_id, domain=self.get_cookie_domain(request),
                              path=self.config.cookie_path, max_age=self.config.max_session,
                              secure=self.config.secure, httpOnly=self.config.httponly)

        self.active_sessions[compact_id] = AuthWebsession(self, data)
        self.active_sessions[compact_id].auth_id_long = session_id
        return self.active_sessions[compact_id]

    def set(self, request, name, value):
        """
        Set a session variable...if session exists.
        :param name:
        :param value:
        :return:
        """
        if self.has_session(request):
            try:
                self.active_sessions[request.received_cookies[self.config.cookie_session_name]].auth_data[name] = value
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
                del self.active_sessions[request.received_cookies[self.config.cookie_session_name]].auth_data[name]
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
        if len(session_id) < 30:
            return False
        if len(session_id) > 120:
            return False
        return True

    @inlineCallbacks
    def clean_sessions(self, force_save=None):
        """
        Called by loopingcall.

        Cleanup the stored sessions from memory
        """
        logger.debug("Clean_sessions starting....")
        count = 0
        current_time = int(time())
        for session_id in list(self.active_sessions.keys()):
            session = self.active_sessions[session_id]

            if session.enabled is False and session.created_at > current_time - 600 \
                    and session.last_access_at > current_time - 120:
                del self.active_sessions[session_id]
                yield self._LocalDB.delete_web_session(session_id)
                count += 1

            if session.is_dirty >= 200 or force_save is True or session.last_access_at < int(time() - (60*30)):
                if session.in_db:
                    logger.debug("clean_sessions - syncing web session to DB: {id}", id=session_id)
                    # print(f"clean_session: update_web_session: {self._LocalDB.update_web_session}")
                    try:
                        yield self._LocalDB.update_web_session(session)
                    except Exception as e:
                        logger.warn("Error saving web sessions: {e}", e=e)
                        continue
                    # print("clean_session: update_web_session: done")
                    session.is_dirty = 0
                elif session.user_id is not None:
                    logger.debug("clean_sessions - adding web session to DB: session_id: {id}", id=session_id)
                    logger.debug("clean_sessions - adding web session to DB: _auth_id: {id}", id=session._auth_id)
                    logger.debug("clean_sessions - adding web session to DB: _auth_id_long: {id}", id=session._auth_id_long)
                    try:
                        yield self._LocalDB.save_web_session(session)
                    except Exception as e:
                        logger.warn("Error saving web sessions: {e}", e=e)
                        continue
                    # print("clean_session: save_web_session: done")
                    session.in_db = True
                    session.is_dirty = 0
                if session.last_access_at < int(time() - (60*60*24)):
                    # delete session from memory after 24 hours
                    logger.debug("clean_sessions - Deleting session from memory only: {session_id}", session_id=session_id)
                    del self.active_sessions[session_id]
                if session.last_access_at < int(time() - (300)) and session.user_id is None:
                    # delete session from memory after 5 minutes of not being active and not logged in yet!
                    logger.debug("clean_sessions - Deleting inactive session with no user! {session_id}", session_id=session_id)
                    del self.active_sessions[session_id]
        logger.debug("Deleted {count} sessions from the session store.", count=count)


class AuthWebsession(UserMixin, AuthMixin):
    """
    A single session.
    """
    # Override AuthMixin
    def _set_auth_id(self, val):
        self._auth_id = val
        self.auth_at = time()

    # Override AuthMixin
    @property
    def enabled(self):
        """"""
        return self.check_valid()

    # Override AuthMixin
    @property
    def enabled(self):
        """"""
        return self.check_valid()

    # Override AuthMixin
    @property
    def auth_id_long(self):
        return self._auth_id_long

    @auth_id_long.setter
    def auth_id_long(self, val):
        self._auth_id_long = val

    # Local
    def __init__(self, parent, record, load_source=None):
        super().__init__(parent, load_source=load_source)

        # Auth specific attributes
        self.auth_type = AUTH_TYPE_WEBSESSION
        self.auth_type_id = 'user'
        self._auth_id = record["id"]
        self._auth_id_long = None  # will eventually be populated by a web request. Usually near creation time.
        self.source = "websessions"
        self.source_type = "library"
        self.gateway_id = record["gateway_id"]

        # Local attributes
        self.auth_at = None
        self.auth_pin = None
        self.auth_pin_at = None
        self._user = None

        # Attempt to set _user based on user_id
        if "user" in record:
            self._user = record["user"]
        elif "user_id" in record:
            try:
                self._user = self._Parent._Users.get(record["user_id"])
            except:
                raise YomboWarning("User_id not found, cannot fully create websession.")

        self.auth_data.update({
            "yomboapi_session": None,
            "yomboapi_login_key": None,
        })

        self.update_attributes(record, load_source == "database")

    def update_attributes(self, record=None, stay_clean=None):
        """
        Update various attributes
        
        :param record:
        :return: 
        """
        if record is None:
            return
        if "auth_id" in record:
            self._auth_id = record["auth_id"]
        if "enabled" in record:
            self._enabled = record["enabled"]
        if "last_access_at" in record:
            self.last_access_at = record["last_access_at"]
        if "created_at" in record:
            self.created_at = record["created_at"]
        if "updated_at" in record:
            self.updated_at = record["updated_at"]
        if "auth_data" in record:
            if isinstance(record["auth_data"], dict):
                self.auth_data.update(record["auth_data"])
        if "yomboapi_session" not in self.auth_data:
            self.auth_data["yombo_session"] = None
            if "yomboapi_login_key" not in self.auth_data:
                self.auth_data["yomboapi_login_key"] = None

        if stay_clean is not True:
            self.is_dirty = 2000

    def check_valid(self, auth_id_missing_ok=None):
        """
        Checks if a session is valid or not.

        :return:
        """
        if self._enabled is False:
            # logger.info("check_valid: enabled is false, returning False")
            return False

        if self.created_at < (int(time() - self._Parent.config.max_session)):
            # logger.info("check_valid: Expiring session, it's too old: {session_id}", session_id=self.session_id)
            self.expire()
            return False

        if self.last_access_at < (int(time() - self._Parent.config.max_idle)):
            # logger.info("check_valid: Expiring session, no recent access: {session_id}", session_id=self.session_id)
            self.expire()
            return False

        if self.auth_id is None and auth_id_missing_ok is not True:
            # logger.info("check_valid: auth_id is None, returning False")
            return False

        if self.auth_id is None and self.last_access_at < (int(time() - self._Parent.config.max_session_no_auth)):
            # logger.info("check_valid: Expiring session, no recent access and not authenticated: {auth_id}",
            #             auth_id=self.auth_id)
            self.expire()
            return False

        return True
