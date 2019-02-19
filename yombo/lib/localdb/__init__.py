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
from yombo.utils import instance_properties, data_pickle, data_unpickle

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
    #    HASMANY = [{"name":"device_status", "class_name":"DeviceStatus", "foreign_key":"id", "association_foreign_key":"device_id"},
    #               {"name":"device_variables", "class_name":"DeviceVariable", "foreign_key":"id", "association_foreign_key":"device_id"}]
    HASMANY = [{"name": "device_status", "class_name": "DeviceStatus", "foreign_key": "device_id"},
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

class DeviceStatus(DBObject):
    TABLENAME = "device_status"
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


class ModuleInstalled(DBObject):
    TABLENAME = "module_installed"
    BELONGSTO = ["modules"]


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
Registry.register(Device, DeviceStatus, VariableData, DeviceType, Command)
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
from yombo.lib.localdb.devices import DB_Devices
from yombo.lib.localdb.devicetypes import DB_DeviceTypes
from yombo.lib.localdb.events import DB_Events
from yombo.lib.localdb.nodes import DB_Nodes
from yombo.lib.localdb.states import DB_States
from yombo.lib.localdb.statistics import DB_Statistics
from yombo.lib.localdb.storage import DB_Storage
from yombo.lib.localdb.variables import DB_Variables
from yombo.lib.localdb.websessions import DB_Websessions


class LocalDB(YomboLibrary, DB_Tools, DB_Devices, DB_DeviceTypes, DB_Events, DB_Nodes, DB_States,
              DB_Statistics, DB_Storage, DB_Variables, DB_Websessions):
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
        Registry.DBPOOL.runOperation("PRAGMA synchronous=2;")

        # used to cache datatables lookups for the webinterface viewers
        self.event_counts = self._Cache.ttl(ttl=15, tags="events")
        self.storage_counts = self._Cache.ttl(ttl=15, tags="storage")
        self.webinterface_counts = self._Cache.ttl(ttl=15, tags="webinterface_logs")

    def _start_(self, **kwargs):
        self.gateway_id = self._Configs.get("core", "gwid", "local", False)
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

    #########################
    ###    Commands     #####
    #########################
    @inlineCallbacks
    def get_commands(self, always_load=None):
        if always_load is None:
            always_load = False

        if always_load == True:
            records = yield self.dbconfig.select("commands", where=["always_load = ?", 1])
            return records
        elif always_load is False:
            records = yield self.dbconfig.select("commands", where=["always_load = ? OR always_load = ?", 1, 0])
            return records
        else:
            return []


    ###########################
    ###     Locations     #####
    ###########################

    @inlineCallbacks
    def get_locations(self, where=None):
        if where is not None:
            find_where = dictToWhere(where)
            records = yield Location.find(where=find_where)
        else:
            records = yield Location.find(orderby="label")
        return records

    @inlineCallbacks
    def insert_locations(self, data, **kwargs):
        location = Location()
        location.id = data["id"]
        location.location_type = data["location_type"]
        location.label = data["label"]
        location.machine_label = data["machine_label"]
        location.description = data.get("description", None)
        location.created_at = data["created_at"]
        location.updated_at = data["updated_at"]
        yield location.save()

    @inlineCallbacks
    def update_locations(self, location, **kwargs):
        args = {
            "location_type": location.location_type,
            "label": location.label,
            "machine_label": location.machine_label,
            "description": location.description,
            "updated_at": location.updated_at,
        }
        # print("saving notice update_locations: %s" % args)
        results = yield self.dbconfig.update("locations", args, where=["id = ?", location.location_id])
        return results

    @inlineCallbacks
    def delete_locations(self, location_id, **kwargs):
        results = yield self.dbconfig.delete("locations", where=["id = ?", location_id])
        return results


    ###########################################
    ###    Device Type Command Inputs     #####
    ###########################################
    @inlineCallbacks
    def device_type_command_inputs_get(self, device_type_id, command_id):
        records = yield DeviceCommandInput.find(
            where=["device_type_id = ? and command_id = ?", device_type_id, command_id])
        return records

    #########################
    ###    Gateways     #####
    #########################
    @inlineCallbacks
    def get_gateways(self, status=None):
        if status is True:
            records = yield self.dbconfig.select("gateways")
            return records
        elif status is None:
            records = yield self.dbconfig.select("gateways", where=["status = ? OR status = ?", 1, 0])
            return records
        else:
            records = yield self.dbconfig.select("gateways", where=["status = ?", status])
            return records

    #################
    ### GPG     #####
    #################
    @inlineCallbacks
    def delete_gpg_key(self, fingerprint):
        results = yield self.dbconfig.delete("gpg_keys",
                                             where=["fingerprint = ?", fingerprint])
        return results

    @inlineCallbacks
    def get_gpg_key(self, **kwargs):
        if "gwid" in kwargs:
            records = yield self.dbconfig.select(
                "gpg_keys",
                where=["endpoint_type = ? endpoint_id = ?", "gw", kwargs["gwid"]]
            )
        elif "keyid" in kwargs:
            records = yield self.dbconfig.select(
                "gpg_keys",
                where=["keyid = ?", kwargs["keyid"]])
        elif "fingerprint" in kwargs:
            records = yield self.dbconfig.select(
                "gpg_keys",
                where=["fingerprint = ?", kwargs["fingerprint"]])
        else:
            records = yield self.dbconfig.select("gpg_keys")

        keys = {}
        for record in records:
            key = {
                "fullname": record["fullname"],
                "comment": record["comment"],
                "email": record["email"],
                "endpoint_id": record["endpoint_id"],
                "endpoint_type": record["endpoint_type"],
                "fingerprint": record["fingerprint"],
                "keyid": record["keyid"],
                "publickey": record["publickey"],
                "length": record["length"],
                "have_private": record["have_private"],
                "ownertrust": record["ownertrust"],
                "trust": record["trust"],
                "algo": record["algo"],
                "type": record["type"],
                "expires_at": record["expires_at"],
                "created_at": record["created_at"],
            }
            keys[record["fingerprint"]] = key
        return keys

    @inlineCallbacks
    def insert_gpg_key(self, gwkey, **kwargs):
        key = GpgKey()
        key.keyid = gwkey["keyid"]
        key.fullname = gwkey["fullname"]
        key.comment = gwkey["comment"]
        key.email = gwkey["email"]
        key.endpoint_id = gwkey["endpoint_id"]
        key.endpoint_type = gwkey["endpoint_type"]
        key.fingerprint = gwkey["fingerprint"]
        key.publickey = gwkey["publickey"]
        key.length = gwkey["length"]
        key.ownertrust = gwkey["ownertrust"]
        key.trust = gwkey["trust"]
        key.algo = gwkey["algo"]
        key.type = gwkey["type"]
        key.expires_at = gwkey["expires_at"]
        key.created_at = gwkey["created_at"]
        key.have_private = gwkey["have_private"]
        if "notes" in gwkey:
            key.notes = gwkey["notes"]
        yield key.save()
        #        yield self.dbconfig.insert("gpg_keys", args, None, "OR IGNORE" )

    #############################
    ###    Input Types      #####
    #############################
    @inlineCallbacks
    def get_input_types(self, always_load=None):
        if always_load is None:
            always_load = False

        if always_load == True:
            records = yield self.dbconfig.select("input_types", where=["always_load = ?", 1], orderby="label")
            return records
        elif always_load is False:
            records = yield self.dbconfig.select("input_types", where=["always_load = ? OR always_load = ?", 1, 0],
                                                 orderby="label")
            return records
        else:
            return []

    #############################
    ###    Modules          #####
    #############################

    @inlineCallbacks
    def get_modules(self, get_all=False):
        if get_all is False:
            records = yield Modules.find(where=["status = ? OR status = ?", 1, 0])
        else:
            records = yield Modules.all()
        return records

    @inlineCallbacks
    def get_modules_view(self, get_all=False, where=None):
        if where is not None:
            records = yield Modules.find(where=where)
        elif get_all is False:
            records = yield ModulesView.find(where=["status = ?", 1])
        else:
            records = yield ModulesView.all()
        return records

    @inlineCallbacks
    def get_module_commits(self, module_id, branch, approved=None, aslist=None):
        print(f"get_module_commits: module_id={module_id}, branch={branch}, aslist={aslist}")
        if approved is None:
            records = yield ModuleCommits.find(where=["module_id = ? and branch = ?", module_id, branch],
                                               group="module_id, branch", orderby="id DESC"
                                               )
        else:
            records = yield ModuleCommits.find(where=["module_id = ? and branch = ? and approved = ?",
                                                      module_id, branch, approved],
                                               group="module_id, branch", orderby="id DESC"
                                               )
        if aslist is True:
            commits = []
            for record in records:
                commits.append(record.commit)
            return commits
        return records

    @inlineCallbacks
    def install_module(self, data):
        results = yield ModuleInstalled(module_id=data["module_id"],
                                        installed_branch=data["installed_branch"],
                                        installed_commit=data["installed_commit"],
                                        install_at=data["install_at"],
                                        last_check_at=data["last_check_at"],
                                        ).save()
        return results

    @inlineCallbacks
    def get_module_routing(self, where=None):
        """
        Used to load a list of deviceType routing information.

        Called by: lib.Modules::load_data

        :param where: Optional - Can be used to append a where statement
        :type returnType: string
        :return: Modules used for routing device message packets
        :rtype: list
        """
        records = yield ModuleRoutingView.all()
        return records

    @inlineCallbacks
    def set_module_status(self, module_id, status):
        """
        Used to set the status of a module. Shouldn't be used by developers.
        Used to load a list of deviceType routing information.

        Called by: lib.Modules::enable, disable, and delete

        :param module_id: Id of the module to updates
        :type module_id: string
        :param status: Value to set the status field.
        :type status: int
        """

        modules = yield Modules.find(where=["id = ?", module_id])
        if modules is None:
            return None
        module = modules[0]
        module.status = status
        results = yield module.save()
        return results

    #############################
    ###    Notifications    #####
    #############################
    @inlineCallbacks
    def get_notifications(self):
        cur_time = int(time())
        records = yield Notifications.find(where=["expire_at > ?", cur_time], orderby="created_at DESC")
        return records

    @inlineCallbacks
    def delete_notification(self, id):
        try:
            records = yield self.dbconfig.delete("notifications", where=["id = ?", id])
        except Exception as e:
            pass

    @inlineCallbacks
    def add_notification(self, notice, **kwargs):
        args = {
            "id": notice["id"],
            "gateway_id": notice["gateway_id"],
            "type": notice["type"],
            "priority": notice["priority"],
            "source": notice["source"],
            "expire_at": notice["expire_at"],
            "always_show": notice["always_show"],
            "always_show_allow_clear": notice["always_show_allow_clear"],
            "acknowledged": notice["acknowledged"],
            "acknowledged_at": notice["acknowledged_at"],
            "user": notice["user"],
            "title": notice["title"],
            "message": notice["message"],
            "local": notice["local"],
            "targets": data_pickle(notice["targets"], encoder="json"),
            "meta": data_pickle(notice["meta"], encoder="json"),
            "created_at": notice["created_at"],
        }
        results = yield self.dbconfig.insert("notifications", args, None, "OR IGNORE")
        return results

    @inlineCallbacks
    def update_notification(self, notice, **kwargs):
        args = {
            "type": notice.type,
            "priority": notice.priority,
            "source": notice.source,
            "expire_at": notice.expire_at,
            "always_show": notice.always_show,
            "always_show_allow_clear": notice.always_show_allow_clear,
            "acknowledged": notice.acknowledged,
            "acknowledged_at": notice.acknowledged_at,
            "user": notice.user,
            "title": notice.title,
            "message": notice.message,
            "meta": data_pickle(notice.meta, encoder="json"),
            "targets": data_pickle(notice.targets, encoder="json"),
        }
        results = yield self.dbconfig.update("notifications", args, where=["id = ?", notice.notification_id])
        return results

    @inlineCallbacks
    def select_notifications(self, where):
        find_where = dictToWhere(where)
        records = yield Notifications.find(where=find_where)
        items = []
        for record in records:
            items.append(instance_properties(record, "_"))

        return items

    #################
    ### SQLDict #####
    #################
    @inlineCallbacks
    def get_sql_dict(self, component, dict_name):
        records = yield self.dbconfig.select("sqldict", select="dict_data",
                                             where=["component = ? AND dict_name = ?", component, dict_name])
        for record in records:
            try:
                before = len(record["dict_data"])
                record["dict_data"] = data_unpickle(record["dict_data"], "msgpack_base85_zip")
                logger.debug("SQLDict Compression. With: {withcompress}, Without: {without}",
                             without=len(record["dict_data"]), withcompress=before)
            except:
                pass
        return records

    @inlineCallbacks
    def set_sql_dict(self, component, dict_name, dict_data):
        """
        Used to save SQLDicts to the database. This is from a loopingcall as well as
        shutdown of the gateway.

        Called by: lib.Loader::save_sql_dict

        :param component: Module/Library that is storing the data.
        :param dictname: Name of the dictionary that is used within the module/library
        :param key1: Key
        :param data1: Data
        :return: None
        """
        dict_data = data_pickle(dict_data, "msgpack_base85_zip")

        args = {"component": component,
                "dict_name": dict_name,
                "dict_data": dict_data,
                "updated_at": int(time()),
                }
        records = yield self.dbconfig.select("sqldict", select="dict_name",
                                             where=["component = ? AND dict_name = ?", component, dict_name])
        if len(records) > 0:
            results = yield self.dbconfig.update("sqldict", args,
                                                 where=["component = ? AND dict_name = ?", component, dict_name])
        else:
            args["created_at"] = args["updated_at"]
            results = yield self.dbconfig.insert("sqldict", args, None, "OR IGNORE")
        return results

    #########################
    ###    Tasks        #####
    #########################
    @inlineCallbacks
    def get_tasks(self, section):
        """
        Get all tasks for a given section.

        :return:
        """
        records = yield Tasks.find(where=["run_section = ?", section])

        results = []
        for record in records:
            data = record.__dict__
            data["task_arguments"] = data_unpickle(data["task_arguments"], "msgpack_base85_zip")
            results.append(data)  # we need a dictionary, not an object
        return results

    @inlineCallbacks
    def del_task(self, id):
        """
        Delete a task id.

        :return:
        """
        records = yield self.dbconfig.delete("tasks", where=["id = ?", id])
        return records

    @inlineCallbacks
    def add_task(self, data):
        """
        Get all tasks for a given section.

        :return:
        """
        data["task_arguments"] = data_pickle(data["task_arguments"], "msgpack_base85_zip")
        results = yield self.dbconfig.insert("tasks", data, None, "OR IGNORE")
        return results

    ###########################
    ###  Users              ###
    ###########################
    @inlineCallbacks
    def get_users(self):
        records = yield Users.all()
        return records

    ################################
    ###   Webinterface logs    #####
    ################################
    @inlineCallbacks
    def webinterface_save_logs(self, logs):
        yield self.dbconfig.insertMany("webinterface_logs", logs)

    @inlineCallbacks
    def search_webinterface_logs_for_datatables(self, order_column, order_direction, start, length, search=None):
        # print("search weblogs... order_column: %s, order_direction: %s, start: %s, length: %s, search:%s" %
        #       (order_column, order_direction, start, length, search))

        select_fields = [
            "request_at",
            '(CASE secure WHEN 1 THEN \'TLS/SSL\' ELSE \'Unsecure\' END || "<br>" || method || "<br>" || hostname || "<br>" || path) as request_info',
            # '(method || "<br>" || hostname || "<br>" || path) as request_info',
            "auth_id as user",
            '(ip || "<br>" || agent || "<br>" || referrer) as client_info',
            '(response_code || "<br>" || response_size) as response',
        ]

        if search in (None, ""):
            records = yield self.dbconfig.select(
                "webinterface_logs",
                select=", ".join(select_fields),
                limit=(length, start),
                orderby=f"{order_column} {order_direction}",
            )

            cache_name_total = "total"
            if cache_name_total in self.webinterface_counts:
                total_count = self.webinterface_counts[cache_name_total]
            else:
                total_count_results = yield self.dbconfig.select(
                    "webinterface_logs",
                    select="count(*) as count",
                )
                total_count = total_count_results[0]["count"]
                self.webinterface_counts[cache_name_total] = total_count
            return records, total_count, total_count

        else:
            where_fields = [f"request_at LIKE '%%{search}%%'",
                            f"request_protocol LIKE '%%{search}%%'",
                            f"referrer LIKE '%%{search}%%'",
                            f"agent LIKE '%%{search}%%'",
                            f"ip LIKE '%%{search}%%'",
                            f"hostname LIKE '%%{search}%%'",
                            f"method LIKE '%%{search}%%'",
                            f"path LIKE '%%{search}%%'",
                            f"secure LIKE '%%{search}%%'",
                            f"auth_id LIKE '%%{search}%%'",
                            f"response_code LIKE '%%{search}%%'",
                            f"response_size LIKE '%%{search}%%'"]

            if re.match("^[ \w-]+$", search) is None:
                raise YomboWarning("Invalid search string contents.")
            where_attrs_str = " OR ".join(where_fields)

            records = yield self.dbconfig.select(
                "webinterface_logs",
                select=", ".join(select_fields),
                where=[str(where_attrs_str)],
                limit=(length, start),
                orderby=f"{order_column} {order_direction}",
                debug=True
            )

            cache_name_total = "total"
            if cache_name_total in self.webinterface_counts:
                total_count = self.webinterface_counts[cache_name_total]
            else:
                total_count_results = yield self.dbconfig.select(
                    "webinterface_logs",
                    select="count(*) as count",
                )
                total_count = total_count_results[0]["count"]
                self.webinterface_counts[cache_name_total] = total_count

            cache_name_filtered = f"filtered {search}"
            if cache_name_filtered in self.webinterface_counts:
                filtered_count = self.webinterface_counts[cache_name_filtered]
            else:
                filtered_count_results = yield self.dbconfig.select(
                    "webinterface_logs",
                    select="count(*) as count",
                    where=[str(where_attrs_str)],
                    limit=(length, start),
                )
                filtered_count = filtered_count_results[0]["count"]
                self.webinterface_counts[cache_name_filtered] = filtered_count

            return records, total_count, filtered_count

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
    def select(self, table, select_cols):
        records = yield self.dbconfig.select(table, select=select_cols)
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
