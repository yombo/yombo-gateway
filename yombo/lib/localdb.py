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
#    HABTM = [dict(name='commands', join_table='command_device_types')]

#    BELONGSTO = ['devices']


class GpgKey(DBObject):
    TABLENAME='gpg_keys'


class Logs(DBObject):
    TABLENAME='logs'


class DeviceTypeModules(DBObject):
    TABLENAME='device_type_modules'


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


class States(DBObject):
    TABLENAME='states'


class Statistics(DBObject):
    TABLENAME='statistics'

class Sqldict(DBObject):
    TABLENAME='sqldict'


class User(DBObject):
#    TABLENAME='users'
    pass

class Variable(DBObject):
    TABLENAME='variables'
    BELONGSTO = ['devices', 'modules']

class Sessions(DBObject):
    TABLENAME='webinterface_sessions'

#### Views ####


class ModuleRoutingView(DBObject):
    TABLENAME='module_routing_view'

#Registry.register(Config)
Registry.SCHEMAS['PRAGMA_table_info'] = ['cid', 'name', 'type', 'notnull', 'dft_value', 'pk']
Registry.register(Device, DeviceStatus, Variable, DeviceType, Command)
Registry.register(Modules, ModuleInstalled)


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
        self._ModDescription = "Manages the local database"
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "https://yombo.net"
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
    def get_dbitem_by_id(self, dbitem, id, status=None):
        if dbitem not in MODULE_CLASSES:
            raise YomboWarning("get_dbitem_by_id expects dbitem to be a DBObject")
#        print MODULE_CLASSES
        if status is None:
            records = yield MODULE_CLASSES[dbitem].find(where=['id = ?', id])
#            print "looking without status!"
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
    def get_commands(self):
        """
        Get all commands
        :return:
        """
        records = yield Command.all()
        returnValue(records)

    # @inlineCallbacks
    # def get_commands_for_device_type(self, device_type_id):
    #     records = yield CommandDeviceTypes.find(where=['device_type_id = ?', device_type_id])
    #     returnValue(records)


#########################
###    Device Types     #####
#########################
    @inlineCallbacks
    def get_input_types(self):
        records = yield self.dbconfig.select("input_types")
        returnValue(records)

#########################
###    Devices      #####
#########################
    @inlineCallbacks
    def get_device_status(self, **kwargs):
        id = kwargs['id']
        limit = self._get_limit(**kwargs)
        records = yield self.dbconfig.select('device_status', select='device_id, set_time, energy_usage, human_status, machine_status, machine_status_extra, source, uploaded, uploadable', where=['device_id = ?', id], orderby='set_time', limit=limit)
        for index in range(len(records)):
            records[index]['machine_status_extra'] = json.loads(str(records[index]['machine_status_extra']))
        returnValue(records)

    @inlineCallbacks
    def save_device_status(self, device_id, **kwargs):
        set_time = kwargs.get('set_time', time())
        energy_usage = kwargs['energy_usage']
        machine_status = kwargs['machine_status']
        human_status = kwargs.get('human_status', machine_status)
        machine_status_extra = json.dumps(kwargs.get('machine_status_extra', ''), separators=(',',':') )
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
            uploadable=uploadable,
        ).save()

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
        # print "session_data: %s" % session_data
        yield Sessions(
            id=session_id,
            session_data=session_data,
            created=created,
            last_access=last_access,
            updated=updated,
        ).save()

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
        yield self.dbconfig.delete('webinterface_sessions', args, where=['id = ?', session_id] )

#########################
###    States     #####
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
        count = yield States.count(where=['name = ?', name])
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

#########################
###    Devices     #####
#########################
    @inlineCallbacks
    def get_devices(self):
#        records = yield self.dbconfig.select("devices_view")
        records = yield self.dbconfig.select("devices")
        returnValue(records)

    @inlineCallbacks
    def get_device_types(self):
#        records = yield self.dbconfig.select("devices_view")
        records = yield self.dbconfig.select("device_types")
        returnValue(records)

    @inlineCallbacks
    def get_device_by_id(self, device_id, status=1):
        records = yield Device.find(where=['id = ? and status = ?', device_id, status])
        results = []
        for record in records:
            results.append(record.__dict__)  # we need a dictionary, not an object
        returnValue(results)

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

    #################
    ### Modules #####
    #################
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
                variables[record.machine_label] = []

            variables[record.machine_label].append({
                'machine_label': record.machine_label,
                'label': record.label,
                'updated': record.updated,
                'created': record.created,
                'weight': record.weight,
                'data_weight': record.data_weight,
                'foreign_id': record.foreign_id,
                'id': record.id,
                'value': record.value,
            })
            # variables[record.machine_label]['value'].append(record.value)
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

