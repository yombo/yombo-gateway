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
from yombo.core.exceptions import YomboWarning, YomboNoAccess
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.lib.users.role import Role
from yombo.lib.users.user import User
from yombo.lib.users.constants import SYSTEM_ROLES
from yombo.utils import global_invoke_all
from yombo.utils.decorators import memoize_ttl

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

            >>> system_cpus = self._Users['mitch@example.com']

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

    @inlineCallbacks
    def _init_(self, **kwargs):
        self.roles: dict = {}
        self.users: dict = {}
        self.owner_id = self._Configs.get('core', 'owner_id', None, False)
        self.owner_user = None
        yield self.load_roles()

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
            for machine_label, data in roles.items():
                if 'label' not in data:
                    data['label'] = machine_label
                if 'description' not in data:
                    data['description'] = data['label']
                if 'permissions' not in data:
                    data['permissions'] = []
                else:
                    if isinstance(data['permissions'], list) is False:
                        logger.warn("Cannot add role, permissions must be a list. Role: {machine_label}",
                                    machine_label=machine_label)
                        continue
                self.roles[machine_label] = Role(self, machine_label,
                                                 label=data['label'],
                                                 description=data['description'],
                                                 source=component._FullName,
                                                 permissions=data['permissions'])

        yield self.load_users()
        if self.owner_id is not None:
            self.owner_user = self.get(self.owner_id)
            self.owner_user.add_role('admin')

    def add_user(self, new_user):
        """
        Primarily called by the users.py web interface routes to add a new user.

        :param new_user:
        :param roles:
        :return:
        """
        self.users[new_user['email']] = User(self, new_user)
        # self.users[new_user['email']].sync_user_to_db()

    @inlineCallbacks
    def load_roles(self):
        self.roles.clear()
        for machine_label, data in SYSTEM_ROLES.items():
            self.roles[machine_label] = Role(self, machine_label,
                                             label=data['label'],
                                             description=data['description'],
                                             source='system',
                                             permissions=data['permissions'])

        db_roles = yield self._LocalDB.get_roles()
        for role in db_roles:
            self.roles[role.machine_label] = Role(self, role.machine_label,
                                                  label=role.label,
                                                  description=role.description,
                                                  source='database',
                                                  role_id=role.id)

    @inlineCallbacks
    def load_users(self):
        db_users = yield self._LocalDB.get_users()
        # db_user_roles = yield self._LocalDB.get_user_roles()

        for user in db_users:
            # if user.email in db_user_roles:
            #     user_roles = db_user_roles[user.email]['roles']
            # else:
            #     user_roles = []
            self.users[user.email] = User(self, user.__dict__)

    def add_role(self, data):
        """
        Add a new possible role to the system.

        :param data:
        :return:
        """
        machine_label = data['machine_label']
        if machine_label in self.roles:
            raise YomboWarning("Role already exists.")
        if 'label' not in data:
            data['label'] = machine_label
        if 'description' not in data:
            data['description'] = machine_label
        if 'permissions' not in data:
            data['permissions'] = []
        self.roles[machine_label] = Role(self, machine_label,
                                         label=data['label'],
                                         description=data['description'],
                                         source='system',
                                         permissions=data['permissions'])

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

    def has_access(self, roles, path, action, raise_error=None):
        """
        Usually called by either the user instance, websession instance, or auth key instance. Checks if the provided
        list (strings) of roles will allow or deny the path/action combo.

        :return: Boolean
        """
        path = path.lower()
        action = action.lower()

        logger.debug("has_access: path: {path}, action: {action}", path=path, action=action)
        logger.debug("has_access: has roles: {roles}", roles=roles)
        if 'admin' in roles:
            return True

        for a_role in self.get_roles(roles):
            results = a_role.has_access(path, action)

            logger.debug("has_access: results for role.has_access: %s" % results)
            if isinstance(results, bool):  # returns None if no matches were found.
                if results is False and raise_error is True:
                    raise YomboNoAccess(path=path, action=action)
                return results
        if raise_error is True:
            raise YomboNoAccess(path=path, action=action)
        return False

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
