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

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from copy import deepcopy
import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants.users import *
from yombo.core.exceptions import YomboWarning, YomboNoAccess
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.lib.users.role import Role
from yombo.lib.users.user import User
from yombo.lib.users.systemuser import SystemUser
from yombo.mixins.authmixin import AuthMixin
from yombo.utils import global_invoke_all, data_unpickle, sha256_compact, random_string

logger = get_logger("library.users")


class Users(YomboLibrary):
    """
    Maintains a list of users and what they can do.
    """
    def __contains__(self, user_requested):
        """
        Checks to if a provided user exists.

            >>> if "mitch@example" in self._Users:
            >>>    print("mitch@example.com is able to login.")

        :raises YomboWarning: Raised when request is malformed.
        :param user_requested: The user key to search for.
        :type user_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(user_requested)
            return True
        except Exception as e:
            return False

    def __getitem__(self, user_requested):
        """
        Attempts to find the user requested.

            >>> user_mitch = self._Users["mitch@example.com"]

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param user_requested: The user key to search for.
        :type user_requested: string
        :return: The value assigned to the user.
        :rtype: mixed
        """
        return self.get(user_requested)

    def __setitem__(self, user_requested, value):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, user_requested):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter users. """
        return self.users.__iter__()

    def __len__(self):
        """
        Returns an int of the number of users defined.

        :return: The number of users defined.
        :rtype: int
        """
        return len(self.users)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo users library"

    def keys(self, gateway_id=None):
        """
        Returns the keys of the users that are defined.

        :return: A list of users defined.
        :rtype: list
        """
        return self.users.keys()

    def items(self, gateway_id=None):
        """
        Gets a list of tuples representing the users defined.

        :return: A list of tuples.
        :rtype: list
        """
        return self.users.items()

    def values(self):
        """
        Gets a list of user values
        :return: list
        """
        return self.users.values()

    def _init_(self, **kwargs):
        self.roles: dict = {}
        self.users: dict = {}
        self.gateway_id = self._Configs.get("core", "gwid", "local", False)
        self.owner_id = self._Configs.get("core", "owner_id", None, False)
        self.owner_user = None
        self.auth_platforms = deepcopy(AUTH_PLATFORMS)  # Possible platforms

        # make sure there"s defaults as needed.
        for auth, data in self.auth_platforms.items():
            if "items_callback" not in data:
                data["items_callback"] = None
            if "item_callback" not in data:
                data["item_callback"] = None
            if "item_id_callback" not in data:
                data["item_id_callback"] = None
            if "item_label_callback" not in data:
                data["item_label_callback"] = None
            if "label_attr" not in data:
                data["label_attr"] = None

        # Itemized platforms allow specific access to one item within a platfrom. such as a device or automation
        self.itemized_auth_platforms = deepcopy(ITEMIZED_AUTH_PLATFORMS)
        self.system_user = SystemUser(self)
        self.cache = self._Cache.ttl(name="lib.users.cache", ttl=86400, tags=("role", "user"))
        self.get_access_cache = self._Cache.ttl(name="lib.users.get_access_cache", ttl=86400, tags=("role", "user"))
        self.get_access_permissions_cache = self._Cache.ttl(name="lib.users.get_access_permissions_cache", ttl=86400, tags=("role", "user"))
        self.get_access_access_permissions_cache = self._Cache.ttl(name="lib.users.get_access_permissions_cache", ttl=21600, tags=("role", "user"))
        self.has_access_cache = self._Cache.ttl(name="lib.users.has_access_cache", ttl=43200, tags=("role", "user"))  # 12hrs

    def _load_(self, **kwargs):
        """
        Calls the _roles_ hook to all components to add system level roles.
        :param kwargs:
        :return:
        """
        self.load_roles()

    @inlineCallbacks
    def _start_(self, **kwargs):
        results = yield global_invoke_all("_auth_platforms_", called_by=self)
        logger.debug("_auth_platforms_ results: {results}", results=results)
        for component, platforms in results.items():
            for machine_label, platform_data in platforms.items():
                if "actions" not in platform_data:
                    logger.warn("Unable to add auth platform, actions is missing: {data}", data=platform_data)
                    continue
                if "items_callback" not in platform_data:
                    platform_data["items_callback"] = None
                if "item_callback" not in platform_data:
                    platform_data["item_callback"] = None
                if "item_id_callback" not in platform_data:
                    platform_data["item_id_callback"] = None
                if "item_label_callback" not in platform_data:
                    platform_data["item_label_callback"] = None
                if "label_attr" not in platform_data:
                    platform_data["label_attr"] = None
                self.auth_platforms[machine_label] = platform_data

        results = yield global_invoke_all("_roles_", called_by=self)
        logger.debug("_roles_ results: {results}", results=results)
        for component, roles in results.items():
            for machine_label, role_data in roles.items():
                if "label" not in role_data:
                    role_data["label"] = machine_label
                if "description" not in role_data:
                    role_data["description"] = role_data["label"]
                if "permissions" not in role_data:
                    role_data["permissions"] = []
                else:
                    if isinstance(role_data["permissions"], list) is False:
                        logger.warn("Cannot add role, permissions must be a list. Role: {machine_label}",
                                    machine_label=machine_label)
                        continue
                role_data["machine_label"] = machine_label
                entity_type = component._Entity_type
                if entity_type == "yombo_module":
                    source = "module"
                else:
                    source = "system"
                self.add_role(role_data, source=source, flush_cache=False)

        yield self.load_users()
        if self.owner_id is not None:
            self.owner_user = self.get(self.owner_id)
            self.owner_user.attach_role("admin")

    def load_roles(self):
        for machine_label, role_data in SYSTEM_ROLES.items():
            role_data["machine_label"] = machine_label
            self.add_role(role_data, source="system", flush_cache=False)
        self._Cache.flush(tags=("user", "role"))

        rbac_roles = self._Configs.get("rbac_roles", "*", {}, False, ignore_case=True)
        for role_id, role_data_raw in rbac_roles.items():
            role_data = data_unpickle(role_data_raw, encoder="msgpack_base64")
            self.add_role(role_data, source="user", flush_cache=False)
        self._Cache.flush(tags=("user", "role"))

    @inlineCallbacks
    def load_users(self):
        db_users = yield self._LocalDB.get_users()

        for user in db_users:
            self.users[user.email] = User(self, user.__dict__, flush_cache=False)

    @inlineCallbacks
    def api_search_user(self, requested_user, session=None):
        """
        Search for user using the Yombo API. Must supply a user_id or user email address. If found returns
        a dictionary with the keys of: "id", "name", and "email".

        :param requested_user: The email address to search for.
        :param session: Session to use, if available.
        :return:
        """
        try:
            search_results = yield self._YomboAPI.request("GET",
                                                          f"/v1/user/{requested_user}",
                                                          None,
                                                          session)
        except YomboWarning as e:
            raise YomboWarning("User not found: %s" % requested_user)
        return search_results["data"]

    @inlineCallbacks
    def add_user(self, requested_user_id, session=None, flush_cache=None):
        """
        Adds a new user to the system using the user's id. The user id  can be found using
        :py:meth:`api_search_user() <api_search_user>`.

        This function will make a call the the Yombo API to add the user, if successful, adds
        the user to memory as well. The database isn't updated, it will be updated on next reboot
        when it pulls configs from the servers.

        :param requested_user:
        :return:
        """
        data = {
            "user_id": requested_user_id,
        }
        try:
            add_results = yield self._YomboAPI.request("POST",
                                                       f"/v1/gateway/{self.gateway_id}/user",
                                                       data,
                                                       session)
        except YomboWarning as e:
            raise YomboWarning("Could not add user to gateway: {e.message[0]}",
                               html_message=f"Could not add user to gateway: { e.html_message}",
                               details=e.details)

        add_results["data"]["id"] = add_results["data"]["user_id"]
        self.users[add_results["data"]["email"]] = User(self, add_results["data"])
        if flush_cache in (None, True):
            self._Cache.flush("user")

        # self.users[add_results["data"]["email"]].sync_user_to_db()

    @inlineCallbacks
    def remove_user(self, requested_user_id, session=None, flush_cache=None):
        """
        Adds a new user to the system using the user's id. The user id  can be found using
        :py:meth:`api_search_user() <api_search_user>`.

        This function will make a call the the Yombo API to add the user, if successful, adds
        the user to memory as well. The database isn't updated, it will be updated on next reboot
        when it pulls configs from the servers.

        :param requested_user:
        :return:
        """
        try:
            yield self._YomboAPI.request("DELETE",
                                         f"/v1/gateway/{self.gateway_id}/user/{requested_user_id}",
                                         session=session)
        except YomboWarning as e:
            raise YomboWarning(f"Could not remove user from gateway: {e.message[0]}",
                               html_message=f"Could not remove user from gateway: {e.html_message}",
                               details=e.details)

        user = self.get(requested_user_id)
        if user.email in self.users:
            del self.users[user.email]
        if flush_cache in (None, True):
            self._Cache.flush('user')

    def add_role(self, data, source=None, flush_cache=None):
        """
        Add a new possible role to the system.

        :param data:
        :return:
        """
        if source not in ("system", "user", "module"):
            raise YomboWarning("Add_role requires a source to be: system, user, or module.")

        machine_label = data["machine_label"]
        if machine_label in self.roles:
            raise YomboWarning("Role already exists.")
        if "label" not in data:
            data["label"] = machine_label
        if "role_id" not in data:
            data["role_id"] = random_string(length=15)
        if "description" not in data:
            data["description"] = machine_label
        if "permissions" not in data:
            data["permissions"] = []
        if "saved_permissions" not in data:
            data["saved_permissions"] = None
        self.roles[data["role_id"]] = Role(self,
                                           machine_label=machine_label,
                                           label=data["label"],
                                           description=data["description"],
                                           source=source,
                                           role_id=data["role_id"],
                                           permissions=data["permissions"],
                                           saved_permissions=data["saved_permissions"],
                                           flush_cache=flush_cache
                                           )
        if flush_cache in (None, True):
            self._Cache.flush("role")
        return self.roles[data["role_id"]]

    def list_role_members(self, requested_role):
        """
        List all users belonging to a role.

        :param requested_role:
        :return:
        """
        role = self.get_role(requested_role)
        return {
            "users": self.list_role_users(role),
            "auth_keys": self.list_role_auth_keys(role),
        }

    def list_role_users(self, requested_role):
        """
        List all users belonging to a role.

        :param requested_role:
        :return:
        """
        role_users = []
        the_role = self.get_role(requested_role)

        cache_id = f"list_role_users::{the_role.role_id}"
        if cache_id in self.cache:
            return self.cache[cache_id]

        role_id = the_role.role_id
        for email, the_user in self.users.items():
            if role_id in the_user.roles:
                role_users.append(the_user)
        self.cache[cache_id] = role_users

        return role_users

    def list_role_auth_keys(self, requested_role):
        """
        List all users belonging to a role.

        :param requested_role:
        :return:
        """
        role_authkeys = []
        the_role = self.get_role(requested_role)

        for auth_id, auth_key in self._AuthKeys.items():
            if the_role.role_id in auth_key.roles:
                role_authkeys.append(auth_key)
        return role_authkeys

    def list_roles_by_user(self):
        """
        All roles and which users belong to them. This takes a bit as it has to iterate all users.

        This is different than list_role_users in that this gets all the roles and the members for each role.

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

    def has_role(self, requested_role_id, auth):
        """
        Checks if a given auth has a role by name or role ID.

        :param requested_role_id:
        :param auth:
        :return:
        """
        requested_role = self.get_role(requested_role_id)
        search_id = requested_role.role_id
        roles = auth.roles
        if search_id in roles:
            return True
        for role_id, role in roles.items():
            if role_id == search_id:
                return True
        return False

    def get_platform_item(self, platform, item=None):
        """
        Gets a platform item (device, automation, scene, etc). If an item is provided, it will
        search for that specific item.

        :param platform:
        :param item:
        :return:
        """
        platform_label_attr = None
        if platform == AUTH_PLATFORM_ATOM:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_ATOM]["actions"]
            platform_items = self._Atoms.atoms
        elif platform == AUTH_PLATFORM_AUTHKEY:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_AUTHKEY]["actions"]
            platform_items = self._AuthKeys.authkeys
            platform_label_attr = "label"
        elif platform == AUTH_PLATFORM_AUTOMATION:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_AUTOMATION]["actions"]
            platform_items = self._Automation.rules
            platform_label_attr = "machine_label"
        elif platform == AUTH_PLATFORM_DEVICE:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_DEVICE]["actions"]
            platform_items = self._Devices.devices
            platform_label_attr = "machine_label"
        elif platform == AUTH_PLATFORM_DEVICE_COMMAND:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_DEVICE_COMMAND]["actions"]
            platform_items = self._Devices.device_commands
            platform_label_attr = "machine_label"
        elif platform == AUTH_PLATFORM_EVENTS:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_EVENTS]["actions"]
            platform_items = {}
        elif platform == AUTH_PLATFORM_GATEWAY:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_GATEWAY]["actions"]
            platform_items = self._Gateways.gateways
            platform_label_attr = "label"
        elif platform == AUTH_PLATFORM_LOCATION:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_LOCATION]["actions"]
            platform_items = self._Locations.locations
            platform_label_attr = "machine_label"
        elif platform == AUTH_PLATFORM_INTENT:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_INTENT]["actions"]
            platform_items = self._Intents.intents
            platform_label_attr = "intent_id"
        elif platform == AUTH_PLATFORM_MODULE:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_MODULE]["actions"]
            platform_items = self._Modules.modules
            platform_label_attr = "machine_label"
        elif platform == AUTH_PLATFORM_NOTIFICATION:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_NOTIFICATION]["actions"]
            platform_items = self._Notifications.notifications
            platform_label_attr = "notification_id"
        elif platform == AUTH_PLATFORM_PANEL:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_PANEL]["actions"]
            platform_items = {}
        elif platform == AUTH_PLATFORM_ROLE:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_ROLE]["actions"]
            platform_items = self._Users.roles
            platform_label_attr = "machine_label"
        elif platform == AUTH_PLATFORM_SCENE:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_SCENE]["actions"]
            platform_items = self._Scenes.scenes
            platform_label_attr = "machine_label"
        elif platform == AUTH_PLATFORM_STATE:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_STATE]["actions"]
            platform_items = self._States.states
        elif platform == AUTH_PLATFORM_STATISTIC:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_STATISTIC]["actions"]
            platform_items = {}
        elif platform == AUTH_PLATFORM_SYSTEM_SETTING:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_SYSTEM_SETTING]["actions"]
            platform_items = {}
        elif platform == AUTH_PLATFORM_SYSTEM_OPTION:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_SYSTEM_OPTION]["actions"]
            platform_items = {}
        elif platform == AUTH_PLATFORM_USER:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_USER]["actions"]
            platform_items = self._Users.users
            platform_label_attr = "email"
        elif platform == AUTH_PLATFORM_WEBLOGS:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_WEBLOGS]["actions"]
            platform_items = {}
        elif platform == AUTH_PLATFORM_WILDCARD:
            platform_actions = self.auth_platforms[AUTH_PLATFORM_WILDCARD]["actions"]
            platform_items = {}
        else:
            platform_actions = ()
            platform_items = {}
            if platform in self.auth_platforms:
                platform_actions = self.auth_platforms[platform]["actions"]
                if self.auth_platforms[platform]["items_callback"] is not None:
                    platform_items = self.auth_platforms[platform]["items_callback"]()
        if item in ("*", None):
            return {
                "platform_item": platform_items,
                "platform_item_id": "*",
                "platform_item_label": "*",
                "platform_actions": platform_actions,
                "platform_label_attr": platform_label_attr,
            }

        if platform == AUTH_PLATFORM_ATOM:
            platform_item = self._Atoms.get(item, full=True)
            platform_item_id = item
            platform_item_label = item
        elif platform == AUTH_PLATFORM_AUTHKEY:
            platform_item = self._AuthKeys.get(item)
            platform_item_id = platform_item.auth_id
            platform_item_label = platform_item.label
            platform_label_attr = "label"
        elif platform == AUTH_PLATFORM_AUTOMATION:
            platform_item = self._Automation.get(item)
            platform_item_id = item
            platform_item_label = platform_item.machine_label
            platform_label_attr = "machine_label"
        elif platform == AUTH_PLATFORM_CRONTAB:
            platform_item = self._CronTab.get(item)
            platform_item_id = platform_item.cron_id
            platform_item_label = platform_item.label
            platform_label_attr = "label"
        elif platform == AUTH_PLATFORM_DEVICE:
            platform_item = self._Devices.get(item)
            platform_item_id = platform_item.device_id
            platform_item_label = platform_item.machine_label
            platform_label_attr = "machine_label"
        elif platform == AUTH_PLATFORM_DEVICE_COMMAND:
            platform_item = self._Devices.device_commands[item]
            platform_item_id = platform_item.command_id
            platform_item_label = platform_item.label
            platform_label_attr = "label"
        elif platform == AUTH_PLATFORM_EVENTS:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        elif platform == AUTH_PLATFORM_GATEWAY:
            platform_item = self._Gateways.get(item)
            platform_item_id = platform_item.gateway_id
            platform_item_label = platform_item.label
            platform_label_attr = "label"
        elif platform == AUTH_PLATFORM_INTENT:
            platform_item = self._Intents.get(item)
            platform_item_id = platform_item.intent_id
            platform_item_label = platform_item.intent_id
            platform_label_attr = "intent_id"
        elif platform == AUTH_PLATFORM_LOCATION:
            platform_item = self._Locations.get(item)
            platform_item_id = platform_item.scene_id
            platform_item_label = platform_item.machine_label
            platform_label_attr = "machine_label"
        elif platform == AUTH_PLATFORM_MODULE:
            platform_item = self._Modules.get(item)
            platform_item_id = platform_item._module_id
            platform_item_label = platform_item._machine_label
            platform_label_attr = "machine_label"
        elif platform == AUTH_PLATFORM_NOTIFICATION:
            platform_item = self._Notifications.get(item)
            platform_item_id = platform_item.notification_id
            platform_item_label = platform_item.notification_id
            platform_label_attr = "notification_id"
        elif platform == AUTH_PLATFORM_PANEL:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        elif platform == AUTH_PLATFORM_ROLE:
            platform_item = self._Users.roles[item]
            platform_item_id = platform_item.role_id
            platform_item_label = platform_item.machine_label
            platform_label_attr = "machine_label"
        elif platform == AUTH_PLATFORM_SCENE:
            platform_item = self._Scenes.get(item)
            platform_item_id = platform_item.scene_id
            platform_item_label = platform_item.machine_label
            platform_label_attr = "machine_label"
        elif platform == AUTH_PLATFORM_STATE:
            platform_item = self._States.get(item)
            platform_item_id = item
            platform_item_label = None
        elif platform == AUTH_PLATFORM_STATISTIC:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        elif platform == AUTH_PLATFORM_SYSTEM_SETTING:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        elif platform == AUTH_PLATFORM_SYSTEM_OPTION:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        elif platform == AUTH_PLATFORM_USER:
            platform_item = self._Users.get(item)
            platform_item_id = platform_item.user_id
            platform_item_label = platform_item.email
            platform_label_attr = "email"
        elif platform == AUTH_PLATFORM_WEBLOGS:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        elif platform == AUTH_PLATFORM_WILDCARD:
            platform_item = None
            platform_item_id = None
            platform_item_label = None
        else:
            platform_actions = []
            platform_item = None
            platform_item_id = None
            platform_item_label = None
            if platform in self.auth_platforms:
                platform_actions = self.auth_platforms[platform]["actions"]
                if self.auth_platforms[platform]["item_callback"] is not None:
                    platform_item = self.auth_platforms[platform]["item_callback"](item)
                if self.auth_platforms[platform]["item_id_callback"] is not None:
                    platform_item_id = self.auth_platforms[platform]["item_id_callback"](item)
                if self.auth_platforms[platform]["item_label_callback"] is not None:
                    platform_item_label = self.auth_platforms[platform]["item_label_callback"](item)
                if self.auth_platforms[platform]["label_attr"] is not None:
                    platform_label_attr = self.auth_platforms[platform]["label_attr"](item)

        return {
            "platform_item": platform_item,
            "platform_item_id": platform_item_id,
            "platform_item_label": platform_item_label,
            "platform_actions": platform_actions,
            "platform_label_attr": platform_label_attr,
        }

    def return_access(self, value, auth, platform, item, action, cache_id=None, raise_error=None):
        """
        Used by various auth checker methods. Used to log the event and send the final results (bool).

        :param value:
        :return:
        """
        auth = self.validate_auth(auth)

        if cache_id not in self.has_access_cache:
            self.has_access_cache[cache_id] = value

        if value is True:
            self._Events.new("auth", "accepted", (platform, item, action), auth=auth)
            return True

        self._Events.new("auth", "denied", (platform, item, action), auth=auth)
        if raise_error is not True:
            return False
        raise YomboNoAccess(item_permissions=auth.item_permissions,
                            roles=auth.roles,
                            platform=platform,
                            item=item,
                            action=action)

    def validate_auth(self, auth):
        """
        Validates an auth isntance is valid. Accepts anyhthing that has an authmixin.

        :param auth:
        :return:
        """
        if isinstance(auth, AuthMixin):
            return auth
        raise YomboWarning(f"Invalid auth: {type(auth)} - {auth}")

    def has_access_scan_item_permissions(self, item_permissions, requested_platform, requested_action, platform_item,
                                         platform_item_label):
        """
        Used to check access permissions. Not to collect access permissions.
        :param item_permissions:
        :param requested_platform:
        :param requested_action:
        :param platform_item:
        :param platform_item_label:
        :return:
        """
        def convert_wildcard(inputs):
            for input in inputs:
                if input == "*":
                    return True
            return False
        if platform_item is not None:
            # print("* scan_item_permissions start: item_permissions %s" % item_permissions)
            for effective_platform in (requested_platform, "*"):
                if effective_platform not in item_permissions:
                    # print("* - scan_item_permissions: effective_platform not found!: %s" % effective_platform)
                    continue
                for effective_platform_item_label in (platform_item_label, "*"):
                    # print("* --- scan_item_permissions: effective_platform_item_label: %s" % effective_platform_item_label)
                    for effective_action in (requested_action, "*"):
                        # print("* ---- scan_item_permissions: effective_action: %s" % effective_action)
                        if "deny" in item_permissions[effective_platform]:
                            # print("* ----- scan_item_permissions: checking deny")
                            if effective_platform_item_label in item_permissions[effective_platform]["deny"]:
                                if effective_action in item_permissions[effective_platform]["deny"][effective_platform_item_label]:
                                    return False, convert_wildcard(
                                        (effective_platform, effective_platform_item_label, effective_action)
                                    )
                        if "allow" in item_permissions[effective_platform]:
                            # print("* ----- scan_item_permissions: checking allow")
                            if effective_platform_item_label in item_permissions[effective_platform]["allow"]:
                                if effective_action in item_permissions[effective_platform]["allow"][effective_platform_item_label]:
                                    return True, convert_wildcard(
                                        (effective_platform, effective_platform_item_label, effective_action)
                                    )

        return None, None

    def has_access(self, auth, platform, item, action, raise_error=None):
        """
        Check if an auth (websession, authkey, system, etc) has access to the requested
        platform/item/action combo.

        :param auth: Either a websession or authkey
        :return: Boolean
        """
        auth = self.validate_auth(auth)
        if raise_error is None:
            raise_error = True
        platform = platform.lower()
        if platform not in self.auth_platforms:
            raise YomboWarning(f"Invalid permission platform: {platform}")

        action = action.lower()

        logger.debug("has_access: platform: {platform}, item: {item}, action: {action}",
                     platform=platform, item=item, action=action)
        logger.debug("has_access: has roles: {roles}", roles=auth.roles)

        cache_id = sha256_compact(f"{json.dumps(auth.item_permissions, sort_keys=True)}:"
                                  f"{json.dumps(list(auth.roles), sort_keys=True)}:"
                                  f"{platform}:"
                                  f"{item}:"
                                  f"{action}"
                                  )

        if cache_id in self.has_access_cache:
            return self.return_access(self.has_access_cache[cache_id], auth, platform, item, action, cache_id,
                                      raise_error)

        try:
            platform_data = self.get_platform_item(platform, item)
        except Exception as e:  # Catch things like keyerrors, or whatever error.
            logger.info("Access blocked: {e}", e=e)
            return self.return_access(False, auth, platform, item, action, cache_id, raise_error)

        platform_item = platform_data["platform_item"]
        platform_item_label = platform_data["platform_item_label"]
        platform_actions = platform_data["platform_actions"]

        # logger.debug("has_access: platform_item: {platform_item}, platform_item_id: "
        #             "{platform_item_id}, platform_actions: {platform_actions}",
        #             platform_item=None, platform_item_id=platform_item_id, platform_actions=platform_actions)

        if action not in platform_actions:
            raise YomboWarning("Action must be one of: %s" % ", ".join(platform_actions))

        # Admins have full access.
        if auth.has_role("admin"):
            self.has_access_cache[cache_id] = True
            return self.return_access(True, auth, platform, item, action, cache_id, raise_error)

        temp_result = None

        # Check if a specific item has a special access listed
        platform_allowed, platform_from_wild = self.has_access_scan_item_permissions(
            auth.item_permissions, platform, action, platform_item, platform_item_label)
        # print("user item permission results: %s - %s" % (platform_allowed, platform_from_wild))
        if isinstance(platform_allowed, bool):
            return self.return_access(platform_allowed, auth, platform, item, action, cache_id, raise_error)

        for role_id, the_role in auth.roles.items():
            item_permissions = the_role.item_permissions
            # print("item_permissions: %s" % item_permissions)
            if platform_item is not None:
                platform_allowed, platform_from_wild = self.has_access_scan_item_permissions(
                    item_permissions,
                    platform,
                    action,
                    platform_item,
                    platform_item_label,
                )
                # print("role (%s) item permission results: %s - %s" % (role, platform_allowed, platform_from_wild))
                if isinstance(platform_allowed, bool):
                    if platform_from_wild is False:
                        return self.return_access(platform_allowed, auth, platform, item, action, cache_id, raise_error)
                    if temp_result is None or platform_allowed is False:
                        temp_result = platform_allowed

        if temp_result is None:
            temp_result = False
        return self.return_access(temp_result, auth, platform, item, action, cache_id, raise_error)

    def get_access_permissions(self, auth, requested_platform, requested_action=None, requested_item=None, source_type=None):
        """
        Collects all permissions from across all user item permissions. It
        also returns two items: list of permissions, and actions broken down by item.

        :param requested_platform:
        :param requested_action:
        :return:
        """
        auth = self.validate_auth(auth)
        if source_type is None:
            source_type = "all"

        cache_id = sha256_compact(f"{auth.auth_id}:"
                                  f"{auth.auth_type}:"
                                  f"{requested_platform}:"
                                  f"{requested_action}:"
                                  f"{source_type}")

        if cache_id in self.get_access_permissions_cache:
            return self.get_access_permissions_cache[cache_id]

        if requested_item is not None:
            platform_data = self.get_platform_item(requested_platform, requested_item)
            requested_item_label = platform_data["platform_item_label"]

        else:
            requested_item_label = None

        out_permissions = {"allow": {}, "deny": {}}
        # print("* get_item_permissions: requested_platform: %s" % requested_platform)
        # print("* get_item_permissions: requested_action: %s" % requested_action)
        # print(" get_access_permissions source_type: %s" % source_type)

        def get_item_permissions(item_permissions):
            # print("* > get_item_permissions: item_permissions: %s" % item_permissions)
            for effective_platform in (requested_platform, "*"):
                if effective_platform not in item_permissions:
                    # print("* -- get_item_permissions effective-platform not found: %s" % effective_platform)
                    continue
                for effective_access, access_data in item_permissions[effective_platform].items():
                    for item, actions in item_permissions[effective_platform][effective_access].items():
                        if requested_item_label is None or requested_item_label == item:
                            # print("* --- get_item_permissions: effective_platform_item_label: %s" % item)
                            for action in actions:
                                # print("requested_action: %s" % requested_action)
                                # print("action: %s" % action)
                                if requested_action is None or requested_action == action:
                                    effective_action = action
                                elif action == "*":
                                    effective_action = requested_action
                                else:
                                    continue

                                # print("* ---- get_item_permissions: effective_action: %s" % effective_action)
                                if effective_access not in out_permissions:
                                    # print("building out_permission_actions..  Adding access.")
                                    out_permissions[effective_access] = {}
                                if item not in out_permissions[effective_access]:
                                    # print("building out_permission_actions..  Adding item.")
                                    out_permissions[effective_access][item] = []
                                if effective_action not in out_permissions[effective_access][item]:
                                        # print("building out_permission_actions..  Adding action.")
                                        out_permissions[effective_access][item].append(effective_action)

                                if effective_access == "deny":
                                    if "allow" in out_permissions:
                                        if item in out_permissions["allow"]:
                                            if effective_action in out_permissions["allow"][item]:
                                                out_permissions["allow"][item].remove(effective_action)
                                            if len(out_permissions["allow"][item]) == 0:
                                                del out_permissions["allow"][item]
                                        if len(out_permissions["allow"]) == 0:
                                            del out_permissions["allow"]
                                if effective_access == "allow":
                                    if "deny" in out_permissions:
                                        if item in out_permissions["deny"]:
                                            if effective_action in out_permissions["deny"][item]:
                                                out_permissions["deny"][item].remove(effective_action)
                                            if len(out_permissions["deny"][item]) == 0:
                                                del out_permissions["deny"][item]
                                        if len(out_permissions["deny"]) == 0:
                                            del out_permissions["deny"]

        # go thru all roles and setup base items
        # print("get_access_permissions in roles- source_type: %s" % source_type)
        if source_type in ("all", "roles"):
            for role_id, role in auth.roles.items():
                # print("get_access_permissions for role: %s" % role.label)

                get_item_permissions(role.item_permissions)
            # print("out_permissions after ROLE scan: %s" % out_permissions)
        # Add user item permissions last, it has the highest priority and will change the roles item permissions.
        if source_type in ("all", "user"):
            # print("get_access_permissions in user")
            get_item_permissions(auth.item_permissions)

        self.get_access_permissions_cache[cache_id] = out_permissions
        return out_permissions

    def get_user_access_permissions(self, requested_platform, requested_item, source_type):
        """
        Like get_access_permissions, but it's output includes the email or role_id and is a simple list
        of entries.

        :param requested_platform:
        :param requested_action:
        :param source_type: One of "user" or "role"
        :return:
        """

        cache_id = sha256_compact("{requested_platform}:"
                                  "{requested_item}:"
                                  "{source_type}")

        if cache_id in self.get_access_access_permissions_cache:
            return self.get_access_access_permissions_cache[cache_id]

        platform_data = self.get_platform_item(requested_platform, requested_item)
        requested_item_label = platform_data["platform_item_label"]
        out_permissions = []

        def get_item_permissions(item_permissions, auth):
            for effective_platform in (requested_platform, "*"):
                if effective_platform not in item_permissions:
                    continue
                for effective_access, access_data in item_permissions[effective_platform].items():
                    if requested_item_label not in item_permissions[effective_platform][effective_access]:
                        continue
                    actions = item_permissions[effective_platform][effective_access][requested_item_label]
                    for action in actions:
                        out_permissions.append(
                            {
                                "auth": auth,
                                "access": effective_access,
                                "action": action,
                            }
                        )

        # go thru all roles and setup base items
        if source_type in ("roles", "role"):
            # print("get_access_permissions in roles- source_type: %s" % source_type)
            for role_id, role in self.roles.items():
                # print("* -> get_access: role_machine_label: %s" % role_machine_label)
                get_item_permissions(role.item_permissions, role)
                # print("out_permissions after ROLE scan: %s" % out_permissions)
        # Add user item permissions last, it has the highest priority and will change the roles item permissions.

        if source_type in ("users", "user"):
            for email, the_user in self.users.items():
                get_item_permissions(the_user.item_permissions, the_user)

        self.get_access_access_permissions_cache[cache_id] = out_permissions
        return out_permissions

    def get_access(self, auth, requested_platform, requested_action):
        """
        Get list of access end points for a given platform and action.  If the platform isn't itemizable (atoms,
        states, etc, then "*" will returned for "items".

        Returns two variables:
        1) items - (list) list of item ID's, if possible. Or '*" if not itemizable.
        2) permissions - (dict) Collective of permissions based on all the combined roles for the given auth.

        :return: list of a list and dict.
        """
        auth = self.validate_auth(auth)

        def return_values(final_item_keys, final_permission):
            """
            Sets the cache content and returns the correctly formatted response
            :param final_item_keys:
            :param final_permission:
            :return:
            """
            self.get_access_cache[cache_id] = (final_item_keys, final_permission)
            return final_item_keys, final_permission

        requested_platform = requested_platform.lower()
        if requested_platform not in self.auth_platforms:
            raise YomboWarning("get_access() requires a valid platform, requested platform not found.")

        cache_id = sha256_compact(f"{auth.auth_id}:"
                                  f"{auth.auth_type}:"
                                  f"{requested_platform}:"
                                  f"{requested_action}")
        if cache_id in self.get_access_cache:
            return self.get_access_cache[cache_id]

        out_permissions = self.get_access_permissions(auth, requested_platform, requested_action=requested_action)
        # print("* get_access: out_permissions: %s" % out_permissions)
        platform_data = self.get_platform_item(requested_platform)
        platform_items = platform_data["platform_item"]
        platform_label_attr = platform_data["platform_label_attr"]

        platform_item_keys = list(platform_items)
        # print("* get_access: platform_item_keys: %s" % platform_item_keys)

        # Call out specific item access according to the out_permissions table.
        out_item_keys = []

        if "*" in out_permissions["allow"]:
            actions = out_permissions["allow"]["*"]
            # print("* actions: %s" % actions)
            # print("generating list of keys for ***")
            for item, not_used_actions in platform_items.items():
                # print("requested action: %s" % requested_action)
                if requested_action in actions:
                    out_item_keys.append(item)
            return return_values(out_item_keys, out_permissions)
        else:
            # Generate platform keys
            platform_labels = {}
            # print("generating list of keys...platform_label_attr: %s" % platform_label_attr)
            if isinstance(platform_items, dict) and isinstance(platform_label_attr, str):
                for temp_id, temp in platform_items.items():
                    label = getattr(temp, platform_label_attr)
                    platform_labels[label] = temp_id
            else:
                platform_labels = platform_items

            # print("generating list of keys... %s " % list(platform_labels))

            for item, actions in out_permissions["allow"].items():
                # print("### actions: %s" % actions)
                # print("### requested action: %s" % requested_action)
                # print("### item: %s" % item)
                if requested_action in actions and item in platform_labels:
                    out_item_keys.append(platform_labels[item])

        # print("### final out items: %s" % out_item_keys)
        return return_values(out_item_keys, out_permissions)

    def get(self, requested_id):
        """
        Looks for a given requested_id as either a user_id or email address.
        :param requested_id:
        :return:
        """
        if requested_id in self.users:
            return self.users[requested_id]
        if requested_id.lower() in self.users:
            return self.users[requested_id]
        for email, user in self.users.items():
            if user.user_id == requested_id:
                return user
            if user.name == requested_id:
                return user
            if user.email == requested_id:
                return user
        raise KeyError(f"User not found. {requested_id}")

    def get_role(self, requested_role):
        """
        Get a role instance using a role id, machine_label, or label.

        :param requested_role:
        :return:
        """
        if isinstance(requested_role, str):
            if requested_role in self.roles:
                return self.roles[requested_role]
            for role_id, role in self.roles.items():
                if role_id == requested_role:
                    return role
                if role.machine_label == requested_role:
                    return role
                if role.label == requested_role:
                    return role
        elif isinstance(requested_role, Role) is True:
            return requested_role

        raise KeyError(f"Role not found, unknown input type: {type(requested_role)} - {requested_role}")
