"""
Many components within the Yombo Framework have a user identity associated with it. This allows changes and other
requests to be tracked internally.

This user can be used for libraries and modules as well as other entities that need this capability.

For the entities, the authentication 'user' is located in self.AUTH_USER

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/users/componentuser.html>`_
"""
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from yombo.constants import AUTH_TYPE_USER
from yombo.core.entity import Entity
from yombo.mixins.auth_mixin import AuthMixin
from yombo.mixins.permission_mixin import PermissionMixin
from yombo.mixins.roles_mixin import RolesMixin


class ComponentUser(Entity, AuthMixin, PermissionMixin, RolesMixin):
    """ This user is assigned to libraries and modules so that actions be controlled by the user. """

    _Entity_type: ClassVar[str] = "ModuleUser"
    _Entity_label_attribute: ClassVar[str] = "machine_label"

    def __contains__(self, data_requested):
        return False

    def __getitem__(self, data_requested):
        return None

    def __setitem__(self, data_requested, value):
        return

    def __delitem__(self, data_requested):
        return

    def keys(self):
        return []

    @property
    def accessor_id(self):
        """ Return either the  """
        return f"{self.component_type}:{self.component_name}"

    @property
    def accessor_type(self):
        return self.component_label

    @property
    def auth_id(self):
        """ Return the ID of the auth class. """
        return self.component_label

    @auth_id.setter
    def auth_id(self, val):
        return

    @property
    def display(self):
        return self.component_label

    @property
    def safe_display(self):
        return self.component_label

    @property
    def full_display(self):
        return f"Module Authentication - {self.component_name}"

    @property
    def auth_id(self):
        return self.component_label

    @auth_id.setter
    def auth_id(self, val):
        return

    @property
    def user_id(self) -> str:
        return self.component_label

    @property
    def item_permissions(self):
        return {}

    @property
    def roles(self):
        return [f"{self.component_label}"]

    @roles.setter
    def roles(self, val):
        return

    @property
    def gateway_id(self) -> str:
        return self._gateway_id

    def __init__(self, parent, component_type, component_name):
        self.last_access_at = int(time())
        self.created_at = int(time())
        self.updated_at = int(time())
        self.auth_data = {}
        self.component_type = component_type
        self.component_name = component_name
        self.component_label = f"{self.component_type}:{self.component_name}"  # Exchange memory for less CPU load

        super().__init__(parent)

        # Auth specific attributes
        self.auth_type = AUTH_TYPE_USER
        self.auth_id = "yombo_blank_account"
        self.source = "system"
        self.source_type = "library"
        self.user = None
        self.name = "Yombo System Blank Account"
        self.email = "yombo@example.com"

    def is_allowed(self, platform, action, item_id: Optional[str] = None, raise_error: Optional[bool] = None):
        """
        Always has access!

        :param action:
        :param platform:
        :param item_id:
        :return:
        """
        if self._gateway_id == "local":
            return True
        else:
            return False
