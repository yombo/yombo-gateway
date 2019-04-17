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
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.library_search import LibrarySearch
from yombo.core.log import get_logger
from yombo.lib.gateways.gateway import Gateway
from yombo.utils import global_invoke_all
from yombo.utils.decorators import deprecated

logger = get_logger("library.gateways")


class Gateways(YomboLibrary, LibrarySearch):
    """
    Manages information about gateways.
    """
    gateways = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    item_search_attribute = "gateways"
    item_searchable_attributes = [
        "gateway_id", "gateway_id", "label", "machine_label", "status"
    ]
    item_sort_key = "machine_label"

    library_phase = 0

    @property
    def local(self):
        return self.gateways[self.gateway_id()]

    @local.setter
    def local(self, val):
        return

    @property
    def local_id(self):
        return self.gateway_id()

    @local.setter
    def local_id(self, val):
        return

    @property
    def master_id(self):
        if self.master_gateway_id() is None:
            return self.local_id
        return self.master_gateway_id()

    @master_id.setter
    def master_id(self, val):
        return

    @property
    def master(self):
        if self.master_gateway_id() is None:
            return self.gateways[self.gateway_id()]
        return self.gateways[self.master_gateway_id()]

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
        self.gateway_id = self._Configs.gateway_id
        self.is_master = self._Configs.is_master
        self.master_gateway_id = self._Configs.master_gateway_id

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

    def _stop_(self, **kwargs):
        """
        Cleans up any pending deferreds.
        """
        if hasattr(self, "load_deferred"):
            if self.load_deferred is not None and self.load_deferred.called is False:
                self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

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
            self._load_gateway_into_memory(a_gateway)

    def _load_gateway_into_memory(self, gateway, test_gateway=False):
        """
        Add a new gateways to memory or update an existing gateways.

        **Hooks called**:

        * _gateway_before_load_ : Called before the gateway is loaded into memory.
        * _gateway_after_load_ : Called after the gateway is loaded into memory.

        :param gateway: A dictionary of items required to either setup a new gateway or update an existing one.
        :type gateway: dict
        :param test_gateway: Used for unit testing.
        :type test_gateway: bool
        :returns: Pointer to new gateway. Only used during unittest
        """
        # print(f"gateway keys installed: {list(self.gateways.keys())}")
        logger.debug("gateway: {gateway}", gateway=gateway)

        gateway_id = gateway["id"]
        if gateway_id in self.gateways:
            raise YomboWarning(f"Cannot add gateway to memory, already exists: {gateway_id}")

        try:
            global_invoke_all("_gateway_before_load_",
                              called_by=self,
                              gateway_id=gateway_id,
                              gateway=gateway,
                              )
        except Exception as e:
            pass
        self.gateways[gateway_id] = Gateway(self, gateway)  # Create a new gateway in memory
        try:
            global_invoke_all("_gateway_after_load_",
                              called_by=self,
                              gateway_id=gateway_id,
                              gateway=self.gateways[gateway_id],
                              )
        except Exception as e:
            pass

    @deprecated(deprecated_in="0.21.0", removed_in="0.25.0",
                current_version=VERSION,
                details="Use the 'local' property instead.")
    def get_local(self):
        return self.gateways[self.gateway_id()]

    @deprecated(deprecated_in="0.21.0", removed_in="0.25.0",
                current_version=VERSION,
                details="Use the 'local_id' property instead.")
    def get_local_id(self):
        """
        For future...
        :return:
        """
        return self.gateway_id()

    def get_gateways(self):
        """
        Returns a copy of the gateways list.
        :return:
        """
        return self.gateways.copy()



    @inlineCallbacks
    def add_gateway(self, api_data, source=None, **kwargs):
        """
        Add a new gateway. Updates Yombo servers and creates a new entry locally.

        :param api_data:
        :param kwargs:
        :return:
        """
        if "gateway_id" not in api_data:
            api_data["gateway_id"] = self.gateway_id()

        if api_data["machine_label"].lower() == "cluster":
            return {
                "status": "failed",
                "msg": "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
                "apimsg": "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
                "apimsghtml": "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
            }
        if api_data["label"].lower() == "cluster":
            return {
                "status": "failed",
                "msg": "Couldn't add gateway: label cannot be 'cluster' or 'all'",
                "apimsg": "Couldn't add gateway: label cannot be 'cluster' or 'all'",
                "apimsghtml": "Couldn't add gateway: label cannot be 'cluster' or 'all'",
            }
        if source != "amqp":
            try:
                if "session" in kwargs:
                    session = kwargs["session"]
                else:
                    session = None

                gateway_results = yield self._YomboAPI.request("POST", "/v1/gateway",
                                                               api_data,
                                                               session=session)
            except YomboWarning as e:
                return {
                    "status": "failed",
                    "msg": f"Couldn't add gateway: {e.message}",
                    "apimsg": f"Couldn't add gateway: {e.message}",
                    "apimsghtml": f"Couldn't add gateway: {e.html_message}",
                }
            gateway_id = gateway_results["data"]["id"]

        new_gateway = gateway_results["data"]
        self._load_gateway_into_memory(new_gateway)
        return {
            "status": "success",
            "msg": "Gateway added.",
            "gateway_id": gateway_id,
        }

    @inlineCallbacks
    def edit_gateway(self, gateway_id, api_data, called_from_gateway=None, source=None, **kwargs):
        """
        Edit a gateway at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        if api_data["machine_label"].lower() == "cluster":
            return {
                "status": "failed",
                "msg": "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
                "apimsg": "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
                "apimsghtml": "Couldn't add gateway: machine_label cannot be 'cluster' or 'all'",
            }
        if api_data["label"].lower() == "cluster":
            return {
                "status": "failed",
                "msg": "Couldn't add gateway: label cannot be 'cluster' or 'all'",
                "apimsg": "Couldn't add gateway: label cannot be 'cluster' or 'all'",
                "apimsghtml": "Couldn't add gateway: label cannot be 'cluster' or 'all'",
            }
        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            gateway_results = yield self._YomboAPI.request("PATCH",
                                                           f"/v1/gateway/{gateway_id}",
                                                           api_data,
                                                           session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't edit gateway: {e.message}",
                "apimsg": f"Couldn't edit gateway: {e.message}",
                "apimsghtml": f"Couldn't edit gateway: {e.html_message}",
            }

        gateway = self.gateways[gateway_id]
        if called_from_gateway is not True:
            gateway.update_attributes(api_data)
            gateway.save_to_db()

        return {
            "status": "success",
            "msg": "Device type edited.",
            "gateway_id": gateway_results["data"]["id"],
        }

    @inlineCallbacks
    def delete_gateway(self, gateway_id, **kwargs):
        """
        Delete a gateway at the Yombo server level, not at the local gateway level.

        :param gateway_id: The gateway ID to delete.
        :param kwargs:
        :return:
        """
        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            yield self._YomboAPI.request("DELETE",
                                         f"/v1/gateway/{gateway_id}",
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't delete gateway: {e.message}",
                "apimsg": f"Couldn't delete gateway: {e.message}",
                "apimsghtml": f"Couldn't delete gateway: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Gateway deleted.",
            "gateway_id": gateway_id,
        }

    @inlineCallbacks
    def enable_gateway(self, gateway_id, **kwargs):
        """
        Enable a gateway at the Yombo server level, not at the local gateway level.

        :param gateway_id: The gateway ID to enable.
        :param kwargs:
        :return:
        """
        api_data = {
            "status": 1,
        }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            yield self._YomboAPI.request("PATCH",
                                         f"/v1/gateway/{gateway_id}|",
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't enable gateway: {e.message}|",
                "apimsg": f"Couldn't enable gateway: {e.message}",
                "apimsghtml": f"Couldn't enable gateway: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Gateway enabled.",
            "gateway_id": gateway_id,
        }

    @inlineCallbacks
    def disable_gateway(self, gateway_id, **kwargs):
        """
        Enable a gateway at the Yombo server level, not at the local gateway level.

        :param gateway_id: The gateway ID to disable.
        :param kwargs:
        :return:
        """
        api_data = {
            "status": 0,
        }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            yield self._YomboAPI.request("PATCH",
                                         f"/v1/gateway/{gateway_id}",
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't disable gateway: {e.message}",
                "apimsg": f"Couldn't disable gateway: {e.message}",
                "apimsghtml": f"Couldn't disable gateway: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Gateway disabled.",
            "gateway_id": gateway_id,
        }

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
