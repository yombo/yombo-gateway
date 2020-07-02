"""
.. note::

  * End user documentation: `Auth Keys @ User Documentation <https://yombo.net/docs/gateway/web_interface/authkeys>`_
  * For library documentation, see: `Auth Keys @ Library Documentation <https://yombo.net/docs/libraries/authkeys>`_

Handles auth key items for the webinterface, primarily used for accessing API endpoints and are used in
place of a username/password for scripts.

To help ensure AuthKey revocations across a cluster, deleted/expired keys are kept for 30 days.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2017-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/authkeys/__init__.html>`_
"""
# Import python libraries
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants.authkeys import AUTHKEY_ID_LENGTH, AUTHKEY_ID_LENGTH_FULL
from yombo.core.library import YomboLibrary
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.core.schemas import AuthKeySchema
from yombo.lib.authkeys.authkey import AuthKey
from yombo.mixins.auth_mixin import AuthMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.utils import bytes_to_unicode, is_true_false
from yombo.utils.caller import caller_string

logger = get_logger("library.authkeys")

MODIFY_FIELDS_READABLE = 1
MODIFY_FIELDS_WRITABLE = 2
MODIFY_FIELDS_REQUIRED = 4


class AuthKeys(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Auth Key management.
    """
    authkeys: ClassVar[Dict[str, Any]] = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "auth_key_id"
    _storage_primary_length: ClassVar[str] = 65
    _storage_attribute_name: ClassVar[str] = "authkeys"
    _storage_label_name: ClassVar[str] = "authkey"
    _storage_class_reference: ClassVar = AuthKey
    _storage_schema: ClassVar = AuthKeySchema()
    _storage_pickled_fields: ClassVar[Dict[str, str]] = {"roles": "msgpack_zip"}
    _storage_search_fields: ClassVar[List[str]] = ["auth_key_id", "machine_label", "label"]
    _time_stamp_resolution = "int"
    _new_items_require_authentication: ClassVar[bool] = True
    # _modify_fields = {
    #     "machine_label": MODIFY_FIELDS_READABLE | MODIFY_FIELDS_WRITABLE,
    #     "label": "rw",
    # }

    @inlineCallbacks
    def _init_(self, **kwargs) -> None:
        """ Load auth keys from database. """
        yield self.load_from_database()

    def _load_(self, **kwargs) -> None:
        """ Ensure that the admin key exists, doesn't matter if it's disabled. """
        try:
            self.get("admin")
        except KeyError:
            admin_role = self._Roles.get("admin")
            self.new(machine_label="admin",
                     label="Administration default auth key",
                     description="Default authentication key created automatically. Can be deleted, but will be automatically recreated.",
                     roles=[admin_role.role_id],
                     preserve_key=True,
                     _authentication=self.AUTH_USER,
                     )

    @inlineCallbacks
    def new(self, machine_label: str, label: str, description: str, preserve_key: Optional[bool] = None,
            status: Optional[int] = None, roles: Optional[List[str]] = None,
            last_access_at: Optional[Union[int, float]] = None, _load_source: Optional[str] = None,
            _request_context: Optional[str] = None,
            _authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None, **kwargs) -> AuthKey:
        """
        Create a new auth_key.

        To track how the authkey was created, either request_by and request_by_type or an authentication item
        can be anything with the authmixin, such as a user, websession, or authkey.


        :param machine_label: Authkey machine_label
        :param label: Authkey human label.
        :param description: Authkey description.
        :param preserve_key: If true, the original auth_id will be available from auth_key
        :param status: 0 - disabled, 1 - enabled, 2 - deleted
        :param roles: Assign authkey to a list of roles.
        :param last_access_at: When auth was last used.
        :param _load_source: Where the data originated from. One of: local, database, yombo, system
        :param _request_context: Context about the request. Such as an IP address of the source.
        :param _authentication: An auth item such as a websession or authkey.
        :return:
        """
        preserve_key = is_true_false(preserve_key) or True

        if _request_context is None:
            _request_context = caller_string()  # get the module/class/function name of caller

        try:
            results = self.get(machine_label)
            raise YomboWarning(
                {
                    "id": results.auth_key_id,
                    "title": "Duplicate entry",
                    "detail": "An authkey with that machine_label already exists."
                })
        except KeyError as e:
            pass

        self._Users.validate_authentication(_authentication)
        logger.debug("authkey new: about to load a new item....: {machine_label}", machine_label=machine_label)
        results = yield self.load_an_item_to_memory(
            {
                "machine_label": machine_label,
                "label": label,
                "description": description,
                "preserve_key": preserve_key,
                "status": status,
                "roles": roles,
                "last_access_at": last_access_at,
            },
            load_source=_load_source,
            request_context=_request_context if _request_context is not None else caller_string(),
            authentication=_authentication
        )
        return results

    def get_session_from_request(self, request: Type["twisted.web.http.Request"]) -> AuthKey:
        """
        Called by the web interface auth system to check if the provided request
        has an auth key. Can be in the query string as "?_auth_key=key" or "?_api_auth=key"
        or in the header as "x-auth-key: key" or "x-api-auth: key"

        Returns the auth object if found otherwise raises YomboWarning.

        :param request: The web request instance.
        :return: bool
        """
        auth_key_id_full = None
        if request is not None:
            auth_key_id_full = bytes_to_unicode(request.getHeader(b"x-auth-key"))
            if auth_key_id_full is None:
                auth_key_id_full = bytes_to_unicode(request.getHeader(b"x-api-auth"))
            if auth_key_id_full is None:
                try:
                    auth_key_id_full = request.args.get("_auth_key")[0]
                except:
                    try:
                        auth_key_id_full = request.args.get("_api_auth")[0]
                    except:
                        pass

        if auth_key_id_full is None:
            raise YomboWarning("x-auth-key or x-api-auth header missing, nor _api_auth or _api_query query string is not found.")

        request.session_long_id = auth_key_id_full
        return self.get_session_by_id(auth_key_id_full)

    def get_session_by_id(self, auth_key_id: str) -> AuthKey:
        """
        Gets an Auth Key based on a auth_key_id.

        :param auth_key_id:
        :return:
        """
        auth_key_id = self._Hash.sha256_compact(auth_key_id)
        if self.validate_auth_id(auth_key_id) is False:
            raise YomboWarning("auth key has invalid characters.")

        if auth_key_id in self.authkeys:
            auth_key = self.authkeys[auth_key_id]
        else:
            raise YomboWarning("Auth Key isn't found")

        if auth_key.status == 2:
            raise YomboWarning("Auth Key is set to be deleted.")

        return auth_key

    def delete(self, auth_key_id: str, load_source: Optional[str] = None, request_context: Optional[str] = None,
               authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None) -> None:
        """
        Deletes an Auth Key.

        :param auth_key_id: The auth key to find.
        :param load_source: Where the data originated from. One of: local, database, yombo, system
        :param request_context: Context about the request. Such as an IP address of the source.
        :param authentication: An auth item such as a websession or authkey.
        :return:
        """
        self.check_authorization(authentication, "remove")

        auth_key = self.get(auth_key_id)
        auth_key.expire(request_context=request_context, authentication=authentication)

    def rotate(self, auth_key_id: str, request_context: Optional[str] = None,
               authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None) -> AuthKey:
        """
        Rotates an Auth Key for security.

        :param auth_key_id: The auth key to find.
        :param request_context: Context about the request. Such as an IP address of the source.
        :param authentication: An auth item such as a websession or authkey.
        :return:
        """
        auth_key = self.get(auth_key_id)
        auth_key.rotate(request_context=request_context, authentication=authentication)
        return auth_key

    # def _finish_rotate_key(self, old_auth_key_id: str, new_auth_key_id: str, auth: Type[AuthKey]) -> None:
    #     """
    #     Called by the child object to update the key_id in self.authkeys. Should never be called elsewhere.
    #
    #     :param old_auth_key_id:
    #     :param new_auth_key_id:
    #     :param auth:
    #     :return:
    #     """
    #     self.authkeys[new_auth_key_id] = auth
    #     del self.authkeys[old_auth_key_id]

    def validate_auth_id(self, auth_key_id: str) -> bool:
        """
        Validate the session id to make sure it's reasonable.

        :param auth_key_id: The auth key to find.
        :return: 
        """
        if auth_key_id == "LOGOFF":  # lets not raise an error.
            return True
        if auth_key_id.isalnum() is False:
            return False
        if len(auth_key_id) < AUTHKEY_ID_LENGTH-5:  # Allows decreasing/increasing the length by 5 in the future.
            return False
        if len(auth_key_id) > AUTHKEY_ID_LENGTH_FULL+5:
            return False
        return True

