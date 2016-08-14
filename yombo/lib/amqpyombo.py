#cython: embedsignature=True
# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
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

import yombo.ext.umsgpack as msgpack

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboMessageError
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import percentage, random_string
from yombo.core.message import Message

logger = get_logger('library.amqpyombo')

PROTOCOL_VERSION = 2
PREFETCH_COUNT = 10  # determine how many messages should be received/inflight before yombo servers
                     # stop sending us messages. Should ACK/NACK all messages quickly.


class AMQPYombo(YomboLibrary):
    """
    Handles interactions with Yombo servers through the AMQP library.
    """
    config_items = {
            'commands' : {
                'table': "commands",
                'library': "commands",
                'function': "add_update_delete",
                'map' : {
                    'Uri' : 'uri',
                    'UUID' : 'id',
                    'machineLabel' : 'machine_label',
                    'voice_cmd' : 'voice_cmd',
                    'label' : 'label',
                    'description' : 'description',
                    'inputtype' : 'input_type_id',
                    'liveupdate' : 'live_update',
                    'created' : 'created',
                    'updated' : 'updated',
                    'status' : 'status',
                    'public' : 'public',
#                    '' : '',
                }
            },
###  needs an ID of some sort for update/delete
            'command_device_types' : {
                'table': "command_device_types",
                'library': "commands",
                'function': "add_or_update_device_types",
                'map' : {
                    'device_type_id' : 'device_type_id',
                    'command_id' : 'command_id',
                }
            },

            'gateway_devices' : {
                'table': "devices",
                'library': "devices",
                'function': "add_update_delete",
                'map' : {
                    'UUID' : 'id',
                    'Uri' : 'uri',
#                   'machineLabel' : 'machineLabel',  #Not implemented yet.
                    'Label' : 'label',
                    'Notes' : 'notes',
                    'Description' : 'description',
                    'GatewayUUID' : 'gateway_id',
                    'DeviceTypeUUID' : 'device_type_id',
                    'VoiceCmd' : 'voice_cmd',
                    'VoiceCmdOrder' : 'voice_cmd_order',
                    'voiceCmdSrc' : 'Voice_cmd_src',
                    'PinCode' : 'pin_code',
                    'PinRequired' : 'pin_required',
                    'PinTimeout' : 'pin_timeout',
                    'Created' : 'created',
                    'Updated' : 'updated',
                    'Status' : 'status',
                }
            },

            'device_types' : {
                'table': "device_types",
                'library': "devices",
                'function': "add_or_update_device_types",
                'map' : {
                    'UUID' : 'id',
                    'Uri' : 'uri',
                    'MachineLabel' : 'machine_label',
                    'Label' : 'label',
                    'DeviceClass' : 'device_class',
                    'Description' : 'description',
                    'LiveUpdate' : 'live_update',
                    'Public' : 'public',
                    'Created' : 'created',
                    'Updated' : 'updated',
                    'Status' : 'status',
                }
            },

###  needs an ID of some sort for update/delete
            'device_type_modules' : {
                'table': "device_type_modules",
                'library': "modules",
                'function': "add_or_update_device_types",
                'map' : {
                    'device_type_id' : 'device_type_id',
                    'module_id' : 'module_id',
                    'priority' : 'priority',
                }
            },

            'gateway_modules' : {
                'table': "modules",
                'library': "modules",
                'function': "add_or_update_modules",
                'map' : {
                    'UUID' : 'id',
                    'Uri' : 'uri',
                    'MachineLabel' : 'machine_label',
                    'ModuleType' : 'module_type',
                    'Label' : 'label',
                    'Description' : 'description',
                    'InstallNotes' : 'instal_notes',
                    'DocLink' : 'doc_link',
                    'ProdVersion' : 'prod_version',
                    'DevVersion' : 'dev_version',
                    'InstallBranch' : 'install_branch',
                    'Public' : 'public',
                    'Created' : 'created',
                    'Updated' : 'updated',
                    'Status' : 'status',
                }
            },

            'gateway_configs' : {}, # Processed with it's own catch.
            'variables' : {
                'table': "variables",
                'library': "configuration",
                'function': "add_or_update_configs",
                'map' : {
                    'VariableType' : 'variable_type',
                    'ForeignUUID' : 'foreign_id',
                    'VariableUUID' : 'variable_id',
                    'Weight' : 'weight',
                    'DataWeight' : 'data_weight',
                    'MachineLabel' : 'machine_label',
                    'Label' : 'label',
                    'Value' : 'value',
                    'Updated' : 'updated',
                    'Created' : 'created',
                }
            },

#            "GatewayDetails",
#            "gateway_modules",
#            "GatewayUserTokens",
#            "GatewayVariables",
#            "GatewayUsers",
        }

    def _init_(self, loader):
        self.loader = loader
        self.gwuuid = "gw_" + self._Configs.get("core", "gwuuid")
        self._startup_request_ID = random_string(length=12) #gw
        self.init_defer = defer.Deferred()
        self.__doing_full_configs = False
        self.__pending_updates = []
        self._LocalDBLibrary = self._Libraries['localdb']

        amqp_port = 5671
        environment = self._Configs.get('server', 'environment', "production", False)
        if self._Configs.get("amqpyombo", 'hostname', "", False) != "":
            amqp_host = self._Configs.get("amqpyombo", 'hostname', False)
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

        # get a new AMPQ connection.
        self.amqp = self._AMQP.new(hostname=amqp_host, port=amqp_port, virtual_host='yombo', username=self.gwuuid,
            password=self._Configs.get("core", "gwhash"), client_id='amqpyombo')

        # Subscribe to the gateway queue.
        self.amqp.subscribe("ygw.q." + self.gwuuid, incoming_callback=self.amqp_incoming, queue_no_ack=False, persistent=True)

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
            request_type='startup',
        )
        self.amqp.publish(**requestmsg)

        self.get_system_configs()
        return self.init_defer

    def _load_(self):
        pass

    def generate_message_request(self, exchange_name, source, destination, body, request_type, callback=None):
        new_body = {
            "data_type": "object",
            "request"  : body,
        }
        if isinstance(body, list):
            new_body['data_type'] = 'objects'

        request_msg = self.generate_message(exchange_name, source, destination, new_body, header_type="request", callback=callback)
        request_msg['properties']['headers']['request_type']=request_type
        return request_msg

    def generate_message(self, exchange_name, source, destination, body, request_type=None, header_type=None, callback=None):
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
               "request_type"   : "GetCommands",
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
        :param request_type: Value of the "request_type" field.
        :type request_type: str

        :return: A dictionary that can be directly returned to Yombo Gateways via AMQP
        :rtype: dict
        """
        correlation_id = random_string(length=12)
        requestmsg = {
            "exchange_name"    : exchange_name,
            "routing_key"      : '*',
            "body"             : msgpack.dumps(body),
            "properties" : {
                "correlation_id" : correlation_id,
                "user_id"        : self.gwuuid,
                "content_type"   : 'application/msgpack',
                "headers"        : {
                    "source"        : source + ":" + self.gwuuid,
                    "destination"   : destination,
                    "type"          : header_type,
                    "protocol_verion": PROTOCOL_VERSION,
                    },
                },
            "callback": callback,
            }

        # Lets test if we can compress. Set headers as needed.

        self._Statistics.averages("lib.amqpyombo.sent.size", len(requestmsg['body']), bucket_time=15, anon=True)
        if len(requestmsg['body']) > 800:
            beforeZlib = len(requestmsg['body'])
            requestmsg['body'] = zlib.compress(requestmsg['body'], 5)  # 5 appears to be the best speed/compression ratio - MSchwenk
            requestmsg['properties']['content_encoding'] = "zlib"
            afterZlib = len(requestmsg['body'])
            self._Statistics.increment("lib.amqpyombo.sent.compressed", bucket_time=15, anon=True)
            self._Statistics.averages("lib.amqpyombo.sent.compressed.percentage", percentage(afterZlib, beforeZlib), anon=True)
        else:
            requestmsg['properties']['content_encoding'] = 'text'
            self._Statistics.increment("lib.amqpyombo.sent.uncompressed", bucket_time=15, anon=True)

        return requestmsg

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
        self._local_log("info", "AMQPLibrary::amqp_incoming")

        time_info = self.amqp.send_correlation_ids[properties.correlation_id]
        daate_time = time_info['time_received'] - time_info['time_sent']
        milliseconds = (daate_time.days * 24 * 60 * 60 + daate_time.seconds) * 1000 + daate_time.microseconds / 1000.0
        logger.debug("Time between sending and receiving a response:: {milliseconds}", milliseconds=milliseconds)
        self._Statistics.averages("lib.amqpyombo.amqp.response.time", milliseconds, bucket_time=15, anon=True)

#        log.msg('%s (%s): %s' % (deliver.exchange, deliver.routing_key, repr(msg)), system='Pika:<=')

        self._local_log("debug", "PikaProtocol::receive_item3")
        # do nothing on requests for now.... in future if we ever accept requests, we will.
        if properties.headers['type'] == 'request':
            raise YomboWarning("Currently not accepting requests.")
        # if a response, lets make sure it's something we asked for!
        elif properties.headers['type'] == "response":
            if properties.correlation_id is None or not isinstance(properties.correlation_id, basestring):
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

        # do nothing on requests for now.... in future if we ever accept requests, we will.
        if properties.headers['type'] == 'Request':
            raise YomboWarning("Currently not accepting requests.")
        # if a response, lets make sure it's something we asked for!
        elif properties.headers['type'] == "Response":
            if properties.correlation_id not in self.amqp.send_correlation_ids:
                self._Statistics.increment("lib.amqpyombo.received.discarded.no_correlation_id", bucket_time=15, anon=True)
                raise YomboWarning("Received request %s, but never asked for it. Discarding" % properties.correlation_id)

        self._local_log("debug", "PikaProtocol::receive_item5")

        # if we are here.. we have a valid message....

        try:
            if properties.headers['type'] == 'response':
                if properties.headers['response_type'] == 'config':
                    print "333"
                    if properties.headers['config_item'] in self.config_items:
                        print "44"
                        config_item = self.config_items[properties.headers['config_item']]
                        library = self.loader.loadedLibraries[config_item['library']]
                        klass = getattr(library, config_item['function'])
                        if msg['data_type'] == 'object':
                            print "555 a"
                            new_data = {}
                            for key, value in msg['data_type'].iteritems(): # we must re-map AMQP names to local names.
                                if key in config_item['map']:
                                    new_data[config_item['map'][key]] = value
 #                           print "new_data: %s" % new_data
                            klass(new_data)
                            self.loader.loadedLibraries['devices'].add_update_delete(new_data)
                        else:
                            print "555 b"
                            for item in msg['data']:
                                print "6666 aa"
                                new_data = {}
                                print "6666 bb"
                                for key, value in item.iteritems(): # we must re-map AMQP names to local names.  Removes ones without a DB column too.
                                    if key in config_item['map']:
                                        # Convert ints and floats.
                                        if self._LocalDBLibrary.db_model[config_item['table']][config_item['map'][key]]['type'] == "INTEGER":
                                            value=int(value)
                                        elif self._LocalDBLibrary.db_model[config_item['table']][config_item['map'][key]]['type'] == "REAL":
                                            value=float(value)
                                        new_data[config_item['map'][key]] = value

                                print "6666 cc"
                                klass(new_data)
                        self._remove_full_download_dueue("get_" + properties.headers['config_item'])

        except Exception, e:
            print "I found a bad thing: %s" % e
#        print "valid to here: %s" % msg


    # # deprecated
    # def message(self, message):
    #     """
    #     Messages bound externally are routed here. This library doesn't subscribe to anything, so it must
    #     sepcifically be routed here by the message system or from another library/module.
    #
    #     Messages sent here will be converted to an AMQP message for delivery.
    #
    #     :param message: A Yombo Message to be routed externally
    #     :type message: Message
    #     """
    #     raise YomboWarning("message -> AMQP - Outgoing message routing not implmented")
    #
    #     if message.checkDestinationAsLocal() is False:
    #         raise YomboMessageError("Tried to send a local message externally. Dropping.")
    #     if message.validateMsgOriginFull() is False:
    #         raise YomboMessageError("Full msgOrigin needs full path.")
    #     if message.validateMsgDestinationFull() is False:
    #         raise YomboMessageError("Full msgDestination needs full path.")
    #
    #     request = {
    #           "DataType": "Object",
    #           "Request": message.dumpToExternal(),
    #         }
    #
    #     requestmsg = {
    #         "exchange_name"    : "gw_config",
    #         "routing_key"      : '*',
    #         "body"             : request,
    #         "properties" : {
    #             "correlation_id" : requestID,
    #             "user_id"        : self.gwuuid,
    #             "headers"        : {
    #                 "source"        : message.msgOrigin,
    #                 "destination"   : message.msgDestination,
    #                 "type"          : "Message",
    #                 },
    #             },
    #         "callback"          : None
    #         }


    def get_system_configs(self):
        self.__doing_full_configs = True
        self._full_download_start_time = time()
        self._getAllConfigsLoggerLoop = LoopingCall(self._show_pending_configs)
        self._getAllConfigsLoggerLoop.start(5, False)  # Display a log line for pending downloaded, false - Dont' show now

        logger.debug("request_system_configs.....")

        allCommands = [
            # "get_commands",
            # "get_device_types",
            "get_gateway_devices",
            # "get_gateway_modules", # includes Moduledevice_types, Commanddevice_types
            # "get_gateway_configs",

#            "GetModuleVariables",
#            "getGatewayUserTokens",
#            "getGatewayUsers",
        ]
#        cur_time = int(time())
        for item in allCommands:
            logger.debug("sending command: {item}", item=item)

           # request device updates
            body = {
                "since": self._Configs.get("amqpyombo_config_times", item, 0),
            }

#            self._Configs.set("amqpyombo_config_times", item, cur_time),

            requestmsg = self.generate_message_request(
                exchange_name='ysrv.e.gw_config',
                source='yombo.gateway.lib.configurationupdate',
                destination='yombo.server.configs',
                body=body,
                request_type=item,
            )
#            print requestmsg
            self.amqp.publish(**requestmsg)

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
        logger.info("Removing table from request queue: {table}", table=table)
        logger.info("Configs pending: {pendingUpdates}", pendingUpdates=self.__pending_updates)
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
        print "devices loaded %s"% self._DevicesLibrary._devicesByUUID

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
