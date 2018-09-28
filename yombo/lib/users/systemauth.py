# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Simply base system class to represent a system user.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from time import time


class SystemAuth(object):

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
    def auth_id(self):
        return "system"

    @auth_id.setter
    def auth_id(self, val):
        return

    @property
    def user_id(self) -> str:
        return "system"

    @property
    def item_permissions(self):
        return {}

    @property
    def roles(self):
        return ['admin']

    @property
    def auth_type(self):
        return 'system'

    def has_access(self, platform, item, action, raise_error=None):
        """
        Check if api auth has access  to a resource / access_type combination.

        :param platform:
        :param item:
        :param action:
        :param raise_error:
        :raise_error YomboNoAccess:
        :return:
        """
        return self._Parent._Users.has_access(
            self.user.item_permissions, self.user.roles, platform, item, action, raise_error,
            self.auth_id, self.auth_type)

    def asdict(self):
        cur_time = time()
        return {
            'auth_id': self.auth_id,
            'gateway_id': None,
            'session_id': None,
            'last_access': cur_time,
            'created_at': cur_time,
            'updated_at': cur_time,
            'session_data': {},
            'is_valid': True,
            'is_dirty': False,
        }