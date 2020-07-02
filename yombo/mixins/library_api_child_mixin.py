"""
Adds ability to first send all new/update/delete requests to API.Yombo.Net first, then it will



@inlineCallbacks
api_update(data):
  send to api.yombo.com
  if success, update locally
  on fail return fail.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/mixins/library_db_child_attributes_mixin.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Union

from twisted.internet.defer import inlineCallbacks, maybeDeferred

# Import Yombo libraries
from yombo.core.log import get_logger

logger = get_logger("mixins.library_api_child_mixin")


class LibraryAPIChildMixin:
    @inlineCallbacks
    def api_update(self, data):
        """
        Alternative to update() found in library_db_child_mixin. This first tries to update the data at API.Yombo.net
        before updating locally.  After API.Yombo is updated, this method will call update() to complete locally.

        Reasoning: The update() method is not deferred friendly. Update() will eventaully complete the same tasks, but
        provides no status back on completed failed.

        :param data:
        :return:
        """
        results = yield self._YomboAPI.update(request_type=self._Parent._storage_attribute_name,
                                              data=self.to_database(),
                                              url_format={"id": self._primary_field_id},
                                              )
        return results

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
