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
import cPickle
from sqlite3 import Binary as sqlite3Binary
import sys
import inspect
from os import chmod

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

logger = get_logger('lib.sqlitedb')

LATEST_SCHEMA_VERSION = 1

#### Various SQLite tables within the database. ####

class Category(DBObject):
    TABLENAME='categories'

class Command(DBObject):
    HABTM = [dict(name='device_types', join_table='CommandDeviceTypes')]
    pass

class CommandDeviceTypes(DBObject):
    TABLENAME='command_device_types'

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

class DeviceCommandInput(DBObject):
    TABLENAME='device_command_inputs'
    BELONGSTO = ['devices']

class DeviceStatus(DBObject):
    TABLENAME='device_status'
    BELONGSTO = ['devices']

class DeviceType(DBObject):
    TABLENAME='device_types'
#    HABTM = [dict(name='commands', join_table='command_device_types')]

#    BELONGSTO = ['devices']

class DeviceTypeCommand(DBObject):
    TABLENAME='device_type_commands'

# class DeviceTypeModules(DBObject):
#     TABLENAME='device_type_modules'

class GpgKey(DBObject):
    TABLENAME='gpg_keys'

class InputType(DBObject):
    TABLENAME='input_types'

class Logs(DBObject):
    TABLENAME='logs'

class ModuleInstalled(DBObject):
    TABLENAME='module_installed'
    BELONGSTO = ['modules']

class Modules(DBObject):
    HASONE = [{'name':'module_installed', 'class_name':'ModuleInstalled', 'foreign_key':'module_id'}]
    HASMANY = [{'name':'module_device_types', 'class_name':'ModuleDeviceTypes', 'foreign_key':'module_id'}]
    TABLENAME='modules'

class ModuleDeviceTypes(DBObject):
    BELONGSTO = ['devices']
    TABLENAME = 'module_device_types'

class ModuleDeviceTypesView(DBObject):
    TABLENAME = 'module_device_types_view'

class ModulesView(DBObject):
    TABLENAME='modules_view'

class Notifications(DBObject):
    TABLENAME='notifications'

class Schema_Version(DBObject):
    TABLENAME='schema_version'

class Sqldict(DBObject):
    TABLENAME='sqldict'

class States(DBObject):
    TABLENAME='states'

class Statistics(DBObject):
    TABLENAME='statistics'

class Tasks(DBObject):
    TABLENAME='tasks'

class Users(DBObject):
    TABLENAME = 'users'

class VariableData(DBObject):
    TABLENAME='variable_data'

class VariableFields(DBObject):
    TABLENAME='variable_fields'

class VariableGroups(DBObject):
    TABLENAME='variable_groups'

class VariableDataView(DBObject):
    TABLENAME='variable_data_view'

# class Variable(DBObject):
#     TABLENAME='variables'
#     BELONGSTO = ['devices', 'modules']

class Sessions(DBObject):
    TABLENAME='webinterface_sessions'

#### Views ####


class ModuleRoutingView(DBObject):
    TABLENAME='module_routing_view'

#Registry.register(Config)
Registry.SCHEMAS['PRAGMA_table_info'] = ['cid', 'name', 'type', 'notnull', 'dft_value', 'pk']
Registry.register(Device, DeviceStatus, VariableData, DeviceType, Command)
Registry.register(Modules, ModuleInstalled, ModuleDeviceTypes)
Registry.register(VariableGroups, VariableData)
Registry.register(Category)
Registry.register(DeviceTypeCommand)


TEMP_MODULE_CLASSES = inspect.getmembers(sys.modules[__name__])
MODULE_CLASSES = {}
for item in TEMP_MODULE_CLASSES:
    if isinstance(item, tuple) and len(item) == 2 :
        if inspect.isclass(item[1]):
            if issubclass(item[1], DBObject):
                MODULE_CLASSES[item[0]] = item[1]
del TEMP_MODULE_CLASSES

