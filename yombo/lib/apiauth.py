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

# from yombo.ext.expiringdict import ExpiringDict

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import random_string, random_int, sleep, bytes_to_unicode
from yombo.utils.datatypes import coerce_value
# from yombo.utils.decorators import memoize_ttl

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
        yield self.load_sessions()
        self._periodic_save_apiauths = LoopingCall(self.save_apiauths)
        self._periodic_save_apiauths.start(random_int(60*60*4, .2))  # Every four-ish. Save api auth records.

    @inlineCallbacks
    def _unload_(self, **kwargs):
        yield self.save_apiauths(force=True)

    @inlineCallbacks
    def load_sessions(self):
        api_auths = yield self._LocalDB.get_api_auth()
        for auth in api_auths:
            # print("apiauth: auth: %s" % auth)
            self.active_api_auth[auth['auth_id']] = Auth(self, auth, source='database')

    def get(self, key):
        """
        Get an API Auth key by key id (prefered) or by label.
        :param key:
        :return:
        """
        # print("Auth key search: %s" % key)
        if key in self.active_api_auth:
            # print("Auth key search - found by keyid")
            return self.active_api_auth[key]
        else:
            for auth_id, auth in self.active_api_auth.items():
                # print("Checking auth: %s = %s" % (auth.label, key))
                if auth.label.lower() == key.lower():
                    return auth

        # print("Auth key search - not FOUND!")
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
            # print("request: %s" % request)
            auth_id = bytes_to_unicode(request.getHeader(b'x-api-auth'))
            if auth_id is None:
                try:
                    auth_id = request.args.get('_api_auth')[0]
                except:
                    auth_id = None
        if auth_id is None:
            raise YomboWarning("x-api-auth header nor query string is found.")
        if self.validate_auth_id(auth_id) is False:
            raise YomboWarning("api auth key has invalid characters.")

        try:
            return self.get(auth_id)
        except KeyError as e:
            raise YomboWarning("api auth isn't found")

    @inlineCallbacks
    def create(self, label, description=None, permissions=None, auth_data=None, is_valid=None):
        """
        Creates a new session.
        :return:
        """
        # print("about to create new apiauth")
        # all_auths = yield self.get_all()
        for auth_id, auth in self.active_api_auth:
            if auth['label'].lower() == label.lower():
                raise YomboWarning("Already exists.")

        if description is None:
            description = "No details."
        if permissions is None:
            permissions = {}
        if auth_data is None:
            auth_data = {}
        if is_valid not in (True, False):
            is_valid = True

        auth_id = random_string(length=randint(50, 55))

        data = {
            'auth_id': auth_id,
            'label': label,
            'description': description,
            'permissions': permissions,
            'auth_data': auth_data,
            'is_valid': is_valid,
        }

        self.active_api_auth[auth_id] = Auth(self, data)
        return self.active_api_auth[auth_id]

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
            if session.is_dirty >= 200 or force is True:
                yield session.save()


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

    def __init__(self, apiauth, record, source=None):
        self._Parent = apiauth
        self.is_valid = True
        if source == 'database':
            self.in_db = True
            self.is_dirty = 0
        else:
            self.in_db = False
            self.is_dirty = 1

        self.session_type = "apiauth"

        self.label = ""
        self.description = ""
        self.auth_id = record['auth_id']
        self.last_access = 1
        self.created_at = int(time())
        self.updated_at = int(time())
        self.auth_data = {}
        self.permissions = {}
        self.update_attributes(record, True)

    def update_attributes(self, record=None, stay_clean=None):
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
        if 'permissions' in record:
            self.permissions = record['permissions']
        if 'last_access' in record:
            self.last_access = record['last_access']
        if 'created_at' in record:
            self.created_at = record['created_at']
        if 'updated_at' in record:
            self.updated_at = record['updated_at']
        if 'auth_data' in record:
            if isinstance(record['auth_data'], dict):
                self.auth_data.update(record['auth_data'])
        if 'yomboapi_session' not in self.auth_data:
            self.auth_data['yombo_session'] = None
        if stay_clean is not True:
            self.save()

    @property
    def user_id(self) -> str:
        return "apiauth:%s..." % self.auth_id[20:]

    def get(self, key, default="BRFEqgdgLgI0I8QM2Em2nWeJGEuY71TTo7H08uuT"):
        if key in self.auth_data:
            self.last_access = int(time())
            return self.auth_data[key]
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
            self.auth_data[key] = val
            self.is_dirty = 200
            return val
        raise KeyError("Session doesn't have key: %s" % key)

    def delete(self, key):
        if key in self:
            self.last_access = int(time())
            try:
                del self.auth_data[key]
                self.auth_data['updated_at'] = int(time())
                self.is_dirty = 200
            except Exception as e:
                pass

    def touch(self):
        self.last_access = int(time())
        self.is_dirty += 1

    def check_valid(self):
        if self.is_valid is False:
            return False

        if self.auth_id is None:
            self.expire_session()
            return False

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
    def save(self, timeout=None):
        if timeout is None:
            timeout = 0.05
        if self.in_db:
            if timeout > 0:
                reactor.callLater(timeout, self._Parent._LocalDB.update_api_auth, self)
            else:
                yield self._Parent._LocalDB.update_api_auth(self)
        else:
            if timeout > 0:
                reactor.callLater(timeout, self._Parent._LocalDB.save_api_auth, self)
            else:
                yield self._Parent._LocalDB.save_api_auth(self)
            self.in_db = True
        self.is_dirty = 0

    def __str__(self):
        return "APIAuth - %s" % self.label
