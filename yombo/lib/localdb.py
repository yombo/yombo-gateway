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

# Import 3rd-party libs
from yombo.ext.twistar.registry import Registry
from yombo.ext.twistar.dbobject import DBObject

# Import twisted libraries
from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks, returnValue

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger

logger = getLogger('lib.sqlitedb')

LATEST_SCHEMA_VERSION = 1

#### Various SQLite tables within the database. ####


class CommandDeviceTypes(DBObject):
    TABLENAME='command_device_types'


class Command(DBObject):
    HABTM = [dict(name='device_types', join_table='CommandDeviceTypes')]
    pass


class Config(DBObject):
#    TABLENAME='devsadf'
    pass


class Device(DBObject):
#    HASMANY = [{'name':'device_status', 'class_name':'DeviceStatus', 'foreign_key':'id', 'association_foreign_key':'device_id'},
#               {'name':'device_variables', 'class_name':'DeviceVariable', 'foreign_key':'id', 'association_foreign_key':'device_id'}]
    HASMANY = [{'name':'device_status', 'class_name':'DeviceStatus', 'foreign_key':'device_id'},
               {'name':'device_variables', 'class_name':'DeviceVariable', 'association_foreign_key':'device_id'}]
    HASONE = [{'name':'device_types', 'class_name':'DeviceType', 'foreign_key':'device_id', 'association_foreign_key':'device_type_id'}]
    TABLENAME='devices'
#    pass

class DeviceStatus(DBObject):
    TABLENAME='device_status'
    BELONGSTO = ['devices']


class DeviceType(DBObject):
    TABLENAME='device_types'
    HABTM = [dict(name='commands', join_table='command_device_types')]
#    BELONGSTO = ['devices']


class GpgKey(DBObject):
    TABLENAME='gpg_keys'


class Logs(DBObject):
    TABLENAME='logs'


class ModuleDeviceTypes(DBObject):
    TABLENAME='moduleDeviceTypes'


class Modules(DBObject):
    HASONE = [{'name':'module_installed', 'class_name':'ModuleInstalled', 'foreign_key':'module_id'}]
    TABLENAME='modules'


class ModulesView(DBObject):
    TABLENAME='modules_view'


class ModuleInstalled(DBObject):
    TABLENAME='module_installed'
    BELONGSTO = ['modules']


class Schema_Version(DBObject):
    TABLENAME='schema_version'


class Sqldict(DBObject):
    TABLENAME='sqldict'


class User(DBObject):
#    TABLENAME='users'
    pass


class Variable(DBObject):
    TABLENAME='variables'
    BELONGSTO = ['devices', 'modules']

#### Views ####


class ModuleRoutingView(DBObject):
    TABLENAME='module_routing_view'

#Registry.register(Config)
Registry.SCHEMAS['PRAGMA_table_info'] = ['cid', 'name', 'type', 'notnull', 'dft_value', 'pk']
Registry.register(Device, DeviceStatus, Variable, DeviceType, Command)
Registry.register(Modules, ModuleInstalled)

class LocalDB(YomboLibrary):
    """
    Manages all database interactions.
    """

    @inlineCallbacks
    def _init_(self, loader):
        """
        Check to make sure the database exists. Will create if missing, will also update schema if any
        changes are required.
        """
        self._ModDescription = "Manages the local database"
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "https://yombo.net"
        self.loader = loader
        self.db_model = {}  #store generated database model here.
        # Connect to the DB
        Registry.DBPOOL = adbapi.ConnectionPool('sqlite3', "usr/etc/yombo.db", check_same_thread = False)
        self.dbconfig = Registry.getConfig()

        self.schema_version = 0
        try:
            results = yield Schema_Version.find(where=['table_name = ?', 'core'])
            self.schema_version = results[0].version
        except:
            logger.info("Creating new database file.")

        start_schema_version = self.schema_version
        for z in range(self.schema_version+1, LATEST_SCHEMA_VERSION+1):
                script = __import__("yombo.utils.db."+str(z), globals(), locals(), ['upgrade'], 0)
                results = yield script.upgrade(Registry)

                self.dbconfig.update("schema_version", {'table_name': 'core', 'version':z})
                results = yield Schema_Version.all()

        yield self._load_db_model()

    def _start_(self):
        pass

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
            columns = yield self.dbconfig.pragma('table_info(%s)'%table['tbl_name'])
            self.db_model[table['tbl_name']] = {}
            for column in columns:
                self.db_model[table['tbl_name']][column['name']] = column

    @inlineCallbacks
    def load_test_data(self):
        logger.info("Loading databsae test data")

        command = yield Command.find('command1')
        if command is None:
          command = yield Command(id='command1', machine_label='6on', label='O6n', public=1, status=1, created=1, updated=1).save()

        device = yield Device.find('device1')
        if device is None:
          device = yield Device(id='device1', machine_label='on', label='Lamp1', gateway_id='gateway1', device_type_id='devicetype1', pin_required=0, pin_timeout=0, status=1, created=1, updated=1, description='desc', notes='note', Voice_cmd_src='auto', voice_cmd='lamp on').save()
          variable = yield Variable(variable_type='device', variable_id="variable_id1", foreign_id='deviceVariable1', device_id=device.id, weigh=0, machine_label='device_var_1', label='Device Var 1', value='somevalue1', updated=1, created=1).save()

        deviceType = yield DeviceType.find('devicetype1')
        if deviceType is None:
          deviceType = yield DeviceType(id=device.device_type_id,  machine_label='x10_appliance', label='Lamp1', device_class='x10', description='x10 appliances', status=1, created=1, updated=1).save()
          args = {'device_type_id': device.id, 'command_id': command.id}
          yield self.dbconfig.insert('command_device_types', args)

        device = yield Device.find('device1')
        results = yield Variable.find(where=['variable_type = ? AND foreign_id = ?', 'device', device.id])
