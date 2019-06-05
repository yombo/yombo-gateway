"""
A class to represent a user.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from yombo.core.entity import Entity
from yombo.constants import AUTH_TYPE_USER
from yombo.core.log import get_logger
from yombo.mixins.auth_mixin import AuthMixin
from yombo.mixins.permission_mixin import PermissionMixin
from yombo.mixins.roles_mixin import RolesMixin
from yombo.utils import data_pickle, data_unpickle

logger = get_logger("library.users.user")


class User(Entity, AuthMixin, PermissionMixin, RolesMixin):
    """
    User class to manage role membership, etc.
    """
    @property
    def user_id(self):
        return self._user_id

    @property
    def display(self):
        return f"{self.name} <{self.email}>"

    def __str__(self):
        return f"{self.name} <{self.email}>"

    def __init__(self, parent, data=object, flush_cache=None):
        """
        Setup a new user instance.

        :param parent: A reference to the users library.
        """
        super().__init__(parent)

        self.auth_type = AUTH_TYPE_USER

        # Auth specific attributes

        # Local attributes
        self._row_id: str = data.id
        self._user_id: str = data.user_id
        self.email: str = data.email
        self.name: str = data.name
        self.access_code_digits: int = data.access_code_digits
        self.access_code_string: str = data.access_code_string

        # Load roles and item permissions.
        rbac_raw = self._Parent._Configs.get("rbac_user_roles", self.user_id, None, False, ignore_case=True)
        if rbac_raw is None:
            rbac = {}
        else:
            rbac = data_unpickle(rbac_raw, encoder="msgpack_base64")

        if "roles" in rbac:
            roles = rbac["roles"]
            if len(roles) > 0:
                for role in roles:
                    try:
                        self.attach_role(role, save=False, flush_cache=False)
                    except KeyError:
                        logger.warn("Cannot find role for user, removing from user: {role}", role=role)
                        # Don't have to actually do anything, it won't be added, so it can't be saved. :-)

        if flush_cache in (None, True):
            self._Parent._Cache.flush(tags=("user", "role"))

        if "item_permissions" in rbac:
            self.item_permissions = rbac["item_permissions"]
        self.save()

    def has_access(self, platform, item, action, raise_error=None):
        """
        Check if user has access  to a resource / access_type combination.

        :param platform:
        :param item:
        :param action:
        :param raise_error:
        :return:
        """
        return self._Parent.has_access(self, self.item_permissions, self.roles, platform, item, action, raise_error)

    def save_to_database(self):
        """
        Updates the information in the database for the user.
        :return:
        """
        yield self._Parent._LocalDB.update_user(self)

    def save(self):
        """
        Save the user roles and permissions.

        :return:
        """
        tosave = {
            "roles": list(self.roles),
            "item_permissions": self.item_permissions
        }
        self._Parent._Configs.set("rbac_user_roles", self.user_id,
                                  data_pickle(tosave, encoder="msgpack_base64", local=True),
                                  ignore_case=True)

    def __repr__(self):
        return f"<User {self._user_id}>"
