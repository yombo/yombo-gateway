"""
A class to represent a user.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from twisted.internet import reactor

from yombo.core.exceptions import YomboWarning
from yombo.lib.users.role import Role
from yombo.utils import data_pickle, data_unpickle
from yombo.utils.decorators import memoize_ttl

DEVICE_ACTIONS = ('allow_view', 'allow_control', 'allow_edit', 'allow_enable', 'allow_disable',
                  'deny_view', 'deny_control', 'deny_edit', 'deny_enable', 'deny_disable')

class User(object):
    """
    User class to manage role membership, etc.
    """

    def __init__(self, parent, data={}):
        """
        Setup a new user instance.

        :param parent: A reference to the users library.
        """
        def repad(local_data):
            """ Used to add the = back the base64... """
            return local_data + "=" * (-len(local_data) % 4)

        self._Parent = parent
        self.user_id: str = data['id']
        self.email: str = data['email']
        self.name: str = data['name']
        self.access_code_digits: int = data['access_code_digits']
        self.access_code_string: str = data['access_code_string']
        self.devices: dict = {}  # {'device_id': ['edit', 'add', ...]
        self.roles: list = []

        rbac_raw = self._Parent._Configs.get('rbac_user_roles', self.user_id, None, False)
        if rbac_raw is None:
            rbac = {}
        else:
            rbac = data_unpickle(repad(rbac_raw), encoder='msgpack_base64')

        if 'roles' in rbac:
            roles = rbac['roles']
            if len(roles) > 0:
                for role in roles:
                    self.attach_role(role, save=False)

        if 'devices' in rbac:
            devices = rbac['devices']
            if len(devices) > 0:
                for device_machine_label, actions in devices.items():
                    self.add_device(device_machine_label, actions, save=False)
        self.save()

    def attach_role(self, role_label, save=None):
        """
        Add a role to this user

        :param role_label: A role instance, role_id, role machine_label, or role label.
        """
        if isinstance(role_label, Role):
            machine_label = role_label.machine_label
        else:
            role = self._Parent.get_role(role_label)
            if role is None:
                raise YomboWarning("Role not found, cannot add role.")
            machine_label = role.machine_label

        if machine_label not in self.roles:
            self.roles.append(machine_label)
            if save in (None, True):
                self.save()

    def unattach_role(self, role_label, save=None):
        """
        Remove a role from this user

        :param role_label: A role instance, role_id, role machine_label, or role label.
        """
        if role_label == 'admin' and self._Parent.owner_id == self.user_id:
            return

        if isinstance(role_label, Role):
            machine_label = role_label.machine_label
        else:
            role = self._Parent.get_role(role_label)
            if role is None:
                raise YomboWarning("Role not found, cannot add role.")
            machine_label = role.machine_label

        if machine_label in self.roles:
            self.roles.remove(machine_label)
            if save in (None, True):
                self.save()
        else:
            raise YomboWarning("User doesn't have requested role, cannot remove.")

    def get_roles(self):
        """
        Get a generator for all roles belong to a user.
        """
        for label in self.roles.copy():
            try:
                yield self._Parent.roles[label]
            except KeyError:
                pass

    def add_device(self, device_id, actions, save=None):
        """
        Adds access to a device

        :param device_id: A device instance, device_id, device_machine_label, or device_label
        :param action: Action for the device. edit, delete, view, control...
        """
        device = self._Parent._Devices.get(device_id)
        # if device.machine_label not in self.devices:
        self.devices[device.machine_label] = []

        if isinstance(actions, list) is False:
            actions = [actions]

        for action in sorted(actions):
            if action not in DEVICE_ACTIONS:
                raise YomboWarning("Add device action is not acceptable: %s" % action)
            if action in self.devices[device.machine_label]:
                continue

            details = action.split('_')

            if details[0] == 'deny':
                if 'allow_%s' % details[1] in self.devices[device.machine_label]:
                    self.devices[device.machine_label].remove('allow_%s' % details[1])

            self.devices[device.machine_label].append(action)
        if save in (None, True):
            self.save()

    def remove_device(self, device_id, actions=None, save=None):
        """
        Remove device access from this user.

        :param device_id: A device instance, device_id, device_machine_label, or device_label
        :param action: Action for the device. edit, delete, view, control...
        """
        device = self._Parent._Devices.get(device_id)
        if device.machine_label not in self.devices:
            return

        if actions is None:
            del self.devices[device.machine_label]
            if save in (None, True):
                self.save()
            return

        if isinstance(actions, list) is False:
            actions = [actions]

        for action in actions:
            if action not in DEVICE_ACTIONS:
                raise YomboWarning("Remove device action is not acceptable: %s" % action)

            if action in self.devices[device.machine_label]:
                self.devices[device.machine_label].remove(action)

        if len(self.devices[device.machine_label]) == 0:
            del self.devices[device.machine_label]

        if save in (None, True):
            self.save()

    def get_devices(self):
        """
        Get a generator for all devices the user has specific access to, not including devices from roles.
        """
        devices = self.devices.copy()
        for machine_label in devices:
            try:
                yield self._Parent._Devices[machine_label], devices[machine_label]
            except KeyError:
                pass

    @memoize_ttl(60)
    def has_access(self, path, action):
        """
        Check if user has access  to a resource / access_type combination.

        :param access_type:
        :param resource:
        :return:
        """
        return self._Parent.has_access(self, self.roles, path, action)

    def save(self):
        """
        Save the user device
        :return:
        """
        tosave = {
            'roles': self.roles,
            'devices': self.devices
        }
        self._Parent._Configs.set('rbac_user_roles', self.user_id,
                                  data_pickle(tosave, encoder="msgpack_base64").rstrip("="),
                                  ignore_case=True)

    def __repr__(self):
        return '<User %s>' % self.roles
