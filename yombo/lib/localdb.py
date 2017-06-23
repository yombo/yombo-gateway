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

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from time import time

try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
import base64
import zlib
import pickle
from sqlite3 import Binary as sqlite3Binary
import sys
import inspect
from os import chmod
from collections import OrderedDict
# Import 3rd-party libs
from yombo.ext.twistar.registry import Registry
from yombo.ext.twistar.utils import dictToWhere
from yombo.ext.twistar.dbobject import DBObject

# Import twisted libraries
from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks, returnValue

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.exceptions import YomboWarning
from yombo.utils import clean_dict

logger = get_logger('lib.localdb')

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
    TABLENAME = 'device_command'
    BELONGSTO = ['devices']


class DeviceStatus(DBObject):
    TABLENAME = 'device_status'
    BELONGSTO = ['devices']


class DeviceType(DBObject):
    TABLENAME = 'device_types'


class DeviceTypeCommand(DBObject):
    TABLENAME = 'device_type_commands'


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
    TABLENAME = 'users'


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

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Check to make sure the database exists. Will create if missing, will also update schema if any
        changes are required.
        """
        def show_connected(connection):
            connection.execute("PRAGMA foreign_keys = ON")

        self.db_model = {}  # store generated database model here.
        # Connect to the DB
        Registry.DBPOOL = adbapi.ConnectionPool('sqlite3', "usr/etc/yombo.db", check_same_thread=False,
                                                cp_min=1, cp_max=1, cp_openfun=show_connected)
        self.dbconfig = Registry.getConfig()

        self.schema_version = 0
        try:
            results = yield Schema_Version.find(where=['table_name = ?', 'core'])
            self.schema_version = results[0].version
        except Exception as e:
            logger.debug("Promblem with database: %s" % e)
            logger.info("Creating new database file.")

        start_schema_version = self.schema_version
        for z in range(self.schema_version + 1, LATEST_SCHEMA_VERSION + 1):
            script = __import__("yombo.utils.db." + str(z), globals(), locals(), ['upgrade'], 0)
            results = yield script.upgrade(Registry)

            self.dbconfig.update("schema_version", {'table_name': 'core', 'version': z})
            results = yield Schema_Version.all()

        chmod('usr/etc/yombo.db', 0o600)

        yield self._load_db_model()

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
            self.db_model[table['tbl_name']] = {}
            for column in columns:
                self.db_model[table['tbl_name']][column['name']] = column

    @inlineCallbacks
    def load_test_data(self):
        logger.info("Loading databsae test data")

        command = yield Command.find('command1')
        if command is None:
            command = yield Command(id='command1', machine_label='6on', label='O6n', public=1, status=1, created=1,
                                    updated=1).save()

        device = yield Device.find('device1')
        if device is None:
            device = yield Device(id='device1', machine_label='on', label='Lamp1', gateway_id='gateway1',
                                  device_type_id='devicetype1', pin_required=0, pin_timeout=0, status=1, created=1,
                                  updated=1, description='desc', notes='note', Voice_cmd_src='auto',
                                  voice_cmd='lamp on').save()
            # variable = yield Variable(variable_type='device', variable_id="variable_id1", foreign_id='deviceVariable1', device_id=device.id, weigh=0, machine_label='device_var_1', label='Device Var 1', value='somevalue1', updated=1, created=1).save()

        deviceType = yield DeviceType.find('devicetype1')
        if deviceType is None:
            deviceType = yield DeviceType(id=device.device_type_id, machine_label='x10_appliance', label='Lamp1',
                                          device_class='x10', description='x10 appliances', status=1, created=1,
                                          updated=1).save()
            args = {'device_type_id': device.id, 'command_id': command.id}
            yield self.dbconfig.insert('command_device_types', args)

        device = yield Device.find('device1')
        # results = yield Variable.find(where=['variable_type = ? AND foreign_id = ?', 'device', device.id])

    #          results = yield DeviceType.find(where=['id = ?', device.device_variables.get()

    @inlineCallbacks
    def get_dbitem_by_id(self, dbitem, id, status=None):
        if dbitem not in MODULE_CLASSES:
            raise YomboWarning("get_dbitem_by_id expects dbitem to be a DBObject")
        #        print MODULE_CLASSES
        if status is None:
            records = yield MODULE_CLASSES[dbitem].find(where=['id = ?', id])
            # print "looking without status! %s = %s (%s)" % (dbitem, id, len(records))
        else:
            records = yield MODULE_CLASSES[dbitem].find(where=['id = ? and status = ?', id, status])
        #        print "get_dbitem_by_id. class: %s, id: %s, status: %s" % (dbitem, id, status)
        results = []
        for record in records:
            results.append(record.__dict__)  # we need a dictionary, not an object
        returnValue(results)

    @inlineCallbacks
    def get_dbitem_by_id_dict(self, dbitem, where=None, status=None):
        if dbitem not in MODULE_CLASSES:
            # print MODULE_CLASSES
            raise YomboWarning("get_dbitem_by_id_dict expects dbitem to be a DBObject")
        #        print MODULE_CLASSES
        if where is None:
            records = yield MODULE_CLASSES[dbitem].find()
        #            print "looking without status!"
        else:
            records = yield MODULE_CLASSES[dbitem].find(where=dictToWhere(where))
        #        print "get_dbitem_by_id. class: %s, id: %s, status: %s" % (dbitem, id, status)
        results = []
        for record in records:
            results.append(record.__dict__)  # we need a dictionary, not an object
        returnValue(results)

    #########################
    ###    Commands     #####
    #########################
    @inlineCallbacks
    def get_commands(self, always_load=None):
        if always_load is None:
            always_load = True

        if always_load == True:
            records = yield self.dbconfig.select('commands', where=['always_load = ?', 1])
            returnValue(records)
        elif always_load is False:
            records = yield self.dbconfig.select('commands', where=['always_load = ? OR always_load = ?', 1, 0])
            returnValue(records)
        else:
            returnValue([])


    #########################
    ###    Devices      #####
    #########################

    @inlineCallbacks
    def get_devices(self, status=None):
        if status == True:
            records = yield Device.all()
            returnValue(records)
        elif status is None:
            records = yield Device.find(where=['status = ? OR status = ?', 1, 0])
            returnValue(records)
        else:
            records = yield Device.find(where=['status = ? ', status])
            returnValue(records)

    @inlineCallbacks
    def set_device_status(self, device_id, status=1):
        # device = yield Device.findBy(id=device_id)

        results = yield self.dbconfig.update('devices', {'status': status},
                                             where=['id = ?', device_id])

    @inlineCallbacks
    def get_device_by_id(self, device_id, status=1):
        records = yield Device.find(where=['id = ? and status = ?', device_id, status])
        results = []
        for record in records:
            results.append(record.__dict__)  # we need a dictionary, not an object
        returnValue(results)

    @inlineCallbacks
    def get_device_status(self, **kwargs):
        id = kwargs['id']
        limit = self._get_limit(**kwargs)
        records = yield self.dbconfig.select('device_status',
                                             select='device_id, set_time, energy_usage, energy_type, human_status, human_message, last_command, machine_status, machine_status_extra, requested_by, reported_by, request_id, uploaded, uploadable',
                                             where=['device_id = ?', id], orderby='set_time', limit=limit)
        for index in range(len(records)):
            machine_status_extra = records[index]['machine_status_extra']
            if machine_status_extra is None:
                records[index]['machine_status_extra'] = None
            else:
                records[index]['machine_status_extra'] = json.loads(machine_status_extra)

            records[index]['requested_by'] = json.loads(str(records[index]['requested_by']))
        returnValue(records)

    @inlineCallbacks
    def save_device_status(self, device_id, **kwargs):
        machine_status = kwargs['machine_status']
        if kwargs['machine_status_extra'] is None :
            machine_status_extra = None
        else:
            machine_status_extra = json.dumps(kwargs['machine_status_extra'], separators=(',', ':'))
        results = yield DeviceStatus(
            device_id=device_id,
            set_time=kwargs.get('set_time', time()),
            energy_usage=kwargs['energy_usage'],
            energy_type=kwargs['energy_type'],
            human_status=kwargs.get('human_status', machine_status),
            human_message=kwargs.get('human_message', machine_status),
            last_command=kwargs.get('last_command', machine_status),
            machine_status=machine_status,
            machine_status_extra=machine_status_extra,
            requested_by=json.dumps(kwargs.get('requested_by', {}), separators=(',', ':')),
            reported_by=kwargs.get('reported_by', 'Unknown'),
            uploaded=kwargs.get('uploaded', 0),
            uploadable=kwargs.get('uploadable', 0),
        ).save()
        returnValue(results)

    @inlineCallbacks
    def get_device_commands(self, where):
        records = yield DeviceCommand.find(where=dictToWhere(where), orderby='created_time DESC')
        DCs = []
        for record in records:
            DC =  record.__dict__
            del DC['errors']
            del DC['_rowid']
            DC['_source'] = "database"
            DC['history'] = json.loads(DC['history'])
            DC['requested_by'] = json.loads(DC['requested_by'])
            DCs.append(DC)
        return DCs

    @inlineCallbacks
    def save_device_command(self, DC):
        if DC.inputs is None:
            inputs = None
        else:
            inputs = json.dumps(DC.inputs, separators=(',', ':'))

        if DC.id is None:
            device_command = DeviceCommand()
            device_command.command_status_received=DC.command_status_received
            device_command.request_id=DC.request_id
            device_command.device_id=DC.device.device_id
            device_command.command_id=DC.command.command_id
            device_command.inputs=inputs
            device_command.created_time=DC.created_time
            device_command.broadcast_time=DC.broadcast_time
            device_command.sent_time=DC.sent_time
            device_command.received_time=DC.received_time
            device_command.pending_time=DC.pending_time
            device_command.finished_time=DC.finished_time
            device_command.not_before_time=DC.not_before_time
            device_command.not_after_time=DC.not_after_time
            device_command.history=json.dumps(DC.history, separators=(',', ':'))
            device_command.status=DC.status
            device_command.requested_by=json.dumps(DC.requested_by, separators=(',', ':'))
            device_command.uploaded=0
            device_command.uploadable=0
            results = yield device_command.save()

            device_command_results = yield DeviceCommand.find(where=['request_id = ?' , DC.request_id])
            return device_command_results

            return results
        else:
            args = {
                'inputs': inputs,
                'created_time': DC.created_time,
                'sent_time': DC.sent_time,
                'received_time': DC.received_time,
                'pending_time': DC.pending_time,
                'finished_time': DC.finished_time,
                'not_before_time': DC.not_before_time,
                'not_after_time': DC.not_after_time,
                'history': json.dumps(DC.history, separators=(',', ':')),
                'status': DC.status,
                'requested_by': json.dumps(DC.requested_by, separators=(',', ':')),
                'command_status_received': DC.command_status_received,
                # 'uploaded': DC.uploaded,
                # 'uploadable': DC.uploadable,
            }
            results = yield self.dbconfig.update('device_command', args,
                                                 where=['id = ?', DC.id])
            return results


    #############################
    ###    Device Types     #####
    #############################
    @inlineCallbacks
    def get_device_types(self, always_load=None):
        if always_load is None:
            always_load = True

        if always_load == True:
            records = yield self.dbconfig.select('device_types', where=['always_load = ?', 1])
            returnValue(records)
        elif always_load is False:
            records = yield self.dbconfig.select('device_types', where=['always_load = ? OR always_load = ?', 1, 0])
            returnValue(records)
        else:
            returnValue([])

    @inlineCallbacks
    def get_module_device_types(self, module_id):
        records = yield ModuleDeviceTypesView.find(where=['module_id = ?', module_id])
        returnValue(records)

    @inlineCallbacks
    def get_device_type(self, id):
        records = yield DeviceType.find(where=['id = ?', id])
        returnValue(records)


    ###########################################
    ###    Device Type Command Inputs     #####
    ###########################################
    @inlineCallbacks
    def device_type_command_inputs_get(self, device_type_id, command_id):
        records = yield DeviceCommandInput.find(
            where=['device_type_id = ? and command_id = ?', device_type_id, command_id])
        return records


    #################
    ### GPG     #####
    #################
    @inlineCallbacks
    def get_gpg_key(self, **kwargs):
        records = None
        if 'gwuuid' in kwargs:
            records = yield self.dbconfig.select("gpg_keys", where=['gwuuid = ?', kwargs['gwuuid']])
        elif 'keyid' in kwargs:
            records = yield self.dbconfig.select("gpg_keys", where=['key_id = ?', kwargs['keyid']])
        elif 'fingerprint' in kwargs:
            records = yield self.dbconfig.select("gpg_keys", where=['fingerprint = ?', kwargs['fingerprint']])
        else:
            records = yield self.dbconfig.select("gpg_keys")

        keys = {}
        for record in records:
            key = {
                'notes': record['notes'],
                'endpoint': record['endpoint'],
                'fingerprint': record['fingerprint'],
                'keyid': record['keyid'],
                'publickey': record['publickey'],
                'length': record['length'],
                'have_private': record['have_private'],
                'expires': record['expires'],
                'created': record['created'],
            }
            keys[record['fingerprint']] = key
        returnValue(keys)

    @inlineCallbacks
    def insert_gpg_key(self, gwkey, **kwargs):
        key = GpgKey()
        key.endpoint = gwkey['endpoint']
        key.fingerprint = gwkey['fingerprint']
        key.keyid = gwkey['keyid']
        key.publickey = gwkey['publickey']
        key.length = gwkey['length']
        key.expires = gwkey['expires']
        key.created = gwkey['created']
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
            always_load = True

        if always_load == True:
            records = yield self.dbconfig.select('input_types', where=['always_load = ?', 1])
            returnValue(records)
        elif always_load is False:
            records = yield self.dbconfig.select('input_types', where=['always_load = ? OR always_load = ?', 1, 0])
            returnValue(records)
        else:
            returnValue([])

    #############################
    ###    Modules          #####
    #############################

    @inlineCallbacks
    def get_modules(self, get_all=False):
        if get_all is False:
            records = yield Modules.find(where=['status = ? OR status = ?', 1, 0])
        else:
            records = yield Modules.all()
        returnValue(records)

    @inlineCallbacks
    def get_modules_view(self, get_all=False):
        if get_all is False:
            records = yield ModulesView.find(where=['status = ?', 1])
        else:
            records = yield ModulesView.all()

        returnValue(records)

    @inlineCallbacks
    def modules_install_new(self, data):
        results = yield ModuleInstalled(module_id=data['module_id'],
                                        installed_version=data['installed_version'],
                                        install_time=data['install_time'],
                                        last_check=data['install_time'],
                                        ).save()
        returnValue(results)

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
        returnValue(records)

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

        module = yield Modules.find(where=['module_id = ?', module_id])
        if module is None:
            returnValue(None)
        module.status = status
        results = yield module.save()
        returnValue(results)

    #############################
    ###    Nodes            #####
    #############################
    @inlineCallbacks
    def get_nodes(self):
        records = yield self.dbconfig.select('nodes',
            select="id, parent_id, node_type, weight, machine_label, gw_always_load, destination, data_type, status, updated, created")
        returnValue(records)

    @inlineCallbacks
    def get_node(self, node_id):
        record = yield Node.find(where=['id = ?', node_id], limit=1)
        record.node_id = record.id
        del record.id
        # attempt to decode the data..
        if record.data_type == 'json':
            try:
                record.data = json.loads(record.data)
            except:
                pass
        returnValue(record)

    @inlineCallbacks
    def get_node_siblings(self, node):
        records = yield Node.find(where=['parent_id = ? and node_type = ?', node.parent_id, node.node_type])
        for record in records:
            # attempt to decode the data..
            if record.data_type == 'json':
                record.data = json.loads(record.data)
        returnValue(records)

    @inlineCallbacks
    def get_node_children(self, node):
        records = yield Node.find(where=['parent_id = ? and node_type = ?', node.id, node.node_type])
        for record in records:
            # attempt to decode the data..
            if record.data_type == 'json':
                record.data = json.loads(record.data)
        returnValue(records)

    @inlineCallbacks
    def set_node_status(self, node_id, status=1):
        results = yield self.dbconfig.update('nodes', {'status': status},
                                             where=['id = ?', node_id])

    # @inlineCallbacks
    # def save_new_node(self, node_id, **kwargs):
    #     set_time = kwargs.get('set_time', time())
    #     energy_usage = kwargs['energy_usage']
    #     machine_status = kwargs['machine_status']
    #     human_status = kwargs.get('human_status', machine_status)
    #     machine_status_extra = json.dumps(kwargs.get('machine_status_extra', ''), separators=(',', ':'))
    #     requested_by = json.dumps(kwargs.get('requested_by', ''), separators=(',', ':'))
    #     source = kwargs.get('source', '')
    #     uploaded = kwargs.get('uploaded', 0)
    #     uploadable = kwargs.get('uploadable', 0)
    #
    #     yield DeviceStatus(
    #         device_id=device_id,
    #         set_time=set_time,
    #         energy_usage=energy_usage,
    #         human_status=human_status,
    #         machine_status=machine_status,
    #         machine_status_extra=machine_status_extra,
    #         source=source,
    #         uploaded=uploaded,
    #         requested_by=requested_by,
    #         uploadable=uploadable,
    #     ).save()

    #############################
    ###    Notifications    #####
    #############################
    @inlineCallbacks
    def get_notifications(self):
        cur_time = int(time())
        records = yield Notifications.find(where=['expire > ?', cur_time], orderby='created DESC')
        returnValue(records)

    @inlineCallbacks
    def delete_notification(self, id):
        records = yield Notifications.delete(where=['id = ?', id])
        returnValue(records)

    @inlineCallbacks
    def delete_expired_notifications(self):
        records = yield self.dbconfig.delete('notifications', where=['expire < ?', time()])
        returnValue(records)

    @inlineCallbacks
    def add_notification(self, notice, **kwargs):
        args = {
            'id': notice['id'],
            'type': notice['type'],
            'priority': notice['priority'],
            'source': notice['source'],
            'expire': notice['expire'],
            'always_show': notice['always_show'],
            'always_show_allow_clear': notice['always_show_allow_clear'],
            'acknowledged': notice['acknowledged'],
            'acknowledged_time': notice['acknowledged_time'],
            'user': notice['user'],
            'title': notice['title'],
            'message': notice['message'],
            'meta': json.dumps(notice['meta'], separators=(',', ':')),
            'created': notice['created'],
        }
        results = yield self.dbconfig.insert('notifications', args, None, 'OR IGNORE')
        return results

    @inlineCallbacks
    def update_notification(self, notice, **kwargs):
        args = {
            'type': notice.type,
            'priority': notice.priority,
            'source': notice.source,
            'expire': notice.expire,
            'always_show': notice.always_show,
            'always_show_allow_clear': notice.always_show_allow_clear,
            'acknowledged': notice.acknowledged,
            'acknowledged_time': notice.acknowledged_time,
            'user': notice.user,
            'title': notice.title,
            'message': notice.message,
            'meta': json.dumps(notice.meta, separators=(',', ':')),
        }
        print("saving notice: %s" %args)
        results = yield self.dbconfig.update('notifications', args, where=['id = ?', notice.notification_id])
        return results

    # @inlineCallbacks
    # def set_ack(self, id, new_ack, ack_time):
    #     records = yield self.dbconfig.update('notifications', {'acknowledged': new_ack, 'acknowledged_time': ack_time}, where=['id = ?', id])
    #     returnValue(records)

    #########################
    ###    Sessions     #####
    #########################
    @inlineCallbacks
    def get_session(self, session_id=None):
        # print "session_data: %s" % session_data
        if session_id is not None:
            record = yield Sessions.find(session_id)
        else:
            record = yield Sessions.find()
        returnValue(record)

    @inlineCallbacks
    def save_session(self, session_id, session_data, created, last_access, updated):
        print("save_session: %s" % session_data)
        args = {
            'id': session_id,
            'session_data': session_data,
            'created': created,
            'last_access': last_access,
            'updated': updated,
        }
        yield self.dbconfig.insert('webinterface_sessions', args, None, 'OR IGNORE')

    @inlineCallbacks
    def update_session(self, session_id, session_data, last_access, updated):
        # print "session_data: %s" % session_data

        args = {'session_data': session_data,
                'last_access': last_access,
                'updated': updated,
                }
        yield self.dbconfig.update('webinterface_sessions', args, where=['id = ?', session_id])

    @inlineCallbacks
    def delete_session(self, session_id):
        # print "session_data: %s" % session_data
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
        # print "name: %s" % name
        if name is not None:
            extra_where = "AND name = %s" % name
        else:
            extra_where = ''

        sql = """SELECT name, value, value_type, live, created
