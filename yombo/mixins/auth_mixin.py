# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For library documentation, see: `Devices @ Module Development <https://yombo.net/docs/libraries/users>`_

Mixin class for anything can act like an authentication. For example, users, websession, authkeys.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.22.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/mixins/auth_mixin.html>`_
"""
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from yombo.constants import AUTH_TYPE_USER, AUTH_TYPE_AUTHKEY, AUTH_TYPE_WEBSESSION, SENTINEL
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("mixins.auth_mixin")


class AuthMixin:
    def __contains__(self, element):
        """
        Checks if the provided data element exists.
        Checks to if a provided data item is in the session.

        :raises YomboWarning: Raised when request is malformed.
        :param element: The data item.
        :type element: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(element)
            return True
        except Exception as e:
            return False

    def __setitem__(self, key, val):
        return self.set(key, val)

    def __getitem__(self, element):
        """
        Get auth_data element.

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param element: The command ID, label, or machine_label to search for.
        :type element: string
        :return: The data.
        :rtype: mixed
        """
        return self.get(element)

    def __setitem__(self, data_requested, value):
        """
        Set auth_data element.

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
        return self.auth_data.keys()

    @property
    def accessor_id(self):
        """ Return either the  """
        if hasattr(self, "user") and self.user is not None:
            return self.user.user_id
        else:
            return getattr(self, self._Parent._storage_primary_field_name)

    @property
    def accessor_type(self):
        """ Return either the  """
        if hasattr(self, "user") and self.user is not None:
            return AUTH_TYPE_USER
        return self.auth_type

    @property
    def auth_id(self):
        """ Return the ID of the auth class. """
        return self.__dict__[self._Parent._storage_primary_field_name]

    @auth_id.setter
    def auth_id(self, val):
        self.__dict__[self._Parent._storage_primary_field_name] = val

    @property
    def display(self):
        """
        Display the auth information. For users, it will display their email address.  For
        everything else, it will be the auth_id.

        See: safe_display() for displaying the same information, but meant for hiding some bits of
        the ID so as not to be usable for accessing the gateway.

        :return:
        """
        raise NotImplemented("Display must be implemented in child classes.")

    @property
    def full_display(self):
        """
        Much like display(), but this will prepend the auth_type if auth isn't a user.

        See: safe_display() for displaying the same information, but meant for hiding some bits of
        the ID so as not to be usable for accessing the gateway.

        :return:
        """
        if hasattr(self, "user_id"):  # Here incase the ording was wrong on loading... BAD DEV!
            return super().display()
        elif self.auth_id is not None:
            return f"{self.auth_type}::{self.auth_id}"
        return None

    @property
    def safe_display(self):
        """
        Safely display the auth information without revealing much about it. For
        example, for users, it will display example@exam.... instead of example@example.com

        For everything else, it will display:
        auth_type::user_id[0:-8][0:10]
        This ensures the last 8 characters are hidden, while still trying to get at least 10 characters.

        Real example:

        authkey::8PkdA03sdW...

        :return:
        """
        if hasattr(self, "email") and self.email is not None:
            u = self.email.split("@")
            return u[0] + "@" + u[1][0:4] + "..."
        elif self.auth_id is not None:
            return f"{self.auth_type}::{self.auth_id[0:-8][0:10]}..."
        return None

    @property
    def has_user(self) -> bool:
        if self.auth_type == AUTH_TYPE_USER and self.auth_id is not None:
            return True
        return False

    @property
    def enabled(self):
        if self.status != 1:
            logger.info("is_valid: status is not 1")
            return False

        if self.created_at < (int(time() - self._Parent.config.max_session)):
            logger.info("is_valid: Expiring session, it's too old: {auth_id}", auth_id=self.auth_id)
            self.expire()
            return False

        if self.last_access_at < (int(time() - self._Parent.config.max_idle)):
            logger.info("is_valid: Expiring session, no recent access: {auth_id}", auth_id=self.auth_id)
            self.expire()
            return False

        if self.auth_id is None and self.last_access_at < (int(time() - self._Parent.config.max_session_no_auth)):
            logger.info("is_valid: Expiring session, no recent access and not authenticated: {auth_id}",
                        auth_id=self.auth_id)
            self.expire()
            return False

        return True

    def __init__(self, *args, **kwargs):
        self.status = 1
        self.auth_data = {}
        if hasattr(self, "gateway_id") is False or self.gateway_id is None:
            self.gateway_id = self._Parent._gateway_id
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            pass

    def get(self, key, default=SENTINEL):
        """
        Get an auth_data item.

        :param key:
        :param default:
        :return:
        """
        if key in ("last_access_at", "created_at", "updated_at", "auth_id", "user_id", "request_by"):
            return getattr(self, key)
        elif key in self.auth_data:
            return self.auth_data[key]
        elif default is not SENTINEL:
            return default
        else:
            raise KeyError("Cannot find auth key: {key}")

    def set(self, key, val):
        """
        Set an auth_data item.

        :param key:
        :param val:
        :return:
        """
        if key in ("last_access_at", "created_at", "updated_at", "auth_id", "user_id", "request_by"):
            raise YomboWarning(f"Cannot use this method to object attribute: {key}")
        elif key == "status":
            raise YomboWarning("Use enable, expire, delete, or disable methods to manage this auth.")
        elif key in ("auth_id", "user_id"):
            raise YomboWarning("Cannot change the ID of this session.")
        else:
            self.updated_at = int(time())
            self.auth_data[key] = val
            return val

    def delete(self, key) -> None:
        """
        Delete an auth_data item.

        :param key:
        :param default:
        :return:
        """
        if key in self.auth_data:
            try:
                del self.auth_data[key]
                self.updated_at = int(time())
            except Exception:
                pass

    def touch(self) -> None:
        """
        Touch the auth item, usually just update the last_access_at.

        :return:
        """
        self.update({"last_access_at": int(time())})

    def enable(self) -> None:
        """
        Enable an auth

        :return:
        """
        updates = {"status": 1}
        if hasattr(self, "expired_at"):
            updates["expired_at"] = None
        self.update(updates)

    def disable(self) -> None:
        """
        Disable an auth

        :return:
        """
        updates = {"status": 0}
        if hasattr(self, "expired_at"):
            updates["expired_at"] = None
        self.update(updates)

    def expire(self) -> None:
        """
        Delete/expire an auth

        :return:
        """
        logger.debug("Expiring '{auth_type}' id: {id}", auth_type=self.auth_type, id=self.auth_id)
        updates = {"status": 2}
        if hasattr(self, "expired_at"):
            updates["expired_at"] = int(time())
        self.update(updates)

    def is_allowed(self, platform, action, item_id: Optional[str] = None, raise_error: Optional[bool] = None):
        return self._Permissions.is_allowed(platform, action, item_id, self, raise_error)

    def is_valid(self) -> bool:
        """ Checks if an authentication item is valid. Returns True if it is."""
        return self.status == 1