class LocalDB(YomboLibrary):
    """
    Manages all database interactions.
    """

    @inlineCallbacks
    def _init_(self):
        """
        Check to make sure the database exists. Will create if missing, will also update schema if any
        changes are required.
        """
        self.db_model = {}  #store generated database model here.
        # Connect to the DB
        Registry.DBPOOL = adbapi.ConnectionPool('sqlite3', "usr/etc/yombo.db", check_same_thread=False,
                                                cp_min=1, cp_max=1)
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

        chmod('usr/etc/yombo.db', 0600)

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
          # variable = yield Variable(variable_type='device', variable_id="variable_id1", foreign_id='deviceVariable1', device_id=device.id, weigh=0, machine_label='device_var_1', label='Device Var 1', value='somevalue1', updated=1, created=1).save()

        deviceType = yield DeviceType.find('devicetype1')
        if deviceType is None:
          deviceType = yield DeviceType(id=device.device_type_id,  machine_label='x10_appliance', label='Lamp1', device_class='x10', description='x10 appliances', status=1, created=1, updated=1).save()
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

        results = yield self.dbconfig.update('devices', {'status':status},
                                             where=['id = ?', device_id])
        #
        # device = yield Device.find(device_id)
        # print device
        # device.status = status
        # yield device.save()
        # print "222 %s" % status

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
        records = yield self.dbconfig.select('device_status', select='device_id, set_time, energy_usage, human_status, machine_status, machine_status_extra, requested_by, source, uploaded, uploadable',
                                             where=['device_id = ?', id], orderby='set_time', limit=limit)
        for index in range(len(records)):
            records[index]['machine_status_extra'] = json.loads(str(records[index]['machine_status_extra']))
            records[index]['requested_by'] = json.loads(str(records[index]['requested_by']))
        returnValue(records)

    @inlineCallbacks
    def save_device_status(self, device_id, **kwargs):
        set_time = kwargs.get('set_time', time())
        energy_usage = kwargs['energy_usage']
        machine_status = kwargs['machine_status']
        human_status = kwargs.get('human_status', machine_status)
        machine_status_extra = json.dumps(kwargs.get('machine_status_extra', ''), separators=(',',':') )
        requested_by = json.dumps(kwargs.get('requested_by', ''), separators=(',',':') )
        source = kwargs.get('source', '')
        uploaded = kwargs.get('uploaded', 0)
        uploadable = kwargs.get('uploadable', 0)

        yield DeviceStatus(
            device_id=device_id,
            set_time=set_time,
            energy_usage=energy_usage,
            human_status=human_status,
            machine_status=machine_status,
            machine_status_extra=machine_status_extra,
            source=source,
            uploaded=uploaded,
            requested_by=requested_by,
            uploadable=uploadable,
        ).save()


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
                              installed_version = data['installed_version'],
                              install_time = data['install_time'],
                              last_check = data['install_time'],
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
        results = yield Notifications(
            id=notice['id'],
            type=notice['type'],
            priority=notice['priority'],
            source=notice['source'],
            expire=notice['expire'],
            acknowledged=notice['acknowledged'],
            title=notice['title'],
            message=notice['message'],
            meta=json.dumps(notice['meta'], separators=(',',':') ),
            created=notice['created'],
        ).save()
        returnValue(results)

    @inlineCallbacks
    def set_ack(self, id, new_ack):
        records = yield self.dbconfig.update('notifications', {'acknowledged': new_ack}, where=['id = ?', id])
        returnValue(records)

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
        print "save_session: %s" % session_data
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
                'updated' : updated,
        }
        yield self.dbconfig.update('webinterface_sessions', args, where=['id = ?', session_id] )

    @inlineCallbacks
    def delete_session(self, session_id):
        # print "session_data: %s" % session_data
        yield self.dbconfig.delete('webinterface_sessions', where=['id = ?', session_id] )

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
GROUP BY name""" % (extra_where, str(int(time()) - 60*60*24*60))
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
        sql = "DELETE FROM states WHERE created < %s" % str(int(time()) - 60*60*24*60)
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
        records = yield self.dbconfig.select('sqldict', select='dict_data', where=['component = ? AND dict_name = ?', component, dict_name])
        if len(records) == 1:
            try:
                before = len(records[0]['dict_data'])
                records[0]['dict_data'] = zlib.decompress(base64.decodestring(records[0]['dict_data']) )
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
            dict_data = base64.encodestring( zlib.compress(dict_data, 5) )

        args = {'component': component,
                'dict_name': dict_name,
                'dict_data' : dict_data,
                'updated' : int(time()),
        }
#        print "starting set_sql_dict"
        records = yield self.dbconfig.select('sqldict', select='dict_name', where=['component = ? AND dict_name = ?', component, dict_name])
        if len(records) > 0:
            results = yield self.dbconfig.update('sqldict', args, where=['component = ? AND dict_name = ?', component, dict_name] )
#            print "set_sql_dict: update reuslts: %s" %results
        else:
            args['created'] = args['updated']
            results = yield self.dbconfig.insert('sqldict', args, None, 'OR IGNORE' )
#            print "set_sql_dict: insert reuslts: %s" %results


    #####################
    ### Statistics  #####
    #####################
    @inlineCallbacks
    def get_distinct_stat_names(self, get_all=False):
        if get_all:
            records = yield self.dbconfig.select('statistics',
                         select='name, MIN(bucket) as bucket_min, MAX(bucket) as bucket_max',
                         group='name')
        else:
            records = yield self.dbconfig.select('statistics', where=['type != ?', 'datapoint'],
                         select='name, MIN(bucket) as bucket_min, MAX(bucket) as bucket_max',
                         group='name')
        returnValue(records)

    @inlineCallbacks
    def get_statistic(self, where):
        find_where = dictToWhere(where)
        records = yield Statistics.find(where=find_where)

        # print "stat records: %s" % records
        returnValue(records)

    @inlineCallbacks
    def get_stat_last_datapoints(self):
        sql = """SELECT s1.name, s1.value