FROM states s1
WHERE created = (SELECT MAX(created) from states s2 where s1.id = s2.id)
%s
AND created > %s
GROUP BY name""" % (extra_where, str(int(time()) - 60 * 60 * 24 * 60))
        states = yield Registry.DBPOOL.runQuery(sql)
        results = []
        for state in states:
            results.append({
                'name': state[0],
                'value': state[1],
                'value_type': state[2],
                'live': state[3],
                'created': state[4],
            })
        returnValue(results)

    @inlineCallbacks
    def get_state_count(self, name=None):
        """
        Get a count of historical values for state

        :param name:
        :return:
        """
        count = yield States.count(where=['name = ?', name])
        returnValue(count)

    @inlineCallbacks
    def del_state(self, name=None):
        """
        Deletes all history of a state. (Deciding to implement)

        :param name:
        :return:
        """
        count = yield self.dbconfig.delete('states', where=['name = ?', name])
        returnValue(count)

    @inlineCallbacks
    def get_state_history(self, name, limit=None, offset=None):
        """
        Get an state history.

        :param name:
        :param limit:
        :param offset:
        :return:
        """
        if limit is None:
            limit = 1

        if offset is not None:
            limit = (limit, offset)

        results = yield States.find(where=['name = ?', name], limit=limit)
        records = []
        for item in results:
            temp = clean_dict(item.__dict__)
            del temp['errors']
            records.append(temp)
        returnValue(records)

    @inlineCallbacks
    def save_state(self, name, value, value_type=None, live=None):
        if live is None:
            live = 0
        yield States(
            name=name,
            value=value,
            value_type=value_type,
            live=live,
            created=int(time()),
        ).save()

    @inlineCallbacks
    def clean_states_table(self, name=None):
        """
        Remove records over 60 days, only keep the last 100 records for a given state. So save history for longer
        term, use the statistics library.

        :param name:
        :return:
        """
        sql = "DELETE FROM states WHERE created < %s" % str(int(time()) - 60 * 60 * 24 * 60)
        yield Registry.DBPOOL.runQuery(sql)
        sql = """DELETE FROM states WHERE id IN
              (SELECT id
               FROM states AS s
               WHERE s.name = states.name
               ORDER BY created DESC
               LIMIT -1 OFFSET 100)"""
        yield Registry.DBPOOL.runQuery(sql)

    #################
    ### SQLDict #####
    #################
    @inlineCallbacks
    def get_sql_dict(self, component, dict_name):
        records = yield self.dbconfig.select('sqldict', select='dict_data',
                                             where=['component = ? AND dict_name = ?', component, dict_name])
        if len(records) == 1:
            try:
                before = len(records[0]['dict_data'])
                records[0]['dict_data'] = zlib.decompress(base64.decodebytes(records[0]['dict_data']))
                logger.debug("SQLDict Compression. With: {withcompress}, Without: {without}",
                             without=len(records[0]['dict_data']), withcompress=before)
            except:
                pass
        returnValue(records)

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
        if len(dict_data) > 3000:
            dict_data = base64.encodestring(zlib.compress(dict_data, 5))

        args = {'component': component,
                'dict_name': dict_name,
                'dict_data': dict_data,
                'updated': int(time()),
                }
        #        print "starting set_sql_dict"
        records = yield self.dbconfig.select('sqldict', select='dict_name',
                                             where=['component = ? AND dict_name = ?', component, dict_name])
        if len(records) > 0:
            results = yield self.dbconfig.update('sqldict', args,
                                                 where=['component = ? AND dict_name = ?', component, dict_name])
        #            print "set_sql_dict: update reuslts: %s" %results
        else:
            args['created'] = args['updated']
            results = yield self.dbconfig.insert('sqldict', args, None, 'OR IGNORE')
        #            print "set_sql_dict: insert reuslts: %s" %results

    #####################
    ### Statistics  #####
    #####################
    @inlineCallbacks
    def get_distinct_stat_names(self, get_all=False):
        if get_all:
            records = yield self.dbconfig.select('statistics',
                 select='bucket_name, MIN(bucket_time) as bucket_time_min, MAX(bucket_time) as bucket_tuime_max',
                 group='bucket_name')
        else:
            records = yield self.dbconfig.select('statistics', where=['bucket_type != ?', 'datapoint'],
                 select='bucket_name, MIN(bucket_time) as bucket_time_min, MAX(bucket_time) as bucket_tuime_max',
                 group='bucket_name')
        returnValue(records)

    @inlineCallbacks
    def get_statistic(self, where):
        find_where = dictToWhere(where)
        records = yield Statistics.find(where=find_where)

        # print "stat records: %s" % records
        returnValue(records)

    @inlineCallbacks
    def get_stat_last_datapoints(self):
        sql = """SELECT s1.bucket_name, s1.bucket_value
