"""
Yombo gateway connects to it's servers using the AMQP library.  It's primarily responsible for connecting to the
server, saying hello, and getting any configuration changes that have happened. This allows the server to
send updates on devices, commands, modules, etc. These messages will be sent to the proper library for handling.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

Connection should be maintained 100% of the time. It's easier on the Yombo servers to maintain an idle connection
than to keep raising and dropping connections.

:TODO: The gateway needs to check for a non-responsive server or if it doesn't get a response in a timely manor.
Perhaps disconnect and reconnect to another server? -Mitch

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2015-2016 by Yombo.
:license: LICENSE for details.
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
from twisted.internet.defer import inlineCallbacks
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

# Import 3rd party extensions
from yombo.ext.expiringdict import ExpiringDict
import yombo.ext.six as six

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import percentage, random_string, dict_has_key
import yombo.ext.umsgpack as msgpack

logger = get_logger('library.amqpyombo')

PROTOCOL_VERSION = 3
PREFETCH_COUNT = 10     # determine how many messages should be received/inflight before yombo servers
                        # stop sending us messages. Should ACK/NACK all messages quickly.


class AMQPYombo(YomboLibrary):
    """
    Handles interactions with Yombo servers through the AMQP library.
    """
    config_item_map = {
        'devices': 'gateway_devices'
    }

    config_items = {
            'commands': {
                'dbclass': "Command",
                'table': "commands",
                'library': "commands",
                'functions': {
                    # 'process': "enable_command",
                    'enabled': "enable_device",
                    'disabled': "disable_device",
                    'deleted': "delete_device",
                },
                'map': {
                    'Uri': 'uri',
                    'UUID': 'id',
                    'machineLabel': 'machine_label',
                    'voice_cmd': 'voice_cmd',
                    'label': 'label',
                    'description': 'description',
                    'inputtype': 'input_type_id',
                    'liveupdate': 'live_update',
                    'created': 'created',
                    'updated': 'updated',
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
                    'UUID': 'id',
                    'Uri': 'uri',
                    # 'machineLabel': 'machineLabel',  #Not implemented yet.
                    'Label': 'label',
                    'Notes': 'notes',
                    'Description': 'description',
                    'GatewayUUID': 'gateway_id',
                    'DeviceTypeUUID': 'device_type_id',
                    'VoiceCmd': 'voice_cmd',
                    'VoiceCmdOrder': 'voice_cmd_order',
                    'voiceCmdSrc': 'Voice_cmd_src',
                    'PinCode': 'pin_code',
                    'PinRequired': 'pin_required',
                    'PinTimeout': 'pin_timeout',
                    'Created': 'created',
                    'Updated': 'updated',
                    'Status': 'status',
                }
            },

            'device_types': {
                'dbclass': "DeviceType",
                'table': "device_types",
                'library': "devices",
                'functions': {
                    'enabled': "enable_device",
                    'disabled': "disable_device",
                    'deleted': "delete_device",
                },
                'map': {
                    'UUID': 'id',
                    'Uri': 'uri',
                    'MachineLabel': 'machine_label',
                    'Label': 'label',
                    'DeviceClass': 'device_class',
                    'Description': 'description',
                    'LiveUpdate': 'live_update',
                    'Commands': 'commands',
                    'Public': 'public',
                    'Created': 'created',
                    'Updated': 'updated',
                    'Status': 'status',
                }
            },

            'gateway_modules': {
                'dbclass': "Modules",
                'table': "modules",
                'library': "modules",
                'functions': {
                    'enabled': "enable_command",
                    'disabled': "enable_command",
                    'deleted': "enable_command",
                },
                'map': {
                    'UUID': 'id',
                    'Uri': 'uri',
                    'MachineLabel': 'machine_label',
                    'ModuleType': 'module_type',
                    'Label': 'label',
                    'Description': 'description',
                    'InstallNotes': 'install_notes',
                    'DocLink': 'doc_link',
                    'ProdVersion': 'prod_version',
                    'DevVersion': 'dev_version',
                    'InstallBranch': 'install_branch',
                    'Public': 'public',
                    'Created': 'created',
                    'Updated': 'updated',
                    'Status': 'status',
                }
            },

            'gateway_configs': {},  # Processed with it's own catch.

            'variables': {
                'dbclass': "Variable",
                'table': "variables",
                'library': "configuration",
                'functions': {
                },
                'map': {
                    'FieldUUID': 'id',
                    'VariableUUID': 'variable_id',
                    'VariableType': 'variable_type',
                    'ForeignUUID': 'foreign_id',
                    'Weight': 'weight',
                    'DataWeight': 'data_weight',
                    'MachineLabel': 'machine_label',
                    'Label': 'label',
                    'Value': 'value',
                    'Updated': 'updated',
                    'UpdatedSrv': 'updated_srv',
                    'Created': 'created',
                }
            },
        }

    def _init_(self):
        self.user_id = "gw_" + self._Configs.get("core", "gwuuid")
        self._startup_request_ID = random_string(length=12)
        self.init_defer = defer.Deferred()
        self.__doing_full_configs = False
        self.__pending_updates = []
        self._LocalDBLibrary = self._Libraries['localdb']

        self.save_cache = ExpiringDict(max_len=100, max_age_seconds=5)

        amqp_port = 5671
        environment = self._Configs.get('server', 'environment', "production", False)
        if self._Configs.get("amqpyombo", 'hostname', "", False) != "":
            amqp_host = self._Configs.get("amqpyombo", 'hostname')
            amqp_port = self._Configs.get("amqpyombo", 'port', 5671, False)
        else:
            if environment == "production":
                amqp_host = "amqp.yombo.net"
            elif environment == "staging":
                amqp_host = "amqpstg.yombo.net"
            elif environment == "development":
                amqp_host = "amqpdev.yombo.net"
            else:
                amqp_host = "amqp.yombo.net"

        # get a new AMPQ connection and connect.
        self.amqp = self._AMQP.new(hostname=amqp_host, port=amqp_port, virtual_host='yombo', username=self.user_id,
            password=self._Configs.get("core", "gwhash"), client_id='amqpyombo',
            connected_callback=self.amqp_connected, disconnected_callback=self.amqp_disconnected)
        self.amqp.connect()

        # Subscribe to the gateway queue.
        self.amqp.subscribe("ygw.q." + self.user_id, incoming_callback=self.amqp_incoming, queue_no_ack=False, persistent=True)

        # Say hello, send some information about us.
        # Local IP address is needed to send to mobile apps / local clients. This allows to mobile app or local client
        # to connect directly to the gateway instead of using Yombo as a proxy. This increases perform greatly for
        # things like light control, etc.  The external IP address will also be sent so that the client can
        # try to connect to the external IP address. If it can not reach the gateway by either of these methods,
        # it will connect to Yombo proxy servers, requests will come through the amqp connection. This is why
        # the connection needs to be open 100% of the time.
        body = {
            "local_ip_address": self._Configs.get("core", "localipaddress"),
            "external_ip_address": self._Configs.get("core", "externalipaddress"),
        }

        requestmsg = self.generate_message_request(
            exchange_name='ysrv.e.gw_config',
            source='yombo.gateway.lib.amqpyombo',
            destination='yombo.server.configs',
            body=body,
            headers={
                "request_type": "startup",
            }
        )
        self.amqp.publish(**requestmsg)

        self.get_system_configs()
        return self.init_defer

    def amqp_connected(self):
        """
        Called by AQMP when connected.
        :return:
        """
        self._States.set('amqp.amqpyombo.state', True)

    def amqp_disconnected(self):
        """
        Called by AQMP when disconnected.
        :return:
        """
        self._States.set('amqp.amqpyombo.state', False)

    def _local_request(self, headers, request_data=""):
        """
        Generate a request specific to this library - configs!

        :param headers:
        :param request_data:
        :return:
        """
        request_msg = self.generate_message_request('ysrv.e.gw_config', 'yombo.gateway.lib.amqpyobo',
                                                    "yombo.server.configs", headers, request_data)
        request_msg['routing_key'] = '*'
        logger.debug("response: {request_msg}", request_msg=request_msg)
        return request_msg

    def generate_message_response(self, properties, exchange_name, source, destination, headers, body ):
        response_msg = self.generate_message(exchange_name, source, destination, "response", headers, body)
        if properties.correlation_id:
           response_msg['properties']['correlation_id'] = properties.correlation_id
#        response_msg['properties']['headers']['response_type']=response_type
        correlation_id = random_string(length=12)

        print "properties: %s" % properties
        if 'route' in properties.headers:
            route = str(properties.headers['route']) + ",yombo.server.configs:" + self.serverid
            response_msg['properties']['headers']['route'] = route
        else:
            response_msg['properties']['headers']['route'] = "yombo.server.configs:" + self.serverid
        return response_msg

    def generate_message_request(self, exchange_name, source, destination, headers, body, callback=None):
        new_body = {
            "data_type": "object",
            "request"  : body,
        }
        if isinstance(body, list):
            new_body['data_type'] = 'objects'

        request_msg = self.generate_message(exchange_name, source, destination, "request",
                                            headers, new_body, callback=callback)
        request_msg['properties']['correlation_id'] = random_string(length=16)
        # request_msg['properties']['headers']['request_type']=request_type
        return request_msg

    def generate_message(self, exchange_name, source, destination, header_type, headers, body, callback=None):
        """
        When interacting with Yombo AMQP servers, we use a standard messaging layout. The below helps other functions
        and libraries conform to this standard.

        This only creates the message, it doesn't send it. Use the publish() function to complete that.

        **Usage**:

        .. code-block:: python

           requestData = {
               "exchange_name"  : "gw_config",
               "source"        : "yombo.gateway.lib.configurationupdate",
               "destination"   : "yombo.server.configs",
               "callback" : self.amqp_direct_incoming,
               "body"          : {
                 "DataType"        : "Object",
                 "Request"         : requestContent,
               },
           }
           request = self.AMQPYombo.generateRequest(**requestData)

        :param exchange_name: The exchange the request should go to.
        :type exchange_name: str
        :param source: Value for the 'source' field.
        :type source: str
        :param destination: Value of the 'destination' field.
        :type destination: str
        :param callback: A pointer to the function to return results to. This function will receive 4 arguments:
          sendInfo (Dict) - Various details of the sent packet. deliver (Dict) - Deliver fields as returned by Pika.
          props (Pika Object) - Message properties, includes headers. msg (dict) - The actual content of the message.
        :type callback: function
        :param body: The body contents for the mesage.
        :type body: dict

        :return: A dictionary that can be directly returned to Yombo Gateways via AMQP
        :rtype: dict
        """
        request_msg = {
            "exchange_name"    : exchange_name,
            "routing_key"      : '*',
            "body"             : msgpack.dumps(body),
            "properties" : {
                # "correlation_id" : correlation_id,
                "user_id"        : self.user_id,
                "content_type"   : 'application/msgpack',
                "headers"        : {
                    "source"        : source + ":" + self.user_id,
                    "destination"   : destination,
                    "type"          : header_type,
                    "protocol_verion": PROTOCOL_VERSION,
                    },
                },
            "callback": callback,
            }

        # Lets test if we can compress. Set headers as needed.

        self._Statistics.averages("lib.amqpyombo.sent.size", len(request_msg['body']), bucket_time=15, anon=True)
        if len(request_msg['body']) > 800:
            beforeZlib = len(request_msg['body'])
            request_msg['body'] = zlib.compress(request_msg['body'], 5)  # 5 appears to be the best speed/compression ratio - MSchwenk
            request_msg['properties']['content_encoding'] = "zlib"
            afterZlib = len(request_msg['body'])
            self._Statistics.increment("lib.amqpyombo.sent.compressed", bucket_time=15, anon=True)
            self._Statistics.averages("lib.amqpyombo.sent.compressed.percentage", percentage(afterZlib, beforeZlib), anon=True)
        else:
            request_msg['properties']['content_encoding'] = 'text'
            self._Statistics.increment("lib.amqpyombo.sent.uncompressed", bucket_time=15, anon=True)
        request_msg['properties']['headers'].update(headers)

        return request_msg


    def amqp_incoming(self, deliver, properties, msg, queue):
        """
        All incoming messages come here. It will be parsed and sorted as needed.  Routing:

        1) Device updates, changes, deletes -> Devices library
        1) Command updates, changes, deletes -> Command library
        1) Module updates, changes, deletes -> Module library
        1) Device updates, changes, deletes -> Devices library
        1) Device updates, changes, deletes -> Devices library

        Summary of tasks:

        1) Validate incoming headers.
        2) Setup ACK/Nack responses.
        3) Route the message to the proper library for final handling.
        """
        self._local_log("debug", "AMQPLibrary::amqp_incoming")
        # print " !!!!!!!!!!!!!!!!!!!!!!!!! "
        # print "properties: %s" % properties
        # print "send_correlation_ids: %s" % self.amqp.send_correlation_ids
        time_info = self.amqp.send_correlation_ids[properties.correlation_id]
        daate_time = time_info['time_received'] - time_info['time_sent']
        milliseconds = (daate_time.days * 24 * 60 * 60 + daate_time.seconds) * 1000 + daate_time.microseconds / 1000.0
        logger.debug("Time between sending and receiving a response:: {milliseconds}", milliseconds=milliseconds)
        self._Statistics.averages("lib.amqpyombo.amqp.response.time", milliseconds, bucket_time=15, anon=True)

#        log.msg('%s (%s): %s' % (deliver.exchange, deliver.routing_key, repr(msg)), system='Pika:<=')

        self._local_log("debug", "PikaProtocol::receive_item3")
        if properties.user_id is None:
            self._Statistics.increment("lib.amqpyombo.received.discarded.nouserid", bucket_time=15, anon=True)
            raise YomboWarning("user_id missing.")
        if properties.content_type is None:
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_type_missing", bucket_time=15, anon=True)
            raise YomboWarning("content_type missing.")
        if properties.content_encoding is None:
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_encoding_missing", bucket_time=15, anon=True)
            raise YomboWarning("content_encoding missing.")
        if properties.content_encoding != 'text' and properties.content_encoding != 'zlib':
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_encoding_invalid", bucket_time=15, anon=True)
            raise YomboWarning("Content Encoding must be either  'text' or 'zlib'. Got: " + properties.content_encoding)
        if properties.content_type != 'text/plain' and properties.content_type != 'application/msgpack' and  properties.content_type != 'application/json':
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_type_invalid", bucket_time=15, anon=True)
            logger.warn('Error with contentType!')
            raise YomboWarning("Content type must be 'application/msgpack', 'application/json' or 'text/plain'. Got: " + properties.content_type)

        if properties.content_encoding == 'zlib':
            beforeZlib = len(msg)
            msg = zlib.decompress(msg)
            afterZlib = len(msg)
            logger.debug("Message sizes: msg_size_compressed = {compressed}, non-compressed = {uncompressed}, percent: {percent}",
                         compressed=beforeZlib, uncompressed=afterZlib, percent=percentage(beforeZlib, afterZlib))
            self._Statistics.increment("lib.amqpyombo.received.compressed", bucket_time=15, anon=True)
            self._Statistics.averages("lib.amqpyombo.received.compressed.percentage", percentage(beforeZlib, afterZlib), bucket_time=15, anon=True)
        else:
            self._Statistics.increment("lib.amqpyombo.received.uncompressed", bucket_time=15, anon=True)
        self._Statistics.averages("lib.amqpyombo.received.payload.size", len(msg), bucket_time=15, anon=True)

        if properties.content_type == 'application/json':
            if self.is_json(msg):
                msg = json.loads(msg)
            else:
                raise YomboWarning("Receive msg reported json, but isn't.")
        elif properties.content_type == 'application/msgpack':
            if self.is_msgpack(msg):
                msg = msgpack.loads(msg)
            else:
                raise YomboWarning("Received msg reported msgpack, but isn't.")

        # do nothing on requests for now.... in future if we ever accept requests, we will handle it here!.
        if properties.headers['type'] == 'request':
            raise YomboWarning("Currently not accepting requests.")
        # if a response, lets make sure it's something we asked for!
        elif properties.headers['type'] == "response":
            if properties.correlation_id is None or not isinstance(properties.correlation_id, six.string_types):
                self._Statistics.increment("lib.amqpyombo.received.discarded.correlation_id_invalid", bucket_time=15, anon=True)
                raise YomboWarning("Correlation_id must be present for 'Response' types, and must be a string.")
            if properties.correlation_id not in self.amqp.send_correlation_ids:
                logger.debug("{correlation_id} not in list of ids: {send_correlation_ids} ",
                             correlation_id=properties.correlation_id, send_correlation_ids=self.amqp.send_correlation_ids.keys())
                self._Statistics.increment("lib.amqpyombo.received.discarded.nocorrelation", bucket_time=15, anon=True)
                raise YomboWarning("Received request {correlation_id}, but never asked for it. Discarding",
                                   correlation_id=properties.correlation_id)
        else:
            self._Statistics.increment("lib.amqpyombo.received.discarded.unknown_msg_type", bucket_time=15, anon=True)
            raise YomboWarning("Unknown message type recieved.")

        self._local_log("debug", "PikaProtocol::receive_item4")

        # if we are here.. we have a valid message....

        try:
            if properties.headers['type'] == 'response':
                # print "222 zz"
                logger.debug("headers: {headers}", headers=properties.headers)
                if properties.headers['response_type'] == 'config':
                    # print "333 zz: %s" % properties.headers['config_item']
                    if properties.headers['config_item'] in self.config_items:
#                        print "process config: config_item: %s, msg: %s" % (properties.headers['config_item'],msg)
                        self.process_config(msg, properties.headers['config_item'])
                        self._remove_full_download_dueue("get_" + properties.headers['config_item'])

        except Exception, e:
            logger.error("--------==(Error: Something bad              )==--------")
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")


    def process_config(self, msg, config_item):
        """
        Process configuration information coming from Yombo Servers. After message is validated, the payload is
        delivered here.

        This is an intermediary method and converts the msg into usable chunks and delievered to "add_update_delete".
        In the future, these may be delievered to the individual libraries for processing.

        :param msg: raw message from AQMP
        :param config_item: What type of configuration item.
        :return:
        """
        if config_item == "gateway_configs":
            payload = msg['data']
            for section in payload:
                for key in section['Values']:
                   self._Configs.set(section['Section'], key['Key'], key['Value'])

        elif config_item in self.config_items:
            config_data = self.config_items[config_item]
            library = self._Loader.loadedLibraries[config_data['library']]
            if 'process' in config_data['functions']:
                klass = getattr(library, config_data['functions']['process'])
            else:
                klass = self.add_update_delete

            # print "Msg: %s" % msg
            if msg['data_type'] == 'object':
                new_data = {}
                data = self.field_remap(msg['data'], config_data)
                if 'updated' in data:
                    data['updated_srv'] = data['updated']
#                logger.info("in amqpyombo:process_config ->> config_item: {config_item}", config_item=config_item)
#                logger.info("amqpyombo::process_config - data: {data}", data=data)
                klass(data, config_item, config_data, True)
                self._Loader.loadedLibraries['devices'].add_update_delete(new_data)
                self.process_config(data, config_item, True)
            else:
                for data in msg['data']:
                    data = self.field_remap(data, config_data)
                    if 'updated' in data:
                        data['updated_srv'] = data['updated']
#                    logger.info("in amqpyombo:process_config ->> config_item: {config_item}", config_item=config_item)
#                    logger.info("amqpyombo::process_config - data: {data}", data=data)
                    klass(data, config_item, True)
        else:
            logger.warn("ConfigurationUpdate::process_config - '{config_item}' is not a valid configuration item. Skipping.", config_item=config_item)
            return

    def field_remap(self, data, config_data):
        new_data = {}
        for key, value in data.iteritems(): # we must re-map AMQP names to local names.  Removes ones without a DB column too.
            if key in config_data['map']:
                # Convert ints and floats.
                if self._LocalDBLibrary.db_model[config_data['table']][config_data['map'][key]]['type'] == "INTEGER":
                    value=int(value)
                elif self._LocalDBLibrary.db_model[config_data['table']][config_data['map'][key]]['type'] == "REAL":
                    value=float(value)
                new_data[config_data['map'][key]] = value
            else:
                new_data[key] = value
        return new_data

    # still in progress function. Need to clean up DB calls.
    # todo: what about updates directly to the library? Just call: config_item = get_config_item('devices')
    @inlineCallbacks
    def add_update_delete(self, data, config_item, from_amqp_incoming=False):
        """
        Adds, updates, or delete various items based on the content of the data item being sent it. It will
        inspect the data and make a determination on what to do. It will also consider the values stored in the
        database for add vs update.

        :param data:
        :param config_item:
        :param from_amqp_incoming:
        :return:
        """
        # print "data: %s"%data
        config_data = self.config_items[config_item]
        required_db_keys = []
        allowed_db_keys = []

        for col, col_data in self._LocalDBLibrary.db_model[config_data['table']].iteritems():
            allowed_db_keys.append(col)
            if col_data['notnull'] == 1:
                required_db_keys.append(col)

        db_data = {}  # dict of just keys that are allowed in the DB.
        for key, value in data.iteritems():
            if key in allowed_db_keys:
                db_data[key] = data[key]


        # print "has_required_db_keys: %s"%has_required_db_keys

        # handle any nested items here.
        if config_item == 'device_types':
            temp = db_data['commands']
            local_data = []
            for temp_data in temp:
                local_data.append(temp_data['UUID'])
            db_data['commands'] = ','.join(local_data)
        elif config_item == 'gateway_modules':
            if 'ModuleConfigs' in data:
                # print "ModuleConfigs, data: %s" % data
                for tempGroup in data['ModuleConfigs']:
                    for tempField in tempGroup['Fields']:
                        field = {
                            'VariableUUID': tempGroup['VariableUUID'],
                            'VariableType': 'module',
                            'FieldUUID': tempField['FieldUUID'],
                            'ForeignUUID': data['id'],  # record = module
                            'Weight': tempGroup['Weight'],
                            'DataWeight': tempField['Weight'],
                            'MachineLabel': tempField['MachineLabel'],
                            'Label': tempField['Label'],
                            'Value': tempField['Value'],
                            'Updated': tempField['Updated'],
                            'UpdatedSrv': tempField['Updated'],
                            'Created': tempField['Created'],
                        }
                        # print "ModuleConfigs, field: %s" % field
                        field = self.field_remap(field, self.config_items['variables'])
                        self.add_update_delete(field, 'variables', True)
        elif config_item == 'gateway_devices':
            if 'DeviceConfigs' in data:
                # print "DeviceConfigs, data: %s" % data
                for tempGroup in data['DeviceConfigs']:
                    for tempField in tempGroup['Fields']:
                        field = {
                            'VariableUUID': tempGroup['VariableUUID'],  # id of the variable, shared with various values
                            'VariableType': 'device',
                            'FieldUUID': tempField['FieldUUID'],  # unique ID for each value
                            'ForeignUUID': data['id'],  # record = device
                            'Weight': tempGroup['Weight'],
                            'DataWeight': tempField['Weight'],
                            'MachineLabel': tempField['MachineLabel'],
                            'Label': tempField['Label'],
                            'Value': tempField['Value'],
                            'Updated': tempField['Updated'],
                            'UpdatedSrv': tempField['Updated'],
                            'Created': tempField['Created'],
                        }
                        # print "DeviceConfigs, field: %s" % field
                        field = self.field_remap(field, self.config_items['variables'])
                        self.add_update_delete(field, 'variables', True)

        # print "config_data: %s"%config_data
        # print "db_data: %s"%db_data

        has_required_db_keys = dict_has_key(data, required_db_keys)
        if has_required_db_keys is False:
            raise YomboWarning("Cannot do anything. Must have these keys: %s  Only had these keys: %s" % (required_db_keys, data), 300, 'add_update_delete', 'Devices')


        action = None
        status_change_actions = None
        records = yield self._LocalDBLibrary.get_dbitem_by_id(config_data['dbclass'], db_data['id'])

        # if config_item == 'variables':
        #     print "data: %s"%data
        #     print "db_data['id']: %s" % db_data['id']
        #     print "config_item: %s" % config_item
        #     print "records: %s" % records

        library = self._Loader.loadedLibraries[config_data['library']]

        if len(records) == 0:
            # print "add record!"
            # action = 'add'
            if from_amqp_incoming:
                db_data['updated_srv'] = data['updated']
            yield self._LocalDBLibrary.insert(config_data['table'], db_data)
            if 'added' in config_data['functions']:
                klass = getattr(library, config_data['functions']['updated'])
                klass(data, True)  # True = the library doesn't need to update the database

        elif len(records) == 1:
            # print "1 record"
            record = records[0]
            if 'status' in data:
                if data['status'] != record['status']:  # might have to disable
                    if data['status'] == 0:
                        status_change_actions = 'disable'
                        if 'disabled' in config_data['functions']:
                            klass = getattr(library, config_data['functions']['disabled'])
                            klass(data, True)
                    elif data['status'] == 1:
                        status_change_actions = 'enable'
                        if 'disaenabledbled' in config_data['functions']:
                            klass = getattr(library, config_data['functions']['enabled'])
                            klass(data, True)
                    elif data['status'] == 2:
                        status_change_actions = 'delete'
                        if 'deleted' in config_data['functions']:
                            klass = getattr(library, config_data['functions']['deleted'])
                            klass(data, True)
                    else:
                        raise YomboWarning("Device status set to an unknown value: %s." % data['status'], 300, 'add_update_delete', 'Devices')

            if data['updated'] > record['updated']:  # lets update!
                action = 'update'
                if from_amqp_incoming:
                    db_data['updated_srv'] = data['updated']
                self._LocalDBLibrary.dbconfig.update(config_data['table'], db_data, where=['id = ?', data['id']] )
                if 'added' in config_data['functions']:
                    klass = getattr(library, config_data['functions']['added'])
                    klass(data, True)
            else:
                pass  # what needs to happen when nothing changes?  Nothing?
        else:
            raise YomboWarning("There are too many %s records. Don't know what to do." % config_data['table'], 300, 'add_update_delete', 'Devices')

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

        logger.debug("request_system_configs.....")

        allCommands = [
            "get_commands",
            "get_device_types", # includes commands
            "get_gateway_devices",
            "get_gateway_modules", # includes Module_device_types,
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
                "since": self._Configs.get("amqpyombo_config_times", item, 0),
            }

            self._Configs.set("amqpyombo_config_times", item, cur_time),

            headers= {
                "request_type": "config",
                "config_item"  : item,
            }
            request = self._local_request(headers, body)

#            print request
            self.amqp.publish(**request)

            self._append_full_download_queue(item)

    def _generate_request_message(self, request_type, requestContent):
        request = {
            "exchange_name": "ysrv.e.gw_config",
            "source"       : "yombo.gateway.lib.configurationupdate",
            "destination"  : "yombo.server.configs",
            "callback"     : self.amqp_direct_incoming,
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
            self.__pending_updates.append(table)

    def _remove_full_download_dueue(self, table):
        # logger.info("Removing table from request queue: {table}", table=table)
        # logger.info("Configs pending: {pendingUpdates}", pendingUpdates=self.__pending_updates)
        if table in self.__pending_updates:
            self.__pending_updates.remove(table)
        logger.debug("Configs pending: {pendingUpdates}", pendingUpdates=self.__pending_updates)

        if len(self.__pending_updates) == 0 and self.__doing_full_configs is True:
            self.__doing_full_configs = False
            self._getAllConfigsLoggerLoop.stop()
            reactor.callLater(0.1, self.init_defer.callback, 10) # give DB some breathing room

    def _show_pending_configs(self):
        waitingTime = time() - self._full_download_start_time
        logger.info("Waited %s for startup; pending these configurations: %s" % (waitingTime, self.__pending_updates))

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
