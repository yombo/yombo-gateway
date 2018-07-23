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
from yombo.utils import random_string, sha256_compact

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

    def __init__(self, parent, machine_label, label=None, description=None, source=None, role_id=None, permissions=[]):
        """
        Setup the role.

        :param parent: A reference to the users library.
        """
        self._Parent = parent
        self.roles = self._Parent.roles
        if machine_label is None:
            raise YomboWarning("Role must have a machine_label.")
        if label is None:
            label = machine_label
        if machine_label in self.roles:
            raise YomboWarning("Role machine_label already exists.")
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
            'allow': [],
            'deny': [],
        }
        for item in permissions:
            self.add_rule(item['path'], item['action'], item['access'])
        self.roles = []  # support nested roles - TODO

    def add_rule(self, path, action, access):
        """
        Add a rule to the ACL

        :param path: A resource that is to be matched. devices:*, web:/url/path
        :param action: edit, view, delete...etc
        :param access: One of 'allow' or 'deny'
        """
        path = path.lower()
        action = action.lower()
        access = access.lower()

        if len(path.split(':')) != 2:
            raise YomboWarning("path must be in the format of:  class:item, example: devices:*")

        if access not in ('allow', 'deny'):
            raise YomboWarning('access must be one of: allow, deny')

        permission = (path, action)
        if permission not in self.permissions[access]:
            self.permissions[access].append(permission)

    def delete_rule(self, path, action, access):
        """
        Delete a rule from the current role

        :param path: A resource that is to be matched. devices:*, web:/url/path
        :param action: edit, view, delete...etc
        :param access: One of 'allow' or 'deny'
        """
        path = path.lower()
        action = action.lower()
        access = access.lower()

        permission = (path, action)
        if permission in self.permissions[access]:
            self.permissions[access].remove(permission)

    def has_access(self, req_path, req_action):
        """
        Checks if the role has any permissions matching the requested path and requested action.  Returns
        true if the access is allowed, otherwise false.

        :param req_path:
        :param req_action:
        :return: bool
        """
        possible_deny = None
        # First check if there's an explicit deny. If it's a wildcard match, we will also check
        # allow permissions to see if there's an explicit allow
        logger.info("has_access: req_path: {path}, req_action: {action}", path=req_path, action=req_action)
        logger.info("has_access: permissions deny: %s" % self.permissions['deny'])
        for permission in self.permissions['deny']:
            matched, wildcard = self.check_permission_match(req_path, req_action, permission)
            if matched is None:
                logger.info("deny, not matched.")
                continue

            if matched is True:
                if wildcard is True:
                    logger.info("has_access: deny WILDCARD matched, returning false...")
                    possible_deny = True
                else:
                    logger.info("has_access: deny matched, returning false...")
                    return False

        logger.info("has_access: permissions allow: %s" % self.permissions['allow'])
        for permission in self.permissions['allow']:
            matched, wildcard = self.check_permission_match(req_path, req_action, permission)
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

    def check_permission_match(self, req_path, req_action, permission):
        """
        Helper function for has_access. Just determines if the requested path and action matches
        the proviced permission.

        :param req_path:
        :param req_action:
        :param permission:
        :return: bool, bool
        """
        logger.debug("check_permission_match: req_path: {path}, req_action: {action}, permission: {permission}",
                    path=req_path, action=req_action, permission=permission)

        action_match_wild = False

        perm_path, perm_action = permission
        if perm_action == "*":
            action_match_wild = True
        elif req_action != perm_action:
            logger.debug("check_permission_match: req_action don't match: none, none")
            return None, None

        perm_class, perm_item = perm_path.split(':')
        req_class, req_item = req_path.split(':')
        if req_class != perm_class:
            logger.debug("check_permission_match: req_class don't match: none, none")
            return None, None

        if perm_item == "*":
            logger.debug("check_permission_match: wildcard item match, true true")
            return True, True
        if perm_item == req_item:
            logger.debug("check_permission_match: item match, true {action_match_wild}",
                        action_match_wild=action_match_wild)
            return True, action_match_wild

        logger.info("check_permission_match: Default, false false")
        return False, False

    def __repr__(self):
        return '<Role %s (%s)>' % (self.machine_label, self.role_id)

