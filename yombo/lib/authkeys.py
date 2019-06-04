"""
.. note::

  * End user documentation: `Auth Keys @ User Documentation <https://yombo.net/docs/gateway/web_interface/authkeys>`_
  * For library documentation, see: `Auth Keys @ Library Documentation <https://yombo.net/docs/libraries/authkeys>`_

Handles auth key items for the webinterface, primarily used for accessing API endpoints and are used in
place of a username/password for scripts.

AuthKeys are only stored within the Yombo.ini file, however, any auth-keys marked with a scope of 'cluster'
will be usable on other gateways.

To help ensure AuthKey revocations across a cluster, deleted/expired keys are kept for 30 days.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2017-2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from time import time
from random import randint

# Import Yombo libraries
from yombo.constants import AUTH_TYPE_AUTHKEY
from yombo.core.library import YomboLibrary
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.authmixin import AuthMixin
from yombo.mixins.permissionmixin import PermissionMixin
from yombo.mixins.rolesmixin import RolesMixin
from yombo.mixins.synctoeverywhere import SyncToEverywhere
from yombo.utils import random_string, bytes_to_unicode, data_unpickle, data_pickle, sha256_compact
from yombo.utils.datatypes import coerce_value

logger = get_logger("library.authkey")

MIN_AUTHKEYID_LENGTH = 45
MAX_AUTHKEYID_LENGTH = 50


class AuthKeys(YomboLibrary):
    """
    Auth Key management.
    """
    authkeys = {}

    def __delitem__(self, key):
        """
        Delete's an authkey.

        :param key: 
        :return: 
        """
        if key in self.authkeys:
            self.authkeys[key].expire()
        return

    def __getitem__(self, key):
        """
        Returns the requested authkey or raises KeyError.

        :param key:
        :return:
        """
        return self.get(key)

    def __len__(self):
        return len(self.authkeys)

    def __setitem__(self, key, value):
        raise YomboWarning("Cannot set an authkey using this method.")

    def __contains__(self, key):
        try:
            self.get(key)
            return True
        except KeyError:
            return False

    def keys(self):
        """
        Returns the keys (command ID's) that are configured.

        :return: A list of command IDs.
        :rtype: list
        """
        return list(self.authkeys.keys())

    def items(self):
        """
        Gets a list of tuples representing the commands configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.authkeys.items())

    def _start_(self, **kwargs):
        self._load_authkeys_from_config()

    def _unload_(self, **kwargs):
        """
        Flush any pending changes to the config file.

        :param kwargs:
        :return:
        """
        for auth_id, authkey in self.authkeys.items():
            authkey.flush_sync()

    def _load_authkeys_from_config(self):
        """ Load authkey from the configuration file. """
        rbac_authkeys = self._Configs.get("rbac_authkeys", "*", {}, False, ignore_case=True)
        for authkey_id, authkey_raw in rbac_authkeys.items():
            authkey_data = data_unpickle(authkey_raw, encoder="msgpack_base64")
            self.add_authkey(authkey_data)

    def _load_authkeys_into_memory(self, data):
        """
        Loads a new authkey by creating a new instance based on dictionary items.

        :param data: A dictionary of items required to setup the authkey.
        :type data: dict
        :returns:
        """
        if "created_by" not in data:
            raise YomboWarning("created_by is required.")
        if "created_by_type" not in data:
            raise YomboWarning("'created_by_type' is required to be one of: system, user, or module")
        if "label" not in data:
            raise YomboWarning("Label is required for a role.")
        label = data["label"]
        for auth_id, auth in self.authkeys.items():
            if auth.label.lower() == label.lower():
                raise YomboWarning("Already exists.")

        if "auth_id" not in data:
            data["auth_id"] = random_string(length=randint(MIN_AUTHKEYID_LENGTH, MAX_AUTHKEYID_LENGTH))
        if "description" not in data:
            data["description"] = ""
        if "auth_data" not in data:
            data["auth_data"] = {}
        if "enabled" not in data:
            data["enabled"] = True
        if "item_permissions" not in data:
            data["item_permissions"] = {}
        if "roles" not in data:
            data["roles"] = []
        if "created_at" not in data:
            data["created_at"] = time()
        if "updated_at" not in data:
            data["updated_at"] = time()
        if "last_access_at" not in data:
            data["last_access_at"] = time()
        if "roles" not in data:
            data["roles"] = []
        if "scope" not in data:
            data["scope"] = "local"

        self.authkeys[data["auth_id"]] = AuthKey(self, data, source="database")
        return self.authkeys[data["auth_id"]]

    def get(self, key):
        """
        Get an Auth Key by key id (preferred) or by label.
        :param key:
        :return:
        """
        # print("authkey get: %s" % key)
        # print("authkey get: self.authkeys %s" % self.authkeys)
        if key in self.authkeys:
            return self.authkeys[key]
        else:
            for auth_id, auth in self.authkeys.items():
                if auth.label.lower() == key.lower():
                    return auth

        raise KeyError(f"Cannot find auth key: {key}")

    def get_session_from_request(self, request=None):
        """
        Called by the web interface auth system to check if the provided request
        has an auth key. Can be in the query string as "?_auth_key=key" or "?_api_auth=key"
        or in the header as "x-auth-key: key" or "x-api-auth: key"

        Returns the auth object if found otherwise raises YomboWarning.

        :param request: The web request instance.
        :return: bool
        """
        auth_id = None
        if request is not None:
            auth_id = bytes_to_unicode(request.getHeader(b"x-auth-key"))
            if auth_id is None:
                auth_id = bytes_to_unicode(request.getHeader(b"x-api-auth"))
            if auth_id is None:
                try:
                    auth_id = request.args.get("_auth_key")[0]
                except:
                    try:
                        auth_id = request.args.get("_api_auth")[0]
                    except:
                        pass

        if auth_id is None:
            raise YomboWarning("x-auth-key or x-api-auth header missing, nor _api_auth or _api_query query string is not found.")

        return self.get_session_by_id(auth_id)

    def get_session_by_id(self, auth_id):
        """
        Gets an Auth Key based on a auth_id.

        :param auth_id:
        :return:
        """
        if self.validate_auth_id(auth_id) is False:
            raise YomboWarning("auth key has invalid characters.")
        try:
            authkey = self.get(auth_id)
        except KeyError:
            raise YomboWarning("Auth Key isn't found")

        if authkey.enabled is False:
            raise YomboWarning("Auth Key is no longer enabled.")
        return authkey

    def delete(self, auth_id):
        """
        Deletes an Auth Key.

        :param auth_id:
        :return:
        """
        auth = self.get(auth_id)
        auth.expire()

    def rotate(self, auth_id):
        """
        Rotates an Auth Key for security.

        :return:
        """
        auth = self.get(auth_id)
        auth.rotate()
        return auth

    def finish_rotate_key(self, old, new, auth):
        self.authkeys[new] = auth
        del self.authkeys[old]

    def update(self, auth_id=None, data=None):
        """
        Updates an Auth Key

        :param request:
        :return:
        """
        auth_key = self.get(auth_id)
        if data is None or isinstance(data, dict) is False:
            raise YomboWarning("'data' must be a dictionary.")
        auth_key.update_attributes(data)

    def validate_auth_id(self, auth_id):
        """
        Validate the session id to make sure it's reasonable.

        :param auth_id:
        :return: 
        """
        if auth_id == "LOGOFF":  # lets not raise an error.
            return True
        if auth_id.isalnum() is False:
            return False
        if len(auth_id) < MIN_AUTHKEYID_LENGTH-5:  # Allows decreasing the length by 5 in the future.
            return False
        if len(auth_id) > MAX_AUTHKEYID_LENGTH+5:
            return False
        return True

    def save_authkeys(self):
        """
        Called by loopingcall and when exiting.

        Saves session information to config file.
        """
        for auth_id, authkey in self.authkeys.items():
            authkey.save()


