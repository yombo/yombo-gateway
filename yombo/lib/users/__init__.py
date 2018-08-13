# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Manages users within the gateway. All users are loaded on startup.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import (DEVICE_ACTIONS, AUTOMATION_ACTIONS, SCENE_ACTIONS, ITEMIZED_PERMISSION_PLATFORMS,
                             PERMISSION_PLATFORMS)
from yombo.core.exceptions import YomboWarning, YomboNoAccess
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.lib.users.role import Role
from yombo.lib.users.user import User
from yombo.lib.users.constants import SYSTEM_ROLES
from yombo.utils import global_invoke_all, data_unpickle

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
        self.owner_id = self._Configs.get('core', 'owner_id', None, False)
        self.owner_user = None
        self.platforms = []  # list of possible/known access platforms

        self.load_roles()

    @inlineCallbacks
    def _start_(self, **kwargs):
        """
        Calls the _roles_ hook to all components to add system level roles.
        :param kwargs:
        :return:
        """
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
                self.roles[machine_label] = self.add_role(role_data, source="system")

        yield self.load_users()
        if self.owner_id is not None:
            self.owner_user = self.get(self.owner_id)
            self.owner_user.attach_role('admin')

    def add_user(self, new_user):
        """
        Primarily called by the users.py web interface routes to add a new user.

        :param new_user:
        :param roles:
        :return:
        """
        self.users[new_user['email']] = User(self, new_user)
        # self.users[new_user['email']].sync_user_to_db()

    def load_roles(self):
        self.roles.clear()
        for machine_label, role_data in SYSTEM_ROLES.items():
            role_data['machine_label'] = machine_label
            self.roles[machine_label] = self.add_role(role_data, source="system")

        user_roles = self._Configs.get('rbac_roles', '*', {}, False)
        for role_id, role_data_raw in user_roles.items():
            role_data = data_unpickle(role_data_raw, encoder='msgpack_base64')
            self.roles[machine_label] = self.add_role(role_data, source="user")

    @inlineCallbacks
    def load_users(self):
        db_users = yield self._LocalDB.get_users()

        for user in db_users:
            self.users[user.email] = User(self, user.__dict__)

    def add_role(self, data, source=None):
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
        if 'description' not in data:
            data['description'] = machine_label
        if 'permissions' not in data:
            data['permissions'] = []
        self.roles[machine_label] = Role(self,
                                         machine_label=machine_label,
                                         label=data['label'],
                                         description=data['description'],
                                         source=source,
                                         permissions=data['permissions'])
        return self.roles[machine_label]

    def add_permission_to_role(self, machine_label, permission):
        """
        Add a new permission to an existing role.

        :param machine_label:
        :param permission:
        :return:
        """
        role = self.get_role(machine_label)
        if role is None:
            raise YomboWarning("Role doesn't exist.")
        if 'path' not in permission:
            raise YomboWarning("Permission is missing path.")
        if 'action' not in permission:
            raise YomboWarning("Permission is missing action.")
        if 'access' not in permission:
            permission['access'] = 'allow'

        role.permissions.append(permission)

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

    def list_role_auth_keys(self, requested_role):
        """
        List all users belonging to a role.

        :param requested_role:
        :return:
        """
        role_apiauths = []
        role = self.get_role(requested_role)

        role_machine_label = role.machine_label
        for auth_id, auth_key in self._APIAuth.items():
            auth_key_roles = auth_key.roles
            if role_machine_label in auth_key_roles:
                role_apiauths.append(auth_key)
        return role_apiauths

    def list_roles_by_user(self):
        """
        All roles and which users belong to them. This takes a bit as it has to iterate all users.

        This is different than list_role_users in that this gets all the roles and the members for each role.

        :return:
        """
        roles = {}
        for email, user in self.users.items():
            for role in user.roles:
                if role not in roles:
                    roles[role] = []
                roles[role].append(user)
        return roles

    def list_role_users(self, requested_role):
        """
        List all users belonging to a role.

        :param requested_role:
        :return:
        """
        role_users = []
        role = self.get_role(requested_role)

        role_machine_label = role.label
        for email, user in self.users.items():
            user_roles = user.roles
            if role_machine_label in user_roles:
                role_users.append(user)
        return role_users

    def get_item_permissions_for_item(self, platform, item):
        """
        List all users and their permissions for a specific platform

        :return:
        """
        platform = platform.lower()
        if platform not in ITEMIZED_PERMISSION_PLATFORMS:
            return {}

        platform_item, platform_item_key, platform_actions = self.get_platform_item(platform, item)

        permissions = {}
        for email, user in self.users.items():
            if platform_item_key in user.item_permissions[platform]:
                permissions[email] = user.item_permissions[platform][platform_item_key]
        return permissions

    def get_platform_item(self, platform, item=None, item_permissions=None):
        if item in ('*', None):
            if platform == 'automation':
                platform_actions = AUTOMATION_ACTIONS
                platform_item = self._Automation.rules
            elif platform == 'device':
                platform_actions = DEVICE_ACTIONS
                platform_item = self._Devices.devices
            elif platform == 'scene':
                platform_actions = SCENE_ACTIONS
                platform_item = self._Scenes.scenes
            else:
                platform_actions = None
                platform_item = None
            return platform_item, None, platform_actions

        if platform == 'automation':
            platform_item = self._Automation.get(item)
            platform_item_key = platform_item.machine_label
            platform_actions = AUTOMATION_ACTIONS
        elif platform == 'device':
            platform_item = self._Devices.get(item)
            platform_item_key = platform_item.machine_label
            platform_actions = DEVICE_ACTIONS
        elif platform == 'scene':
            platform_item = self._Scenes.get(item)
            platform_item_key = platform_item.machine_label
            platform_actions = SCENE_ACTIONS
        else:
            platform_item = None
            platform_item_key = None
            platform_actions = None

        if item_permissions is None:
            return platform_item, platform_item_key, platform_actions

        if platform in item_permissions:
            if platform_item_key in item_permissions[platform]:
                item_actions = item_permissions[platform]
                return platform_item, platform_item_key, platform_actions, item_permissions[platform][platform_item_key]
        return platform_item, platform_item_key, platform_actions, []

    def get_platform_items(self, platform):
        if platform == 'automation':
            return self._Automation.rules
        elif platform == 'device':
            return self._Devices.devices
        elif platform == 'scene':
            return self._Scenes.scenes
        return {}

    def has_access(self, item_permissions, roles, platform, item, action, raise_error=None):
        """
        Usually called by either the user instance, websession instance, or auth key instance. Checks if the provided
        list (strings) of roles will allow or deny the path/action combo.

        :return: Boolean
        """
        def return_access(value):
            if value is True:
                return True

            if value is False:
                if raise_error is not True:
                    return False
            raise YomboNoAccess(item_permissions=item_permissions,
                                roles=roles,
                                platform=platform,
                                item=item,
                                action=action)

        if raise_error is None:
            raise_error = True

        platform = platform.lower()
        action = action.lower()

        logger.info("has_access: platform: {platform}, item: {item}, action: {action}",
                     platform=platform, item=item, action=action)
        logger.info("has_access: has roles: {roles}", roles=roles)

        # Admins have full access.
        if 'admin' in roles:
            return True

        # Check if a specific item has a special access listed
        platform_item, platform_item_key, platform_actions = self.get_platform_item(platform, item)

        if platform_item is not None:
            if platform_item_key in item_permissions[platform]:
                item_actions = item_permissions[platform][platform_item_key]
                if "deny_%s" % action in item_actions:
                    return return_access(False)
                if "allow_%s" % action in item_actions:
                    return True

        for a_role in self.get_roles(roles):
            results = a_role.has_access(platform, item, action)
            logger.info("has_access: results for role.has_access: %s" % results)
            return return_access(results)
        return return_access(False)

    def get_access(self, in_item_permissions, in_roles, requested_platform=None):
        """
        Gets list of access end points for the user. This includes all devices and all rules for all roles the
        user belongs to.

        :return: Boolean
        """
        out_permissions = {
            'allow': {},
            'deny': {},
        }

        # go thru all roles and setup base items
        for role_machine_label in in_roles:
            role = self.get_role(role_machine_label)

            for access_type in ('allow', 'deny'):
                for permission_id, permission in role.permissions[access_type].items():
                    platform = permission['platform']
                    if access_type == 'allow':
                        if platform in out_permissions['deny']:
                            if permission['item'] in out_permissions['deny'][platform]:
                                if permission['action'] in out_permissions['deny'][platform][permission['item']]:
                                    continue

                    if access_type == 'deny':
                        if platform in out_permissions['allow']:
                            if permission['item'] in out_permissions['allow'][platform]:
                                if permission['action'] in out_permissions['allow'][platform][permission['item']]:
                                    out_permissions['allow'][platform][permission['item']].remove(permission['action'])

                    if platform not in out_permissions[access_type]:
                        out_permissions[access_type][platform] = {}
                    if permission['item'] not in out_permissions[access_type][platform]:
                        out_permissions[access_type][platform][permission['item']] = []
                    if permission['action'] not in out_permissions[access_type][platform][permission['item']]:
                        out_permissions[access_type][platform][permission['item']].append(permission['action'])

        # Now apply bulk role permissions to individual item_permissions..
        out_item_permission = {}

        ############################
        def add_itemized_platform(source_platform, destination_platform=None):
            if destination_platform is None:
                destination_platform = source_platform

            if requested_platform is not None and destination_platform != requested_platform:
                return

            if destination_platform not in out_item_permission:
                out_item_permission[destination_platform] = {}

            for item, actions in out_permissions[access_type][source_platform].items():
                try:
                    platform_item, platform_item_key, platform_actions = self.get_platform_item(destination_platform,
                                                                                                item)
                except:
                    continue
                if item == '*':
                    for the_id, the_item in platform_item.items():
                        machine_label = the_item.machine_label
                        if the_id not in out_item_permission[destination_platform]:
                            out_item_permission[destination_platform][machine_label] = []
                        for action in actions:
                            if action == '*':
                                for temp_action in platform_actions:
                                    if temp_action.startswith("allow_") and \
                                            temp_action not in out_item_permission[destination_platform][machine_label]:
                                        out_item_permission[destination_platform][machine_label].append(temp_action)
                            else:
                                if action not in out_item_permission[destination_platform][machine_label]:
                                    out_item_permission[destination_platform][machine_label].append(
                                        "%s_%s" % (access_type, action))
                else:
                    if platform_item_key not in out_item_permission[destination_platform]:
                        out_item_permission[destination_platform][platform_item_key] = []
                    for action in actions:
                        if action not in out_item_permission[destination_platform][platform_item_key]:
                            out_item_permission[destination_platform][platform_item_key].append("%s_%s" % (access_type, action))
        ############################

        for platform in ITEMIZED_PERMISSION_PLATFORMS:
            for access_type in ('allow', 'deny'):
                if '*' in out_permissions[access_type]:
                    for temp_platform in PERMISSION_PLATFORMS:
                        add_itemized_platform('*', temp_platform)
                elif platform in out_permissions[access_type]:
                    add_itemized_platform(platform)

        # now apply user/session specific item_permissions..
        # print("get_access: starting specific items......")
        # print("get_access: requested_platform: %s" % requested_platform)
        # print("get_access: in_item_permissions: %s" % in_item_permissions)
        for platform, items in in_item_permissions.items():
            # print("get_access: platform: %s" % platform)
            if requested_platform is not None and platform != requested_platform:
                continue
            for item_id, actions in items.items():
                platform_item, platform_item_key, platform_actions = self.get_platform_item(platform, item_id)
                for action in actions:
                    access_type, action = action.split("_")
                    # If we have an allow, remove any deny items.
                    if access_type == 'deny':
                        if platform in out_item_permission:
                            if platform_item_key in out_item_permission[platform]:
                                allow_action = "allow_%s" % action
                                if allow_action in out_item_permission[platform][platform_item_key]:
                                    out_item_permission[platform][platform_item_key].remove(allow_action)

                    # If we have an deny, remove any allow items.
                    if access_type == 'allow':
                        if platform in out_item_permission:
                            if platform_item_key not in out_item_permission[platform]:
                                deny_action = "deny_%s" % action
                                if deny_action in out_item_permission[platform][platform_item_key]:
                                    out_item_permission[platform][platform_item_key].remove(deny_action)

                    if platform not in out_item_permission:
                        out_item_permission[platform] = {}
                    if platform_item_key not in out_item_permission[platform]:
                        out_item_permission[platform][platform_item_key] = []
                    out_item_permission[platform][platform_item_key].append("%s_%s" % (access_type, action))

        return out_permissions, out_item_permission

    def get(self, requested_id):
            if requested_id in self.users:
                return self.users[requested_id]
            if requested_id.lower() in self.users:
                return self.users[requested_id]
            for email, user in self.users.items():
                if user.user_id == requested_id:
                    return user
                if user.name == requested_id:
                    return user
            raise KeyError("User not found.")

    def get_roles(self, role_labels=None):
        """
        Convert a list of roles into a generator that returns a role instance.
        """
        if role_labels is None:
            role_labels = list(self.roles.keys())

        roles = {}
        for machine_label in role_labels:
            roles[machine_label] = self.roles[machine_label]

        for machine_label, role in sorted(roles.items(), key=lambda x: x[1].label):
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
                if role.label == requested_role:
                    return role
            return None
        elif isinstance(requested_role, Role) is True:
            role = requested_role
        else:
            raise KeyError("Role not found, unknown input type.")
        return role
