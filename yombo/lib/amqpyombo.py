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
#try: import simplejson as json
#except ImportError: import json
import json

try:  #prefer to talk in msgpack, if available.
    import msgpack
    HASMSGPACK = True
except ImportError:
    HASMSGPACK = False

import pika
from pika import spec
from pika import exceptions
from pika.adapters import twisted_connection

from twisted.internet.defer import inlineCallbacks
from twisted.internet import ssl, protocol, defer, reactor
from twisted.python import log
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.helpers import getConfigValue, setConfigValue, generateRandom, sleep
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
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
        logger.info("In PikaProtocol connected")
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

#        gwuuid = getConfigValue("core", "gwuuid")
        self.factory.connected()

    def close(self):
        logger.info("In PikaProtocol close - trying to close!!!!!!!!!!!")
        self.channel.close()

    @inlineCallbacks
    def register_exchange(self, **kwargs):
        """
        Register a new exchange with the server.
        """
        logger.info("In PikaProtocol register_exchange")
        self.amqp_exchanges.append(kwargs)
        if self.connected:
            yield self.setup_register_exchange(**kwargs)

    @inlineCallbacks
    def setup_register_exchange(self, **kwargs):
        """
        Sets up the actual queue.
        """
        logger.info("In PikaProtocol setup_register_exchange %s" % kwargs)
        yield self.channel.exchange_declare(exchange=kwargs['exchange_name'], type=kwargs['exchange_type'], durable=kwargs['exchange_durable'], auto_delete=kwargs['exchange_auto_delete'])


    @inlineCallbacks
    def register_queue(self, **kwargs):
        """
        Register a new queue. Allows libraries to setup queues.
        """
        logger.info("In PikaProtocol register_queue %s" % kwargs)
        self.amqp_queues.append(kwargs)
        if self.connected:
            yield self.setup_register_queue(**kwargs)

    @inlineCallbacks
    def setup_register_queue(self, **kwargs):
        """
        Sets up the actual queue.
        """
        logger.info("In PikaProtocol setup_register_queue %s" % kwargs)

        yield self.channel.queue_declare(queue=kwargs['queue_name'], durable=kwargs['queue_durable'])

    @inlineCallbacks
    def register_queue_bind(self, **kwargs):
        """
        Bind to a queue
        """
        logger.info("In PikaProtocol register_queue_bind %s" % kwargs)
        self.amqp_queue_bind.append(kwargs)
        if self.connected:
            yield self.setup_register_queue_bind(**kwargs)

    def setup_register_queue_bind(self, **kwargs):
        """
        Sets up the actual binding.
        """
        logger.info("In PikaProtocol setup_register_queue_bind %s" % kwargs)
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
        logger.info("In PikaProtocol _read_item: item:%s queue_no_ack: %s  callback: %s" % (item, queue_no_ack, callback))
        d = queue.get()
        d.addCallback(self._read_item, queue, queue_no_ack, callback)
        d.addErrback(self._read_item_err)
        (channel, deliver, props, msg,) = item

        log.msg('%s (%s): %s' % (deliver.exchange, deliver.routing_key, repr(msg)), system='Pika:<=')

        try:
          deliver, propers, msg = self.validate_incoming(deliver, props, msg)
        except YomboWarning as e:
          logger.debug("Validate_incoming is bad: %s" % e)
          if not queue_no_ack:
            logger.debug("Sending NACK due to invalid request. Tag: %s" % deliver.delivery_tag)
            channel.basic_nack(deliver.delivery_tag, False, False)
        else:
          logger.warn('Calling callback: %s' % callback)

          d = defer.maybeDeferred(callback, deliver, props, msg)
          if not queue_no_ack:
            logger.trace("ACK: Activating delivery tag: %s" % deliver.delivery_tag)
            d.addCallbacks(
                lambda _: channel.basic_ack(deliver.delivery_tag),
                lambda _: channel.basic_nack(deliver.delivery_tag, False, False)
            )

    def _read_item_err(self, error):
        logger.info("In PikaProtocol _read_item_err: %s" % error)

    def send(self):
        """
        Sends a message to Yombo Services. If offline, messages will be queued
        and sent when connected.
        #TODO: Add timestamp to a message and check against TTL. Ensure message
          isn't expired before being sent.
        """
        logger.trace("In PikaProtocol send")
        if self.connected:
            while len(self.factory.queued_messages) > 0:
                message = self.factory.queued_messages.pop(0)
                self.send_message(**message)

    @inlineCallbacks
    def send_message(self, **kwargs):
        """
        Send a single message.
        """
        logger.info("In PikaProtocol send_message: %s" % kwargs)
        log.msg('%s (%s) (%s): %s' % (kwargs['exchange_name'], kwargs['routing_key'], kwargs['properties'], repr(kwargs['body'])), system='Pika:=>')
