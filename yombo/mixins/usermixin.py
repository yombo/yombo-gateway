# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For library documentation, see: `Devices @ Module Development <https://yombo.net/docs/libraries/users>`_

Mixin class to represent users.

THIS MIXIN MUST BE LISTED BEFORE AUTHMIXIN!

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.22.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from time import time
from yombo.core.log import get_logger
from yombo.mixins.yombobasemixin import YomboBaseMixin


from yombo.core.exceptions import YomboWarning
from yombo.mixins.rolesmixin import RolesMixin

logger = get_logger("mixins.usermixin")


class UserMixin(RolesMixin, YomboBaseMixin):

    @property
    def display(self):
        return f"{self._user.name} <{self._user.email}>"

    @property
    def has_user(self) -> str:
        if self._user is None:
            return False
        return True

    @property
    def item_permissions(self):
        return self._user._item_permissions

    # @item_permissions.setter
    # def item_permissions(self, val):
    #     self._user._item_permissions = val

    @property
    def roles(self):
        return self._user._roles

    # @item_permissions.setter
    # def item_permissions(self, val):
    #     self._user._item_permissions = val

    @property
    def user(self):
        return self._user

    @property
    def user_id(self):
        if self._user is None:
            return None
        return self._user.user_id

    @property
    def name(self):
        if self._user is None:
            return None
        return self._user.name

    @property
    def email(self):
        if self._user is None:
            return None
        return self._user.email

    @property
    def safe_email(self):
        if self._user is None:
            return None
        u = self._email.split("@")
        return u[0] + "@" + u[1][0:4] + "..."

    @user.setter
    def user(self, val):
        self._user = val

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._user = None

    def has_role(self, requested_role_id):
        return self._Parent._Users.has_role(requested_role_id, self)
