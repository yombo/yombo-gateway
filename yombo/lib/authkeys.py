"""
.. note::

  * End user documentation: `Auth Keys @ User Documentation <https://yombo.net/docs/gateway/web_interface/auth_keys>`_
  * For library documentation, see: `Auth Keys @ Library Documentation <https://yombo.net/docs/libraries/auth_keys>`_

Handles auth key items for the webinterface. Auth keys can be used in place of a username/password
for scripts.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2017-2018 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from time import time
from random import randint

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import AUTH_TYPE_AUTHKEY
from yombo.core.library import YomboLibrary
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.authmixin import AuthMixin
from yombo.mixins.permissionmixin import PermissionMixin
from yombo.mixins.rolesmixin import RolesMixin
from yombo.utils import random_string, random_int, bytes_to_unicode
from yombo.utils.datatypes import coerce_value
from yombo.utils.decorators import cached

logger = get_logger("library.authkey")


class AuthKeys(YomboLibrary):
    """
    Auth Key management.
    """
    active_auth_keys = {}

    def __delitem__(self, key):
        if key in self.active_auth_keys:
            self.active_auth_keys[key].expire()
        return

    def __getitem__(self, key):
        return self.get(key)

    def __len__(self):
        return len(self.active_auth_keys)

    def __setitem__(self, key, value):
        raise YomboWarning("Cannot set a session using this method.")

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
        return list(self.active_auth_keys.keys())

    def items(self):
        """
        Gets a list of tuples representing the commands configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.active_auth_keys.items())

    @inlineCallbacks
    def _start_(self, **kwargs):
        yield self.load_auth_keys()

    def _started_(self, **kwargs):
        self.save_authkeys_loop = LoopingCall(self.save_authkeys)
        self.save_authkeys_loop.start(random_int(60*60*2, .2))  # Every 2-ish hours. Save auth key records.

    @inlineCallbacks
    def _unload_(self, **kwargs):
        yield self.save_authkeys(force=True)

    @inlineCallbacks
    def load_auth_keys(self):
        auth_keys = yield self._LocalDB.get_auth_key()
        for record in auth_keys:
            self.active_auth_keys[record['auth_id']] = AuthKey(self, record, load_source='database')

    def get(self, key):
        """
        Get an Auth Key by key id (preferred) or by label.
        :param key:
        :return:
        """
        # print("authkey get: %s" % key)
        # print("authkey get: self.active_auth_keys %s" % self.active_auth_keys)
        if key in self.active_auth_keys:
            return self.active_auth_keys[key]
        else:
            for auth_id, auth in self.active_auth_keys.items():
                if auth.label.lower() == key.lower():
                    return auth

        raise KeyError("Cannot find auth key: %s" % key)

    def close_session(self, request):
        return

    def get_session_from_request(self, request=None):
        """
        Called by the web interface auth system to check if the provided request
        has an auth key. Can be in the query string as '?_auth_key=key' or '?_api_auth=key'
        or in the header as "x-auth-key: key" or "x-api-auth: key"

        Returns the auth object if found otherwise raises YomboWarning.

        :param request: The web request instance.
        :return: bool
        """
        auth_id = None
        if request is not None:
            auth_id = bytes_to_unicode(request.getHeader(b'x-auth-key'))
            if auth_id is None:
                auth_id = bytes_to_unicode(request.getHeader(b'x-api-auth'))
            if auth_id is None:
                try:
                    auth_id = request.args.get('_auth_key')[0]
                except:
                    try:
                        auth_id = request.args.get('_api_auth')[0]
                    except:
                        pass

        if auth_id is None:
            raise YomboWarning("x-auth-key or x-api-auth header missing, nor _api_auth or _api_query query string is not found.")

        return self.get_session_by_id(auth_id)

    def get_session_by_id(self, auth_id):
        """
        Gets an Auth Key session based on a auth_id.

        :param auth_id:
        :return:
        """
        if self.validate_auth_id(auth_id) is False:
            raise YomboWarning("auth key has invalid characters.")
        try:
            session = self.get(auth_id)
        except KeyError as e:
            raise YomboWarning("Auth Key isn't found")

        if session.enabled is False:
            raise YomboWarning("Auth Key is no longer enabled.")
        return session

    def create(self, label, description=None, roles=None, auth_data=None, enabled=None, created_by=None):
        """
        Creates a new session.

        :return:
        """
        for auth_id, auth in self.active_auth_keys.items():
            if auth.label.lower() == label.lower():
                raise YomboWarning("Already exists.")

        if description is None:
            description = "No details."
        if auth_data is None:
            auth_data = {}
        if enabled not in (True, False):
            enabled = True
        if roles is None:
            roles = []

        auth_id = random_string(length=randint(45, 50))

        data = {
            'auth_id': auth_id,
            'label': label,
            'description': description,
            'auth_data': auth_data,
            'enabled': enabled,
            'roles': roles,
            'created_by': created_by,
        }

        self.active_auth_keys[auth_id] = AuthKey(self, data)
        return self.active_auth_keys[auth_id]

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
        self.active_auth_keys[new] = auth
        del self.active_auth_keys[old]

    @inlineCallbacks
    def update(self, id=None, data=None):
        """
        Updates an Auth Key

        :param request:
        :return:
        """
        if id is None or data is None:
            return
        try:
            auth_key = yield self.get(id)
        except KeyError:
            raise YomboWarning("Auth Key ID doesn't exist")
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
        if len(auth_id) < 30:
            return False
        if len(auth_id) > 60:
            return False
        return True

    @inlineCallbacks
    def save_authkeys(self, force=None):
        """
        Called by loopingcall and when exiting.

        Saves session information to disk.
        """
        for auth_id, session in self.active_auth_keys.items():
            if session.is_dirty >= 100 or force is True:
                yield session.save(call_later_time=0)


