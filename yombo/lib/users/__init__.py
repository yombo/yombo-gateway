# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Manages users within the gateway. All users are loaded on startup.

.. note::

  * End user documentation: `User permissions @ User Documentation <https://yombo.net/docs/gateway/web_interface/user_permissions>`_
  * End user documentation: `Roles @ User Documentation <https://yombo.net/docs/gateway/web_interface/roles>`_
  * For library documentation, see: `Users @ Library Documentation <https://yombo.net/docs/libraries/users>`_

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from copy import deepcopy
import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import AUTH_TYPE_AUTHKEY, AUTH_TYPE_WEBSESSION, AUTH_TYPE_USER
from yombo.core.exceptions import YomboWarning, YomboNoAccess
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.lib.authkeys import Auth as AuthKeyAuth
from yombo.lib.websessions import Auth as WebSessionAuth
from yombo.lib.users.role import Role
from yombo.lib.users.user import User
from yombo.lib.users.systemauth import SystemAuth
from yombo.constants.users import *
from yombo.utils import global_invoke_all, data_unpickle, format_user_id_logging, sha256_compact

logger = get_logger('library.users')


class Users(YomboLibrary):
    """
    Maintains a list of users and what they can do.
    """
    def __contains__(self, user_requested):
        """
        Checks to if a provided user exists.

            >>> if 'mitch@example' in self._Users:
            >>>    print("mitch@example.com is able to login.")

        :raises YomboWarning: Raised when request is malformed.
        :param user_requested: The user key to search for.
        :type user_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(user_requested)
            return True
        except Exception as e:
            return False

    def __getitem__(self, user_requested):
        """
        Attempts to find the user requested.

            >>> user_mitch = self._Users['mitch@example.com']

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param user_requested: The user key to search for.
        :type user_requested: string
        :return: The value assigned to the user.
        :rtype: mixed
        """
        return self.get(user_requested)

    def __setitem__(self, user_requested, value):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, user_requested):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter users. """
        return self.users.__iter__()

    def __len__(self):
        """
        Returns an int of the number of users defined.

        :return: The number of users defined.
        :rtype: int
        """
        return len(self.users)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo users library"

    def keys(self, gateway_id=None):
        """
        Returns the keys of the users that are defined.

        :return: A list of users defined.
        :rtype: list
        """
        return self.users.keys()

    def items(self, gateway_id=None):
        """
        Gets a list of tuples representing the users defined.

        :return: A list of tuples.
        :rtype: list
        """
        return self.users.items()

    def values(self):
        """
        Gets a list of user values
        :return: list
        """
        return self.users.values()

    def _init_(self, **kwargs):
        self.roles: dict = {}
        self.users: dict = {}
        self.gateway_id = self._Configs.get('core', 'gwid', 'local', False)
        self.owner_id = self._Configs.get('core', 'owner_id', None, False)
        self.owner_user = None
        self.auth_platforms = deepcopy(AUTH_PLATFORMS)  # Possible platforms

        # make sure there's defaults as needed.
        for auth, data in self.auth_platforms.items():
            if 'items_callback' not in data:
                data['items_callback'] = None
            if 'item_callback' not in data:
                data['item_callback'] = None
            if 'item_id_callback' not in data:
                data['item_id_callback'] = None
            if 'item_label_callback' not in data:
                data['item_label_callback'] = None

        # Itemized platforms allow specific access to one item within a platfrom. such as a device or automation
        self.itemized_auth_platforms = deepcopy(ITEMIZED_AUTH_PLATFORMS)
        self.system_user = SystemAuth()
        self.cache = self._Cache.ttl(name='lib.users.cache', ttl=86400, tags=('role', 'user'))
        self.get_access_cache = self._Cache.ttl(name='lib.users.get_access_cache', ttl=86400, tags=('role', 'user'))
        self.get_access_permissions_cache = self._Cache.ttl(name='lib.users.get_access_permissions_cache', ttl=86400, tags=('role', 'user'))
        self.get_access_access_permissions_cache = self._Cache.ttl(name='lib.users.get_access_permissions_cache', ttl=300, tags=('role', 'user'))
        self.has_access_cache = self._Cache.ttl(name='lib.users.has_access_cache', ttl=86400, tags=('role', 'user'))

    @inlineCallbacks
    def _start_(self, **kwargs):
        """
        Calls the _roles_ hook to all components to add system level roles.
        :param kwargs:
        :return:
        """
        self.load_roles()
        yield self.load_users()
        if self.owner_id is not None:
            self.owner_user = self.get(self.owner_id)
            self.owner_user.attach_role('admin')

        results = yield global_invoke_all('_auth_platforms_', called_by=self)
        logger.debug("_auth_platforms_ results: {results}", results=results)
        for component, platforms in results.items():
            for machine_label, platform_data in platforms.items():
                if 'actions' not in platform_data:
                    logger.warn("Unable to add auth platform, actions is missing: {data}", data=platform_data)
                    continue
                if 'items_callback' not in platform_data:
                    platform_data['items_callback'] = None
                if 'item_callback' not in platform_data:
                    platform_data['item_callback'] = None
                if 'item_id_callback' not in platform_data:
                    platform_data['item_id_callback'] = None
                if 'item_label_callback' not in platform_data:
                    platform_data['item_label_callback'] = None
                self.auth_platforms[machine_label] = platform_data

        results = yield global_invoke_all('_roles_', called_by=self)
        logger.debug("_roles_ results: {results}", results=results)
        for component, roles in results.items():
            for machine_label, role_data in roles.items():
                if 'label' not in role_data:
                    role_data['label'] = machine_label
                if 'description' not in role_data:
                    role_data['description'] = role_data['label']
                if 'permissions' not in role_data:
                    role_data['permissions'] = []
                else:
                    if isinstance(role_data['permissions'], list) is False:
                        logger.warn("Cannot add role, permissions must be a list. Role: {machine_label}",
                                    machine_label=machine_label)
                        continue
                role_data['machine_label'] = machine_label
                entity_type = component._Entity_type
                if entity_type == "yombo_module":
                    source = "module"
                else:
                    source = "system"
                self.add_role(role_data, source=source, flush_cache=False, debug=True)

    def load_roles(self):
        for machine_label, role_data in SYSTEM_ROLES.items():
            role_data['machine_label'] = machine_label
            self.add_role(role_data, source="system", flush_cache=False)
        self._Cache.flush(tags=('user', 'role'))

        rbac_roles = self._Configs.get('rbac_roles', '*', {}, False, ignore_case=True)
        for role_id, role_data_raw in rbac_roles.items():
            role_data = data_unpickle(role_data_raw, encoder='msgpack_base64')
            self.add_role(role_data, source="user", flush_cache=False)
        self._Cache.flush(tags=('user', 'role'))

    @inlineCallbacks
    def load_users(self):
        db_users = yield self._LocalDB.get_users()

        for user in db_users:
            self.users[user.email] = User(self, user.__dict__, flush_cache=False)

    @inlineCallbacks
    def api_search_user(self, requested_user, session=None):
        """
        Search for user using the Yombo API. Must supply a user_id or user email address. If found returns
        a dictionary with the keys of: 'id', 'name', and 'email'.

        :param requested_user: The email address to search for.
        :param session: Session to use, if available.
        :return:
        """
        try:
            search_results = yield self._YomboAPI.request('GET',
                                                          '/v1/user/%s' % requested_user,
                                                          None,
                                                          session)
        except YomboWarning as e:
            raise YomboWarning("User not found: %s" % requested_user)
        return search_results['data']

    @inlineCallbacks
    def add_user(self, requested_user_id, session=None, flush_cache=None):
        """
        Adds a new user to the system using the user's id. The user id  can be found using
        :py:meth:`api_search_user() <api_search_user>`.

        This function will make a call the the Yombo API to add the user, if successful, adds
        the user to memory as well. The database isn't updated, it will be updated on next reboot
        when it pulls configs from the servers.

        :param requested_user:
        :return:
        """
        data = {
            'user_id': requested_user_id,
        }
        try:
            add_results = yield self._YomboAPI.request('POST',
                                                       '/v1/gateway/%s/user' % self.gateway_id,
                                                       data,
                                                       session)
        except YomboWarning as e:
            raise YomboWarning("Could not add user to gateway: %s" % e.message[0],
                               html_message="Could not add user to gateway: %s" % e.html_message,
                               details=e.details)

        add_results['data']['id'] = add_results['data']['user_id']
        self.users[add_results['data']['email']] = User(self, add_results['data'])
        if flush_cache in (None, True):
            self._Cache.flush('user')

        # self.users[add_results['data']['email']].sync_user_to_db()

    @inlineCallbacks
    def remove_user(self, requested_user_id, session=None, flush_cache=None):
        """
        Adds a new user to the system using the user's id. The user id  can be found using
        :py:meth:`api_search_user() <api_search_user>`.

        This function will make a call the the Yombo API to add the user, if successful, adds
        the user to memory as well. The database isn't updated, it will be updated on next reboot
        when it pulls configs from the servers.

        :param requested_user:
        :return:
        """
        try:
            add_results = yield self._YomboAPI.request('DELETE',
                                                       '/v1/gateway/%s/user/%s' % (self.gateway_id, requested_user_id),
                                                       session=session)
        except YomboWarning as e:
            raise YomboWarning("Could not remove user from gateway: %s" % e.message[0],
                               html_message="Could not remove user from gateway: %s" % e.html_message,
                               details=e.details)

        user = self.get(requested_user_id)
        if user.email in self.users:
            del self.users[user.email]
        if flush_cache in (None, True):
            self._Cache.flush('user')

    def add_role(self, data, source=None, no_save=None, flush_cache=None, debug=None):
        """
        Add a new possible role to the system.

        :param data:
        :return:
        """
        if source not in ('system', 'user', 'module'):
            raise YomboWarning("Add_role requires a source to be: system, user, or module.")

        machine_label = data['machine_label']
        if machine_label in self.roles:
            raise YomboWarning("Role already exists.")
        if 'label' not in data:
            data['label'] = machine_label
        if 'role_id' not in data:
            data['role_id'] = sha256_compact(machine_label)
        if 'description' not in data:
            data['description'] = machine_label
        if 'permissions' not in data:
            data['permissions'] = []
        if 'saved_permissions' not in data:
            data['saved_permissions'] = None
        self.roles[data['role_id']] = Role(self,
                                           machine_label=machine_label,
                                           label=data['label'],
                                           description=data['description'],
                                           source=source,
                                           role_id=data['role_id'],
                                           permissions=data['permissions'],
                                           saved_permissions=data['saved_permissions'],
                                           flush_cache=flush_cache
                                           )
        if debug is True:
            print("add_role: role_id: %s" % data['role_id'])
            print("add_role: role: %s" % self.roles[data['role_id']])
        if flush_cache in (None, True):
            self._Cache.flush('role')
        return self.roles[data['role_id']]

    def list_role_members(self, requested_role):
        """
        List all users belonging to a role.

        :param requested_role:
        :return:
        """
        role = self.get_role(requested_role)
        return {
            'users': self.list_role_users(role),
            'auth_keys': self.list_role_auth_keys(role),
        }

    def list_role_users(self, requested_role):
        """
        List all users belonging to a role.

        :param requested_role:
        :return:
        """
        role_users = []
        the_role = self.get_role(requested_role)

        role_machine_label = the_role.label
        for email, the_user in self.users.items():
            if role_machine_label in user.roles:
                role_users.append(the_user)
        return role_users

    def list_role_auth_keys(self, requested_role):
        """
        List all users belonging to a role.

        :param requested_role:
        :return:
        """
        role_authkeys = []
        the_role = self.get_role(requested_role)

        for auth_id, auth_key in self._AuthKeys.items():
            if the_role.machine_label in auth_key.roles:
                role_authkeys.append(auth_key)
        return role_authkeys

    def list_roles_by_user(self):
        """
        All roles and which users belong to them. This takes a bit as it has to iterate all users.

        This is different than list_role_users in that this gets all the roles and the members for each role.

        :return:
        """
        if 'roles_by_user' in self.cache:
            return self.cache['roles_by_user']
        roles = {}
        for email, user in self.users.items():
            for the_role in user.roles:
                if the_role not in roles:
                    roles[the_role] = []
                roles[the_role].append(user)
        self.cache['roles_by_user'] = roles
        return roles

    def get_all_item_permissions(self, requested_platform, requested_item, source_type):
        """
        List all users and their permissions for a specific platform

        :return:
        """
        requested_platform = requested_platform.lower()
        if requested_platform not in self.itemized_auth_platforms:
            return {}

        platform_item, platform_item_id, platform_item_label, platform_actions = \
            self.get_platform_item(requested_platform, requested_item)

        # permissions = {}
        # for email, the_user in self.users.items():
        #     for access in ('allow',
        #     if platform_item_label in the_user.item_permissions[requested_platform]:
        #         permissions[email] = the_user.item_permissions[platform][platform_item_label]
        # return permissions

    def get_platform_item(self, platform, item=None):
        """
        Gets a platform item (device, automation, scene, etc). If an item is provided, it will
        search for that specific item.

        :param platform:
        :param item:
        :return:
        """
        if platform == AUTH_PLATFORM_ATOM:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_ATOM]['actions']
            platform_items = self._Atoms.atoms
        elif platform == AUTH_PLATFORM_AUTHKEY:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_AUTHKEY]['actions']
            platform_items = self._AuthKeys.active_auth_keys
        elif platform == AUTH_PLATFORM_AUTOMATION:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_AUTOMATION]['actions']
            platform_items = self._Automation.rules
        elif platform == AUTH_PLATFORM_DEVICE:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_DEVICE]['actions']
            platform_items = self._Devices.devices
        elif platform == AUTH_PLATFORM_DEVICE_COMMAND:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_DEVICE_COMMAND]['actions']
            platform_items = self._Devices.device_commands
        elif platform == AUTH_PLATFORM_EVENTS:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_EVENTS]['actions']
            platform_items = {}
        elif platform == AUTH_PLATFORM_GATEWAY:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_GATEWAY]['actions']
            platform_items = self._Gateways.gateways
        elif platform == AUTH_PLATFORM_LOCATION:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_LOCATION]['actions']
            platform_items = self._Locations.locations
        elif platform == AUTH_PLATFORM_MODULE:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_MODULE]['actions']
            platform_items = self._Modules.modules
        elif platform == AUTH_PLATFORM_NOTIFICATION:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_NOTIFICATION]['actions']
            platform_items = self._Notifications.notifications
        elif platform == AUTH_PLATFORM_PANEL:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_PANEL]['actions']
            platform_items = {}
        elif platform == AUTH_PLATFORM_ROLE:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_ROLE]['actions']
            platform_items = self._Users.roles
        elif platform == AUTH_PLATFORM_SCENE:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_SCENE]['actions']
            platform_items = self._Scenes.scenes
        elif platform == AUTH_PLATFORM_STATE:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_STATE]['actions']
            platform_items = self._States.states
        elif platform == AUTH_PLATFORM_STATISTIC:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_STATISTIC]['actions']
            platform_items = {}
        elif platform == AUTH_PLATFORM_SYSTEM_SETTING:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_SYSTEM_SETTING]['actions']
            platform_items = {}
        elif platform == AUTH_PLATFORM_SYSTEM_OPTION:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_SYSTEM_OPTION]['actions']
            platform_items = {}
        elif platform == AUTH_PLATFORM_USER:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_USER]['actions']
            platform_items = self._Users.users
        elif platform == AUTH_PLATFORM_WEBLOGS:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_WEBLOGS]['actions']
            platform_items = {}
        elif platform == AUTH_PLATFORM_WILDCARD:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_WILDCARD]['actions']
            platform_items = {}
        else:
            platform_actions = ()
            platform_items = {}
            if platform in self.auth_platforms:
                platform_actions = self.auth_platforms[platform]['actions']
                if self.auth_platforms[platform]['items_callback'] is not None:
                    platform_items = self.auth_platforms[platform]['items_callback']()
        if item in ('*', None):
            return platform_items, '*', '*', platform_actions

        if platform == AUTH_PLATFORM_ATOM:
            platform_item = self._Atoms.get(item, full=True)
            platform_item_id = item
            platform_item_label = item
        elif platform == AUTH_PLATFORM_AUTHKEY:
            platform_item = self._AuthKeys.get(item)
            platform_item_id = platform_item.auth_id
            platform_item_label = platform_item.label
        elif platform == AUTH_PLATFORM_AUTOMATION:
            platform_item = self._Automation.get(item)
            platform_item_id = item
            platform_item_label = platform_item.machine_label
        elif platform == AUTH_PLATFORM_DEVICE:
            platform_item = self._Devices.get(item)
            platform_item_id = platform_item.device_id
            platform_item_label = platform_item.machine_label
        elif platform == AUTH_PLATFORM_DEVICE_COMMAND:
            platform_item = self._Devices.device_commands[item]
            platform_item_id = item
            platform_item_label = item
        elif platform == AUTH_PLATFORM_EVENTS:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        elif platform == AUTH_PLATFORM_GATEWAY:
            platform_item = self._Gateways.get(item)
            platform_item_id = platform_item.gateway_id
            platform_item_label = platform_item.label
        elif platform == AUTH_PLATFORM_LOCATION:
            platform_item = self._Locations.get(item)
            platform_item_id = platform_item.scene_id
            platform_item_label = platform_item.machine_label
        elif platform == AUTH_PLATFORM_MODULE:
            platform_item = self._Modules.get(item)
            platform_item_id = platform_item._module_id
            platform_item_label = platform_item._machine_label
        elif platform == AUTH_PLATFORM_NOTIFICATION:
            platform_item = self._Notifications.get(item)
            platform_item_id = platform_item.notification_id
            platform_item_label = platform_item.notification_id
        elif platform == AUTH_PLATFORM_PANEL:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        elif platform == AUTH_PLATFORM_ROLE:
            platform_item = self._Users.roles[item]
            platform_item_id = platform_item.role_id
            platform_item_label = platform_item.machine_label
        elif platform == AUTH_PLATFORM_SCENE:
            platform_item = self._Scenes.get(item)
            platform_item_id = platform_item.scene_id
            platform_item_label = platform_item.machine_label
        elif platform == AUTH_PLATFORM_STATE:
            platform_item = self._States.get(item)
            platform_item_id = item
            platform_item_label = item
        elif platform == AUTH_PLATFORM_STATISTIC:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        elif platform == AUTH_PLATFORM_SYSTEM_SETTING:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        elif platform == AUTH_PLATFORM_SYSTEM_OPTION:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        elif platform == AUTH_PLATFORM_USER:
            platform_item = self._Users.get(item)
            platform_item_id = platform_item.user_id
            platform_item_label = platform_item.email
        elif platform == AUTH_PLATFORM_WEBLOGS:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        elif platform == AUTH_PLATFORM_WILDCARD:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        else:
            platform_actions = []
            platform_item = None
            platform_item_id = None
            platform_item_label = None
            if platform in self.auth_platforms:
                platform_actions = self.auth_platforms[platform]['actions']
                if self.auth_platforms[platform]['item_callback'] is not None:
                    platform_item = self.auth_platforms[platform]['item_callback'](item)
                if self.auth_platforms[platform]['item_id_callback'] is not None:
                    platform_item_id = self.auth_platforms[platform]['item_id_callback'](item)
                if self.auth_platforms[platform]['item_label_callback'] is not None:
                    platform_item_label = self.auth_platforms[platform]['item_label_callback'](item)

        return platform_item, platform_item_id, platform_item_label, platform_actions

    def return_access(self, value, auth, platform, item, action, cache_id=None, raise_error=None):
        """
        Used by various auth checker methods. Used to log the event and send the final results (bool).

        :param value:
        :return:
        """
        auth = self.check_auth(auth)

        if cache_id not in self.has_access_cache:
            self.has_access_cache[cache_id] = value

        save_user_id = format_user_id_logging(auth.auth_id, auth.auth_type)
        if value is True:
            self._Events.new('auth', 'accepted', (platform, item, action),
                             user_id=save_user_id, user_type=auth.auth_type)
            return True

        self._Events.new('auth', 'denied', (platform, item, action),
                         user_id=save_user_id, user_type=auth.auth_type)
        if raise_error is not True:
            return False
        raise YomboNoAccess(item_permissions=auth.item_permissions,
                            roles=auth.roles,
                            platform=platform,
                            item=item,
                            action=action)

    def check_auth(self, auth):
        """
        Checks if the auth variable is valid. Accepts a websession, auth key, or user objects. Also accepts
        a string as a last resort to try and determine which of the above item is being referenced.
        :param auth:
        :return:
        """
        if isinstance(auth, WebSessionAuth) or isinstance(auth, AuthKeyAuth) or isinstance(auth, User):
            return auth
        else:
            # now brute force lookup by only user_id or authkey_id
            # print("check auth: auth: %s" % auth)
            for email, user in self.users.items():
                # print("check auth: user_id: %s" % user.user_id)
                if auth == user.user_id:
                    return user
            # print("check auth: auth: %s" % auth)
            for auth_id, auth_key in self._AuthKeys.items():
                # print("check auth: auth_id: %s" % auth_id)
                if auth == auth_id:
                    return auth_key
            for session_id, session in self._WebSessions.items():
                if auth == session_id:
                    return session
        raise YomboWarning("Invalid auth: %s - %s" % (type(auth), auth))

    def check_user_has_access(self, user_id, user_type, platform, item, action, raise_error=None):
        """
        Collects the user information and passes it to has_access().

        :param user_id:
        :param user_type:
        :return:
        """
        logger.debug("check_user_has_access: user_id: {user_id} - user_type: {user_type}", user_id=user_id, user_type=user_type)

        if user_type == 'system':
            return self.return_access(True, self.system_user, platform, item, action)

        if user_id is None:  # soon, this will cause an error!
            logger.warn("Check user has access received NoneType for *user_id*. Future versions will not accept this.")
            return self.return_access(True, self.system_user, platform, item, action)
        elif user_type is None:  # soon, this will cause an error!
            logger.warn(
                "Check user has access received NoneType for *user_id*. Future versions will not accept this.")
            return self.return_access(True, self.system_user, platform, item, action)

        if isinstance(user_id, AuthKeyAuth) or isinstance(user_id, WebSessionAuth) or isinstance(user_id, User):
            return self.has_access(user_id, platform, item, action, raise_error)
        elif isinstance(user_type, AuthKeyAuth) or isinstance(user_type, WebSessionAuth) or isinstance(user_id, User):
            return self.has_access(user_type, platform, item, action, raise_error)
        elif isinstance(user_id, str) is False:
            raise YomboWarning("user_id must be a string")
        elif isinstance(user_type, str) is False:
            raise YomboWarning("user_type (%s) must be one of: system, user, %s, or %s" %
                               (user_type, AUTH_TYPE_AUTHKEY, AUTH_TYPE_WEBSESSION))

        if user_type == AUTH_TYPE_AUTHKEY:
            auth = self._AuthKeys[user_id]
            return self.has_access(auth, platform, item, action, raise_error)
        elif user_type == AUTH_TYPE_USER:
            auth = self._Users[user_id]
            return self.has_access(auth, platform, item, action, raise_error)
        elif user_type == AUTH_TYPE_WEBSESSION:
            auth = self._WebSessions[user_id]
            return self.has_access(auth, platform, item, action, raise_error)
        else:
            raise YomboWarning("check_user_has_access must be of type user, authkey or websession.")

    def has_access_scan_item_permissions(self, item_permissions, requested_platform, requested_action, platform_item,
                                         platform_item_label):
        """
        Used to check access permissions. Not to collect access permissions.
        :param item_permissions:
        :param requested_platform:
        :param requested_action:
        :param platform_item:
        :param platform_item_label:
        :return:
        """
        def convert_wildcard(inputs):
            for input in inputs:
                if input == "*":
                    return True
            return False
        if platform_item is not None:
            # print("* scan_item_permissions start: item_permissions %s" % item_permissions)
            for effective_platform in (requested_platform, '*'):
                if effective_platform not in item_permissions:
                    # print("* - scan_item_permissions: effective_platform not found!: %s" % effective_platform)
                    continue
                for effective_platform_item_label in (platform_item_label, '*'):
                    # print("* --- scan_item_permissions: effective_platform_item_label: %s" % effective_platform_item_label)
                    for effective_action in (requested_action, '*'):
                        # print("* ---- scan_item_permissions: effective_action: %s" % effective_action)
                        if 'deny' in item_permissions[effective_platform]:
                            # print("* ----- scan_item_permissions: checking deny")
                            if effective_platform_item_label in item_permissions[effective_platform]['deny']:
                                if effective_action in item_permissions[effective_platform]['deny'][effective_platform_item_label]:
                                    return False, convert_wildcard(
                                        (effective_platform, effective_platform_item_label, effective_action)
                                    )
                        if 'allow' in item_permissions[effective_platform]:
                            # print("* ----- scan_item_permissions: checking allow")
                            if effective_platform_item_label in item_permissions[effective_platform]['allow']:
                                if effective_action in item_permissions[effective_platform]['allow'][effective_platform_item_label]:
                                    return True, convert_wildcard(
                                        (effective_platform, effective_platform_item_label, effective_action)
                                    )

        return None, None

    def has_access(self, auth, platform, item, action, raise_error=None):
        """
        Check if an auth (websession, authkey, system, etc) has access to the requested
        platform/item/action combo.

        :param auth: Either a websession or authkey
        :return: Boolean
        """
        auth = self.check_auth(auth)

        if raise_error is None:
            raise_error = True
        platform = platform.lower()
        if platform not in self.auth_platforms:
            raise YomboWarning("Invalid permission platform: %s" % platform)

        action = action.lower()

        logger.debug("has_access: platform: {platform}, item: {item}, action: {action}",
                     platform=platform, item=item, action=action)
        logger.debug("has_access: has roles: {roles}", roles=auth.roles)
        logger.debug("has_access: has roles: user_id: {user_id}, user_type: {user_type}",
                    user_id=auth.auth_id, user_type=auth.auth_type)

        cache_id = sha256_compact("%s:%s:%s:%s:%s" % (
            json.dumps(auth.item_permissions, sort_keys=True),
            json.dumps(auth.roles, sort_keys=True),
            platform,
            item,
            action,
            )
        )
        if cache_id in self.has_access_cache:
            return self.return_access(self.has_access_cache[cache_id], auth, platform, item, action, cache_id,
                                      raise_error)

        platform_item, platform_item_id, platform_item_label, platform_actions = \
            self.get_platform_item(platform, item)

        logger.debug("has_access: platform_item: {platform_item}, platform_item_id: "
                    "{platform_item_id}, platform_actions: {platform_actions}",
                    platform_item=None, platform_item_id=platform_item_id, platform_actions=platform_actions)

        if action not in platform_actions:
            raise YomboWarning('Action must be one of: %s' % ", ".join(platform_actions))

        # Admins have full access.
        if 'admin' in auth.roles:
            self.has_access_cache[cache_id] = True
            return self.return_access(True, auth, platform, item, action, raise_error)

        temp_result = None

        # Check if a specific item has a special access listed
        platform_allowed, platform_from_wild = self.has_access_scan_item_permissions(auth.item_permissions, platform, action, platform_item,
                                             platform_item_label)
        # print("user item permission results: %s - %s" % (platform_allowed, platform_from_wild))
        if isinstance(platform_allowed, bool):
            return self.return_access(platform_allowed, auth, platform, item, action, cache_id, raise_error)

        for a_role in self.get_roles(auth.roles):
            item_permissions = a_role.item_permissions
            # print("item_permissions: %s" % item_permissions)
            if platform_item is not None:
                platform_allowed, platform_from_wild = self.has_access_scan_item_permissions(
                    item_permissions,
                    platform,
                    action,
                    platform_item,
                    platform_item_label,
                )
                # print("role (%s) item permission results: %s - %s" % (role, platform_allowed, platform_from_wild))
                if isinstance(platform_allowed, bool):
                    if platform_from_wild is False:
                        return self.return_access(platform_allowed, auth, platform, item, action, cache_id, raise_error)
                    if temp_result is None or platform_allowed is False:
                        temp_result = platform_allowed

        if temp_result is None:
            temp_result = False
        return self.return_access(temp_result, auth, platform, item, action, cache_id, raise_error)

    def get_access_permissions(self, auth, requested_platform, requested_action=None, requested_item=None, source_type=None):
        """
        Collects all permissions from across all user item permissions. It
        also returns two items: list of permissions, and actions broken down by item.

        :param requested_platform:
        :param requested_action:
        :return:
        """
        auth = self.check_auth(auth)
        if source_type is None:
            source_type = 'all'

        cache_id = sha256_compact("%s:%s:%s:%s:%s" % (
            auth.auth_id,
            auth.auth_type,
            requested_platform,
            requested_action,
            source_type,
            )
        )

        if cache_id in self.get_access_permissions_cache:
            # print("returning cache: %s" % cache_id)
            return self.get_access_permissions_cache[cache_id]

        if requested_item is not None:
            platform_item, platform_item_id, requested_item_label, platform_actions = \
                self.get_platform_item(requested_platform, requested_item)
        else:
            requested_item_label = None

        out_permissions = {'allow': {}, 'deny': {}}
        # print("* get_item_permissions: requested_platform: %s" % requested_platform)
        # print("* get_item_permissions: requested_action: %s" % requested_action)
        # print(" get_access_permissions source_type: %s" % source_type)

        def get_item_permissions(item_permissions):
            # print("* > get_item_permissions: item_permissions: %s" % item_permissions)
            for effective_platform in (requested_platform, '*'):
                if effective_platform not in item_permissions:
                    # print("* -- get_item_permissions effective-platform not found: %s" % effective_platform)
                    continue
                for effective_access, access_data in item_permissions[effective_platform].items():
                    for item, actions in item_permissions[effective_platform][effective_access].items():
                        if requested_item_label is None or requested_item_label == item:
                            # print("* --- get_item_permissions: effective_platform_item_label: %s" % item)
                            for action in actions:
                                # print("requested_action: %s" % requested_action)
                                # print("action: %s" % action)
                                if requested_action is None or requested_action == action:
                                    effective_action = action
                                elif action == '*':
                                    effective_action = requested_action
                                else:
                                    continue

                                # print("* ---- get_item_permissions: effective_action: %s" % effective_action)
                                if effective_access not in out_permissions:
                                    # print("building out_permission_actions..  Adding access.")
                                    out_permissions[effective_access] = {}
                                if item not in out_permissions[effective_access]:
                                    # print("building out_permission_actions..  Adding item.")
                                    out_permissions[effective_access][item] = []
                                if effective_action not in out_permissions[effective_access][item]:
                                        # print("building out_permission_actions..  Adding action.")
                                        out_permissions[effective_access][item].append(effective_action)

                                if effective_access == 'deny':
                                    if 'allow' in out_permissions:
                                        if item in out_permissions['allow']:
                                            if effective_action in out_permissions['allow'][item]:
                                                out_permissions['allow'][item].remove(effective_action)
                                            if len(out_permissions['allow'][item]) == 0:
                                                del out_permissions['allow'][item]
                                        if len(out_permissions['allow']) == 0:
                                            del out_permissions['allow']
                                if effective_access == 'allow':
                                    if 'deny' in out_permissions:
                                        if item in out_permissions['deny']:
                                            if effective_action in out_permissions['deny'][item]:
                                                out_permissions['deny'][item].remove(effective_action)
                                            if len(out_permissions['deny'][item]) == 0:
                                                del out_permissions['deny'][item]
                                        if len(out_permissions['deny']) == 0:
                                            del out_permissions['deny']

        # go thru all roles and setup base items
        if source_type in ("all", "roles"):
            # print("get_access_permissions in roles- source_type: %s" % source_type)
            for role_id, role in self.roles.items():
                get_item_permissions(role.item_permissions)
                # print("out_permissions after ROLE scan: %s" % out_permissions)
        # Add user item permissions last, it has the highest priority and will change the roles item permissions.
        if source_type in ("all", "user"):
            get_item_permissions(auth.item_permissions)

        self.get_access_permissions_cache[cache_id] = out_permissions
        return out_permissions

    def get_user_access_permissions(self, requested_platform, requested_item, source_type):
        """
        Like get_access_permissions, but it's output includes the email or role_id and is a simple list
        of entries.

        :param requested_platform:
        :param requested_action:
        :param source_type: One of 'user' or 'role'
        :return:
        """

        cache_id = sha256_compact("%s:%s:%s" % (
            requested_platform,
            requested_item,
            source_type,
            )
        )

        if cache_id in self.get_access_access_permissions_cache:
            print("returning cache: %s" % cache_id)
            return self.get_access_access_permissions_cache[cache_id]

        platform_item, platform_item_id, requested_item_label, platform_actions = \
            self.get_platform_item(requested_platform, requested_item)

        out_permissions = []

        def get_item_permissions(item_permissions, auth):
            print("* > get_item_permissions: item_permissions: %s" % item_permissions)
            for effective_platform in (requested_platform, '*'):
                if effective_platform not in item_permissions:
                    print("* -- get_item_permissions effective-platform not found: %s" % effective_platform)
                    continue
                try:
                    print("* - get_item_permissions: data: %s" % item_permissions[effective_platform])
                except:
                    pass
                for effective_access, access_data in item_permissions[effective_platform].items():
                    if requested_item_label not in item_permissions[effective_platform][effective_access]:
                        continue
                    actions = item_permissions[effective_platform][effective_access][requested_item_label]
                    for action in actions:
                        out_permissions.append(
                            {
                                "auth": auth,
                                "access": effective_access,
                                "action": action,
                            }
                        )

        # go thru all roles and setup base items
        if source_type in ("roles", "role"):
            print("get_access_permissions in roles- source_type: %s" % source_type)
            for role_id, role in self.roles.items():
                # print("* -> get_access: role_machine_label: %s" % role_machine_label)
                get_item_permissions(role.item_permissions, role)
                # print("out_permissions after ROLE scan: %s" % out_permissions)
        # Add user item permissions last, it has the highest priority and will change the roles item permissions.

        if source_type in ("users", "user"):
            for email, the_user in self.users.items():
                get_item_permissions(the_user.item_permissions, the_user)

        self.get_access_access_permissions_cache[cache_id] = out_permissions
        return out_permissions

    def get_access(self, auth, requested_platform, requested_action):
        """
        Get list of access end points for a given platform and action.  If the platform isn't itemizable (atoms,
        states, etc, then '*' will returned for 'items'.

        Returns two variables:
        1) items - (list) list of item ID's, if possible. Or '*" if not itemizable.
        2) permissions - (dict) Collective of permissions based on all the combined roles for the given auth.

        :return: list of a list and dict.
        """
        auth = self.check_auth(auth)

        def return_values(final_item_keys, final_permission):
            """
            Sets the cache content and returns the correctly formatted response
            :param final_item_keys:
            :param final_permission:
            :return:
            """
            self.get_access_cache[cache_id] = (final_item_keys, final_permission)
            return final_item_keys, final_permission

        requested_platform = requested_platform.lower()
        if requested_platform not in self.auth_platforms:
            raise YomboWarning("get_access() requires a valid platform, requested platform not found.")

        cache_id = sha256_compact("%s:%s:%s:%s" % (
            auth.auth_id,
            auth.auth_type,
            requested_platform,
            requested_action,
            )
        )
        if cache_id in self.get_access_cache:
            return self.get_access_cache[cache_id]

        out_permissions = self.get_access_permissions(auth, requested_platform, requested_action=requested_action)
        # print("* get_access: out_permissions: %s" % out_permissions)
        platform_item, platform_item_id, platform_item_label, platform_actions = \
            self.get_platform_item(requested_platform)

        platform_item_keys = list(platform_item)
        # print("* get_access: platform_item_keys: %s" % platform_item_keys)

        # Call out specific item access according to the out_permissions table.
        out_item_keys = []

        if '*' in out_permissions['allow']:
            return return_values(platform_item_keys, out_permissions)
        else:
            for item, item_data in out_permissions['allow'].items():
                out_item_keys.append(item)

        return return_values(out_item_keys, out_permissions)

    def get(self, requested_id):
        """
        Looks for a given requested_id as either a user_id or email address.
        :param requested_id:
        :return:
        """
        if requested_id in self.users:
            return self.users[requested_id]
        if requested_id.lower() in self.users:
            return self.users[requested_id]
        for email, user in self.users.items():
            if user.user_id == requested_id:
                return user
            if user.name == requested_id:
                return user
        raise KeyError("User not found. %s" % requested_id)

    def get_roles(self, role_labels=None):
        """
        Convert a list of roles into a generator that returns a role instance.
        """
        if role_labels is None:
            role_labels = list(self.roles.keys())

        roles = {}
        for role_id in role_labels:
            roles[role_id] = self.get_role(role_id)

        for role_id, role in sorted(roles.items(), key=lambda x: x[1].label):
            try:
                yield role
            except KeyError:
                pass

    def get_role(self, requested_role):
        """
        Get a role instance using a role id, machine_label, or label.

        :param requested_role:
        :return:
        """
        if isinstance(requested_role, str):
            if requested_role in self.roles:
                return self.roles[requested_role]
            for label, role in self.roles.items():
                if role.role_id == requested_role:
                    return role
                if role.machine_label == requested_role:
                    return role
                if role.label == requested_role:
                    return role
            return None
        elif isinstance(requested_role, Role) is True:
            role = requested_role
        else:
            raise KeyError("Role not found, unknown input type.")
        return role