FROM  statistics s1
INNER JOIN
(
    SELECT Max(updated) updated, bucket_name
    FROM   statistics
    WHERE bucket_type = 'datapoint'
    GROUP BY bucket_name
) AS s2
    ON s1.bucket_name = s2.bucket_name
    AND s1.updated = s2.updated
ORDER BY id desc"""
        stats = yield Registry.DBPOOL.runQuery(sql)
        results = {}
        for stat in stats:
            results[stat[0]] = stat[1]
        returnValue(results)

    @inlineCallbacks
    def save_statistic_bulk(self, buckets):
        # print "localdb save: %s" % buckets
        results = yield self.dbconfig.insertMany('statistics', buckets)
        returnValue(results)

    @inlineCallbacks
    def save_statistic(self, bucket, finished=None):
        if finished is None:
            finished = False

        # print "save stat data : %s" % bucket
        args = {'bucket_value': bucket['value'],
                'updated': int(time()),
                'anon': bucket['anon'],
                }

        if finished is not None:
            args['finished'] = finished
        else:
            args['finished'] = 0

        if bucket['type'] == 'average':
            args['bucket_average_data'] = json.dumps(bucket['average_data'], separators=(',',':'))

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

        returnValue(results)

    @inlineCallbacks
    def get_unfinished_statistics(self):
        records = yield self.dbconfig.select(
            'statistics',
            select='*',
            where=['finished = 0'])
        self._unpickle_stats(records)
        returnValue(records)

    @inlineCallbacks
    def get_uploadable_statistics(self, uploaded_type = 0):
        anonymous_allowed = self._Configs.get('statistics', 'anonymous', True)
        if anonymous_allowed:
            records = yield self.dbconfig.select('statistics',
                 select='id as stat_id, bucket_time, bucket_size, bucket_type, bucket_name, bucket_value, bucket_average_data, bucket_time',
                 where=['finished = 1 AND uploaded = ?', uploaded_type], limit=2000)
        else:
            records = yield self.dbconfig.select('statistics', select='*',
                 where=['finished = 1 AND uploaded = ? and anon = 0', uploaded_type])

        self._unpickle_stats(records, 'bucket_type', 'bucket_average_data')

        returnValue(records)

    @inlineCallbacks
    def set_uploaded_statistics(self, value, the_list):
        where_str = "id in (" + ", ".join(map(str, the_list)) + ")"
        yield self.dbconfig.update('statistics', {'updated': int(time()), 'uploaded': value},
                                   where=[where_str])

    def _unpickle_stats(self, stats, type_name=None, averagedata_name=None):
        if averagedata_name is None:
            averagedata_name = 'bucket_average_data'
        if type_name is None:
            type_name = 'bucket_type'
        if isinstance(stats, list):
            for s in stats:
                if s[type_name] == 'average':
                    s[averagedata_name] = json.loads(str(s[averagedata_name]))
        else:
            stats[averagedata_name] = json.loads(str(stats[averagedata_name]))

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
        # print "select_fields: %s" % select_fields
        records = yield self.dbconfig.select('statistics',
                                             select=select_fields,
                                             where=where_final,
                                             group='bucket')
        returnValue(records)

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
            data['task_arguments'] = zlib.decompress(base64.decodestring(data['task_arguments']))
            results.append(data)  # we need a dictionary, not an object
        returnValue(results)

    @inlineCallbacks
    def del_task(self, id):
        """
        Delete a task id.

        :return:
        """
        records = yield self.dbconfig.delete('taskes', where=['id = ?', id])
        returnValue(records)

    @inlineCallbacks
    def add_task(self, data):
        """
        Get all tasks for a given section.

        :return:
        """
        data['task_arguments'] = sqlite3Binary(pickle.dumps(data['task_arguments'], pickle.HIGHEST_PROTOCOL))
        if len(data['task_arguments']) > 3000:
            data['task_arguments'] = base64.encodestring(zlib.compress(data['task_arguments'], 5))

        results = yield self.dbconfig.insert('sqldict', data, None, 'OR IGNORE')
        returnValue(results)
        #
        # table = """CREATE TABLE `tasks` (
        #  `id`             INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        #  `run_section`    INTEGER NOT NULL,
        #  `run_once`       INTEGER NOT NULL,
        #  `run_interval`   INTEGER NOT NULL,
        #  `task_component` TEXT NOT NULL,
        #  `task_name`      TEXT NOT NULL,
        #  `task_arguments` BLOB,
        #  `source`         TEXT NOT NULL,
        #  `created`        INTEGER NOT NULL,
        #  );"""

    ###########################
    ###  Users              ###
    ###########################
    @inlineCallbacks
    def get_gateway_user_by_email(self, gateway_id, email):
        records = yield Users.find(where=['gateway_id = ? and email = ?', gateway_id, email])
        results = []
        for record in records:
            results.append(record.__dict__)  # we need a dictionary, not an object
        returnValue(results)

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
        records = yield VariableData.find(
            where=dictToWhere(kwargs),
            orderby='data_weight ASC')

        returnValue(records)

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

        returnValue(records)

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
        returnValue(items)

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

        returnValue(records)

    @inlineCallbacks
    def get_variable_fields_data(self,  **kwargs):
        """
        Gets fields an associated data. Named arguments are used to crate the WHERE statement.

        :return: Available variable data nested inside the fields as 'data'.
        :rtype: list
        """
        records = yield VariableFieldDataView.find(
            where=dictToWhere(kwargs),
            orderby='field_weight ASC, data_weight ASC')
        # print "get_variable_data records: %s" % records
        variables = OrderedDict()
        for record in records:
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
                    'created': record.field_created,
                    'updated': record.field_updated,
                    'data': OrderedDict(),
                    'values': [],
                    'values_display': [],
                    'values_orig': [],
                }

            data = {
                'id': record.data_id,
                'weight': record.data_weight,
                'created': record.data_created,
                'updated': record.data_updated,
                'relation_id': record.data_relation_id,
                'relation_type': record.data_relation_type,
            }
            value = yield self._GPG.decrypt(record.data)
            # validate the value is valid input
            try:  # lets be gentle for now.  Try to validate and corerce.
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
                logger.warn("Variable doesn't validate: {label}   Value:{value}.  Reason: {e}",
                            label=variables[record.field_machine_label]['field_label'],
                            value=value,
                            e=e)
                data['value'] = value

            data['value_display'] = yield self._GPG.display_encrypted(record.data)
            data['value_orig'] = record.data
            variables[record.field_machine_label]['data'][record.data_id] = data
            variables[record.field_machine_label]['values'].append(data['value'])
            variables[record.field_machine_label]['values_display'].append(data['value_display'])
            variables[record.field_machine_label]['values_orig'].append(data['value_orig'])
        returnValue(variables)

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
            # print "get_variable_groups_fields record: %s" % record
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
                    'created': record.field_created,
                    'updated': record.field_updated,
                    'data': OrderedDict(),
                    'values': [],
                    'values_display': [],
                    'values_orig': [],
                }
        returnValue(variables)

    @inlineCallbacks
    def get_variable_groups_fields_data(self, **kwargs):
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
                    'created': record.field_created,
                    'updated': record.field_updated,
                    'data': OrderedDict(),
                    'values': [],
                    'values_display': [],
                    'values_orig': [],
                }
            data = {
                'id': record.data_id,
                'weight': record.data_weight,
                'created': record.data_created,
                'updated': record.data_updated,
                'relation_id': record.data_relation_id,
                'relation_type': record.data_relation_type,
            }
            data['value'] = yield self._GPG.decrypt(record.data)
            data['value_display'] = yield self._GPG.display_encrypted(record.data)
            data['value_orig'] = record.data

            variables[record.group_machine_label]['fields'][record.field_machine_label]['data'][record.data_id] = data
            variables[record.group_machine_label]['fields'][record.field_machine_label]['values'].append(data['value'])
            variables[record.group_machine_label]['fields'][record.field_machine_label]['values_display'].append(data['value_display'])
            variables[record.group_machine_label]['fields'][record.field_machine_label]['values_orig'].append(data['value_orig'])
        returnValue(variables)

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
        returnValue(results)

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
        returnValue(records)

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

        returnValue(commands)

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
    def insert_many(self, table, vals):
        """
        Insert a list of records into a table

        :param table:
        :param vals:
        :return:
        """
        #        print "insert_many: (%s) %s" % (table, vals)
        yield self.dbconfig.insertMany(table, vals)

    @inlineCallbacks
    def insert(self, table, val):
        """
        Insert a record into a table.

        :param table:
        :param val:
        :return:
        """
        # print "insert: (%s) %s" % (table, val)
        yield self.dbconfig.insert(table, val)

    @inlineCallbacks
    def truncate(self, table):
        """
        Truncate table

        :param table:
        :return:
        """
        records = yield self.dbconfig.truncate(table)
        returnValue(records)

    def _get_limit(self, **kwargs):
        limit = kwargs.get('limit', None)
        offset = kwargs.get('offset', None)
        if limit is None:
            return None
        if offset is None:
            return limit
        else:
            return (limit, offset)
