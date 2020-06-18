"""
.. note::

  * For library documentation, see: `Download System data @ Library Documentation <https://yombo.net/docs/libraries/systemdatahandler>`_

Handles downloading system configurations at startup as well as any updates received from AMQP or the API.

During system run-time, any AMQP System Data changes are sent thru here for processing.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/systemdatahandler/__init__.html>`_
"""
# Import python libraries
from marshmallow.exceptions import ValidationError
import traceback
import sys

# Import twisted libraries
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants.library_references import LIBRARY_REFERENCES
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
import yombo.core.schemas as core_schemas

from yombo.constants.systemdatahandler import CONFIG_ITEMS

logger = get_logger("library.systemdatahandler")

PERSISTENT_DB_IDS = {  # Tables and IDs that shouldn't be purged.
    "locations": [
        "area_none", "location_none",
    ]
}


class SystemDataHandler(YomboLibrary):
    """
    Handles downloading system data and saving it to the database. If the system is running, it will send
    events as needed.
    """
    MAX_DOWNLOAD_CONCURRENT = 4  # config: misc:downloadmodulesconcurrent

    @inlineCallbacks
    def _init_(self):
        self.api_routes = {
            "categories": {
                "url": "/v1/categories"
            },
            "locations": {
                "url": f"/v1/locations"
            },
            "users": {
                "url": f"/v1/gateways/{self._gateway_id}/users"
            },
            "related_commands": {
                "url": f"/v1/gateways/{self._gateway_id}/relationships/commands"
            },
            "related_devices": {
                "url": f"/v1/gateways/{self._gateway_id}/relationships/devices",
                "query_params": ["include=variables"]
            },
            "related_device_command_inputs": {
                "url": f"/v1/gateways/{self._gateway_id}/relationships/device_command_inputs"
            },
            "related_device_types": {
                "url": f"/v1/gateways/{self._gateway_id}/relationships/device_types"
            },
            "related_device_type_commands": {
                "url": f"/v1/gateways/{self._gateway_id}/relationships/device_type_commands"
            },
            "related_gateways": {
                "url": f"/v1/gateways/{self._gateway_id}/relationships/gateways"
            },
            "related_input_types": {
                "url": f"/v1/gateways/{self._gateway_id}/relationships/input_types"
            },
            "related_modules": {
                "url": f"/v1/gateways/{self._gateway_id}/relationships/modules",
                "query_params": ["include=variables"]
            },
            "related_module_commits": {
                "url": f"/v1/gateways/{self._gateway_id}/relationships/module_commits"
            },
            "related_module_device_types": {
                "url": f"/v1/gateways/{self._gateway_id}/relationships/module_device_types"
            },
            "related_nodes": {
                "url": f"/v1/gateways/{self._gateway_id}/relationships/nodes"
            },
            "related_variable_group_devices": {
                "url": f"/v1/gateways/{self._gateway_id}/relationships/variable_groups_devices"
            },
            "related_variable_group_modules": {
                "url": f"/v1/gateways/{self._gateway_id}/relationships/variable_groups_modules"
            },
        }
        self.download_semaphore = defer.DeferredSemaphore(self.MAX_DOWNLOAD_CONCURRENT)  # used to queue deferreds
        self.download_list = []
        self.process_queue = []  # All downloaded configs are placed here. Only update the data one at a time.

        self.bulk_load = False
        self.db_existing_data = {}  # used to keep track of items to add, update, or delete
        self.db_completed_ids = {}  # [table][row_id]
        self.db_delete_ids = {}  # [table][row_id]
        self.db_insert_data = {}  # [table][row_id] = Dictionaries
        self.db_update_data = {}  # [table][row_id] = Dictionaries

        self.db_existing_ids = {}  # Track what ID's are already in the system.

        yield self.download_system_data()

    @inlineCallbacks
    def download_system_data(self, routes=None):
        self.bulk_load = True
        self.db_existing_ids = yield self._LocalDB.get_ids_for_yombo_api_tables()
        logger.debug("Existing IDs: {existing_ids}", existing_ids=self.db_existing_ids)

        if routes is None:
            routes = list(self.api_routes.keys())

        download_list = []
        for route in routes:
            logger.debug("getting data from: {route}", route=self.api_routes[route]["url"])
            query_params = ["page[size]=500"]
            if "query_params" in self.api_routes[route]:
                query_params += self.api_routes[route]["query_params"]
            downloader = self.download_semaphore.run(self._YomboAPI.request,
                                                     "GET",
                                                     f"{self.api_routes[route]['url']}",
                                                     query_params=query_params)
            downloader.addCallback(self.download_semaphore_process_results)
            download_list.append(downloader)
        dl = defer.DeferredList(download_list)
        yield dl
        logger.debug("Done downloading first round of configs.")
        while len(self.download_list) > 0:
            url = self.download_list.pop()
            data = yield self._YomboAPI.request("GET", url)
            self.download_semaphore_process_results(data)
        yield self.download_semaphore_process_results_done()

    def download_semaphore_process_results(self, data):
        if "links" in data.content:
            links = data.content["links"]
            if "next" in links and links["next"] is not None:
                self.download_list.append(links["next"])

        for source_type in ("data", "included"):
            if source_type in data.content:
                if isinstance(data.content[source_type], list):
                    for item in data.content[source_type]:
                        self.process_incoming(item)
                else:
                    self.process_incoming(data.content)
            # if "included" in data.content:
            #     if isinstance(data.content["included"], list):
            #         for item in data.content["included"]:
            #             self.process_incoming(item)
            #     else:
            #         self.process_incoming(data.content)

    @inlineCallbacks
    def download_semaphore_process_results_done(self):
        if self.bulk_load:
            for table, records in self.db_delete_ids.items():
                for completed_id in self.db_completed_ids[table]:  # delete items that were not sent to us.
                    if completed_id in self.db_existing_ids[table]:
                        del self.db_existing_ids[table][completed_id]
                for existing_id in self.db_existing_ids[table]:
                    if existing_id not in records:
                        records.append(existing_id)
                if table in PERSISTENT_DB_IDS:
                    for persist_id in PERSISTENT_DB_IDS[table]:
                        try:
                            records.remove(persist_id)
                        except:
                            pass
                if len(records) > 0:
                    yield self._LocalDB.database.db_delete_many(table, records)
            self.db_delete_ids = {}
            self.db_existing_ids = {}
            self.db_completed_ids = {}

            for table, records in self.db_update_data.items():
                if len(records) > 0:
                    save_data = []
                    for id, data in records.items():
                        save_data.append(data)
                    # print(f"sys data handler: updating: {table} - {save_data}")
                    if table in LIBRARY_REFERENCES:
                        klass = getattr(self, LIBRARY_REFERENCES[table]["class"])
                        if hasattr(klass, "_storage_pickled_fields"):
                            self._Tools.pickle_records(save_data, klass._storage_pickled_fields)
                    yield self._LocalDB.database.db_update_many(table, save_data, "id")
            self.db_update_data = {}

            for table, records in self.db_insert_data.items():
                if len(records) > 0:
                    save_data = []
                    for id, data in records.items():
                        save_data.append(data)
                    if table in LIBRARY_REFERENCES:
                        klass = getattr(self, LIBRARY_REFERENCES[table]["class"])
                        if hasattr(klass, "_storage_pickled_fields"):
                            save_data = self._Tools.pickle_records(save_data, klass._storage_pickled_fields)
                    yield self._LocalDB.database.db_insert(table, save_data)
            self.db_insert_data = {}

    def process_incoming(self, data_raw):
        """
        Processes incoming data from either the API or YomboAMQP

        :param data_raw: The data to add/update/delete.
        :type data_raw: dict
        :return:
        """
        item_type = data_raw["type"]

        if item_type not in CONFIG_ITEMS:
            logger.warn("Unknown API JSON type: {item_type}  Skipping data!", item_type=item_type)
            return

        config_data = CONFIG_ITEMS[item_type]
        current_table = config_data["table"]

        # logger.debug("process_incoming, schema 1: config_data: {config_data}", config_data=config_data)
        schema_class = getattr(core_schemas, config_data["schemaclass"])
        schema = schema_class()

        attributes = self.field_remap(data_raw["attributes"], config_data)

        try:
            data = schema.load(attributes)
        except ValidationError as e:
            logger.warn("Loading schema data error for: {item_type}", item_type=item_type)
            logger.warn("Error: {error}", error=e)
            print(e.__dict__)
            logger.warn("---------------==(Traceback)==--------------------------")
            logger.warn("{trace}", trace=traceback.format_exc())
            logger.warn("--------------------------------------------------------")
            return
        if self.bulk_load:
            should_be_deleted = False
            if current_table not in self.db_existing_ids:
                self.db_existing_ids[current_table] = []
            if current_table not in self.db_insert_data:
                self.db_insert_data[current_table] = {}
                self.db_update_data[current_table] = {}
            if current_table not in self.db_delete_ids:
                self.db_delete_ids[current_table] = []
            if current_table not in self.db_completed_ids:
                self.db_completed_ids[current_table] = []

            if "status" in data and data["status"] == 2:
                should_be_deleted = True
                if data["id"] in self.db_existing_ids[current_table] and \
                        data["id"] not in self.db_delete_ids[current_table]:
                    self.db_delete_ids[current_table].append(data["id"])

            if should_be_deleted is False:
                if data["id"] in self.db_existing_ids[current_table]:
                    # print("ID is in existing data...")
                    if "updated_at" in data:
                        # print(f"ID is in existing data...2: {self.db_existing_ids[current_table][data['id']]}")
                        if self.db_existing_ids[current_table][data["id"]] < data["updated_at"]:
                            # print("ID is in existing data...3")
                            self.db_update_data[current_table][data["id"]] = data
                else:
                    # print(f"New Data: {current_table} -> {data['id']}")
                    # print(f"ID is new data...4 {data}")
                    self.db_insert_data[current_table][data["id"]] = data

            if data["id"] not in self.db_completed_ids[current_table]:
                self.db_completed_ids[current_table].append(data["id"])

    def field_remap(self, data, config_data):
        """
        Takes incoming data from Yombo API or YomboAQMP and formats it so that we can add it
        to the database using the correct field names. Also removes fields that shouldn't belong.

        :param data:
        :param config_data:
        :return:
        """
        new_data = {}
        try:
            for key, value in data.items():
                if key in config_data["map"]:
                    new_data[config_data["map"][key]] = value
            return new_data
        except Exception as e:
            logger.error("---==(Error in field_rempa: {e})==---", e=e)
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")