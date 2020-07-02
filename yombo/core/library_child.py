"""

.. note::

  For more information see: `Library Core @ Module Development <https://yombo.net/docs/core/library>`_

Used by library child, such as an individual command, crontask, state.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/library.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning


class YomboLibraryChild(Entity):
    """
    For use in individual library children, such as in a command, atom, category.
    Define a basic class that setup basic library class variables.

    This is the only class where the Entity class won't fully populate this class.
    """
    _Entity_type: str = "library_child"

    def check_authorization(self, authentication: Union[None, Type["yombo.mixins.auth_mixin.AuthMixin"]],
                            action: str, required: Optional[bool] = None):
        """
        Checks the authentication item if it's authorized for the requested action. Authentication item must
        have the AuthMixin included, such as a websession or authkey.

        :param authentication: An auth item such as a websession or authkey.
        :param action: The action being requested, such as "create", "modify", "view", etc.
        :param required: If authentication is required. Default is currently False, but will become True in v0.25
        :return:
        """
        if authentication is None:
            if required is True:
                raise YomboWarning("Authorization missing, but it required. Error: lcca-97158")
            else:
                return False
        return authentication.is_allowed(self._Parent.AUTH_TYPE, self._Parent.AUTH_PLATFORM, action)
