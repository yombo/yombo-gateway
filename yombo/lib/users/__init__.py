# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Manages users within the gateway. All users are loaded on startup.

.. note::

  * End user documentation: `User permissions @ User Documentation <https://yombo.net/docs/gateway/web_interface/user_permissions>`_
  * End user documentation: `Roles @ User Documentation <https://yombo.net/docs/gateway/web_interface/roles>`_
  * For library documentation, see: `Users @ Library Documentation <https://yombo.net/docs/libraries/users>`_

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/users/__init__.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboNoAccess
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import UserSchema
from yombo.lib.users.user import User
from yombo.lib.users.blankuser import BlankUser
from yombo.lib.users.systemuser import SystemUser
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

logger = get_logger("library.users")


class Users(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Maintains a list of users and what they can do.
    """
    users: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "user_id"
    _storage_label_name: ClassVar[str] = "user"
    _storage_class_reference: ClassVar = User
    _storage_schema: ClassVar = UserSchema()
    _storage_attribute_name: ClassVar[str] = "users"
    _storage_search_fields: ClassVar[List[str]] = [
        "user_id", "email", "name"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "name"
    _storage_attribute_sort_key_order: ClassVar[str] = "asc"

    def _init_(self, **kwargs):
        self.owner_id = self._Configs.get("core.owner_id", None, False)
        self.system_seed = self._Configs.get("core.rand_seed")

        self.owner_user = None

        # Itemized platforms allow specific access to one item within a platfrom. such as a device or automation
        self.system_user = SystemUser(self)
        self.blank_user = BlankUser(self)

    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Start the users library by loading the users.

        :param kwargs:
        :return:
        """
        if self._Loader.operating_mode != "run":
            return

        yield self.load_from_database()

        if self.owner_id is not None:
            self.owner_user = self.get(self.owner_id)
            self.owner_user.attach_role("admin")

    def list_roles_by_user(self):
        """
        All roles and which users belong to them. This takes a bit as it has to iterate all users.

        This is different than list_role_users in that this gets all the roles and the members for each role.

        :return:
        """
        roles = {}
        for email, user in self.users.items():
            for the_role_id, the_role in user.roles.items():
                if the_role_id not in roles:
                    roles[the_role_id] = []
                roles[the_role_id].append(user)
        return roles

    def has_role(self, requested_role_id, auth):
        """
        Checks if a given auth has a role by name or role ID.

        :param requested_role_id:
        :param auth:
        :return:
        """
        requested_role = self._Roles.get(requested_role_id)
        search_id = requested_role.role_id
        roles = auth.roles
        if search_id in roles:
            return True
        for role_id, role in roles.items():
            if role_id == search_id:
                return True
        return False

    # def get_access(self, auth, requested_platform, requested_action):
    #     """
    #     Get list of access end points for a given platform and action.  If the platform isn't itemizable (atoms,
    #     states, etc, then "*" will returned for "items".
    #
    #     Returns two variables:
    #     1) items - (list) list of item ID's, if possible. Or '*" if not itemizable.
    #     2) permissions - (dict) Collective of permissions based on all the combined roles for the given auth.
    #
    #     :return: list of a list and dict.
    #     """
    #     auth = self.validate_auth(auth)
    #
    #     def return_values(final_item_keys, final_permission):
    #         """
    #         Sets the cache content and returns the correctly formatted response
    #         :param final_item_keys:
    #         :param final_permission:
    #         :return:
    #         """
    #         self.get_access_cache[cache_id] = (final_item_keys, final_permission)
    #         return final_item_keys, final_permission
    #
    #     requested_platform = requested_platform.lower()
    #     if requested_platform not in self.auth_platforms:
    #         raise YomboWarning("get_access() requires a valid platform, requested platform not found.")
    #
    #     cache_id = self._Hash.sha256_compact(f"{auth.auth_id}:"
    #                               f"{auth.auth_type}:"
    #                               f"{requested_platform}:"
    #                               f"{requested_action}")
    #     if cache_id in self.get_access_cache:
    #         return self.get_access_cache[cache_id]
    #
    #     out_permissions = self.get_access_permissions(auth, requested_platform, requested_action=requested_action)
    #     # print("* get_access: out_permissions: %s" % out_permissions)
    #     platform_data = self.get_platform_item(requested_platform)
    #     platform_items = platform_data["platform_item"]
    #     platform_label_attr = platform_data["platform_label_attr"]
    #
    #     platform_item_keys = list(platform_items)
    #     # print("* get_access: platform_item_keys: %s" % platform_item_keys)
    #
    #     # Call out specific item access according to the out_permissions table.
    #     out_item_keys = []
    #
    #     if "*" in out_permissions["allow"]:
    #         actions = out_permissions["allow"]["*"]
    #         # print("* actions: %s" % actions)
    #         # print("generating list of keys for ***")
    #         for item, not_used_actions in platform_items.items():
    #             # print("requested action: %s" % requested_action)
    #             if requested_action in actions:
    #                 out_item_keys.append(item)
    #         return return_values(out_item_keys, out_permissions)
    #     else:
    #         # Generate platform keys
    #         platform_labels = {}
    #         # print("generating list of keys...platform_label_attr: %s" % platform_label_attr)
    #         if isinstance(platform_items, dict) and isinstance(platform_label_attr, str):
    #             for temp_id, temp in platform_items.items():
    #                 label = getattr(temp, platform_label_attr)
    #                 platform_labels[label] = temp_id
    #         else:
    #             platform_labels = platform_items
    #
    #         # print("generating list of keys... %s " % list(platform_labels))
    #
    #         for item, actions in out_permissions["allow"].items():
    #             # print("### actions: %s" % actions)
    #             # print("### requested action: %s" % requested_action)
    #             # print("### item: %s" % item)
    #             if requested_action in actions and item in platform_labels:
    #                 out_item_keys.append(platform_labels[item])
    #
    #     # print("### final out items: %s" % out_item_keys)
    #     return return_values(out_item_keys, out_permissions)
    #
    # def get_role(self, requested_role):
    #     """
    #     Get a role instance using a role id, machine_label, or label.
    #
    #     :param requested_role:
    #     :return:
    #     """
    #     if isinstance(requested_role, str):
    #         if requested_role in self.roles:
    #             return self.roles[requested_role]
    #         for role_id, role in self.roles.items():
    #             if role_id == requested_role:
    #                 return role
    #             if role.machine_label == requested_role:
    #                 return role
    #             if role.label == requested_role:
    #                 return role
    #     elif isinstance(requested_role, Role) is True:
    #         return requested_role
    #
    #     raise KeyError(f"Role not found, unknown input type: {type(requested_role)} - {requested_role}")
