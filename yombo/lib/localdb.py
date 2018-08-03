# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
A database API to SQLite3.

.. warning::

   These functions, variables, and classes **should not** be accessed directly
   by modules. These are documented here for completeness. Use (or create) a
   :ref:`utils <utils>` function to get what is needed.

   If additional information is needed to/from the database, open a feature
   request at `<https://projects.yombo.net/>` under the Gateway Project.


.. note::

  For more information see: `LocalDB @ Module Development <https://yombo.net/docs/libraries/localdb>`_


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/localdb.html>`_
"""
# Import python libraries
from collections import OrderedDict
from sqlite3 import IntegrityError
import decimal
import inspect
from os import chmod
import sys
from time import time

# Import 3rd-party libs
from yombo.ext.twistar.registry import Registry
from yombo.ext.twistar.utils import dictToWhere
from yombo.ext.twistar.dbobject import DBObject

# Import twisted libraries
from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.core.settings as settings
from yombo.utils import clean_dict, instance_properties, data_pickle, data_unpickle, bytes_to_unicode
from yombo.utils.datatypes import coerce_value

logger = get_logger('library.localdb')

LATEST_SCHEMA_VERSION = 1


#### Various SQLite tables within the database. ####

class Category(DBObject):
    TABLENAME = 'categories'


class Command(DBObject):
    HABTM = [dict(name='device_types', join_table='CommandDeviceTypes')]
    pass


class CommandDeviceTypes(DBObject):
    TABLENAME = 'command_device_types'


class Config(DBObject):
    #    TABLENAME='devsadf'
    pass


class Device(DBObject):
    #    HASMANY = [{'name':'device_status', 'class_name':'DeviceStatus', 'foreign_key':'id', 'association_foreign_key':'device_id'},
    #               {'name':'device_variables', 'class_name':'DeviceVariable', 'foreign_key':'id', 'association_foreign_key':'device_id'}]
    HASMANY = [{'name': 'device_status', 'class_name': 'DeviceStatus', 'foreign_key': 'device_id'},
               {'name': 'device_variables', 'class_name': 'DeviceVariable', 'association_foreign_key': 'device_id'}]
    HASONE = [{'name': 'device_types', 'class_name': 'DeviceType', 'foreign_key': 'device_id',
               'association_foreign_key': 'device_type_id'}]
    TABLENAME = 'devices'


# pass

class DeviceCommandInput(DBObject):
    TABLENAME = 'device_command_inputs'
    BELONGSTO = ['devices']


class DeviceCommand(DBObject):
    TABLENAME = 'device_commands'
    BELONGSTO = ['devices']

class Location(DBObject):
    TABLENAME = 'locations'
    BELONGSTO = ['devices']

class DeviceStatus(DBObject):
    TABLENAME = 'device_status'
    BELONGSTO = ['devices']


class DeviceType(DBObject):
    TABLENAME = 'device_types'


class DeviceTypeCommand(DBObject):
    TABLENAME = 'device_type_commands'


class Gateway(DBObject):
    TABLENAME = 'gateways'


class GpgKey(DBObject):
    TABLENAME = 'gpg_keys'


class InputType(DBObject):
    TABLENAME = 'input_types'


class Logs(DBObject):
    TABLENAME = 'logs'


class ModuleInstalled(DBObject):
    TABLENAME = 'module_installed'
    BELONGSTO = ['modules']


class Modules(DBObject):
    HASONE = [{'name': 'module_installed', 'class_name': 'ModuleInstalled', 'foreign_key': 'module_id'}]
    HASMANY = [{'name': 'module_device_types', 'class_name': 'ModuleDeviceTypes', 'foreign_key': 'module_id'}]
    TABLENAME = 'modules'


class ModuleDeviceTypes(DBObject):
    BELONGSTO = ['devices']
    TABLENAME = 'module_device_types'


class ModuleDeviceTypesView(DBObject):
    TABLENAME = 'module_device_types_view'


class ModulesView(DBObject):
    TABLENAME = 'modules_view'


class Node(DBObject):
    TABLENAME = 'nodes'


class Notifications(DBObject):
    TABLENAME = 'notifications'


class Schema_Version(DBObject):
    TABLENAME = 'schema_version'


class Sqldict(DBObject):
    TABLENAME = 'sqldict'


class States(DBObject):
    TABLENAME = 'states'


class Statistics(DBObject):
    TABLENAME = 'statistics'


class Tasks(DBObject):
    TABLENAME = 'tasks'


class Users(DBObject):
    HASMANY = [{'name': 'user_roles', 'class_name': 'UserRoles', 'foreign_key': 'user_id'}]
    TABLENAME = 'users'


class UserRoles(DBObject):
    TABLENAME = 'user_roles'


class Roles(DBObject):
    TABLENAME = 'roles'


class VariableData(DBObject):
    TABLENAME = 'variable_data'


class VariableFields(DBObject):
    TABLENAME = 'variable_fields'


class VariableGroups(DBObject):
    TABLENAME = 'variable_groups'


class VariableFieldDataView(DBObject):
    TABLENAME = 'variable_field_data_view'


class VariableGroupFieldView(DBObject):
    TABLENAME = 'variable_group_field_view'


class VariableGroupFieldDataView(DBObject):
    TABLENAME = 'variable_group_field_data_view'

# class Variable(DBObject):
#     TABLENAME='variables'
#     BELONGSTO = ['devices', 'modules']


class ApiAuth(DBObject):
    TABLENAME = 'webinterface_api_auth'


class Sessions(DBObject):
    TABLENAME = 'webinterface_sessions'


class WebinterfaceLogs(DBObject):
    TABLENAME = 'webinterface_logs'

#### Views ####


class ModuleRoutingView(DBObject):
    TABLENAME = 'module_routing_view'


# Registry.register(Config)
Registry.SCHEMAS['PRAGMA_table_info'] = ['cid', 'name', 'type', 'notnull', 'dft_value', 'pk']
Registry.register(Device, DeviceStatus, VariableData, DeviceType, Command)
Registry.register(Modules, ModuleInstalled, ModuleDeviceTypes)
Registry.register(VariableGroups, VariableData)
Registry.register(Category)
Registry.register(DeviceTypeCommand)

TEMP_MODULE_CLASSES = inspect.getmembers(sys.modules[__name__])
MODULE_CLASSES = {}
for item in TEMP_MODULE_CLASSES:
    if isinstance(item, tuple) and len(item) == 2:
        if inspect.isclass(item[1]):
            if issubclass(item[1], DBObject):
                MODULE_CLASSES[item[0]] = item[1]
del TEMP_MODULE_CLASSES


class LocalDB(YomboLibrary):
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
        self.working_dir = settings.arguments['working_dir']
        self.db_bulk_queue = {}
        self.db_bulk_queue_id_cols = {}
        self.save_bulk_queue_loop = None
        def show_connected(connection):
            connection.execute("PRAGMA foreign_keys = ON")
        self.db_model = {}  # store generated database model here.
        # Connect to the DB
        Registry.DBPOOL = adbapi.ConnectionPool('sqlite3',
                                                "%s/etc/yombo.db" % self.working_dir,
                                                check_same_thread=False,
                                                cp_min=1, cp_max=1, cp_openfun=show_connected)
        self.dbconfig = Registry.getConfig()

        self.schema_version = 0
        self.database_file_is_new = None
        try:
            results = yield Schema_Version.find(where=['table_name = ?', 'core'])
            self.schema_version = results[0].version
            self.database_file_is_new = False
        except Exception as e:
            logger.debug("Problem with database: %s" % e)
            logger.info("Creating new database file.")
            self.database_file_is_new = True

        self.current_db_meta_file = __import__("yombo.utils.db." + str(LATEST_SCHEMA_VERSION), globals(), locals(),
                                   [str(LATEST_SCHEMA_VERSION)], 0)
        if self.database_file_is_new is False:
            # if existing, we will upgrade the database.
            start_schema_version = self.schema_version
            for z in range(self.schema_version + 1, LATEST_SCHEMA_VERSION + 1):
                imported_file = __import__("yombo.utils.db." + str(z), globals(), locals(), ['upgrade'], 0)
                results = yield imported_file.upgrade(Registry)

                self.dbconfig.update("schema_version",
                                     {'version': z},
                                     where=['table_name = ?', 'core'])
                # results = yield Schema_Version.all()
        else:
            # if new, we will just install the latest meta in the lastest version file.
            results = yield self.current_db_meta_file.new_db_file(Registry)

            self.dbconfig.update("schema_version",
                                 {'version': LATEST_SCHEMA_VERSION},
                                 where=['table_name = ?', 'core'])
            # results = yield Schema_Version.all()

        chmod("%s/etc/yombo.db" % self.working_dir, 0o600)

        yield self._load_db_model()

    def _load_(self, **kwargs):
        self.gateway_id = self._Configs.get('core', 'gwid', 'local', False)
        self.save_bulk_queue_loop = LoopingCall(self.save_bulk_queue)
        self.save_bulk_queue_loop.start(17, False)

    @inlineCallbacks
    def _stop_(self, **kwargs):
        yield self.save_bulk_queue()
        if self.save_bulk_queue_loop is not None and self.save_bulk_queue_loop.running:
            self.save_bulk_queue_loop.stop()

    def get_model_class(self, class_name):
        return globals()[class_name]()

    @inlineCallbacks
    def _load_db_model(self):
        """
        Inspect the DB and generate a model.

        :return:
        """
        tables = yield self.dbconfig.select('sqlite_master', select='tbl_name', where=['type = ?', 'table'])
        for table in tables:
            columns = yield self.dbconfig.pragma('table_info(%s)' % table['tbl_name'])
            self.db_model[table['tbl_name']] = OrderedDict()
            for column in columns:
                self.db_model[table['tbl_name']][column['name']] = column

    @inlineCallbacks
    def load_test_data(self):
        logger.info("Loading databsae test data")

        command = yield Command.find('command1')
        if command is None:
            command = yield Command(id='command1', machine_label='6on', label='O6n', public=1, status=1, created_at=1,
                                    updated_at=1).save()

        device = yield Device.find('device1')
        if device is None:
            device = yield Device(id='device1', machine_label='on', label='Lamp1', gateway_id='gateway1',
                                  device_type_id='devicetype1', pin_required=0, pin_timeout=0, status=1, created_at=1,
                                  updated_at=1, description='desc', notes='note', Voice_cmd_src='auto',
                                  voice_cmd='lamp on').save()
            # variable = yield Variable(variable_type='device', variable_id="variable_id1", foreign_id='deviceVariable1', device_id=device.id, weigh=0, machine_label='device_var_1', label='Device Var 1', value='somevalue1', updated_at=1, created_at=1).save()

        deviceType = yield DeviceType.find('devicetype1')
        if deviceType is None:
            deviceType = yield DeviceType(id=device.device_type_id, machine_label='x10_appliance', label='Lamp1',
                                          device_class='x10', description='x10 appliances', status=1, created_at=1,
                                          updated_at=1).save()
            args = {'device_type_id': device.id, 'command_id': command.id}
            yield self.dbconfig.insert('command_device_types', args)

        device = yield Device.find('device1')
        # results = yield Variable.find(where=['variable_type = ? AND foreign_id = ?', 'device', device.id])

    #          results = yield DeviceType.find(where=['id = ?', device.device_variables().get()

    @inlineCallbacks
    def get_dbitem_by_id(self, dbitem, id, status=None):
        if dbitem not in MODULE_CLASSES:
            raise YomboWarning("get_dbitem_by_id expects dbitem to be a DBObject")
        if status is None:
            records = yield MODULE_CLASSES[dbitem].find(where=['id = ?', id])
        else:
            records = yield MODULE_CLASSES[dbitem].find(where=['id = ? and status = ?', id, status])
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

    def add_bulk_queue(self, table, queue_type, data, id_col=None, insert_blind=None):
        if id_col is None:
            id_col = 'id'
        self.db_bulk_queue_id_cols[table] = id_col

        if queue_type not in ('update', 'insert', 'delete'):
            return
        if table not in self.db_bulk_queue:
            self.db_bulk_queue[table] = {
                'insert': {},
                'insert_blind': [],
                'update': {},
                'delete': [],
            }

        if queue_type == 'insert':
            if insert_blind is True:
                self.db_bulk_queue[table]['insert_blind'].append(data)
            else:
                self.db_bulk_queue[table][queue_type][data[id_col]] = data
        elif queue_type == 'update':
            if data[id_col] in self.db_bulk_queue[table]['insert']:
                for key, value in data.items():
                    self.db_bulk_queue[table]['insert'][data[id_col]][key] = value
            elif data[id_col] in self.db_bulk_queue[table]['update']:
                for key, value in data.items():
                    self.db_bulk_queue[table]['update'][data[id_col]][key] = value
            else:
                self.db_bulk_queue[table][queue_type][data[id_col]] = data
        elif queue_type == 'delete':
            self.db_bulk_queue[table][queue_type].append(data[id_col])

    @inlineCallbacks
    def save_bulk_queue(self):
        # print("saving bulk data: %s" % self.db_bulk_queue)
        for table in self.db_bulk_queue.keys():
            # print("saving bulk table: %s" % table)
            queues = self.db_bulk_queue[table]
            for queue_type in queues.keys():
                if len(self.db_bulk_queue[table][queue_type]) > 0:
                    db_data = self.db_bulk_queue[table][queue_type].copy()
                    self.db_bulk_queue[table][queue_type].clear()
                    if queue_type == 'insert':
                        send_data = []
                        for key, value in db_data.items():
                            send_data.append(value)
                        try:
                            yield self.insert_many(table, send_data)
                        except IntegrityError as e:
                            logger.warn("Error trying to insert_many in bulk save: {e}", e=e)
                    elif queue_type == 'update':
                        send_data = []
                        for key, value in db_data.items():
                            send_data.append(value)
                        try:
                            yield self.update_many(table, send_data, self.db_bulk_queue_id_cols[table])
                        except IntegrityError as e:
                            logger.warn("Error trying to update_many in bulk save: {e}", e=e)
                    elif queue_type == 'delete':
                        try:
                            yield self.delete_many(table, db_data)
                        except IntegrityError as e:
                            logger.warn("Error trying to delete_many in bulk save: {e}", e=e)

    @inlineCallbacks
    def make_backup(self, filename=None):
        if filename is None:
            filename = 'imarealbigtest.db'
        yield self.dbconfig.executeOperation(".backup %s" % filename)

    #########################
    ###    Commands     #####
    #########################
    @inlineCallbacks
    def get_commands(self, always_load=None):
        if always_load is None:
            always_load = False

        if always_load == True:
            records = yield self.dbconfig.select('commands', where=['always_load = ?', 1])
            return records
        elif always_load is False:
            records = yield self.dbconfig.select('commands', where=['always_load = ? OR always_load = ?', 1, 0])
            return records
        else:
            return []


    #########################
    ###    Devices      #####
    #########################

    @inlineCallbacks
    def get_devices(self, status=None):
        if status == True:
            records = yield Device.all()
#            return records
        elif status is None:
            records = yield Device.find(where=['status = ? OR status = ?', 1, 0])
        else:
            records = yield Device.find(where=['status = ? ', status])
        if len(records) > 0:
            for record in records:
                record = record.__dict__
                if record['energy_map'] is None:
                    record['energy_map'] = {"0.0": 0, "1.0": 0}
                else:
                    record['energy_map'] = data_unpickle(record['energy_map'], encoder='json')
        return records


    @inlineCallbacks
    def add_device(self, data, **kwargs):
        # print("add_device in lcoaldb: %s" % kwargs)
        device = Device()
        device.id = data['device_id']
        device.device_type_id = data['device_type_id']
        device.location_id = data['location_id']
        device.area_id = data['area_id']
        device.label = data['label']
        device.machine_label = data['machine_label']
        device.description = data['description']
        device.pin_required = data['pin_required']
        device.pin_code = data['pin_code']
        device.pin_timeout = data['pin_timeout']
        device.voice_cmd = data['voice_cmd']
        device.voice_cmd_order = data['voice_cmd_order']
        device.statistic_label = data['statistic_label']
        device.statistic_lifetime = data['statistic_lifetime']
        device.status = data['status']
        device.energy_tracker_device = data['energy_tracker_device']
        device.energy_tracker_source = data['energy_tracker_source']
        device.energy_map = data['energy_map']
        device.created_at = data['created_at']
        device.updated_at = data['updated_at']
        yield device.save()

    @inlineCallbacks
    def update_device(self, device, **kwargs):
        args = {
            'device_type_id': device.device_type_id,
            'location_id': device.location_id,
            'area_id': device.area_id,
            'machine_label': device.machine_label,
            'label': device.label,
            'description': device.description,
            'pin_required': device.pin_required,
            'pin_code': device.pin_code,
            'pin_timeout': device.pin_timeout,
            'voice_cmd': device.voice_cmd,
            'voice_cmd_order': device.voice_cmd_order,
            'statistic_label': device.statistic_label,
            'statistic_lifetime': device.statistic_lifetime,
            'status': device.enabled_status,
            'created_at': device.created_at,
            'updated_at': device.updated_at,
            'energy_tracker_device': device.energy_tracker_device,
            'energy_tracker_source': device.energy_tracker_source,
            'energy_map': data_pickle(device.energy_map, encoder='json'),
        }
        results = yield self.dbconfig.update('devices', args, where=['id = ?', device.device_id])
        return results

    @inlineCallbacks
    def delete_device(self, id, **kwargs):
        args = {
            'status': 2,
        }
        results = yield self.dbconfig.update('devices', args, where=['id = ?', id])
        return results

    @inlineCallbacks
    def set_device_status(self, device_id, status=1):
        yield self.dbconfig.update('devices', {'status': status},
                                             where=['id = ?', device_id])

    @inlineCallbacks
    def get_device_by_id(self, device_id, status=1):
        records = yield Device.find(where=['id = ? and status = ?', device_id, status])
        results = []
        for record in records:
            results.append(record.__dict__)  # we need a dictionary, not an object
        return results

    @inlineCallbacks
    def get_device_status(self, where, **kwargs):
        limit = self._get_limit(**kwargs)

        records = yield self.dbconfig.select('device_status',
                                             where=dictToWhere(where),
                                             orderby='set_at',
                                             limit=limit)
        data = []
        for record in records:
            record['source'] = "database"
            machine_status_extra = record['machine_status_extra']
            if machine_status_extra is None:
                record['machine_status_extra'] = None
            else:
                record['machine_status_extra'] = data_unpickle(machine_status_extra)

            requested_by = record['requested_by']
            if requested_by is None:
                record['requested_by'] = None
            else:
                record['requested_by'] = data_unpickle(requested_by)
            data.append(record)
        return data

    @inlineCallbacks
    def cleanup_device_status(self, days=None):
        """
        Remove old device status updates.  Long term info goes into statistics.

        :param days: Number of days to keep.
        :param kwargs:
        :return:
        """
        if days is None:
            days = 60

        results = yield self.dbconfig.delete('device_status', where=['set_at < ?', time()-(60*60*24*days)])
        return results

    @inlineCallbacks
    def get_device_commands(self, where, **kwargs):
        limit = self._get_limit(**kwargs)
        records = yield self.dbconfig.select('device_commands',
                                             where=dictToWhere(where),
                                             orderby='created_at DESC',
                                             limit=limit)
        data = []
        for record in records:
            record['source'] = "database"
            record['inputs'] = data_unpickle(record['inputs'])
            record['history'] = data_unpickle(record['history'])
            record['requested_by'] = data_unpickle(record['requested_by'])
            data.append(record)
        return data

    #############################
    ###    Device Types     #####
    #############################
    @inlineCallbacks
    def get_device_types(self, always_load=None):
        if always_load is None:
            always_load = False

        if always_load == True:
            records = yield self.dbconfig.select('device_types', where=['always_load = ?', 1])
            return records
        elif always_load is False:
            records = yield self.dbconfig.select('device_types', where=['always_load = ? OR always_load = ?', 1, 0])
            return records
        else:
            return []

    @inlineCallbacks
    def get_module_device_types(self, module_id):
        results = yield ModuleDeviceTypesView.find(where=['module_id = ?', module_id])
        records = []
        for item in results:
            temp = clean_dict(item.__dict__)
            del temp['errors']
            records.append(temp)
        return records

    @inlineCallbacks
    def get_device_type(self, id):
        records = yield DeviceType.find(where=['id = ?', id])
        return records

    @inlineCallbacks
    def get_addable_device_types(self):
        records = yield self.dbconfig.select('addable_device_types_view')
        return records

    ###########################
    ###     Locations     #####
    ###########################

    @inlineCallbacks
    def get_locations(self, where=None):
        if where is not None:
            find_where = dictToWhere(where)
            records = yield Location.find(where=find_where)
        else:
            records = yield Location.find(orderby='label')
        return records

    @inlineCallbacks
    def insert_locations(self, data, **kwargs):
        location = Location()
        location.id = data['id']
        location.location_type = data['location_type']
        location.label = data['label']
        location.machine_label = data['machine_label']
        location.description = data.get('description', None)
        location.created_at = data['created_at']
        location.updated_at = data['updated_at']
        yield location.save()

    @inlineCallbacks
    def update_locations(self, location, **kwargs):
        args = {
            'location_type': location.location_type,
            'label': location.label,
            'machine_label': location.machine_label,
            'description': location.description,
            'updated_at': location.updated_at,
        }
        # print("saving notice update_locations: %s" % args)
        results = yield self.dbconfig.update('locations', args, where=['id = ?', location.location_id])
        return results

    @inlineCallbacks
    def delete_locations(self, id, **kwargs):
        results = yield self.dbconfig.delete('locations', where=['id = ?', id])
        return results


    ###########################################
    ###    Device Type Command Inputs     #####
    ###########################################
    @inlineCallbacks
    def device_type_command_inputs_get(self, device_type_id, command_id):
        records = yield DeviceCommandInput.find(
            where=['device_type_id = ? and command_id = ?', device_type_id, command_id])
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
            records = yield self.dbconfig.select("gateways", where=['status = ? OR status = ?', 1, 0])
            return records
        else:
            records = yield self.dbconfig.select("gateways", where=['status = ?', status])
            return records

    #################
    ### GPG     #####
    #################
    @inlineCallbacks
    def delete_gpg_key(self, fingerprint):
        results = yield self.dbconfig.delete('gpg_keys',
                                             where=['fingerprint = ?', fingerprint])
        return results

    @inlineCallbacks
    def get_gpg_key(self, **kwargs):
        if 'gwid' in kwargs:
            records = yield self.dbconfig.select(
                "gpg_keys",
                where=['endpoint_type = ? endpoint_id = ?', 'gw', kwargs['gwid']]
            )
        elif 'keyid' in kwargs:
            records = yield self.dbconfig.select(
                "gpg_keys",
                where=['keyid = ?', kwargs['keyid']])
        elif 'fingerprint' in kwargs:
            records = yield self.dbconfig.select(
                "gpg_keys",
                where=['fingerprint = ?', kwargs['fingerprint']])
        else:
            records = yield self.dbconfig.select("gpg_keys")

        keys = {}
        for record in records:
            key = {
                'fullname': record['fullname'],
                'comment': record['comment'],
                'email': record['email'],
                'endpoint_id': record['endpoint_id'],
                'endpoint_type': record['endpoint_type'],
                'fingerprint': record['fingerprint'],
                'keyid': record['keyid'],
                'publickey': record['publickey'],
                'length': record['length'],
                'have_private': record['have_private'],
                'ownertrust': record['ownertrust'],
                'trust': record['trust'],
                'algo': record['algo'],
                'type': record['type'],
                'expires_at': record['expires_at'],
                'created_at': record['created_at'],
            }
            keys[record['keyid']] = key
        return keys

    @inlineCallbacks
    def insert_gpg_key(self, gwkey, **kwargs):
        key = GpgKey()
        key.keyid = gwkey['keyid']
        key.fullname = gwkey['fullname']
        key.comment = gwkey['comment']
        key.email = gwkey['email']
        key.endpoint_id = gwkey['endpoint_id']
        key.endpoint_type = gwkey['endpoint_type']
        key.fingerprint = gwkey['fingerprint']
        key.publickey = gwkey['publickey']
        key.length = gwkey['length']
        key.ownertrust = gwkey['ownertrust']
        key.trust = gwkey['trust']
        key.algo = gwkey['algo']
        key.type = gwkey['type']
        key.expires_at = gwkey['expires_at']
        key.created_at = gwkey['created_at']
        key.have_private = gwkey['have_private']
        if 'notes' in gwkey:
            key.notes = gwkey['notes']
        yield key.save()
        #        yield self.dbconfig.insert('gpg_keys', args, None, 'OR IGNORE' )

    #############################
    ###    Input Types      #####
    #############################
    @inlineCallbacks
    def get_input_types(self, always_load=None):
        if always_load is None:
            always_load = False

        if always_load == True:
            records = yield self.dbconfig.select('input_types', where=['always_load = ?', 1])
            return records
        elif always_load is False:
            records = yield self.dbconfig.select('input_types', where=['always_load = ? OR always_load = ?', 1, 0])
            return records
        else:
            return []

    #############################
    ###    Modules          #####
    #############################

    @inlineCallbacks
    def get_modules(self, get_all=False):
        if get_all is False:
            records = yield Modules.find(where=['status = ? OR status = ?', 1, 0])
        else:
            records = yield Modules.all()
        return records

    @inlineCallbacks
    def get_modules_view(self, get_all=False):
        if get_all is False:
            records = yield ModulesView.find(where=['status = ?', 1])
        else:
            records = yield ModulesView.all()

        return records

    @inlineCallbacks
    def modules_install_new(self, data):
        results = yield ModuleInstalled(module_id=data['module_id'],
                                        installed_version=data['installed_version'],
                                        install_at=data['install_at'],
                                        last_check=data['last_check'],
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

        modules = yield Modules.find(where=['id = ?', module_id])
        if modules is None:
            return None
        module = modules[0]
        module.status = status
        results = yield module.save()
        return results

    #############################
    ###    Nodes            #####
    #############################

    @inlineCallbacks
    def get_nodes(self):
        records = yield self.dbconfig.select('nodes', where=['destination = ?', 'gw'])
        for record in records:
            record['data'] = data_unpickle(record['data'], record['data_content_type'])
        return records

    @inlineCallbacks
    def get_node(self, node_id):
        record = yield Node.select(where=['id = ?', node_id], limit=1)
        record['node_id'] = record['id']
        del record['id']
        # attempt to decode the data..
        record['data'] = data_unpickle(record['data'], record['data_content_type'])
        return record
    #
    # @inlineCallbacks
    # def get_node_siblings(self, node):
    #     records = yield Node.select(where=['parent_id = ? and node_type = ?', node.parent_id, node.node_type])
    #     for record in records:
    #         record['data'] = data_unpickle(record['data'], record['data_content_type'])
    #     return records
    #
    # @inlineCallbacks
    # def get_node_children(self, node):
    #     records = yield Node.select(where=['parent_id = ? and node_type = ?', node.id, node.node_type])
    #     for record in records:
    #         record['data'] = data_unpickle(record['data'], record['data_content_type'])
    #     return records

    @inlineCallbacks
    def add_node(self, data, **kwargs):
        node = Node()
        node.id = data.node_id
        node.parent_id = data.parent_id
        node.gateway_id = data.gateway_id
        node.node_type = data.node_type
        node.weight = data.weight
        node.label = data.label
        node.machine_label = data.machine_label
        node.always_load = data.always_load
        node.destination = data.destination
        node.data = data_pickle(data.data, data.data_content_type)
        node.data_content_type = data.data_content_type
        node.status = data.status
        node.updated_at = data.updated_at
        node.created_at = data.created_at
        yield node.save()

    @inlineCallbacks
    def update_node(self, node, **kwargs):
        args = {
            'parent_id': node.parent_id,
            'gateway_id': node.gateway_id,
            'node_type': node.node_type,
            'weight': node.weight,
            'label': node.label,
            'machine_label': node.machine_label,
            'always_load': node.always_load,
            'destination': node.destination,
            'data': data_pickle(node.data, node.data_content_type),
            'data_content_type': node.data_content_type,
            'status': node.status,
            'created_at': node.created_at,
            'updated_at': node.updated_at,
        }
        results = yield self.dbconfig.update('nodes', args, where=['id = ?', node.node_id])
        return results


    @inlineCallbacks
    def delete_node(self, node_id):
        results = yield self.dbconfig.delete('nodes', where=['id = ?', node_id])
        return results

    #############################
    ###    Notifications    #####
    #############################
    @inlineCallbacks
    def get_notifications(self):
        cur_time = int(time())
        records = yield Notifications.find(where=['expire_at > ?', cur_time], orderby='created_at DESC')
        return records

    @inlineCallbacks
    def delete_notification(self, id):
        try:
            records = yield self.dbconfig.delete('notifications', where=['id < ?', id])
        except Exception as e:
            pass

    @inlineCallbacks
    def delete_expired_notifications(self):
        records = yield self.dbconfig.delete('notifications', where=['expire_at < ?', time()])
        return records

    @inlineCallbacks
    def add_notification(self, notice, **kwargs):
        args = {
            'id': notice['id'],
            'gateway_id': notice['gateway_id'],
            'type': notice['type'],
            'priority': notice['priority'],
            'source': notice['source'],
            'expire_at': notice['expire_at'],
            'always_show': notice['always_show'],
            'always_show_allow_clear': notice['always_show_allow_clear'],
            'acknowledged': notice['acknowledged'],
            'acknowledged_at': notice['acknowledged_at'],
            'user': notice['user'],
            'title': notice['title'],
            'message': notice['message'],
            'local': notice['local'],
            'targets': data_pickle(notice['targets'], encoder='json'),
            'meta': data_pickle(notice['meta'], encoder='json'),
            'created_at': notice['created_at'],
        }
        results = yield self.dbconfig.insert('notifications', args, None, 'OR IGNORE')
        return results

    @inlineCallbacks
    def update_notification(self, notice, **kwargs):
        args = {
            'type': notice.type,
            'priority': notice.priority,
            'source': notice.source,
            'expire_at': notice.expire_at,
            'always_show': notice.always_show,
            'always_show_allow_clear': notice.always_show_allow_clear,
            'acknowledged': notice.acknowledged,
            'acknowledged_at': notice.acknowledged_at,
            'user': notice.user,
            'title': notice.title,
            'message': notice.message,
            'meta': data_pickle(notice.meta, encoder='json'),
            'targets': data_pickle(notice.targets, encoder='json'),
        }
        results = yield self.dbconfig.update('notifications', args, where=['id = ?', notice.notification_id])
        return results

    @inlineCallbacks
    def select_notifications(self, where):
        find_where = dictToWhere(where)
        records = yield Notifications.find(where=find_where)
        items = []
        for record in records:
            items.append(instance_properties(record, '_'))

        return items

    #########################
    ###  API AUTH       #####
    #########################
    @inlineCallbacks
    def get_api_auth(self, auth_id=None):
        if auth_id is None:
            records = yield ApiAuth.all()
            if len(records) == 0:
                return []
            output = []
            for record in records:
                record.auth_data = data_unpickle(record.auth_data)
                record.roles = data_unpickle(record.roles)
                output.append({
                    'auth_id': record.id,
                    'label': record.label,
                    'description': record.description,
                    'is_valid': coerce_value(record.is_valid, 'bool'),
                    'auth_data': record.auth_data,
                    'roles': record.roles,
                    'created_at': record.created_at,
                    'last_access': record.last_access,
                    'updated_at': record.updated_at,
                })
            return output
        else:
            record = yield ApiAuth.find(auth_id, where=['is_valid = 1'])
            if record is None:
                raise YomboWarning("No API Keys found.")
            record.auth_data = data_unpickle(record.auth_data)
            record.roles = data_unpickle(record.roles)
            return {
                'auth_id': record.id,
                'label': record.label,
                'description': record.description,
                'is_valid': coerce_value(record.is_valid, 'bool'),
                'auth_data': record.auth_data,
                'roles': record.roles,
                'created_at': record.created_at,
                'last_access': record.last_access,
                'updated_at': record.updated_at,
            }

    @inlineCallbacks
    def save_api_auth(self, api_auth):
        args = {
            'id': api_auth.auth_id,
            'label': api_auth.label,
            'description': api_auth.description,
            'is_valid': coerce_value(api_auth.is_valid, 'int'),
            'auth_data': data_pickle(api_auth.auth_data),
            'roles': data_pickle(api_auth.roles),
            'created_at': api_auth.created_at,
            'last_access': api_auth.last_access,
            'updated_at': api_auth.updated_at,
        }
        print("save_api_auth: %s" % args)
        yield self.dbconfig.insert('webinterface_api_auth', args, None, 'OR IGNORE')

    @inlineCallbacks
    def update_api_auth(self, api_auth):
        args = {
            'label': api_auth.label,
            'description': api_auth.description,
            'auth_data': data_pickle(api_auth.auth_data),
            'roles': data_pickle(api_auth.roles),
            'is_valid': coerce_value(api_auth.is_valid, 'bool'),
            'last_access': api_auth.last_access,
            'updated_at': api_auth.updated_at,
            }
        yield self.dbconfig.update('webinterface_api_auth', args, where=['id = ?', api_auth.auth_id])

    @inlineCallbacks
    def rotate_api_auth(self, old_id, new_id):
        args = {
            'id': new_id,
            }
        yield self.dbconfig.update('webinterface_api_auth', args, where=['id = ?', old_id])

    @inlineCallbacks
    def delete_api_auth(self, auth_id):
        yield self.dbconfig.delete('webinterface_api_auth', where=['id = ?', auth_id])

    #########################
    ###  Web  Sessions    ###
    #########################
    @inlineCallbacks
    def get_web_session(self, session_id=None):
        def parse_record(data):
            save_data = data_unpickle(data.session_data)
            return {
                'id': data.id,
                'is_valid': coerce_value(data.is_valid, 'bool'),
                'auth_id': save_data.get('auth_id', None),
                'auth_at': save_data.get('auth_at', 0),
                'auth_pin': save_data.get('auth_pin', False),
                'auth_pin_at': save_data.get('auth_pin_at', 0),
                'created_by': save_data.get('created_by', "unknown"),
                'gateway_id': data.gateway_id,
                'session_data': save_data.get('session_data', {}),
                'created_at': data.created_at,
                'last_access': data.last_access,
                'updated_at': data.updated_at,
            }

        if session_id is None:
            records = yield Sessions.all()
            if len(records) == 0:
                raise YomboWarning("Session not found in deep storage.")
            output = []
            for record in records:
                output.append(parse_record(record))
            return output
        else:
            record = yield Sessions.find(session_id)
            if record is None:
                raise YomboWarning("Session not found in deep storage.")
            return parse_record(record)

    @inlineCallbacks
    def save_web_session(self, session):
        save_data = data_pickle({
            'session_data': session.session_data,
            'auth_id': session.auth_id,
            'auth_at': session.auth_at,
            'auth_pin': session.auth_pin,
            'auth_pin_at': session.auth_pin_at,
            'created_by': session.created_by,
        })

        args = {
            'id': session.session_id,
            'is_valid': coerce_value(session.is_valid, 'int'),
            'gateway_id': session.gateway_id,
            'session_data': save_data,
            'created_at': session.created_at,
            'last_access': session.last_access,
            'updated_at': session.updated_at,
        }
        yield self.dbconfig.insert('webinterface_sessions', args, None, 'OR IGNORE')

    @inlineCallbacks
    def update_web_session(self, session):
        save_data = data_pickle({
            'session_data': session.session_data,
            'auth_id': session.auth_id,
            'auth_at': session.auth_at,
            'auth_pin': session.auth_pin,
            'auth_pin_at': session.auth_pin_at,
            'created_by': session.created_by,
        })

        args = {
            'is_valid': coerce_value(session.is_valid, 'int'),
            'session_data': save_data,
            'last_access': session.last_access,
            'updated_at': session.updated_at,
            }
        yield self.dbconfig.update('webinterface_sessions', args, where=['id = ?', session.session_id])

    @inlineCallbacks
    def delete_web_session(self, session_id):
        yield self.dbconfig.delete('webinterface_sessions', where=['id = ?', session_id])

    #########################
    ###    States      #####
    #########################
    @inlineCallbacks
    def get_states(self, name=None):
        """
        Gets the last version of a state. Note: Only returns states that were set within the last 60 days.

        :param name:
        :return:
        """
        if name is not None:
            extra_where = "AND name = %s" % name
        else:
            extra_where = ''

        sql = """SELECT name, gateway_id, value, value_type, live, created_at, updated_at
FROM states s1
WHERE created_at = (SELECT MAX(created_at) from states s2 where s1.id = s2.id)
%s
AND created_at > %s
GROUP BY name""" % (extra_where, str(int(time()) - 60 * 60 * 24 * 60))
        states = yield Registry.DBPOOL.runQuery(sql)
        results = []
        for state in states:
            results.append({
                'name': state[0],
                'gateway_id': state[1],
                'value': state[2],
                'value_type': state[3],
                'live': state[4],
                'created_at': state[5],
                'updated_at': state[6],
            })
        return results

    @inlineCallbacks
    def get_state_count(self, name=None, gateway_id=None):
        """
        Get a count of historical values for state

        :param name:
        :return:
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        count = yield States.count(where=['name = ? and gateway_id = ?', name, gateway_id])
        return count

    @inlineCallbacks
    def del_state(self, name=None, gateway_id=None):
        """
        Deletes all history of a state. (Deciding to implement)

        :param name:
        :return:
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        count = yield self.dbconfig.delete('states', where=['name = ? and gateway_id = ?', name, gateway_id])
        return count

    @inlineCallbacks
    def get_state_history(self, name, limit=None, offset=None, gateway_id=None):
        """
        Get an state history.

        :param name:
        :param limit:
        :param offset:
        :return:
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        if limit is None:
            limit = 1

        if offset is not None:
            limit = (limit, offset)

        where = {
            'name': name,
        }
        # if gateway_id is not None:
        #     where['gateway_id'] = gateway_id
        sql_where = dictToWhere(where)

        results = yield States.find(where=sql_where, limit=limit)
        records = []
        for item in results:
            temp = clean_dict(item.__dict__)
            del temp['errors']
            records.append(temp)
        return records

    @inlineCallbacks
    def save_state(self, name, values):
        if values['live'] is True:
            live = 1
        else:
            live = 0

        if values['gateway_id'] == 'local':
            return
        yield States(
            gateway_id=values['gateway_id'],
            name=name,
            value=values['value'],
            value_type=values['value_type'],
            live=live,
            created_at=values['created_at'],
            updated_at=values['updated_at'],
        ).save()

    @inlineCallbacks
    def save_state_bulk(self, states):
        results = yield self.dbconfig.insertMany('states', states)
        return results

    @inlineCallbacks
    def clean_states_table(self, name=None):
        """
        Remove records over 60 days, only keep the last 100 records for a given state. So save history for longer
        term, use the statistics library.

        :param name:
        :return:
        """
        sql = "DELETE FROM states WHERE created_at < %s" % str(int(time()) - 60 * 60 * 24 * 60)
        yield Registry.DBPOOL.runQuery(sql)
        sql = """DELETE FROM states WHERE id IN
              (SELECT id
               FROM states AS s
               WHERE s.name = states.name
               ORDER BY created_at DESC
               LIMIT -1 OFFSET 100)"""
        yield Registry.DBPOOL.runQuery(sql)

    #################
    ### SQLDict #####
    #################
    @inlineCallbacks
    def get_sql_dict(self, component, dict_name):
        records = yield self.dbconfig.select('sqldict', select='dict_data',
                                             where=['component = ? AND dict_name = ?', component, dict_name])
        for record in records:
            try:
                before = len(record['dict_data'])
                record['dict_data'] = data_unpickle(record['dict_data'], 'msgpack_base85_zip')
                logger.debug("SQLDict Compression. With: {withcompress}, Without: {without}",
                             without=len(record['dict_data']), withcompress=before)
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
        dict_data = data_pickle(dict_data, 'msgpack_base85_zip')

        args = {'component': component,
                'dict_name': dict_name,
                'dict_data': dict_data,
                'updated_at': int(time()),
                }
        records = yield self.dbconfig.select('sqldict', select='dict_name',
                                             where=['component = ? AND dict_name = ?', component, dict_name])
        if len(records) > 0:
            results = yield self.dbconfig.update('sqldict', args,
                                                 where=['component = ? AND dict_name = ?', component, dict_name])
        else:
            args['created_at'] = args['updated_at']
            results = yield self.dbconfig.insert('sqldict', args, None, 'OR IGNORE')
        return results

    #####################
    ### Statistics  #####
    #####################
    @inlineCallbacks
    def get_distinct_stat_names(self, name=None, search_name_all=None, search_name_start=None,
                                search_name_end=None, bucket_type=None):
        where = {}
        dictToWhere
        if bucket_type is not None:
            where['bucket_type'] = bucket_type
        if name is not None:
            where['bucket_name'] = name
        if search_name_all is not None:
            where['bucket_name'] = ["%%%s%%" % search_name_all, 'like']
        if search_name_start is not None:
            where['bucket_name'] = ["%s%%" % search_name_start, 'like']
        if search_name_end is not None:
            where['bucket_name'] = ["%%%s" % search_name_end, 'like']

        # print("searching these stats: %s" % dict(where))
        records = yield self.dbconfig.select('statistics',
             where=dictToWhere(where),
             select='bucket_name, bucket_type, bucket_size, bucket_lifetime, MIN(bucket_time) as bucket_time_min, MAX(bucket_time) as bucket_time_max, count(*) as count',
             group='bucket_name')
        return records

    @inlineCallbacks
    def get_statistic(self, where):
        find_where = dictToWhere(where)
        records = yield Statistics.find(where=find_where)
        return records

    @inlineCallbacks
    def statistic_get_range(self, names, start, stop, minimal=None):
        if isinstance(names, list) is False:
            raise YomboWarning("statistic_get_range: names argument expects a list.")
        if isinstance(start, int) is False and isinstance(start, float) is False:
            raise YomboWarning("statistic_get_range: start argument expects an int or float, got: %s" % start)
        if isinstance(stop, int) is False and isinstance(stop, float) is False:
            # print("stop is typE: %s" % type(stop))
            raise YomboWarning("statistic_get_range: stop argument expects an int or float, got: %s" % stop)

        # names_str = ", ".join(map(str, names))
        names_str = ', '.join('"{0}"'.format(w) for w in names)
        sql = """SELECT id, bucket_time, bucket_size, bucket_lifetime, bucket_type, bucket_name,
 bucket_value, bucket_average_data, anon, uploaded, finished, updated_at 
 FROM  statistics WHERE bucket_name in (%s) AND bucket_time >= %s
        AND bucket_time <= %s
        ORDER BY bucket_time""" % (names_str, start, stop)
        # print("statistic_get_range: %s" % sql)
        records = yield Registry.DBPOOL.runQuery(sql)
        results = []
        for record in records:
            if minimal in (None, False):
                results.append({
                    'id': record[0],
                    'bucket_time': record[1],
                    'bucket_size': record[2],
                    'bucket_lifetime': record[3],
                    'bucket_type': record[4],
                    'bucket_name': record[5],
                    'bucket_value': record[6],
                    'bucket_average_data': record[7],
                    'anon': record[8],
                    'uploaded': record[9],
                    'finished': record[10],
                    'updated_at': record[11],
                })
            else:
                results.append({
                    'id': record[0],
                    'bucket_time': record[1],
                    'bucket_size': record[2],
                    'bucket_lifetime': record[3],
                    'bucket_type': record[4],
                    'bucket_name': record[5],
                    'bucket_value': record[6],
                })

        return results

    @inlineCallbacks
    def get_stat_last_datapoints(self):
        sql = """SELECT s1.bucket_name, s1.bucket_value
FROM  statistics s1
INNER JOIN
(
    SELECT Max(updated_at) updated_at, bucket_name
    FROM   statistics
    WHERE bucket_type = 'datapoint'
    GROUP BY bucket_name
) AS s2
    ON s1.bucket_name = s2.bucket_name
    AND s1.updated_at = s2.updated_at
ORDER BY id desc"""
        stats = yield Registry.DBPOOL.runQuery(sql)
        results = {}
        for stat in stats:
            results[stat[0]] = stat[1]
        return results

    @inlineCallbacks
    def save_statistic_bulk(self, buckets):
        results = yield self.dbconfig.insertMany('statistics', buckets)
        return results

    @inlineCallbacks
    def save_statistic(self, bucket, finished=None):
        # print("save_statistic was called directly... sup?!")
        if finished is None:
            finished = False

        args = {'bucket_value': bucket['value'],
                'updated_at': int(time()),
                'anon': bucket['anon'],
                }

        if finished is not None:
            args['finished'] = finished
        else:
            args['finished'] = 0

        if bucket['type'] == 'average':
            args['bucket_average_data'] = data_pickle(bucket['average_data'], separators=(',',':'))

        if 'restored_db_id' in bucket:
            results = yield self.dbconfig.update('statistics',
                                                 args,
                                                 where=['id = ?',
                                                        bucket['restored_db_id']
                                                        ]
                                                 )
        else:
            args['bucket_time'] = bucket['time']
            args['bucket_type'] = bucket['type']
            args['bucket_name'] = bucket['bucket_name']
            results = yield self.dbconfig.insert('statistics', args, None, 'OR IGNORE')

        return results

    @inlineCallbacks
    def get_unfinished_statistics(self):
        records = yield self.dbconfig.select(
            'statistics',
            select='*',
            where=['finished = 0'])
        self._unpickle_stats(records)
        return records

    @inlineCallbacks
    def get_uploadable_statistics(self, uploaded_type = 0):
        anonymous_allowed = self._Configs.get('statistics', 'anonymous', True)
        if anonymous_allowed:
            records = yield self.dbconfig.select('statistics',
                 select='id as stat_id, bucket_time, bucket_size, bucket_type, bucket_name, bucket_value, bucket_average_data, bucket_time',
                 where=['finished = 1 AND uploaded = ?', uploaded_type], limit=750)
        else:
            records = yield self.dbconfig.select('statistics', select='*',
                 where=['finished = 1 AND uploaded = ? and anon = 0', uploaded_type])

        self._unpickle_stats(records, 'bucket_type', 'bucket_average_data')

        return records

    @inlineCallbacks
    def set_uploaded_statistics(self, value, the_list):
        where_str = "id in (" + ", ".join(map(str, the_list)) + ")"
        yield self.dbconfig.update('statistics', {'updated_at': int(time()), 'uploaded': value},
                                   where=[where_str])

    def _unpickle_stats(self, stats, type_name=None, averagedata_name=None):
        if averagedata_name is None:
            averagedata_name = 'bucket_average_data'
        if type_name is None:
            type_name = 'bucket_type'
        if isinstance(stats, list):
            for s in stats:
                if s[type_name] == 'average':
                    s[averagedata_name] = data_unpickle(s[averagedata_name])
        else:
            stats[averagedata_name] = data_unpickle(stats[averagedata_name])

    @inlineCallbacks
    def get_stats_sums(self, bucket_name, bucket_type=None, bucket_size=None, time_start=None, time_end=None):
        if bucket_size is None:
            bucket_size = 3600

        wheres = []
        values = []

        wheres.append("(bucket_name like ?)")
        values.append(bucket_name)

        if bucket_type is not None:
            wheres.append("(bucket_type > ?)")
            values.append(time_start)

        if time_start is not None:
            wheres.append("(bucket > ?)")
            values.append(time_start)

        if time_end is not None:
            wheres.append("(bucket < ?)")
            values.append(time_end)
        where_final = [(" AND ").join(wheres)] + values

        # records = yield self.dbconfig.select('statistics',
        #             select='sum(value), bucket_name, bucket_type, round(bucket / 3600) * 3600 AS bucket',
        select_fields = 'sum(bucket_value) as value, bucket_name, bucket_type, round(bucket_time / %s) * %s AS bucket' % (
        bucket_size, bucket_size)
        records = yield self.dbconfig.select('statistics',
                                             select=select_fields,
                                             where=where_final,
                                             group='bucket')
        return records

    #########################
    ###    Tasks        #####
    #########################
    @inlineCallbacks
    def get_tasks(self, section):
        """
        Get all tasks for a given section.

        :return:
        """
        records = yield Tasks.find(where=['run_section = ?', section])

        results = []
        for record in records:
            data = record.__dict__
            data['task_arguments'] = data_unpickle(data['task_arguments'], 'msgpack_base85_zip')
            results.append(data)  # we need a dictionary, not an object
        return results

    @inlineCallbacks
    def del_task(self, id):
        """
        Delete a task id.

        :return:
        """
        records = yield self.dbconfig.delete('tasks', where=['id = ?', id])
        return records

    @inlineCallbacks
    def add_task(self, data):
        """
        Get all tasks for a given section.

        :return:
        """
        data['task_arguments'] = data_pickle(data['task_arguments'], 'msgpack_base85_zip')
        results = yield self.dbconfig.insert('tasks', data, None, 'OR IGNORE')
        return results


    # ###########################
    # ###  Roles              ###
    # ###########################
    # @inlineCallbacks
    # def get_roles(self):
    #     records = yield Roles.all()
    #     return records
    #
    # @inlineCallbacks
    # def save_role(self, role):
    #     if role.source != "user":
    #         return
    #     records = yield Roles.find(where=['machine_label = ?', role.machine_label])
    #     print("db:save_role got records: %s" % records)
    #     if len(records) == 0:
    #         print("got no records, will create a roles record")
    #         args = {
    #             'label': role.label,
    #             'machine_label': role.machine_label,
    #             'description': role.description,
    #             'permissions': data_pickle(role.permissions),
    #             'updated_at': int(time()),
    #             'created_at': int(time()),
    #         }
    #         yield self.dbconfig.insert('roles', args, None, 'OR IGNORE')
    #     else:
    #         print("save role found: %s" % records)
    #         yield self.dbconfig.update("roles",
    #                                    {
    #                                        'label': role.label,
    #                                        'machine_label': role.machine_label,
    #                                        'description': role.description,
    #                                        'permissions': data_pickle(role.permissions),
    #                                        'updated_at': int(time())
    #                                    },
    #                                    where=['id = ?', records[0].id])

    ###########################
    ###  Users              ###
    ###########################
    @inlineCallbacks
    def get_users(self):
        records = yield Users.all()
        return records

    @inlineCallbacks
    def get_user_roles(self):
        records = yield UserRoles.all()
        # We need this as a dictionary....
        roles = {}
        for record in records:
            record.roles = data_unpickle(record.roles)
            roles[record.email] = record.__dict__
        return roles

    @inlineCallbacks
    def save_user_data(self, user):
        records = yield UserRoles.find(where=['email = ?', user.email])
        if len(records) == 0:
            print("got no records, will create a user record for roles...")
            args = {
                'email': user.email,
                'devices': data_pickle(user.roles),
                'roles': data_pickle(user.roles),
                'updated_at': int(time()),
                'created_at': int(time()),
            }
            yield self.dbconfig.insert('user_roles', args, None, 'OR IGNORE')
        else:
            yield self.dbconfig.update("user_roles",
                                       {
                                           'devices': data_pickle(user.devices),
                                           'roles': data_pickle(user.roles),
                                           'updated_at': int(time())
                                       },
                                       where=['id = ?', records[0].id])


    ###########################
    ###  Variables          ###
    ###########################
    @inlineCallbacks
    def get_variable_data(self, **kwargs):
        """
        Searches for variable data, using named agurments as where search fields, and'd together.

        :param group_id: Field group_id to search for.
        :type group_id: str
        :return: Available variable fields.
        :rtype: list
        """
        records = yield VariableFieldDataView.find(
            where=dictToWhere(kwargs),
            orderby='data_weight ASC')

        variables = OrderedDict()
        for record in records:
            # print("record: %s" % record)
            if record.field_machine_label not in variables:
                variables[record.field_machine_label] = {}
                variables[record.field_machine_label][record.data_id] = record.data
        return variables

    @inlineCallbacks
    def get_variable_fields(self, **kwargs):
        """
        Searches for variable fields, using named agurments as where search fields, and'd together.

        :param group_id: Field group_id to search for.
        :type group_id: str
        :return: Available variable fields.
        :rtype: list
        """
        records = yield VariableFields.find(
            where=dictToWhere(kwargs),
            orderby='field_weight ASC')

        return records

    @inlineCallbacks
    def get_variable_fields_encrypted(self):
        """
        Get all field id's that should be encrypted.

        :return: Field id's that have encryption set to suggested or always.
        :rtype: list
        """
        records = yield VariableFields.find(
            where=["encryption = 'always' or encryption = 'suggested'"]
        )
        items = []
        for record in records:
            items.append(record.id)
        return items

    @inlineCallbacks
    def get_variable_groups(self, **kwargs):
        """
        Searches for variable groups, using named agurments as where search fields, and'd together.

        :return: Available variable groups.
        :rtype: list
        """
        records = yield VariableGroups.find(
            where=dictToWhere(kwargs),
            orderby='group_weight ASC')

        return records

    @inlineCallbacks
    def get_variable_fields_data(self, data_relation_id=None, **kwargs):
        """
        Gets fields an associated data. Named arguments are used to crate the WHERE statement.

        :return: Available variable data nested inside the fields as 'data'.
        :rtype: list
        """
        records = yield VariableFieldDataView.find(
            where=dictToWhere(kwargs),
            orderby='field_weight ASC, data_weight ASC')
        variables = OrderedDict()
        for record in records:
            if data_relation_id is not None:
                if record.data_relation_id not in (None, data_relation_id):
                    continue

            if record.field_machine_label not in variables:
                variables[record.field_machine_label] = {
                    'id': record.field_id,
                    'field_machine_label': record.field_machine_label,
                    'field_label': record.field_label,
                    'field_description': record.field_description,
                    'field_help_text': record.field_help_text,
                    'field_weight': record.field_weight,
                    'value_min': record.value_min,
                    'value_max': record.value_max,
                    'value_casing': record.encryption,
                    'value_required': record.value_required,
                    'encryption': record.encryption,
                    'input_type_id': record.input_type_id,
                    'default_value': record.default_value,
                    'multiple': record.multiple,
                    'data_weight': record.data_weight,
                    'created_at': record.field_created_at,
                    'updated_at': record.field_updated_at,
                    'data': OrderedDict(),
                    'values': [],
                    'values_display': [],
                    'values_orig': [],
                }

            data = {
                'id': record.data_id,
                'weight': record.data_weight,
                'created_at': record.data_created_at,
                'updated_at': record.data_updated_at,
                'relation_id': record.data_relation_id,
                'relation_type': record.data_relation_type,
            }
            if record.data is not None:
                value = yield self._GPG.decrypt(record.data)
                try:  # lets be gentle for now.  Try to validate and corerce.
                    # validate the value is valid input
                    data['value'] = self._InputTypes.check(
                        variables[record.field_machine_label]['input_type_id'],
                        value,
                        casing=variables[record.field_machine_label]['value_casing'],
                        required=variables[record.field_machine_label]['value_required'],
                        min=variables[record.field_machine_label]['value_min'],
                        max=variables[record.field_machine_label]['value_max'],
                        default=variables[record.field_machine_label]['default_value'],
                    )
                except Exception as e:
                    logger.debug("Variable doesn't validate ({input_type_id}): {label}   Value:{value}    Reason: {e}",
                                label=variables[record.field_machine_label]['field_label'],
                                value=value,
                                input_type_id=variables[record.field_machine_label]['input_type_id'],
                                e=e)
                    data['value'] = value

                data['value_display'] = yield self._GPG.display_encrypted(record.data)
            else:
                data['value'] = None
                data['value_display'] = ""

            data['value_orig'] = record.data
            variables[record.field_machine_label]['data'][record.data_id] = data
            variables[record.field_machine_label]['values'].append(data['value'])
            variables[record.field_machine_label]['values_display'].append(data['value_display'])
            variables[record.field_machine_label]['values_orig'].append(data['value_orig'])
        return variables

    @inlineCallbacks
    def get_variable_groups_fields(self,  **kwargs):
        """
        Gets groups with nested fields, with nested data. Named arguments are used to crate the WHERE statement.

        :return: Available variable data nested inside the fields as 'data'.
        :rtype: list
        """
        # print("lbdb: %s" % dictToWhere(kwargs))
        records = yield VariableGroupFieldView.find(
            where=dictToWhere(kwargs),
            orderby='group_weight ASC, field_weight ASC')
        variables = OrderedDict()
        for record in records:
            if record.group_machine_label not in variables:
                variables[record.group_machine_label] = {
                    'id': record.group_id,
                    'group_relation_type': record.group_relation_type,
                    'group_id': record.group_id,
                    'group_machine_label': record.group_machine_label,
                    'group_label': record.group_label,
                    'group_description': record.group_description,
                    'group_weight': record.group_weight,
                    'group_status': record.group_status,
                    'fields': OrderedDict(),
                }
            if record.field_machine_label not in variables[record.group_machine_label]['fields']:
                variables[record.group_machine_label]['fields'][record.field_machine_label] = {
                    'id': record.field_id,
                    'field_machine_label': record.field_machine_label,
                    'field_label': record.field_label,
                    'field_description': record.field_description,
                    'field_help_text': record.field_help_text,
                    'field_weight': record.field_weight,
                    'value_min': record.value_min,
                    'value_max': record.value_max,
                    'value_casing': record.encryption,
                    'value_required': record.value_required,
                    'encryption': record.encryption,
                    'input_type_id': record.input_type_id,
                    'default_value': record.default_value,
                    'multiple': record.multiple,
                    'created_at': record.field_created_at,
                    'updated_at': record.field_updated_at,
                    'data': OrderedDict(),
                    'values': [],
                    'values_display': [],
                    'values_orig': [],
                }
        return variables

    @inlineCallbacks
    def get_variable_groups_fields_data(self, data_relation_id=None, **kwargs):
        """
        Gets groups with nested fields, with nested data. Named arguments are used to crate the WHERE statement.

        :return: Available variable data nested inside the fields as 'data'.
        :rtype: list
        """
        records = yield VariableGroupFieldDataView.find(
            where=dictToWhere(kwargs),
            orderby='group_weight ASC, field_weight ASC, data_weight ASC')
        variables = OrderedDict()
        for record in records:
            if data_relation_id is not None:
                if record.data_relation_id not in (None, data_relation_id):
                    continue

            if record.group_machine_label not in variables:
                variables[record.group_machine_label] = {
                    'id': record.group_id,
                    'group_relation_type': record.group_relation_type,
                    'group_id': record.group_id,
                    'group_machine_label': record.group_machine_label,
                    'group_label': record.group_label,
                    'group_description': record.group_description,
                    'group_weight': record.group_weight,
                    'group_status': record.group_status,
                    'fields': OrderedDict(),
                }
            if record.field_machine_label not in variables[record.group_machine_label]['fields']:
                variables[record.group_machine_label]['fields'][record.field_machine_label] = {
                    'id': record.field_id,
                    'field_machine_label': record.field_machine_label,
                    'field_label': record.field_label,
                    'field_description': record.field_description,
                    'field_help_text': record.field_help_text,
                    'field_weight': record.field_weight,
                    'value_min': record.value_min,
                    'value_max': record.value_max,
                    'value_casing': record.encryption,
                    'value_required': record.value_required,
                    'encryption': record.encryption,
                    'input_type_id': record.input_type_id,
                    'default_value': record.default_value,
                    'multiple': record.multiple,
                    'data_weight': record.data_weight,
                    'created_at': record.field_created_at,
                    'updated_at': record.field_updated_at,
                    'data': OrderedDict(),
                    'values': [],
                    'values_display': [],
                    'values_orig': [],
                }
            data = {
                'id': record.data_id,
                'weight': record.data_weight,
                'created_at': record.data_created_at,
                'updated_at': record.data_updated_at,
                'relation_id': record.data_relation_id,
                'relation_type': record.data_relation_type,
            }
            if record.data is not None:
                value = yield self._GPG.decrypt(record.data)
                try:  # lets be gentle for now.  Try to validate and corerce.
                    # validate the value is valid input
                    data['value'] = self._InputTypes.check(
                        variables[record.field_machine_label]['input_type_id'],
                        value,
                        casing=variables[record.field_machine_label]['value_casing'],
                        required=variables[record.field_machine_label]['value_required'],
                        min=variables[record.field_machine_label]['value_min'],
                        max=variables[record.field_machine_label]['value_max'],
                        default=variables[record.field_machine_label]['default_value'],
                    )
                except Exception as e:  # for now, just pass
                    logger.debug("Variable doesn't validate: {label}   Value:{value}.  Reason: {e}",
                                label=variables[record.field_machine_label]['field_label'],
                                value=value,
                                e=e)
                    data['value'] = value
                data['value_display'] = yield self._GPG.display_encrypted(record.data)
            else:
                data['value'] = None
                data['value_display'] = ""

            data['value_orig'] = record.data
            variables[record.group_machine_label]['fields'][record.field_machine_label]['data'][record.data_id] = data
            variables[record.group_machine_label]['fields'][record.field_machine_label]['values'].append(data['value'])
            variables[record.group_machine_label]['fields'][record.field_machine_label]['values_display'].append(data['value_display'])
            variables[record.group_machine_label]['fields'][record.field_machine_label]['values_orig'].append(data['value_orig'])
        return variables

    @inlineCallbacks
    def del_variables(self, data_relation_type, data_relation_id):
        """
        Deletes variables for a given relation type and relation id.

        :return:
        """
        results = yield self.dbconfig.delete('variable_data',
                                             where=['data_relation_type = ? and data_relation_id = ?',
                                                    data_relation_type,
                                                    data_relation_id]
                                             )
        return results

    @inlineCallbacks
    def add_variable_data(self, data, **kwargs):
        print("add_variable_data: data: %s" % data)

        # add_variable_data: data: {'field_id': 'pVyrdoVdDglKbj', 'relation_id': 'j2z8gbJxkNl4qwM6',
        #                           'relation_type': 'device', 'data_weight': 0, 'data': '4075575332',
        #                           'updated_at': 1530552709, 'created_at': 1530552709, 'id': 'qZlMkAzWd8aW4pngyx'}

        args = {
            'id': data['id'],
            'field_id': data['field_id'],
            'data_relation_id': data['relation_id'],
            'data_relation_type': data['relation_type'],
            'data': data['data'],
            'data_weight': data['data_weight'],
            'updated_at': data['updated_at'],
            'created_at': data['created_at'],
        }
        results = yield self.dbconfig.insert('variable_data', args, None, 'OR IGNORE')
        return results

    @inlineCallbacks
    def edit_variable_data(self, data_id, value):
        yield self.dbconfig.update("variable_data",
                                   {'data': value, 'updated_at': time()},
                                   where=['id = ?', data_id])

    @inlineCallbacks
    def get_variable_groups(self, group_relation_type, group_relation_id):
        """
        Gets all variable groups for a given type and by id.

        :param group_relation_type:
        :param group_relation_id:
        :return:
        """
        records = yield VariableGroups.find(
            where=['group_relation_type = ? AND group_relation_id =?', group_relation_type, group_relation_id],
            orderby='group_weight ASC')
        return records

    @inlineCallbacks
    def get_device_type_commands(self, device_type_id):
        """
        Gets available variables for a given device_id.

        Called by: library.Devices::_init_

        :param variable_type:
        :param foreign_id:
        :return:
        """
        records = yield DeviceTypeCommand.find(
            where=['device_type_id = ?', device_type_id])
        commands = []
        for record in records:
            if record.command_id not in commands:
                commands.append(record.command_id)

        return commands

    ################################
    ###   Webinterface logs    #####
    ################################
    @inlineCallbacks
    def webinterface_save_logs(self, logs):
        yield self.dbconfig.insertMany('webinterface_logs', logs)


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
        limit = kwargs.get('limit', None)
        offset = kwargs.get('offset', None)
        if limit is None:
            return None
        if offset is None:
            return limit
        else:
            return (limit, offset)
