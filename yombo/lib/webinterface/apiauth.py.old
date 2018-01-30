"""
Handles api auth headers for the webinterface.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import os
from time import time
from random import randint
import hashlib

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, Deferred

# from yombo.ext.expiringdict import ExpiringDict

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.utils.dictobject import DictObject
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import random_string, random_int, sleep, bytes_to_unicode
from yombo.utils.datatypes import coerce_value
# from yombo.utils.decorators import memoize_ttl

logger = get_logger("library.webinterface.apiauth")

class ApiAuths(YomboLibrary):
    """
    Session management.
    """
    def __init__(self, loader):  # we do some simulation of a Yombo Library...
        self.loader = loader
        self._FullName = "yombo.gateway.lib.webinterface.api_auth"
        self._Configs = self.loader.loadedLibraries['configuration']
        self._LocalDB = self.loader.loadedLibraries['localdb']
        self._Gateways = self.loader.loadedLibraries['gateways']
        self.gateway_id = self._Configs.get('core', 'gwid', 'local', False)
        self.active_api_auth = {}
        self.session_type = "apiauth"
        # self.active_api_auth_cache = ExpiringDict(200, 5)  # keep 200 entries, for at most 1 second...???

    def __delitem__(self, key):
        if key in self.active_api_auth:
            self.active_api_auth[key].expire_session()
        return

    def __getitem__(self, key):
        if key in self.active_api_auth:
            return self.active_api_auth[key]
        else:
            raise KeyError("Cannot find api auth key 2: %s" % key)

    def __len__(self):
        return len(self.active_api_auth)

    def __setitem__(self, key, value):
        raise YomboWarning("Cannot set a session using this method.")

    def __contains__(self, key):
        if key in self.active_api_auth:
            return True
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

    # @inlineCallbacks
    def init(self):
        self._periodic_clean_sessions = LoopingCall(self.clean_sessions)
        self._periodic_clean_sessions.start(random_int(60*60*2, .7))  # Every 60-ish seconds. Save to disk, or remove from memory.

    def _unload_(self):
        self.unload_deferred = Deferred()
        self.clean_sessions(self.unload_deferred)
        return self.unload_deferred

    def close(self, request):
        api_auth = self.get(request)
        api_auth.expire_session()

    @inlineCallbacks
    def get_all(self):
        """
        Returns the api auths from DB.

        :return: A list of command IDs.
        :rtype: list
        """
        yield self.clean_sessions(True)
        api_auths = yield self._LocalDB.get_api_auth()
        return api_auths

    @inlineCallbacks
    def get(self, request=None, api_auth_id=None):
        """
        Checks the request for an x-api-auth header and then tries to validate it.

        Returns True if everything is good, otherwise raises YomboWarning with
        status reason.

        :param request: The request instance.
        :return: bool
        """
        if api_auth_id is None and request is not None:
            # print("request: %s" % request)
            api_auth_id = bytes_to_unicode(request.getHeader(b'x-api-auth'))
            if api_auth_id is None:
                try:
                    api_auth_id = request.args.get('_api_auth')[0]
                except:
                    api_auth_id = None
        if api_auth_id is None:
            raise YomboWarning("x-api-auth header is missing or blank.")
        if self.validate_api_auth_id(api_auth_id) is False:
            raise YomboWarning("x-api-auth header has invalid characters.")

        if api_auth_id in self.active_api_auth:
            if self.active_api_auth[api_auth_id].is_valid is True:
                return self.active_api_auth[api_auth_id]
            else:
                raise YomboWarning("x-api-auth header is no longer valid.")
        else:
            logger.debug("has_session is looking in database for session...")
            try:
                db_api_auth = yield self._LocalDB.get_api_auth(api_auth_id)
            except Exception as e:
                raise YomboWarning("x-api-auth is not valid")
            # logger.debug("has_session - found in DB! {db_session}", db_session=db_session)
            self.active_api_auth[api_auth_id] = ApiAuth(self, db_api_auth, source='database')
            return self.active_api_auth[api_auth_id]
        raise YomboWarning("x-api-auth header is invalid, other reasons.")

    def create(self, request=None, data=None):
        """
        Creates a new session.
        :param request:
        :param make_active: If True or None (default), then store sesion in memory.
        :return:
        """
        if data is None:
            data = {}
        if 'gateway_id' not in data or data['gateway_id'] is None:
            data['gateway_id'] = self.gateway_id
        if 'api_auth_id' not in data or data['api_auth_id'] is None:
            data['api_auth_id'] = random_string(length=randint(50, 55))
        if 'api_auth_data' not in data:
            data['api_auth_data'] = {}

        self.active_api_auth[data['api_auth_id']] = ApiAuth(self, data)
        return self.active_api_auth[data['api_auth_id']]

    @inlineCallbacks
    def update(self, id=None, data=None):
        """
        Updates an API Auth key

        :param request:
        :return:
        """
        if id is None or data is None:
            return
        api_auth = yield self.get(api_auth_id=id)
        if api_auth is None or api_auth is False:
            raise YomboWarning("API Auth ID doesn't exist")
        api_auth.update_attributes(data)

    def validate_api_auth_id(self, api_auth_id):
        """
        Validate the session id to make sure it's reasonable.
        :param api_auth_id: 
        :return: 
        """
        if api_auth_id == "LOGOFF":  # lets not raise an error.
            return True
        if api_auth_id.isalnum() is False:
            return False
        if len(api_auth_id) < 30:
            return False
        if len(api_auth_id) > 60:
            return False
        return True

    @inlineCallbacks
    def clean_sessions(self, close_deferred=None):
        """
        Called by loopingcall.

        Cleanup the stored sessions
        """
        for api_auth_id in list(self.active_api_auth.keys()):
            if self.active_api_auth[api_auth_id].check_valid() is False or self.active_api_auth[api_auth_id].is_valid is False:
                logger.debug("Removing invalid api auth: %s" % api_auth_id)
                del self.active_api_auth[api_auth_id]
                yield self._LocalDB.delete_api_auth(api_auth_id)

        for api_auth_id in list(self.active_api_auth):
            session = self.active_api_auth[api_auth_id]
            if session.is_dirty >= 200 or close_deferred is not None or session.last_access < int(time() - (60*5)):
                if session.in_db:
                    logger.debug("updating old db api auth record: {id}", id=api_auth_id)
                    yield self._LocalDB.update_api_auth(session)
                else:
                    logger.debug("creating new db api auth record: {id}", id=api_auth_id)
                    yield self._LocalDB.save_api_auth(session)
                    session.in_db = True
                session.is_dirty = 0
                if session.last_access < int(time() - (60*60*3)):   # delete session from memory after 3 hours
                    logger.debug("Deleting session from memory: {api_auth_id}", api_auth_id=api_auth_id)
                    del self.active_api_auth[api_auth_id]

        # print("api auth clean sessions...: %s" % close_deferred)
        if close_deferred is not None and close_deferred is not True and close_deferred is not False:
            yield sleep(0.1)
            close_deferred.callback(1)

class ApiAuth(object):
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
        return self.api_auth_data.keys()

    def __init__(self, apiauth, record, source=None):
        self._ApiAuth = apiauth
        self.is_valid = True
        if source == 'database':
            self.in_db = True
            self.is_dirty = 0
        else:
            self.in_db = False
            self.is_dirty = 1

        self.label = ""
        self.description = ""
        self.gateway_id = record['gateway_id']
        self.api_auth_id = record['api_auth_id']
        self.last_access = 1
        self.created_at = int(time())
        self.updated_at = int(time())
        self.api_auth_data = {}
        self.permissions = {}
        self.update_attributes(record, True)

    def update_attributes(self, record=None, called_from_init=None):
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
        if 'api_auth_data' in record:
            if isinstance(record['api_auth_data'], dict):
                self.api_auth_data.update(record['api_auth_data'])
        if called_from_init is not True:
            self.is_dirty = 2000
    #
    # def get(self, key, default="BRFEqgdgLgI0I8QM2Em2nWeJGEuY71TTo7H08uuT"):
    #     if key in self.api_auth_data:
    #         self.last_access = int(time())
    #         return self.api_auth_data[key]
    #     if default != "BRFEqgdgLgI0I8QM2Em2nWeJGEuY71TTo7H08uuT":
    #         return default
    #     else:
    #         # return None
    #         raise KeyError("Cannot find api auth key: %s" % key)
    #
    # def set(self, key, val):
    #     if key == 'is_valid':
    #         raise YomboWarning("Use expire_session() method to expire this session.")
    #     if key == 'api_auth_id':
    #         raise YomboWarning("Cannot change the ID of this session.")
    #     if key not in ('last_access', 'created_at', 'updated_at'):
    #         self.updated_at = int(time())
    #         self.api_auth_data[key] = val
    #         self.is_dirty = 200
    #         return val
    #     raise KeyError("ApiAuth doesn't have key: %s" % key)


    @property
    def user_id(self) -> str:
        return "apiauth:%s..." % self.api_auth_id[20:]

    def delete(self, key):
        if key in self:
            self.last_access = int(time())
            try:
                del self.api_auth_data[key]
                self.api_auth_data['updated_at'] = int(time())
                self.is_dirty = 200
            except:
                pass

    def touch(self):
        self.last_access = int(time())
        self.is_dirty += 1

    def check_valid(self):
        if self.is_valid is False:
            return False

        if self.api_auth_id is None:
            self.expire_session()
            return False

    def expire_session(self):
        self.is_valid = False
        self.is_dirty = 20000
