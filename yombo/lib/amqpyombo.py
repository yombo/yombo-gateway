#cython: embedsignature=True
# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Yombo uses message queuing and implements the Advanced Message Queuing Protocol (AMQP) to balance load within it's
infrastructure. This allows Yombo to provide redundancy and resiliency.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
    and classes **should not** be accessed directly by modules. These are documented here for completeness.

Connection should be maintained 100% of the time. It's easier on the Yombo servers to maintain an idle connection
than to keep raising and dropping connections.

Depending on the security options the user has selected, it can be used to transmit real time data to the servers
for further processing and event handling. See the Yombo privacy policy regarding users data: In short, it's the
users data, the user's own it, Yombo won't sell it, Yombo keeps it private.

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
import pika
import zlib
from datetime import datetime

import yombo.ext.umsgpack as msgpack

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet import ssl, protocol, defer
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboCritical, YomboMessageError
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import percentage, random_string
from yombo.utils.maxdict import MaxDict
from yombo.core.message import Message

logger = get_logger('library.amqpyombo')

PROTOCOL_VERSION = 2
PREFETCH_COUNT = 10  # determine how many messages should be received/inflight before yombo servers
                     # stop sending us messages. Should ACK/NACK all messages quickly.


class PikaProtocol(pika.adapters.twisted_connection.TwistedProtocolConnection):
    """
    Responsible for low level handling. Does the actual work of setting up any exchanges, queues, and bindings. Also
    sends greeting and initial handshake.

    On connect, it always sends a message to let Yombo know of it's pertinent information.
    """
    connected = False
    connection = None

    def __init__(self, factory):
        """
        Save pointer to factory and then call it's parent __init__.
        """
        self.factory = factory
        self._consumers = {}
        super(PikaProtocol, self).__init__(self.factory.AMQPYombo.pika_parameters)
        self._startup_request_ID = random_string(length=12) #gw

        self.incoming_queue = []

    @inlineCallbacks
    def connected(self, connection):
        """
        Is called when connected to Yombo AMQP server. Binds to the gateway listening queue, and sends a basic hello
        message. The response will be caught in the self.factory.incoming function.

        :param connection: The connection to Yombo AMQP server.
        """
        self._local_log("debug", "PikaProtocol::connected")
        self.connection = connection
        self.channel = yield connection.channel()

        def close_connection(channel, replyCode, replyText):
            logger.info("!!!!!!!!!!Trying to nicely close connection!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            connection.close()
        self.channel.add_on_close_callback(close_connection)

        yield self.channel.basic_qos(prefetch_count=PREFETCH_COUNT)
        logger.debug("Setting AMQP connected to true.")
        self.connected = True

        register = {
                    "queue_name"           : "ygw.q." + self.factory.AMQPYombo.gwuuid,
                    "queue_no_ack"         : False,
                    "callback"             : self.factory.incoming,
                    "yamqp_register_persist": True,
                   }
        self.setup_register_consumer(**register)

        # Local IP address is needed to send to mobile apps / local clients. This allows to mobile app or local client
        # to connect directly to the gateway instead of using Yombo as a proxy. This increases perform greatly for
        # things like light control, etc.  The external IP address will also be sent so that the client can
        # try to connect to the external IP address. If it can not reach the gateway by either of these methods,
        # it will connect to Yombo proxy servers, requests will come through the amqp connection. This is why
        # the connection needs to be open 100% of the time.
        request = {
              "data_type": "object",
              "request": {
                    "local_ip_address": self.factory.AMQPYombo._Configs.get("core", "localipaddress"),
                    "external_ip_address": self.factory.AMQPYombo._Configs.get("core", "externalipaddress"),
                    "protocol_version": PROTOCOL_VERSION,
              },
            }

        requestmsg = {
            "exchange_name"    : "ysrv.e.gw_config",
            "routing_key"      : '*',
            "body"             : request,
            "properties" : {
                "correlation_id" : self._startup_request_ID,
                "user_id"        : self.factory.AMQPYombo.gwuuid,
                "headers"        : {
                    "source"        : "yombo.gateway.lib.amqpyombo:" + self.factory.AMQPYombo.gwuuid,
                    "destination"   : "yombo.server.amqpyombo",
                    "type"          : "request",
                    "request_type"   : "startup",
                    },
                },
            "callback"          : None,
            "correlation_type"  : "local",
            }

        self.factory.send_correlation_ids[self._startup_request_ID] = {
            "time_created": datetime.now(),
            'time_sent': None,
            "time_received": None,
            "callback": None,
            "correlation_type": "local",
        }

        requestmsg['properties'] = pika.BasicProperties(**requestmsg['properties'])
        self.send_message(**requestmsg)

    def close(self):
        """
        Close the connection to Yombo.

        :return:
        """
        self._local_log("debug", "PikaProtocol::close", "Trying to close!")
        try:
            self.channel.close()
        except:
            pass

    def _local_log(self, level, location, msg=""):
        logit = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    @inlineCallbacks
    def setup_register_consumer(self, **kwargs):
        """
        Performs the actual binding of the queue to the AMQP channel.
        """
        self._local_log("debug", "PikaProtocol::setup_register_consumer")
        (queue, consumer_tag,) = yield self.channel.basic_consume(queue=kwargs['queue_name'],
                                                                  no_ack=kwargs['queue_no_ack'])
        d = queue.get()
        d.addCallback(self.receive_item, queue, kwargs['queue_no_ack'], kwargs['callback'])
        d.addErrback(self.receive_item_err)
        yield defer.succeed(None)

    def receive_item(self, item, queue, queue_no_ack, callback):
        """
        This function is called with EVERY incoming message. It will perform basic checks and then pass the message
        to the callback registered when the queue was defined.

        Summary of tasks:

        1) Validate incoming headers
        2) Setup ACK/Nack responses
        3) Send the message to the registered callback for the given queue.
        """
        self._local_log("debug", "PikaProtocol::receive_item, callback: %s" % callback)
        d = queue.get()
        d.addCallback(self.receive_item, queue, queue_no_ack, callback)
        d.addErrback(self.receive_item_err)
        (channel, deliver, props, msg,) = item
        if props.correlation_id in self.factory.send_correlation_ids:
            self.factory.send_correlation_ids[props.correlation_id]['time_received'] = datetime.now()

        time_info = self.factory.send_correlation_ids[props.correlation_id]
        daate_time = time_info['time_received'] - time_info['time_sent']
        milliseconds = (daate_time.days * 24 * 60 * 60 + daate_time.seconds) * 1000 + daate_time.microseconds / 1000.0
        logger.debug("Time between sending and receiving a response:: {milliseconds}", milliseconds=milliseconds)
        self.factory._Statistics.averages("lib.amqpyombo.amqp.response.time", milliseconds, bucket_time=15, anon=True)

#        log.msg('%s (%s): %s' % (deliver.exchange, deliver.routing_key, repr(msg)), system='Pika:<=')

        try:
            self._local_log("debug", "PikaProtocol::receive_item3")
            # do nothing on requests for now.... in future if we ever accept requests, we will.
            if props.headers['type'] == 'request':
                raise YomboWarning("Currently not accepting requests.")
            # if a response, lets make sure it's something we asked for!
            elif props.headers['type'] == "response":
                if props.correlation_id is None or not isinstance(props.correlation_id, basestring):
                    self.factory._Statistics.increment("lib.amqpyombo.amqp.received.discarded.correlation_id_invalid", bucket_time=15, anon=True)
                    raise YomboWarning("Correlation_id must be present for 'Response' types, and must be a string.")
                if props.correlation_id not in self.factory.send_correlation_ids:
                    logger.debug("{correlation_id} not in list of ids: {send_correlation_ids} ",
                                 correlation_id=props.correlation_id, send_correlation_ids=self.factory.send_correlation_ids.keys())
                    self.factory._Statistics.increment("lib.amqpyombo.amqp.received.discarded.nocorrelation", bucket_time=15, anon=True)
                    raise YomboWarning("Received request {correlation_id}, but never asked for it. Discarding",
                                       correlation_id=props.correlation_id)
            else:
                self.factory._Statistics.increment("lib.amqpyombo.amqp.received.discarded.unknown_msg_type", bucket_time=15, anon=True)
                raise YomboWarning("Unknown message type recieved.")

            self._local_log("debug", "PikaProtocol::receive_item4")
            if props.user_id is None:
                self.factory._Statistics.increment("lib.amqpyombo.amqp.received.discarded.nouserid", bucket_time=15, anon=True)
                raise YomboWarning("user_id missing.")
            if props.content_type is None:
                self.factory._Statistics.increment("lib.amqpyombo.amqp.received.discarded.content_type_missing", bucket_time=15, anon=True)
                raise YomboWarning("content_type missing.")
            if props.content_encoding is None:
                self.factory._Statistics.increment("lib.amqpyombo.amqp.received.discarded.content_encoding_missing", bucket_time=15, anon=True)
                raise YomboWarning("content_encoding missing.")
            if props.content_encoding != 'text' and props.content_encoding != 'zlib':
                self.factory._Statistics.increment("lib.amqpyombo.amqp.received.discarded.content_encoding_invalid", bucket_time=15, anon=True)
                raise YomboWarning("Content Encoding must be either  'text' or 'zlib'. Got: " + props.content_encoding)
            if props.content_type != 'text/plain' and props.content_type != 'application/msgpack' and  props.content_type != 'application/json':
                self.factory._Statistics.increment("lib.amqpyombo.amqp.received.discarded.content_type_invalid", bucket_time=15, anon=True)
                logger.warn('Error with contentType!')
                raise YomboWarning("Content type must be 'application/msgpack', 'application/json' or 'text/plain'. Got: " + props.content_type)

            if props.content_encoding == 'zlib':
                beforeZlib = len(msg)
                msg = zlib.decompress(msg)
                afterZlib = len(msg)
                logger.debug("Message sizes: msg_size_compressed = {compressed}, non-compressed = {uncompressed}, percent: {percent}",
                             compressed=beforeZlib, uncompressed=afterZlib, percent=percentage(beforeZlib, afterZlib))
                self.factory._Statistics.increment("lib.amqpyombo.amqp.received.compressed", bucket_time=15, anon=True)
                self.factory._Statistics.averages("lib.amqpyombo.amqp.received.compressed.percentage", percentage(beforeZlib, afterZlib), bucket_time=15, anon=True)
            else:
                self.factory._Statistics.increment("lib.amqpyombo.amqp.received.uncompressed", bucket_time=15, anon=True)
            self.factory._Statistics.averages("lib.amqpyombo.amqp.received.payload.size", len(msg), bucket_time=15, anon=True)

            if props.content_type == 'application/json':
                if self.is_json(msg):
                    msg = json.loads(msg)
                else:
                    raise YomboWarning("Receive msg reported json, but isn't.")
            elif props.content_type == 'application/msgpack':
                if self.is_msgpack(msg):
                    msg = msgpack.loads(msg)
                else:
                    raise YomboWarning("Received msg reported msgpack, but isn't.")

            # do nothing on requests for now.... in future if we ever accept requests, we will.
            if props.headers['type'] == 'Request':
                raise YomboWarning("Currently not accepting requests.")
            # if a response, lets make sure it's something we asked for!
            elif props.headers['type'] == "Response":
                if props.correlation_id not in self.factory.send_correlation_ids:
                    self.factory._Statistics.increment("lib.amqpyombo.amqp.received.discarded.no_correlation_id", bucket_time=15, anon=True)
                    raise YomboWarning("Received request %s, but never asked for it. Discarding" % props.correlation_id)

            self._local_log("debug", "PikaProtocol::receive_item5")
        except YomboWarning as e:
            if not queue_no_ack:
                logger.debug("AMQP Sending {status} due to invalid request. Tag: {tag}  E: {e}",
                             status='NACK', tag=deliver.delivery_tag, e=e)
                channel.basic_nack(deliver.delivery_tag, False, False)
        except Exception as e:
            if not queue_no_ack:
                logger.debug("AMQP Sending {status} due to unknown exception. Tag: {tag}  E: {e}",
                             status='NACK', tag=deliver.delivery_tag, e=e)
                channel.basic_nack(deliver.delivery_tag, False, False)
#          raise Exception
        else:
            self._local_log("debug", "PikaProtocol::receive_item6")
            logger.debug('Calling callback: {callback}', callback=callback)
            d = defer.maybeDeferred(callback, deliver, props, msg)
            logger.debug('Called callback: {callback}', callback=callback)
            if not queue_no_ack:
                # if it gets here, it's passed basic checks. Lets either store the message for later or pass it on.
                logger.debug("AMQP 1 Sending {status} due to valid request. Tag: {tag}",
                             status='ACK', tag=deliver.delivery_tag)
                d.addCallback(self._basic_ack, channel, deliver.delivery_tag)
                d.addErrback(self._basic_nack, channel, deliver.delivery_tag)

    def receive_item_err(self, error):
        """
        Is caled when an un-caught exception happens while processing an incoming message.

        :param error:
        :return:
        """
        self._local_log("debug", "PikaProtocol::receive_item_err", "Error: %s" % error)

    def _basic_ack(self, tossaway, channel, tag):
        self._local_log("debug", "PikaProtocol::_basic_ack", "Tag: %s" % tag)
        channel.basic_ack(tag)

    def _basic_nack(self, error, channel, tag):
        self._local_log("debug", "PikaProtocol::_basic_nack", "Tag: %s" % tag)
        channel.basic_nack(tag, False, False)

    def send(self):
        """
        Sends any queued messages to Yombo Services. If offline, messages will be queued and sent when connected.
        """
        self._local_log("debug", "PikaProtocol::send")
        if self.connected:
            while len(self.factory.outgoing_queue) > 0:
                message = self.factory.outgoing_queue.pop(0)
                if 'time_expires' in message:
                    if message['time_expires'] > datetime.now():
                        logger.warn("Message has expired..Not sending...")
                        continue
                self.send_message(**message)

    @inlineCallbacks
    def send_message(self, **kwargs):
        """
        Send a single message. This shouldn't be called directly by any library or module (except for this one).
        """
#        logger.debug("In PikaProtocol send_message a: %s" % kwargs['properties'].correlation_id)
#        prop = spec.BasicProperties(delivery_mode=2)

#        logger.info("exchange=%s, routing_key=%s, body=%s, properties=%s " % (kwargs['exchange_name'],kwargs['routing_key'],kwargs['body'], kwargs['properties']))
#        if HASMSGPACK:
        kwargs['body'] = msgpack.dumps(kwargs['body'])
        kwargs['properties'].content_type = "application/msgpack"
#        else:
#            kwargs['body'] = json.dumps(kwargs['body'])
#            kwargs['properties'].content_type = "application/json"

        self.factory._Statistics.averages("lib.amqpyombo.amqp.sent.size", len(kwargs['body']), bucket_time=15, anon=True)
        if len(kwargs['body']) > 700:
            beforeZlib = len(kwargs['body'])
            kwargs['body'] = zlib.compress(kwargs['body'], 5)  # 5 appears to be fastest with test data - MSchwenk
            kwargs['properties'].content_encoding == "zlib"
            self.factory._Statistics.increment("lib.amqpyombo.amqp.sent.compressed", bucket_time=15, anon=True)
            afterZlib = len(kwargs['body'])
            self.factory._Statistics.increment("lib.amqpyombo.amqp.sent.compressed", bucket_time=15, anon=True)
            self.factory._Statistics.averages("lib.amqpyombo.amqp.sent.compressed.percentage", percentage(afterZlib, beforeZlib), anon=True)
        else:
            kwargs['properties'].content_encoding = 'text'
            self.factory._Statistics.increment("lib.amqpyombo.amqp.sent.uncompressed", bucket_time=15, anon=True)

        try:
            if kwargs['properties'].correlation_id in self.factory.send_correlation_ids:
                self.factory.send_correlation_ids[kwargs['properties'].correlation_id]['time_sent'] = datetime.now()
#            logger.info("exchange=%s, routing_key=%s, body=%s, properties=%s " % (kwargs['exchange_name'],kwargs['routing_key'],kwargs['body'], kwargs['properties']))
            yield self.channel.basic_publish(exchange=kwargs['exchange_name'], routing_key=kwargs['routing_key'], body=kwargs['body'], properties=kwargs['properties'])
        except Exception as error:
            logger.warn('Error while sending message: {error}', error=error)

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

class PikaFactory(protocol.ReconnectingClientFactory):
    """
    Responsible for setting up the factory, building the protocol and then connecting.
    """
    def __init__(self, AMQPYombo):
        self._local_log("debug", "PikaFactory::__init__")
        self._Name = "PikaFactory"
        self._FullName = "yombo.gateway.lib.PikaFactory"
        # DO NOT CHANGE THESE!  Mitch Schwenk @ yombo.net
        # Reconnect sort-of fast, but random. ~25 second max wait
        # This is set incase a server reboots, don't DDOS the servers!
        self.initialDelay = 0.2
        self.jitter = 0.2
        self.factor = 1.82503912
        self.maxDelay = 25 # this puts retrys around 17-26 seconds

        self.send_correlation_ids = MaxDict(700)  # correlate requests with responses
        self.AMQPProtocol = None

        self._Statistics = AMQPYombo._Libraries['statistics']
        self.AMQPYombo = AMQPYombo
        self.outgoing_queue = []
        self.incoming_queue = []

        self.fullyConnected = False  # connected to AMQP, and ready to send messages.   #gw

    def _local_log(self, level, location, msg=""):
        logit = func = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    def startedConnecting(self, connector):
        self._local_log("debug", "PikaFactory::startedConnecting")

    def buildProtocol(self, addr):
        self._local_log("debug", "PikaFactory::buildProtocol")
        self.resetDelay()
        self.AMQPProtocol = PikaProtocol(self)
        self.AMQPProtocol.factory = self
        self.AMQPProtocol.ready.addCallback(self.AMQPProtocol.connected)
        return self.AMQPProtocol

    def connected(self):
        """
        Called by incoming (below function) after it has received a "Startup = OK" message from the server. At this
        level, it's a full connection instead of just a simple TCP connection, which is called at the protocol layer.

        :return:
        """
        temp_queue = list(self.incoming_queue)
        self.incoming_queue = []
        for queue_item in temp_queue:
            logger.info("Incoming loop....")
            d = defer.maybeDeferred(self.do_incoming, queue_item['deliver'],
                                    queue_item['properties'], queue_item['message'])

    def incoming(self, deliver, properties, msg):
        """
        Handles all incoming message routed to the common gateway queue.

        :param deliver: 
        :param properties: 
        :param msg: 
        :return: 
        """
        logger.debug("got incoming: {msg}", msg=msg)
        item = {
            "deliver" : deliver,
            "properties" : properties,
            "message" : msg,
        }

        # first, lets process a startup complete if available.
        if self.fullyConnected == False:
            if (self.AMQPProtocol._startup_request_ID == properties.correlation_id and
                properties.headers['response_type'] == 'startup'):
#                logger.debug("msg: {msg}", msg=msg)
                if msg['startup'] == 'ok':
                    self.fullyConnected = True
                    logger.info("Fully connected to Yombo infrastructure....nice.")
                    self.connected()
                    self.AMQPYombo.connected()
                    self.AMQPProtocol.send()
                elif msg['startup'] == 'error':
                    raise YomboCritical("Yombo Server won't accept our startup request. Reason: %s" % msg['reason'])
                else:
                    raise YomboCritical("Yombo Server won't accept our startup request. Reason: %s" % msg['reason'])
            else:
                self.incoming_queue.append(item)
            return
        else:
            temp_queue = list(self.incoming_queue)
            self.incoming_queue = []
            for queue_item in temp_queue:
                logger.info("Incoming loop....")
                d = defer.maybeDeferred(self.do_incoming, queue_item['deliver'], queue_item['properties'], queue_item['message'])
            self.do_incoming(deliver, properties, msg)

    def do_incoming(self, deliver, properties, msg):
        """
        Incoming from Yombo AMQP server.
        """
        self._local_log("debug", "PikaFactory::do_incoming")
#        self._local_log("debug", "Msg:{msg}", msg=msg)
#        if msg['Code'] != 200:
#            raise YomboWarning("Yombo service responsed with code %s: %s" %(msg['Code'], msg['Message']))

        # A request from somewhere
        if properties.headers['type'] == 'request':
            self.do_incoming_request(deliver, properties, msg)
        # A response from a library or sepcific module
        elif properties.headers['type'] == "response":
            dt = self.send_correlation_ids[properties.correlation_id]['time_received'] - self.send_correlation_ids[properties.correlation_id]['time_sent']
            ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
            logger.debug("Message Response time: {mesageResponseTime} ms", mesageResponseTime=ms)  # todo: add to stats
            self.do_incoming_response(deliver, properties, msg)
        # Route to Yombo Message system for delivery.
        elif properties.headers['type'] == "Message":
            self.AMQPYombo.amqpTomsg(deliver, properties, msg)
        # nothing else to do. Bad message!
        else:
            raise YomboWarning("Unknown message type ({messageType}), dropping.", messageType=properties.headers['type'])

    def do_incoming_response(self, deliver, properties, msg):
        """
        Handle incoming responses. If the message gets here, it's in response to a request.
        """
        self._local_log("debug", "PikaFactory::do_incoming_response")
        if properties.correlation_id in self.send_correlation_ids:
            # Handle messages that were directly sent from an external library.
            if self.send_correlation_ids[properties.correlation_id]['correlation_type'] == "direct_send":
                if self.send_correlation_ids[properties.correlation_id]['callback'] != None:
                    self.send_correlation_ids[properties.correlation_id]['callback'](self.send_correlation_ids[properties.correlation_id], deliver, properties, msg)
                    return
                else:
                    raise YomboWarning("All direct_send responses must have a callback!")
        raise YomboWarning("No where to route response to, dropping message.")

    def do_incoming_request(self, deliver, properties, response):
        """
        Currently, we don't accept requests.
        """
        pass

    def connection_lost(self):
        """
        Connection was lost.  What to do?
        :return:
        """
        pass

    def close(self):
        """
        Called from AMQPYombo._unload_, usually when gateway is shutting down.
        :return:
        """
        self._local_log("debug", "!!!!PikaFactory::close")
#        print "amqp factory about to call close: %s" % self.AMQPProtocol
        self.AMQPProtocol.close()
        self.AMQPYombo.disconnected()

    def clientConnectionLost(self, connector, reason):
        logger.debug("In PikaFactory clientConnectionLost. Reason: {reason}", reason=reason)
        self.connection_lost()
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        logger.debug("In PikaFactory clientConnectionFailed. Reason: {reason}", reason=reason)
        self.connection_lost()
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def send_message(self, **kwargs):
        logger.debug("In PikaFactory send_message")
#        if(kwargs[properties][headers][type] == "Request") {

#        }
        self.send_correlation_ids[kwargs['properties'].correlation_id] = {
            "time_created"      : kwargs.get("time_created", datetime.now()),
            'time_sent'         : None,
            "time_received"     : None,
            "callback"          : kwargs['callback'],
            "correlation_type"  : kwargs.get('correlation_type', None),
        }

        self.outgoing_queue.append((kwargs))
        logger.debug("In PikaFactory send_message client: protocol: %s, fullyConnected: %s" % (self.AMQPProtocol, self.fullyConnected))
        if self.AMQPProtocol is not None and self.fullyConnected is True:
            self.AMQPProtocol.send()


class AMQPYombo(YomboLibrary):
    """
    Yombo library to handle connection to RabbitMQ. It's responsible for starting up the factory and telling it to
    connect using the protocol.
    
    Developers should only interact with these functions and not with the factory or protocol functions.
    """
    def _init_(self, loader):
        self.loader = loader
        self._connecting = False  # True if trying to connect now
        self._connected = False  # Connected to AMQP
        self.gwuuid = "gw_" + self._Configs.get("core", "gwuuid")

        self.pika_factory = PikaFactory(self)
        self._local_log("debug", "AMQPYombo::connect")
        environment = self._Configs.get('server', 'environment', "production")
        if self._Configs.get("server", 'hostname', "") != "":
            self.amqp_host = self._Configs.get("server", 'hostname')
        else:
            if environment == "production":
                self.amqp_host = "amqp.yombo.net"
            elif environment == "staging":
                self.amqp_host = "amqpstg.yombo.net"
            elif environment == "development":
                self.amqp_host = "amqpdev.yombo.net"
            else:
                self.amqp_host = "amqp.yombo.net"

        self.pika_credentials=pika.PlainCredentials( self.gwuuid, self._Configs.get("core", "gwhash") )
        self.pika_parameters = pika.ConnectionParameters(
            host=self.amqp_host,
            port=5671,
            virtual_host='yombo',
            heartbeat_interval=1800,
            ssl=True,
            credentials=self.pika_credentials
        )
        self._States.set('amqp.connected', False)

        self.connect()

    def _unload_(self):
        self._local_log("debug", "AMQPYombo::_stop_")
        self.pika_factory.close()

    def _local_log(self, level, location, msg=""):
        logit = func = getattr(logger, level)
        logit("In {location} : {AMQPProtocolmsg}", location=location, msg=msg)

    def AMQPYombo_i18n_states(self, **kwargs):
       return [
           {'amqp.connected': {
               'en': 'True if AMQP connection exists to Yombo servers.',
               },
           },
       ]
    def connect(self):
        """
        Called from self._init_ to start the connection to Yombo AMQP.
        """
        if self._connecting is True:
            logger.debug("Already trying to connect, connect attempt aborted.")
            return
        self._connecting = True

        self.myreactor = reactor.connectSSL(self.amqp_host, 5671, self.pika_factory,
             ssl.ClientContextFactory())

    def connected(self):
        """
        Called by pika_factory.incoming() after successfully completed negotiation. It's already been connected
        for a while, but now it's connected as far as the library is concerned.
        """
        self._local_log("debug", "AMQPYombo::connected")
        self._connected = True
        self._connecting = False
        self.timeout_reconnect_task = False
        self._States.set('amqp.connected', True)

    def send_amqp_message(self, **kwargs):
        """
        Modules can use this with caution for performance reasons or a specific need to bypass the messaging system.
        Otherwise, use the message system below to send messages.
        """
        self._local_log("debug", "send_amqp_message", "Message: %s" % kwargs)
        callback = kwargs.get('callback', None)
        if callback is None:
            raise YomboWarning("AMQP.send_amqp_message must have a 'callback'")
        if callable(callback) is False:
            raise YomboWarning("AMQP.send_amqp_message - callback must be callable.")

        exchange_name = kwargs.get('exchange_name', None)
        if exchange_name is None:
            raise YomboWarning("AMQP.send_amqp_message must have an 'exchange_name'")

        body = kwargs.get('body', None)
        if body is None:
            raise YomboWarning("AMQP.send_amqp_message must have a 'body'")

        kwargs["time_created"] = kwargs.get("time_created", datetime.now())
        kwargs['routing_key'] = kwargs.get('routing_key', '*')
        kwargs['correlation_id'] = kwargs.get('correlation_id', random_string(length=18))
        kwargs['correlation_type'] = "direct_send"

        properties = kwargs.get('properties', {})
        properties['user_id'] = self.gwuuid
        kwargs['properties'] = pika.BasicProperties(**properties)

        self.pika_factory.send_message(**kwargs)

    def generate_request_message(self, **kwargs):
        """
        Generates a standard request, need to call "send_amqp_message" to send the request.

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
        request_type = kwargs.get('request_type', None)
        exchange_name = kwargs.get('exchange_name', None)
        body = kwargs.get('body', None)
        source = kwargs.get('source', None)
        destination = kwargs.get('destination', None)
        callback = kwargs.get('callback', None)

        if exchange_name is None:
            raise YomboWarning("AMQP.generateRequest requires 'exchange_name'.")
        if body is None:
            raise YomboWarning("AMQP.generateRequest requires 'body'.")
        if source is None:
            raise YomboWarning("AMQP.generateRequest requires 'source'.")
        if destination is None:
            raise YomboWarning("AMQP.generateRequest requires 'destination'.")
        if callback is None:
            raise YomboWarning("AMQP.generateRequest requires 'callback'.")
        if request_type is None:
            raise YomboWarning("AMQP.generateRequest requires 'request_type'.")

        request_id = random_string(length=12)

        requestmsg = {
            "exchange_name"    : exchange_name,
            "routing_key"      : '*',
            "body"             : body,
            "properties" : {
                "correlation_id" : request_id,
                "user_id"        : self.gwuuid,
                "headers"        : {
                    "source"        : source + ":" + self.gwuuid,
                    "destination"   : destination,
                    "type"          : "request",
                    "request_type"   : request_type,
                    },
                },
            "callback"          : callback,
            }
        return requestmsg

    def disconnect(self):
        """
        Disconnect from the Yombo AMQP service, and tell the connector to not reconnect.
        """
        print "aqmp disconnect"
        self.pika_factory.stopTrying()
        self.pika_factory.close()
#        self.myreactor.disconnect()

    def disconnected(self):
        """
        Function is called when the Gateway is disconnected from the AMQP service.
        """
        self._States.set('amqp.connected', False)
        logger.info("Disconnected from Yombo service.")
        self.pika_factory.fullyConnected = False  # connected to AMQP, and ready to send messages.
        self._connected = False  # connected to AMQP, and ready to send messages.

    def amqp_to_message(self, deliver, properties, amqp):
        """
        Convert an AMQP message to a Yombo Message. This is used for routing command and status messages.

        :param deliver:
        :param properties:
        :param message:
        """
        raise YomboWarning("amqpToMesasge - Incoming message routing not implmented")

        if message.checkDestinationAsLocal() is not True: # in future, if we become a router, this will change
            raise YomboMessageError("Received a message not meant for us, dropping.")

        #this is first stab - need error checking.
        message = Message(amqp['Request'])
        message.send()

    def message(self, message):
        """
        Messages bound externally are routed here. This library doesn't subscribe to anything, so it must
        sepcifically be routed here by the message system or from another library/module.

        Messages sent here will be converted to an AMQP message for delivery.

        :param message: A Yombo Message to be routed externally
        :type message: Message
        """
        raise YomboWarning("message -> AMQP - Outgoing message routing not implmented")

        if message.checkDestinationAsLocal() is False:
            raise YomboMessageError("Tried to send a local message externally. Dropping.")
        if message.validateMsgOriginFull() is False:
            raise YomboMessageError("Full msgOrigin needs full path.")
        if message.validateMsgDestinationFull() is False:
            raise YomboMessageError("Full msgDestination needs full path.")

        request = {
              "DataType": "Object",
              "Request": message.dumpToExternal(),
            }

        requestmsg = {
            "exchange_name"    : "gw_config",
            "routing_key"      : '*',
            "body"             : request,
            "properties" : {
                "correlation_id" : requestID,
                "user_id"        : self.gwuuid,
                "headers"        : {
                    "source"        : message.msgOrigin,
                    "destination"   : message.msgDestination,
                    "type"          : "Message",
                    },
                },
            "callback"          : None
            }