#        prop = spec.BasicProperties(delivery_mode=2)
        try:
            yield self.channel.basic_publish(exchange=kwargs['exchange_name'], routing_key=kwargs['routing_key'], body=kwargs['body'], properties=kwargs['properties'])
        except Exception as error:
            logger.warn('Error while sending message: %s' % error)

    def validate_incoming(self, deliver, props, msg):
        logger.info("validate_incoming: %s" % msg)
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

        if props.correlation_id != None and not isinstance(props.correlation_id, basestring):
            raise YomboWarning("correlation_id must be string is present.")
        logger.info('validate good')
        return deliver, props, msg

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
    name = 'AMQP:Factory'
    AMQPYombo = None   #AMQPYombo Library
#    protocol = PikaProtocol

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
        self.client = None
        self.queued_messages = []
        self.exchange_list = []
        self.queue_list = []
        self.queue_bind_list = []
        self.consumer_list = []

    def startedConnecting(self, connector):
        logger.trace("In PikaFactory startedConnecting")

    def buildProtocol(self, addr):
        logger.trace("In PikaFactory buildProtocol")
        self.resetDelay()
        self.client = PikaProtocol(self)
        self.client.factory = self
        self.client.ready.addCallback(self.client.connected)
        return self.client

    def connected(self):
        self.AMQPYombo.connected()

#    def respond(self, msg):
#        logger.trace("respond: %s", msg)

    def close(self):
        logger.debug("In PikaFactory close ########################")
        self.client.close()

    def clientConnectionLost(self, connector, reason):
        logger.debug("In PikaFactory clientConnectionLost. Reason: %s" % reason)
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        logger.debug("In PikaFactory clientConnectionFailed. Reason: %s" % reason)
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def send_message(self, **kwargs):
        logger.info("In PikaFactory send_message")

        if HASMSGPACK:
            kwargs['body'] = msgpack.dumps(kwargs['body'])
            kwargs['properties'].content_type = "application/msgpack"
        else:
            kwargs['body'] = json.dumps(kwargs['body'])
            kwargs['properties'].content_type = "application/json"

        self.queued_messages.append((kwargs))
        logger.info("In PikaFactory send_message client: %s" % self.client)
        if self.client is not None:
            logger.info("In PikaFactory send_message client is not none")
            self.client.send()


    def register_exchange(self, **kwargs):
        """
        Configure an exchange.
        """
        logger.trace("In PikaFactory register_exchange %s" % kwargs)
        self.exchange_list.append(kwargs)
        if self.client is not None:
            self.client.register_exchange(**kwargs)

    def register_queue(self, **kwargs):
        """
        Configure a queue.
        """
        logger.trace("In PikaFactory register_queue %s" % kwargs)
        self.queue_list.append(kwargs)
        if self.client is not None:
            self.client.register_queue(**kwargs)

    def register_queue_bind(self, **kwargs):
        """
        Binds a queue to an exchange.
        """
        logger.trace("in PikaFactory register_queue_bind: %s" % kwargs)
        self.queue_bind_list.append(kwargs)
        if self.client is not None:
            self.client.register_queue_bind(**kwargs)

    def register_consumer(self, **kwargs):
        """
        Consumes a queue
        """
        logger.info("in PikaFactory register_consumer: %s" % kwargs)
        self.consumer_list.append(kwargs)
        if self.client is not None:
            self.client.register_consumer(**kwargs)

