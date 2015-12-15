#cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Establishes a connection the Yombo servers. Configuration updates are sent,
device logs (if enabled), statistics (if enabled), and various other features
can use this data channel. The gateawy can also receive commands from Yombo
API, mobile devices, or 3rd party automation servicesfor command / data control.

This data connection is also used to send messages to other gateways that are
not directly routable. The Yombo servers also acts as a router to deliver
a :ref:`Message`_ from remote sources, including remote controllers that
couldn't reach the gateway directly.

Connection should be maintained 100% of the time.  It's easier on the yombo
servers to maintain an idle connection than to keep rasing and dropping
connections.

Depending on the security options the user has selected, it can be used to
transmit real time data to the servers for further processing and event
handling.  See the Yombo privacy policy regarding users data: In short, it's
the users data, Yombo keeps it private.

.. warning::

  Module developers and users should not use this library independantly
  without consulting with Yombo support as a feature enhancement.
  This is listed here for completeness. Use a :mod:`helpers` function
  to get what is needed.

:TODO: The gateway needs to check for a non-responsive server or
if it doesn't get a response in a timely manor. It should respond
in MS, but it could have died/hung.  Perhaps disconnect and reconnect to
another server? -Mitch

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2015 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
try: import simplejson as json  # Prefer simplejson is installed, otherwise json will work swell.
except ImportError: import json
from collections import deque
from time import time
from datetime import datetime
import zlib

try:  #prefer to talk in msgpack, if available.
    import msgpack
    HASMSGPACK = True
except ImportError:
    HASMSGPACK = False

import pika
#from pika import spec
#from pika import exceptions
from pika.adapters import twisted_connection

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet import ssl, protocol, defer
from twisted.python import log
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboCritical, YomboMessageError
from yombo.core.helpers import getConfigValue, generateRandom, percentage, getComponent
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
from yombo.core.maxdict import MaxDict
from yombo.core.message import Message

logger = getLogger('library.amqpyombo')

PREFETCH_COUNT = 10  # determine how many messages should be received/inflight
                     # before yombo servers stop sending us messages. Shoul ACK/NACK
                     # all messages quickly.

