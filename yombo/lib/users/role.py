"""
Handles role functions.

Resounce syntax:

* URI/URL: web:/api/v1/some_resource/here
* A method within the gateway: ygw:library.states.some_function
* MQTT: mqtt:/some/topic/or/another

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.20.0
"""
from copy import deepcopy
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.lib.users.authbase import AuthBase
from yombo.utils import sha256_compact, data_pickle, data_unpickle
from yombo.utils.decorators import cached

logger = get_logger('library.users.role')


class Role(AuthBase):
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
                 permissions=None, saved_permissions=None, flush_cache=None):
        """
        Setup the role.

        :param parent: A reference to the users library.
        """
        super().__init__(parent)

        if machine_label is None:
            raise YomboWarning("Role must have a machine_label.")
        if machine_label in self.available_roles:
            raise YomboWarning("Role machine_label already exists.: %s" % machine_label)

        if label is None:
            label = machine_label
        if description is None:
            description = ""

        self.role_id: str = role_id
        self.machine_label: str = machine_label
        self.label: str = label
        self.description: str = description

        if source is None:
            source = "system"
        self.source: str = source

        if isinstance(saved_permissions, dict):
            self.item_permissions = saved_permissions
        if isinstance(permissions, list):
            for perm in permissions:
                # print("role adding permissions: %s" % perm)
                self.add_item_permission(
                    perm['platform'],
                    perm['item'],
                    perm['access'],
                    perm['action'],
                    flush_cache=flush_cache
                )
        self.save()

    def save(self):
        """
        Save the user device
        :return:
        """
        if self.source != "user":
            return
        # print("Starting role permission save... %s" % self.label)
        # print("Saving: %s %s" % (self.label, self.permissions))
        tosave = {
            'label': self.label,
            'machine_label': self.machine_label,
            'description': self.description,
            'saved_permissions': self.item_permissions
        }
        # print("writing config for role_id: %s" % self.role_id)
        self._Parent._Configs.set('rbac_roles', self.role_id,
                                  data_pickle(tosave, encoder="msgpack_base64", local=True),
                                  ignore_case=True)
