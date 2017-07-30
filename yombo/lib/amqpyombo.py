# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This library is responsible for handling configuration and control messages with the Yombo servers. It requests
configurations and directs them to the configuration handler. It also directs any control messages to the control
handler.

This library utilizes the amqp library to handle the low level handling.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

This connection should be maintained 100% of the time. This allows control messages to be received by your devices
or 3rd party sources such as Amazon Alexa, Google Home, etc etc.

.. todo:: The gateway needs to check for a non-responsive server or if it doesn't get a response in a timely manor.
   Perhaps disconnect and reconnect to another server? -Mitch

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

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
import collections
import msgpack
import six
import sys
from time import time
import traceback

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, Deferred

# Import 3rd party extensions

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import percentage, random_string, random_int, bytes_to_unicode

# Handlers for processing various messages.
from yombo.lib.handlers.amqpcontrol import AmqpControlHandler
from yombo.lib.handlers.amqpconfigs import AmqpConfigHandler

logger = get_logger('library.amqpyombo')

PROTOCOL_VERSION = 4  # Which version of the yombo protocol we have implemented.
PREFETCH_COUNT = 5  # Determine how many messages should be received/inflight before yombo servers


class AMQPYombo(YomboLibrary):
    """
    Handles interactions with Yombo servers through the AMQP library.
    """

    def _init_(self, **kwargs):
        """
        Loads various variables and calls :py:meth:connect() when it's ready.

        :return:
        """
        self.gateway_id = "gw_" + self._Configs.get('core', 'gwid', 'local', False)
        self.login_gwuuid = self.gateway_id + "_" + self._Configs.get("core", "gwuuid")
        self._LocalDBLibrary = self._Libraries['localdb']
        self.request_configs = False

        self.amqp = None  # holds our pointer for out amqp connection.
        self._getAllConfigsLoggerLoop = None
        self.send_local_information_loop = None  # used to periodically send yombo servers updated information

        self.controlHandler = AmqpControlHandler(self)
        self.configHandler = AmqpConfigHandler(self)

        self._States.set('amqp.amqpyombo.state', False)
        self.init_deferred = Deferred()
        self.connect()
        return self.init_deferred

    def _stop_(self, **kwargs):
        """
        Called by the Yombo system when it's time to shutdown. This in turn calls the disconnect.
        :return:
        """

        if self.init_deferred is not None and self.init_deferred.called is False:
            self.init_deferred.callback(1)  # if we don't check for this, we can't stop!

        self.configHandler._stop_()
        self.controlHandler._stop_()
        self.disconnect()  # will be cleaned up by amqp library anyways, but it's good to be nice.

    def _unload_(self, **kwargs):
        self.amqp.disconnect()

    @inlineCallbacks
    def connect(self):
        """
        Connect to Yombo amqp server.

        :return:
        """
        if self.amqp is None:
            already_have_amqp = None
        else:
            already_have_amqp = True

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

        # get a new amqp instance and connect.
        if self.amqp is None:
            self.amqp = yield self._AMQP.new(hostname=amqp_host,
                                             port=amqp_port,
                                             virtual_host='yombo',
                                             username=self.login_gwuuid,
                                             password=self._Configs.get("core", "gwhash"),
                                             client_id='amqpyombo',
                                             prefetch_count=PREFETCH_COUNT,
                                             connected_callback=self.amqp_connected,
                                             disconnected_callback=self.amqp_disconnected,
                                             critical=True)
        self.amqp.connect()

        # The servers will have a dedicated queue for us. All pending messages will be held there for us. If we
        # connect to a different server, they wil automagically be re-routed to our new queue.
        if already_have_amqp is None:
            self.amqp.subscribe("ygw.q." + self.gateway_id, incoming_callback=self.amqp_incoming, queue_no_ack=False,
                                persistent=True)

        self.configHandler.connect_setup(self.init_deferred)
        # self.init_deferred.callback(10)

    def disconnect(self):
        """
        Called by the yombo system when it's time to shutdown.

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

        logger.debug("Disconnected from Yombo message server.")

    def amqp_connected(self):
        """
        Called by AQMP when connected. This function was define above when setting up self.ampq.

        :return:
        """
        self._States.set('amqp.amqpyombo.state', True)

        if self.send_local_information_loop is None:
            self.send_local_information_loop = LoopingCall(self.send_local_information)

        # Sends various information, helps Yombo cloud know we are alive and where to find us.
        if self.send_local_information_loop.running is False:
            self.send_local_information_loop.start(random_int(60 * 60 * 4,.2))

    def amqp_disconnected(self):
        """
        Called by AQMP when disconnected.
        :return:
        """
        # logger.info("amqpyombo yombo disconnected: {state}", state=self._States.get('amqp.amqpyombo.state'))
        # If we have at least connected once, then we don't toss errors.  We just wait for reconnection...

        if self._States.get('amqp.amqpyombo.state') is False:
            logger.error(
                "Unable to connect. This may be due to multiple connections or bad gateway hash. See: http://g2.yombo.net/noconnect")
            self._Loader.sigint = True
            self.amqp.disconnect()
            reactor.stop()
            return

        self._States.set('amqp.amqpyombo.state', False)
        if self.send_local_information_loop is not None and self.send_local_information_loop.running:
            self.send_local_information_loop.stop()

    def send_local_information(self):
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
            "is_master": self._Configs.get("core", "is_master", True, False),
            "master_gateway": self._Configs.get("core", "master_gateway", "", False),
            "internal_ipv4": self._Configs.get("core", "localipaddress_v4"),
            "external_ipv4": self._Configs.get("core", "externalipaddress_v4"),
            # "internal_ipv6": self._Configs.get("core", "externalipaddress_v6"),
            # "external_ipv6": self._Configs.get("core", "externalipaddress_v6"),
            "internal_port": self._Configs.get("webinterface", "nonsecure_port"),
            "external_port": self._Configs.get("webinterface", "nonsecure_port"),
            "internal_secure_port": self._Configs.get("webinterface", "secure_port"),
            "external_secure_port": self._Configs.get("webinterface", "secure_port"),
            "internal_mqtt": self._Configs.get("mqtt", "server_listen_port"),
            "internal_mqtt_le": self._Configs.get("mqtt", "server_listen_port_le_ssl"),
            "internal_mqtt_ss": self._Configs.get("mqtt", "server_listen_port_ss_ssl"),
            "internal_mqtt_ws": self._Configs.get("mqtt", "server_listen_port_websockets"),
            "internal_mqtt_ws_le": self._Configs.get("mqtt", "server_listen_port_websockets_le_ssl"),
            "internal_mqtt_ws_ss": self._Configs.get("mqtt", "server_listen_port_websockets_ss_ssl"),
            "external_mqtt": self._Configs.get("mqtt", "server_listen_port"),
            "external_mqtt_le": self._Configs.get("mqtt", "server_listen_port_le_ssl"),
            "external_mqtt_ss": self._Configs.get("mqtt", "server_listen_port_ss_ssl"),
            "external_mqtt_ws": self._Configs.get("mqtt", "server_listen_port_websockets"),
            "external_mqtt_ws_le": self._Configs.get("mqtt", "server_listen_port_websockets_le_ssl"),
            "external_mqtt_ws_ss": self._Configs.get("mqtt", "server_listen_port_websockets_ss_ssl"),
        }

        # logger.debug("sending local information.")

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
        requestmsg['properties']['headers']['response_type'] = 'system'
        self.amqp.publish(**requestmsg)

    def receive_local_information(self, msg=None, properties=None, correlation_info=None,
                                  send_message_info=None, receied_message_info=None, **kwargs):
        if self.request_configs is False:  # this is where we start requesting information - after we have sent out info.
            self.request_configs = True
            return self.configHandler.connected()

    def generate_message_response(self, properties, exchange_name, source, destination, headers, body):
        response_msg = self.generate_message(exchange_name, source, destination, "response", headers, body)

        if hasattr('correlation_id', properties) and properties.correlation_id is not None:
            response_msg['properties']['correlation_id'] = properties.correlation_id
        if hasattr('message_id', properties) and properties.message_id is not None and \
                properties.message_id[0:2] != "xx_":
            response_msg['properties']['reply_to'] = properties.correlation_id

        # print "properties: %s" % properties
        if 'route' in properties.headers:
            route = str(properties.headers['route']) + ",yombo.gw.amqpyombo:" + self.gateway_id
            response_msg['properties']['headers']['route'] = route
        else:
            response_msg['properties']['headers']['route'] = "yombo.gw.amqpyombo:" + self.gateway_id
        return response_msg

    def generate_message_request(self, exchange_name=None, source=None, destination=None,
                                 headers=None, body=None, callback=None, correlation_id=None, message_id=None):
        new_body = {
            "data_type": "object",
            "request": body,
        }
        if isinstance(body, list):
            new_body['data_type'] = 'objects'

        request_msg = self.generate_message(exchange_name, source, destination, "request",
                                            headers, new_body, callback=callback, correlation_id=correlation_id,
                                            message_id=message_id)
        return request_msg

    def generate_message(self, exchange_name, source, destination, header_type, headers, body, callback=None,
                         correlation_id=None, message_id=None):
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
        :param header_type: Type of header. Usually one of: request, response
        :type header_type: str
        :param headers: Extra headers
        :type headers: dict
        :param body: The part that will become the body, or payload, of the message.
        :type body: str, dict, list
        :param callback: A pointer to the function to return results to. This function will receive 4 arguments:
          sendInfo (Dict) - Various details of the sent packet. deliver (Dict) - Deliver fields as returned by Pika.
          props (Pika Object) - Message properties, includes headers. msg (dict) - The actual content of the message.
        :type callback: function
        :param body: The body contents for the mesage.
        :type body: dict

        :return: A dictionary that can be directly returned to Yombo Gateways via AMQP
        :rtype: dict
        """
        # print("body: %s" % body)
        request_msg = {
            "exchange_name": exchange_name,
            "routing_key": '*',
            "body": msgpack.dumps(body),
            "properties": {
                # "correlation_id" : correlation_id,
                "user_id": self.gateway_id,  # system id is required to be able to send it.
                "content_type": 'application/msgpack',
                "headers": {
                    # "requesting_user_id"        : user
                    "source": source + ":" + self.gateway_id,
                    "destination": destination,
                    "type": header_type,
                    "protocol_verion": PROTOCOL_VERSION,
                    "message_id": random_string(length=20),
                    "msg_created_time": str(time()),
                },
            },
            "meta": {
                "content_type": 'application/msgpack',
            },
            "created_time": time(),
        }

        if "callback" is not None:
            request_msg['callback'] = callback
            if correlation_id is None:
                request_msg['properties']['correlation_id'] = random_string(length=24)
            else:
                request_msg['properties']['correlation_id'] = correlation_id

        if message_id is None:
            request_msg['properties']['message_id'] = random_string(length=26)
        else:
            request_msg['properties']['message_id'] = message_id

        # Lets test if we can compress. Set headers as needed.
        if len(request_msg['body']) > 800:
            beforeZlib = len(request_msg['body'])
            request_msg['body'] = zlib.compress(request_msg['body'], 5)  # 5 appears to be the best speed/compression ratio - MSchwenk
            afterZlib = len(request_msg['body'])
            request_msg['meta']['compression_percent'] = percentage(afterZlib, beforeZlib)

            request_msg['properties']['content_encoding'] = "zlib"
        else:
            request_msg['properties']['content_encoding'] = 'text'
        request_msg['properties']['headers'].update(headers)
        request_msg['meta']['content_encoding'] = request_msg['properties']['content_encoding']
        request_msg['meta']['payload_size'] = len(request_msg['body'])
        return request_msg

    def publish(self, **kwargs):
        """
        Publishes a message. Use generate_message(), generate_message_request, or generate_message_response to
        create the message.
        :return:
        """
        if 'callback' in kwargs:
            callback = kwargs['callback']
            del kwargs['callback']
            if 'correlation_id' not in kwargs['properties']:
                kwargs['properties']['correlation_id'] = random_string()
        else:
            callback = None

        # print "publish kwargs: %s" % kwargs
        results = self.amqp.publish(**kwargs)
        if results['correlation_info'] is not None:
            results['correlation_info']['amqpyombo_callback'] = callback

    def amqp_incoming(self, msg=None, properties=None, deliver=None, correlation_info=None,
                      received_message_info=None, sent_message_info=None, **kwargs):
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
        # print "properties: %s" % properties
        # print "correlation: %s" % correlation

        #        log.msg('%s (%s): %s' % (deliver.exchange, deliver.routing_key, repr(msg)), system='Pika:<=')

        msg_meta = {}
        if properties.user_id is None:
            self._Statistics.increment("lib.amqpyombo.received.discarded.nouserid", bucket_size=15, anon=True)
            raise YomboWarning("user_id missing.")
        if properties.content_type is None:
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_type_missing", bucket_size=15,
                                       anon=True)
            raise YomboWarning("content_type missing.")
        if properties.content_encoding is None:
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_encoding_missing", bucket_size=15,
                                       anon=True)
            raise YomboWarning("content_encoding missing.")
        if properties.content_encoding != 'text' and properties.content_encoding != 'zlib':
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_encoding_invalid", bucket_size=15,
                                       anon=True)
            raise YomboWarning("Content Encoding must be either  'text' or 'zlib'. Got: " + properties.content_encoding)
        if properties.content_type != 'text/plain' and properties.content_type != 'application/msgpack' and properties.content_type != 'application/json':
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_type_invalid", bucket_size=15,
                                       anon=True)
            logger.warn('Error with contentType!')
            raise YomboWarning(
                "Content type must be 'application/msgpack', 'application/json' or 'text/plain'. Got: " + properties.content_type)

        msg_meta['payload_size'] = len(msg)
        if properties.content_encoding == 'zlib':
            compressed_size = len(msg)
            msg = zlib.decompress(msg)
            uncompressed_size = len(msg)
            # logger.info(
            #     "Message sizes: msg_size_compressed = {compressed}, non-compressed = {uncompressed}, percent: {percent}",
            #     compressed=beforeZlib, uncompressed=afterZlib, percent=abs(percentage(beforeZlib, afterZlib)-1))
            received_message_info['uncompressed_size'] = uncompressed_size
            received_message_info['compression_percent'] = abs((compressed_size / uncompressed_size) - 1)*100


        if properties.content_type == 'application/json':
            try:
                msg = bytes_to_unicode(json.loads(msg))
            except Exception:
                raise YomboWarning("Receive msg reported json, but isn't: %s" % msg)
        elif properties.content_type == 'application/msgpack':
            try:
                msg = bytes_to_unicode(msgpack.loads(msg))
            except Exception:
                raise YomboWarning("Received msg reported msgpack, but isn't: %s" % msg)

        # if a response, lets make sure it's something we asked for!
        elif properties.headers['type'] == "response":
            # print "send_correlation_ids: %s" % self.amqp.send_correlation_ids
            if properties.correlation_id not in self.amqp.send_correlation_ids:
                self._Statistics.increment("lib.amqpyombo.received.discarded.correlation_id_missing", bucket_size=15,
                                           anon=True)
                raise YomboWarning("correlation_id missing.")

            if sent_message_info is not None and sent_message_info['sent_time'] is not None:
                delay_date_time = received_message_info['received_time'] - sent_message_info['sent_time']
                milliseconds = (delay_date_time.days * 24 * 60 * 60 + delay_date_time.seconds) * 1000 + delay_date_time.microseconds / 1000.0
                logger.debug("Time between sending and receiving a response:: {milliseconds}", milliseconds=milliseconds)
                received_message_info['round_trip_timing'] = milliseconds

            if properties.correlation_id is None or not isinstance(properties.correlation_id, six.string_types):
                self._Statistics.increment("lib.amqpyombo.received.discarded.correlation_id_invalid", bucket_size=15,
                                           anon=True)
                raise YomboWarning("Correlation_id must be present for 'Response' types, and must be a string.")
            if properties.correlation_id not in self.amqp.send_correlation_ids:
                logger.debug("{correlation_id} not in list of ids: {send_correlation_ids} ",
                             correlation_id=properties.correlation_id,
                             send_correlation_ids=list(self.amqp.send_correlation_ids.keys()))
                self._Statistics.increment("lib.amqpyombo.received.discarded.nocorrelation", bucket_size=15, anon=True)
                raise YomboWarning("Received request %s, but never asked for it. Discarding" % properties.correlation_id)
        else:
            self._Statistics.increment("lib.amqpyombo.received.discarded.unknown_msg_type", bucket_size=15, anon=True)
            raise YomboWarning("Unknown message type received.")

        # self._local_log("debug", "PikaProtocol::receive_item4")

        # if we are here.. we have a valid message....
        if correlation_info is not None and 'amqpyombo_callback' in correlation_info and \
                correlation_info['amqpyombo_callback'] and isinstance(correlation_info['amqpyombo_callback'], collections.Callable):
            correlation_info['amqpyombo_callback'](msg=msg, properties=properties, deliver=deliver,
                                                   correlation_info=correlation_info, **kwargs)
        received_message_info['meta'] = msg_meta

        if properties.headers['type'] == 'request':
            try:
                logger.debug("headers: {headers}", headers=properties.headers)
                if properties.headers['request_type'] == 'control':
                    self.controlHandler.process_control(msg, properties)
                elif properties.headers['request_type'] == 'system':
                    self.process_system_request(msg=msg, properties=properties, deliver=deliver,
                                                correlation_info=correlation_info, sent_message_info=sent_message_info,
                                                received_message_info=received_message_info, **kwargs)

            except Exception as e:
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
                    self.configHandler.process_config_response(msg=msg, properties=properties, deliver=deliver,
                                                               correlation_info=correlation_info,
                                                               sent_message_info=sent_message_info,
                                                               received_message_info=received_message_info, **kwargs)
                elif properties.headers['response_type'] == 'sslcert':
                    self._SSLCerts.amqp_incoming(msg=msg, properties=properties, deliver=deliver,
                                                 correlation_info=correlation_info, sent_message_info=sent_message_info,
                                                 received_message_info=received_message_info, **kwargs)

            except Exception as e:
                logger.error("--------==(Error: in response processing     )==--------")
                logger.error("--------------------------------------------------------")
                logger.error("{error}", error=sys.exc_info())
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
                logger.error("--------------------------------------------------------")

    def process_system(self, msg, properties):
        pass

    def _local_log(self, level, location, msg=""):
        logit = func = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)