class AMQPYombo(YomboLibrary):
    """
    Yombo library to aandle connection to RabbitMQ.
    """
    def _init_(self, loader):
        logger.trace("In AMQPYombo _init_")
        self.loader = loader
        self._connecting = False
        self._connected = False  # connected to AMQP
        self.fullyConnected = False  # connected to AMQP, and ready to send messages.
        self.PFactory = None
        self.user_id = "gw_" + getConfigValue("core", "gwuuid")
        self.startupResponseID = generateRandom(length=12)
        self.callbacks = {} # register callbacks to local gateway modules
        self.queued_messages = []  # for other libraries/modules

        self.connect()

    def _load_(self):
        logger.info("In AMQPYombo _load_")

        request = {
          "Request": [
            {
            "RequestCommand"    : "startup",
            "LocalIPAddress"    : getConfigValue("core", "localipaddress"),
            "ExternalIPAddress" : getConfigValue("core", "externalipaddress"),
            }
          ]
        }

        message = {"exchange_name"    : "gw_config",
                   "routing_key"      : '*',
                   "body"             : request,
                   "properties" : {
                       "correlation_id" : self.startupResponseID,
                       "user_id"        : self.user_id
                       }
                  }

        message['properties'] = pika.BasicProperties(**message['properties'])
        logger.info("In AMQPYombo _load_: message: %s" % message)
        self.PFactory.send_message(**message)

    @defer.inlineCallbacks
    def _start_(self):
        yield sleep(2)
        register = {
                    "queue_name"           : self.user_id,
                    "queue_no_ack"         : False,
                    "callback"             : self.incoming,
                   }
        self.PFactory.register_consumer(**register)
        logger.info("4")

    def _stop_(self):
        logger.trace("In AMQPYombo close.")
        self.PFactory.close()

    def _unload_(self):
        logger.debug("Disonnecting due to unload.")
#        if self._connection != None:
#            self.disconnect()

    def incoming(self, deliver, properties, message):
        """
        Incoming from Yombo AMQP server.
        """
        logger.info("deliver (%s), props (%s), message (%s)" % (deliver, properties, message,))
        logger.info("properties.user_id: %s" % properties.user_id)
#'{"Message": "Ok", "Code": 200, ' \
#'"Response": {"Locator": "Amqp", "LocatorType": "Object", "Amqp": {"ResponseLevel": "Public", "Response": "Pong"}}}'
        logger.info("message: %s" % message)
        if message['Type'] == 'Response': # lets handle a response to a previous request
            logger.info("incoming1111")
            locator = message['Response']['Locator']
            if message['Response']['LocatorType'] == 'Object': # a single response
                logger.info("incoming2222")
                self.incomingResponse(deliver, properties, locator, message['Response'][locator])
            elif message['Response']['LocatorType'] == 'Objects': # multiple responses
                for response in message['Response'][locator]:
                    self.incomingResponse(deliver, properties, locator, response)


    def incomingResponse(self, deliver, properties, locator, response):
        logger.debug("incomingResponse")
        if locator == "Amqp":
            if self.startupResponseID == properties.correlation_id:
                self.fullyConnected = True
                self.check_send_messages()

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
        creds=pika.PlainCredentials(self.user_id, getConfigValue("core", "gwhash"))
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


    def send_message(self, **kwargs):

        logger.info("library:send_message")
        exchange_name = kwargs.get('exchange_name', None)
        body = kwargs.get('body', None)
        queue_routing_key = kwargs.get('queue_routing_key', '*')

        properties = kwargs.get('properties', {})
        properties['user_id'] = self.user_id

        if exchange_name == None or body == None:
            raise YomboWarning("AMQP.send_message is missing a value...")

        logger.info("library:send_mssage:properties: %s" % kwargs['properties'])
        kwargs['properties'] = pika.BasicProperties(**properties)
        logger.info("library:send_mssage:properties: %s" % kwargs['properties'])
        kwargs['queue_routing_key'] = queue_routing_key

        self.queued_messages.append((kwargs))
        self.check_send_messages()

    def check_send_messages(self):
        if self.fullyConnected:
            logger.info("In AMQPLibrary check_send_messages and fully connected")
            while len(self.queued_messages) > 0:
                message = self.factory.queued_messages.pop(0)
                self.PFactory.send_message(**message)
        else:
            logger.info("In AMQPLibrary check_send_messages, not connected. Calling later.")
            reactor.callLater(0.5, self.check_send_messages())


    def disconnect(self):
        self.GCfactory.stopTrying()
        self.myreactor.disconnect()

    def disconnected(self):
        logger.info("Disconnected from Yombo service.!!!!!!!!!!!!!!!!!!!!!!!!")
        self.fullyConnected = False  # connected to AMQP, and ready to send messages.
        self._connected = False  # connected to AMQP, and ready to send messages.

#        self._connecting = True

    def message(self, message):
        """
        Yombo Gateway sends most messages here for delivery externally.

        If the message is for us, don't forward.  Otherwise, check to make sure
        destination is valid before sending to Yombo servers.
        """

        #TODO: Implement this!
        forUs = message.checkDestinationAsLocal()

        if forUs == False:
            logger.warning("asdf")
 #           self._connection.sendMessage(message.dumpToExternal())
        else:
            logger.warning("Not routing message to YomboSvc since the message is for us.: %s", message.dump())

