# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Mixin class that add setters and getters for various attributes. This allows processing common attribute
names.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/mixins/library_db_child_attributes_mixin.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Union

# Import Yombo libraries
from yombo.core.log import get_logger

logger = get_logger("mixins.library_db_parent_processors_mixin")


class LibraryDBChildAttributesMixin:
    def _get_roles_attribute(self, data=None, **kwargs) -> list:
        """
        Returns a list of roles based on the current classes self.roles value.

        :return: A list to represent the roles.
        """
        results = []
        if data is not None:
            roles = data
        else:
            roles = self.roles
        for role_id, role in roles.items():
            results.append(role_id)
        return results

    def _set_roles_attribute(self, value: Union[str, list], return_value: Optional[bool] = None) -> dict:
        """
        Accepts roles as either a list of role ids, or a single role is as a string.

        :return: A dictionary to represent the roles.
        """
        results = []
        if value is not None:
            if isinstance(value, list) is False:
                value = [value]
            if len(value) > 0:
                for role in value:
                    if return_value is True:
                        results.append(role)
                    else:
                        try:
                            self.attach_role(role)
                        except KeyError as e:
                            logger.warn("Cannot find role for authkey {auth_id}, role: {role} - {e}",
                                        auth_id=self.auth_id, role=role, e=e)
            return results
