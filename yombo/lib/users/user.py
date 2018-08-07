"""
A class to represent a user.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from twisted.internet import reactor

from yombo.constants import ITEMIZED_PERMISSION_PLATFORMS
from yombo.core.exceptions import YomboWarning
from yombo.lib.users.role import Role
from yombo.utils import data_pickle, data_unpickle
from yombo.utils.decorators import memoize_ttl

class User(object):
    """
    User class to manage role membership, etc.
    """

    def __init__(self, parent, data={}):
        """
        Setup a new user instance.

        :param parent: A reference to the users library.
        """
        self._Parent = parent
        self.user_id: str = data['id']
        self.email: str = data['email']
        self.name: str = data['name']
        self.access_code_digits: int = data['access_code_digits']
        self.access_code_string: str = data['access_code_string']
        self.item_permissions: dict = {}  # {'device': {'machine_label': ['allow_edit', 'allow_add', ...]} }
        self.roles: list = []

        rbac_raw = self._Parent._Configs.get('rbac_user_roles', self.user_id, None, False)
        if rbac_raw is None:
            rbac = {}
        else:
            rbac = data_unpickle(rbac_raw, encoder='msgpack_base64')

        if 'roles' in rbac:
            roles = rbac['roles']
            if len(roles) > 0:
                for role in roles:
                    self.attach_role(role, save=False)

        if 'item_permissions' in rbac:
            self.item_permissions = rbac['item_permissions']
        self.save()

    def has_role(self, role):
        if role.lower() in self.roles:
            return True
        else:
            return False

    def attach_role(self, role_id, save=None):
        """
        Add a role to this user

        :param role_label: A role instance, role_id, role machine_label, or role label.
        """
        role = self._Parent.get_role(role_id)
        machine_label = role.machine_label

        if machine_label not in self.roles:
            self.roles.append(machine_label)
            if save in (None, True):
                self.save()

    def unattach_role(self, role_id, save=None):
        """
        Remove a role from this user

        :param role_label: A role instance, role_id, role machine_label, or role label.
        """
        role = self._Parent.get_role(role_id)
        machine_label = role.machine_label

        if role.label == 'admin' and self._Parent.owner_id == self.user_id:
            return

        if machine_label in self.roles:
            self.roles.remove(machine_label)
            if save in (None, True):
                self.save()

    def get_roles(self):
        """
        Get a generator for all roles belong to a user.
        """
        for label in self.roles.copy():
            try:
                yield self._Parent.roles[label]
            except KeyError:
                pass

    def add_item_permission(self, platform, item, actions, save=None):
        """
        Adds an item permission.

        :param platform: 'device', 'scene', 'automation', etc.
        :param item: Item ID to reference
        :param actions: Action to add.... edit, delete, view, control...
        """
        platform = platform.lower()
        if platform not in ITEMIZED_PERMISSION_PLATFORMS:
            raise YomboWarning("Invalid permission platform.")

        if platform not in self.item_permissions:
            self.item_permissions[platform] = {}
        platform_item, platform_item_key, platform_actions = self._Parent.get_platform_item(platform, item)

        if platform_item_key not in self.item_permissions[platform]:
            self.item_permissions[platform][platform_item_key] = []

        if actions is None:
            return

        if isinstance(actions, list) is False:
            actions = [actions]

        [x.lower() for x in actions]

        for action in sorted(actions):
            if action not in platform_actions:
                raise YomboWarning("Add %s action is not acceptable: %s" % (platform, action))
            if action in self.item_permissions[platform][platform_item_key]:
                continue

            details = action.split('_')

            if details[0] == 'deny':
                if 'allow_%s' % details[1] in self.item_permissions[platform][platform_item_key]:
                    self.item_permissions[platform][platform_item_key].remove('allow_%s' % details[1])

            self.item_permissions[platform][platform_item_key].append(action)
        if save in (None, True):
            self.save()

    def remove_item_permission(self, platform, item, actions=None, save=None):
        """
        Remove item specific permissions from a user.

        :param platform: Which platform to work with: automation, device, scene
        :param item: The item id or machine_label to remove.
        """
        platform = platform.lower()
        if platform not in ITEMIZED_PERMISSION_PLATFORMS:
            raise YomboWarning("Invalid permission platform.")

        if platform not in self.item_permissions:
            return

        platform_item, platform_item_key, platform_actions = self._Parent.get_platform_item(platform, item)
        # print("data: %s, %s, %s" % (platform_item, platform_item_key, platform_actions))
        if platform_item_key not in self.item_permissions[platform]:
            return

        if actions is not None:
            if isinstance(actions, list) is False:
                actions = [actions]
            [x.lower() for x in actions]

            for action in sorted(actions):
                if action not in platform_actions:
                    continue
                self.item_permissions[platform][platform_item_key].remove(action)
            if len(self.item_permissions[platform][platform_item_key]):
                del self.item_permissions[platform][platform_item_key]
        else:
            del self.item_permissions[platform][platform_item_key]

        if save in (None, True):
            self.save()

    def get_item_permissions(self, platform):
        """
        Get a generator for all devices the user has specific access to, not including devices from roles.
        """
        # print("get_item_permissions::item_permissions: %s" % self.item_permissions)
        if platform not in self.item_permissions:
            return
        permissions = self.item_permissions[platform].copy()
        for item_id in permissions:
            try:
                platform_item, platform_item_key, platform_actions = self._Parent.get_platform_item(platform, item_id)
                yield platform_item, self.item_permissions[platform][platform_item_key]
            except KeyError as e:
                pass

    @memoize_ttl(60)
    def has_access(self, platform, item, action, raise_error=None):
        """
        Check if user has access  to a resource / access_type combination.

        :param access_type:
        :param resource:
        :return:
        """
        return self._Parent.has_access(self, self.item_permissions, self.roles, platform, item, action, raise_error)

    def save(self):
        """
        Save the user device
        :return:
        """
        tosave = {
            'roles': self.roles,
            'item_permissions': self.item_permissions
        }
        self._Parent._Configs.set('rbac_user_roles', self.user_id,
                                  data_pickle(tosave, encoder="msgpack_base64", local=True),
                                  ignore_case=True)

    def __repr__(self):
        return '<User %s>' % self.roles
