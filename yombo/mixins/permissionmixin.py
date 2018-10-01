# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For library documentation, see: `Devices @ Module Development <https://yombo.net/docs/libraries/users>`_

Mixin class that adds permission handling. Used in things like users and roles objects within the user
library.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.yombobasemixin import YomboBaseMixin

logger = get_logger('mixins.permissionmixin')


class PermissionMixin(YomboBaseMixin):
    @property
    def item_permissions(self):
        return self._item_permissions

    @item_permissions.setter
    def item_permissions(self, val):
        self._item_permissions = val

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._item_permissions: dict = {}  # {'device': {'allow': {'view': {'garage_door': True}}}}

    def add_item_permission(self, platform, item, access, actions, save=None, flush_cache=None):
        """
        Adds an item permission.

        :param platform: 'device', 'scene', 'automation', etc.
        :param item: Item ID to reference. Device id, scene id, etc. Or * for wildcard.
        :param access: Either 'allow' or 'deny'.
        :param actions: A string or list/tuple of strings. edit, delete, view, control...  Or * for wildcard.
        """
        platform = platform.lower()
        if item != "*":
            item = self._Parent._Validate.id_string(item)
        access = access.lower()
        if isinstance(actions, str):
            actions = [actions]
        [x.lower() for x in actions]  # make all actions lower case

        # print("add item platform: %s" % platform)
        if platform not in self._Parent.auth_platforms:
            # print("auth platforms:")
            # print(self._Parent.auth_platforms)
            raise YomboWarning("Invalid permission platform: %s" % platform)

        if access not in ('allow', 'deny'):
            raise YomboWarning("Access must be allow or deny.")

        # print("add_item_permission: get_platform_item: %s, %s" % (platform, item))
        platform_data = self._Parent.get_platform_item(platform, item)
        platform_item_label = platform_data['platform_item_label']
        platform_actions = platform_data['platform_actions']

        if platform not in self.item_permissions:
            self.item_permissions[platform] = {}

        if access not in self.item_permissions[platform]:
            self.item_permissions[platform][access] = {}

        # print("add item permission platform: %s" % platform)
        for action in actions:
            # print("add item permission action: %s" % action)
            # print("add item permission platform_actions:")
            # print(platform_actions)
            try:
                if action not in platform_actions and action != '*' and platform != '*':
                    raise YomboWarning('Action must be one of: %s' % ", ".join(platform_actions))
                if platform_item_label not in self.item_permissions[platform][access]:
                    self.item_permissions[platform][access][platform_item_label] = []
                if action not in self.item_permissions[platform][access][platform_item_label]:
                    self.item_permissions[platform][access][platform_item_label].append(action)
            except YomboWarning as e:
                logger.warn("Skipping adding action '{action}': {reason}", action=action, reason=e)

        # Now remove any opposing access item. For example, if just added allow, remove any
        # matching deny.

        if access == 'allow':
            remove_access = 'deny'
        else:
            remove_access = 'allow'

        for action in actions:
            if remove_access not in self.item_permissions[platform]:
                continue
            if platform_item_label not in self.item_permissions[platform][remove_access]:
                continue
            if action in self.item_permissions[platform][remove_access][platform_item_label]:
                self.item_permissions[platform][remove_access][platform_item_label].remove(action)
        if flush_cache in (None, True):
            self._Parent._Cache.flush(tags=('user', 'role'))
        if save in (None, True):
            self.save()

    def remove_item_permission(self, platform, item, access=None, actions=None, save=None, flush_cache=None):
        """
        Remove item specific permissions from a user.

        :param platform: 'device', 'scene', 'automation', etc.
        :param item: Item ID to reference. Device id, scene id, etc. Or * for wildcard.
        :param access: Either 'allow' or 'deny'.
        :param actions: A string or list/tuple of strings. edit, delete, view, control...  Or * for wildcard.
        """
        platform = platform.lower()
        if item != "*":
            item = self._Parent._Validate.id_string(item)
        if access is not None or actions is not None:
            access = access.lower()
            if access not in ('allow', 'deny'):
                raise YomboWarning("Access must be allow or deny.")

            if isinstance(actions, str):
                actions = [actions]
            [x.lower() for x in actions]  # make all actions lower case

        if platform not in self._Parent.auth_platforms:
            raise YomboWarning("Invalid permission platform.")

        platform_data = self._Parent.get_platform_item(platform, item)
        platform_item_label = platform_data['platform_item_label']
        platform_actions = platform_data['platform_actions']

        if platform not in self.item_permissions:
            return


        print("remove item: platform: %s" % platform)
        print("remove item: item: %s" % item)
        print("remove item: access: %s" % access)
        print("remove item: actions: %s" % actions)
        if access is None:
            try:
                del self.item_permissions[platform]['allow'][platform_item_label]
            except:
                pass
            try:
                del self.item_permissions[platform]['deny'][platform_item_label]
            except:
                pass
            return

        if access not in self.item_permissions[platform]:
            return

        if platform_item_label not in self.item_permissions[platform][access]:
            return

        for action in actions:
            if action != "*" and action not in platform_actions:
                raise YomboWarning("Invalid action.")

            if action in self.item_permissions[platform][access][platform_item_label]:
                self.item_permissions[platform][access][platform_item_label].remove(action)

        if len(self.item_permissions[platform][access][platform_item_label]) == 0:
            del self.item_permissions[platform][access][platform_item_label]

        if flush_cache in (None, True):
            self._Parent._Cache.flush(tags=('user', 'role'))

        if save in (None, True):
            self.save()
