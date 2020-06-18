"""
.. note::

  * For library documentation, see: `Web Sessions @ Library Documentation <https://yombo.net/docs/libraries/web_sessions>`_

Handles session information for the webinterface.

Sessions are lazy loaded on demand. Sessions can only be looked up using the session_long_id, which is not stored
anywhere - it's submitted as a cookie from the browser. The session_long_id also protects the session's
Yombo credentials.

To help keep memory requirements down, sessions are periodically purged from memory after they haven't been used for
a while. However, they session will be restored automatically when needed.

Some components and inspiration was taken from web.py: https://github.com/webpy/webpy . web.py is in the public domain;
it can be used for whatever purpose with absolutely no restrictions.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0 Added lazy loading of sessions.

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/websessions/__init__.html>`_
"""
# Import python libraries
from time import time
from random import randint
from ratelimit import limits as ratelimits
from typing import ClassVar, Dict, Type

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor

# Import Yombo libraries
from yombo.classes.dictobject import DictObject
from yombo.core.library import YomboLibrary
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.core.schemas import WebSessionSchema
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.utils import random_string, random_int

from yombo.lib.websessions.websession import WebSession

logger = get_logger("library.websessions")


class WebSessions(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Web session management library. When a browser makes a request, typically needs to be associated with each request.
    """
    web_sessions: dict = {}
    _storage_primary_field_name: ClassVar[str] = "auth_id"
    _storage_attribute_name: ClassVar[str] = "web_sessions"
    _storage_label_name: ClassVar[str] = "web_session"
    _storage_class_reference: ClassVar = WebSession
    _storage_schema: ClassVar = WebSessionSchema()
    _storage_pickled_fields: ClassVar[Dict[str, str]] = {"auth_data": "msgpack_zip"}
    _storage_search_fields: ClassVar[str] = [
        "auth_id"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "last_access_at"

    def __delitem__(self, key):
        """ Expire a session. """
        if key in self.web_sessions:
            logger.info("Expiring session, delete request: {session_id}", session_id=self.web_sessions[key].auth_id)
            self.web_sessions[key].expire()
        return

    def __getitem__(self, key):
        """ Get a web session by it's ID. """
        if key in self.web_sessions:
            return self.web_sessions[key]
        else:
            raise KeyError(f"Cannot find websession key: {key} -- Use yield self._WebSessions.get() instead")

    def _init_(self, **kwargs):
        """
        Setup cookie configuration options. Setup removing old/expired sessions from memory and database.

        :param kwargs:
        :return:
        """
        # self.session_id_lookup_cache = {}  # Stores lookups from the database.
        self.session_id_lookup_cache = self._Cache.ttl(name="lib.websessions.session_id_lookup_cache",
                                                       ttl=30,
                                                       tags=("websession",
                                                             "user")
                                                       )

        cookie_id = self._Configs.get("webinterface.cookie_id",
                                      self._Hash.sha224_compact(random_string(length=randint(500, 1000))))

        self.config = DictObject({
            "cookie_session_name": "yombo_" + cookie_id,
            "cookie_path": "/",
            "max_session": 15552000,      # How long session can be good for: 180 days
            "max_idle": 5184000,          # Max idle timeout: 60 days
            "max_session_no_auth": 1200,  # If not auth in 20 mins, delete session
            "ignore_expiry": True,
            "ignore_change_ip": True,
            "expired_message": "Session expired",
            "httponly": False,  # If enabled, frontend app won't work. :(
            "secure": False,
        })
        self.clean_sessions_loop = LoopingCall(self.clean_sessions)
        self.clean_sessions_loop.start(random_int(30, .2), False)  # Every hour-ish. Save to disk, or remove from memory.

    @inlineCallbacks
    def get(self, session_long_id: str) -> WebSession:
        """
        Gets a web session by it's long id (not the database id). This should only be called by the web interface
        authentication system.

        This returns a web session if it exists.

        :param session_long_id:
        """
        session_id = self._Hash.sha224_compact(session_long_id)

        if session_id in self.web_sessions:
            return self.web_sessions[session_id]
        results = yield self.get_session_by_id(session_id)
        return results

    @inlineCallbacks
    def get_session_by_id(self, session_long_id: str) -> WebSession:
        """
        Checks if the session ID is in the active session dictionary. If not, it queries the
        database and returns the session if it's found.

        :param session_long_id: The requested session id
        """
        def raise_error(message):
            """
            Sets the cache and raises an error.

            :param message:
            :return:
            """
            self.session_id_lookup_cache[session_id] = message + " (cached)"
            raise YomboWarning(message)
        logger.debug("get_session_by_id: session_long_id: {session_long_id}", session_long_id=session_long_id)

        if session_long_id is None:
            raise_error("Session long id is not valid.")
        if session_long_id == "LOGOFF":
            raise_error("Session has been logged off.")
        if self.validate_session_id(session_long_id) is False:
            raise_error("Invalid session id.")

        session_id = self._Hash.sha224_compact(session_long_id)
        logger.debug("get_session_by_id: session_id: {session_id}", session_id=session_id)
        if session_id in self.web_sessions:
            if self.web_sessions[session_id].enabled is True:
                return self.web_sessions[session_id]
            else:
                raise_error("Session is no longer valid. 1")
        else:
            if session_id in self.session_id_lookup_cache:
                logger.info("Session found in session_id_lookup_cache, going to return bad...")
                raise YomboWarning(self.session_id_lookup_cache[session_id])

            try:
                db_session = yield self.db_select(where={"id": session_id, "status": [1, "<="]})
            except Exception as e:
                raise_error(f"Cannot find session id: {e}")
            if len(db_session) == 0:
                raise_error("Session not found.")
            db_session = db_session[0]

            if self._gateway_id == "local":
                db_session["user"] = self._Users.system_user
            else:
                try:
                    db_session["user"] = self._Users.get(db_session["user_id"])
                except KeyError as e:
                    raise_error("User in session wasn't found.")

            del db_session["user_id"]
            db_session["auth_id"] = db_session["id"]
            yield self.load_an_item_to_memory(db_session, load_source="database")

            if self.web_sessions[session_id].enabled is True:
                return self.web_sessions[session_id]
            else:
                raise_error("Session is no longer valid.")

        raise_error("Unknown session lookup error.")

    def close_session(self, request: Type["twisted.web.http.Request"]) -> None:
        """
        Can be called by any route to logout the session. This will request the browser to clear out the cookie
        and marks the session expired..

        :param request:
        """
        cookie_session_name = self.config.cookie_session_name
        cookies = request.received_cookies
        if cookie_session_name in cookies:
            logger.debug("Closing session: {cookie_session_name}", cookie_session_name=cookie_session_name)
            request.addCookie(cookie_session_name, "LOGOFF", domain=self.get_cookie_domain(request),
                              path=self.config.cookie_path, expires="Thu, 01 Jan 1970 00:00:00 GMT",
                              secure=self.config.secure, httpOnly=self.config.httponly)
        reactor.callLater(.001, self.do_close_session, request)

    @inlineCallbacks
    def do_close_session(self, request: Type["twisted.web.http.Request"]) -> None:
        try:
            session = yield self.get_session_from_request(request)
        except YomboWarning:
            return
        logger.info("Closing session: {auth_id} ", auth_id=session.auth.auth_id)
        session.expire()
        try:
            del self.session_id_lookup_cache[session.auth.auth_id]
        except:
            pass
        session.expire()

    @inlineCallbacks
    def get_session_from_request(self, request: Type["twisted.web.http.Request"]) -> WebSession:
        """
        Checks the request for a valid session cookie and then tries to validate it.

        Returns True if everything is good, otherwise raises YomboWarning with
        status reason.

        :param request: The request instance.
        """
        if request is None:
            raise YomboWarning("get_session_from_request requires a non-None request object.")

        session_long_id = self.get_session_long_id_from_request(request)
        request.session_long_id = session_long_id

        logger.debug("get_session_from_request: Found session_long_id: {session_long_id}",
                     session_long_id=session_long_id)
        if session_long_id is None:
            raise YomboWarning("Session long id was not found in web request.")

        results = yield self.get_session_by_id(session_long_id)
        # logger.info("get_session_from_request: Found the session: {session}", session=results)
        return results

    def get_session_long_id_from_request(self, request: Type["twisted.web.http.Request"]) -> WebSession:
        """
        Checks the request for a valid session cookie and then tries to validate it.

        Returns True if everything is good, otherwise raises YomboWarning with
        status reason.

        :param request: The request instance.
        """
        if request is None:
            raise YomboWarning("get_session_long_id_from_request requires a non-None request object.")

        cookie_session_name = self.config.cookie_session_name
        cookies = request.received_cookies
        if cookie_session_name in cookies:
            return cookies[cookie_session_name]
        else:
            raise YomboWarning("Session cookie not found.")

    def get_cookie_domain(self, request: Type["twisted.web.http.Request"]) -> str:
        """
        Returns the FQDN of either the requested hostname or the configured FQDN. Returns the requested
        hostname if it doesn't match the configured FQDN to handle local IP address access.

        :param request:
        :return:
        """
        fqdn = self._Configs.get("dns.fqdn", None, False)
        host = str(request.getRequestHostname().decode())

        if fqdn is None:
            return host

        if host.endswith(fqdn):
            return fqdn
        else:
            return host

    @ratelimits(calls=15, period=60)
    @inlineCallbacks
    def create_from_web_request(self, request: Type["twisted.web.http.Request"] = None) -> WebSession:
        """
        Creates a new session.

        :param request:
        :return:
        """
        session_long_id = random_string(length=randint(60, 70))
        compact_id = self._Hash.sha224_compact(session_long_id)
        data = {
            "id": compact_id,
            "auth_data": {},
            "refresh_token": None,
            "refresh_token_expires_at": 0,
            "access_token": None,
            "access_token_expires_at": 0,
        }

        if request is not None:
            request.addCookie(self.config.cookie_session_name, session_long_id, domain=self.get_cookie_domain(request),
                              path=self.config.cookie_path, max_age=str(self.config.max_session),
                              secure=self.config.secure, httpOnly=self.config.httponly)
            request.received_cookies[self.config.cookie_session_name] = session_long_id

        results = yield self.load_an_item_to_memory(data)
        logger.info("create_from_web_request - {results}", results=results)
        return results

    def validate_session_id(self, session_long_id: str) -> bool:
        """
        Validate the session id to make sure it's reasonable.
        :param session_long_id:
        :return: 
        """
        if session_long_id == "LOGOFF":  # lets not raise an error.
            return True
        if session_long_id.isalnum() is False:
            return False
        if len(session_long_id) < 60:
            return False
        if len(session_long_id) > 80:
            return False
        return True

    def clean_sessions(self) -> None:
        """
        Cleanup the stored sessions from memory. This is periodically called by the looping call.
        """
        logger.debug("Clean_sessions starting....")
        current_time = int(time())
        for session_id in list(self.web_sessions.keys()):
            session = self.web_sessions[session_id]

            # delete session from memory after 30 minutes of not being active and not logged in yet!
            if session.user_id is None and session.last_access_at < current_time - 1800:
                logger.debug("clean_sessions - Deleting inactive session with no user! {session_id}",
                             session_id=session_id)
                del self.web_sessions[session_id]
                continue

            # Remove sessions older than 1 day if they haven't been used.
            if session.last_access_at < current_time - 86400:
                session.sync_item_data()
                logger.debug("clean_sessions - Deleting session from memory only: {session_id}",
                             session_id=session_id)
                del self.web_sessions[session_id]