FROM  statistics s1
INNER JOIN
(
    SELECT Max(updated) updated, name
    FROM   statistics
    WHERE type = 'datapoint'
    GROUP BY name
) AS s2
    ON s1.name = s2.name
    AND s1.updated = s2.updated
ORDER BY id desc"""
        stats = yield Registry.DBPOOL.runQuery(sql)
        results = {}
        for stat in stats:
            results[stat[0]] = stat[1]
        returnValue(results)

    @inlineCallbacks
    def save_statistic(self, bucket, type, name, value, anon, in_average_data=None):
        args = {'value': value,
                'updated': int(time()),
                'anon': anon,
        }
#        print "starting set_sql_dict"

        records = yield self.dbconfig.select('statistics', select='*', where=['bucket = ? AND type = ? AND name = ?', bucket, type, name])
        if len(records) > 0:  # now we need to merge the results. This can be fun.
#            print "existing stat found: %s" % records[0]
            if type == 'counter':
                args['value'] = records[0]['value'] + value
                results = yield self.dbconfig.update('statistics', args, where=['id = ?', records[0]['id']] )
            elif type == 'datapoint': # chance is super rare.... Just replace the value. Probably never happens.
                results = yield self.dbconfig.update('statistics', args, where=['id = ?', records[0]['id']] )
            elif type == 'average':

                record_average_data = cPickle.loads(str(records[0]['averagedata']))
#                print "record_average_data: %s" % record_average_data
#                print "in_average_data: %s" % in_average_data

                counts = [record_average_data['count'], in_average_data['count']]
                medians = [record_average_data['median'], in_average_data['median']]
                uppers = [record_average_data['upper'], in_average_data['upper']]
                lowers = [record_average_data['lower'], in_average_data['lower']]
                upper_90s = [record_average_data['upper_90'], in_average_data['upper_90']]
                lower_90s = [record_average_data['lower_90'], in_average_data['lower_90']]
                median_90s = [record_average_data['median_90'], in_average_data['median_90']]

                # found this weighted averaging method here:
                # http://stackoverflow.com/questions/29330792/python-weighted-averaging-a-list
                new_average_data = {}
                new_average_data['count'] = record_average_data['count'] + in_average_data['count']
                new_average_data['median'] = sum(x * y for x, y in zip(medians, counts)) / sum(counts)
                new_average_data['upper'] = sum(x * y for x, y in zip(uppers, counts)) / sum(counts)
                new_average_data['lower'] = sum(x * y for x, y in zip(lowers, counts)) / sum(counts)
                new_average_data['upper_90'] = sum(x * y for x, y in zip(upper_90s, counts)) / sum(counts)
                new_average_data['lower_90'] = sum(x * y for x, y in zip(lower_90s, counts)) / sum(counts)
                new_average_data['median_90'] = sum(x * y for x, y in zip(median_90s, counts)) / sum(counts)

                args['averagedata'] = sqlite3Binary(cPickle.dumps(new_average_data, cPickle.HIGHEST_PROTOCOL))
                results = yield self.dbconfig.update('statistics', args, where=['id = ?', records[0]['id']] )
            else:
                pass
        else:
            args['bucket'] =  bucket
            args['type'] = type
            args['name'] = name
            if type == 'average':
                args['averagedata'] = sqlite3Binary(cPickle.dumps(in_average_data, cPickle.HIGHEST_PROTOCOL))
#            print "saving new SQL record: %s" % args
            results = yield self.dbconfig.insert('statistics', args, None, 'OR IGNORE' )

        returnValue(results)
#            print "set_sql_dict: insert reuslts: %s" %results

    @inlineCallbacks
    def get_stats_sums(self, name, type=None, bucket_size=None, time_start=None, time_end=None):
        if bucket_size is None:
            bucket_size = 3600

        wheres = []
        values = []

        wheres.append("(name like ?)")
        values.append(name)

        if type is not None:
            wheres.append("(type > ?)")
            values.append(time_start)

        if time_start is not None:
            wheres.append("(bucket > ?)")
            values.append(time_start)

        if time_end is not None:
            wheres.append("(bucket < ?)")
            values.append(time_end)
        where_final = [(" AND ").join(wheres)] + values
        # print "where_final: %s" % where_final

        # records = yield self.dbconfig.select('statistics',
        #             select='sum(value), name, type, round(bucket / 3600) * 3600 AS bucket',
        select_fields='sum(value) as value, name, type, round(bucket / %s) * %s AS bucket' % (bucket_size, bucket_size)
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
        data['task_arguments'] = sqlite3Binary(cPickle.dumps(data['task_arguments'], cPickle.HIGHEST_PROTOCOL))
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

    @inlineCallbacks
    def get_variables(self, relation_type, relation_id):
        """
        Gets available variables for a given device_id.

        Called by: library.Devices::_init_

        :param variable_type:
        :param foreign_id:
        :return:
        """
        records = yield VariableDataView.find(where=['relation_type = ? AND relation_id =?', relation_type, relation_id], orderby='field_weight ASC, data_weight ASC')
        variables = {}
        for record in records:

            if record.field_machine_label not in variables:
                variables[record.field_machine_label] = {
                    'id': record.id,
                    'relation_id': record.relation_id,
                    'relation_type': record.relation_type,
                    'field_machine_label': record.field_machine_label,
                    'field_label': record.field_label,
                    'field_weight': record.field_weight,
                    'value_min': record.value_min,
                    'value_max': record.value_max,
                    'value_casing': record.encryption,
                    'value_required': record.value_required,
                    'encryption': record.encryption,
                    'input_type_id': record.input_type_id,
                    'default_value': record.default_value,
                    'help_text': record.help_text,
                    'multiple': record.multiple,
                    'data_weight': record.data_weight,
                    'created': record.field_created,
                    'updated': record.field_updated,
                    'data': [],
                }

            variables[record.field_machine_label]['data'].append({
                'id': record.id,
                'value': self._GPG.decrypt_asymmetric(record.data),
                'weight': record.data_weight,
                'created': record.data_created,
                'updated': record.data_updated,
            })
            # variables[record.machine_label]['value'].append(record.value)
#                print record.__dict__
#         print "variables %s:%s = %s" % (relation_type, relation_id, variables)
        returnValue(variables)

    @inlineCallbacks
    def del_variables(self, relation_type, relation_id):
        """
        Deletes variables for a given relation type and relation id.

        :return:
        """
        results = yield self.dbconfig.delete('variable_data', where=['relation_type = ? and relation_id = ?', relation_type, relation_id])
        returnValue(results)

    @inlineCallbacks
    def get_variable_groups(self, relation_type, relation_id):
        """
        Gets all variable groups for a given type and by id.

        :param relation_type:
        :param relation_id:
        :return:
        """
        records = yield VariableGroups.find(
            where=['relation_type = ? AND relation_id =?', relation_type, relation_id],
            orderby='group_weight ASC')
        returnValue(records)

    @inlineCallbacks
    def get_variable_fields_by_group(self, group_id):
        """
        Get all variable fields by groupId

        :param group_id:
        :param relation_id:
        :return:
        """
        records = yield VariableFields.find(
            where=['group_id = ?', group_id],
            orderby='field_weight ASC')
        returnValue(records)

    @inlineCallbacks
    def get_variable_data_by_relation(self, field_id, relation_id):
        """
        Get variable data for a give field/relation

        :param field_id:
        :param relation_id:
        :return:
        """
        records = yield VariableData.find(
            where=['field_id = ? and relation_id = ?', field_id, relation_id],
            orderby='data_weight ASC')
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