class AuthKey(AuthMixin, PermissionMixin, RolesMixin):
    """
    A single auth key item.
    """
    @property
    def editable(self):
        if self.created_by in (None, 'user'):
            return True
        return False

    def __init__(self, parent, record, load_source=None):
        super().__init__(parent, load_source=load_source)

        # Auth specific attributes
        self.auth_type = AUTH_TYPE_AUTHKEY
        self._auth_id = record['auth_id']
        self.source = "authkey"
        self.source_type = "library"

        # Local attributes
        self.label = ""
        self.description = ""
        self.auth_id = record['auth_id']
        self.last_access_at = 1

        self.update_attributes(record, stay_dirty=(load_source == 'database'))

    def update_attributes(self, record=None, stay_dirty=None):
        """
        Update various attributes
        
        :param record:
        :return: 
        """
        if record is None:
            return
        if 'enabled' in record:
            self.enabled = coerce_value(record['enabled'], 'bool')
        if 'label' in record:
            self.label = record['label']
        if 'label' in record:
            self.label = record['label']
        if 'description' in record:
            self.description = record['description']
        if 'last_access_at' in record:
            self.last_access_at = record['last_access_at']
        if 'created_at' in record:
            self.created_at = record['created_at']
        if 'updated_at' in record:
            self.updated_at = record['updated_at']
        if 'source' in record:
            self.source = record['source']
        if 'auth_data' in record:
            if isinstance(record['auth_data'], dict):
                self.auth_data.update(record['auth_data'])
        if 'item_permissions' in record:
            if isinstance(record['item_permissions'], dict):
                self.item_permissions = record['item_permissions']
        if 'roles' in record:
            if isinstance(record['roles'], list):
                for role_id in record['roles']:
                    try:
                        self.attach_role(role_id, save=False, flush_cache=False)
                    except KeyError:
                        logger.warn("Auth key '%s' was unable to add role_id (don't exist)" % self.label)
        if stay_dirty is not True:
            self.save()

    def rotate(self):
        old_auth_id = self.auth_id
        self.auth_id = random_string(length=randint(50, 55))
        self._Parent.finish_rotate_key(old_auth_id, self.auth_id, self)
        reactor.callLater(1, self._Parent._LocalDB.rotate_auth_key, old_auth_id, self.auth_id)

    @inlineCallbacks
    def save(self, call_later_time=None):
        if call_later_time is None or isinstance(call_later_time, int) is False:
            call_later_time = 0.05
        if self.in_db is True:
            if call_later_time > 0:
                if self.enabled is True:
                    reactor.callLater(call_later_time, self._Parent._LocalDB.update_auth_key, self)
                else:
                    reactor.callLater(call_later_time, self._Parent._LocalDB.delete_auth_key, self.auth_id)
                    if self.auth_id in self._Parent.active_auth_keys:
                        del self._Parent.active_auth_keys[self.auth_id]
            else:
                if self.enabled is True:
                    yield self._Parent._LocalDB.update_auth_key(self)
                else:
                    yield self._Parent._LocalDB.delete_auth_key(self.auth_id)
                    if self.auth_id in self._Parent.active_auth_keys:
                        del self._Parent.active_auth_keys[self.auth_id]
        else:
            if call_later_time > 0:
                reactor.callLater(call_later_time, self._Parent._LocalDB.save_auth_key, self)
            else:
                yield self._Parent._LocalDB.save_auth_key(self)
            self.in_db = True
        self.is_dirty = 0

    def __str__(self):
        return "AuthKeys - %s" % self.label
