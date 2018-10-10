# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For library documentation, see: `Devices @ Module Development <https://yombo.net/docs/libraries/users>`_

Mixin class to support roles for users, authkeys, etc.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.22.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from time import time
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.yombobasemixin import YomboBaseMixin

logger = get_logger('mixins.rolesmixin')


class RolesMixin(YomboBaseMixin):
    @property
    def roles(self):
        return self._roles

    @roles.setter
    def roles(self, val):
        self._roles = val

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.available_roles: dict = self._Parent._Users.roles
        self._roles: dict = {}

    def set_roles(self, roles, save=None, flush_cache=None):
        """
        Set roles for this current object. Note: this will remove existing roles.

        :param roles: One or more roles to assign to this object.
        :param save: If should save updates, default is True.
        :param flush_cache: If should flush role caches when done. Normally used during load only.

        :param roles:
        :param save:
        :param flush_cache:
        :return:
        """
        if isinstance(roles, list) is False or isinstance(roles, tuple) is False:
            roles = [roles]

        if len(roles) == 0:
            return

        self.roles.clear()
        for role_id in roles:
            self.attach_role(role_id, save=False, flush_cache=False)

        if flush_cache in (None, True):
            self._Parent._Cache.flush('role')
        if save in (None, True):
            self.save()

    def attach_role(self, role_id, save=None, flush_cache=None):
        """
        Add a role

        :param role_id: A role instance, role_id, role machine_label, or role label.
        :param save: If should save updates, default is True.
        :param flush_cache: If should flush role caches when done. Normally used during load only.
        """
        role = self._Parent._Users.get_role(role_id)
        role_id = role.role_id

        if role_id not in self.roles:
            self.roles[role_id] = role

            if flush_cache in (None, True):
                self._Parent._Cache.flush('role')
            if hasattr(self, 'is_dirty'):
                self.is_dirty += 10
            if save in (None, True):
                self.save()

    def unattach_role(self, role_id, save=None, flush_cache=None):
        """
        Remove a role

        :param role_id: A role instance, role_id, role machine_label, or role label.
        :param save: If should save updates, default is True.
        :param flush_cache: If should flush role caches when done. Normally used during load only.
        """
        role = self._Parent._Users.get_role(role_id)
        role_id = role.role_id

        if role.label == 'admin' and self._Parent.owner_id == self.user_id:
            return

        if role_id in self.roles:
            del self.roles[role_id]
            if flush_cache in (None, True):
                self._Parent._Cache.flush('role')
            if hasattr(self, 'is_dirty'):
                self.is_dirty += 50
            if save in (None, True):
                self.save()

    def has_role(self, requested_role_id):
        return self._Parent._Users.has_role(requested_role_id, self)

    def save(self):
        pass