class AuthKey(AuthMixin, PermissionMixin, RolesMixin, SyncToEverywhere):
    """
    A single auth key item.
    """
    @property
    def editable(self):
        """
        Checks if the authkey is editable. Only user generated ones are.
        :return:
        """
        if self.created_by == "user":
            return True
        return False

    @property
    def _sync_fields(self):
        return ["auth_data", "enabled", "accepted_at", "scope", "label", "description", "created_by", "created_by_type",
                "created_at", "updated_at", "last_access_at", "item_permissions", "roles", "auth_id"]

    def __init__(self, parent, record, source=None):
        self._internal_label = "rbac_authkeys"  # Used by mixins
        self._syncs_to_db = False
        self._syncs_to_yombo = False
        self._syncs_to_config = True
        super().__init__(parent, load_source="database")

        # Auth specific attributes
        self.auth_type = AUTH_TYPE_AUTHKEY
        self.auth_type_id = AUTH_TYPE_AUTHKEY
        self._auth_id = record["auth_id"]

        # Local attributes
        self.label = ""
        self.description = ""
        self.auth_id = record["auth_id"]
        self.last_access_at = 1
        self.expired_at = None

        if "roles" in record:
            roles = record["roles"]
            if len(roles) > 0:
                for role in roles:
                    try:
                        self.attach_role(role, save=False, flush_cache=False)
                    except KeyError:
                        logger.warn("Cannot find role for user, removing from user: {role}", role=role)
                        # Don't have to actually do anything, it won't be added, so it can't be saved. :-)

        self.update_attributes(record, source=source)
        self.start_data_sync()

    def update_attributes(self, record, source=None):
        """
        Update various attributes
        
        :param record:
        :return: 
        """
        if record is None:
            return
        if "auth_data" in record:
            if isinstance(record["auth_data"], dict):
                temp = self.auth_data.copy()
                temp.update(record["auth_data"])
                record["auth_data"] = temp
        if "enabled" in record:
            record["enabled"] = coerce_value(record["enabled"], "bool")
        if "scope" in record:
            if record["scope"] not in ("local", "cluster"):
                raise YomboWarning(f"Auth key scope must be one of: local, cluster.  '{record['scope']}'"
                                   " is not permitted.")
        if "item_permissions" in record:
            if isinstance(record["item_permissions"], dict) is False:
                del record["item_permissions"]
        if "roles" in record:
            if isinstance(record["roles"], list):
                for role_id in record["roles"]:
                    try:
                        self.attach_role(role_id, save=False, flush_cache=False)
                    except KeyError:
                        logger.warn("Auth key {label} was unable to add role_id (don't exist)", label=self.label)

        super().update_attributes(record, source=source)

    def rotate(self):
        """
        Rotates the authkey ID. It's a good idea to rotate keys regularly.

        :return:
        """
        old_auth_id = self.auth_id
        self.auth_id = random_string(length=randint(50, 55))
        self._Parent.finish_rotate_key(old_auth_id, self.auth_id, self)

    def is_valid(self):
        """
        Checks if a session is valid or not.

        :return:
        """
        if self.enabled is True:
            # logger.info("is_valid: enabled is false, returning False")
            return True
        return False

    def expire(self):
        """ Expire an auth key. """
        self.enabled = False
        self.expired_at = int(time())

    def _do_sync_config(self):
        print("auth key: do_sync_config")
        tosave = {
            "source": self.source,
            "label": self.label,
            "description": self.description,
            "auth_data": self.auth_data,
            "enabled": self.enabled,
            "roles": list(self.roles),
            "auth_id": self.auth_id,
            "created_by": self.created_by,
            "created_by_type": self.created_by_type,
            "last_access_at": self.last_access_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "item_permissions": self.item_permissions,
            "saved_permissions": self.item_permissions
        }
        self._Parent._Configs.set("rbac_authkeys", sha256_compact(self.auth_id),
                                  data_pickle(tosave, encoder="msgpack_base64", local=True),
                                  ignore_case=True)

    def __str__(self):
        return f"AuthKeys - {self.label}"
