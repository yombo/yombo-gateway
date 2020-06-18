# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
This mixin adds database support to libraries or modules and allows them to access database systems
with a common API in a non-blocking manor. The primary use case for this mixin is the LocalDB library.

This mixin also handles migrations using the YoYo module. To use, simply set the 'database_yoyo_path'
to migration files compatible with YoYo.  See 'lib/localdb/migrations' path for an example.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/classes/database/__init__.html>`_
"""
# Import python libraries
from copy import deepcopy
import traceback
from typing import Any, ClassVar, Dict, Optional, Type
from sqlite3 import IntegrityError
import sys

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboCritical
from yombo.core.log import get_logger
from yombo.utils import sleep
from yombo.utils.decorators import cached

logger = get_logger("mixins.database")


class DatabaseMixin:
    """
    Manages all database interactions. Can be used by both modules and libraries to conenct to a database backend.
    """
    @inlineCallbacks
    def setup_database_connection(self) -> None:
        """
        Setup various database attributes. Will call the migration tool YoYo and perform any migrations
        Check to make sure the database exists. Will create if missing, will also update schema if any
        changes are required.

        Ensure the database is available:
          sqlite - That the file is available for reading
          mysql/mariadb - That we can connect to the database with the provided credentials.

        Also ensures that any pending migrations are complete.
        :return:
        """
        if self.database_type not in ("sqlite", "mysql", "mariadb"):
            raise YomboCritical("Only sqlite, mariabdb, or mysql databases are currently supported.")

        self.database = None  # Reference to the database connection.
        self.db_bulk_queue: Dict[str, Any] = {}
        self.db_bulk_queue_id_cols: Dict[str, Any] = {}
        self.db_pool = None
        self.db_model: Dict[str, dict] = {}  # store generated database model here.

        self.db_save_bulk_queue_running = False
        self.db_save_bulk_queue_run_again = False
        self.db_save_bulk_queue_loop = None
        self.db_cleanup_loop = None
        self.db_cleanup_running = False
        # self.db_model: dict = {}  # store generated database model here.

        logger.debug("Connecting to database, database type: '{db_type}'", db_type=self.database_type)
        if self.database_type == "sqlite":
            try:
                from yombo.mixins.database_mixin.connections.sqlite import SQLiteDB
            except Exception as e:
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
                logger.error("--------------------------------------------------------")
                logger.warn("Error loading SQLite connection handler: {e}", e=e)
            self.database = SQLiteDB(self)
        elif self.database_type == "mysql" or self.database_type == "mariadb":
            try:
                from yombo.mixins.database_mixin.connections.mysql import MySQL
            except Exception as e:
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
                logger.error("--------------------------------------------------------")
                logger.warn("Error loading SQLite connection handler: {e}", e=e)
            self.database = MySQL(self)
        else:
            logger.info("Connecting to database, database type: {db_type}", db_type=self.database_type)
            logger.info("Connecting to database, database type: {db_type}", db_type=type(self.database_type))
            logger.info("Connecting to database, database type: {db_type}", db_type=type(str(self.database_type)))
            raise YomboCritical(f"Unknown database type: {self.database_type}")

        yield maybeDeferred(self.database.init)
        self.db_pool = self.database.db_pool  # to be removed in future
        self.db_model = yield maybeDeferred(self.database.db_generate_model)
        # print(f"self.db_model: {self.db_model}")
        self.db_save_bulk_queue_loop = LoopingCall(self.db_save_bulk_queue, slow=True)
        self.db_save_bulk_queue_loop.start(5, False)
        self._CronTab.new(self.database.db_cleanup, mins=0, hours=3,  # Clean database at 3am every day.
                          label="Periodically clean the database.",
                          load_source="system")

    @inlineCallbacks
    def _unload_(self, **kwargs):
        yield self.db_save_bulk_queue()
        if self.db_save_bulk_queue_loop is not None and self.db_save_bulk_queue_loop.running:
            self.db_save_bulk_queue_loop.stop()

    ########################
    # Basic SQL Operations #
    ########################
    @inlineCallbacks
    def db_all(self, *args, **kwargs):
        """
        Get all table items. This is a wrapper to the database connection.

        results = yield db_all("some_table", columns)

        :param table: Name of the table to select from.
        :type table: str
        :param columns: List of columns to select, default is "*".
        :type columns: str
        """
        results = yield self.database.db_all(*args, **kwargs)
        return results

    @inlineCallbacks
    def db_delete(self, *args, **kwargs):
        """
        Delete item(s) from table. This is a wrapper to the database connection.

        results = yield db_delete("some_table", where=["label = ? AND status = ?", "mylabel", 1])

        :param table: Name of table to delete rows from
        :type table: str
        :param where: A list of arguments. The first item is a string for formatting, remaining items are the arguments.
        :type where: list
        """
        results = yield self.database.db_delete(*args, **kwargs)
        return results

    @inlineCallbacks
    def db_delete_many(self, *args, **kwargs):
        """
        Delete items from table

        :param table: Name of table to delete rows from
        :type table: str
        :param ids: List of id's to delete.
        :type ids: list
        :param id_column: Name of the column where the id's reside, default is 'id'.
        :type id_column: str
        """
        results = yield self.database.db_delete_many(*args, **kwargs)
        return results

    @inlineCallbacks
    def db_drop(self, *args, **kwargs):
        """
        Drop a database table.

        :param table: Name of table to drop
        :type table: str
        """
        results = yield self.database.db_drop(*args, **kwargs)
        return results

    @inlineCallbacks
    def db_insert(self, *args, **kwargs):
        """
        Insert a record (or a list of records) into a table.

        :param table: Table to insert records into.
        :type table: str
        :param vals: A dictionary or list of dictionaries of values to insert.
        :type vals: dict, List[dict]
        :param txn: If txn is given it will be used for the query, otherwise a typical runQuery will be used
        """
        results = yield self.database.db_insert(*args, **kwargs)
        return results

    @inlineCallbacks
    def db_select(self, *args, **kwargs):
        """
        Select records from a database table.

        results = yield select("some_table", where=["label = ? AND status = ?", "mylabel", 1])

        :param table: The database table to get rows from
        :param columns: Which columns to select, default is '*'.
        :param where: A list of arguments. The first item is a string for formatting, remaining items are the arguments.
        :param groupby: AKA GROUP BY - A group by string.
        :param limit: Limit the number of results. If limit is 1, then results will be a single dictionary item,
          otherwise a list of dictionaries will be returned.
        :param offset: An int to offset, must be used with limit.
        :param orderby: String describing how to order the results.
        :param row_id: If provided, builds a where statement to include this id.

        :return: If limit is 1 or id is set, then one dictionary or None if not found is returned. Otherwiwse,
          a list of dictionaries are returned.
        """
        results = yield self.database.db_select(*args, **kwargs)
        return results

    @inlineCallbacks
    def db_truncate(self, *args, **kwargs):
        """
        Remove all records from the table.

        :param table: Table to truncate all records from.
        :type table: str
        :return:
        """
        results = yield self.database.db_truncate(*args, **kwargs)
        return results

    @inlineCallbacks
    def db_update(self, *args, **kwargs):
        """
        Update a database record

        :param table: Table to update records.
        :type table: str
        :param args: Values to update.  Should be a dictionary in the form of
          {'name': value, 'othername': value}.
        :type args: dict
        :param where: Conditional of the same form as the where parameter nearly everywhere else.
        :type where: list
        :param limit: If limit is given it will limit the number of rows that are updated.
        :type limit: int
        """
        results = yield self.database.db_update(*args, **kwargs)
        return results

    @inlineCallbacks
    def db_update_many(self, *args, **kwargs):
        """
        Update a bunch of records. Currently, this just iterates the values in 'the_items' and calls db_update.

        :param table: Table to update records.
        :type table: str
        :param the_items: A list of dictionaries, like 'args' for db_update().
        :type the_items: List[dict]
        :param where_column: Which column within the dictionary to use for the where statement.
        :type where_column: str
        """
        results = yield self.database.db_update_many(*args, **kwargs)
        return results

    @cached(600)
    def db_get_table_columns(self, table: str) -> dict:
        if table in self.db_model:
            return list(self.db_model[table].keys())
        raise KeyError(f"Table not found: {table}")
    #
    # @inlineCallbacks
    # def load_test_data(self):
    #     logger.info("Loading databsae test data")
    #
    #     command = yield Command.find("command1")
    #     if command is None:
    #         command = yield Command(id="command1", machine_label="6on", label="O6n", public=1, status=1, created_at=1,
    #                                 updated_at=1).save()
    #
    #     device = yield Device.find("device1")
    #     if device is None:
    #         device = yield Device(id="device1", machine_label="on", label="light1", gateway_id="gateway1",
    #                               device_type_id="devicetype1", pin_required=0, pin_timeout=0, status=1, created_at=1,
    #                               updated_at=1, description="desc", notes="note").save()
    #         # variable = yield Variable(variable_type="device", variable_id="variable_id1", foreign_id="deviceVariable1", device_id=device.id, weigh=0, machine_label="device_var_1", label="Device Var 1", value="somevalue1", updated_at=1, created_at=1).save()
    #
    #     deviceType = yield DeviceType.find("devicetype1")
    #     if deviceType is None:
    #         deviceType = yield DeviceType(id=device.device_type_id, machine_label="x10_appliance", label="light1",
    #                                       device_class="x10", description="x10 appliances", status=1, created_at=1,
    #                                       updated_at=1).save()
    #         args = {"device_type_id": device.id, "command_id": command.id}
    #         yield self.dbconfig.insert("command_device_types", args)
    #
    #     device = yield Device.find("device1")
    #     # results = yield Variable.find(where=["variable_type = ? AND foreign_id = ?", "device", device.id])
    #
    # #          results = yield DeviceType.find(where=["id = ?", device.device_variables().get()

    def add_bulk_queue(self, table, queue_type, data, id_col=None, insert_blind=None):
        """
        Perform various activities against the database. For example, bulk inserts, updates, deletes, etc.

        add_bulk_queue("statistics", "insert", {"colname": "data1", "colname2": "data2"})

        :param table: The table to interact with.
        :param queue_type: One of: insert, update, or delete
        :param data: A dictionary of data items. This must be the complete record to update.
        :param id_col: Which column within the table to use for the ID row.
        :param insert_blind:
        :return:
        """
        if table not in self.db_model:
            raise KeyError(f"Table '{table}' doesn't exist in 'add_bulk_queue'.")
        if id_col is None:
            id_col = "id"
        self.db_bulk_queue_id_cols[table] = id_col

        if queue_type not in ("update", "insert", "delete"):
            return
        if table not in self.db_bulk_queue:
            self.db_bulk_queue[table] = {
                "insert": {},
                "insert_blind": [],
                "update": {},
                "delete": [],
            }

        # print(f"add_bulk_queue, data: {table} - {queue_type} - {data}")
        if queue_type == "insert":
            if insert_blind is True:
                self.db_bulk_queue[table]["insert_blind"].append(data)
            else:
                self.db_bulk_queue[table]["insert"][data["id"]] = data
        elif queue_type == "update":
            # Check if item exists in the insert first, just update that. Less DB work.
            if table in self.db_bulk_queue and data["id"] in self.db_bulk_queue[table]["insert"]:
                # print("add_bulk_queue - update, going to change update to insert")
                for key, value in data.items():
                    self.db_bulk_queue[table]["insert"][data["id"]][key] = value
            else:
                if data["id"] in self.db_bulk_queue[table]["update"]:
                    for key, value in data.items():
                        self.db_bulk_queue[table]["update"][data["id"]][key] = value
                elif data["id"] in self.db_bulk_queue[table]["update"]:
                    for key, value in data.items():
                        self.db_bulk_queue[table]["update"][data["id"]][key] = value
                else:
                    self.db_bulk_queue[table]["update"][data["id"]] = data
        elif queue_type == "delete":
            self.db_bulk_queue[table]["delete"].append(data["id"])

    @inlineCallbacks
    def db_save_bulk_queue(self, slow: Optional[bool] = None):
        """
        Saves the bulk data to the database.

        :param slow: If true, sleeps 1 second between tables to give the system breathing room.
        :return:
        """
        if len(self.db_bulk_queue) == 0:
            return

        if self.db_save_bulk_queue_running == True:
            self.db_save_bulk_queue_run_again = True
            return
        self.db_save_bulk_queue_running = True
        # print("saving bulk data: %s" % self.db_bulk_queue)
        for table in list(self.db_bulk_queue):
            # print("saving bulk table: %s" % table)
            table_data = deepcopy(self.db_bulk_queue[table])
            del self.db_bulk_queue[table]

            for queue_type in table_data.keys():
                if len(table_data[queue_type]) > 0:
                    data_values = table_data[queue_type].copy()
                    table_data[queue_type].clear()
                    if queue_type == "insert":
                        save_data = []
                        for key, value in data_values.items():
                            save_data.append(value)
                        try:
                            # print(f"save bulk queue, type {queue_type}, table: {table}, data: {save_data}")
                            yield self.db_insert(table, save_data)
                            yield sleep(0.01)
                        except IntegrityError as e:
                            logger.warn("Error trying to insert in bulk save: {e}", e=e)
                            logger.warn("Table: {table}, data: {save_data}", table=table, save_data=save_data)
                    elif queue_type == "insert_blind":
                        save_data = []
                        for data in data_values:
                            save_data.append(data)
                        try:
                            # print(f"save bulk queue, type {queue_type}, table: {table}, data: {save_data}")
                            yield self.db_insert(table, save_data)
                            yield sleep(0.01)
                        except IntegrityError as e:
                            logger.warn("Error trying to insert_blind in bulk save: {e}", e=e)
                            logger.warn("Table: {table}, data: {save_data}", table=table, save_data=save_data)
                    elif queue_type == "update":
                        save_data = []
                        for key, value in data_values.items():
                            save_data.append(value)
                        try:
                            # print(f"save bulk queue, type {queue_type}, table: {table}, data: {save_data}")
                            yield self.db_update_many(table, save_data, self.db_bulk_queue_id_cols[table])
                            yield sleep(0.01)
                        except IntegrityError as e:
                            logger.warn("Error trying to update_many in bulk save: {e}", e=e)
                            logger.warn("Table: {table}, data: {save_data}", table=table, save_data=save_data)
                    elif queue_type == "delete":
                        try:
                            # print(f"save bulk queue, type {queue_type}, table: {table}, data: {save_data}")
                            yield self.db_delete_many(table, data_values)
                            yield sleep(0.01)
                        except IntegrityError as e:
                            logger.warn("Error trying to delete_many in bulk save: {e}", e=e)
                            logger.warn("Table: {table}, data: {save_data}", table=table, save_data=save_data)

        self.db_save_bulk_queue_running = False
        if self.db_save_bulk_queue_run_again is True:
            self.db_save_bulk_queue_run_again = False
            yield self.db_save_bulk_queue()