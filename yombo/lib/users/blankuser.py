# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
A blank user used during bootstrapping of the gateway. Only used when the gateway is being first being installed
or during re-configuration.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/users/blankuser.html>`_
"""
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from yombo.constants import AUTH_TYPE_USER
from yombo.core.entity import Entity
from yombo.mixins.auth_mixin import AuthMixin
from yombo.mixins.permission_mixin import PermissionMixin
from yombo.mixins.roles_mixin import RolesMixin


class BlankUser(Entity, AuthMixin, PermissionMixin, RolesMixin):
    """ User placeholder when bootstrapping the gateway. """

    _Entity_type: ClassVar[str] = "BlankUser"
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
    def display(self):
        return "yombo_blank_user"

    @property
    def safe_display(self):
        return "system::yombo_blank_acc..."

    @property
    def full_display(self):
        return "system::yombo_blank_account"

    @property
    def auth_id(self):
        return "yombo_blank_account"

    @auth_id.setter
    def auth_id(self, val):
        return "yombo_blank_account"

    @property
    def user_id(self) -> str:
        return "yombo_blank_account"

    @property
    def item_permissions(self):
        return {}

    @property
    def roles(self):
        return ["admin"]

    @roles.setter
    def roles(self, val):
        return

    @property
    def gateway_id(self) -> str:
        return self._gateway_id

    def __init__(self, parent):
        self.last_access_at = int(time())
        self.created_at = int(time())
        self.updated_at = int(time())
        self.auth_data = {}
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
