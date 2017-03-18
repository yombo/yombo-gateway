# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This library is responsible for handling configuration and controll messages with the Yombo servers. It requests
configurations and directs them to the configuration handler. It also directs any control messages to the control
handler.

This library utilizes the amqp library to handle the low level handling.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

This connection should be maintained 100% of the time. This allows control messages to be recieved by your devices
or 3rd party sources such as Amazon Alexa, Google Home, etc etc.

:TODO: The gateway needs to check for a non-responsive server or if it doesn't get a response in a timely manor.
Perhaps disconnect and reconnect to another server? -Mitch

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2015-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/amqpyombo.py>`_
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
from twisted.internet.task import LoopingCall

# Import 3rd party extensions
import yombo.ext.six as six

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboCritical
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import percentage, random_string
import yombo.ext.umsgpack as msgpack

# Handlers for processing various messages.
from yombo.lib.handlers.amqpcontrol import AmqpControlHandler
from yombo.lib.handlers.amqpconfigs import AmqpConfigHandler

logger = get_logger('library.amqpyombo')

PROTOCOL_VERSION = 3    # Which version of the yombo protocol we have implemented.
PREFETCH_COUNT = 5      # Determine how many messages should be received/inflight before yombo servers
                        # stop sending us messages. Should ACK/NACK all messages quickly.


class AMQPYombo(YomboLibrary):
    """
    Handles interactions with Yombo servers through the AMQP library.
    """

    def _init_(self):
        """
        Loads various variables and calls :py:meth:connect() when it's ready.

        :return:
        """
        self.user_id = "gw_" + self._Configs.get("core", "gwid")
        self.login_user_id = self.user_id + "_" + self._Configs.get("core", "gwuuid")
        self.__pending_updates = []  # Holds a list of configuration items we've asked for, but not response yet.
        self._LocalDBLibrary = self._Libraries['localdb']
        self.init_startup_count = 0

        self.amqp = None  # holds our pointer for out amqp connection.
        self._getAllConfigsLoggerLoop = None

        self._getAllConfigsLoggerLoop = None
        self.reconnect = True  # If we get disconnected, we should reconnect to the server.
        self.sendLocalInformationLoop = None  # used to periodically send yombo servers updated information

        self.controlHandler = AmqpControlHandler(self)
        self.configHandler = AmqpConfigHandler(self)

        self._States.set('amqp.amqpyombo.state', False)
        return self.connect()

    def _stop_(self):
        """
        Called by the Yombo system when it's time to shutdown. This in turn calls the disconnect.
        :return:
        """
        self.configHandler._stop_()
        self.controlHandler._stop_()
        self.disconnect()  # will be cleaned up by amqp library anyways, but it's good to be nice.

    def connect(self):
        """
        Connect to Yombo AMQP server.

        :return:
        """
        already_have_amqp = self.amqp
        environment = self._Configs.get('server', 'environment', "production", False)
        if self._Configs.get("amqpyombo", 'hostname', "", False) != "":
            amqp_host = self._Configs.get("amqpyombo", 'hostname')
            amqp_port = self._Configs.get("amqpyombo", 'port', 5671, False)
        else:
            amqp_port = 5671
            if environment == "production":
                amqp_host = "amqp.yombo.net"
            elif environment == "staging":
                amqp_host = "amqpstg.yombo.net"
            elif environment == "development":
                amqp_host = "amqpdev.yombo.net"
            else:
                amqp_host = "amqp.yombo.net"

        # get a new AMPQ instance and connect.
        if self.amqp is None:
            self.amqp = self._AMQP.new(hostname=amqp_host, port=amqp_port, virtual_host='yombo', username=self.login_user_id,
                password=self._Configs.get("core", "gwhash"), client_id='amqpyombo',
                connected_callback=self.amqp_connected, disconnected_callback=self.amqp_disconnected)
        self.amqp.connect()

        # The servers will have a dedicated queue for us. All pending messages will be held there for us. If we
        # connect to a different server, they wil automagically be re-routed to our new queue.
        if already_have_amqp is None:
            self.amqp.subscribe("ygw.q." + self.user_id, incoming_callback=self.amqp_incoming, queue_no_ack=False, persistent=True)

        return self.configHandler.connect_setup()

    def disconnect(self):
        """
        Called by the yombo system when it's
        :return:
        """
        body = {
        }

        requestmsg = self.generate_message_request(
            exchange_name='ysrv.e.gw_config',
            source='yombo.gateway.lib.amqpyombo',
            destination='yombo.server.configs',
            body=body,
            headers={
                "request_type": "disconnecting",
            }
        )
        self.amqp.publish(**requestmsg)

        self.reconnect = False
        logger.debug("Disconnected from Yombo message server.")

    def amqp_connected(self):
        """
        Called by AQMP when connected. This function was define above when setting up self.ampq.

        :return:
        """
        return self.configHandler.connected()
        logger.warn("amqp yombo connected")
        self.sendLocalInformationLoop = LoopingCall(self.sendLocalInformation)
        self.sendLocalInformationLoop.start(60*60*4)  # Sends various information, helps Yombo cloud know we are alive and where to find us.

        self._States.set('amqp.amqpyombo.state', True)

    def amqp_disconnected(self):
        """
        Called by AQMP when disconnected.
        :return:
        """
        if self._States.get('amqp.amqpyombo.state') == 0:
            logger.error("Unable to connect. This may be due to multiple connections or bad gateway hash. See: http://g2.yombo.net/noconnect")
            raise YomboCritical('Yombo is unable to connect to server.', 500, "amqpyombo", "connect")

        logger.warn("amqp yombo disconnected: {state}", state=self._States.get('amqp.amqpyombo.state'))
        self._States.set('amqp.amqpyombo.state', False)
        if self.sendLocalInformationLoop is not None and self.sendLocalInformationLoop.running:
            self.sendLocalInformationLoop.stop()

        if self.reconnect is True:
            self.connect()

    def sendLocalInformation(self):
        """
        Say hello, send some information about us. What we use these IP addresses for:

        Devices in your home can connect directly to the gateway for faster access. We give this information
        to your clients so they can find the gateway easier/faster.

        Your external IP is also given to your clients so they can attempt to connect directly to the gateway when
        you are not at home.

        If either of these conenctions are not available, applications can use the Yombo servers as proxy and will
        be delivered here as either a control or status request message.

        :return:
        """
        body = {
            "internal_ipv4": self._Configs.get("core", "localipaddress_v4"),
            "external_ipv4": self._Configs.get("core", "externalipaddress_v4"),
            "internal_port": self._Configs.get("webinterface", "nonsecure_port"),
            "external_port": self._Configs.get("webinterface", "nonsecure_port"),
            "internal_secure_port": self._Configs.get("webinterface", "secure_port"),
            "external_secure_port": self._Configs.get("webinterface", "secure_port"),
        }

        requestmsg = self.generate_message_request(
            exchange_name='ysrv.e.gw_config',
            source='yombo.gateway.lib.amqpyombo',
            destination='yombo.server.configs',
            body=body,
            callback=self.receive_local_information,
            headers={
                "request_type": "gatewayInfo",
            }
        )
        requestmsg['properties']['headers']['response_type']='system'
        self.amqp.publish(**requestmsg)

    def receive_local_information(self, deliver, props, msg, queue):
        # print "########################################################### receive_local_information"
        pass

    def generate_message_response(self, properties, exchange_name, source, destination, headers, body ):
        response_msg = self.generate_message(exchange_name, source, destination, "response", headers, body)
        if properties.correlation_id:
           response_msg['properties']['correlation_id'] = properties.correlation_id
#        response_msg['properties']['headers']['response_type']=response_type
        correlation_id = random_string(length=12)

        # print "properties: %s" % properties
        if 'route' in properties.headers:
            route = str(properties.headers['route']) + ",yombo.gw.amqpyombo:" + self.user_id
            response_msg['properties']['headers']['route'] = route
        else:
            response_msg['properties']['headers']['route'] = "yombo.gw.amqpyombo:" + self.user_id
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

    def publish(self, message):
        """
        Publishes a message. Use generate_message(), generate_message_request, or generate_message_response to
        create the message.
        :param message:
        :return:
        """
        self.amqp.publish(**message)

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
        # self._local_log("info", "AMQPLibrary::amqp_incoming")
        # print " !!!!!!!!!!!!!!!!!!!!!!!!! "
        # print "properties: %s" % properties
#        log.msg('%s (%s): %s' % (deliver.exchange, deliver.routing_key, repr(msg)), system='Pika:<=')

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

        if properties.headers['type'] == 'request':
            self._Statistics.increment("lib.amqpyombo.received.request", bucket_time=15, anon=True)

        # if a response, lets make sure it's something we asked for!
        elif properties.headers['type'] == "response":
            # print "send_correlation_ids: %s" % self.amqp.send_correlation_ids
            if properties.correlation_id not in self.amqp.send_correlation_ids:
                self._Statistics.increment("lib.amqpyombo.received.discarded.correlation_id_missing", bucket_time=15,
                                           anon=True)
                raise YomboWarning("correlation_id missing.")

            time_info = self.amqp.send_correlation_ids[properties.correlation_id]
            daate_time = time_info['time_received'] - time_info['time_sent']
            milliseconds = (
                           daate_time.days * 24 * 60 * 60 + daate_time.seconds) * 1000 + daate_time.microseconds / 1000.0
            logger.debug("Time between sending and receiving a response:: {milliseconds}", milliseconds=milliseconds)
            self._Statistics.averages("lib.amqpyombo.amqp.response.time", milliseconds, bucket_time=15, anon=True)

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

        # self._local_log("debug", "PikaProtocol::receive_item4")

        # if we are here.. we have a valid message....

        if properties.headers['type'] == 'request':
            try:
                logger.debug("headers: {headers}", headers=properties.headers)
                if properties.headers['request_type'] == 'control':
                    self.controlHandler.process_control(msg, properties)
                elif properties.headers['request_type'] == 'system':
                    self.process_system_request(msg, properties)

            except Exception, e:
                logger.error("--------==(Error: in response processing     )==--------")
                logger.error("--------------------------------------------------------")
                logger.error("{error}", error=sys.exc_info())
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
                logger.error("--------------------------------------------------------")
        elif properties.headers['type'] == 'response':
            try:
                logger.debug("headers: {headers}", headers=properties.headers)
                if properties.headers['response_type'] == 'config':
                    self.configHandler.process_config_response(msg, properties)

            except Exception, e:
                logger.error("--------==(Error: in response processing     )==--------")
                logger.error("--------------------------------------------------------")
                logger.error("{error}", error=sys.exc_info())
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
                logger.error("--------------------------------------------------------")

    def process_system(self, msg, properties):
        pass

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