class PikaProtocol(twisted_connection.TwistedProtocolConnection):
    """
    Responsible for semi-low level handling. Does the actual work of
    setting up any exchanges, queues, and bindings.
    """
    connected = False
    connection = None
    name = 'AMQP:Protocol'

    def __init__(self, factory):
        """
        Save pointer to factory and then call it's parent __init__.
        """
        self.factory = factory
        self._consumers = {}
        super(PikaProtocol, self).__init__(self.factory.AMQPYombo.parameters)
        self.startupRequestID = generateRandom(length=12) #gw

        self.incoming_queue = []

    @inlineCallbacks
    def connected(self, connection):
        """
        Is called when connected to Yombo AMQP server.

        :param connection: The connection to Yombo AMQP server.
        """
        self.logLocation("debug", "PikaProtocol::connected")
        self.connection = connection
        self.channel = yield connection.channel()

        def closeConnection(channel, replyCode, replyText):
            logger.info("!!!!!!!!!!Trying to nicely close connection!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            connection.close()
        self.channel.add_on_close_callback(closeConnection)

        yield self.channel.basic_qos(prefetch_count=PREFETCH_COUNT)
        logger.info("!!!!! Setting AMQP connected to true.")
        self.connected = True

        register = {
                    "queue_name"           : "ygw.q." + self.factory.AMQPYombo.gwuuid,
                    "queue_no_ack"         : False,
                    "callback"             : self.factory.incoming,
                    "yamqp_register_persist" : False,
                   }
        self.setup_register_consumer(**register)

        request = {
              "DataType": "Object",
              "Request": {
                    "LocalIPAddress"    : getConfigValue("core", "localipaddress"),
                    "ExternalIPAddress" : getConfigValue("core", "externalipaddress"),
              },
            }

        requestmsg = {
            "exchange_name"    : "ysrv.e.gw_config",
            "routing_key"      : '*',
            "body"             : request,
            "properties" : {
                "correlation_id" : self.startupRequestID,
                "user_id"        : self.factory.AMQPYombo.gwuuid,
                "headers"        : {
                    "Source"        : "yombo.gateway.lib.amqpyombo:" + self.factory.AMQPYombo.gwuuid,
                    "Destination"   : "yombo.server.amqpyombo",
                    "Type"          : "Request",
                    "RequestType"   : "Startup",
                    },
                },
            "callback"          : None,
            "correlation_type"  : "local",
            }

        self.factory.sentCorrelationIDs[self.startupRequestID] = {
            "time_created"      : datetime.now(),
            'time_sent'         : None,
            "time_received"     : None,
            "callback"          : None,
            "correlation_type"  : "local",
        }

        requestmsg['properties'] = pika.BasicProperties(**requestmsg['properties'])
        self.sendMessage(**requestmsg)

    def close(self):
        self.logLocation("debug", "PikaProtocol::close", "Trying to close!")
        try:
            self.channel.close()
        except:
            pass

    def logLocation(self, level, location, msg=""):
        logit = func = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    def register_consumer(self):
        """
        Bind to a queue
        """
        self.logLocation("debug", "PikaProtocol::setup_register_consumer")
        if self.connected == True:
            for key in self.factory.consumer_list.keys():
                if self.factory.consumer_list[key]['yaqmp_registered'] == False:
                    self.factory.consumer_list[key]['yaqmp_registered'] = True
                    self.setup_register_consumer(**self.factory.consumer_list[key]['kwargs'])
                    if self.factory.consumer_list[key]['yamqp_register_persist'] == False:
                        del self.factory.consumer_list[key]

    @inlineCallbacks
    def setup_register_consumer(self, **kwargs):
        """
        Sets up the actual binding.
        """
        self.logLocation("debug", "PikaProtocol::setup_register_consumer")
        (queue, consumer_tag,) = yield self.channel.basic_consume(queue=kwargs['queue_name'], no_ack=kwargs['queue_no_ack'])
        d = queue.get()
        d.addCallback(self._read_item, queue, kwargs['queue_no_ack'], kwargs['callback'])
        d.addErrback(self._read_item_err)
        yield defer.succeed(None)

    @inlineCallbacks
    def setup_unregister_consumer(self, **kwargs):
        """
        Sets up the actual binding.
        """
        (queue, consumer_tag,) = yield self.channel.basic_cancel(consumer_tag=self._consumers[kwargs['queue_name']])

    def _read_item(self, item, queue, queue_no_ack, callback):
        """
        Callback function which is called when an item is read. Forwards the item received
        to the correct callback method.
        """
        self.logLocation("debug", "PikaProtocol::_read_item")
        d = queue.get()
        d.addCallback(self._read_item, queue, queue_no_ack, callback)
        d.addErrback(self._read_item_err)
        (channel, deliver, props, msg,) = item
        self.logLocation("debug", "PikaProtocol::_read_item2")
        if props.correlation_id in self.factory.sentCorrelationIDs:
            self.factory.sentCorrelationIDs[props.correlation_id]['time_received'] = datetime.now()

#        log.msg('%s (%s): %s' % (deliver.exchange, deliver.routing_key, repr(msg)), system='Pika:<=')

        try:
            self.logLocation("debug", "PikaProtocol::_read_item3")
            # do nothing on requests for now.... in future if we ever accept requests, we will.
            if props.headers['Type'] == 'Request':
                raise YomboWarning("Currently not accepting requests.")
            # if a response, lets make sure it's something we asked for!
            elif props.headers['Type'] == "Response":
                if props.correlation_id is None or not isinstance(props.correlation_id, basestring):
                    raise YomboWarning("Correlation_id must be present for 'Response' types, and must be a string.")
                if props.correlation_id not in self.factory.sentCorrelationIDs:
                    logger.debug("{correlation_id} not in list of ids: {sentCorrelationIDs} ", correlation_id= props.correlation_id, sentCorrelationIDs=self.factory.sentCorrelationIDs)
                    raise YomboWarning("Received request {correlation_id}, but never asked for it. Discarding", correlation_id=props.correlation_id)
            else:
                raise YomboWarning("Unknown message type recieved.")

            self.logLocation("debug", "PikaProtocol::_read_item4")
            if props.user_id is None:
                raise YomboWarning("user_id missing.")
            if props.content_type is None:
                raise YomboWarning("content_type missing.")
            if props.content_encoding is None:
                raise YomboWarning("content_encoding missing.")
            if props.content_encoding != 'text' and props.content_encoding != 'zlib':
                raise YomboWarning("Content Encoding must be either  'text' or 'zlib'. Got: " + props.content_encoding)
            if props.content_type != 'text/plain' and props.content_type != 'application/msgpack' and  props.content_type != 'application/json':
                logger.warn('Error with contentType!')
                raise YomboWarning("Content type must be 'application/msgpack', 'application/json' or 'text/plain'. Got: " + props.content_type)

            self.factory.StatisticsLibrary.increment("lib.amqpyombo.amqp.recieved")
            if props.content_encoding == 'zlib':
                beforeZlib = len(msg)
                msg = zlib.decompress(msg)
                afterZlib = len(msg)
                self.factory.StatisticsLibrary.increment("lib.amqpyombo.amqp.compressed")
                self.factory.StatisticsLibrary.timing("lib.amqpyombo.amqp.compressed", percentage(afterZlib, beforeZlib))

            else:
                self.factory.StatisticsLibrary.increment("lib.amqpyombo.amqp.uncompressed")

            if props.content_type == 'application/json':
                if self.is_json(msg):
                    msg = json.loads(msg)
                else:
                    raise YomboWarning("Received msg reported json, but isn't.")
            elif props.content_type == 'application/msgpack':
                if self.is_msgpack(msg):
                    msg = msgpack.loads(msg)
                else:
                    raise YomboWarning("Received msg reported msgpack, but isn't.")

            # do nothing on requests for now.... in future if we ever accept requests, we will.
            if props.headers['Type'] == 'Request':
                raise YomboWarning("Currently not accepting requests.")
            # if a response, lets make sure it's something we asked for!
            elif props.headers['Type'] == "Response":
                if props.correlation_id not in self.factory.sentCorrelationIDs:
                    raise YomboWarning("Received request %s, but never asked for it. Discarding" % props.correlation_id)

            self.logLocation("debug", "PikaProtocol::_read_item5")
        except YomboWarning as e:
          if not queue_no_ack:
            logger.debug("AMQP Sending {status} due to invalid request. Tag: {tag}", status='NACK', tag=deliver.delivery_tag)
            channel.basic_nack(deliver.delivery_tag, False, False)
        except Exception as e:
          if not queue_no_ack:
            logger.debug("AMQP Sending {status} due to unknown exception. Tag: {tag}", status='NACK', tag=deliver.delivery_tag)
            channel.basic_nack(deliver.delivery_tag, False, False)
          raise Exception
        else:
          logger.info('Calling callback: {callback}', callback=callback)
          d = defer.maybeDeferred(callback, deliver, props, msg)
          if not queue_no_ack:
            # if it gets here, it's passed basic checks. Lets either store the message for later or pass it on.
            logger.debug("AMQP Sending {status} due to invalid request. Tag: {tag}", status='ACK', tag=deliver.delivery_tag)
            d.addCallback(self._basic_ack, channel, deliver.delivery_tag)
            d.addErrback(self._basic_nack, channel, deliver.delivery_tag)

    def _basic_ack(self, tossaway, channel, tag):
        self.logLocation("debug", "PikaProtocol::_basic_ack", "Tag: %s" % tag)
        channel.basic_ack(tag)

    def _basic_nack(self, error, channel, tag):
        self.logLocation("debug", "PikaProtocol::_basic_nack", "Tag: %s" % tag)
        channel.basic_nack(tag, False, False)

    def _read_item_err(self, error):
        self.logLocation("debug", "PikaProtocol::_read_item_err", "Error: %s" % error)

    def send(self):
        """
        Sends a message to Yombo Services. If offline, messages will be queued
        and sent when connected.
        #TODO: Add timestamp to a message and check against TTL. Ensure message
          isn't expired before being sent.
        """
        self.logLocation("debug", "PikaProtocol::send")
        if self.connected:
            while len(self.factory.outgoing_queue) > 0:
                message = self.factory.outgoing_queue.pop(0)
                self.sendMessage(**message)

    @inlineCallbacks
    def sendMessage(self, **kwargs):
        """
        Send a single message.
        """
#        logger.debug("In PikaProtocol sendMessage a: %s" % kwargs['properties'].correlation_id)
#        prop = spec.BasicProperties(delivery_mode=2)

#        logger.info("exchange=%s, routing_key=%s, body=%s, properties=%s " % (kwargs['exchange_name'],kwargs['routing_key'],kwargs['body'], kwargs['properties']))
        if HASMSGPACK:
            kwargs['body'] = msgpack.dumps(kwargs['body'])
            kwargs['properties'].content_type = "application/msgpack"
        else:
            kwargs['body'] = json.dumps(kwargs['body'])
            kwargs['properties'].content_type = "application/json"

        if len(kwargs['body']) > 700:
            kwargs['body'] = zlib.compress(kwargs['body'], 5) #5 appears to be fastest with test data - MSchwenk
            kwargs['properties'].content_encoding == "zlib"
        else:
            kwargs['properties'].content_encoding = 'text'

        try:
            if kwargs['properties'].correlation_id in self.factory.sentCorrelationIDs:
                self.factory.sentCorrelationIDs[kwargs['properties'].correlation_id]['time_sent'] = datetime.now()
#            logger.info("exchange=%s, routing_key=%s, body=%s, properties=%s " % (kwargs['exchange_name'],kwargs['routing_key'],kwargs['body'], kwargs['properties']))
            yield self.channel.basic_publish(exchange=kwargs['exchange_name'], routing_key=kwargs['routing_key'], body=kwargs['body'], properties=kwargs['properties'])
        except Exception as error:
            logger.warn('Error while sending message: {error}', error=error)

    def is_json(self, myjson):
        try:
            json_object = json.loads(myjson)
        except ValueError, e:
            return False
        return True

    def is_msgpack(self, mymsgpack):
        try:
            json_object = msgpack.loads(mymsgpack)
        except ValueError, e:
            return False
        return True

class PikaFactory(protocol.ReconnectingClientFactory):
#    name = 'AMQP:Factory'
    AMQPYombo = None   #AMQPYombo Library
    sentCorrelationIDs = MaxDict(500) #correlate requests with responses
    AMQPProtocol = None #

    def __init__(self, AMQPYombo):
        self.logLocation("debug", "PikaFactory::__init__")
        self._Name = "PikaFactory"
        self._FullName = "yombo.gateway.lib.PikaFactory"
        # DO NOT CHANGE THESE!  Mitch Schwenk @ yombo.net
        # Reconnect sort-of fast, but random. ~25 second max wait
        # This is set incase a server reboots, don't DDOS the servers!
        self.initialDelay = 0.1
        self.jitter = 0.2
        self.factor = 1.82503912
        self.maxDelay = 25 # this puts retrys around 17-26 seconds

        self.StatisticsLibrary = getComponent('yombo.gateway.lib.statistics')
        self.AMQPYombo = AMQPYombo
        self.AMQPProtocol = None
        self.outgoing_queue = []
        self.outgoing_persistent_queue = [] #to use? if so, make into sqldict
        self.incoming_queue = []

        self.fullyConnected = False  # connected to AMQP, and ready to send messages.   #gw

    def logLocation(self, level, location, msg=""):
        logit = func = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    def startedConnecting(self, connector):
        self.logLocation("debug", "PikaFactory::startedConnecting")

    def buildProtocol(self, addr):
        self.logLocation("debug", "PikaFactory::buildProtocol")
        self.resetDelay()
        self.AMQPProtocol = PikaProtocol(self)
        self.AMQPProtocol.factory = self
        self.AMQPProtocol.ready.addCallback(self.AMQPProtocol.connected)
        return self.AMQPProtocol

    def connected(self):
        #todo: do incoming and outgoing queues!
        for queue_item in self.incoming_queue:
            logger.info("Incoming loop....")
            d = defer.maybeDeferred(self.do_incoming, queue_item['deliver'], queue_item['properties'], queue_item['message'])
        self.incoming_queue = []

    def incoming(self, deliver, properties, msg):
        item = {
            "deliver" : deliver,
            "properties" : properties,
            "message" : msg,
        }

        # first, lets process a startup complete if available.
        if self.fullyConnected == False:
            if (self.AMQPProtocol.startupRequestID == properties.correlation_id and
                properties.headers['ResponseType'] == 'Startup'):
                logger.debug("msg: {msg}", msg=msg)
                if msg['Startup'] == 'Ok':
                    self.fullyConnected = True
                    logger.info("Fully connected")
                    self.connected()
                    self.AMQPYombo.connected()
                    self.AMQPProtocol.send()
                else:
                    raise YomboCritical("Yombo Server won't accept our startup request. Reason: %s" % msg['Message'])
            else:
                self.incoming_queue.append(item)
            return
        else:
            self.do_incoming(deliver, properties, msg)
            for queue_item in self.incoming_queue:
                logger.info("Incoming loop....")
                d = defer.maybeDeferred(queue_item['callback'], queue_item['deliver'], queue_item['props'], queue_item['msg'])

            self.incoming_queue = []

    def do_incoming(self, deliver, properties, msg):
        """
        Incoming from Yombo AMQP server.
        """
        self.logLocation("debug", "PikaFactory::do_incoming")
        if msg['Code'] != 200:
            raise YomboWarning("Yombo service responsed with code %s: %s" %(msg['Code'], msg['Message']))

        # A request from somewhere
        if properties.headers['Type'] == 'Request':
            self.do_incoming_request(deliver, properties, msg)
        # A response from a library or sepcific module
        elif properties.headers['Type'] == "Response":
            dt = self.sentCorrelationIDs[properties.correlation_id]['time_received'] - self.sentCorrelationIDs[properties.correlation_id]['time_sent']
            ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
            logger.info("Message Response time: {mesageResponseTime} ms", mesageResponseTime=ms)
            self.do_incoming_response(deliver, properties, msg)
        # Route to Yombo Message system for delivery.
        elif properties.headers['Type'] == "Message":
            self.AMQPYombo.amqpTomsg(deliver, properties, msg)
        # nothing else to do. Bad message!
        else:
            raise YomboWarning("Unknown message type ({messageType), dropping.", messageType=properties.headers['Type'] )

    def do_incoming_response(self, deliver, properties, msg):
        """
        Handle incoming responses. If the message gets here, it's in response to a request.
        """
        self.logLocation("debug", "PikaFactory::do_incoming_response")
        if properties.correlation_id in self.sentCorrelationIDs:
            # Handle messages that were directly sent from an external library.
            if self.sentCorrelationIDs[properties.correlation_id]['correlation_type'] == "direct_send":
                if self.sentCorrelationIDs[properties.correlation_id]['callback'] != None:
                    self.sentCorrelationIDs[properties.correlation_id]['callback'](self.sentCorrelationIDs[properties.correlation_id], deliver, properties, msg)
                    return
                else:
                    raise YomboWarning("All direct_send responses must have a callback!")
        raise YomboWarning("No where to route response to, dropping message.")

    def do_incoming_request(self, deliver, properties, response):
        """
        Currently, we don't accept requests.
        """
        pass

    def close(self):
        self.logLocation("debug", "PikaFactory::close")
        self.AMQPProtocol.close()

    def clientConnectionLost(self, connector, reason):
        logger.debug("In PikaFactory clientConnectionLost. Reason: {reason}", reason=reason)
        self._resetRegistrationItems()
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        logger.debug("In PikaFactory clientConnectionFailed. Reason: {reason}", reason=reason)
        self._resetRegistrationItems()
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def sendMessage(self, **kwargs):
        logger.debug("In PikaFactory sendMessage")
#        if(kwargs[properties][headers][Type] == "Request") {

#        }
        self.sentCorrelationIDs[kwargs['properties'].correlation_id] = {
            "time_created"      : kwargs.get("time_created", datetime.now()),
            'time_sent'         : None,
            "time_received"     : None,
            "callback"          : kwargs['callback'],
            "correlation_type"  : kwargs.get('correlation_type', None),
        }

        self.outgoing_queue.append((kwargs))
        logger.debug("In PikaFactory sendMessage client: %s" % self.AMQPProtocol)
        if self.AMQPProtocol is not None and self.AMQPProtocol.fullyConnected is True:
            self.AMQPProtocol.send()

class AMQPYombo(YomboLibrary):
    """
    Yombo library to aandle connection to RabbitMQ.
    """
    def _init_(self, loader):
        self.logLocation("debug", "AMQPYombo::_init_")
        self.loader = loader
        self._connecting = False
        self._connected = False  # connected to AMQP
        self.PFactory =  PikaFactory(self)
        self.gwuuid = "gw_" + getConfigValue("core", "gwuuid")
        self.headerSourceCallbacks = {} # register callbacks to local gateway modules
        self.messageCallbacks = {} # register callbacks to local gateway modules

        self.connect()

    def _load_(self):
        pass

    def _start_(self):
        pass

    def _stop_(self):
        self.logLocation("debug", "AMQPYombo::_stop_")
        self.PFactory.close()

    def _unload_(self):
        pass

    def logLocation(self, level, location, msg=""):
        logit = func = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    def registerCallback(self, type, locator, callback):
        """
        Register a callback function to be used when a new message arrives.

        The params defined refer to kwargs and become class variables.

        :param type: **Required.** One of:

            * "headerSource" - A response to an outgoing message.
        :type type: string
        :param locator: **Required.** Used to filter types of message to be sent to the callback. Examples:
            "Amqp", "gw_configs", "SomeType".
        :type locator: string
        :param callback: The function to call.
        :type callback: function
        """
        if(type == "headerSource"):
            self.headerSourceCallbacks[locator] = callback
        elif(type == "message"):
            self.messageCallbacks[locator] = callback
        else:
            raise YomboWarning("Unknown type of callback for AMQP system.")


    def updateSvcList(self):
        """
        This function will download a list of active Yombo Servers. This allows the gateway
        to select the closest/least busy server.

        This function doesn't currently do anything.
        """
        pass

    def connect(self):
        """
        Called during startup to connect to the Yombo AQMP message service.
        """
        self.logLocation("debug", "AMQPYombo::connect")
        if self._connecting is True:
            logger.debug("Already trying to connect, connect attempt aborted.")
            return
        self._connecting = True

        environment = getConfigValue('server', 'environment', "production")
        if getConfigValue("server", 'hostname', "") != "":
            host = getConfigValue("server", 'hostname')
        else:
            if(environment == "production"):
                host = "amqp.yombo.net"
            elif (environment == "staging"):
                host = "amqpstg.yombo.net"
            elif (environment == "development"):
                host = "amqpdev.yombo.net"
            else:
                host = "amqp.yombo.net"

        creds=pika.PlainCredentials(self.gwuuid, getConfigValue("core", "gwhash"))
        self.parameters = pika.ConnectionParameters(
            host=host,
            port=5671,
            virtual_host='yombo',
            heartbeat_interval=1800,
            ssl=True,
            credentials=creds
        )
        self.myreactor =  reactor.connectSSL("projects.yombo.net", 5671, self.PFactory,
             ssl.ClientContextFactory())

    def connected(self):
        """
        Called when connected to Yombo AMQP service.
        """
        self.logLocation("debug", "AMQPYombo::connected")
        self._connected = True
        self._connecting = False
        self.timeout_reconnect_task = False

    def sendDirectMessage(self, **kwargs):
        """
        Send a message through AMQP directly. This feature should only be used by libraries for direct access
        to the Yombo Servers. Modules can use this with caution for performance reasons or a specific need to
        bypass the messaging system.
        """
        self.logLocation("debug", "AMQPYombo::connected", "Message: %s" % kwargs)
        callback = kwargs.get('callback', None)
        if callback is None:
            raise YomboWarning("AMQP.sendDirectMessage must have a 'callback'")

        exchange_name = kwargs.get('exchange_name', None)
        if exchange_name is None:
            raise YomboWarning("AMQP.sendDirectMessage must have an 'exchange_name'")

        body = kwargs.get('body', None)
        if body is None:
            raise YomboWarning("AMQP.sendDirectMessage must have a 'body'")

        time_created = kwargs.get("time_created", datetime.now())
        kwargs["time_created"] = time_created

        routing_key = kwargs.get('routing_key', '*')
        kwargs['routing_key'] = routing_key

        properties = kwargs.get('properties', {})
        properties['user_id'] = self.gwuuid
        kwargs['properties'] = pika.BasicProperties(**properties)

        correlation_id = kwargs.get('correlation_id',generateRandom(length=18))
        kwargs['correlation_id'] = correlation_id
        kwargs['correlation_type'] = "direct_send"

        self.PFactory.sendMessage(**kwargs)

    def generateRequest(self, **kwargs):
        """
        Generates a standard request, need to call "sendDirectMessage" to send the request. This function is
        currently only used by other libraries and shouldn't be called by modules.

        **Usage**:

        .. code-block:: python

           requestData = {
               "exchange_name"  : "gw_config",
               "source"        : "yombo.gateway.lib.configurationupdate",
               "destination"   : "yombo.server.configs",
               "callback" : self.amqpDirectIncoming,
               "body"          : {
                 "DataType"        : "Object",
                 "Request"         : requestContent,
               },
               "request_type"   : request_type,
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

        requestID = generateRandom(length=12)

        requestmsg = {
            "exchange_name"    : exchange_name,
            "routing_key"      : '*',
            "body"             : body,
            "properties" : {
                "correlation_id" : requestID,
                "user_id"        : self.gwuuid,
                "headers"        : {
                    "Source"        : source + ":" + self.gwuuid,
                    "Destination"   : destination,
                    "Type"          : "Request",
                    "RequestType"   : request_type,
                    },
                },
            "callback"          : callback,
            }
        return requestmsg

    def disconnect(self):
        """
        Disconnect from the Yombo AMQP service, and tell the connector to not reconnect.
        """
        self.PFactory.stopTrying()
        self.myreactor.disconnect()

    def disconnected(self):
        """
        Function is called when the Gateway is disconnected from the AMQP service.
        """
        logger.info("Disconnected from Yombo service.")
        self.PFactory.fullyConnected = False  # connected to AMQP, and ready to send messages.
        self._connected = False  # connected to AMQP, and ready to send messages.

#        self._connecting = True

    def amqpToMessage(self, deliver, properties, amqp):
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
                    "Source"        : message.msgOrigin,
                    "Destination"   : message.msgDestination,
                    "Type"          : "Message",
                    },
                },
            "callback"          : None
            }
