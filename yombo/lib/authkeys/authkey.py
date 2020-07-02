"""
A single authkey instance.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2017-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/authkeys/authkey.html>`_
"""
# Import python libraries
from typing import ClassVar, Optional,Type, Union

# Import Yombo libraries
from yombo.constants import AUTH_TYPE_AUTHKEY, AUTH_TYPE_USER
from yombo.constants.authkeys import AUTHKEY_ID_LENGTH_FULL
from yombo.core.library_child import YomboLibraryChild
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.auth_mixin import AuthMixin
from yombo.mixins.permission_mixin import PermissionMixin
from yombo.mixins.roles_mixin import RolesMixin
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_child_attributes_mixin import LibraryDBChildAttributesMixin
from yombo.utils import random_string

logger = get_logger("library.authkey_instance")


class AuthKey(YomboLibraryChild, LibraryDBChildMixin, AuthMixin, PermissionMixin, RolesMixin,
              LibraryDBChildAttributesMixin):
    """
    A single auth key item.
    """
    _Entity_type: ClassVar[str] = "Authentication key"
    _Entity_label_attribute: ClassVar[str] = "label"
    auth_type: ClassVar[str] = AUTH_TYPE_AUTHKEY

    def __str__(self):
        return f"AuthKey - {self.auth_key_id} - {self.label}"

    @property
    def user_id(self):
        return self.auth_key_id

    @property
    def display(self) -> str:
        return self.__str__()

    @property
    def editable(self) -> bool:
        """
        Checks if the authkey is editable. Only user generated ones are.

        :return:
        """
        if self.request_by_type == AUTH_TYPE_USER:
            return True
        return False

    def get_alerts(self):
        """ Placeholder, always returns an empty dict. """
        return {}

    def load_attribute_values_pre_process(self, incoming: dict) -> None:
        """ Setup basic class attributes based on incoming data. """
        # print(f"auth load pre process: {incoming}")
        self.request_by = None  #
        self.request_by_type = None  # one of: user, module, library

        search_dict = {
            "machine_label": incoming["machine_label"],
            "auth_key_id": incoming["auth_key_id"]
        }
        try:
            found = self._Parent.get_advanced(search_dict, multiple=False)
            raise YomboWarning(f"Found a duplicate auth key: {found.machine_label} - {found.label}")
        except KeyError:
            pass

        self.update_attributes_pre_process(incoming)

    def _set_new_auth_id(self):
        """ Sets the auth_id and possibly the auth_key. """
        auth_key_id_full = random_string(length=AUTHKEY_ID_LENGTH_FULL)
        self.auth_key_id = self._Hash.sha256_compact(auth_key_id_full)
        if self.preserve_key is True:
            self.auth_key_id_full = auth_key_id_full
        else:
            self.auth_key_id_full = ""
        return auth_key_id_full

    def rotate(self, request_context: Optional[str] = None,
               authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None):
        """
        Rotates the auth key (it's the matching auth_id). It's a good idea to rotate keys regularly.

        :param request_context: Context about the request. Such as an IP address of the source.
        :param authentication: An auth item such as a websession or authkey.
        :return:
        """
        self.check_authorization(authentication, "modify")

        old_auth_id = self.auth_id
        auth_key_id_full = self._set_new_auth_id()

        # self._Parent._finish_rotate_key(old_auth_id, self.auth_id, self)
        self._Parent.authkeys[self.auth_id] = self
        del self._Parent.authkeys[old_auth_id]
        return auth_key_id_full

    # def to_database_preprocess(self, incoming):
    #     """
    #     Modify the results being sent to the database.
    #
    #     :param incoming:
    #     :return:
    #     """
    #     roles = []
    #     for role_id, role in self.roles.items():
    #         roles.append(role_id)
    #     incoming["roles"] = roles
    #     # print(f"authkey incoming to database post process: {incoming}")
