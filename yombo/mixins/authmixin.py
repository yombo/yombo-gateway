# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For library documentation, see: `Devices @ Module Development <https://yombo.net/docs/libraries/users>`_

Mixin class for anything can act like an authentication. For example, users, websession, authkeys.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.22.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from time import time
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.yombobasemixin import YomboBaseMixin

logger = get_logger("mixins.authmixin")


class AuthMixin(YomboBaseMixin):

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
    def display(self):
        """
        Display the auth information. For users, it will display their email address.  For
        everything else, it will be the auth_id.

        See: safe_display() for displaying the same information, but meant for hiding some bits of
        the ID so as not to be usable for accessing the gateway.

        :return:
        """
        if hasattr(self, "_user_id"):  # Here incase the ording was wrong on loading... BAD DEV!
            return f"{self.name} <{self.email}>"
        return self.auth_id

    @property
    def full_display(self):
        """
        Much like display(), but this will prepend the auth_type if auth isn't a user.

        See: safe_display() for displaying the same information, but meant for hiding some bits of
        the ID so as not to be usable for accessing the gateway.

        :return:
        """
        if hasattr(self, "_user_id"):  # Here incase the ording was wrong on loading... BAD DEV!
            return f"{self.name} ({self.user_id}) <{self.email}>"
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
    def auth_id(self):
        if hasattr(self, "user_id") and self.user_id is not None:
            return self.user_id
        return self._auth_id

    @auth_id.setter
    def auth_id(self, val):
        self._set_auth_id(val)

    def _set_auth_id(self, val):
        self._auth_id = val

    @property
    def has_user(self) -> str:
        if hasattr(self, "_user_id"):
            if self._user_id is None:
                return False
            return True
        return False

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, val):
        self._enabled = val

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._enabled = True
        load_source = kwargs.get("load_source", "database")
        if load_source == "database":
            self.in_db = True
            self.is_dirty = 0
        else:
            self.in_db = False
            self.is_dirty = 1000

        self._auth_id = kwargs.get("auth_id", None)

        self.auth_data = {}
        # These are set by the item that actually created this instance.
        self.source = None  # Label of library or module that created this
        self.source_type = None  # one of: module, library

        # Original creation source. Typically used by authkeys and such to note where it was sourced.
        self.created_by = None  #
        self.created_by_type = None  # one of: user, module, library

        self.auth_type = None  # websession, user, authkey, etc
        self.gateway_id = None  # originating gateway_id, if available.

        self.last_access_at = int(time())
        self.created_at = int(time())
        self.updated_at = int(time())

    def get(self, key, default="BRFEqgdgLgI0I8QM2Em2nWeJGEuY71TTo7H08uuT"):
        """
        Get an auth_data item.

        :param key:
        :param default:
        :return:
        """
        if key in ("last_access_at", "created_at", "updated_at", "auth_id", "user_id", "created_by"):
            return getattr(self, key)
        elif key == "enabled":
            raise YomboWarning("Use expire() method to disable this auth.")
        elif key in self.auth_data:
            self.last_access_at = int(time())
            return self.auth_data[key]
        elif default != "BRFEqgdgLgI0I8QM2Em2nWeJGEuY71TTo7H08uuT":
            return default
        else:
            raise KeyError("Cannot find auth key: {key}")

    def set(self, key, val):
        """
        Set an auth_data item.

        :param key:
        :param default:
        :return:
        """
        if key in ("last_access_at", "created_at", "updated_at", "auth_id", "user_id", "created_by"):
            raise YomboWarning("Cannot use this method to object attribute: {key}", key=key)
        elif key == "enabled":
            raise YomboWarning("Use expire() method to disable this auth.")
        elif key in ("auth_id", "user_id"):
            raise YomboWarning("Cannot change the ID of this session.")
        else:
            self.updated_at = int(time())
            self.auth_data[key] = val
            if hasattr(self, "is_dirty"):
                self.is_dirty += 50
            return val

    def delete(self, key):
        """
        Delete an auth_data item.

        :param key:
        :param default:
        :return:
        """
        if key in self.auth_data:
            self.last_access_at = int(time())
            try:
                del self.auth_data[key]
                self.updated_at = int(time())
                if hasattr(self, "is_dirty"):
                    self.is_dirty += 50
            except Exception:
                pass

    def touch(self):
        """
        Touch the
        :return:
        """
        self.last_access_at = int(time())
        self.is_dirty += 1

    def has_access(self, platform, item, action, raise_error=None):
        """
        Check if auth has access to a resource / access_type combination.

        :param platform: device, command, etc
        :param item: *, device_id, command_id, etc
        :param action: view, edit, delete, etc
        :param raise_error: Bool if error should be raise on deny, or just return true/false
        :return:
        """
        return self._Parent._Users.has_access(self, platform, item, action, raise_error)

    def enable(self):
        """
        Enable an auth

        :return:
        """
        self.enabled = True
        if hasattr(self, "is_dirty"):
            self.is_dirty += 50000
        self.save()

    def is_valid(self):
        return self.enabled

    def expire(self):
        """
        Disable/expire an auth

        :return:
        """
        logger.debug("Expiring '{auth_type}' id: {id}", auth_type=self.auth_type, id=self._auth_id)
        self.enabled = False
        if hasattr(self, "is_dirty"):
            self.is_dirty += 50000
        self.save()

    def asdict(self):
        results = {
            "auth_id": self.auth_id,
            "auth_type": self.auth_type,
            "last_access_at": self.last_access_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "auth_data": self.auth_data,
            "enabled": self.enabled,
            "is_dirty": self.is_dirty,
        }

        if hasattr(self, "_user_id"):
            results['user_id'] = self._user_id
        else:
            results['user_id'] = None
