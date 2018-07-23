"""
A class to represent a user.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""

from yombo.lib.users.role import Role
from yombo.utils.decorators import memoize_ttl


class User(object):
    """
    User class to manage role membership, etc.
    """

    def __init__(self, parent, data={}, roles=[]):
        """
        Setup a new user instance.

        :param parent: A reference to the users library.
        """
        self.user_id: str = data['id']
        self.email: str = data['email']
        self.name: str = data['name']
        self.access_code_digits: int = data['access_code_digits']
        self.access_code_string: str = data['access_code_string']
        self.roles: list = []
        self._Parent = parent
        if len(roles) > 0:
            for a_role in roles:
                if isinstance(a_role, Role):
                    machine_label = a_role.machine_label
                else:
                    role = self._Parent.get_role(a_role)
                    machine_label = role.machine_label
                if machine_label is not None:
                    self.roles.append(machine_label)

    def add_role(self, role_label, source=None):
        """
        Simply add a role to this user

        :param role_label: A role instance, role_id, role machine_label, or role label.
        """
        if isinstance(role_label, Role):
            machine_label = role_label.machine_label
        else:
            role = self._Parent.get_role(role_label)
            machine_label = role.machine_label

        edited = False
        if machine_label not in self.roles:
            edited = True
            self.roles.append(machine_label)
        if edited and source != 'db':
            self.sync_roles_to_db()

    def get_roles(self):
        """
        Get a generator for all roles belong to a user.
        """
        for label in self.roles.copy():
            try:
                yield self._Parent.roles[label]
            except KeyError:
                pass

    def remove_role(self, role_label, source=None):
        """
        Remove role that is assigned to a user.

        :param role_label: name of the role which needs to be removed
        """
        if role_label == 'admin' and self._Parent.owner_id == self.user_id:
            return
        if isinstance(role_label, Role) is False:
            role = role_label
            machine_label = role_label.machine_label
        else:
            role = self._Parent.get_role(role_label)
            machine_label = role.machine_label

        edited = False
        for role in self.get_roles():
            if role.get_name() == machine_label:
                self.roles.remove(role)
                edited = True
                break

        if edited and source != 'db':
            self.sync_roles_to_db()

    @memoize_ttl(60)
    def has_access(self, path, action):
        """
        Check if user has access  to a resource / access_type combination.

        :param access_type:
        :param resource:
        :return:
        """
        return self._Parent.has_access(self, self.roles, path, action)

    def sync_roles_to_db(self):
        self._Parent._LocalDB.save_user_roles(self)

    def __repr__(self):
        return '<User %s>' % self.roles
