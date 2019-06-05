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
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.core.log import get_logger
from yombo.lib.gateways.gateway import Gateway

logger = get_logger("library.gateways")


class Gateways(YomboLibrary, LibrarySearchMixin):
    """
    Manages information about gateways.
    """
    gateways = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_attribute_name = "gateways"
    _class_storage_fields = [
        "gateway_id", "gateway_id", "label", "machine_label", "status"
    ]
    _class_storage_sort_key = "machine_label"

    library_phase = 0

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

    def __contains__(self, gateway_requested):
        """
        .. note:: The gateway must be enabled to be found using this method.

        Checks to if a provided gateway ID or machine_label exists.

            >>> if "0kas02j1zss349k1" in self._Gateways:

        or:

            >>> if "some_gateway_name" in self._Gateways:

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param gateway_requested: The gateway id or machine_label to search for.
        :type gateway_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get_meta(gateway_requested)
            return True
        except:
            return False

    def __getitem__(self, gateway_requested):
        """
        .. note:: The gateway must be enabled to be found using this method.

        Attempts to find the device requested using a couple of methods.

            >>> gateway = self._Gateways["0kas02j1zss349k1"]  #by uuid

        or:

            >>> gateway = self._Gateways["alpnum"]  #by name

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param gateway_requested: The gateway ID or machine_label to search for.
        :type gateway_requested: string
        :return: A pointer to the device type instance.
        :rtype: instance
        """
        return self.get_meta(gateway_requested)

    def __setitem__(self, **kwargs):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, **kwargs):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter device types. """
        return self.device_types.__iter__()

    def __len__(self):
        """
        Returns an int of the number of device types configured.

        :return: The number of gateways configured.
        :rtype: int
        """
        return len(self.gateways)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo gateway library"

    def keys(self):
        """
        Returns the keys (device type ID's) that are configured.

        :return: A list of device type IDs. 
        :rtype: list
        """
        return list(self.gateways.keys())

    def items(self):
        """
        Gets a list of tuples representing the device types configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.gateways.items())

    def values(self):
        return list(self.gateways.values())

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.library_phase = 1
        self.gateway_status = yield self._SQLDict.get(self, "gateway_status")

        if self._Loader.operating_mode != "run":
            self._load_gateway_into_memory({
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
            })
        self._load_gateway_into_memory({
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
        })
        yield self._load_gateways_from_database()

    def _start_(self, **kwargs):
        self.library_phase = 3
        if self._Loader.operating_mode != "run":
            return

    def _started_(self, **kwargs):
        self.library_phase = 4
        if self._Loader.operating_mode != "run":
            return

    def _unload_(self, **kwargs):
        """Called during the last phase of shutdown. We'll save any pending changes."""
        for gateway_id, gateway in self.gateways.items():
            gateway.flush_sync()

    @inlineCallbacks
    def _load_gateways_from_database(self):
        """
        Loads gateways from database and sends them to
        :py:meth:`_load_gateway_into_memory <Gateways._load_gateway_into_memory>`

        This can be triggered either on system startup or when new/updated gateways have been saved to the
        database and we need to refresh existing gateways.
        """
        gateways = yield self._LocalDB.get_gateways()
        for a_gateway in gateways:
            self._load_gateway_into_memory(a_gateway, source="database")

    def _load_gateway_into_memory(self, gateway, source=None, **kwargs):
        """
        Add a new gateways to memory or update an existing gateways.


        :param gateway: A dictionary of items required to either setup a new gateway or update an existing one.
        :type gateway: dict
        :returns: Pointer to new gateway. Only used during unittest
        """
        gateway = self._generic_load_into_memory(self.gateways, 'gateway', Gateway, gateway, source=source, **kwargs)

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
