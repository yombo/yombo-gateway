"""
A class to represent a user.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/users/user.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from yombo.core.entity import Entity
from yombo.constants import AUTH_TYPE_USER
from yombo.core.log import get_logger
from yombo.mixins.auth_mixin import AuthMixin
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.permission_mixin import PermissionMixin
from yombo.mixins.roles_mixin import RolesMixin

logger = get_logger("library.users.user")


class User(Entity, LibraryDBChildMixin, AuthMixin, PermissionMixin, RolesMixin):
    """
    An individual gateway user. Handles various aspects User class to manage role membership, etc.
    """
    _Entity_type: ClassVar[str] = "User"
    _Entity_label_attribute: ClassVar[str] = "machine_label"

    @property
    def display(self):
        return f"{self.name} <{self.email}>"

    def __str__(self):
        return f"User: {self.name} <{self.email}>"

    def load_attribute_values_pre_process(self, incoming: dict) -> None:
        # Local attributes
        self.auth_type: str = AUTH_TYPE_USER
        self.auth_id: str = incoming["user_id"]
        self.email: str = incoming["email"]
        self.name: str = incoming["name"]
        self.access_code_string: str = incoming["access_code_string"]

        # Load roles and item permissions.
        rbac_raw = self._Parent._Configs.get(f"rbac_user_roles.{self.user_id}", None, False, ignore_case=True)
        if rbac_raw is None:
            rbac = {}
        else:
            rbac = self._Tools.data_unpickle(rbac_raw, content_type="msgpack_base64")

        if "roles" in rbac:
            roles = rbac["roles"]
            if len(roles) > 0:
                for role in roles:
                    try:
                        self.attach_role(role)
                    except KeyError:
                        logger.warn("Cannot find role for user {user}, removing role: {role}",
                                    user=self.auth_id, role=role)
                        # Don't have to actually do anything, it won't be added, so it can't be saved. :-)

    def __repr__(self):
        return f"<User {self.user_id}>"
