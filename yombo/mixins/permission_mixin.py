# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For library documentation, see: `Devices @ Module Development <https://yombo.net/docs/libraries/users>`_

Mixin class that adds permission handling. Used in things like users and roles objects within the user
library.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.22.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/mixins/permission_mixin.html>`_
"""
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("mixins.permission_mixin")


class PermissionMixin(object):
    def is_allowed(self, platform, action, item_id):
        """
        Checks if the given item can perform an action.

        :param action: Usually one of: get, edit, add, delete, view
        :param platform: An auth platform from: yombo.constants.permissions
        :param item_id:
        :return:
        """
        return self._Roles.is_allowed(platform, action, item_id, self)
