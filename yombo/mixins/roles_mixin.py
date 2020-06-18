# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For library documentation, see: `Devices @ Module Development <https://yombo.net/docs/libraries/users>`_

This mixin adds roles to the given class. Typically used for users and authkeys.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.22.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/mixins/roles_mixin.html>`_
"""
import weakref

from yombo.core.log import get_logger
from yombo.utils.caller import caller_string

logger = get_logger("mixins.roles_mixin")


class RolesMixin(object):
    @property
    def roles(self):
        for role_id, role in self._roles.items():
            if role is None:
                del self._roles[role_id]
        return self._roles

    @roles.setter
    def roles(self, val):
        if isinstance(val, dict) is False:
            raise ValueError("Roles must be a dictionary.")
        self._roles = val

    def __init__(self, *args, **kwargs):
        self._roles: dict = {}
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            pass

    def set_roles(self, roles):
        """
        Set roles for this current object. Note: this will remove existing roles.

        :param roles: One or more roles to assign to this object.
        :return:
        """
        if isinstance(roles, list) is False or isinstance(roles, tuple) is False:
            roles = [roles]

        if len(roles) == 0:
            return

        self._roles.clear()
        for role_id in roles:
            self.attach_role(role_id)

    def attach_role(self, role_id):
        """
        Add a role

        :param role_id: A role instance, role_id, role machine_label, or role label.
        """
        role = self._Roles.get(role_id)
        role_id = role.role_id

        if role_id not in self.roles:
            self._roles[role_id] = weakref.ref(role)

    def unattach_role(self, role_id):
        """
        Remove a role

        :param role_id: A role instance, role_id, role machine_label, or role label.
        """
        try:
            role = self._Roles.get(role_id)
            role_id = role.role_id
        except:
            if role_id in self.roles:
                del self._roles[role_id]
            return

        if role.label == "admin" and self._Users.owner_id == self.user_id:
            return

        if role_id in self.roles:
            del self._roles[role_id]

    def has_role(self, role_id):
        try:
            role = self._Roles.get(role_id)
            role_id = role.role_id
        except:
            if role_id in self.roles:
                del self._roles[role_id]
            return False

        if role_id in self.roles:
            return True
        return False
