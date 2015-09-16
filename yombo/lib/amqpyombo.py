#cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
Establishes a connection the Yombo servers. Configuration updates are sent,
device logs (if enabled), statistics (if enabled), and various other features
can use this data channel. The gateawy can also recieve commands from Yombo
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
try: import simplejson as json
except ImportError: import json
from collections import deque
from time import time
from datetime import datetime

try:  #prefer to talk in msgpack, if available.
    import msgpack
    HASMSGPACK = True
except ImportError:
    HASMSGPACK = False

import pika
from pika import spec
from pika import exceptions
from pika.adapters import twisted_connection

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet import ssl, protocol, defer, reactor
from twisted.python import log
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboCritical, YomboMessageError
from yombo.core.helpers import getConfigValue, setConfigValue, generateRandom, sleep
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
from yombo.core.maxdict import MaxDict
from yombo.core.message import Message

logger = getLogger('library.AMQPYombo')

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
        super(PikaProtocol, self).__init__(self.factory.AMQPYombo.parameters)
        self.amqp_exchanges = []
        self.amqp_queues = []
        self.amqp_queue_bind = []
        self.amqp_consumers = []

    @inlineCallbacks
    def connected(self, connection):
        """
        Is called when connected to Yombo AMQP server.

        :param connection: The connection to Yombo AMQP server.
        """
        logger.debug("In PikaProtocol connected")
        self.connection = connection
        self.channel = yield connection.channel()

        def closeConnection(channel, replyCode, replyText):
            logger.info("!!!!!!!!!!Trying to nicely close connection!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            connection.close()
        self.channel.add_on_close_callback(closeConnection)

        yield self.channel.basic_qos(prefetch_count=PREFETCH_COUNT)
        self.connected = True
        for exchange in self.factory.exchange_list:
            yield self.setup_register_exchange(**exchange)
        for queue in self.factory.queue_list:
            yield self.setup_register_queue(**queue)
        for queue_bind in self.factory.queue_bind_list:
            yield self.setup_register_queue_bind(**queue_bind)
        for consumer in self.factory.consumer_list:
            yield self.setup_register_consumer(**consumer)
        self.send()
        self.factory.connected()

    def close(self):
        logger.debug("In PikaProtocol close - trying to close!!!!!!!!!!!")
        self.channel.close()

    @inlineCallbacks
    def register_exchange(self, **kwargs):
        """
        Register a new exchange with the server.
        """
        logger.debug("In PikaProtocol register_exchange")
        self.amqp_exchanges.append(kwargs)
        if self.connected:
            yield self.setup_register_exchange(**kwargs)

    @inlineCallbacks
    def setup_register_exchange(self, **kwargs):
        """
        Sets up the actual queue.
        """
        yield self.channel.exchange_declare(exchange=kwargs['exchange_name'], type=kwargs['exchange_type'], durable=kwargs['exchange_durable'], auto_delete=kwargs['exchange_auto_delete'])

    @inlineCallbacks
    def register_queue(self, **kwargs):
        """
        Register a new queue. Allows libraries to setup queues.
        """
        logger.debug("In PikaProtocol register_queue")
        self.amqp_queues.append(kwargs)
        if self.connected:
            yield self.setup_register_queue(**kwargs)

    @inlineCallbacks
    def setup_register_queue(self, **kwargs):
        """
        Sets up the actual queue.
        """
        yield self.channel.queue_declare(queue=kwargs['queue_name'], durable=kwargs['queue_durable'])

    @inlineCallbacks
    def register_queue_bind(self, **kwargs):
        """
        Bind to a queue
        """
        logger.info("In PikaProtocol register_queue_bind")
        self.amqp_queue_bind.append(kwargs)
        if self.connected:
            yield self.setup_register_queue_bind(**kwargs)

    def setup_register_queue_bind(self, **kwargs):
        """
        Sets up the actual binding.
        """
        logger.info("In PikaProtocol setup_register_queue_bind")
        self.channel.queue_bind(exchange=kwargs['exchange_name'],
                   queue=kwargs['queue_name'],
                   routing_key=kwargs['queue_routing_key'])

    @inlineCallbacks
    def register_consumer(self, **kwargs):
        """
        Bind to a queue
        """
        self.amqp_consumers.append(kwargs)
        if self.connected:
            yield self.setup_register_consumer(**kwargs)

    @inlineCallbacks
    def setup_register_consumer(self, **kwargs):
        """
        Sets up the actual binding.
        """
        (queue, consumer_tag,) = yield self.channel.basic_consume(queue=kwargs['queue_name'], no_ack=kwargs['queue_no_ack'])
        d = queue.get()
        d.addCallback(self._read_item, queue, kwargs['queue_no_ack'], kwargs['callback'])
        d.addErrback(self._read_item_err)
        yield defer.succeed(None)

    def _read_item(self, item, queue, queue_no_ack, callback):
        """
        Callback function which is called when an item is read. Forwards the item received
        to the correct callback method.
        """
        logger.debug("In PikaProtocol _read_item")
        d = queue.get()
        d.addCallback(self._read_item, queue, queue_no_ack, callback)
        d.addErrback(self._read_item_err)
        (channel, deliver, props, msg,) = item
        if props.correlation_id in self.factory.sentCorrelationIDs:
            self.factory.sentCorrelationIDs[props.correlation_id]['time_recieved'] = datetime.now()

        log.msg('%s (%s): %s' % (deliver.exchange, deliver.routing_key, repr(msg)), system='Pika:<=')

        try:
          deliver, props, msg = self.validate_incoming(deliver, props, msg)
        except YomboWarning as e:
          logger.info("_read_item is bad: %s" % e)
          if not queue_no_ack:
            logger.debug("Sending NACK due to invalid request. Tag: %s" % deliver.delivery_tag)
            channel.basic_nack(deliver.delivery_tag, False, False)
        except Exception as e:
          logger.info("Some other exception: %s" % e)
        else:
          logger.trace('Calling callback: %s' % callback)

          d = defer.maybeDeferred(callback, deliver, props, msg)
          if not queue_no_ack:
            logger.trace("ACK: Activating delivery tag: %s" % deliver.delivery_tag)
            d.addCallback(self._basic_ack, channel, deliver.delivery_tag)
            d.addErrback(self._basic_nack, channel, deliver.delivery_tag)


    def _basic_ack(self, tossaway, channel, tag):
        logger.info("In ack: %s" % tag)
        channel.basic_ack(tag)

    def _basic_nack(self, error, channel, tag):
        logger.info("Error: %s" % error)
        logger.info("In nack: %s" % tag)
        channel.basic_nack(tag, False, False)


    def validate_incoming(self, deliver, props, msg):
        logger.trace("validate_incoming: %s" % props)
        if props.correlation_id == None or not  isinstance(props.correlation_id, basestring):
            raise YomboWarning("correlation_id must be present and be a string.")

        if props.user_id == None:
            raise YomboWarning("user_id missing.")
        if props.content_type == None:
            raise YomboWarning("content_type missing.")
        if props.content_type != 'text/plain' and props.content_type != 'application/msgpack' and  props.content_type != 'application/json':
            logger.warn('Error with contentType!')
            raise YomboWarning("Content type must be 'msgpack', 'string' or 'json'. Got: " + props.content_type)
        if props.content_type == 'application/json':
            if self.is_json(msg):
                msg = json.loads(msg)
            else:
                raise YomboWarning("Recieved msg reported json, but isn't.")
        elif props.content_type == 'application/msgpack':
            if self.is_msgpack(msg):
                msg = msgpack.loads(msg)
            else:
                raise YomboWarning("Recieved msg reported msgpack, but isn't.")

        # do nothing on requests for now.... in future if we ever accept requests, we will.
        if props.headers['Type'] == 'Request':
            raise YomboWarning("Currently not accepting requests.")
        # if a response, lets make sure it's something we asked for!
        elif props.headers['Type'] == "Response":
            if props.correlation_id not in self.factory.sentCorrelationIDs:
                logger.info("################# list of ids: %s " % self.factory.sentCorrelationIDs)
                raise YomboWarning("Recieved request %s, but never asked for it." % props.correlation_id)

        logger.trace('validate good')
        return deliver, props, msg

    def _read_item_err(self, error):
        logger.debug("In PikaProtocol _read_item_err: %s" % error)

    def send(self):
        """
        Sends a message to Yombo Services. If offline, messages will be queued
        and sent when connected.
        #TODO: Add timestamp to a message and check against TTL. Ensure message
          isn't expired before being sent.
        """
        logger.trace("In PikaProtocol send %s" % self.connected)
        if self.connected:
            while len(self.factory.queued_messages) > 0:
                message = self.factory.queued_messages.pop(0)
                self.send_message(**message)

    @inlineCallbacks
    def send_message(self, **kwargs):
        """
        Send a single message.
        """
        logger.trace("In PikaProtocol send_message a: %s" % kwargs['properties'].correlation_id)
#        prop = spec.BasicProperties(delivery_mode=2)


        if HASMSGPACK:
            kwargs['body'] = msgpack.dumps(kwargs['body'])
            kwargs['properties'].content_type = "application/msgpack"
        else:
            kwargs['body'] = json.dumps(kwargs['body'])
            kwargs['properties'].content_type = "application/json"

        try:
            if kwargs['properties'].correlation_id in self.factory.sentCorrelationIDs:
                self.factory.sentCorrelationIDs[kwargs['properties'].correlation_id]['time_sent'] = datetime.now()
            yield self.channel.basic_publish(exchange=kwargs['exchange_name'], routing_key=kwargs['routing_key'], body=kwargs['body'], properties=kwargs['properties'])
        except Exception as error:
            logger.warn('Error while sending message: %s' % error)

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
    sentCorrelationIDs = MaxDict(200) #correlate requests with responses
    AMQPProtocol = None #

    def __init__(self, AMQPYombo):
        logger.trace("In PikaFactory __init__")
        self._Name = "PikaFactory"
        self._FullName = "yombo.server.lib.PikaFactory"
        # DO NOT CHANGE THESE!  Mitch Schwenk @ yombo.net
        # Reconnect sort-of fast, but random. ~25 second max wait
        # This is set incase a server reboots, don't DDOS our servers!
        self.initialDelay = 0.1
        self.jitter = 0.2
        self.factor = 1.82503912
        self.maxDelay = 25 # this puts retrys around 17-26 seconds

        self.AMQPYombo = AMQPYombo
        self.queued_messages = []
        self.exchange_list = []
        self.queue_list = []
        self.queue_bind_list = []
        self.consumer_list = []
        self.fullyConnected = False  # connected to AMQP, and ready to send messages.   #gw
        self.startupRequestID = generateRandom(length=12) #gw
        self.incoming_queue = []

    def startedConnecting(self, connector):
        logger.trace("In PikaFactory startedConnecting")

    def buildProtocol(self, addr):
        logger.trace("In PikaFactory buildProtocol")
        self.resetDelay()
        self.AMQPProtocol = PikaProtocol(self)
        self.AMQPProtocol.factory = self
        self.AMQPProtocol.ready.addCallback(self.AMQPProtocol.connected)
        return self.AMQPProtocol

    @defer.inlineCallbacks
    def connected(self):  #gw
        request = {
              "DataType": "Object",
              "Request": {
                    "RequestType":"Startup",
                    "LocalIPAddress"    : getConfigValue("core", "localipaddress"),
                    "ExternalIPAddress" : getConfigValue("core", "externalipaddress"),
              },
            }

        requestmsg = {
            "exchange_name"    : "gw_config",
            "routing_key"      : '*',
            "body"             : request,
            "properties" : {
                "correlation_id" : self.startupRequestID,
                "user_id"        : self.AMQPYombo.gwuuid,
                "headers"        : {
                    "Source"        : "yombo.gateway.lib.amqpyombo:" + self.AMQPYombo.gwuuid,
                    "Destination"   : "yombo.server.amqpyombo",
                    "Type"          : "Request",
                    },
                },
            "callback"          : None,
            "correlation_type"  : "local",
            }

        requestmsg['properties'] = pika.BasicProperties(**requestmsg['properties'])
        self.send_message(**requestmsg)

        yield sleep(0.75)
        register = {
                    "queue_name"           : self.AMQPYombo.gwuuid,
                    "queue_no_ack"         : False,
                    "callback"             : self.incoming,
                   }
        self.register_consumer(**register)


    def incoming(self, deliver, properties, message):
        """
        Incoming from Yombo AMQP server.
        """
        #logger.info("deliver (%s), props (%s), message (%s)" % (deliver, properties, message,))
        logger.debug("do incoming")

        item = {
            "deliver" : deliver,
            "properties" : properties,
            "message" : message,
        }


        # first, lets process a startup complete if available.
        if self.fullyConnected == False:
            if self.startupRequestID == properties.correlation_id:
                if message['Code'] == 200:
                    self.fullyConnected = True
                    logger.info("Fully connected")
                    self.AMQPYombo.connected()
                    self.AMQPProtocol.send()
                else:
                    raise YomboCritical("Yombo Server won't accept our startup request. Reason: %s" % message['Message'])
            else:
                self.incoming_queue.append(item)
            return
        else:
            for queue_item in self.incoming_queue:
                self.do_incoming(queue_item['deliver'], queue_item['properties'], queue_item['message'])
            self.do_incoming(deliver, properties, message)

    def do_incoming(self, deliver, properties, message):
        logger.info("do_incoming item: %s" % message)
        logger.info("message: %d" % message['Code'])
        if message['Code'] != 200:
            raise YomboWarning("Yombo service responsed with code %s: %s" %(message['Code'], message['Message']))

        # A request from somehwere
        if properties.headers['Type'] == 'Request':
            if message['DataType'] == 'Object': # a single response
                self.do_incoming_request(deliver, properties, message['Request'])
            elif message['DataType'] == 'Objects': # An array of responses
                for response in message['Response']:
                    self.do_incoming_request(deliver, properties, response)

        # A response form a library or sepcific module
        elif properties.headers['Type'] == "Response":
            dt = self.sentCorrelationIDs[properties.correlation_id]['time_recieved'] - self.sentCorrelationIDs[properties.correlation_id]['time_sent']
            ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
            logger.info("Message Response time: %s ms" % ms)
            if message['DataType'] == 'Object': # a single response
                logger.debug("incoming3333")
                self.do_incoming_response(deliver, properties, message['Response'])
            elif message['DataType'] == 'Objects': # An array of responses
                for response in message['Response']:
                    self.do_incoming_response(deliver, properties, response)

        # Route to Yombo Message system for delivery.
        elif properties.headers['Type'] == "Message":
            self.AMQPYombo.amqpToMessage(deliver, properties, message)

        # nothing else to do. Bad message!
        else:
            raise YomboWarning("Unknown message type (%s), dropping." % properties.headers['Type'] )

    def do_incoming_response(self, deliver, properties, response):
        """
        Handle incoming responses. If the message gets here, it's in response to a request.
        """
        logger.debug("in do_incoming_response")
        if properties.correlation_id in self.sentCorrelationIDs:
            # Handle messages that were directly sent from an external library.
            if self.sentCorrelationIDs[properties.correlation_id]['correlation_type'] == "direct_send":
                if self.sentCorrelationIDs[properties.correlation_id]['callback'] != None:
                    self.sentCorrelationIDs[properties.correlation_id]['callback'](self.sentCorrelationIDs[properties.correlation_id], deliver, properties, response)
                    return
                else:
                    raise YomboWarning("All direct_send responses must have a callback!")

        raise YomboWarning("Unknown how to deliver message... dropping..")

    def do_incoming_request(self, deliver, properties, response):
        """
        Currently, we don't accept requests.
        """
        pass

    def close(self):
        logger.debug("In PikaFactory close ########################")
        self.AMQPProtocol.close()

    def clientConnectionLost(self, connector, reason):
        logger.debug("In PikaFactory clientConnectionLost. Reason: %s" % reason)
        self.fullyConnected = True
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        logger.debug("In PikaFactory clientConnectionFailed. Reason: %s" % reason)
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def send_message(self, **kwargs):
        logger.debug("In PikaFactory send_message")
        self.sentCorrelationIDs[kwargs['properties'].correlation_id] = {
            "time_created"      : kwargs.get("time_created", datetime.now()),
            'time_sent'         : None,
            "time_received"     : None,
            "callback"          : kwargs['callback'],
            "correlation_type"  : kwargs.get('correlation_type', None),
        }

        self.queued_messages.append((kwargs))
        logger.trace("In PikaFactory send_message client: %s" % self.AMQPProtocol)
        if self.AMQPProtocol is not None:
            self.AMQPProtocol.send()

    def register_exchange(self, **kwargs):
        """
        Configure an exchange.
        """
        logger.trace("In PikaFactory register_exchange %s" % kwargs)
        self.exchange_list.append(kwargs)
        if self.AMQPProtocol is not None:
            self.AMQPProtocol.register_exchange(**kwargs)

    def register_queue(self, **kwargs):
        """
        Configure a queue.
        """
        logger.trace("In PikaFactory register_queue %s" % kwargs)
        self.queue_list.append(kwargs)
        if self.AMQPProtocol is not None:
            self.AMQPProtocol.register_queue(**kwargs)

    def register_queue_bind(self, **kwargs):
        """
        Binds a queue to an exchange.
        """
        logger.trace("in PikaFactory register_queue_bind: %s" % kwargs)
        self.queue_bind_list.append(kwargs)
        if self.AMQPProtocol is not None:
            self.AMQPProtocol.register_queue_bind(**kwargs)

    def register_consumer(self, **kwargs):
        """
        Consumes a queue
        """
        logger.trace("in PikaFactory register_consumer: %s" % kwargs)
        self.consumer_list.append(kwargs)
        if self.AMQPProtocol is not None:
            self.AMQPProtocol.register_consumer(**kwargs)

class AMQPYombo(YomboLibrary):
    """
    Yombo library to aandle connection to RabbitMQ.
    """
    def _init_(self, loader):
        logger.trace("In AMQPYombo _init_")
        self.loader = loader
        self._connecting = False
        self._connected = False  # connected to AMQP
        self.PFactory = None
        self.gwuuid = "gw_" + getConfigValue("core", "gwuuid")
        self.checking_queued_mesasge = False
        self.queued_messages = []  # for other libraries/modules
        self.headerSourceCallbacks = {} # register callbacks to local gateway modules
        self.messageCallbacks = {} # register callbacks to local gateway modules

        self.connect()

    def _load_(self):
        pass

    def _start_(self):
        pass

    def _stop_(self):
        logger.trace("In AMQPYombo close.")
        self.PFactory.close()

    def _unload_(self):
        logger.debug("Disonnecting due to unload.")
#        if self._connection != None:
#            self.disconnect()

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
        logger.trace("in AMQPYombo connect")
        if self._connecting == True:
            logger.trace("Already trying to connect, connect attempt aborted.")
            return
        self._connecting = True

        environment = getConfigValue('server', 'environment', "production")
        if getConfigValue("server", 'hostname', "") != "":
            host = getConfigValue("server", 'hostname')
        else:
            if(environment == "production"):
                host = "svc.yombo.net"
            elif (environment == "staging"):
                host = "svcstg.yombo.net"
            elif (environment == "development"):
                host = "svcdev.yombo.net"
            else:
                host = "svc.yombo.net"

        host = 'projects.yombo.net'
        creds=pika.PlainCredentials(self.gwuuid, getConfigValue("core", "gwhash"))
        self.parameters = pika.ConnectionParameters(
            host=host,
            port=5671,
            virtual_host='yombo',
            heartbeat_interval=120,
            ssl=True,
            credentials=creds
        )
        self.PFactory = PikaFactory(self)

        self.myreactor =  reactor.connectSSL("projects.yombo.net", 5671, self.PFactory,
             ssl.ClientContextFactory())

    def connected(self):
        logger.debug("AMQPYombo connected")
        self._connected = True
        self._connecting = False
        self.timeout_reconnect_task = False
        self.check_send_messages()

    def send_direct_message(self, **kwargs):
        """
        Send a message through AMQP directly. This feature should only be used by libraries for direct access
        to the Yombo Servers. Modules can use this with caution for performance reasons or a specific need to
        bypass the messaging system.
        """
        logger.trace("library:send_direct_message")
        time_created = kwargs.get("time_created", datetime.now())
        kwargs["time_created"] = time_created

        callback = kwargs.get('callback', None)
        if callback == None:
            raise YomboWarning("AMQP.send_message must have a 'callback'")

        exchange_name = kwargs.get('exchange_name', None)
        if exchange_name == None:
            raise YomboWarning("AMQP.send_message must have an 'exchange_name'")

        body = kwargs.get('body', None)
        if body == None:
            raise YomboWarning("AMQP.send_message must have a 'body'")

        queue_routing_key = kwargs.get('queue_routing_key', '*')
        kwargs['queue_routing_key'] = queue_routing_key

        properties = kwargs.get('properties', {})
        properties['user_id'] = self.gwuuid
        kwargs['properties'] = pika.BasicProperties(**properties)

        correlation_id = kwargs.get('correlation_id',generateRandom(length=18))
        kwargs['correlation_id'] = correlation_id
        kwargs['correlation_type'] = "direct_send"

        self.queued_messages.append((kwargs))
        self.check_send_messages()

    def check_send_messages(self):
        logger.trace("check_send_message: %s " % self.PFactory.fullyConnected)
        if self.PFactory.fullyConnected:
            while len(self.queued_messages) > 0:
                message = self.queued_messages.pop(0)
                self.PFactory.send_message(**message)
        elif self.checking_queued_mesasge == False:
            self.checking_queued_mesasge = True
            reactor.callLater(0.5, self._do_check_send_message)

    def _do_check_send_message(self):
        self.checking_queued_mesasge = False
        self.check_send_messages()

    def disconnect(self):
        self.PFactory.stopTrying()
        self.myreactor.disconnect()

    def disconnected(self):
        logger.info("Disconnected from Yombo service.!!!!!!!!!!!!!!!!!!!!!!!!")
        self.PFactory.fullyConnected = False  # connected to AMQP, and ready to send messages.
        self._connected = False  # connected to AMQP, and ready to send messages.

#        self._connecting = True

    def amqpToMessage(self, deliver, properties, amqp):
        """
        Convert an AMQP message to a Yombo Message. If message is a response, it the correlations will be set
        automatically.

        :param deliver:
        :param properties:
        :param message:
        """
        raise YomboWarning("amqpToMesasge - Incoming message routing not implmented")

        if message.checkDestinationAsLocal() != True: # in future, if we become a router, this will change
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


        if message.checkDestinationAsLocal() == False:
            raise YomboMessageError("Tried to send a local message externally. Dropping.")
        if message.validateMsgOriginFull() == False:
            raise YomboMessageError("Full msgOrigin needs full path.")
        if message.validateMsgDestinationFull() == False:
            raise YomboMessageError("Full msgDestination needs full path.")


        request = {
              "DataType": "Object",
              "Request": message.dumpToExternal(),
            }

        source
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
