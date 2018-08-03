"""
Handles api auth headers for the webinterface.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2017 by Yombo.
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
from yombo.core.library import YomboLibrary
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import random_string, random_int, sleep, bytes_to_unicode
from yombo.utils.datatypes import coerce_value
from yombo.utils.decorators import memoize_ttl

logger = get_logger("library.apiauth")

class APIAuth(YomboLibrary):
    """
    API Key management.
    """
    active_api_auth = {}

    def __delitem__(self, key):
        if key in self.active_api_auth:
            self.active_api_auth[key].expire_session()
        return

    def __getitem__(self, key):
        return self.get(key)

    def __len__(self):
        return len(self.active_api_auth)

    def __setitem__(self, key, value):
        raise YomboWarning("Cannot set a session using this method.")

    def __contains__(self, key):
        try:
            self.get(key)
            return True
        except KeyError as e:
            return False

    def keys(self):
        """
        Returns the keys (command ID's) that are configured.

        :return: A list of command IDs.
        :rtype: list
        """
        return list(self.active_api_auth.keys())

    def items(self):
        """
        Gets a list of tuples representing the commands configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.active_api_auth.items())

    @inlineCallbacks
    def _init_(self, **kwargs):
        self.session_type = "apiauth"
        self.created_items_not_from_db = []
        yield self.load_sessions()

    def _started_(self, **kwargs):
        self._periodic_save_apiauths = LoopingCall(self.save_apiauths)
        self._periodic_save_apiauths.start(random_int(60*60*4, .2))  # Every four-ish. Save api auth records.

    @inlineCallbacks
    def _unload_(self, **kwargs):
        yield self.save_apiauths(force=True)

    @inlineCallbacks
    def load_sessions(self):
        api_auths = yield self._LocalDB.get_api_auth()
        for auth in api_auths:
            self.active_api_auth[auth['auth_id']] = Auth(self, auth, source='database')

    def get(self, key):
        """
        Get an API Auth key by key id (prefered) or by label.
        :param key:
        :return:
        """
        if key in self.active_api_auth:
            return self.active_api_auth[key]
        else:
            for auth_id, auth in self.active_api_auth.items():
                if auth.label.lower() == key.lower():
                    return auth

        raise KeyError("Cannot find api auth key: %s" % key)

    def close_session(self, request):
        return

    def get_session_from_request(self, request=None):
        """
        Called by the web interface auth system to check if the provided request
        has an API key. Can be in the query string as '?_api_auth=key' or in
        the header as "x-api-auth: key"

        Returns the auth object if found otherwise raises YomboWarning.

        :param request: The web request instance.
        :return: bool
        """
        auth_id = None
        if request is not None:
            auth_id = bytes_to_unicode(request.getHeader(b'x-api-auth'))
            if auth_id is None:
                try:
                    auth_id = request.args.get('_api_auth')[0]
                except:
                    auth_id = None
        if auth_id is None:
            raise YomboWarning("x-api-auth header nor _api_query query string is found.")

        return self.get_session_by_id(auth_id)

    def get_session_by_id(self, auth_id):
        """
        Gets an API Auth session based on a auth_id.

        :param auth_id:
        :return:
        """
        if self.validate_auth_id(auth_id) is False:
            raise YomboWarning("api auth key has invalid characters.")
        try:
            session = self.get(auth_id)
        except KeyError as e:
            raise YomboWarning("API Auth key isn't found")

        if session.is_valid is False:
            raise YomboWarning("API Auth key is no longer valid.")
        return session

    def register_active_auth(self, auth_id, source):
        auth = self.get(auth_id)
        auth.register_active_auth(source)

    def create(self, label, description=None, roles=None, auth_data=None, is_valid=None, source=None):
        """
        Creates a new session.

        :return:
        """
        for auth_id, auth in self.active_api_auth.items():
            if auth.label.lower() == label.lower():
                raise YomboWarning("Already exists.")

        if description is None:
            description = "No details."
        if auth_data is None:
            auth_data = {}
        if is_valid not in (True, False):
            is_valid = True
        if roles is None:
            roles = []

        auth_id = random_string(length=randint(45, 50))

        data = {
            'auth_id': auth_id,
            'label': label,
            'description': description,
            'auth_data': auth_data,
            'is_valid': is_valid,
            'roles': roles,
            'source': source,
        }

        self.active_api_auth[auth_id] = Auth(self, data)
        if source not in (None, 'database'):
            self.created_items_not_from_db.append(auth_id)

        return self.active_api_auth[auth_id]

    def delete(self, auth_id):
        """
        Deletes an API Auth key.

        :param auth_id:
        :return:
        """
        auth = self.get(auth_id)
        auth.expire_session()

    def rotate(self, auth_id):
        """
        Rotates an API Auth key for security.

        :return:
        """
        auth = self.get(auth_id)
        auth.rotate()
        return auth

    def finish_rotate_key(self, old, new, auth):
        self.active_api_auth[new] = auth
        del self.active_api_auth[old]

    @inlineCallbacks
    def update(self, id=None, data=None):
        """
        Updates an API Auth key

        :param request:
        :return:
        """
        if id is None or data is None:
            return
        try:
            api_auth = yield self.get(id)
        except KeyError:
            raise YomboWarning("API Auth ID doesn't exist")
        api_auth.update_attributes(data)

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
    def save_apiauths(self, force=None):
        """
        Called by loopingcall and when exiting.

        Saves session information to disk.
        """
        for auth_id, session in self.active_api_auth.items():
            if session.is_dirty >= 100 or force is True:
                yield session.save(call_later_time=0)


