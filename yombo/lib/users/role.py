"""
Handles role functions.

Resounce syntax:

* URI/URL: web:/api/v1/some_resource/here
* A method within the gateway: ygw:library.states.some_function
* MQTT: mqtt:/some/topic/or/another

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.0
"""

from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import sha256_compact, data_pickle, data_unpickle

logger = get_logger('library.users.role')


class Role(object):
    """
    Roles are associated to permissions. Users are added to roles. Resources are protected by permissions.
    """
    @property
    def members(self):
        """
        Returns the label of the current role.
        """
        return self._Parent.list_role_members(self)

    @property
    def auth_keys(self):
        """
        Returns the label of the current role.
        """
        return self._Parent.list_role_auth_keys(self)

    @property
    def users(self):
        """
        Returns the label of the current role.
        """
        return self._Parent.list_role_users(self)

    def __init__(self, parent, machine_label=None, label=None, description=None, source=None, role_id=None,
                 permissions=None, saved_permissions=None):
        """
        Setup the role.

        :param parent: A reference to the users library.
        """
        self._Parent = parent
        self.all_roles = self._Parent.roles
        if machine_label is None:
            raise YomboWarning("Role must have a machine_label.")
        if machine_label in self.all_roles:
            raise YomboWarning("Role machine_label already exists.: %s" % machine_label)

        if label is None:
            label = machine_label
        if description is None:
            description = ""
        if role_id is None:
            role_id = sha256_compact(machine_label)

        self.role_id: str = role_id
        self.machine_label: str = machine_label
        self.label: str = label
        self.description: str = description

        if source is None:
            source = "system"
        self.source: str = source
        self.permissions = {
            'allow': {},
            'deny': {},
        }

        if isinstance(saved_permissions, dict):
            self.permissions = saved_permissions
        if isinstance(permissions, list):
            for permission in permissions:
                self.add_rule(permission)
        self.save()

    def permission_id(self, permission):
        return sha256_compact("%s:%s:%s:%s" %
                              (permission['platform'],
                               permission['item'],
                               permission['action'],
                               permission['access']))

    def add_rule(self, permission):
        """
        Add a rule to the ACL

        :param permission: A dict containing the permission items.
        """
        if all(name in permission for name in ('platform', 'item', 'action', 'access')) is False:
            raise YomboWarning("Permission is missing a key.")

        permission['access'] = permission['access'].lower()
        access = permission['access']

        if access not in ('allow', 'deny'):
            raise YomboWarning('access must be one of: allow, deny')

        permission['id'] = self.permission_id(permission)
        permission['platform'] = permission['platform'].lower()
        permission['action'] = permission['action'].lower()

        if permission['id'] not in self.permissions[access]:
            self.permissions[access][permission['id']] = permission
        self.save()

    def delete_rule(self, permission_id):
        """
        Delete a rule from the current role

        :param platform: A resource that is to be matched. devices:*, web:/url/platform
        :param action: edit, view, delete...etc
        :param access: One of 'allow' or 'deny'
        """
        if permission_id in self.permissions['allow']:
            del self.permissions['allow'][permission_id]
        elif permission_id in self.permissions['deny']:
            del self.permissions['deny'][permission_id]
        else:
            return
        self.save()

    def has_access(self, req_platform, req_item, req_action):
        """
        Checks if the role has any permissions matching the requested path and requested action.  Returns
        true if the access is allowed, otherwise false.

        :param req_platform:
        :param req_item:
        :param req_action:
        :return: bool
        """
        req_platform = req_platform.lower()
        req_action = req_action.lower()
        possible_deny = None
        # First check if there's an explicit deny. If it's a wildcard match, we will also check
        # allow permissions to see if there's an explicit allow
        # logger.info("has_access: req_path: {path}, req_action: {action}", path=req_path, action=req_action)
        # logger.info("has_access: permissions deny: %s" % self.permissions['deny'])
        for permission_id, permission in self.permissions['deny'].items():
            matched, wildcard = self.check_permission_match(req_platform, req_item, req_action, permission)
            if matched is None:
                logger.debug("deny, not matched.")
                continue

            if matched is True:
                if wildcard is True:
                    logger.debug("has_access: deny WILDCARD matched, returning false...")
                    possible_deny = True
                else:
                    logger.debug("has_access: deny matched, returning false...")
                    return False

        logger.info("has_access: permissions allow: %s" % self.permissions['allow'])
        for permission_id, permission in self.permissions['allow'].items():
            matched, wildcard = self.check_permission_match(req_platform, req_item, req_action, permission)
            if matched is None:
                logger.info("has_access: allow, not matched.")
                continue

            if matched is True:
                if wildcard is True:  # if a wildcard matched a deny, then we can't have a wildcard accept.
                    if possible_deny is True:
                        continue
                    else:
                        return True
                else:
                    return True

        if possible_deny is True:
            logger.info("has_access: possible deny, return false.")
            return False
        logger.info("has_access: default, returning none.")
        return None

    def check_permission_match(self, req_platform, req_item, req_action, permission):
        """
        Helper function for has_access. Just determines if the requested path and action matches
        the proviced permission.

        :param req_platform:
        :param req_item:
        :param req_action:
        :param permission:
        :return: bool, bool
        """
        logger.debug("check_permission_match: req_path: {path}, req_action: {action}, permission: {permission}",
                    path=req_platform, action=req_action, permission=permission)

        action_match_wild = False

        if req_platform != permission['platform']:
            logger.debug("check_permission_match: req_platform don't match: none, none")
            return None, None

        if permission['action'] == "*":
            pass
        elif req_action != permission['action']:
            logger.debug("check_permission_match: req_action don't match: none, none")
            return None, None

        if permission['item'] == "*":
            logger.debug("check_permission_match: wildcard item match, true true")
            return True, True
        if permission['item'] == req_item:
            return True, False

        logger.info("check_permission_match: Default, false false")
        return False, False

    def save(self):
        """
        Save the user device
        :return:
        """
        if self.source != "user":
            return

        tosave = {
            'label': self.label,
            'machine_label': self.machine_label,
            'description': self.description,
            'saved_permissions': self.permissions
        }
        self._Parent._Configs.set('rbac_roles', self.role_id,
                                  data_pickle(tosave, encoder="msgpack_base64").rstrip("="),
                                  ignore_case=True)
