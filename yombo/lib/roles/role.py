"""
Handles role functions.

Resource syntax:

* URI/URL: web:/api/v1/some_resource/here
* A method within the gateway: ygw:library.states.some_function
* MQTT: mqtt:/some/topic/or/another

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>z
.. versionadded:: 0.20.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/roles/role.html>`_
"""
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.permission_mixin import PermissionMixin

logger = get_logger("library.roles.role")


class Role(Entity, LibraryDBChildMixin, PermissionMixin):
    """
    Roles are associated to permissions. Users are added to roles. Resources are protected by permissions.
    """
    _Entity_type: ClassVar[str] = "Role"
    _Entity_label_attribute: ClassVar[str] = "machine_label"

    @property
    def members(self):
        """
        Returns the label of the current role.
        """
        return {
            "users": self.users(),
            "auth_keys": self.auth_keys(),
        }

    @property
    def auth_keys(self):
        """
        Returns a list of auth_keys this role belongs to.
        """
        return self._Parent.list_role_auth_keys(self)

    @property
    def users(self):
        """
        Returns the label of the current role.
        """
        return self._Parent.list_role_users(self)

    @property
    def auth_id(self):
        """ Used to simulate an authentication item for permissions. """
        return self.role_id

    @property
    def auth_type(self):
        """ Used to simulate an authentication item for permissions. """
        return "role"

    def __init__(self, parent, **kwargs):
        """
        Setup the role.

        :param parent: A reference to the users library.
        """
        super().__init__(parent, **kwargs)

    def load_attribute_values_pre_process(self, incoming):
        """ Setup basic class attributes based on incoming data. """
        # print(f"role pre process: {incoming}")
        if "label" not in incoming or incoming["label"] is None:
            incoming["label"] = incoming["machine_label"]
        if "description" not in incoming or incoming["description"] is None:
            incoming["description"] = incoming["label"]

        search_dict = {"role_id": incoming["role_id"], "machine_label": incoming["machine_label"]}
        try:
            found = self._Parent.get_advanced(search_dict, multiple=False)
            print(f"found a matching role: {type(found)} - {found}")
            # raise YomboWarning(f"Found a matching role: ")
            raise YomboWarning(f"Found a matching role: {found.machine_label} - {found.label}")
        except KeyError:
            pass
# 79qd9VkRHgZt39yzwdSqrQ7BD7PC06ZTZSUI54
        if "created_at" not in incoming or incoming["created_at"] is None:
            incoming["created_at"] = int(time())
        if "updated_at" not in incoming or incoming["updated_at"] is None:
            incoming["updated_at"] = int(time())

    def users(self):
        """
        List all users belonging to the current role.

        :return:
        """
        role_users = []
        for email, user in self._Users.users.items():
            if self.role_id in user.roles:
                role_users.append(user)
        return role_users

    def auth_keys(self):
        """
        List all auth_keys that have this role.

        :return:
        """
        authkeys = []
        for auth_id, auth_key in self._AuthKeys.items():
            if self.role_id in auth_key.roles:
                authkeys.append(auth_key)
        return authkeys
