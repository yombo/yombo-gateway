# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This library is responsible for handling configuration and control messages with the Yombo servers. It requests
configurations and directs them to the configuration handler. It also directs any control messages to the control
handler.

This library utilizes the amqp library to handle the low level handling.

This connection should be maintained 100% of the time. This allows control messages to be received by your devices
or 3rd party sources such as Amazon Alexa, Google Home, etc etc.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. note::

  For developer documentation, see: `AMQPYombo @ Module Development <https://yombo.net/docs/libraries/amqpyombo>`_

.. todo:: The gateway needs to check for a non-responsive server or if it doesn't get a response in a timely manor.
   Perhaps disconnect and reconnect to another server? -Mitch

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2015-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/amqpyombo.html>`_
"""

# Import python libraries

try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
import zlib
import collections
import msgpack
from time import time

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, Deferred, maybeDeferred

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import percentage, random_string, random_int, bytes_to_unicode, global_invoke_all
from yombo.constants import CONTENT_TYPE_JSON, CONTENT_TYPE_MSGPACK, CONTENT_TYPE_TEXT_PLAIN

# Handlers for processing various messages.
from yombo.lib.amqpyomb_handlers.amqpcontrol import AmqpControlHandler
from yombo.lib.amqpyomb_handlers.amqpconfigs import AmqpConfigHandler
from yombo.lib.amqpyomb_handlers.amqpsystem import AmqpSystemHandler

logger = get_logger('library.amqpyombo')

PROTOCOL_VERSION = 5  # Which version of the yombo protocol we have implemented.
PREFETCH_COUNT = 5  # Determine how many messages should be received/inflight before yombo servers


class AMQPYombo(YomboLibrary):
    """
    Handles interactions with Yombo servers through the AMQP library.
    """
    @property
    def connected(self):
        return self._States.get('amqp.amqpyombo.state', None)

    @connected.setter
    def connected(self, val):
        return self._States.set('amqp.amqpyombo.state', val)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo amqp yombo library"

    def _init_(self, **kwargs):
        """
        Loads various variables and calls :py:meth:connect() when it's ready.

        :return:
        """
        self.user_id = "gw_" + self._Configs.get('core', 'gwid', 'local', False)
        self.login_gwuuid = self.user_id + "_" + self._Configs.get("core", "gwuuid")
        self.request_configs = False
        self.controlHandler = AmqpControlHandler(self)
        self.configHandler = AmqpConfigHandler(self)
        self.systemHandler = AmqpSystemHandler(self)
        self.gateway_id = self._Configs.get2('core', 'gwid', 'local', False)

        self.amqpyombo_options = {   # Stores data from sub-modules
            'connected': [],
            'disconnected': [self.configHandler.disconnected, ],
            'routing': {
                'config': [self.configHandler.amqp_incoming, ],
                'control': [self.controlHandler.amqp_incoming, ],
                'system': [self.systemHandler.amqp_incoming, ],
                'sslcerts': [self._SSLCerts.amqp_incoming, ],
            },
        }

        self.amqp = None  # holds our pointer for out amqp connection.
        self._getAllConfigsLoggerLoop = None
        self.send_local_information_loop = None  # used to periodically send yombo servers updated information

        self.connected = False
        self.init_deferred = Deferred()
        self.connect()
        return self.init_deferred

    @inlineCallbacks
    def _load_(self, **kwargs):
        # print("################# about to process_amqpyombo_options")
        results = yield global_invoke_all('_amqpyombo_options_', called_by=self)
        for component_name, data in results.items():
            if 'connected' in data:
                self.amqpyombo_options['connected'].append(data['connected'])
            if 'disconnected' in data:
                self.amqpyombo_options['disconnected'].append(data['disconnected'])
            if 'routing' in data:
                for key, the_callback in data['gateway_routing'].items():
                    if key not in self.amqpyombo_options['gateway_routing']:
                        self.amqpyombo_options['gateway_routing'][key] = []
                    self.amqpyombo_options['gateway_routing'][key].append(the_callback)

    def _stop_(self, **kwargs):
        """
        Called by the Yombo system when it's time to shutdown. This in turn calls the disconnect.
        :return:
        """

        if self.init_deferred is not None and self.init_deferred.called is False:
            self.init_deferred.callback(1)  # if we don't check for this, we can't stop!

        self.configHandler._stop_()
        self.controlHandler._stop_()
        self.systemHandler._stop_()
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
            self.amqp.subscribe("ygw.q." + self.user_id, incoming_callback=self.amqp_incoming, queue_no_ack=False,
                                persistent=True)

        # print("in amqp:connect - setting init_deffered")
        self.configHandler.connect_setup(self.init_deferred)

    def disconnect(self):
        """
        Called by the yombo system when it's time to shutdown.

        :return:
        """
        if self._Loader.operating_mode != 'run':
            return
        requestmsg = self.generate_message_request(
            exchange_name='ysrv.e.gw_system',
            source='yombo.gateway.lib.amqpyombo',
            destination='yombo.server.gw_system',
            request_type="disconnect",
            headers={'request_type': 'disconnect,'},
        )

        self.publish(**requestmsg)

        logger.debug("Disconnected from Yombo message server.")

    def amqp_connected(self):
        """
        Called by AQMP when connected. This function was define above when setting up self.ampq.

        :return:
        """
        self.connected = True
        for the_callback in self.amqpyombo_options['connected']:
            the_callback()

        if self.send_local_information_loop is None:
            self.send_local_information_loop = LoopingCall(self.send_local_information)

        # Sends various information, helps Yombo cloud know we are alive and where to find us.
        if self.send_local_information_loop.running is False:
            self.send_local_information_loop.start(random_int(60 * 60 * 4, .2))

    def amqp_disconnected(self):
        """
        Called by AQMP when disconnected.
        :return:
        """
        # logger.info("amqpyombo yombo disconnected: {state}", state=self._States.get('amqp.amqpyombo.state'))
        # If we have at least connected once, then we don't toss errors.  We just wait for reconnection...

        if self.connected is False:
            logger.error(
                "Unable to connect. This may be due to multiple connections or bad gateway hash. See: http://g2.yombo.net/noconnect")
            self._Loader.sigint = True
            self.amqp.disconnect()
            reactor.stop()
            return

        self.connected = False
        for the_callback in self.amqpyombo_options['disconnected']:
            the_callback()
        if self.send_local_information_loop is not None and self.send_local_information_loop.running:
            self.send_local_information_loop.stop()

    def send_local_information(self, full=False):
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
        if full is True:
            body['is_master'] = self._Configs.get("core", "is_master")
            body['master_gateway'] = self._Configs.get("core", "master_gateway")

            # logger.info("sending local information: {body}", body=body)

        requestmsg = self.generate_message_request(
            exchange_name='ysrv.e.gw_system',
            source='yombo.gateway.lib.amqpyombo',
            destination='yombo.server.gw_system',
            body=body,
            request_type="connected",
            callback=self.receive_local_information,
        )
        self.publish(**requestmsg)

    def receive_local_information(self, body=None, properties=None, correlation_info=None,
                                  send_message_meta=None, receied_message_meta=None, **kwargs):
        if self.request_configs is False:  # this is where we start requesting information - after we have sent out info.
            self.request_configs = True
            if 'owner_id' in body:
                self._Configs.set("core", "owner_id", body['owner_id'])

            return self.configHandler.connected()

    def amqp_incoming_parse(self, channel, deliver, properties, msg):
        """
        :param deliver:
        :param properties:
        :param msg:
        :param queue:
        :return:
        """
        # print("amqp_incoming_parse............")

        if not hasattr(properties, 'user_id') or properties.user_id is None:
            self._Statistics.increment("lib.amqpyombo.received.discarded.nouserid", bucket_size=15, anon=True)
            raise YomboWarning("user_id missing.")
        if not hasattr(properties, 'content_type') or properties.content_type is None:
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_type_missing", bucket_size=15,
                                       anon=True)
            raise YomboWarning("content_type missing.")
        if not hasattr(properties, 'content_encoding') or properties.content_encoding is None:
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_encoding_missing", bucket_size=15,
                                       anon=True)
            raise YomboWarning("content_encoding missing.")
        if properties.content_encoding != 'text' and properties.content_encoding != 'zlib':
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_encoding_invalid", bucket_size=15,
                                       anon=True)
            raise YomboWarning("Content Encoding must be either  'text' or 'zlib'. Got: " + properties.content_encoding)
        if properties.content_type != CONTENT_TYPE_TEXT_PLAIN and properties.content_type != CONTENT_TYPE_MSGPACK and properties.content_type != CONTENT_TYPE_JSON:
            self._Statistics.increment("lib.amqpyombo.received.discarded.content_type_invalid", bucket_size=15,
                                       anon=True)
            logger.warn('Error with contentType!')
            raise YomboWarning(
                "Content type must be 'application/msgpack', 'application/json' or 'text/plain'. Got: " + properties.content_type)

        received_message_meta = {}
        received_message_meta['content_encoding'] = properties.content_encoding
        received_message_meta['content_type'] = properties.content_type
        if properties.content_encoding == 'zlib':
            compressed_size = len(msg)
            msg = zlib.decompress(msg)
            uncompressed_size = len(msg)
            # logger.info(
            #     "Message sizes: msg_size_compressed = {compressed}, non-compressed = {uncompressed}, percent: {percent}",
            #     compressed=beforeZlib, uncompressed=afterZlib, percent=abs(percentage(beforeZlib, afterZlib)-1))
            received_message_meta['payload_size'] = uncompressed_size
            received_message_meta['compressed_size'] = compressed_size
            received_message_meta['compression_percent'] = abs((compressed_size / uncompressed_size) - 1)*100
        else:
            received_message_meta['payload_size'] = len(msg)
            received_message_meta['compressed_size'] = len(msg)
            received_message_meta['compression_percent'] = None

        if properties.content_type == CONTENT_TYPE_JSON:
            if self._Validate.is_json(msg):
                msg = bytes_to_unicode(json.loads(msg))
            else:
                raise YomboWarning("Receive msg reported json, but isn't: %s" % msg)
        elif properties.content_type == CONTENT_TYPE_MSGPACK:
            if self._Validate.is_msgpack(msg):
                msg = bytes_to_unicode(msgpack.loads(msg))
                # print("msg: %s" % type(msg))
                # print("msg: %s" % msg['headers'])
            else:
                raise YomboWarning("Received msg reported msgpack, but isn't: %s" % msg)

        # todo: Validate signatures/encryption here!
        return {
            'headers': msg['headers'],
            'body': msg['body'],
            'received_message_meta': received_message_meta,
        }

    @inlineCallbacks
    def amqp_incoming(self, body=None, properties=None, headers=None,
                            deliver=None, correlation_info=None,
                            received_message_meta=None, sent_message_meta=None,
                            subscription_callback=None, **kwargs):

        # arguments = {
        #     'body': body,
        #     'properties': properties,
        #     'headers': headers,
        #     'deliver': deliver,
        #     'correlation_info': correlation_info,
        #     'received_message_meta': received_message_meta,
        #     'sent_message_meta': sent_message_meta,
        # }
        # print("amqp_incoming................: %s" % arguments)

        ## Valiate that we have the required headers
        if 'message_type' not in headers:
            raise YomboWarning("Discarding request message, header 'message_type' is missing.")
        if 'gateway_routing' not in headers:
            raise YomboWarning("Discarding request message, header 'gateway_routing' is missing.")
        if headers['message_type'] == 'request':
            if 'request_type' not in headers:
                raise YomboWarning("Discarding request message, header 'request_type' is missing.")
        if headers['message_type'] == 'response':
            if 'response_type' not in headers:
                raise YomboWarning("Discarding request message, header 'response_type' is missing.")

        # Now, route the message. If it's a yombo message, send it to your AQMPYombo for delivery
        if correlation_info is not None and correlation_info['callback'] is not None and \
                        isinstance(correlation_info['callback'], collections.Callable) is True:
            logger.debug("calling message callback, not incoming queue callback")
            sent = maybeDeferred(
                correlation_info['callback'],
                body=body,
                properties=properties,
                headers=headers,
                deliver=deliver,
                correlation_info=correlation_info,
                received_message_meta=received_message_meta,
                sent_message_meta=sent_message_meta,
                subscription_callback=subscription_callback,
                )
            yield sent

        # Lastly, send it to the callback defined by the hooks returned.
        else:
            # print("amqp_incoming..correlation info: %s" % correlation_info)
            routing = headers['gateway_routing']
            # print("amqp_incoming..routing to amqpyombo_options callback: %s" % routing)
            # print("amqp_incoming...details: %s" % self.amqpyombo_options['routing'])
            if routing in self.amqpyombo_options['routing']:
                for the_callback in self.amqpyombo_options['routing'][routing]:
                    # print("about to call callback: %s" % the_callback)
                    sent = maybeDeferred(
                        the_callback,
                        deliver=deliver,
                        properties=properties,
                        headers=headers,
                        body=body,
                        correlation_info=correlation_info,
                        received_message_meta=received_message_meta,
                        sent_message_meta=sent_message_meta,
                        )
                    # d.callback(1)
                    yield sent

    def generate_message_response(self, exchange_name=None, source=None, destination=None,
                                 headers=None, body=None, routing_key=None, callback=None,
                                 correlation_id=None, message_type=None, response_type=None,
                                 data_type=None, route=None, gateway_routing=None,
                                 previous_properties=None, previous_headers=None):
        if self._Loader.operating_mode != 'run':
            return {}
        if previous_properties is None:
            raise YomboWarning("generate_message_response() requires 'previous_properties' argument.")
        if previous_headers is None:
            raise YomboWarning("generate_message_response() requires 'previous_headers' argument.")

        if message_type is None:
            message_type = "response"

        reply_to = None
        if 'correlation_id' in previous_headers and previous_headers['correlation_id'] is not None and \
            previous_headers['correlation_id'][0:2] != "xx_":
            reply_to = previous_headers['correlation_id']
            if headers is None:
                headers = {}
            headers['reply_to'] = reply_to

        response_msg = self.generate_message(exchange_name=exchange_name,
                                            source=source,
                                            destination=destination,
                                            message_type=message_type,
                                            data_type=data_type,
                                            body=body,
                                            routing_key=routing_key,
                                            callback=callback,
                                            correlation_id=correlation_id,
                                            headers=headers,
                                            route=route,
                                            gateway_routing=gateway_routing,
                                            )
        if response_type is not None:
            response_msg['body']['headers']['response_type'] = response_type

        return response_msg

    def generate_message_request(self, exchange_name=None, source=None, destination=None,
                                 headers=None, body=None, routing_key=None, callback=None,
                                 correlation_id=None, message_type=None, request_type=None,
                                 data_type=None, route=None, gateway_routing=None):
        if self._Loader.operating_mode != 'run':
            return {}

        if message_type is None:
            message_type = "request"

        request_msg = self.generate_message(exchange_name=exchange_name,
                                            source=source,
                                            destination=destination,
                                            message_type=message_type,
                                            data_type=data_type,
                                            body=body,
                                            routing_key=routing_key,
                                            callback=callback,
                                            correlation_id=correlation_id,
                                            headers=headers,
                                            route=route,
                                            gateway_routing=gateway_routing,
                                            )
        if request_type is not None:
            request_msg['body']['headers']['request_type'] = request_type

        return request_msg

    def generate_message(self, exchange_name, source, destination, message_type, data_type=None,
                         body=None, routing_key=None, callback=None, correlation_id=None,
                         headers=None, reply_to=None, route=None, gateway_routing=None):
        """
        When interacting with Yombo AMQP servers, we use a standard messaging layout. The format
        below helps other functions and libraries conform to this standard.

        This only creates the message, it doesn't send it. Use the publish() function to complete that.

        **Usage**:

        .. code-block:: python

           requestData = {
               "exchange_name" : "gw_config",
               "source"        : "yombo.gateway.lib.configurationupdate",
               "destination"   : "yombo.server.configs",
               "callback"      : self.amqp_direct_incoming,
               "data_type      : "object",
               "body"          : payload_content,  # Usually a dictionary.
               },
           }
           request = self.AMQPYombo.generateRequest(**requestData)

        :param exchange_name: The exchange the request should go to.
        :type exchange_name: str
        :param source: Value for the 'source' field.
        :type source: str
        :param destination: Value of the 'destination' field.
        :type destination: str
        :param message_type: Type of header. Usually one of: request, response
        :type message_type: str
        :param data_type: One of: Object, Objects, or String
        :type data_type: string
        :param body: The part that will become the body, or payload, of the message.
        :type body: str, dict, list
        :param routing_key: Routing key to use for message delivery. Usually '*'.
        :type routing_key: str
        :param callback: A pointer to the function to return results to. This function will receive 4 arguments:
          sendInfo (Dict) - Various details of the sent packet. deliver (Dict) - Deliver fields as returned by Pika.
          props (Pika Object) - Message properties, includes headers. msg (dict) - The actual content of the message.
        :type callback: function
        :param correlation_id: A correlation_id to use.
        :type correlation_id: string
        :param headers: Extra headers. Note: these cannot be validated with GPG/PGP keys.
        :type headers: dict

        :return: A dictionary that can be directly returned to Yombo SErvers via AMQP
        :rtype: dict
        """
        if self._Loader.operating_mode != 'run':
            return {}

        # print("body: %s" % exchange_name)
        # print("body: %s" % body)
        if routing_key is None:
            routing_key = '*'

        if body is None:
            body = {}

        if correlation_id is None:
            correlation_id = random_string(length=24)

        if data_type is None:
            if isinstance(body, list):
                data_type = 'objects'
            elif isinstance(body, str):
                data_type = 'string'
            else:
                data_type = 'object'

        if route is None:
            route = ["yombo.gw.amqpyombo:" + self.user_id]
        else:
            route.append("yombo.gw.amqpyombo:" + self.user_id)


        msg_created_at = float(time())
        request_msg = {
            "exchange_name": exchange_name,
            "routing_key": routing_key,
            "body": {
                "headers": {
                    "source": source + ":" + self.user_id,
                    "destination": destination,
                    "message_type": message_type.lower(),
                    "yombo_msg_protocol_verion": PROTOCOL_VERSION,
                    "correlation_id": correlation_id,
                    "msg_created_at": msg_created_at,
                    "data_type": data_type.lower(),
                    "route": route,
                },
                "body": body,
            },
            "properties": {
                "user_id": self.user_id,  # system id is required to be able to send it.
                "content_type": CONTENT_TYPE_MSGPACK,
                "content_encoding": None,
                "headers": {
                    "yombo_msg_protocol_verion": PROTOCOL_VERSION,
                    "route": "yombo.gw.amqpyombo:" + self.user_id,
                    "body_signature": "",
                },
            },
            "meta": {
                'finalized_for_sending': False,
                'msg_created_at': msg_created_at,
            },
        }

        if gateway_routing is not None:
            request_msg['body']['headers']['gateway_routing'] = gateway_routing
        if isinstance(headers, dict):
            request_msg['body']['headers'].update(headers)

        if callback is not None:
            request_msg['callback'] = callback
            if correlation_id is None:
                request_msg['body']['headers']['correlation_id'] = random_string(length=24)

        if reply_to is not None:
            request_msg['body']['headers']['reply_to'] = reply_to

        return request_msg

    def finalize_message(self, message):
        if 'correlation_id' in message['body']['headers']:
            message['properties']['correlation_id'] = message['body']['headers']['correlation_id']
        if 'reply_to' in message['body']['headers']:
            message['properties']['reply_to'] = message['body']['headers']['reply_to']
        # print("finalize message: %s" % message)
        message['body'] = msgpack.dumps(message['body'])

        # Lets test if we can compress. Set headers as needed.
        if len(message['body']) > 800:
            beforeZlib = len(message['body'])
            message['body'] = zlib.compress(message['body'], 5)  # 5 appears to be the best speed/compression ratio - MSchwenk
            afterZlib = len(message['body'])
            message['meta']['compression_percent'] = percentage(afterZlib, beforeZlib)

            message['properties']['content_encoding'] = "zlib"
        else:
            message['properties']['content_encoding'] = 'text'
        # request_msg['meta']['content_encoding'] = request_msg['properties']['content_encoding']
        # request_msg['meta']['payload_size'] = len(request_msg['body'])
        message['meta']['finalized_for_sending'] = True
        return message

    def publish(self, **kwargs):
        """
        Publishes a message. Use generate_message(), generate_message_request, or generate_message_response to
        create the message.
        :return:
        """
        if self._Loader.operating_mode != 'run':
            return

        logger.debug("about to publish: {kwargs}", kwargs=kwargs)
        if kwargs['meta']['finalized_for_sending'] is False:
            kwargs = self.finalize_message(kwargs)
        if "callback" in kwargs:
            # callback = kwargs['callback']
            # del kwargs['callback']
            if 'correlation_id' not in kwargs['properties']:
                kwargs['properties']['correlation_id'] = random_string()

        kwargs['yomboprotocol'] = True
        self.amqp.publish(**kwargs)

    def process_system(self, msg, properties):
        pass

    def _local_log(self, level, location, msg=""):
        logit = func = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)
