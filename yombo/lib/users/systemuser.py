# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Simply base system class to represent a system user.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from time import time
from yombo.mixins.authmixin import AuthMixin
from yombo.mixins.permissionmixin import PermissionMixin
from yombo.mixins.rolesmixin import RolesMixin


class SystemUser(AuthMixin, PermissionMixin, RolesMixin):

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
        return "yombo_system_account"

    @property
    def safe_display(self):
        return "system::yombo_system_acc..."

    @property
    def full_display(self):
        return "system::yombo_system_account"

    @property
    def auth_id(self):
        return "yombo_system_account"

    @auth_id.setter
    def auth_id(self, val):
        return self._auth_id

    @property
    def user_id(self) -> str:
        return "yombo_system_account"

    @property
    def item_permissions(self):
        return {}

    @property
    def roles(self):
        return ['admin']

    # Local
    def __init__(self, parent):
        super().__init__(parent)

        # Auth specific attributes
        self.auth_type = 'system'
        self._auth_id = 'yombo_system_account'
        self.source = "system"
        self.source_type = "library"
        self.gateway_id = None
        self.user = None
        self.name = "Yombo System Account"
        self.email = "yombo@example.com"

    def has_access(self, platform, item, action, raise_error=None):
        """
        Always has access!

        :param platform:
        :param item:
        :param action:
        :param raise_error:
        :raise_error YomboNoAccess:
        :return:
        """
        return True

    def asdict(self):
        cur_time = time()
        return {
            'auth_id': self.auth_id,
            'auth_type': self.auth_type,
            'user_id': self.user_id,
            'last_access_at': cur_time,
            'created_at': cur_time,
            'updated_at': cur_time,
            'auth_data': {},
            'enabled': True,
            'is_dirty': False,
        }