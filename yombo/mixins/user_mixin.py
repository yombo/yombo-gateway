# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For library documentation, see: `Devices @ Module Development <https://yombo.net/docs/libraries/users>`_

Mixin class to represent users.

THIS MIXIN MUST BE LISTED BEFORE AUTHMIXIN!

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.22.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/mixins/user_mixin.html>`_
"""
from yombo.core.log import get_logger
from yombo.mixins.roles_mixin import RolesMixin

logger = get_logger("mixins.user_mixin")


class UserMixin(RolesMixin):
    @property
    def display(self):
        return f"{self.user.name} <{self.user.email}>"

    @property
    def has_user(self) -> str:
        if self.user is None:
            return False
        return True

    @property
    def roles(self):
        return self.user.roles

    @roles.setter
    def roles(self, val):
        self.user.roles = val

    @property
    def user_id(self):
        if self.user is None:
            return None
        return self.user.user_id

    @property
    def name(self):
        if self.user is None:
            return None
        return self.user.name

    @property
    def email(self):
        if self.user is None:
            return None
        return self.user.email

    @property
    def safe_email(self):
        if self.user is None:
            return None
        u = self._email.split("@")
        return u[0] + "@" + u[1][0:4] + "..."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__["user"] = None

    def has_role(self, requested_role_id):
        return self._Parent._Users.has_role(requested_role_id, self)