class Auth(object):
    """
    A single api auth item.
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
        return self.setitem(data_requested, value)

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

    def __init__(self, apiauth, record, source=None):
        self._Parent = apiauth
        self.is_valid = True
        if source == 'database':
            self.in_db = True
            self.is_dirty = 0
        else:
            self.in_db = False
            self.is_dirty = 1000

        self.session_type = "apiauth"

        self.label = ""
        self.description = ""
        self.auth_id = record['auth_id']
        self.last_access = 1
        self.created_at = int(time())
        self.updated_at = int(time())
        self.auth_data = {}
        self.roles = []
        self.source = None
        self.update_attributes(record, stay_dirty=(source == 'database'))

    def update_attributes(self, record=None, stay_dirty=None):
        """
        Update various attributes
        
        :param record:
        :return: 
        """
        if record is None:
            return
        if 'is_valid' in record:
            self.is_valid = coerce_value(record['is_valid'], 'bool')
        if 'label' in record:
            self.label = record['label']
        if 'label' in record:
            self.label = record['label']
        if 'description' in record:
            self.description = record['description']
        if 'last_access' in record:
            self.last_access = record['last_access']
        if 'created_at' in record:
            self.created_at = record['created_at']
        if 'updated_at' in record:
            self.updated_at = record['updated_at']
        if 'source' in record:
            self.source = record['source']
        if 'auth_data' in record:
            if isinstance(record['auth_data'], dict):
                self.auth_data.update(record['auth_data'])
        if 'roles' in record:
            if isinstance(record['roles'], list):
                self.roles = record['roles']
        if stay_dirty is not True:
            self.save()

    @property
    def user_id(self) -> str:
        return self.auth_id

    def register_active_auth(self, source):
        self.source = source
        self._Parent.created_items_not_from_db.append(self.auth_id)

    def attach_role(self, machine_label):
        if isinstance(machine_label, str) is False:
            logger.warn("Cannot attach role, must be a string.")
            return
        if machine_label not in self.roles:
            self.roles.append(machine_label)
        self.is_dirty += 1

    def unattach_role(self, machine_label):
        if isinstance(machine_label, str) is False:
            logger.warn("Cannot remove role, must be a string.")
            return
        if machine_label in self.roles:
            self.roles.remove(machine_label)
        self.is_dirty += 1

    def set_roles(self, roles):
        if isinstance(roles, list) is False:
            return
        self.roles = roles
        self.is_dirty += 1

    def get(self, key, default="BRFEqgdgLgI0I8QM2Em2nWeJGEuY71TTo7H08uuT"):
        if key in self.auth_data:
            self.last_access = int(time())
            return self.auth_data[key]
        if default != "BRFEqgdgLgI0I8QM2Em2nWeJGEuY71TTo7H08uuT":
            return default
        else:
            # return None
            raise KeyError("Cannot find session key: %s" % key)

    def setitem(self, key, val):
        if key == 'is_valid':
            raise YomboWarning("Use expire_session() method to expire this session.")
        if key == 'id' or key == 'session_id':
            raise YomboWarning("Cannot change the ID of this session.")
        if key not in ('last_access', 'created_at', 'updated_at'):
            self.updated_at = int(time())
            self.auth_data[key] = val
            self.is_dirty = 200
            return val
        raise KeyError("Session doesn't have key: %s" % key)

    def delete(self, key):
        if key in self.auth_data:
            self.last_access = int(time())
            try:
                del self.auth_data[key]
                self.updated_at = int(time())
                self.is_dirty = 200
            except Exception as e:
                pass

    def touch(self):
        self.last_access = int(time())
        self.is_dirty += 1

    @memoize_ttl(60)
    def has_access(self, path, action, raise_error=None):
        """
        Check if api auth has access  to a resource / access_type combination.

        :param access_type:
        :param resource:
        :return:
        """
        return self._Parent._Users.has_access(self.roles, path, action, raise_error)

    def check_valid(self):
        if self.is_valid is False:
            return False

        if self.auth_id is None:
            self.expire_session()
            return False
        return True

    def rotate(self):
        old_auth_id = self.auth_id
        self.auth_id = random_string(length=randint(50, 55))
        self._Parent.finish_rotate_key(old_auth_id, self.auth_id, self)
        reactor.callLater(1, self._Parent._LocalDB.rotate_api_auth, old_auth_id, self.auth_id)

    def enable(self):
        self.is_valid = True
        self.save()

    def expire_session(self):
        self.is_valid = False
        self.save()

    @inlineCallbacks
    def save(self, call_later_time=None):
        if call_later_time is None or isinstance(call_later_time, int) is False:
            call_later_time = 0.05
        if self.in_db is True:
            if call_later_time > 0:
                if self.is_valid is True:
                    reactor.callLater(call_later_time, self._Parent._LocalDB.update_api_auth, self)
                else:
                    reactor.callLater(call_later_time, self._Parent._LocalDB.delete_api_auth, self.auth_id)
                    if self.auth_id in self._Parent.active_api_auth:
                        del self._Parent.active_api_auth[self.auth_id]
            else:
                if self.is_valid is True:
                    yield self._Parent._LocalDB.update_api_auth(self)
                else:
                    yield self._Parent._LocalDB.delete_api_auth(self.auth_id)
                    if self.auth_id in self._Parent.active_api_auth:
                        del self._Parent.active_api_auth[self.auth_id]
        else:
            if call_later_time > 0:
                reactor.callLater(call_later_time, self._Parent._LocalDB.save_api_auth, self)
            else:
                yield self._Parent._LocalDB.save_api_auth(self)
            self.in_db = True
        self.is_dirty = 0

    def __str__(self):
        return "APIAuth - %s" % self.label
