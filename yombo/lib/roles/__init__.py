# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Manages roles within the gateway. Roles are attached to All users are loaded on startup.

.. note::

  * End user documentation: `User permissions @ User Documentation <https://yombo.net/docs/gateway/web_interface/user_permissions>`_
  * End user documentation: `Roles @ User Documentation <https://yombo.net/docs/gateway/web_interface/roles>`_
  * For library documentation, see: `Users @ Library Documentation <https://yombo.net/docs/libraries/users>`_

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/roles/__init__.html>`_
"""
from typing import ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import LOCAL_SOURCES
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.lib.roles.role import Role
from yombo.core.schemas import RoleSchema
from yombo.mixins.auth_mixin import AuthMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.utils.caller import caller_string
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.roles")


class Roles(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Maintains a list of users and what they can do.
    """
    roles: dict = {}

    _storage_primary_field_name: ClassVar[str] = "role_id"
    _storage_attribute_name: ClassVar[str] ="roles"
    _storage_label_name: ClassVar[str] ="role"
    _storage_class_reference: ClassVar = Role
    _storage_schema: ClassVar = RoleSchema()
    _storage_search_fields: ClassVar[List[str]] = ["role_id", "machine_label", "label"]
    _storage_pickled_fields: ClassVar[Dict[str, str]] = {"mqtt_topics": "json"}
    _storage_attribute_sort_key: ClassVar[str] = "machine_label"
    _storage_attribute_sort_key_order: ClassVar[str] = "asc"

    @inlineCallbacks
    def _init_(self, **kwargs):
        self.owner_id = self._Configs.get("core.owner_id", None, False)

        self.system_seed = self._Configs.get("core.rand_seed")
        yield self.load_from_database()
        yield self.setup_system_roles()

    def _load_(self, **kwargs):
        """
        Start the roles library by loading the roles from the yombo.toml file. This also calls the _roles_ hook
        to see if any libraries or modules have any additional roles to add.

        :param kwargs:
        :return:
        """
        results = yield global_invoke_all("_roles_", called_by=self)
        logger.debug("_roles_ results: {results}", results=results)
        for component, roles in results.items():
            for machine_label, role_data in roles.items():
                entity_type = component._Entity_type
                if "load_source" in role_data:
                    load_source = role_data["load_source"]
                    del role_data["source"]
                elif entity_type == "yombo_module":
                    load_source = "local"
                else:
                    load_source = "library"
                role_data["machine_label"] = machine_label
                self.new(role_data,
                         _load_source="local",
                         _authentication=self.AUTH_USER
                         )

        if self._Loader.operating_mode != "run":
            return

    @inlineCallbacks
    def setup_system_roles(self):
        """
        Setup default roles, if they don't exist.
        :return:
        """
        role_id = self._Hash.sha224_compact(f"admin-{self.system_seed}")
        roles = self.roles
        if role_id not in self.roles:
            if role_id not in roles and "admin" not in roles:
                yield self.new(
                    role_id=role_id,
                    machine_label="admin",
                    label="Administrators",
                    description="Full access to everything.",
                    _load_source="local",
                    _authentication=self.AUTH_USER
                )
        role_id = self._Hash.sha224_compact(f"users-{self.system_seed}")
        if role_id not in roles and "users" not in roles:
            yield self.new(
                role_id=role_id,
                machine_label="users",
                label="Users",
                description="All users have this role. Permits basic system operation.",
                _load_source="local",
                _authentication=self.AUTH_USER
            )

    @inlineCallbacks
    def new(self, machine_label: str, label: Optional[str] = None, description: Optional[str] = None,
            mqtt_topics: Optional[Union[List[str], str]] = None, role_id: Optional[str] = None,
            _load_source: Optional[str] = None, _request_context: Optional[str] = None,
            _authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None) -> Role:
        """
        Add a new role to the system.

        To track how the role was created, either request_by and request_by_type or an authentication item
        can be anything with the authmixin, such as a user, websession, or authkey.

        For the MQTT topic, the format is: permission:/topic   The following example grants read, write, and
        subscribe permission to the topic /yombo_set/devices/#
        read,write,subscribe:/yombo_set/devices/#

        :param machine_label: Role machine_label
        :param label: Role human label.
        :param description: Role description.
        :param mqtt_topics: A list of strings, a single string, that denotes which topics the role can perform
        :param role_id: How the role was loaded.
        :param _load_source: Where the data originated from. One of: local, database, yombo, system
        :param _request_context: Context about the request. Such as an IP address of the source.
        :param _authentication: An auth item such as a websession or authkey.
        :return:
        """
        try:
            found = self.get_advanced({"machine_label": machine_label, "role_id": role_id}, multiple=False)
            # print(f"found matching role: {role_id} = {found.role_id}")
            # print(self.roles)
            raise YomboWarning(f"Found a matching role: {found.role_id} - {found.machine_label} - {found.label}")
        except KeyError:
            pass

        _load_source = _load_source or "local"

        try:
            self.get(machine_label)
            raise YomboWarning("Role already exists.")
        except KeyError:
            pass
        if _load_source not in LOCAL_SOURCES:
            raise YomboWarning(f"Add new roles requires a load_source received '{load_source}',"
                               f" must be one of: {', '.join(LOCAL_SOURCES)}")

        if _authentication is None:
            raise YomboWarning("New role must have a valid authentication or request_by and request_by_type.")

        if _request_context is None:
            _request_context = caller_string()  # get the module/class/function name of caller

        mqtt = []
        if isinstance(mqtt_topics, str):
            mqtt_topics = [mqtt_topics]

        if isinstance(mqtt_topics, list):
            for temp_topic in mqtt_topics:
                permissions, topic = temp_topic.split(":")
                for permission in permissions.split(","):
                    if permission not in ("read", "write", "subscribe"):
                        logger.warn("Discarding mqtt_topic for role, invalid permission: '{permission}' - {temp_topic}",
                                    permission=permission, temp_topic=temp_topic)
                    mqtt.append(temp_topic)

        results = yield self.load_an_item_to_memory(
            {
                "id": role_id,
                "machine_label": machine_label,
                "label": label,
                "description": description,
                "mqtt_topics": mqtt
            },
            load_source=_load_source,
            request_context=_request_context if _request_context is not None else caller_string(),
            authentication=_authentication
        )
        return results

    def users(self, requested_role):
        """
        List all users belonging to a role.

        :param requested_role:
        :return:
        """
        role = self.get(requested_role)
        return role.users()

    def auth_keys(self, requested_role):
        """
        List all users belonging to a role.

        :param requested_role:
        :return:
        """
        role = self.get(requested_role)
        return role.auth_keys()

    def roles_by_user(self):
        """
        All roles and which users belong to them. This takes a bit as it has to iterate all users.

        This is different than users() in that this gets all the roles and the members for each role.

        :return:
        """
        if "list_roles_by_user" in self.cache:
            return self.cache["list_roles_by_user"]
        roles = {}
        for email, user in self.users.items():
            for the_role_id, the_role in user.roles.items():
                if the_role_id not in roles:
                    roles[the_role_id] = []
                roles[the_role_id].append(user)
        self.cache["list_roles_by_user"] = roles
        return roles

    # def return_access(self, value, auth, platform, item, action, cache_id=None, raise_error=None):
    #     """
    #     Used by various auth checker methods. Used to log the event and send the final results (bool).
    #
    #     :param value:
    #     :return:
    #     """
    #     auth = self.validate_auth(auth)
    #
    #     if cache_id not in self.has_access_cache:
    #         self.has_access_cache[cache_id] = value
    #
    #     if value is True:
    #         self._Events.new("auth", "accepted", (platform, item, action), auth=auth)
    #         return True
    #
    #     self._Events.new("auth", "denied", (platform, item, action), auth=auth)
    #     if raise_error is not True:
    #         return False
    #     raise YomboNoAccess(item_permissions=auth.item_permissions,
    #                         roles=auth.roles,
    #                         platform=platform,
    #                         item=item,
    #                         action=action)
    #
    # def validate_auth(self, auth):
    #     """
    #     Validates an auth isntance is valid. Accepts anyhthing that has an authmixin.
    #
    #     :param auth:
    #     :return:
    #     """
    #     if isinstance(auth, AuthMixin):
    #         return auth
    #     raise YomboWarning(f"Invalid auth: {type(auth)} - {auth}")
    #
    # def has_access_scan_item_permissions(self, item_permissions, requested_platform, requested_action, platform_item,
    #                                      platform_item_label):
    #     """
    #     Used to check access permissions. Not to collect access permissions.
    #     :param item_permissions:
    #     :param requested_platform:
    #     :param requested_action:
    #     :param platform_item:
    #     :param platform_item_label:
    #     :return:
    #     """
    #     def convert_wildcard(inputs):
    #         for input in inputs:
    #             if input == "*":
    #                 return True
    #         return False
    #     if platform_item is not None:
    #         # print("* scan_item_permissions start: item_permissions %s" % item_permissions)
    #         for effective_platform in (requested_platform, "*"):
    #             if effective_platform not in item_permissions:
    #                 # print("* - scan_item_permissions: effective_platform not found!: %s" % effective_platform)
    #                 continue
    #             for effective_platform_item_label in (platform_item_label, "*"):
    #                 # print("* --- scan_item_permissions: effective_platform_item_label: %s" % effective_platform_item_label)
    #                 for effective_action in (requested_action, "*"):
    #                     # print("* ---- scan_item_permissions: effective_action: %s" % effective_action)
    #                     if "deny" in item_permissions[effective_platform]:
    #                         # print("* ----- scan_item_permissions: checking deny")
    #                         if effective_platform_item_label in item_permissions[effective_platform]["deny"]:
    #                             if effective_action in item_permissions[effective_platform]["deny"][effective_platform_item_label]:
    #                                 return False, convert_wildcard(
    #                                     (effective_platform, effective_platform_item_label, effective_action)
    #                                 )
    #                     if "allow" in item_permissions[effective_platform]:
    #                         # print("* ----- scan_item_permissions: checking allow")
    #                         if effective_platform_item_label in item_permissions[effective_platform]["allow"]:
    #                             if effective_action in item_permissions[effective_platform]["allow"][effective_platform_item_label]:
    #                                 return True, convert_wildcard(
    #                                     (effective_platform, effective_platform_item_label, effective_action)
    #                                 )
    #
    #     return None, None
    #
    # def has_access(self, auth, platform, item, action, raise_error=None):
    #     """
    #     Check if an auth (websession, authkey, system, etc) has access to the requested
    #     platform/item/action combo.
    #
    #     :param auth: Either a websession or authkey
    #     :return: Boolean
    #     """
    #     auth = self.validate_auth(auth)
    #     if raise_error is None:
    #         raise_error = True
    #     platform = platform.lower()
    #     if platform not in self.auth_platforms:
    #         raise YomboWarning(f"Invalid permission platform: {platform}")
    #
    #     action = action.lower()
    #
    #     logger.debug("has_access: platform: {platform}, item: {item}, action: {action}",
    #                  platform=platform, item=item, action=action)
    #     logger.debug("has_access: has roles: {roles}", roles=auth.roles)
    #
    #     cache_id = self._Hash.sha224_compact(f"{json.dumps(auth.item_permissions, sort_keys=True)}:"
    #                               f"{json.dumps(list(auth.roles), sort_keys=True)}:"
    #                               f"{platform}:"
    #                               f"{item}:"
    #                               f"{action}"
    #                               )
    #
    #     if cache_id in self.has_access_cache:
    #         return self.return_access(self.has_access_cache[cache_id], auth, platform, item, action, cache_id,
    #                                   raise_error)
    #
    #     try:
    #         platform_data = self.get_platform_item(platform, item)
    #     except Exception as e:  # Catch things like keyerrors, or whatever error.
    #         logger.info("Access blocked: {e}", e=e)
    #         return self.return_access(False, auth, platform, item, action, cache_id, raise_error)
    #
    #     platform_item = platform_data["platform_item"]
    #     platform_item_label = platform_data["platform_item_label"]
    #     platform_actions = platform_data["platform_actions"]
    #
    #     # logger.debug("has_access: platform_item: {platform_item}, platform_item_id: "
    #     #             "{platform_item_id}, platform_actions: {platform_actions}",
    #     #             platform_item=None, platform_item_id=platform_item_id, platform_actions=platform_actions)
    #
    #     if action not in platform_actions:
    #         raise YomboWarning("Action must be one of: %s" % ", ".join(platform_actions))
    #
    #     # Admins have full access.
    #     if auth.has_role("admin"):
    #         self.has_access_cache[cache_id] = True
    #         return self.return_access(True, auth, platform, item, action, cache_id, raise_error)
    #
    #     temp_result = None
    #
    #     # Check if a specific item has a special access listed
    #     platform_allowed, platform_from_wild = self.has_access_scan_item_permissions(
    #         auth.item_permissions, platform, action, platform_item, platform_item_label)
    #     # print("user item permission results: %s - %s" % (platform_allowed, platform_from_wild))
    #     if isinstance(platform_allowed, bool):
    #         return self.return_access(platform_allowed, auth, platform, item, action, cache_id, raise_error)
    #
    #     for role_id, the_role in auth.roles.items():
    #         item_permissions = the_role.item_permissions
    #         # print("item_permissions: %s" % item_permissions)
    #         if platform_item is not None:
    #             platform_allowed, platform_from_wild = self.has_access_scan_item_permissions(
    #                 item_permissions,
    #                 platform,
    #                 action,
    #                 platform_item,
    #                 platform_item_label,
    #             )
    #             # print("role (%s) item permission results: %s - %s" % (role, platform_allowed, platform_from_wild))
    #             if isinstance(platform_allowed, bool):
    #                 if platform_from_wild is False:
    #                     return self.return_access(platform_allowed, auth, platform, item, action, cache_id, raise_error)
    #                 if temp_result is None or platform_allowed is False:
    #                     temp_result = platform_allowed
    #
    #     if temp_result is None:
    #         temp_result = False
    #     return self.return_access(temp_result, auth, platform, item, action, cache_id, raise_error)
    #
    # def get_access_permissions(self, auth, requested_platform, requested_action=None, requested_item=None, source_type=None):
    #     """
    #     Collects all permissions from across all user item permissions. It
    #     also returns two items: list of permissions, and actions broken down by item.
    #
    #     :param requested_platform:
    #     :param requested_action:
    #     :return:
    #     """
    #     auth = self.validate_auth(auth)
    #     if source_type is None:
    #         source_type = "all"
    #
    #     cache_id = self._Hash.sha224_compact(f"{auth.auth_id}:"
    #                               f"{auth.auth_type}:"
    #                               f"{requested_platform}:"
    #                               f"{requested_action}:"
    #                               f"{source_type}")
    #
    #     if cache_id in self.get_access_permissions_cache:
    #         return self.get_access_permissions_cache[cache_id]
    #
    #     if requested_item is not None:
    #         platform_data = self.get_platform_item(requested_platform, requested_item)
    #         requested_item_label = platform_data["platform_item_label"]
    #
    #     else:
    #         requested_item_label = None
    #
    #     out_permissions = {"allow": {}, "deny": {}}
    #     # print("* get_item_permissions: requested_platform: %s" % requested_platform)
    #     # print("* get_item_permissions: requested_action: %s" % requested_action)
    #     # print(" get_access_permissions source_type: %s" % source_type)
    #
    #     def get_item_permissions(item_permissions):
    #         # print("* > get_item_permissions: item_permissions: %s" % item_permissions)
    #         for effective_platform in (requested_platform, "*"):
    #             if effective_platform not in item_permissions:
    #                 # print("* -- get_item_permissions effective-platform not found: %s" % effective_platform)
    #                 continue
    #             for effective_access, access_data in item_permissions[effective_platform].items():
    #                 for item, actions in item_permissions[effective_platform][effective_access].items():
    #                     if requested_item_label is None or requested_item_label == item:
    #                         # print("* --- get_item_permissions: effective_platform_item_label: %s" % item)
    #                         for action in actions:
    #                             # print("requested_action: %s" % requested_action)
    #                             # print("action: %s" % action)
    #                             if requested_action is None or requested_action == action:
    #                                 effective_action = action
    #                             elif action == "*":
    #                                 effective_action = requested_action
    #                             else:
    #                                 continue
    #
    #                             # print("* ---- get_item_permissions: effective_action: %s" % effective_action)
    #                             if effective_access not in out_permissions:
    #                                 # print("building out_permission_actions..  Adding access.")
    #                                 out_permissions[effective_access] = {}
    #                             if item not in out_permissions[effective_access]:
    #                                 # print("building out_permission_actions..  Adding item.")
    #                                 out_permissions[effective_access][item] = []
    #                             if effective_action not in out_permissions[effective_access][item]:
    #                                     # print("building out_permission_actions..  Adding action.")
    #                                     out_permissions[effective_access][item].append(effective_action)
    #
    #                             if effective_access == "deny":
    #                                 if "allow" in out_permissions:
    #                                     if item in out_permissions["allow"]:
    #                                         if effective_action in out_permissions["allow"][item]:
    #                                             out_permissions["allow"][item].remove(effective_action)
    #                                         if len(out_permissions["allow"][item]) == 0:
    #                                             del out_permissions["allow"][item]
    #                                     if len(out_permissions["allow"]) == 0:
    #                                         del out_permissions["allow"]
    #                             if effective_access == "allow":
    #                                 if "deny" in out_permissions:
    #                                     if item in out_permissions["deny"]:
    #                                         if effective_action in out_permissions["deny"][item]:
    #                                             out_permissions["deny"][item].remove(effective_action)
    #                                         if len(out_permissions["deny"][item]) == 0:
    #                                             del out_permissions["deny"][item]
    #                                     if len(out_permissions["deny"]) == 0:
    #                                         del out_permissions["deny"]
    #
    #     # go thru all roles and setup base items
    #     # print("get_access_permissions in roles- source_type: %s" % source_type)
    #     if source_type in ("all", "roles"):
    #         for role_id, role in auth.roles.items():
    #             # print("get_access_permissions for role: %s" % role.label)
    #
    #             get_item_permissions(role.item_permissions)
    #         # print("out_permissions after ROLE scan: %s" % out_permissions)
    #     # Add user item permissions last, it has the highest priority and will change the roles item permissions.
    #     if source_type in ("all", "user"):
    #         # print("get_access_permissions in user")
    #         get_item_permissions(auth.item_permissions)
    #
    #     self.get_access_permissions_cache[cache_id] = out_permissions
    #     return out_permissions
    #
    # def get_user_access_permissions(self, requested_platform, requested_item, source_type):
    #     """
    #     Like get_access_permissions, but it's output includes the email or role_id and is a simple list
    #     of entries.
    #
    #     :param requested_platform:
    #     :param requested_action:
    #     :param source_type: One of "user" or "role"
    #     :return:
    #     """
    #
    #     cache_id = self._Hash.sha224_compact("{requested_platform}:"
    #                               "{requested_item}:"
    #                               "{source_type}")
    #
    #     if cache_id in self.get_access_access_permissions_cache:
    #         return self.get_access_access_permissions_cache[cache_id]
    #
    #     platform_data = self.get_platform_item(requested_platform, requested_item)
    #     requested_item_label = platform_data["platform_item_label"]
    #     out_permissions = []
    #
    #     def get_item_permissions(item_permissions, auth):
    #         for effective_platform in (requested_platform, "*"):
    #             if effective_platform not in item_permissions:
    #                 continue
    #             for effective_access, access_data in item_permissions[effective_platform].items():
    #                 if requested_item_label not in item_permissions[effective_platform][effective_access]:
    #                     continue
    #                 actions = item_permissions[effective_platform][effective_access][requested_item_label]
    #                 for action in actions:
    #                     out_permissions.append(
    #                         {
    #                             "auth": auth,
    #                             "access": effective_access,
    #                             "action": action,
    #                         }
    #                     )
    #
    #     # go thru all roles and setup base items
    #     if source_type in ("roles", "role"):
    #         # print("get_access_permissions in roles- source_type: %s" % source_type)
    #         for role_id, role in self.roles.items():
    #             # print("* -> get_access: role_machine_label: %s" % role_machine_label)
    #             get_item_permissions(role.item_permissions, role)
    #             # print("out_permissions after ROLE scan: %s" % out_permissions)
    #     # Add user item permissions last, it has the highest priority and will change the roles item permissions.
    #
    #     if source_type in ("users", "user"):
    #         for email, the_user in self.users.items():
    #             get_item_permissions(the_user.item_permissions, the_user)
    #
    #     self.get_access_access_permissions_cache[cache_id] = out_permissions
    #     return out_permissions
    #
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
    #     cache_id = self._Hash.sha224_compact(f"{auth.auth_id}:"
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
