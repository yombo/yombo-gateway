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
:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/websessions/websession.html>`_
"""
# Import python libraries
from time import time
from typing import ClassVar, List, Optional, Type

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import AUTH_TYPE_WEBSESSION
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.auth_mixin import AuthMixin
from yombo.mixins.user_mixin import UserMixin
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.utils import random_string

logger = get_logger("library.websessions.websession")


class WebSession(Entity, UserMixin, AuthMixin, LibraryDBChildMixin):
    """
    A single session.
    """
    _Entity_type: ClassVar[str] = "Web session"
    _Entity_label_attribute: ClassVar[str] = "auth_id"
    auth_type: ClassVar[str] = AUTH_TYPE_WEBSESSION

    def __str__(self):
        if self.user is None:
            return f"WebSession - {self.auth_id}, User: None"
        else:
            return f"WebSession - {self.auth_id}, User: {self.user.name} <{self.user.email}>"

    @property
    def display(self) -> str:
        return self.__str__()

    def __init__(self, parent, **kwargs) -> None:
        self.alerts = {}
        super().__init__(parent, **kwargs)

        # Auth specific attributes
        incoming = kwargs["incoming"]

        # Attempt to set _user based on user_id
        if "user" in incoming:
            self.user = incoming["user"]
        elif "user_id" in incoming:
            try:
                self.user = self._Parent._Users.get(incoming["user_id"])
            except:
                raise YomboWarning("User_id not found, cannot fully create websession.")

    def db_save_allow(self) -> bool:
        """ Only save to the database if there's a valid user. """
        if self.user_id is None:
            return False

    def add_alert(self, message, level="danger", display_once=True, deletable=True, id=None):
        """
        Add an alert to the stack.
        :param message:
        :param level: info, warning, error
        :param display_once: bool - If the message should only be displayed once.
        :return:
        """
        if id is None:
            id = random_string(length=15)
        self.alerts[id] = {
            "level": level,
            "message": message,
            "display_once": display_once,
            "deletable": deletable,
        }
        return id

    def get_alerts(self, autodelete: Optional[bool]=None) -> dict:
        """
        Retrieve a list of alerts for display.
        """
        # print(f"get_alerts: {self.alerts}")
        if autodelete is None:
            autodelete = True
        show_alerts = {}
        for keyid in list(self.alerts.keys()):
            show_alerts[keyid] = self.alerts[keyid]
            if self.alerts[keyid]["display_once"] is True and autodelete is True:
                del self.alerts[keyid]
        return show_alerts

    def authorization_header(self, request: Type["twisted.web.http.Request"]) -> str:
        """
        Used to generate the Authorization header for making Yombo API calls.

        :return:
        """
        access_token = self.get_access_token(request)
        return f"user_api_token {access_token[0]}"

    def is_valid(self) -> bool:
        """
        Checks if a session is valid or not.
        """
        if self.enabled is False:
            logger.info("is_valid: not valid - not enabled")
            return False

        if self.has_user is False:
            logger.info("is_valid: not valid - no user found.")
            return False

        return True

    def get_refresh_token(self, request: Type["twisted.web.http.Request"]) -> list:
        if self.refresh_token is None:
            raise YomboWarning("Refresh toking is missing.")

        session_refresh_token = self._Parent._Encryption.decrypt(self.refresh_token,
                                                                 passphrase=request.session_long_id)
        return session_refresh_token, self.refresh_token_expires_at

    def set_refresh_token(self, request: Type["twisted.web.http.Request"], token: str, expires_at: int):
        self.refresh_token = self._Parent._Encryption.encrypt(token, request.session_long_id)
        self.refresh_token_expires_at = expires_at
        self.updated_at = int(time())

    def get_access_token(self, request: Type["twisted.web.http.Request"]) -> list:
        if self.access_token is None:
            raise YomboWarning("Access token is missing.")
        if hasattr(request, 'session_access_token') is False:
            session_access_token = self._Parent._Encryption.decrypt(self.access_token,
                                                                    passphrase=request.session_long_id)
        return session_access_token, self.access_token_expires_at

    def set_access_token(self, request: Type["twisted.web.http.Request"], token, expires_at: int):
        self.access_token = self._Parent._Encryption.encrypt(token,
                                                             passphrase=request.session_long_id)
        self.access_token_expires_at = expires_at
        self.updated_at = int(time())
