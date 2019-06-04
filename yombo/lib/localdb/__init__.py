# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
A database API to SQLite3.

.. warning::

   These functions, variables, and classes **should not** be accessed directly
   by modules. These are documented here for completeness. Use (or create) a
   :ref:`utils <utils>` function to get what is needed.

.. note::

  * For library documentation, see: `LocalDB @ Library Documentation <https://yombo.net/docs/libraries/localdb>`_

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/localdb.html>`_
"""
# Import python libraries
import inspect
import re
import sys
from time import time

# Import 3rd-party libs
from yombo.ext.twistar.dbobject import DBObject
from yombo.ext.twistar.registry import Registry
from yombo.ext.twistar.utils import dictToWhere

# Import twisted libraries
from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.core.settings as settings
# from yombo.lib.systemdatahandler.constants import CONFIG_ITEMS
from yombo.utils import data_pickle, data_unpickle

logger = get_logger("library.localdb")

LATEST_SCHEMA_VERSION = 1


#### Various SQLite tables within the database. ####

class Category(DBObject):
    TABLENAME = "categories"


class Command(DBObject):
    HABTM = [dict(name="device_types", join_table="CommandDeviceTypes")]
    pass


class CommandDeviceTypes(DBObject):
    TABLENAME = "command_device_types"


class Events(DBObject):
    TABLENAME = "events"


class EventTypes(DBObject):
    TABLENAME = "event_types"


class Device(DBObject):
    #    HASMANY = [{"name":"device_states", "class_name":"DeviceStatus", "foreign_key":"id", "association_foreign_key":"device_id"},
    #               {"name":"device_variables", "class_name":"DeviceVariable", "foreign_key":"id", "association_foreign_key":"device_id"}]
    HASMANY = [{"name": "device_states", "class_name": "DeviceState", "foreign_key": "device_id"},
               {"name": "device_variables", "class_name": "DeviceVariable", "association_foreign_key": "device_id"}]
    HASONE = [{"name": "device_types", "class_name": "DeviceType", "foreign_key": "device_id",
               "association_foreign_key": "device_type_id"}]
    TABLENAME = "devices"


class DeviceCommandInput(DBObject):
    TABLENAME = "device_command_inputs"
    BELONGSTO = ["devices"]


class DeviceCommand(DBObject):
    TABLENAME = "device_commands"
    BELONGSTO = ["devices"]


class Location(DBObject):
    TABLENAME = "locations"
    BELONGSTO = ["devices"]


class DeviceState(DBObject):
    TABLENAME = "device_states"
    BELONGSTO = ["devices"]


class DeviceType(DBObject):
    TABLENAME = "device_types"


class DeviceTypeCommand(DBObject):
    TABLENAME = "device_type_commands"


class Gateway(DBObject):
    TABLENAME = "gateways"


class GpgKey(DBObject):
    TABLENAME = "gpg_keys"


class InputType(DBObject):
    TABLENAME = "input_types"


class Logs(DBObject):
    TABLENAME = "logs"


class Modules(DBObject):
    HASONE = [{"name": "module_installed", "class_name": "ModuleInstalled", "foreign_key": "module_id"}]
    HASMANY = [{"name": "module_device_types", "class_name": "ModuleDeviceTypes", "foreign_key": "module_id"}]
    TABLENAME = "modules"


class ModuleCommits(DBObject):
    BELONGSTO = ["modules"]
    TABLENAME = "module_commits"


class ModuleDeviceTypes(DBObject):
    BELONGSTO = ["devices"]
    TABLENAME = "module_device_types"


class ModuleDeviceTypesView(DBObject):
    TABLENAME = "module_device_types_view"


class ModuleInstalled(DBObject):
    TABLENAME = "module_installed"
    BELONGSTO = ["modules"]


class ModulesView(DBObject):
    TABLENAME = "modules_view"


class Node(DBObject):
    TABLENAME = "nodes"


class Notifications(DBObject):
    TABLENAME = "notifications"


class Roles(DBObject):
    TABLENAME = "roles"


class Sessions(DBObject):
    TABLENAME = "webinterface_sessions"


class Sqldict(DBObject):
    TABLENAME = "sqldict"


class States(DBObject):
    TABLENAME = "states"


class Statistics(DBObject):
    TABLENAME = "statistics"


class Storage(DBObject):
    TABLENAME = "storage"


class Tasks(DBObject):
    TABLENAME = "tasks"


class Users(DBObject):
    HASMANY = [{"name": "user_roles", "class_name": "UserRoles", "foreign_key": "user_id"}]
    TABLENAME = "users"


class UserRoles(DBObject):
    TABLENAME = "user_roles"


class VariableData(DBObject):
    TABLENAME = "variable_data"


class VariableFields(DBObject):
    TABLENAME = "variable_fields"


class VariableGroups(DBObject):
    TABLENAME = "variable_groups"


class VariableFieldDataView(DBObject):
    TABLENAME = "variable_field_data_view"


class VariableGroupFieldView(DBObject):
    TABLENAME = "variable_group_field_view"


class VariableGroupFieldDataView(DBObject):
    TABLENAME = "variable_group_field_data_view"


class WebinterfaceLogs(DBObject):
    TABLENAME = "webinterface_logs"

#### Views ####


class ModuleRoutingView(DBObject):
    TABLENAME = "module_routing_view"


Registry.SCHEMAS["PRAGMA_table_info"] = ["cid", "name", "type", "notnull", "dft_value", "pk"]
Registry.register(Device, DeviceState, VariableData, DeviceType, Command)
Registry.register(Modules, ModuleInstalled, ModuleDeviceTypes)
Registry.register(VariableGroups, VariableData)
Registry.register(Category)
Registry.register(DeviceTypeCommand)
Registry.register(Events)
Registry.register(EventTypes)
#Registry.setDebug(True)

TEMP_MODULE_CLASSES = inspect.getmembers(sys.modules[__name__])
MODULE_CLASSES = {}
for item in TEMP_MODULE_CLASSES:
    if isinstance(item, tuple) and len(item) == 2:
        if inspect.isclass(item[1]):
            if issubclass(item[1], DBObject):
                MODULE_CLASSES[item[0]] = item[1]
del TEMP_MODULE_CLASSES

from yombo.lib.localdb._tools import DB_Tools
from yombo.lib.localdb.commands import DB_Commands
from yombo.lib.localdb.devices import DB_Devices
from yombo.lib.localdb.devicecommands import DB_DeviceCommands
from yombo.lib.localdb.devicecommandinputs import DB_DeviceCommandInputs
from yombo.lib.localdb.devicetypes import DB_DeviceTypes
from yombo.lib.localdb.devicetypecommands import DB_DeviceTypeCommands
from yombo.lib.localdb.devicestates import DB_DevicesStates
from yombo.lib.localdb.events import DB_Events
from yombo.lib.localdb.gateways import DB_Gateways
from yombo.lib.localdb.gpg import DB_GPG
from yombo.lib.localdb.locations import DB_Locations
from yombo.lib.localdb.inputtypes import DB_InputTypes
from yombo.lib.localdb.modules import DB_Modules
from yombo.lib.localdb.moduledevicetypes import DB_ModuleDeviceTypes
from yombo.lib.localdb.nodes import DB_Nodes
from yombo.lib.localdb.notifications import DB_Notifications
from yombo.lib.localdb.sqldict import DB_SqlDict
from yombo.lib.localdb.states import DB_States
from yombo.lib.localdb.statistics import DB_Statistics
from yombo.lib.localdb.storage import DB_Storage
from yombo.lib.localdb.tasks import DB_Tasks
from yombo.lib.localdb.users import DB_Users
from yombo.lib.localdb.variables import DB_Variables
from yombo.lib.localdb.websessions import DB_Websessions
from yombo.lib.localdb.webinterfacelogs import DB_WebinterfaceLogs


class LocalDB(
    YomboLibrary,
    DB_Tools, DB_Commands, DB_Devices, DB_DeviceCommands, DB_DeviceCommandInputs, DB_DeviceTypes,
    DB_DeviceTypeCommands, DB_DevicesStates, DB_Events,
    DB_Gateways, DB_GPG, DB_Locations, DB_InputTypes, DB_Modules, DB_ModuleDeviceTypes,
    DB_Nodes, DB_Notifications, DB_SqlDict, DB_States,
    DB_Statistics, DB_Storage, DB_Tasks, DB_Users, DB_Variables, DB_Websessions, DB_WebinterfaceLogs):
    """
    Manages all database interactions.
    """
    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo local database library"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Check to make sure the database exists. Will create if missing, will also update schema if any
        changes are required.
        """
        self.working_dir = settings.arguments["working_dir"]
        self.db_bulk_queue = {}
        self.db_bulk_queue_id_cols = {}
        self.save_bulk_queue_loop = None
        self.cleanup_database_loop = None
        self.cleanup_database_running = False
        self.db_model = {}  # store generated database model here.
        self.remote_tables = ['auth_keys', 'categories', 'commands', 'devices', 'device_command_inputs',
                              'device_commands', 'device_types', 'device_type_commands', 'gateways', 'input_types',
                              'locations', 'modules', 'module_commits', 'module_device_types', 'nodes', 'users',
                              'variable_groups', 'variable_fields', 'variable_data']

        # Connect to the DB
        def show_connected(connection):
            connection.execute("PRAGMA foreign_keys = ON")

        Registry.DBPOOL = adbapi.ConnectionPool("sqlite3",
                                                f"{self.working_dir}/etc/yombo.sqlite3",
                                                check_same_thread=False,
                                                cp_min=1, cp_max=1, cp_openfun=show_connected)
        self.dbconfig = Registry.getConfig()
        # self._Events.new("localdb", "connected", (start_schema_version, current_schema_version))

        yield self._load_db_model()
        # print(self.db_model)
        Registry.DBPOOL.runOperation("PRAGMA synchronous=2;")

        # used to cache datatables lookups for the webinterface viewers
        self.event_counts = self._Cache.ttl(ttl=15, tags="events")
        self.storage_counts = self._Cache.ttl(ttl=15, tags="storage")
        self.webinterface_counts = self._Cache.ttl(ttl=15, tags="webinterface_logs")

    def _start_(self, **kwargs):
        self.save_bulk_queue_loop = LoopingCall(self.save_bulk_queue)
        self.save_bulk_queue_loop.start(17, False)
        self.cleanup_database_loop = LoopingCall(self.cleanup_database)
        self._CronTab.new(self.cleanup_database, min=0, hour=3, label="Periodically clean the database.", source="lib.localdb")  # Clean database at 3am every day.

    @inlineCallbacks
    def _unload_(self, **kwargs):
        yield self.save_bulk_queue()
        if self.save_bulk_queue_loop is not None and self.save_bulk_queue_loop.running:
            self.save_bulk_queue_loop.stop()

    def get_model_class(self, class_name):
        return globals()[class_name]

    @inlineCallbacks
    def get_dbitem_by_id(self, dbitem, db_id, status=None):
        if dbitem not in MODULE_CLASSES:
            raise YomboWarning("get_dbitem_by_id expects dbitem to be a DBObject")
        if status is None:
            records = yield MODULE_CLASSES[dbitem].find(where=["id = ?", db_id])
        else:
            records = yield MODULE_CLASSES[dbitem].find(where=["id = ? and status = ?", db_id, status])
        results = []
        for record in records:
            results.append(record.__dict__)  # we need a dictionary, not an object
        return results

    @inlineCallbacks
    def get_dbitem_by_id_dict(self, dbitem, where=None, status=None):
        if dbitem not in MODULE_CLASSES:
            raise YomboWarning("get_dbitem_by_id_dict expects dbitem to be a DBObject")
        if where is None:
            records = yield MODULE_CLASSES[dbitem].select()
        else:
            records = yield MODULE_CLASSES[dbitem].select(where=dictToWhere(where))
        return records

    @inlineCallbacks
    def get_ids_for_remote_tables(self):
        """
        Gets all the IDS for all tables that are remotely managed.

        :return:
        """
        ids = {}
        current_time = int(time())
        for table in self.remote_tables:
            ids[table] = {}
            select = "id"
            # print(f"db_model: {self.db_model[table]}")
            if "updated_at" in self.db_model[table]:
                select += ", updated_at"
            table_ids = yield self.dbconfig.select(table, select=select)
            for item in table_ids:
                if "updated_at" in self.db_model[table]:
                    ids[table][item['id']] = item['updated_at']
                else:
                    ids[table][item['id']] = current_time

            # print(f"get_ids_for_remote_tables Table: {table}, data: {ids[table]}")
        return ids

    #############################
    ## Generic SQL ##############
    #############################

    @inlineCallbacks
    def delete(self, table, where=None):
        """
        Delete items from table

        :param table:
        :return:
        """
        yield self.dbconfig.delete(table, where)

    @inlineCallbacks
    def delete_many(self, table, ids):
        """
        Delete items from table

        :param table:
        :return:
        """
        yield self.dbconfig.deleteMany(table, ids)

    @inlineCallbacks
    def drop_table(self, table):
        """
        Drop a database table.

        :param table:
        :param val:
        :return:
        """
        yield self.dbconfig.drop(table)

    @inlineCallbacks
    def insert_many(self, table, vals):
        """
        Insert a list of records into a table

        :param table:
        :param vals:
        :return:
        """
        # print("insert many: %s : %s" % (table, vals))
        yield self.dbconfig.insertMany(table, vals)

    @inlineCallbacks
    def insert(self, table, val):
        """
        Insert a record into a table.

        :param table:
        :param val:
        :return:
        """
        yield self.dbconfig.insert(table, val)

    @inlineCallbacks
    def select(self, table, select_cols, **kwargs):
        records = yield self.dbconfig.select(table, select=select_cols, **kwargs)
        return records

    @inlineCallbacks
    def update_many(self, table, vals, where_column):
        """
        Update a bunch of records in a transaction.

        :param table:
        :param vals:
        :return:
        """
        yield self.dbconfig.updateMany(table, vals, where_column)

    @inlineCallbacks
    def truncate(self, table):
        """
        Truncate table. SQLite doesn't have this feature. Instead, we drop the
        table and recreate it using the latest db meta version.

        :param table:
        :return:
        """
        yield self.drop_table(table)
        create_function = getattr(self.current_db_meta_file, "create_table_" + table)
        yield create_function(Registry)

    def _get_limit(self, **kwargs):
        limit = kwargs.get("limit", None)
        offset = kwargs.get("offset", None)
        if limit is None:
            return None
        if offset is None:
            return limit
        else:
            return (limit, offset)
