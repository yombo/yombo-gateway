# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * End user documentation: `Gateways @ User Documentation <https://yombo.net/docs/gateway/web_interface/gateways>`_
  * For library documentation, see: `Gateways @ Library Documentation <https://yombo.net/docs/libraries/gateways>`_

Tracks gateway details for the local gateway and any member gateways within the current cluster.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.14.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/gateways.html>`_
"""
from time import time
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import VERSION
from yombo.core.library import YomboLibrary
from yombo.mixins.library_db_model_mixin import LibraryDBModelMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.core.log import get_logger
from yombo.lib.gateways.gateway import Gateway

logger = get_logger("library.gateways")


class Gateways(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Manages information about gateways.
    """
    gateways = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "gateway"
    _class_storage_load_db_class = Gateway
    _class_storage_attribute_name = "gateways"
    _class_storage_search_fields = [
        "gateway_id", "machine_label", "label"
    ]
    _class_storage_sort_key = "machine_label"

    @property
    def local(self):
        return self.gateways[self.gateway_id]

    @local.setter
    def local(self, val):
        return

    @property
    def local_id(self):
        return self.gateway_id

    @local.setter
    def local_id(self, val):
        return

    @property
    def master_id(self):
        if self.master_gateway_id is None:
            return self.local_id
        return self.master_gateway_id

    @master_id.setter
    def master_id(self, val):
        return

    @property
    def master(self):
        if self.master_gateway_id is None:
            return self.gateways[self.gateway_id]
        return self.gateways[self.master_gateway_id]

    @master.setter
    def master(self, val):
        return

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.gateway_status = yield self._SQLDict.get(self, "gateway_status")

        if self._Loader.operating_mode != "run":
            self._class_storage_load_db_items_to_memory({
                "id": "local",
                "is_master": True,
                "master_gateway_id": "",
                "machine_label": "local",
                "label": "Local",
                "description": "Local",
                "dns_name": "127.0.0.1",
                "version": VERSION,
                "user_id": "local",
                "created_at": int(time()),
                "updated_at": int(time()),
            }, source="database")
        self._class_storage_load_db_items_to_memory({
            "id": "cluster",
            "is_master": False,
            "master_gateway_id": "",
            "machine_label": "cluster",
            "label": "Cluster",
            "description": "All gateways in a cluster.",
            "dns_name": "127.0.0.1",
            "version": VERSION,
            "user_id": "local",
            "created_at": int(time()),
            "updated_at": int(time()),
        }, source="database")
        yield self._class_storage_load_from_database()

    def get_gateways(self):
        """
        Returns a copy of the gateways list.
        :return:
        """
        return self.gateways.copy()

    def _configuration_set_(self, **kwargs):
        """
        Check for various configurations have changes so we can update ourselves too.

        :param kwargs: section, option(key), value
        :return:
        """
        section = kwargs["section"]
        option = kwargs["option"]
        value = kwargs["value"]

        if section == "dns":
            if option == "fqdn":
                self.local.dns_name = value

    def full_list_gateways(self):
        """
        Return a list of dictionaries representing all known commands to this gateway.
        :return:
        """
        items = []
        for gateway_id, gateway in self.gateways.items():
            if gateway.machine_label in ("cluster", "all"):
                continue
            items.append(gateway.asdict())
        return items