#          results = yield DeviceType.find(where=['id = ?', device.device_variables.get()

    @inlineCallbacks
    def get_commands(self):
        """
        Get all commands
        :return:
        """
        records = yield Command.all()
        returnValue(records)

    @inlineCallbacks
    def get_commands_for_device_type(self, device_type_id):
        records = yield CommandDeviceTypes.find(where=['device_type_id = ?', device_type_id])
        returnValue(records)

    @inlineCallbacks
    def get_device_status(self, **kwargs):
        id = kwargs['id']
        limit = self._get_limit(**kwargs)
        records = yield self.dbconfig.select('device_status', select='device_id, set_time, device_state, human_status, machine_status, machine_status_extra, source, uploaded, uploadable', where=['device_id = ?', id], orderby='set_time', limit=limit)
        for index in range(len(records)):
            records[index]['machine_status_extra'] = json.loads(str(records[index]['machine_status_extra']))
        returnValue(records)

    @inlineCallbacks
    def save_device_status(self, device_id, **kwargs):
        set_time = kwargs.get('set_time', time())
        device_state = kwargs.get('device_state', 0)
        machine_status = kwargs['machine_status']
        machine_status_extra = json.dumps(kwargs.get('machine_status_extra', ''), separators=(',',':') )
        human_status = kwargs.get('human_status', machine_status)
        source = kwargs.get('source', '')
        uploaded = kwargs.get('uploaded', 0)
        uploadable = kwargs.get('uploadable', 0)

        yield DeviceStatus(
            device_id=device_id,
            set_time=set_time,
            device_state=device_state,
            human_status=human_status,
            machine_status=machine_status,
            machine_status_extra=machine_status_extra,
            source=source,
            uploaded=uploaded,
            uploadable=uploadable,
        ).save()

    @inlineCallbacks
    def get_devices(self):
        records = yield self.dbconfig.select("devices_view")
        returnValue(records)

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

        variables = {}
        for record in records:
            key = {
                'endpoint': record['endpoint'],
                'fingerprint': record['fingerprint'],
                'length': record['length'],
                'expires': record['expires'],
                'created': record['created'],
            }
            variables[record['fingerprint']] = key
        returnValue(variables)

    @inlineCallbacks
    def insert_gpg_key(self, gwkey, **kwargs):
        key = GpgKey()
        key.endpoint = gwkey['endpoint']
        key.fingerprint = gwkey['fingerprint']
        key.length = gwkey['length']
        key.expires = gwkey['expires']
        key.created = gwkey['created']
        yield key.save()
#        yield self.dbconfig.insert('gpg_keys', args, None, 'OR IGNORE' )

    @inlineCallbacks
    def get_modules(self, get_all=False):
        if get_all is False:
            records = yield Modules.find(where=['status = ?', 1])
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
    def get_module_routing(self, where = None):
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
    def get_sql_dict(self, module, dict_name):
        records = yield self.dbconfig.select('device_status', select='dict_key, dict_data', where=['module = ? AND dict_name = ?', module, dict_name])
        returnValue(records[0])

    @inlineCallbacks
    def set_sql_dict(self, module, dict_name, dict_key, dict_data):
        """
        Used to save SQLDicts to the database. This is from a loopingcall as well as
        shutdown of the gateway.

        Called by: lib.Loader::saveSQLDict

        :param module: Module/Library that is storing the data.
        :param dictname: Name of the dictionary that is used within the module/library
        :param key1: Key
        :param data1: Data
        :return: None
        """
        args = {'module': module,
                'dict_name': dict_name,
                'dict_key' : dict_key,
                'dict_data' : dict_data,
                'updated' : int(time()),
        }
        yield self.dbconfig.update('sqldict', args, where=['dict_key = ? AND module = ? AND dict_name = ?', dict_key, module, dict_name] )
        args['created'] = args['updated']
        yield self.dbconfig.insert('sqldict', args, None, 'OR IGNORE' )

    @inlineCallbacks
    def get_variables(self, variable_type, foreign_id = None):
        """
        Gets available variables for a given device_id.

        Called by: library.Devices::_init_

        :param variable_type:
        :param foreign_id:
        :return:
        """
        records = yield Variable.find(where=['variable_type = ? AND foreign_id =?', variable_type, foreign_id], orderby='weight ASC, data_weight ASC')
        variables = {}
        for record in records:
            if record.machine_label not in variables:
                variables[record.machine_label] = {
                    'machine_label': record.machine_label,
                    'label': record.label,
                    'updated': record.updated,
                    'created': record.created,
                    'weight': record.weight,
                    'data_weight': record.data_weight,
                    'foreign_id': record.foreign_id,
                    'id': record.id,
                    'value': [],
                }

            variables[record.machine_label]['value'].append(record.value)
#                print record.__dict__
        returnValue(variables)



#        returnValue(variables)

    @inlineCallbacks
    def delete(self, table, where=None):
        """
        Truncate table

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

