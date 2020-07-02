# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `Commands @ Library Documentation <https://yombo.net/docs/libraries/permissions>`_

This library is responsible for managing all system permissions. This is accomplished using an attribute-based
access control (ABAC) system, namely, this uses the python Vakt library.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/permissions.html>`_
"""
from copy import deepcopy
from typing import Any, ClassVar, Dict, List, Optional, Type, Union
import vakt
from vakt.rules import Eq, Any, NotEq, StartsWith, In, RegexMatch, CIDR, And, Greater, Less
from vakt.rules.base import Rule

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import AUTH_TYPE_AUTHKEY, AUTH_TYPE_USER, AUTH_TYPE_WEBSESSION
from yombo.constants.permissions import *
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboNoAccess, YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import PermissionSchema
from yombo.mixins.auth_mixin import AuthMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.utils import random_string
from yombo.utils.caller import caller_string
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.commands")


class Permission(Entity, LibraryDBChildMixin):
    """
    A permission (vakt policy) is an attribute based rule. This class represents that
    policy. This class helps to manage the policy and show various details about that policy.
    """
    _Entity_type: ClassVar[str] = "Permission"
    _Entity_label_attribute: ClassVar[str] = "machine_label"

    vakt_policy = None

    @property
    def policy(self):
        if self.vakt_policy is None:
            return None
        return self.vakt_policy.to_json()

    @policy.setter
    def policy(self, val):
        try:
            self._Parent.vakt_storage.delete(self.permission_id)
        except:
            pass
        self.vakt_policy = vakt.Policy.from_json(val)

    def __init__(self, parent, **kwargs):
        """
        Setup the policy object using information passed in.

        :param incoming: A command containing required items to setup.
        :type incoming: dict
        :return: None
        """
        super().__init__(parent, **kwargs)
        self._Parent.vakt_storage.add(self.vakt_policy)


class Permissions(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages all commands available for devices.

    All modules already have a predefined reference to this library as
    `self._Commands`. All documentation will reference this use case.
    """
    permissions: ClassVar[dict] = {}  # store policy to role mapping
    auth_platforms: ClassVar[dict] = {}
    vakt_storage: ClassVar = vakt.MemoryStorage()

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "permission_id"
    _class_storage_yombo_toml_section: str = "rbac_permissions"  # what section of the config to use
    _storage_label_name: ClassVar[str] = "permission"
    _storage_class_reference: ClassVar = Permission
    _storage_schema: ClassVar = PermissionSchema()
    _storage_attribute_name: ClassVar[str] = "permissions"
    _storage_search_fields: ClassVar[List[str]] = [
        "permission_id", "machine_label", "label"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "created_at"
    _storage_attribute_sort_key_order: ClassVar[str] = "desc"
    _new_items_require_authentication: ClassVar[bool] = True

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Define the base permissions
        """
        self.system_seed = self._Configs.get("core.rand_seed")
        yield self.load_from_database()
        self.guard = vakt.Guard(self.vakt_storage, vakt.RulesChecker())
        self.auth_platforms = deepcopy(AUTH_PLATFORMS)  # Possible authentication platforms and their actions.
        yield self.setup_permissions(self.auth_platforms)

    @inlineCallbacks
    def _load_(self, **kwargs):
        results = yield global_invoke_all("_auth_platforms_", called_by=self)
        logger.debug("_auth_platforms_ results: {results}", results=results)
        new_permissions = {}
        for component, platforms in results.items():
            for machine_label, platform_data in platforms.items():
                if "actions" not in platform_data:
                    logger.warn("Unable to add auth platform, actions is missing from: {component} - {machine_label}",
                                component=component, machine_label=machine_label)
                    continue
                if "possible" not in platform_data["actions"]:
                    logger.warn("Unable to add auth platform, 'possible' actions are missing from:"
                                " {component} - {machine_label}",
                                component=component, machine_label=machine_label)
                    continue
                if "user" not in platform_data["actions"]:
                    logger.info("'user' default allowed actions is missing from {component} - {machine_label},"
                                " setting to none.",
                                component=component, machine_label=machine_label)
                    platform_data["actions"]["user"] = []
                new_permissions[machine_label] = platform_data

        self.auth_platforms.update(new_permissions)
        yield self.setup_permissions(new_permissions)

    @inlineCallbacks
    def setup_permissions(self, new_permissions):
        """
        Setup all the system permissions. This creates all the system roles and sets up VAKT.
        :return:
        """
        Roles = self._Roles
        # print(f'permissions - init - roles: {Roles.roles}')

        # define admin
        # print("11 permissions, about to define system admin.")
        permission_id = self._Hash.sha224_compact(f"auto-admin-{self.system_seed}")
        if permission_id not in self.permissions:
            # print(f"creating admin permission: {permission_id}")
            role = Roles.get("admin")
            yield self.new(
                role,
                machine_label="admin",
                label="Administrator",
                description="Grant access to everything for admins.",
                actions=[Any()],
                resources=[{"platform": Any(), "id": Any()}],
                # subjects=[f"role:{role.role_id}"],
                permission_id=permission_id,
                effect=vakt.ALLOW_ACCESS,
                _request_context="setup_permissions",
                _load_source="local",
                _authentication=self.AUTH_USER
                )

        for platform, data in new_permissions.items():
            platform_parts = platform.split(".")

            # define platform admins
            platform_machine_label = f"{platform_parts[0]}_{platform_parts[1]}_{platform_parts[2]}_admin".lower()
            platform_label = f"{platform_parts[2]} {platform_parts[1]} {platform_parts[0]}"
            permission_id = self._Hash.sha224_compact(f"admin-{platform_machine_label} {self.system_seed}")
            role_id = self._Hash.sha224_compact(permission_id)
            try:
                role = self._Roles.get_advanced({"role_id": role_id, "machine_label": platform_machine_label},
                                                multiple=False)
            except KeyError:
                # print(f'data["actions"]["possible"]: {data["actions"]["possible"]}')
                actions_string = ", ".join(data["actions"]["possible"])
                description = f"Admin access to '{platform_label}', actions: {actions_string}"
                role = yield self._Roles.new(
                    role_id=role_id,
                    machine_label=platform_machine_label,
                    label=f"{platform_label} admin",
                    description=description,
                    _request_context="setup_permissions",
                    _load_source="local",
                    _authentication=self.AUTH_USER
                )
            # print(f"22 permissions, about to define platform admin: {platform_label}")
            if permission_id not in self.permissions:
                yield self.new(
                    role,
                    machine_label=platform_machine_label,
                    label=f"{platform_label} admin",
                    description=description,
                    actions=data["actions"]["possible"],
                    resources=[{"platform": Eq(platform), "id": Any()}],
                    # subjects=[Eq(f"role:{role.role_id}")],
                    permission_id=permission_id,
                    effect=vakt.ALLOW_ACCESS,
                    _request_context="setup_permissions",
                    _load_source="local",
                    _authentication=self.AUTH_USER
                    )
            # else:
            #     self.attach_

            # define platform actions for more fine grained controls
            for action in data["actions"]["possible"]:
                platform_machine_label = f"{platform_parts[0]}_{platform_parts[1]}_{platform_parts[2]}_{action}".lower()
                platform_label = f"{platform_parts[0]} {platform_parts[1]} {platform_parts[2]}"
                permission_id = self._Hash.sha224_compact(f"action-{platform_machine_label} {action} {self.system_seed}")
                role_id = self._Hash.sha224_compact(permission_id)
                try:
                    role = self._Roles.get_advanced({"role_id": role_id, "machine_label": platform_machine_label},
                                                    multiple=False)
                except KeyError:
                    description = f"Allow '{platform_label}', action: {action}"
                    role = yield self._Roles.new(
                        role_id=role_id,
                        label=f"{platform_label} {action}",
                        machine_label=platform_machine_label,
                        description=description,
                        _request_context="setup_permissions",
                        _load_source="local",
                        _authentication=self.AUTH_USER
                    )
                if permission_id not in self.permissions:
                    yield self.new(
                        role,
                        machine_label=platform_machine_label,
                        label=f"{platform_label} {action}",
                        description=description,
                        actions=[action],
                        resources=[{"platform": Eq(platform), "id": Any()}],
                        # subjects=[f"role:{role.role_id}"],
                        permission_id=permission_id,
                        effect=vakt.ALLOW_ACCESS,
                        _request_context="setup_permissions",
                        _load_source="local",
                        _authentication=self.AUTH_USER
                        )
                # else:
                #     attach....
            # Grant all users basic access rights. This can be revoked using new policies to negate this.
            platform_machine_label = f"{platform_parts[0]}_{platform_parts[1]}_{platform_parts[2]}_user".lower()
            platform_label = f"{platform_parts[2]} {platform_parts[1]} {platform_parts[0]}"
            permission_id = self._Hash.sha224_compact(f"user-{platform_machine_label} {self.system_seed}")
            if permission_id not in self.permissions:
                if len(data["actions"]["user"]):
                    role = Roles.get("users")
                    actions_string = ", ".join(data["actions"]["user"])
                    # print(f"44 permissions, about to define platform user: {platform_machine_label} - {actions_string}")
                yield self.new(
                    role,
                    machine_label=platform_machine_label,
                    label=platform_label,
                    description=f"All users access to '{platform_machine_label}', actions: {actions_string}",
                    actions=data["actions"]["user"],
                    resources=[{"platform": Eq(platform), "id": Any()}],
                    # subjects=[Eq(f"role:{role.role_id}")],
                    permission_id=permission_id,
                    effect=vakt.ALLOW_ACCESS,
                    _request_context="setup_permissions",
                    _load_source="local",
                    _authentication=self.AUTH_USER
                )

    @staticmethod
    def get_auth_platform(auth_type: str, auth_name: str) -> str:
        """
        Looks through AUTH_PLATFORMS for the requested type and name, and returns the auth platform.

        :param auth_type: Either 'library' or 'module'.
        :param auth_name: Name of the library or module, such as "Atoms".
        :return:
        """
        # print(f"get_auth_platform - starting:  {auth_type} - {auth_name}")
        for platform, data in AUTH_PLATFORMS.items():
            # print(f"checking: {platform} - {data}")
            if data["resource_type"] == auth_type and data["resource_name"] == auth_name:
                return platform
        # print(f"get_auth_platform - Not found:: {auth_name}")
        return None

    @inlineCallbacks
    def new(self, attachment: Type[AuthMixin], machine_label: str, label: str, description: str, actions, resources,
            subjects: Optional[list] = None, effect: Union[None, vakt.ALLOW_ACCESS, vakt.DENY_ACCESS] = None,
            permission_id=None, _load_source: Optional[str] = None, _request_context: Optional[str] = None,
            _authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None):
        """
        Create a new permission and attach to a role, user, or authkey.

        To track how the permission was created, either request_by and request_by_type or an authentication item
        can be anything with the authmixin, such as a user, websession, or authkey.

        :param attachment: A role, authkey, or user.
        :param machine_label: Permission machine_label
        :param label: Permission human label.
        :param description: Permission description.
        :param actions:
        :param resources:
        :param subjects:
        :param effect:
        :param permission_id: permission the role was loaded.
        :param _load_source: Where the data originated from. One of: local, database, yombo, system
        :param _request_context: Context about the request. Such as an IP address of the source.
        :param _authentication: An auth item such as a websession or authkey.
        :return:
        """

        if permission_id is None:
            permission_id = random_string(length=38)

        try:
            found = self.get_advanced({"machine_label": machine_label, "permission_id": permission_id}, multiple=False)
            raise YomboWarning(f"Found a matching permission: {found.machine_label} - {found.label}")
        except KeyError:
            pass

        if effect in (None, True, 1, 'allow'):
            effect = vakt.ALLOW_ACCESS
        else:
            effect = vakt.DENY_ACCESS

        if subjects is None:
            subjects = [Eq(f"{attachment.auth_type}:{attachment.auth_id}")]
        else:
            subjects = self.convert_items_to_vakt(subjects)

        policy = vakt.Policy(
            permission_id,
            actions=self.convert_items_to_vakt(actions),
            resources=self.convert_items_to_vakt(resources),
            subjects=subjects,
            effect=effect,
            # context=self.convert_items_to_vakt(context),
            description=description,
        ).to_json()

        if label is None:
            label = machine_label
        if description is None:
            description = label

        self._Users.validate_authentication(_authentication)

        results = yield self.load_an_item_to_memory(
            {
                "id": permission_id,
                "attach_id": attachment.auth_id,
                "attach_type": attachment.auth_type,
                "policy": policy,
                "machine_label": machine_label,
                "label": label,
                "description": description,
                "request_context": _request_context,
            },
            load_source=_load_source,
            request_context=_request_context if _request_context is not None else caller_string(),
            authentication=_authentication
        )
        return results

    def delete(self, permssion_id: str) -> None:
        """
         Deletes a permission item.

         :param permssion_id: Permission id to delete.
        """
        if permssion_id not in self.permissions:
            raise KeyError("Permission id not found, cannot delete it.")
        permission = self.permissions[permssion_id]
        if permission._meta["load_source"] == "library":
            raise YomboWarning("Unable to delete library created permissions.")

        try:
            self.vakt_storage.delete(permssion_id)
        except:
            pass

        del self.permissions[permssion_id]
        #TODO: delete

    def find_authentication_item(self, request_by: str, request_by_type: str) -> Type[AuthMixin]:
        """ Attempts to locate the authentication item using the id and type. """
        if request_by_type == AUTH_TYPE_AUTHKEY:
            if request_by in self._AuthKeys:
                return self._AuthKeys[request_by]
        if request_by_type == AUTH_TYPE_USER:
            if request_by in self._Users:
                return self._Users.get(request_by)
            else:
                print(f"Cannot find in : {self._Users.users}")
        raise KeyError(f"Could not find the source auth item: {request_by_type} - {request_by}")

    def is_allowed(self, platform: str, action: str, item_id: Optional[str] = None,
                   authentication: Type[AuthMixin] = None,
                   request_context: Optional[str] = None, raise_error: Optional[bool] = None):
        """
        Check if the action is allowed for the platform, by subject (who).

        :param platform: Which resource - yombo.lib.atoms
        :param action: What's happening - edit, view, delete, etc.
        :param item_id: Which item is being manipulated. Use "*" for any.
        :param authentication: Who - either a websession or authkey, or any authentication class instance.
        :param request_context: Context for the request. Such as source IP, automation rule, etc.
        :param raise_error: If true, raise YomboNoAccess if no access, this is the default.
        :return:
        """
        if self._Loader.run_phase[1] <= 3400:
            return True
        # TODO: Validate libary and module permissions. For now, they can do anything.
        if authentication.user_id.startswith("^yombo^"):
            return True
        if authentication is None:
            logger.warn("is_allow got a blank authentication, going to deny because...duhhhh...")
            return False

        if item_id is None:
            item_id = "*"

        inq = vakt.Inquiry(action=action,
                           resource={'platform': platform, 'id': item_id},
                           subject=f'user:{authentication.accessor_id}'
                           )
        if bool(self.guard.is_allowed(inq)) is True:
            return True

        for role_id, role in authentication.roles.items():
            inq = vakt.Inquiry(action=action,
                               resource={'platform': platform, 'id': item_id},
                               subject=f'role:{role_id}'
                               )
            if bool(self.guard.is_allowed(inq)) is True:
                return True

        if raise_error in (None, True, "1", "yes"):
            raise YomboNoAccess(action=action,
                                platform=platform,
                                item_id=item_id,
                                authentication=authentication,
                                request_context=request_context)

        return False

    @staticmethod
    def convert_items_to_vakt(incoming: Any) -> Any:
        """
        Converts items sent in from strings to vakt items.

        :param incoming:
        :return:
        """
        def do_convert(input):
            if isinstance(input, str):
                if input == "*":
                    return Any()
                else:
                    return Eq(input)
            elif isinstance(input, Rule):
                return input
            return None

        items = deepcopy(incoming)
        if isinstance(items, list):
            for idx, value in enumerate(items):
                if isinstance(value, dict):
                    # print("CTTV: doing dict.")
                    for label, data in value.items():
                        items[idx][label] = do_convert(data)
                else:
                    # print(f"CTTV: doing single item: {value}")
                    items[idx] = do_convert(value)
                    # print(f"CTTV: DONE doing single item: {items[idx]}")
        else:
            items = do_convert(items)

        return items
