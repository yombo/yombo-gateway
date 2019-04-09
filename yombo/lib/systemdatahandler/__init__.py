"""
.. note::

  * For library documentation, see: `Download System data @ Library Documentation <https://yombo.net/docs/libraries/systemdatahandler>`_

Handles downloading system configurations at startup as well as any updates received from AMQP or the API.

During system run-time, any AMQP System Data changes are sent thru here for processing.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import traceback
import sys

# Import twisted libraries
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary

from yombo.lib.systemdatahandler.constants import CONFIG_ITEM_MAP, CONFIG_ITEMS
from yombo.lib.localdb.schemas import *

logger = get_logger("library.systemdatahandler")


class SystemDataHandler(YomboLibrary, object):
    """
    Handles downloading system data and saving it to the database. If the system is running, it will send
    events as needed.
    """
    MAX_DOWNLOAD_CONCURRENT = 4  # config: misc:downloadmodulesconcurrent

    @inlineCallbacks
    def _init_(self):
        self.gwid = self._Configs.gateway_id()
        self.api_routes = {
            "categories": "/v1/categories",
            "locations": f"/v1/locations",
            "users": f"/v1/gateways/{self.gwid}/users",
            "related_commands": f"/v1/gateways/{self.gwid}/relationships/commands",
            "related_devices": f"/v1/gateways/{self.gwid}/relationships/devices?include=variables",
            "related_device_command_inputs": f"/v1/gateways/{self.gwid}/relationships/device_command_inputs",
            "related_device_types": f"/v1/gateways/{self.gwid}/relationships/device_types",
            "related_device_type_commands": f"/v1/gateways/{self.gwid}/relationships/device_type_commands",
            "related_gateways": f"/v1/gateways/{self.gwid}/relationships/gateways",
            "related_input_types": f"/v1/gateways/{self.gwid}/relationships/input_types",
            "related_modules": f"/v1/gateways/{self.gwid}/relationships/modules",
            "related_module_commits": f"/v1/gateways/{self.gwid}/relationships/module_commits",
            "related_module_device_types": f"/v1/gateways/{self.gwid}/relationships/module_device_types",
            "related_nodes": f"/v1/gateways/{self.gwid}/relationships/nodes",
            "related_variable_group_devices": f"/v1/gateways/{self.gwid}/relationships/variable_groups_devices",
            "related_variable_group_modules": f"/v1/gateways/{self.gwid}/relationships/variable_groups_modules",
        }
        self.download_semaphore = defer.DeferredSemaphore(self.MAX_DOWNLOAD_CONCURRENT)  # used to queue deferreds
        self.download_deferreds = []
        self.process_queue = []  # All downloaded configs are placed here. Only update the data one at a time.

        self.bulk_load = False
        self.db_existing_data = {}  # used to keep track of items to add, update, or delete
        self.db_completed_ids = {}  # [table][row_id]
        self.db_delete_ids = {}  # [table][row_id]
        self.db_insert_data = {}  # [table][row_id] = orderedDicts
        self.db_update_data = {}  # [table][row_id] = Dictionaries

        self.db_existing_ids = {}  # Track what ID's are already in the system.

        yield self.download_system_data()

    @inlineCallbacks
    def download_system_data(self, routes=None):
        # print("about to download system data....")
        self.bulk_load = True
        self.db_existing_ids = yield self._LocalDB.get_ids_for_remote_tables()
        logger.debug("Existing IDs: {existing_ids}", existing_ids=self.db_existing_ids)

        if routes is None:
            routes = list(self.api_routes.keys())

        for route in routes:
            logger.debug("getting data from: {route}", route=self.api_routes[route])
            d = self.download_semaphore.run(self._YomboAPI.request, "GET", self.api_routes[route])
            d.addCallback(self.download_semaphore_process_results)
            self.download_deferreds.append(d)
        dl = defer.DeferredList(self.download_deferreds)
        dl.addCallback(self.download_semaphore_process_results_done)
        yield dl

    def download_semaphore_process_results(self, data):
        if "data" in data.content:
            if isinstance(data.content["data"], list):
                for item in data.content["data"]:
                    self.process_incoming(item)
            else:
                self.process_incoming(data.content)
        if "included" in data.content:
            if isinstance(data.content["data"], list):
                for item in data.content["included"]:

                    self.process_incoming(item)
            else:
                self.process_incoming(data.content)

    @inlineCallbacks
    def download_semaphore_process_results_done(self, data):
        if self.bulk_load:
            for table, records in self.db_delete_ids.items():
                for completed_id in self.db_completed_ids[table]:  # delete items that were not sent to us.
                    if completed_id in self.db_existing_ids[table]:
                        del self.db_existing_ids[table][completed_id]
                for existing_id in self.db_existing_ids[table]:
                    if existing_id not in records:
                        records.append(existing_id)
                if len(records) > 0:
                    yield self._LocalDB.delete_many(table, records)
            self.db_delete_ids = {}
            self.db_existing_ids = {}
            self.db_completed_ids = {}

            for table, records in self.db_update_data.items():
                if len(records) > 0:
                    save_data = []
                    for id, data in records.items():
                        save_data.append(data)
                    yield self._LocalDB.update_many(table, save_data, "id")
            self.db_update_data = {}

            for table, records in self.db_insert_data.items():
                if len(records) > 0:
                    save_data = []
                    for id, data in records.items():
                        save_data.append(data)
                    yield self._LocalDB.insert_many(table, save_data)
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

        schema_class = globals()[config_data["schemaclass"]]
        schema = schema_class()

        attributes = self.field_remap(data_raw["attributes"], config_data)

        try:
            # print(f"{item_type}: {attributes}")
            data = schema.load(attributes)
        except Exception as e:
            logger.info("Loading schema data error for: {item_type}", item_type=item_type)
            logger.info("Error: {error}", error=e)
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.format_exc())
            logger.error("--------------------------------------------------------")
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