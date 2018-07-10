# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
All AMQP connetions are managed by this library. To create a new connection use the
:py:meth:`self._AMQP.new() <AMQP.new>` function to create a new connection. This will return a
:class:`AMQPClient` instance which allows for creating exchanges, queues, queue bindings,
and sending/receiving messages.

To learn more about AMQP, see the `RabbitMQ Tutorials <https://www.rabbitmq.com/getstarted.html>`_.

Yombo Gateway interacts with Yombo servers using AMQPYombo which depends on this library.

.. note::

  For developer documentation, see: `AMQP @ Module Development <https://yombo.net/docs/libraries/amqp>`_

.. seealso::

   The :doc:`mqtt library </lib/mqtt>` can connect to MQTT brokers, this a light weight message broker.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2015-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/amqp.html>`_
"""
# Import python libraries
from collections import deque
try:
    from hashlib import sha3_256 as sha256
except ImportError:
    from hashlib import sha256
import pika
from pika.exceptions import ChannelClosed
import sys
import traceback
from time import time

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet import ssl, protocol, defer
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboCritical
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import random_string, unicode_to_bytes
import collections

logger = get_logger('library.amqp')


class AMQP(YomboLibrary):
    """
    Base, or root class that manages all AMQP connections.
    """
    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo amqp library"

    def _init_(self, **kwargs):
        """
        Loads previously saved message information.

        :param kwargs:
        :return:
        """
        self.client_connections = {}
        self.messages_processed = None  # Track incoming and outgoing messages. Meta data only.
        self.message_correlations = None  # Track various bits of information for sent correlation_ids.

        self.init_deferred = Deferred()
        self.load_meta_data()
        return self.init_deferred

    def _start_(self, **kwargs):
        """
        Sets up the loop that cleans out old messages. These are stored for a period of time
        for reference and security.

        :param kwargs:
        :return:
        """
        self.clean_correlation_ids_loop = LoopingCall(self.clean_correlation_ids)
        self.clean_correlation_ids_loop.start(36)

    def _stop_(self, **kwargs):
        """
        Cleans up any pending deferreds.

        :return:
        """
        if self.init_deferred is not None and self.init_deferred.called is False:
            self.init_deferred.callback(1)  # if we don't check for this, we can't stop!

    def _unload_(self, **kwargs):
        """
        Force disconnects all AQMP clients.

        :param kwargs:
        :return:
        """
        self._local_log("debug", "AMQP::_unload_")
        for client_id, client in self.client_connections.items():
            if client.is_connected:
                try:
                    client.disconnect()  # this tells the factory to tell the protocol to close.
                except:
                    pass

    @inlineCallbacks
    def load_meta_data(self):
        """
        Loads previous message data stored in SQLDict.
        :return:
        """
        self.messages_processed = yield self._AMQP._SQLDict.get(
            self,
            "client_connections",
            max_length=400
        )

        self.message_correlations = yield self._AMQP._SQLDict.get(
            self,
            "send_correlation_ids",
            serializer=self.message_correlations_serializer,
            unserializer=self.message_correlations_unserializer,
            max_length=400
        )

        self.init_deferred.callback(10)

    def message_correlations_serializer(self, correlation):
        """
        Serializes message data for storage into SQLDict.

        :param correlation:
        :return:
        """
        if 'correlation_persistent' in correlation and correlation['correlation_persistent'] is False:
            raise YomboWarning("We don't save non-persistent items...")
        #todo: using sys or function tools to get the module name and function name to re-create a link.
        correlation['callback'] = None
        correlation['amqpyombo_callback'] = None
        return correlation

    def message_correlations_unserializer(self, correlation):
        """
        Unserializes message data.

        :param correlation:
        :return:
        """
        output = correlation.copy()
        # print("output: %s" % output)
        if output['callback_component_type'] is not None and \
            output['callback_component_type_name'] is not None and \
            output['callback_component_type_function'] is not None:
            try:
                output['callback'] = self._AMQP._Loader.find_function(output['callback_component_type'],
                                                        output['callback_component_type_name'],
                                                        output['callback_component_type_function'] )
            except:
                pass
        return output

    def clean_correlation_ids(self):
        """
        Clean up the tracking dictionaries for messages sent and messages processed.
        """
        for correlation_id in list(self.message_correlations.keys()):
            if self.message_correlations[correlation_id]['correlation_at'] < (time() - (60*10)):
                del self.message_correlations[correlation_id]

        for msg_id in list(self.messages_processed.keys()):
            if self.messages_processed[msg_id]['msg_at'] < (time() - (60*5)):
                    del self.messages_processed[msg_id]

    def _local_log(self, level, location="", msg=""):
        logit = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    def new(self, hostname=None, port=5671, virtual_host=None, username=None, password=None,
            use_ssl=True, connected_callback=None, disconnected_callback=None, error_callback=None,
            client_id=None, keepalive=60, prefetch_count=10, critical=False):
        """
        Creates a new :py:class:AMQPClient instance. It will not auto-connect, just simply call the connect method
        when you're ready for the instance to start connecting. It will continue to attempt to connect if connection
        is not initially made or connection is dropped. It implements an auto-backup feature so as not to overload
        the server.  For example, it will make connection attempts pretty fast, but will increase the rate of
        connection attempts of time.

        :param hostname: String (required) - IP address or hostname to connect to.
        :param port: Int (required) - Port number to connect to.
        :param virtual_host: String (required) - AMQP virutal host name to connect to.
        :param username: String (Default = None) - Username to connect as. If None, will use the Yombo system username.
          Use "" to not use a username & password.
        :param password: String (Default = None) - Pasword to to connect with. If None, will use the Yombo system
          username. Use "" to not use a password.
        :param use_ssl: bool (Default = True) - Use SSL when attempting to connect to server.
        :param connected_callback: method - If you want a function called when connected to server.
        :param disconnected_callback: method - If you want a function called when disconnected from server.
        :param error_callback: method - A function to call if something goes wrong.
        :param client_id: String (default - random) - A client id to use for logging.
        :param keepalive: Int (default 600) - How many seconds a ping should be performed if there's not recent
          traffic.
        :param prefetch_count: Int (default 10) - How many outstanding messages the client should have at any
          given time.
        :return:
        """
        if client_id is None:
            client_id = random_string(length=10)

        if client_id in self.client_connections:
            raise YomboWarning ("client_id must be unique. Got: %s" % client_id, 200, 'MQTT::new', 'mqtt')

        if hostname is None:
            raise YomboWarning("New AMQP client must has a servername or IP to connect to.", 200, 'new', 'AMQP')

        if port is None:
            raise YomboWarning("New AMQP client must has a port number to connect to.", 200, 'new', 'AMQP')

        if username is "" or password is "":
            username = None
            password = None

        if virtual_host is None:
            raise YomboWarning("New AMQP client must has a virtual host to connect to.", 200, 'new', 'AMQP')

        if use_ssl is None:
            raise YomboWarning("New AMQP client must have use_ssl set as True or False..", 200, 'new', 'AMQP')

        if connected_callback is not None:
            if isinstance(connected_callback, collections.Callable) is False:
                raise YomboWarning("If incoming_callback is set, it must be be callable.")

        if disconnected_callback is not None:
            if isinstance(disconnected_callback, collections.Callable) is False:
                raise YomboWarning("If incoming_callback is set, it must be be callable.")

        if error_callback is not None:
            if isinstance(error_callback, collections.Callable) is False:
                raise YomboWarning("If error_callback is set, it must be be callable.")

        self.client_connections[client_id] = AMQPClient(self, client_id, hostname, port, virtual_host, username,
                password, use_ssl, connected_callback, disconnected_callback, error_callback, keepalive, prefetch_count,
                critical)
        return self.client_connections[client_id]


class AMQPClient(object):
    def __init__(self, _AMQP, client_id, hostname, port, virtual_host, username, password, use_ssl,
                 connected_callback, disconnected_callback, error_callback, keepalive, prefetch_count,
                 critical_connection):
        """
        Abstracts much of the tasks for AMQP handling. Yombo Gateway libraries and modules should primarily interact
        with these methods.

        Note: Check with your AMQP host to validate you are have permissions before performing many of these tasks.
        Many times, the server will disconnect the session if a request is being made and don't have permission.

        :param _AMQP: Class - A pointer to AMQP library.
        :param client_id: String (default - random) - A client id to use for logging.
        :param hostname: String (required) - IP address or hostname to connect to.
        :param port: Int (required) - Port number to connect to.
        :param virtual_host: String (required) - AMQP virutal host name to connect to.
        :param username: String (Default = None) - Username to connect as. If None, will use the Yombo system username.
          Use "" to not use a username & password.
        :param password: String (Default = None) - Pasword to to connect with. If None, will use the Yombo system
          username. Use "" to not use a password.
        :param use_ssl: bool (Default = True) - Use SSL when attempting to connect to server.
        :param connected_callback: method - If you want a function called when connected to server.
        :param disconnected_callback: method - If you want a function called when disconnected from server.
        :param error_callback: method - A function to call if something goes wrong.
        :param keepalive: Int (default 600) - How many seconds a ping should be performed if there's not recent
          traffic.
        :param prefetch_count: Int (default 10) - How many outstanding messages the client should have at any
          given time.
        """
        self._FullName = 'yombo.gateway.lib.AMQP.AMQPClient'
        self._Name = 'AMQP.AMQPClient'

        self._AMQP = _AMQP
        self.client_id = client_id
        self.hostname = hostname
        self.port = port
        self.virtual_host = virtual_host
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.keepalive = keepalive
        self.prefetch_count = prefetch_count
        self.critical_connection = critical_connection

        self.connected_callback = connected_callback
        self.is_connected = False
        self.disconnected_callback = disconnected_callback
        self.error_callback = error_callback

        self._connecting = False
        self._disconnecting = False
        self.pika_factory = PikaFactory(self)
        self.pika_factory.noisy = False  # turn off Starting/stopping message

        pika_params = {
            'host': hostname,
            'port': port,
            'virtual_host': virtual_host,
            'heartbeat_interval': keepalive,
            'ssl': use_ssl,  # ignored, but we keep it here anyways.
        }

        if username is not None and password is not None:
            self.pika_credentials=pika.PlainCredentials( username, password )
            pika_params['credentials'] = self.pika_credentials

        self.pika_parameters = pika.ConnectionParameters(**pika_params)

    def _local_log(self, level, location="", msg=""):
        """
        Simple logger tool.
        :param level:
        :param location:
        :param msg:
        :return:
        """
        logit = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    def connect(self):
        """
        Called when ready to connect.
        """
        self._local_log("debug", "AMQP::connect")

        if self._connecting is True:
            logger.debug(
                    "AMQP Client: {client_id} - Already trying to connect, connect attempt aborted.",
                    client_id=self.client_id)
            return
        self._connecting = True
        if self.use_ssl:
            self.myreactor = reactor.connectSSL(self.hostname, self.port, self.pika_factory, ssl.ClientContextFactory())
        else:
            self.myreactor = reactor.connectTCP(self.hostname, self.port, self.pika_factory)

    def connected(self):
        """
        Called by pika_factory.incoming() after successfully completed negotiation. It's already been connected
        for a while, but now it's connected as far as the library is concerned.
        """
        logger.debug("######## AMQPClient::connected 1")
        self._local_log("debug", "AMQP Client: {client_id} - Connected")
        self._connecting = False
        self.is_connected = True
        self.timeout_reconnect_task = False

        if self.connected_callback:
            self.connected_callback()

    def disconnect(self):
        """
        Disconnect from the AMQP service, and tell the connector to not reconnect.
        """
        if self._disconnecting is True or self.is_connected is False:
            return
        self._disconnecting = True

        logger.debug("AMQPClient going to disconnect for client id: {client_id}", client_id=self.client_id)
        self.pika_factory.stopTrying()
        self.pika_factory.close()

    def disconnected(self, reconnect=True):
        """
        Function is called when the Gateway is disconnected from the AMQP service.
        """
        logger.info("AMQP Client {client_id} disconnected. Will usually auto-reconnected.", client_id=self.client_id)
        self.is_connected = False
        if self.disconnected_callback:
            self.disconnected_callback()

    def register_exchange(self, exchange_name, exchange_type, exchange_durable=None, register_persist=None,
                          exchange_auto_delete=None):
        """
        Register an exchange with the server.

        For details on these actions, please review any AMQP guide.

        :param exchange_name: String (required) - Name of exchange to create
        :param exchange_type: String (required) - Type of AMQP exchange. One of: direct, fanout, topic.
        :param exchange_durable: Bool (default = False) - If the exchange should persist data to disk.
        :param register_persist: Bool (default = True) - If exchange should be re-created on re-connect.
        :param exchange_auto_delete: Bool (default = False) - If the exchange should auto delete when last
           consumer disconencts.
        :return:
        """
        if exchange_durable is None:
            exchange_durable = False
        if register_persist is None:
            register_persist = True
        if exchange_auto_delete is None:
            exchange_auto_delete = False

        self.pika_factory.register_exchange(exchange_name, exchange_type, exchange_durable, register_persist,
                          exchange_auto_delete)

    def register_queue(self, queue_name, queue_durable=None, queue_arguments=None, register_persist=None):
        """
        Register an exchange with the server.

        For details on these actions, please review any AMQP guide.

        :param queue_name: String (required) - Name of queue to create
        :param queue_durable: Bool (default = False) - If yes, queue survives broker restart.
        :param queue_arguments: Dict - Any arguments to pass to Pika queue creation.
        :param register_persist: Bool (default = True) - If queue should be re-created on re-connect.
        :return:
        """
        if queue_durable is None:
            queue_durable = False
        if register_persist is None:
            register_persist = False

        self.pika_factory.register_queue(queue_name, queue_durable, queue_arguments, register_persist)

    def register_exchange_queue_binding(self, exchange_name, queue_name, routing_key=None, register_persist=None):
        """
        Binds a queue to an exchange. The queue and exchange must exists first.

        :param exchange_name: String (required) - Exchange to bing the queue to.
        :param queue_name: String (required) - Queue to bind to exchange to.
        :param routing_key: String (required) - A routing key to bind the queue with.
        :param register_persist: Bool (default = False) - If binding should be re-created on re-connect.
        :return:
        """
        if routing_key is None:
            raise YomboWarning(
                    "AMQP Client:{%s} - register_exchange_queue_binding must have a routing key!" % self.client_id,
                    203, 'register_exchange_queue_binding', 'AMQPClient')
        if register_persist is None:
            register_persist = False

        self.pika_factory.register_exchange_queue_binding(exchange_name, queue_name, routing_key,
                          register_persist)

    def subscribe(self, queue_name, incoming_callback, error_callback=None, queue_no_ack=False, persistent=True):
        self._local_log("debug", "AMQPClient::subscribe", "queue_name: %s" % queue_name)

        if isinstance(incoming_callback, collections.Callable) is False:
            raise YomboWarning(
                    "AMQP Client:{%s} - incoming_callback must be callabled." % self.client_id,
                    203, 'subscribe', 'AMQPClient')

        if error_callback is not None:
            if isinstance(error_callback, collections.Callable) is False:
                raise YomboWarning(
                      "AMQP Client:{%s} - If error_callback is set, it must be be callable" % self.client_id,
                        204, 'subscribe', 'AMQPClient')

        self.pika_factory.subscribe(queue_name, incoming_callback, error_callback, queue_no_ack, persistent)

    def publish(self, **kwargs):
        """
        Used to send a message to the AMQP server. Can direct responses back to a callback, if defined. Otherwise,
        responses will be tossed to /dev/null.

        The following items in the kwargs are allowed/required.

        :param exchange_name:
        :param properties: Dict - A dictionary of properties that is passed to pika.BasicProperties.
        :param routing_key: String (required) - A routing key is required when sending messages. For security,
          default routing is not allowed.
        :param body: Any - Any data that should be sent in the AMQP message payload.
        """
        # self._local_log("debug", "AMQPClient::send_amqp_message", "Message: %s" % kwargs)
        meta = kwargs.get('meta', {})

        callback = kwargs.get('callback', None)
        if callback is not None:
            if isinstance(callback, collections.Callable) is False:
                raise YomboWarning(
                        "AMQP Client{:%s} - If callback is set, it must be be callable." % self.client_id,
                        200, 'publish', 'AMQPClient')

        exchange_name = kwargs.get('exchange_name', None)
        if exchange_name is None:
            raise YomboWarning(
                    "AMQP Client:{%s} - Must have exchange_name to publish to." % self.client_id,
                    201, 'publish', 'AMQPClient')

        body = kwargs.get('body', None)
        if body is None:
            raise YomboWarning(
                    "AMQP Client:{%s} - Must have a body." % self.client_id,
                    202, 'publish', 'AMQPClient')

        kwargs['routing_key'] = kwargs.get('routing_key', '*')
        kwargs['meta'] = meta
        return self.pika_factory.publish(**kwargs)

    def unsubscribe(self, queue_name):
        self.pika_factory.subscribe(queue_name)


class PikaFactory(protocol.ReconnectingClientFactory):
    """
    Responsible for setting up the factory, building the protocol and then connecting.
    """
    def __init__(self, AMQPClient):
        self._local_log("debug", "PikaFactory::__init__")
        self._Name = "PikaFactory"
        self._FullName = "yombo.gateway.lib.PikaFactory"
        # DO NOT CHANGE THESE!  Mitch Schwenk @ yombo.net
        # Reconnect sort-of fast, but random. ~25 second max wait
        # This is set in-case a server reboots, don't DDOS the servers!
        self.initialDelay = 0.9
        self.jitter = 0.2
        self.factor = 1.72503912
        self.maxDelay = 30  # this puts retries around 25-35 seconds

        self.AMQPClient = AMQPClient
        self.AMQPProtocol = None

        self.send_queue = deque() # stores any received items like publish and subscribe until fully connected
        self.exchanges = {}  # store a list of exchanges, will try to re-establish on reconnect.
        self.queues = {}  # store a list of queue, will try to re-establish on reconnect.
        self.exchange_queue_bindings = {}  # store a list of exchange queue bindings, will try to re-establish.
        self.consumers = {}  # store a list of consumers, will try to re-establish on reconnect.

    def _local_log(self, level, location, msg=""):
        logit = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    def startedConnecting(self, connector):
        """
        Called when the client has started conencting to the server.
        :param connector:
        :return:
        """
        self._local_log("debug", "PikaFactory::startedConnecting")

    def buildProtocol(self, addr):
        self._local_log("debug", "PikaFactory::buildProtocol")
        self.delay = 2
        self.retries = 0
        self._callID = None
        self.continueTrying = 1
        self.AMQPProtocol = PikaProtocol(self)
        self.AMQPProtocol.ready.addCallback(self.AMQPProtocol.connected)
        return self.AMQPProtocol

    def connected(self):
        """
        Called by PikaProtocol when connected.

        Checks to see if any queues, exchanings, bindings, or subscirptions needs to be
        setup. Also delivers any queued messages.

        :return:
        """
        # First load the queues up with any configuration items...
        self._local_log("debug", "PikaFactory::connected")
        self.AMQPProtocol.check_register_queues()
        self.AMQPProtocol.check_register_exchanges()
        self.AMQPProtocol.check_register_exchange_queue_bindings()
        self.AMQPProtocol.check_register_subscribe()

        self.AMQPProtocol.check_delivery_queue()  # now send to server.

        self.AMQPClient.connected()  # let the world know we are connected and ready.

    def register_queue(self, queue_name, queue_durable, queue_arguments, register_persist):
        """
        Request a new queue. Simply adds to the queue to be processed when the connection
        is fully established.

        :param queue_name:
        :param queue_durable:
        :param queue_arguments:
        :param register_persist:
        :return:
        """
        if queue_name in self.queues:
            raise YomboWarning(
                    "AMQP Protocol:{client_id} - Already has a queue: %s" % queue_name,
                    200, 'register_exchange', 'PikaFactory')

        self.queues[queue_name] = {
            'registered': False,
            'queue_name': queue_name,
            'queue_durable': queue_durable,
            'queue_arguments': queue_arguments,
            'register_persist': register_persist,
        }
        # print("new queue: %s" % self.queues[queue_name])
        if self.AMQPProtocol:
            self.AMQPProtocol.check_register_queues()

    def register_exchange(self, exchange_name, exchange_type, exchange_durable, register_persist,
                          exchange_auto_delete):
        """
        Request a new exchange. Simply adds to the queue to be processed when the connection
        is fully established.

        :param exchange_name:
        :param exchange_type:
        :param exchange_durable:
        :param register_persist:
        :param exchange_auto_delete:
        :return:
        """
        self._local_log("debug", "PikaFactory::register_exchange")

        if exchange_name in self.exchanges:
            raise YomboWarning(
                    "AMQP Protocol:{client_id} - Already has an exchange_name: %s" % exchange_name,
                    200, 'register_exchange', 'PikaFactory')

        self.exchanges[exchange_name] = {
            'registered': False,
            'exchange_name': exchange_name,
            'exchange_type': exchange_type,
            'exchange_durable': exchange_durable,
            'register_persist': register_persist,
            'exchange_auto_delete': exchange_auto_delete,
        }

        if self.AMQPProtocol:
            self.AMQPProtocol.check_register_exchanges()

    def register_exchange_queue_binding(self, exchange_name, queue_name, routing_key, register_persist):
        """
        Request a new exchange->queue binding. Simply adds to the queue to be processed when the
        connection is fully established.

        :param exchange_name:
        :param queue_name:
        :param routing_key:
        :param register_persist:
        :return:
        """
        eqb_name = sha256(unicode_to_bytes(exchange_name + queue_name + routing_key)).hexdigest()
        if eqb_name in self.exchange_queue_bindings:
            raise YomboWarning(
                    "AMQP Protocol:{client_id} - Already has an exchange-queue-routing key binding: %s-%s-%s" %
                        (exchange_name, queue_name, routing_key), 200, 'register_exchange', 'PikaFactory')

        self.exchange_queue_bindings[exchange_name+queue_name] = {
            'registered': False,
            'exchange_name': exchange_name,
            'queue_name': queue_name,
            'routing_key': routing_key,
            'register_persist': register_persist,
        }

        if self.AMQPProtocol:
            self.AMQPProtocol.check_register_exchange_queue_bindings()

    def subscribe(self, queue_name, incoming_callback, error_callback, queue_no_ack, register_persist):
        """
        Setups of a new subscription. Creates a new queue items to completed when the connection is
        up.

        :param queue_name:
        :param incoming_callback:
        :param error_callback:
        :param queue_no_ack:
        :param register_persist:
        :return:
        """
        if queue_name in self.consumers:
            raise YomboWarning(
                    "AMQP Protocol:{client_id} - Already subscribed to queue_name: %s" % queue_name,
                    200, 'subscribe', 'PikaFactory')

        self.consumers[queue_name] = {
            'queue_name': queue_name,
            'incoming_callback': incoming_callback,
            'error_callback': error_callback,
            'queue_no_ack': queue_no_ack,
            'register_persist': register_persist,
            'registered': False,
        }

        if self.AMQPProtocol:
            self.AMQPProtocol.check_register_subscribe()

    def publish(self, **kwargs):
        """
        Queues up the message, and asks the protocol to send if connected.
        """
        # logger.debug("factory:publish: {kwargs}", kwargs=kwargs)

        properties = kwargs.get('properties', {})

        callback_type = None
        callback_name = None
        callback_function = None
        callback = kwargs.get('callback', None)
        if callback is not None:
            if isinstance(callback, dict):
                try:
                    callback_type = callback['callback_component_type']
                    callback_name = callback['callback_component_type_name']
                    callback_function = callback['callback_component_type_function']
                except:
                    callback_type = None
                    callback_name = None
                    callback_function = None
                    callback = None
                else:
                    try:
                        callback = self._AMQP._Loader.find_function(callback_type, callback_name, callback_function)
                    except:
                        callback_type = None
                        callback_name = None
                        callback_function = None
                        callback = None
            elif isinstance(callback, collections.Callable) is False:
                raise YomboWarning(
                        "AMQP Client:%s - If callback is set, it must be be callable." % self.client_id,
                        201, 'publish', 'AMQPClient')

        else:
            callback_type = None
            callback_name = None
            callback_function = None
            callback = None

        exchange_name = kwargs.get('exchange_name', None)
        if exchange_name is None:
            raise YomboWarning(
                    "AMQP Client:{client_id} - Must have exchange_name to publish to." % self.client_id,
                    202, 'publish', 'AMQPClient')

        body = kwargs.get('body', None)
        if body is None:
            raise YomboWarning(
                    "AMQP Client:{client_id} - Must have a body." % self.client_id,
                    203, 'publish', 'AMQPClient')

        kwargs['routing_key'] = kwargs.get('routing_key', '*')
        if 'correlation_id' in properties:
            correlation_id = properties['correlation_id']
        else:
            if callback is not None:
                correlation_id = random_string(length=24)
                properties['correlation_id'] = correlation_id
            else:
                correlation_id = None
        if 'reply_to' in properties:
            reply_to = properties['reply_to']
        else:
            reply_to = None

        properties['user_id'] = self.AMQPClient.username
        kwargs['properties'] = properties

        message_meta = {
            "msg_at": time(),
            "msg_created_at": None,
            "msg_sent_at": None,
            "received_at": None,
            "direction": 'outgoing',
            "correlation_id": correlation_id,
            "reply_to": reply_to,
            "reply_received_at": None,
            "reply_correlation_id": None,
            "replied_at": None,
            "round_trip_timing": None,
            "payload_size": len(body),
            "content_encoding": None,
            "content_type": None,
            "uncompressed_size": None,
            "compression_percent": None,
        }
        if 'content_encoding' in properties:
            message_meta['content_encoding'] = properties['content_encoding']
        if 'content_type' in properties:
            message_meta['content_type'] = properties['content_type']

        meta = kwargs.get('meta', {})
        if len(meta) > 0:
            message_meta.update(meta)

        if message_meta['msg_created_at'] is None:
            meta['msg_created_at'] = time()

        correlation_persistent = kwargs.get('correlation_persistent', True)
        if correlation_id is not None:
            correlation_info = {
                "callback": callback,
                "callback_component_type": callback_type,  # module or component
                "callback_component_type_name": callback_name,  # module of component name
                "callback_component_type_function": callback_function,  # name of the function to call
                "correlation_id": correlation_id,
                "correlation_persistent": correlation_persistent,
                "correlation_at": time()
            }
            self.AMQPClient._AMQP.message_correlations[correlation_id] = correlation_info

        self.AMQPClient._AMQP.messages_processed[correlation_id] = message_meta
        kwargs['message_meta'] = message_meta
        if 'callback' in kwargs:
            del kwargs['callback']
        self.AMQPProtocol.delivery_queue['urgent'].append({
            'type': 'message',
            'fields': kwargs,
        })

        if self.AMQPProtocol:
            self.AMQPProtocol.check_delivery_queue()

        return {
            'message_meta': message_meta,
            'correlation_info': correlation_info,
        }

    def close(self):
        """
        Called from AMQPYombo._unload_, usually when gateway is shutting down.
        :return:
        """
        self._local_log("debug", "!!!!PikaFactory::close")
        self.AMQPProtocol.close()

    def disconnected(self):
        """
        Called by the protocol when the connection closes.
        :return:
        """
        for item_key, item in self.exchanges.items():
            if item['register_persist']:
                self.exchanges[item_key]['registered'] = False

        for item_key, item in self.queues.items():
            if item['register_persist']:
                self.queues[item_key]['registered'] = False

        for item_key, item in self.exchange_queue_bindings.items():
            if item['register_persist']:
                self.exchange_queue_bindings[item_key]['registered'] = False

        for item_key, item in self.consumers.items():
            if item['subscribed']:
                self.consumers[item_key]['subscribed'] = False

        self.AMQPClient.disconnected('unknown')

    def clientConnectionLost(self, connector, reason):
        print("clientConnectionLost: self.connection_state: %s" % self.AMQPProtocol.connection_state)
        # print("error 1: %s" % connector)
        # print("error 2: %s" % reason.__dict__)
        # raise YomboCritical("something...")
        logger.warn("pika factory clientConnectionLost, reason: {reason}", reason=reason.value)
        if self.AMQPClient.is_connected and str(reason.value) != "Connection was closed cleanly.":
            logger.warn("In PikaFactory clientConnectionLost. Reason: {reason}", reason=reason.value)
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
        if self.continueTrying:
            self.retry()

    def clientConnectionFailed(self, connector, reason):
        logger.info("!!!!!!!!!!!!!!!!!!!!!!!1In PikaFactory clientConnectionFailed. Reason: {reason}", reason=reason)
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


class PikaProtocol(pika.adapters.twisted_connection.TwistedProtocolConnection):
    """
    Responsible for low level handling. Does the actual work of setting up any exchanges, queues, and bindings. Also
    sends greeting and initial handshake.

    On connect, it always sends a message to let Yombo know of it's pertinent information.
    """

    def __init__(self, factory):
        """
        Save pointer to factory and then call it's parent __init__.
        """
        self.delivery_queue = {
            'urgent': deque(),
            'high': deque(),
            'normal': deque(),
            'low': deque(),
        }

        self.factory = factory
        self._connected = None
        self.connection = None
        self.check_delivery_queue_running = False
        super(PikaProtocol, self).__init__(
            parameters=self.factory.AMQPClient.pika_parameters)

    def _local_log(self, level, location="", msg=""):
        logit = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    @inlineCallbacks
    def connected(self, connection):
        """
        Is called when connected to AMQP server.

        :param connection: The connection to Yombo AMQP server.
        """
        self._local_log("debug", "PikaProtocol::connected")
        self.connection = connection
        self.channel = yield connection.channel()
        yield self.channel.basic_qos(prefetch_count=self.factory.AMQPClient.prefetch_count)
        self.channel.add_on_close_callback(self.on_connection_closed)
        self.channel.add_on_cancel_callback(self.on_consumer_cancelled)
        logger.debug("Setting AMQP connected to true.")
        self._connected = True
        self.factory.connected()

    def on_consumer_cancelled(self, method_frame):
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer
        receiving messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame

        """
        print('Consumer was cancelled remotely, shutting down: %r', method_frame)
        if self._channel:
            self._channel.close()

    def on_connection_closed(self, channel, replyCode, replyText):
        """
        This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.

        :param pika.connection.Connection connection: The closed connection obj
        :param int reply_code: The server provided reply_code if given
        :param str reply_text: The server provided reply_text if given
        """
        # logger.debug("$$$$$$$$$$$$$$$$$$ on_connection_closed %s: %s" % (replyCode, replyText))
        if replyCode == 403:
            logger.warn("AMQP access denied to login. Usually this happens when there is more then one instance of the same gateway running.")
        if replyCode == 404:
            logger.debug("close_channel: %s : %s" % (replyCode, replyText))
        if replyCode != 200:
            logger.info("close_channel: %s : %s" % (replyCode, replyText))
            # self.channel.close()
        self.factory.disconnected()

    def get_delivery_item(self):
        for priority in ['urgent', 'high', 'normal', 'low']:
            if len(self.delivery_queue[priority]) > 0:
                return priority, self.delivery_queue[priority].popleft()
        return None, None

    @inlineCallbacks
    def check_delivery_queue(self):
        if self._connected is None:
            return None

        if self.check_delivery_queue_running is True:
            # logger.debug("check_delivery_queue already running.. bye....")
            return None
        self.check_delivery_queue_running = True
        logger.debug("check_delivery_queue... Go")

        while True:
            priority, item = self.get_delivery_item()
            if item is None:
                break
            if item['type'] == 'queue':
                yield self.do_send_queue(item['fields'])
            elif item['type'] == 'exchange':
                yield self.do_send_exchange(item['fields'])
            elif item['type'] == 'binding':
                yield self.do_send_exchange_queue_bindings(item['fields'])
            elif item['type'] == 'subscribe':
                yield self.do_send_subscribe(item['fields'])
            elif item['type'] == 'message':
                yield self.do_send_message(priority, item)

        self.check_delivery_queue_running = False

    @inlineCallbacks
    def do_send_queue(self, fields):
        """
        Performs the actual registration of queues.
        """
        # self._local_log("debug", "PikaProtocol::do_send_queue")
        # print("do_send_queue fields: %s" % fields)
        queue_name = fields['queue_name']
        yield self.channel.queue_declare(
            queue=fields['queue_name'],
            durable=fields['queue_durable'],
            arguments=fields['queue_arguments'])
        if queue_name in self.factory.queues:
            self.factory.queues[queue_name]['registered'] = True

    @inlineCallbacks
    def do_send_exchange(self, fields):
        """
        Performs the actual registration of exchanges.
        """
        # self._local_log("debug", "PikaProtocol::do_send_exchange")
        exchange_name = fields['exchange_name']
        yield self.channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=fields['exchange_type'],
            durable=fields['exchange_durable'],
            auto_delete=fields['exchange_auto_delete'])
        if exchange_name in self.factory.exchanges:
            self.factory.exchanges[exchange_name]['registered'] = True

    @inlineCallbacks
    def do_send_exchange_queue_bindings(self, fields):
        """
        Performs the actual registration of exchange_queue_bindings.
        """
        # self._local_log("debug", "PikaProtocol::do_send_exchange_queue_bindings")
        queue_name = fields['queue_name']
        exchange_name = fields['exchange_name']
        yield self.channel.queue_bind(
            exchange=fields['exchange_name'],
            queue=fields['queue_name'],
            routing_key=fields['routing_key'])
        name = exchange_name+queue_name
        if name in self.factory.exchange_queue_bindings:
            self.factory.exchange_queue_bindings[name]['registered'] = True

    @inlineCallbacks
    def do_send_subscribe(self, fields):
        """
        Performs the actual binding of the queue to the AMQP channel.
        """
        # self._local_log("debug", "PikaProtocol::do_send_subscribe")
        queue_name = fields['queue_name']
        (queue, consumer_tag,) = yield self.channel.basic_consume(queue=queue_name,
                                                                  no_ack=fields['queue_no_ack'])

        d = queue.get()
        d.addCallback(self.receive_item, queue, fields['queue_no_ack'], fields['incoming_callback'])
        if fields['error_callback'] is not None:
            d.addErrback(fields['error_callback'])
        else:
            d.addErrback(self.receive_item_err)
        d.addCallback(self._register_consumer_success, queue_name)
        if queue_name in self.factory.consumers:
            self.factory.consumers[queue_name]['registered'] = True

    def _register_consumer_success(self, tossaway, queue_name):
        self.factory.consumers[queue_name]['subscribed'] = True

    @inlineCallbacks
    def do_send_message(self, priority, item):
        """
        Sends an AMQP message
        """
        # logger.info("exchange=%s, routing_key=%s, body=%s, properties=%s " % (kwargs['exchange_name'],kwargs['routing_key'],kwargs['body'], kwargs['properties']))
        # self._local_log("debug", "PikaProtocol::do_send_message")
        fields = item['fields']
        try:
            message_meta = fields['message_meta']
            fields['properties'] = pika.BasicProperties(**fields['properties'])
            fields['properties'].headers['msg_sent_at'] = str(time())
            # print("do_send_message fields: %s" % fields)
            try:
                yield self.channel.basic_publish(exchange=fields['exchange_name'],
                                                 routing_key=fields['routing_key'],
                                                 body=fields['body'],
                                                 properties=fields['properties'])
            except ChannelClosed as e:
                self.delivery_queue[priority].append(item)
                if self.factory.continueTrying:
                    self.factory.retry()
                return

            message_meta['msg_sent_at'] = float(time())
            message_meta['send_success'] = True

        except Exception as error:
            logger.warn("--------==(Error: While sending message.     )==--------")
            logger.warn("--------------------------------------------------------")
            logger.warn("{error}", error=sys.exc_info())
            logger.warn("---------------==(Traceback)==--------------------------")
            logger.warn("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.warn("--------------------------------------------------------")
            message_meta['send_success'] = False

    def check_register_queues(self):
        """
        Checks if any queues need to be registered on connection.
        """
        # self._local_log("debug", "PikaProtocol::do_register_queues")
        for queue_name in list(self.factory.queues.keys()):
            fields = self.factory.queues[queue_name]
            if fields['registered'] is False:
                self.delivery_queue['urgent'].append({
                    'type': 'queue',
                    'fields': fields,
                })
            if fields['register_persist'] is False:
                del self.factory.queues[queue_name]
        self.check_delivery_queue()

    def check_register_exchanges(self):
        """
        Performs the actual registration of exchanges.
        """
        # logger.debug("Do_register_exchanges, todo: {exchanges}", exchanges=self.factory.exchanges)
        for exchange_name in list(self.factory.exchanges.keys()):
            fields = self.factory.exchanges[exchange_name]
            if fields['registered'] is False:
                self.delivery_queue['urgent'].append({
                    'type': 'exchange',
                    'fields': fields,
                })
            if fields['register_persist'] is False:
                del self.factory.exchanges[exchange_name]
        self.check_delivery_queue()

    def check_register_exchange_queue_bindings(self):
        """
        Performs the actual registration of exchange_queue_bindings.
        """
        # self._local_log("debug", "PikaProtocol::check_exchange_queue_bindings")
        for eqb_name in list(self.factory.exchange_queue_bindings.keys()):
            fields = self.factory.exchange_queue_bindings[eqb_name]
            if fields['registered'] is False:
                self.delivery_queue['urgent'].append({
                    'type': 'binding',
                    'fields': fields,
                })
            if fields['register_persist'] is False:
                del self.factory.exchange_queue_bindings[eqb_name]
        self.check_delivery_queue()

    def check_register_subscribe(self):
        """
        Checks if any subscriptions (consumers/bindings) need to be registered on connection.
        """
        # self._local_log("debug", "PikaProtocol::check_send_subscribe")
        for queue_name in list(self.factory.consumers.keys()):
            fields = self.factory.consumers[queue_name]
            self.delivery_queue['normal'].append({
                'type': 'subscribe',
                'fields': fields,
            })
            if fields['register_persist'] is False:
                del self.factory.consumers[queue_name]
        self.check_delivery_queue()

    def receive_item(self, item, queue, queue_no_ack, subscription_callback):
        """
        This function is called with EVERY incoming message. We don't have logic here, just send to factory.
        """
        (channel, deliver, props, msg,) = item
        sent_message_meta = None
        correlation_info = None
        correlation_id = None
        reply_to = None

        queue_deferred = queue.get()  # get the queue again, so we can add another callback to get the next message.
        queue_deferred.addCallback(self.receive_item, queue, queue_no_ack, subscription_callback)
        queue_deferred.addErrback(self.receive_item_err)  # todo: use supplied error callback...  which one?

        if hasattr(props, 'headers') and 'yombo_msg_protocol_verion' in props.headers:
            try:
                yombo_protocol_version = int(props.headers['yombo_msg_protocol_verion'])
            except:
                pass
            finally:

                try:
                    yombo_parsed_data = self.factory.AMQPClient._AMQP._AMQPYombo.amqp_incoming_parse(
                        channel, deliver, props, msg)
                    headers = yombo_parsed_data['headers']
                    if 'correlation_id' in headers:
                        correlation_id = headers['correlation_id']
                    if 'reply_to' in headers:
                        reply_to = headers['reply_to']
                except YomboWarning as e:
                    logger.warn("While parsing yombo message: %s" % e)
        else:
            yombo_protocol_version = None

        if correlation_id is None and hasattr(props, 'correlation_id') and props.correlation_id is not None:
            correlation_id = props.correlation_id
        if reply_to is None and hasattr(props, 'reply_to') and props.reply_to is not None:
            reply_to = props.reply_to

        if reply_to is not None:
            if reply_to.isalnum() is False or len(reply_to) < 15 or len(reply_to) > 84:
                if yombo_protocol_version is not None:
                    logger.warn("Discarding incoming message, invalid reply_to.")
                    return self._basic_ack(1, channel, deliver.delivery_tag)
                else:
                    logger.warn("Message doesn't appear to have a friendly reply_to. Not long enough or contains odd characters.")
            else:
                if reply_to in self.factory.AMQPClient._AMQP.messages_processed:
                    sent_message_meta = self.factory.AMQPClient._AMQP.messages_processed[reply_to]

            # If there's no correlation and it's a Yombo message, ignore.
            if reply_to not in self.factory.AMQPClient._AMQP.message_correlations and \
                        yombo_protocol_version is not None:
                    logger.warn("Ignoring incoming AMQP message: Correlation ID not found")
                    return self._basic_ack(1, channel, deliver.delivery_tag)


        if correlation_id is not None:
            if correlation_id.isalnum() is False or len(correlation_id) < 15 or len(correlation_id) > 84:
                if yombo_protocol_version is not None:
                    logger.warn("Discarding incoming message, invalid correlation_id.")
                    return self._basic_ack(1, channel, deliver.delivery_tag)
                else:
                    logger.warn("Message doesn't appear to have a friendly correlation_id. Not long enough or contains odd characters.")
            else:
                # print("got yombo message bd1")
                if correlation_id in self.factory.AMQPClient._AMQP.message_correlations:
                    # print("got yombo message bd2")
                    correlation_info = self.factory.AMQPClient._AMQP.message_correlations[correlation_id]
                    if sent_message_meta is None:
                        # print("got yombo message bd3")
                        if correlation_info['correlation_id'] is not None and \
                            correlation_info['received_correlation_id'] in self.factory.AMQPClient._AMQP.messages_processed:
                            sent_message_meta = self.factory.AMQPClient._AMQP.messages_processed[correlation_id]

                if reply_to in self.factory.AMQPClient._AMQP.message_correlations and correlation_info is None:
                        correlation_info = self.factory.AMQPClient._AMQP.message_correlations[reply_to]

        received_message_meta = {
            "msg_at": time(),
            "msg_created_at": None,
            "msg_sent_at": None,
            "msg_received_at": float(time()),
            "direction": 'incoming',
            "correlation_id": correlation_id,
            "reply_to": reply_to,
            "reply_received_at": None,
            "reply_correlation_id": None,
            "replied_at": None,
            # "replied_correlation_id": None,
            "round_trip_timing": None,
            "payload_size": len(msg),
            "content_encoding": None,
            "content_type": None,
            "compressed_size": None,
            "compression_percent": None,
        }

        if hasattr(props, 'content_encoding'):
            received_message_meta['content_encoding'] = props.content_encoding
        if hasattr(props, 'content_type'):
            received_message_meta['content_type'] = props.content_type

        if sent_message_meta is not None:
            sent_message_meta['reply_received_at'] = float(time())
            sent_message_meta['reply_correlation_id'] = correlation_id
            # received_message_meta['reply_received_at'] = time()
            # received_message_meta['reply_correlation_id'] = time()

        # print("starting receiving stuff.....")
        if yombo_protocol_version is not None:
            received_message_meta.update(yombo_parsed_data['received_message_meta'])
            # print("got yombo message d1 - yombo_parsed_data: %s" % yombo_parsed_data['received_message_meta'])
        try:
            if correlation_id[0:2] != 'xx_' and sent_message_meta is not None:
                milliseconds = received_message_meta['msg_received_at'] - sent_message_meta['msg_sent_at']
                sent_message_meta['round_trip_timing'] = milliseconds
        except Exception as e:
            logger.warn("Problem calculating message round_trip_timing: %s" % e)
        if correlation_info is not None:
            received_message_meta['correlation_id'] = correlation_id
            received_message_meta['correlation_id_correlated'] = True
        else:
            received_message_meta['correlation_id_correlated'] = False

        # print("got yombo message d1 - sent_message_meta: %s" % sent_message_meta)
        # print("got yombo message d1 - received_message_meta: %s" % received_message_meta)
        # print("Ending receiving stuff.....")

        if correlation_id is not None and correlation_id[0:2] != 'xx_':
            self.factory.AMQPClient._AMQP.messages_processed[correlation_id] = received_message_meta

        # Now, route the message. If it's a yombo message, send it to your AQMPYombo for delivery
        if yombo_protocol_version is not None:
            # print("amqp route: amqpyombo: %s" % correlation_info)
            the_callback = self.factory.AMQPClient._AMQP._AMQPYombo.amqp_incoming

        # Else if we have a correlation_id with a callback, send it there.
        elif correlation_info is not None and correlation_info['callback'] is not None and \
                isinstance(correlation_info['callback'], collections.Callable) is True:
            # logger.info("amqp route: message callback from correlation_info")
            the_callback = correlation_info['callback']

        # Lastly, send it to the callback defined by the subscription
        else:
            # logger.info("amqp route: default amqp subscribe binding callback")
            the_callback = subscription_callback

        sent = defer.maybeDeferred(the_callback,
                                   body=yombo_parsed_data['body'],
                                   properties=props,
                                   headers=yombo_parsed_data['headers'],
                                   deliver=deliver,
                                   correlation_info=correlation_info,
                                   received_message_meta=received_message_meta,
                                   sent_message_meta=sent_message_meta,
                                   subscription_callback=subscription_callback,
                                   )

        if not queue_no_ack:
            sent.addCallback(self._basic_ack, channel, deliver.delivery_tag)
            sent.addErrback(self._basic_nack, channel, deliver.delivery_tag)

    def receive_item_err(self, error):
        """
        Is caled when an un-caught exception happens while processing an incoming message.

        :param error:
        :return:
        """
        logger.warn("AQMP Receive_item_err: %s" % error)
        # if error.value[0] == 200:
        #     return
        self._local_log("debug", "PikaProtocol::receive_item_err", "Error: %s" % error.__dict__)

    def _basic_ack(self, tossaway, channel, tag):
        self._local_log("debug", "PikaProtocol::_basic_ack", "Tag: %s" % tag)
        channel.basic_ack(tag)

    def _basic_nack(self, error, channel, tag):
        self._local_log("info", "PikaProtocol::_basic_nack for client: %s   Tag: %s" % (self.factory.AMQPClient.client_id, tag))
        logger.error("AMQP nack'd on error: {error}", error=error)
        channel.basic_nack(tag, False, False)
