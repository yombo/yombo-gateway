# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This handler library is responsible for handling configuration messages received from amqpyombo library.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/handler/amqpconfigs.py>`_
"""
# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
import zlib
from time import time
import sys
import traceback

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import defer, reactor
from twisted.internet.task import LoopingCall

# Import 3rd party extensions
from yombo.ext.expiringdict import ExpiringDict
import yombo.ext.six as six

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import random_string, dict_has_key
import yombo.ext.umsgpack as msgpack

logger = get_logger('library.handler.amqpconfigs')

class AmqpConfigHandler(YomboLibrary):
    """
    Handles interactions with Yombo servers through the AMQP library.
    """
    config_item_map = {
        'devices': 'gateway_devices'
    }

    config_items = {
            'categories': {
                'dbclass': "Category",
                'table': "categories",
                'library': None,
                'functions': {
                    # 'process': "enable_command",
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'map': {
                    'id': 'id',
                    'category_type': 'category_type',
                    'machine_label': 'machine_label',
                    'label': 'label',
                    'description': 'description',
                    'status': 'status',
                    'created_at': 'created',
                    'updated_at': 'updated',
                    # '': '',
                }
            },

            'gateway_dns_name': {
                'dbclass': "none",
                'table': "none",
                'library': None,
                'functions': {
                },
                'map': {
                }
            },

            'gateway_commands': {
                'dbclass': "Command",
                'table': "commands",
                'library': "commands",
                'functions': {
                    # 'process': "enable_command",
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'map': {
                    'id': 'id',
                    'machine_label': 'machine_label',
                    'voice_cmd': 'voice_cmd',
                    'label': 'label',
                    'description': 'description',
                    'always_load': 'always_load',
                    'created_at': 'created',
                    'updated_at': 'updated',
                    'status': 'status',
                    'public': 'public',
                    # '': '',
                }
            },

            'gateway_devices': {
                'dbclass': "Device",
                'table': "devices",
                'library': "devices",
                'functions': {
                    'enabled': "enable_device",
                    'disabled': "disable_device",
                    'deleted': "delete_device",
                },
                'map': {
                    'id': 'id',
                    'label': 'label',
                    'notes': 'notes',
                    'description': 'description',
                    'gateway_id': 'gateway_id',
                    'device_type_id': 'device_type_id',
                    'voice_cmd': 'voice_cmd',
                    'voice_cmd_order': 'voice_cmd_order',
                    'voice_cmd_src': 'voice_cmd_src',
                    'pin_code': 'pin_code',
                    'pin_required': 'pin_required',
                    'pin_timeout': 'pin_timeout',
                    'statistic_label': 'statistic_label',
                    'energy_type': 'energy_type',
                    'energy_tracker_source': 'energy_tracker_source',
                    'energy_tracker_device': 'energy_tracker_device',
                    'energy_map': 'energy_map',
                    'created_at': 'created',
                    'updated_at': 'updated',
                    'status': 'status',
                }
            },

            'gateway_device_command_inputs': {
                'dbclass': "DeviceCommandInput",
                'table': "device_command_inputs",
                'library': None,
                'functions': {
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'map': {
                    'id': 'id',
                    'category_id': 'category_id',
                    'device_type_id': 'device_type_id',
                    'command_id': 'command_id',
                    'input_type_id': 'input_type_id',
                    'live_update': 'live_update',
                    'value_required': 'value_required',
                    'value_max': 'value_max',
                    'value_min': 'value_min',
                    'value_casing': 'value_casing',
                    'encryption': 'encryption',
                    'notes': 'notes',
                    'always_load': 'always_load',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

            'gateway_device_types': {
                'dbclass': "DeviceType",
                'table': "device_types",
                'library': "devices",
                'functions': {
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'map': {
                    'id': 'id',
                    'category_id': 'category_id',
                    'machine_label': 'machine_label',
                    'label': 'label',
                    'description': 'description',
                    'always_load': 'always_load',
                    'created_at': 'created',
                    'updated_at': 'updated',
                    'public': 'public',
                    'status': 'status',
                }
            },

            'gateway_device_type_commands': {
                'dbclass': "DeviceTypeCommand",
                'table': "device_type_commands",
                'library': None,
                'functions': {
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'map': {
                    'id': 'id',
                    'device_type_id': 'device_type_id',
                    'command_id': 'command_id',
                    'created_at': 'created',
                }
            },

            'gateway_input_types': {
                'dbclass': "InputType",
                'table': "input_types",
                'library': "inputtypes",
                'functions': {
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'map': {
                    'id': 'id',
                    'category_id': 'category_id',
                    'machine_label': 'machine_label',
                    'label': 'label',
                    'description': 'description',
                    'input_regex': 'input_regex',
                    'always_load': 'always_load',
                    'created_at': 'created',
                    'updated_at': 'updated',
                    'public': 'public',
                    'status': 'status',
                }
            },

            'gateway_modules': {
                'dbclass': "Modules",
                'table': "modules",
                'library': "modules",
                'functions': {
                    # 'enabled': "enable_command",
                    # 'disabled': "enable_command",
                    # 'deleted': "enable_command",
                },
                'map': {
                    'module_id': 'id',
                    'gateway_id': 'gateway_id',
                    'machine_label': 'machine_label',
                    'module_type': 'module_type',
                    'label': 'label',
                    'short_description': 'short_description',
                    'description': 'description',
                    'description_formatting': 'description_formatting',
                    'see_also': 'see_also',
                    'repository_link': 'repository_link',
                    'issue_tracker_link': 'issue_tracker_link',
                    'install_count': 'install_count',
                    'doc_link': 'doc_link',
                    'git_link': 'git_link',
                    'prod_branch': 'prod_branch',
                    'dev_branch': 'dev_branch',
                    'prod_version': 'prod_version',
                    'dev_version': 'dev_version',
                    'install_branch': 'install_branch',
                    'always_load': 'always_load',
                    'public': 'public',
                    'status': 'status',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

            'gateway_configs': {},  # Processed with it's own catch.

            'gateway_users': {
                'dbclass': "Users",
                'table': "users",
                'library': None,
                'functions': {
                },
                'map': {
                    'id': 'id',
                    'gateway_id': 'gateway_id',
                    'user_id': 'user_id',
                    'email': 'email',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

            'module_device_type': {
                'dbclass': "ModuleDeviceTypes",
                'table': "module_device_types",
                'library': None,
                'functions': {
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'map': {
                    'id': 'id',
                    'module_id': 'module_id',
                    'device_type_id': 'device_type_id',
                    'created_at': 'created',
                }
            },

            'variable_groups': {
                'dbclass': "VariableGroups",
                'table': "variable_groups",
                'library': "configuration",
                'functions': {
                },
                'map': {
                    'id': 'id',
                    'relation_id': 'relation_id',
                    'relation_type': 'relation_type',
                    'group_machine_label': 'group_machine_label',
                    'group_label': 'group_label',
                    'group_description': 'group_description',
                    'group_weight': 'group_weight',
                    'status': 'status',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

            'variable_fields': {
                'dbclass': "VariableFields",
                'table': "variable_fields",
                'library': "configuration",
                'functions': {
                },
                'map': {
                    'id': 'id',
                    'group_id': 'group_id',
                    'field_machine_label': 'field_machine_label',
                    'field_label': 'field_label',
                    'field_description': 'field_description',
                    'field_weight': 'field_weight',
                    'value_required': 'value_required',
                    'value_max': 'value_max',
                    'value_min': 'value_min',
                    'value_casing': 'value_casing',
                    'encryption': 'encryption',
                    'input_type_id': 'input_type_id',
                    'default_value': 'default_value',
                    'help_text': 'help_text',
                    'multiple': 'multiple',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

            'variable_data': {
                'dbclass': "VariableData",
                'table': "variable_data",
                'library': "configuration",
                'functions': {
                },
                'map': {
                    'id': 'id',
                    'gateway_id': 'gateway_id',
                    'field_id': 'field_id',
                    'relation_id': 'relation_id',
                    'relation_type': 'relation_type',
                    'data': 'data',
                    'data_weight': 'data_weight',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

    }

    def __init__(self, amqpyombo):
        """
        Loads various variables and calls :py:meth:connect() when it's ready.

        :return:
        """
        self.parent = amqpyombo
        self.init_startup_count = 0
        self.init_defer = defer.Deferred()  # Prevents loader from moving on until we are done.
        self.__doing_full_configs = False  # will be set to True later when download configurations
        self.__pending_updates = {}  # Holds a dict of configuration items we've asked for, but not response yet.
        self.__process_queue = {}  # Holds a list of configuration items we've asked for, but not response yet.
        self.processing = False
        self.processing_queue = False
        self._checkProcessQueueLoop = LoopingCall(self.process_config_queue)
        self.check_download_done_loop = None

        self._LocalDBLibrary = self.parent._Libraries['localdb']

        self.amqp = None  # holds our pointer for out amqp connection.
        self._getAllConfigsLoggerLoop = None

    def connect_setup(self):
        """

        :return:
        """
        # self.get_system_configs()
        # self.check_download_done_loop = reactor.callLater(30, self.check_download_done)
        return self.init_defer

    def connected(self):
        """

        :return:
        """
        self.get_system_configs()
        self.check_download_done_loop = reactor.callLater(30, self.check_download_done)
        # return self.init_defer

    def disconnected(self):
        """
        Called by amqpyombo when the system is disconnected.
        :return:
        """
        if self._getAllConfigsLoggerLoop is not None and self._getAllConfigsLoggerLoop.running:
            self._getAllConfigsLoggerLoop.stop()
        if self._checkProcessQueueLoop is not None and self._checkProcessQueueLoop.running:
            self._checkProcessQueueLoop.stop()

        self.__pending_updates.clear()
        self.__doing_full_configs = False

        try:
            self.check_download_done_loop.cancel()
        except:
            pass

    def _stop_(self):
        """
        Called by the Yombo system when it's time to shutdown. This in turn calls the disconnect.
        :return:
        """
        if self.init_defer.called is False:
            # reactor.callLater(0.1, self.init_defer.callback, 10) #
            self.init_defer.callback(1)  # if we don't check for this, we can't stop!

        if self._getAllConfigsLoggerLoop is not None and self._getAllConfigsLoggerLoop.running:
            self._getAllConfigsLoggerLoop.stop()
        if self._checkProcessQueueLoop is not None and self._checkProcessQueueLoop.running:
            self._checkProcessQueueLoop.stop()
        try:
            self.check_download_done_loop.cancel()
        except:
            pass


    def check_download_done(self):
        """
        Called after 30 seconds to check if downloads have completed. If they haven't, it will just give up and move on.

        :return:
        """
        if self.__doing_full_configs == True:
            last_complete = self.parent._Configs.get("amqpyombo", 'lastcomplete')
            if last_complete == None:
                if self.init_startup_count > 5:
                    logger.error("Unable to reach or contact server. If problem persists, check your configs. (Help link soon.)")
                    self.reconnect = False
                    reactor.stop()
                    return
                logger.warn("Try #{count}, haven't been able to download configurations. However, there are no existing configs. Will keep trying.",
                            count=self.init_startup_count)
            else:
                if last_complete < int(time() - 60*60*48):
                    logger.warn("Try #{count}, haven't been able to download configurations. Will continue trying in background.",
                            count=self.init_startup_count)
                    logger.warn("Using old configuration information. If this persists, check your configs. (Help link soon.)")
                    if self.init_defer.called is False:
                        self.init_defer.callback(1)  # if we don't check for this, we can't stop!
                else:
                    logger.error("Unable to reach or contact server. Configurations too old to keep using. If problem persists, check your configs. (Help link soon.)")
                    self.reconnect = False
                    reactor.stop()
                    return

            self.init_startup_count = self.init_startup_count + 1
            self.check_download_done_loop = reactor.callLater(30, self.check_download_done) #

    def generate_config_request(self, headers, request_data=""):
        """
        Generate a request specific to this library - configs!

        :param headers:
        :param request_data:
        :return:
        """
        request_msg = self.parent.generate_message_request('ysrv.e.gw_config', 'yombo.gateway.lib.amqpyobo',
                                                    "yombo.server.configs", headers, request_data)
        request_msg['routing_key'] = '*'
        logger.debug("response: {request_msg}", request_msg=request_msg)
        return request_msg

    def process_config_response(self, msg, properties):
        """
        Process configuration information coming from Yombo Servers. After message is validated, the payload is
        delivered here.

        This is an intermediary method and converts the msg into usable chunks and delievered to "add_update_delete".
        In the future, these may be delievered to the individual libraries for processing.

        :param msg: raw message from AQMP
        :param properties: msg properties, so additional information can be retrieved.
        :return:
        """
        # logger.info("properties: {properties}", properties=properties)
        # logger.info("headers: {headers}", headers=properties.headers)
        #
        # config_item = properties.headers['config_item']

        if properties.headers['config_item'] not in self.config_items:
            raise YomboWarning("Configuration item '%s' not configured." % properties.headers['config_item'])
            #                        print "process config: config_item: %s, msg: %s" % (properties.headers['config_item'],msg)
        self.__process_queue[random_string(length=10)] = {
            'msg': msg,
            'headers': properties.headers,
            }
        self.__pending_updates['get_%s' % properties.headers['config_item']]['status'] = 'received'

        self.process_config_queue();

    @inlineCallbacks
    def process_config_queue(self):
        """
        We queue incoming responses for processing. This helps to prevent race conditions as well as
        killing sqlite3 database with a bunch of concurrent requests.

        This is called to feed the process_config function configuration items to process and is called whenever
        we receive a configuration response item as well as a looping call to ensure everything gets processed.
        :return:
        """
        if self.processing:
            returnValue(None)

        if self.processing_queue == False:
            self.processing_queue = True
            for key in list(self.__process_queue):
                queue = self.__process_queue[key]
                self.__pending_updates['get_%s' % queue['headers']['config_item']]['status'] = 'processing'
                yield self.process_config(queue['msg'], queue['headers']['config_item'], queue['headers']['config_type'])
                del self.__process_queue[key]
            self.processing_queue = False


    @inlineCallbacks
    def process_config(self, msg, config_item, config_type=None):
        """
        Process configuration information coming from Yombo Servers. After message is validated, the payload is
        delivered here.

        This is an intermediary method and converts the msg into usable chunks and delievered to "add_update_delete".
        In the future, these may be delievered to the individual libraries for processing.

        :param msg: raw message from AQMP
        :param properties: msg properties, so additional information can be retrieved.
        :return:
        """
        self.processing = True
        # print "processing config.... %s" % config_item
        # print "processing msg.... %s" % msg
        if msg['code'] != 200:
            logger.warn("Configuration for configuration '{type}' received an error ({code}): {error}", type=config_item, code=msg['code'], error=msg['message'])
            self._remove_full_download_dueue("get_" + config_item)
            self.processing = False
            return;

        if config_item == "gateway_configs":
            payload = msg['data']
            for section in payload:
                for key in section['Values']:
                   self.parent._Configs.set(section['Section'], key['Key'], key['Value'])

        elif config_item == "gateway_dns_name":
            payload = msg['data']
            self.parent._Configs.set('dns', 'dns_name', payload['dns_name'])
            self.parent._Configs.set('dns', 'dns_domain', payload['dns_domain'])
            self.parent._Configs.set('dns', 'dns_domain_id', payload['dns_domain_id'])
            self.parent._Configs.set('dns', 'allow_change_at', payload['allow_change_at'])
            self.parent._Configs.set('dns', 'fqdn', payload['fqdn'])

        elif config_item in self.config_items:
            config_data = self.config_items[config_item]
            # print "Msg: %s" % msg
            if config_type == 'full':
                yield self._LocalDBLibrary.truncate(config_data['table'])

            if msg['data_type'] == 'object':
                data = self.field_remap(msg['data'], config_data)
                # if 'updated' in data:
                #     data['updated_srv'] = data['updated']
#                logger.info("in amqpyombo:process_config ->> config_item: {config_item}", config_item=config_item)
#                logger.info("amqpyombo::process_config - data: {data}", data=data)
                yield self.add_update_delete(msg, data, config_item, config_data, True)
                # self._Loader.loadedLibraries['devices'].add_update_delete(new_data)
                self.process_config(data, config_item)
            else:
                for data in msg['data']:
                    data = self.field_remap(data, config_data)
                    # if 'updated' in data:
                    #     data['updated_srv'] = data['updated']
#                    logger.info("in amqpyombo:process_config ->> config_item: {config_item}", config_item=config_item)
#                    logger.info("amqpyombo::process_config - data: {data}", data=data)
                    yield self.add_update_delete(msg, data, config_item, True)
        else:
            logger.warn("ConfigurationUpdate::process_config - '{config_item}' is not a valid configuration item. Skipping.", config_item=config_item)
        self._remove_full_download_dueue("get_" + config_item)
        self.processing = False

    def field_remap(self, data, config_data):
        # print "field remap"
        # print "field remap - config_data =%s" % config_data
        # print "field remap - data =%s" % data
        new_data = {}
        # print "remap data: %s" % data
        table_meta = self._LocalDBLibrary.db_model[config_data['table']]
        # print "tablemeta: %s" % table_meta
        key = None
        value = None
        try:
            for key, value in data.iteritems(): # we must re-map AMQP names to local names.  Removes ones without a DB column too.
                if key in config_data['map']:
                    # print "field remap - key = %s (%s)" % (key, table_meta[config_data['map'][key]]['type'])
                    # Convert ints and floats.
                    if value is None:
                        pass
                    elif table_meta[config_data['map'][key]]['type'] == "INTEGER":
                        value=int(value)
                    elif table_meta[config_data['map'][key]]['type'] == "REAL":
                        value=float(value)
                    new_data[config_data['map'][key]] = value
                else:
                    new_data[key] = value
            return new_data
        except Exception, e:
            print "error in field remap.  Last key: %s" % key
            # print "table info for key: %s" % table_meta[config_data['map'][key]]
            print "input value: %s" % value
            print "field remap - config_data =%s" % config_data
            print "field remap - data =%s" % data
            print "tablemeta: %s" % table_meta

            logger.error("--------==(Error: Something bad              )==--------")
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")

    # still in progress function. Need to clean up DB calls.
    # todo: what about updates directly to the library? Just call: config_item = get_config_item('devices')
    @inlineCallbacks
    def add_update_delete(self, msg, data, config_item, from_amqp_incoming=False):
        """
        Adds, updates, or delete various items based on the content of the data item being sent it. It will
        inspect the data and make a determination on what to do. It will also consider the values stored in the
        database for add vs update.

        :param data:
        :param config_item:
        :param from_amqp_incoming:
        :return:
        """
        # print "add_update_delete config_item111111: %s" % config_item
        # print "add_update_delete msg....11111111111 %s" % msg
        # print "data: %s"%data
        config_data = self.config_items[config_item]
        required_db_keys = []
        allowed_db_keys = []

        table_cols = self._LocalDBLibrary.db_model[config_data['table']].iteritems()
        for col, col_data in table_cols:
            allowed_db_keys.append(col)
            if col_data['notnull'] == 1:
                required_db_keys.append(col)

        db_data = {}  # dict of just keys that are allowed in the DB.
        for key, value in data.iteritems():
            if key in allowed_db_keys:
                db_data[key] = data[key]


        # print "has_required_db_keys: %s"%has_required_db_keys

        # if config_item == 'device_types':
        #     temp = db_data['commands']
        #     local_data = []
        #     for temp_data in temp:
        #         local_data.append(temp_data['UUID'])
        #     db_data['commands'] = ','.join(local_data)

        if config_item == 'gateway_modules':
            yield self._LocalDBLibrary.delete('module_device_types', where=['module_id = ?', data['id']])

        if config_item == 'variable_groups':
            yield self._LocalDBLibrary.delete('variable_groups', where=['relation_id = ?', data['relation_id']])

        if config_item == 'gateway_users':
            yield self._LocalDBLibrary.delete('users')

        if 'status' in data:
            if data['status'] == 2:  # delete any nested items...
                if config_item == 'gateway_modules':
                    yield self._LocalDBLibrary.delete('module_installed', where=['module_id = ?', data['id']])
                    yield self._LocalDBLibrary.delete('module_device_types', where=['module_id = ?', data['id']])

        # print "config_data: %s"%config_data
        # print "db_data: %s"%db_data

        has_required_db_keys = dict_has_key(data, required_db_keys)
        if has_required_db_keys is False:
            raise YomboWarning("Cannot do anything. Must have these keys: %s  Only had these keys: %s" % (required_db_keys, data), 300, 'add_update_delete', 'Devices')


        records = yield self._LocalDBLibrary.get_dbitem_by_id(config_data['dbclass'], db_data['id'])

        library = None
        if config_data['library'] is not None:
            library = self.parent._Loader.loadedLibraries[config_data['library']]

        if len(records) == 0:
            # print "add record!"
            # action = 'add'
            if from_amqp_incoming:
                if 'updated_srv' in table_cols:
                    db_data['updated_srv'] = data['updated']
            # print "db_data['id']: %s" % db_data['id']
            # print "config_data['dbclass']: %s" % config_data['dbclass']
            #     print "config_item: %s" % config_item
            # print "records: %s" % records
            # print "inserting into: %s   data: %s" % (config_data['table'], db_data)
            if 'status' in data:
                if data['status'] == 2: # we don't add deleted items...
                    returnValue(None)
            yield self._LocalDBLibrary.insert(config_data['table'], db_data)
            if 'added' in config_data['functions']:
                klass = getattr(library, config_data['functions']['updated'])
                klass(data, True)  # True = the library doesn't need to update the database

        elif len(records) == 1:
            # print "1 record"
            record = records[0]
            # if 'status' in data:
            #     print "record= %s" % record
            #     if data['status'] != record['status']:  # might have to disable
            #         if data['status'] == 0:
            #             status_change_actions = 'disable'
            #             if 'disabled' in config_data['functions']:
            #                 klass = getattr(library, config_data['functions']['disabled'])
            #                 klass(data, True)
            #         elif data['status'] == 1:
            #             status_change_actions = 'enable'
            #             if 'disaenabledbled' in config_data['functions']:
            #                 klass = getattr(library, config_data['functions']['enabled'])
            #                 klass(data, True)
            #         elif data['status'] == 2:
            #             status_change_actions = 'delete'
            #             if 'deleted' in config_data['functions']:
            #                 klass = getattr(library, config_data['functions']['deleted'])
            #                 klass(data, True)
            #         else:
            #             raise YomboWarning("Device status set to an unknown value: %s." % data['status'], 300, 'add_update_delete', 'Devices')

            if 'updated' in data and 'updated' in record:
                if 'status' in record: # if the record has been marked deleted, lets delete it.
                    if record['status'] == 2:
                        self._LocalDBLibrary.dbconfig.delete(config_data['table'], where=['id = ?', data['id']])

                elif data['updated'] > record['updated']:  # lets update!
                    action = 'update'
                    if from_amqp_incoming:
                        if 'updated_srv' in table_cols:
                            db_data['updated_srv'] = data['updated']
                    self._LocalDBLibrary.dbconfig.update(config_data['table'], db_data, where=['id = ?', data['id']] )
                    if 'added' in config_data['functions']:
                        klass = getattr(library, config_data['functions']['added'])
                        klass(data, True)
            else:
                pass  # what needs to happen when nothing changes?  Nothing?
        else:
            raise YomboWarning("There are too many %s records. Don't know what to do." % config_data['table'], 300, 'add_update_delete', 'Devices')

        # handle any nested items here.
        if 'device_types' in data:
            # print "device types: %s" % data['device_types']
            if len(data['device_types']):
                newMsg = msg.copy()
                newMsg['data'] = data['device_types']
                self.process_config(newMsg, 'module_device_type')

        if 'variable_groups' in data:
            if len(data['variable_groups']):
                newMsg = msg.copy()
                newMsg['data'] = data['variable_groups']
                self.process_config(newMsg, 'variable_groups')

        if 'variable_fields' in data:
            if len(data['variable_fields']):
                newMsg = msg.copy()
                newMsg['data'] = data['variable_fields']
                self.process_config(newMsg, 'variable_fields')

        if 'variable_data' in data:
            if len(data['variable_data']):
                # print "var data: %s"  % data['variable_data']
                yield self._LocalDBLibrary.delete('variable_data', where=['relation_type = ? and relation_id = ?',
                                                                          data['variable_data'][0]['relation_type'],
                                                                          data['variable_data'][0]['relation_id']])
                newMsg = msg.copy()
                newMsg['data'] = data['variable_data']
                self.process_config(newMsg, 'variable_data')

                    # print "device add-update-delete action: %s, status_change_action: %s" %( action, status_change_actions)

    def get_config_item(self, library):
        """
        Simple lookup function to get config_item
        :param library:
        :return:
        """
        return self.config_item_map[library]

    def get_system_configs(self):
        """
        On startup, this is called to request all configuration items.

        TODO: After heavy development cycle is done, we check will be placed here to determine if the gateway
        can reach the servers or not. It it's not possible, and we some configuration data that isn't too old,
        we will can start without talking to the servers.

        :return:
        """
        self.__doing_full_configs = True
        self._full_download_start_time = time()
        self._getAllConfigsLoggerLoop = LoopingCall(self._show_pending_configs)
        self._getAllConfigsLoggerLoop.start(5, False)  # Display a log line for pending downloaded, false - Dont' show now
        self._checkProcessQueueLoop.start(0.5, False)

        logger.info("Requesting system configurations from server. This can take a few seconds.")

        allCommands = [
            "get_categories",
            "get_gateway_commands",
            "get_gateway_devices", # Includes device variable groups/fields/data
            "get_gateway_device_types",
            "get_gateway_modules", # Includes module variable groups/fields/data

            "get_gateway_device_type_commands",
            "get_gateway_device_command_inputs",
            "get_gateway_input_types",
            "get_gateway_users",
            "get_gateway_dns_name",
            # "get_gateway_input_types",

            # "get_gateway_configs",

#            "GetModuleVariables",
#            "getGatewayUserTokens",
#            "getGatewayUsers",
        ]
        cur_time = int(time())
        for item in allCommands:
            logger.debug("sending command: {item}", item=item)

           # request device updates
            body = {
                "since": self.parent._Configs.get("amqpyombo_config_times", item, 0),
            }

            self.parent._Configs.set("amqpyombo_config_times", item, cur_time),

            headers= {
                "request_type": "config",
                "config_item"  : item,
            }
            request = self.generate_config_request(headers, body)

#            print request
            self.parent.amqp.publish(**request)

            self._append_full_download_queue(item)

    def _generate_request_message(self, request_type, requestContent):
        request = {
            "exchange_name": "ysrv.e.gw_config",
            "source"       : "yombo.gateway.lib.configurationupdate",
            "destination"  : "yombo.server.configs",
            "body": {
              "data_type": "object",
              "request"  : requestContent,
            },
            "request_type": request_type,
        }
        return self.AMQPYombo.generate_request_message(**request)

    def _append_full_download_queue(self, table):
        """
        Adds an item to pending table queue.

        Will be removed as each config item is returned by _removeFullTableQueue.
        """
        if table not in self.__pending_updates:
            logger.debug("Adding table to request queue: {table}", table=table)
            self.__pending_updates[table] = {
                'status': 'requested',
                'request_time': time(),
            }

    def _remove_full_download_dueue(self, table):
        # logger.info("Removing table from request queue: {table}", table=table)
        # logger.info("Configs pending: {pendingUpdates}", pendingUpdates=self.__pending_updates)
        if table in self.__pending_updates:
            del self.__pending_updates[table]
        logger.debug("Configs pending: {pendingUpdates}", pendingUpdates=self.__pending_updates)

        if len(self.__pending_updates) == 0 and self.__doing_full_configs is True:
            self.__doing_full_configs = False
            self._getAllConfigsLoggerLoop.stop()
            self._checkProcessQueueLoop.stop()
            reactor.callLater(0.1, self.done_with_startup_downloads) # give DB some breathing room

    def done_with_startup_downloads(self):
        """
        Called when configuration downloads are complete.
        :return:
        """
        self.parent._Configs.set("amqpyombo", 'lastcomplete', int(time()))
        if self.init_defer.called is False:
            self.init_defer.callback(1)  # if we don't check for this, we can't stop!
            self.parent._Notifications.add(
                {'title': 'Configs Downloaded', 'message': 'Downloaded system configurations from Yombo server.',
                 'timeout': 300, 'source': 'Yombo Gateway System'})


    def _show_pending_configs(self):
        waitingTime = time() - self._full_download_start_time
        logger.info("Waited {waitingTime} for startup; pending these configurations:", waitingTime=waitingTime)
        for key in list(self.__pending_updates):
            logger.info("Config: {config}, Status: {status}", config=key,  status=self.__pending_updates[key]['status'])
            if self.__pending_updates[key]['status'] == 'processing':
                self.check_download_done_loop.reset(30)

    def is_json(self, myjson):
        """
        Helper function to determine if data is json or not.

        :param myjson:
        :return:
        """
        try:
            json_object = json.loads(myjson)
        except ValueError, e:
            return False
        return True

    def is_msgpack(self, mymsgpack):
        """
        Helper function to determine if data is msgpack or not.

        :param mymsgpack:
        :return:
        """
        try:
            json_object = msgpack.loads(mymsgpack)
        except ValueError, e:
            return False
        return True

    def _local_log(self, level, location, msg=""):
        logit = func = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

