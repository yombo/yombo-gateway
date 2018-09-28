"""
A class to represent a user.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from yombo.lib.users.authbase import AuthBase
from yombo.utils import data_pickle, data_unpickle

class User(AuthBase):
    """
    User class to manage role membership, etc.
    """
    @property
    def auth_id(self):
        return self.user_id

    @property
    def auth_type(self):
        return "user"

    @property
    def label(self):
        return "%s <%s>" % (self.name, self.email)

    @property
    def __str__(self):
        return "%s <%s>" % (self.name, self.email)

    def __init__(self, parent, data={}, flush_cache=None):
        """
        Setup a new user instance.

        :param parent: A reference to the users library.
        """
        super().__init__(parent)
        self.user_id: str = data['id']
        self.email: str = data['email']
        self.name: str = data['name']
        self.access_code_digits: int = data['access_code_digits']
        self.access_code_string: str = data['access_code_string']
        self.roles: list = []

        rbac_raw = self._Parent._Configs.get('rbac_user_roles', self.user_id, None, False, ignore_case=True)
        if rbac_raw is None:
            rbac = {}
        else:
            rbac = data_unpickle(rbac_raw, encoder='msgpack_base64')

        # print("rbac user load: %s %s" % (self.user_id, rbac))
        if 'roles' in rbac:
            roles = rbac['roles']
            if len(roles) > 0:
                for role in roles:
                    self.attach_role(role, save=False, flush_cache=False)

        if flush_cache in (None, True):
            self._Parent._Cache.flush(tags=('user', 'role'))

        if 'item_permissions' in rbac:
            self.item_permissions = rbac['item_permissions']
        self.save()

    def has_role(self, role):
        if role.lower() in self.roles:
            return True
        else:
            return False

    def attach_role(self, role_id, save=None, flush_cache=None):
        """
        Add a role to this user

        :param role_label: A role instance, role_id, role machine_label, or role label.
        """
        role = self._Parent.get_role(role_id)
        role_id = role.role_id

        if role_id not in self.roles:
            self.roles.append(role_id)
            if save in (None, True):
                self.save()

        if flush_cache in (None, True):
            self._Parent._Cache.flush('role')

    def unattach_role(self, role_id, save=None, flush_cache=None):
        """
        Remove a role from this user

        :param role_label: A role instance, role_id, role machine_label, or role label.
        """
        role = self._Parent.get_role(role_id)
        role_id = role.role_id

        if role.label == 'admin' and self._Parent.owner_id == self.user_id:
            return

        if role_id in self.roles:
            self.roles.remove(role_id)
            if save in (None, True):
                self.save()
        if flush_cache in (None, True):
            self._Parent._Cache.flush('role')

    def get_roles(self):
        """
        Get a generator for all roles belong to a user.
        """
        for label in self.roles.copy():
            try:
                yield self._Parent.roles[label]
            except KeyError:
                pass

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
        # print("rbac saving user: %s %s" % (self.user_id, tosave))
        self._Parent._Configs.set('rbac_user_roles', self.user_id,
                                  data_pickle(tosave, encoder="msgpack_base64", local=True),
                                  ignore_case=True)

    def __repr__(self):
        return '<User %s>' % self.roles
