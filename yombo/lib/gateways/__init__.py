# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * End user documentation: `Gateways @ User Documentation <https://yombo.net/docs/gateway/web_interface/gateways>`_
  * For library documentation, see: `Gateways @ Library Documentation <https://yombo.net/docs/libraries/gateways>`_

Tracks gateway details for the local gateway and any member gateways within the current cluster.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.14.0

:copyright: Copyright 2017-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/gateways/__init__.html>`_
"""
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import VERSION
from yombo.core.library import YomboLibrary
from yombo.core.schemas import GatewaySchema
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.core.log import get_logger
from yombo.lib.gateways.gateway import Gateway

logger = get_logger("library.gateways")


class Gateways(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages information about gateways.
    """
    gateways = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "gateway_id"
    _storage_attribute_name: ClassVar[str] = "gateways"
    _storage_label_name: ClassVar[str] = "gateway"
    _storage_class_reference: ClassVar = Gateway
    _storage_schema: ClassVar = GatewaySchema()
    _storage_search_fields: ClassVar[List[str]] = [
        "gateway_id", "machine_label", "label"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "machine_label"

    @property
    def local(self) -> Gateway:
        return self.gateways[self._gateway_id]

    @local.setter
    def local(self, val: Any) -> None:
        return None

    @property
    def local_id(self) -> str:
        return self._gateway_id

    @local_id.setter
    def local_id(self, val: Any) -> None:
        return None

    @property
    def master_gateway_id(self) -> str:
        if self._master_gateway_id is None:
            return self._gateway_id
        return self._master_gateway_id

    @master_gateway_id.setter
    def master_gateway_id(self, val: Any) -> None:
        return None

    @property
    def master(self) -> Gateway:
        if self.master_gateway_id is None:
            return self.gateways[self._gateway_id]
        return self.gateways[self.master_gateway_id]

    @master.setter
    def master(self, val: Any) -> None:
        return None

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.gateway_status = yield self._SQLDicts.get(self, "gateway_status")

        if self._Loader.operating_mode != "run":
            yield self.load_an_item_to_memory({
                    "id": "local",
                    "is_master": 1,
                    "master_gateway_id": "",
                    "machine_label": "local",
                    "label": "Local",
                    "description": "Local",
                    "dns_name": "127.0.0.1",
                    "version": VERSION,
                    "user_id": "local",
                    "created_at": int(time()),
                    "updated_at": int(time()),
                    "status": 1,
                    "_fake_data": True,
                },
                load_source="system",
                request_context="gateways::init",
                authentication=self.AUTH_USER
            )
        yield self.load_an_item_to_memory({
                "id": "cluster",
                "is_master": 0,
                "master_gateway_id": "",
                "machine_label": "cluster",
                "label": "Cluster",
                "description": "All gateways in a cluster.",
                "dns_name": "127.0.0.1",
                "version": VERSION,
                "user_id": "local",
                "created_at": int(time()),
                "updated_at": int(time()),
                "status": 1,
                "_fake_data": True,
            },
            load_source="system",
            request_context="gateways::init",
            authentication=self.AUTH_USER
        )
        yield self.load_from_database()

    def get_gateways(self) -> Dict[str, Gateway]:
        """
        Returns a copy of the gateways list.
        :return:
        """
        return self.gateways.copy()

    def _configs_set_(self, arguments, **kwargs) -> None:
        """
        Check for various configurations have changes so we can update ourselves too.

        :param arguments: section, option(key), value
        :return:
        """
        if self._gateway_id == "local" or len(self.gateways) == 0:
            return
        section = arguments["section"]
        option = arguments["option"]
        value = arguments["value"]

        if section == "dns":
            if option == "fqdn":
                self.local.dns_name = value
