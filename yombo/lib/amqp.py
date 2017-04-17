# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For developer documentation, see: `AMQP @ Module Development <https://yombo.net/docs/modules/amqp/>`_

.. seealso::

   The :doc:`mqtt library </lib/mqtt>` can connect to MQTT brokers, this a light weight message broker.

AMQP messaging is implemented by this library. It's used by Yombo Gateway to commuicate with it's servers. This
library also exposes and API that modules can use to connect to other servers.
AMQP protocol can be used for sending messages to other systems for processing, status updates, or requests. For
for more informatin, see the `RabbitMQ Tutorials <https://www.rabbitmq.com/getstarted.html>`_.

Yombo Gateway interacts with Yombo servers using AMQPYombo which depends on this library.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2015-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/amqp.py>`_
"""
# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
import pika
from datetime import datetime
from collections import deque
from hashlib import sha1
import sys
import traceback

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import ssl, protocol, defer
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import random_string
from yombo.utils.maxdict import MaxDict

logger = get_logger('library.amqp')


class AMQP(YomboLibrary):
    """
    This library can connect to any AMQP compatible server. It uses the Pika library to perform the actual
    AMQP handling.

    Developers should only be interested in the **new** function of this class. You will get back a
    :py:class:AMQPClient instance. This instance will allow you to subscribe, publish, and setup exchanges and
    queues.
    """
    def _init_(self):
        self.client_connections = {}

    def _unload_(self):
        self._local_log("debug", "AMQP::_unload_")
        # print "amqp - removing all clients.."
        for client_id, client in self.client_connections.iteritems():
            # print "amqp-clinet: %s" % client_id
            if client.is_connected:
                try:
                    client.disconnect()  # this tells the factory to tell the protocol to close.
    #                client.factory.stopTrying()  # Tell reconnecting factory to don't attempt connecting after disconnect.
    #                client.factory.protocol.disconnect()
                except:
                    pass

    def _local_log(self, level, location="", msg=""):
        logit = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    @inlineCallbacks
    def new(self, hostname=None, port=5671, virtual_host=None, username=None, password=None, use_ssl=True,
            connected_callback=None, disconnected_callback=None, error_callback=None, client_id=None, keepalive=1800,
            prefetch_count=10, critical=False):
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
        :param keepalive: Int (default 1800) - How many seconds a ping should be performed if there's not recent
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
            if callable(connected_callback) is False:
                raise YomboWarning("If incoming_callback is set, it must be be callable.")

        if disconnected_callback is not None:
            if callable(disconnected_callback) is False:
                raise YomboWarning("If incoming_callback is set, it must be be callable.")

        if error_callback is not None:
            if callable(error_callback) is False:
                raise YomboWarning("If error_callback is set, it must be be callable.")

        self.client_connections[client_id] = AMQPClient(self, client_id, hostname, port, virtual_host, username,
                password, use_ssl, connected_callback, disconnected_callback, error_callback, keepalive, prefetch_count,
                critical)
        yield self.client_connections[client_id].init()
        returnValue(self.client_connections[client_id])


class AMQPClient(object):
    def __init__(self, amqp_library, client_id, hostname, port, virtual_host, username, password, use_ssl,
                 connected_callback, disconnected_callback, error_callback, keepalive, prefetch_count, critical_connection):
        """
        Abstracts much of the tasks for AMQP handling. Yombo Gateway libraries and modules should primarily interact
        with these methods.

        Note: Check with your AMQP host to validate you are have permissions before performing many of these tasks.
        Many times, the server will disconnect the session if a request is being made and don't have permission.

        :param amqp_library: Class - A pointer to AMQP library.
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
        :param keepalive: Int (default 1800) - How many seconds a ping should be performed if there's not recent
          traffic.
        :param prefetch_count: Int (default 10) - How many outstanding messages the client should have at any
          given time.
        """
        self._FullName = 'yombo.gateway.lib.AMQP.AMQPClient'
        self._Name = 'AMQP.AMQPClient'

        self.amqp_library = amqp_library
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

    @inlineCallbacks
    def init(self):
        self.send_correlation_ids = yield self.amqp_library._SQLDict.get(
            self,
            "send_request_ids",
            serializer=self.correlation_ids_serializer,
            unserializer=self.correlation_ids_unserializer,
            max_length=250
        )

        # print "correlation_ids: %s" % self.send_correlation_ids
        # MaxDict(250)  # correlate requests with responses

    def correlation_ids_serializer(self, correlation):
        output = {}
        print "correlation: %s" % correlation
        correlation['callback'] = None
        return correlation

    def correlation_ids_unserializer(self, correlation):
        output = correlation.copy()

        if output['callback_component_type'] is not None and \
            output['callback_component_type_name'] is not None and \
            output['callback_component_type_function'] is not None:
            try:
                output['callback'] = self.amqp_library._Loader.find_function(output['callback_component_type'],
                                                        output['callback_component_type_name'],
                                                        output['callback_component_type_function'] )
            except:
                pass

        return output

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

    def disconnected(self, reason):
        """
        Function is called when the Gateway is disconnected from the AMQP service.
        """
        logger.info("AMQP Client {client_id} disconnected. Will usually auto-reconnected.", client_id=self.client_id)
        self.is_connected = False
        self._disconnecting = False
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

        if callable(incoming_callback) is False:
            raise YomboWarning(
                    "AMQP Client:{%s} - incoming_callback must be callabled." % self.client_id,
                    203, 'subscribe', 'AMQPClient')

        if error_callback is not None:
            if callable(error_callback) is False:
                # print "Error_callback - %s" % error_callback
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
        self._local_log("debug", "AMQPClient::send_amqp_message", "Message: %s" % kwargs)
        callback = kwargs.get('callback', None)
        if callback is not None:
            if callable(callback) is False:
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

        kwargs["time_created"] = kwargs.get("time_created", datetime.now())
        if 'routing_key' not in kwargs:
            raise YomboWarning(
                    "AMQP Client:{%s} - Must have routing_key to publish to, therwise, don't know how to route!" % self.client_id,
                    201, 'publish', 'AMQPClient')
        kwargs['routing_key'] = kwargs.get('routing_key', '*')

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
        # This is set incase a server reboots, don't DDOS the servers!
        self.initialDelay = 0.2
        self.jitter = 0.2
        self.factor = 1.82503912
        self.maxDelay = 25 # this puts retrys around 17-26 seconds

        self.AMQPClient = AMQPClient
        self.AMQPProtocol = None

        self._Statistics = AMQPClient.amqp_library._Libraries['statistics']

        self.send_queue = deque() # stores any received items like publish and subscribe until fully connected
        self.exchanges = {}  # store a list of exchanges, will try to re-establish on reconnect.
        self.queues = {}  # store a list of queue, will try to re-establish on reconnect.
        self.exchange_queue_bindings = {}  # store a list of exchange queue bindings, will try to re-establish.
        self.consumers = {}  # store a list of consumers, will try to re-establish on reconnect.

    def _local_log(self, level, location, msg=""):
        logit = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    def startedConnecting(self, connector):
        self._local_log("debug", "PikaFactory::startedConnecting")

    def buildProtocol(self, addr):
        self._local_log("debug", "PikaFactory::buildProtocol")
        self.resetDelay()
        self.AMQPProtocol = PikaProtocol(self)
        self.AMQPProtocol.ready.addCallback(self.AMQPProtocol.connected)
        return self.AMQPProtocol

    def register_exchange(self, exchange_name, exchange_type, exchange_durable, register_persist, exchange_auto_delete):
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
            self.AMQPProtocol.do_register_exchanges()

    def register_queue(self, queue_name, queue_durable, queue_arguments, register_persist):
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

        if self.AMQPProtocol:
            self.AMQPProtocol.do_register_queues()

    def register_exchange_queue_binding(self, exchange_name, queue_name, routing_key, register_persist):
        eqb_name = sha1(exchange_name + queue_name + routing_key).hexdigest()
        if eqb_name in self.exchange_queue_bindings:
            raise YomboWarning(
                    "AMQP Protocol:{client_id} - Already has an exchange-queue-routing key binding: %s-%s-%s" %
                        (exchange_name, queue_name, routing_key), 200, 'register_exchange', 'PikaFactory')

        self.exchange_queue_bindings[queue_name] = {
            'registered': False,
            'exchange_name': exchange_name,
            'queue_name': queue_name,
            'routing_key': routing_key,
            'register_persist': register_persist,
        }

        if self.AMQPProtocol:
            self.AMQPProtocol.do_register_exchange_queue_bindings()

    def subscribe(self, queue_name, incoming_callback, error_callback, queue_no_ack, register_persist):
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
            'subscribed': False,
        }

        if self.AMQPProtocol:
            self.AMQPProtocol.do_register_consumers()

    def publish(self, **kwargs):
        """
        Queues up the message, and asks the protocol to send if connected.
        """
        logger.debug("factory:publish: {kwargs}", kwargs=kwargs)
        self._local_log("debug", "PikaFactory::send_amqp_message", "Message: %s" % kwargs)

        c_type = None
        c_name = None
        c_function = None
        callback = kwargs.get('callback', None)
        if callback is not None:
            if callable(callback) is False:
                raise YomboWarning(
                        "AMQP Client:%s - If callback is set, it must be be callable." % self.client_id,
                        201, 'publish', 'AMQPClient')
            elif isinstance(callback, dict):
                try:
                    c_type = callback['callback_component_type']
                    c_name = callback['callback_component_type_name']
                    c_function = callback['callback_component_type_function']
                except:
                    c_type = None
                    c_name = None
                    c_function = None
                    callback = None
                else:
                    try:
                        callback = self.amqp_library._Loader.find_function(c_type, c_name, c_function)
                    except:
                        c_type = None
                        c_name = None
                        c_function = None
                        callback = None

        else:
            c_type = None
            c_name = None
            c_function = None
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

        kwargs["time_created"] = kwargs.get("time_created", datetime.now())
        kwargs['routing_key'] = kwargs.get('routing_key', '*')
        properties = kwargs.get('properties', {})
        if 'correlation_id' in properties:
            correlation_id = properties['correlation_id']
        else:
            if callback is not None:
                correlation_id = random_string()
            else:
                correlation_id = None
        properties['user_id'] = self.AMQPClient.username

        kwargs['properties'] = properties

        if correlation_id is not None:
            self.AMQPClient.send_correlation_ids[correlation_id] = {
                "time_created"      : kwargs.get("time_created", datetime.now()),
                'time_sent'         : None,
                "time_received"     : None,
                "callback"          : callback,
                "callback_component_type"         : c_type, # module or component
                "callback_component_type_name"    : c_name, # module of compentnt name
                "callback_component_type_function": c_function, # name of the function to call
                "correlation_id"  : correlation_id,
            }
        self.send_queue.append(kwargs)

        if self.AMQPProtocol:
            self.AMQPProtocol.do_publish()

        if correlation_id is None:
            return None
        else:
            return self.AMQPClient.send_correlation_ids[correlation_id]

    def connected(self):
        """
        Called by PikaProtocol when connected.
        :return:
        """
        self.AMQPProtocol.do_register_queues()
        self.AMQPProtocol.do_register_exchanges()
        self.AMQPProtocol.do_register_exchange_queue_bindings()
        self.AMQPProtocol.do_register_consumers()
        self.AMQPProtocol.do_publish()

        self.AMQPClient.connected()

    def close(self):
        """
        Called from AMQPYombo._unload_, usually when gateway is shutting down.
        :return:
        """
        self._local_log("debug", "!!!!PikaFactory::close")
#        print "amqp factory about to call close: %s" % self.AMQPProtocol
        self.AMQPProtocol.close()

    def disconnected(self):
        """
        Called by the protocol when the connection closes.
        :return:
        """
        for item_key, item in self.exchanges.iteritems():
            if item['register_persist']:
                self.exchanges[item_key]['registered'] = False

        for item_key, item in self.queues.iteritems():
            if item['register_persist']:
                self.queues[item_key]['registered'] = False

        for item_key, item in self.exchange_queue_bindings.iteritems():
            if item['register_persist']:
                self.exchange_queue_bindings[item_key]['registered'] = False

        for item_key, item in self.consumers.iteritems():
            if item['subscribed']:
                self.consumers[item_key]['subscribed'] = False

        self.AMQPClient.disconnected('unknown')

    def clientConnectionLost(self, connector, reason):
        if self.AMQPClient.is_connected and str(reason.value) != "Connection was closed cleanly.":
            logger.warn("In PikaFactory clientConnectionLost. Reason: {reason}", reason=reason.value)
        # self.AMQPClient.disconnected('lost')
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        logger.debug("In PikaFactory clientConnectionFailed. Reason: {reason}", reason=reason)
        # self.AMQPClient.disconnected('failed')
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
        self.factory = factory
        self._connected = None
        self.connection = None
        super(PikaProtocol, self).__init__(self.factory.AMQPClient.pika_parameters)

    def _local_log(self, level, location="", msg=""):
        logit = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    @inlineCallbacks
    def connected(self, connection):
        """
        Is called when connected to AMQP server.

        :param connection: The connection to Yombo AMQP server.
        """
        self._local_log("warn", "PikaProtocol::connected")
        self.connection = connection
        self.channel = yield connection.channel()

        def close_connection(channel, replyCode, replyText):
            if replyCode == 403:
                logger.warn("AMQP access denied to login. Usually this happens when there is more then one instance of the same gateway running.")
            if replyCode == 404:
                logger.debug("close_channel: %s : %s" % (replyCode, replyText))
            if replyCode != 200:
                logger.info("close_channel: %s : %s" % (replyCode, replyText))
                connection.close()
            self.factory.disconnected()
        self.channel.add_on_close_callback(close_connection)

        yield self.channel.basic_qos(prefetch_count=self.factory.AMQPClient.prefetch_count)
        logger.debug("Setting AMQP connected to true.")
        self._connected = True
        self.factory.connected()

    # def close(self):
    #     """
    #     Close the connection to Yombo.
    #
    #     :return:
    #     """
    #     self._local_log("debug", "PikaProtocol::close", "Trying to close!")
    #     self.connected = False
    #     try:
    #         self.connection.close()
    #     except:
    #         pass

    @inlineCallbacks
    def do_register_exchanges(self):
        """
        Performs the actual registration of exchanges.
        """
        self._local_log("debug", "PikaProtocol::do_register_exchanges")
        logger.debug("Do_register_exchanges, todo: {exchanges}", exchanges=self.factory.exchanges)
        for exchange_name in self.factory.exchanges.keys():
            fields = self.factory.exchanges[exchange_name]
            # print "do_register_exchanges, fields: %s" % fields
            if fields['registered'] is False:
                yield self.channel.exchange_declare(exchange=exchange_name, type=fields['exchange_type'],
                            durable=fields['exchange_durable'], auto_delete=fields['exchange_auto_delete'])
                self.factory.exchanges[exchange_name]['subscribed'] = True
                if fields['register_persist'] is False:
                    del self.factory.exchanges[exchange_name]

    @inlineCallbacks
    def do_register_queues(self):
        """
        Performs the actual registration of queues.
        """
        self._local_log("debug", "PikaProtocol::do_register_queues")
        for queue_name in self.factory.queues.keys():
            fields = self.factory.queues[queue_name]
            if fields['registered'] is False:
                yield self.channel.queue_declare(queue=fields['queue_name'], durable=fields['queue_durable'],
                            arguments=fields['queue_arguments'])
                self.factory.queues[queue_name]['subscribed'] = True
                if fields['register_persist'] is False:
                    del self.factory.queues[queue_name]

    @inlineCallbacks
    def do_register_exchange_queue_bindings(self):
        """
        Performs the actual registration of exchange_queue_bindings.
        """
        self._local_log("debug", "PikaProtocol::do_register_exchange_queue_binds")
        for eqb_name in self.factory.exchange_queue_bindings.keys():
            fields = self.factory.exchange_queue_bindings[eqb_name]
            if fields['registered'] is False:
                yield self.channel.queue_bind(exchange=fields['exchange_name'],
                            queue=fields['queue_name'],
                            routing_key=fields['routing_key'])
                self.factory.exchange_queue_bindings[eqb_name]['subscribed'] = True
                if fields['register_persist'] is False:
                    del self.factory.exchange_queue_bindings[eqb_name]

    @inlineCallbacks
    def do_register_consumers(self):
        """
        Performs the actual binding of the queue to the AMQP channel.
        """
        self._local_log("debug", "PikaProtocol::do_register_consumer")
        for queue_name in self.factory.consumers.keys():
            fields = self.factory.consumers[queue_name]
            if fields['subscribed'] is False:
                (queue, consumer_tag,) = yield self.channel.basic_consume(queue=queue_name,
                                                                          no_ack=fields['queue_no_ack'])
                self.factory.consumers[queue_name]['subscribed'] = True
                d = queue.get()
                d.addCallback(self.receive_item, queue, fields['queue_no_ack'], fields['incoming_callback'])
                if fields['error_callback'] is not None:
                    d.addErrback(fields['error_callback'])
                else:
                    d.addErrback(self.receive_item_err)
                d.addCallback(self._register_consumer_success, queue_name)
                if fields['register_persist'] is False:
                    del self.factory.consumers[queue_name]

    @inlineCallbacks
    def do_publish(self):
        """
        Performs the actual binding of the queue to the AMQP channel.
        """
#        prop = spec.BasicProperties(delivery_mode=2)

#        logger.info("exchange=%s, routing_key=%s, body=%s, properties=%s " % (kwargs['exchange_name'],kwargs['routing_key'],kwargs['body'], kwargs['properties']))
        logger.debug("In PikaProtocol do_publish...")
        if self._connected is None:
            returnValue(None)

        while True:
            try:
                msg = self.factory.send_queue.popleft()
                logger.debug("In PikaProtocol do_publish a: {msg}", msg=msg)
                # print "do_publish: %s"  % msg['properties']
                try:
                    if 'correlation_id' in msg['properties']:
                        if msg['properties']['correlation_id'] in self.factory.AMQPClient.send_correlation_ids:
                            self.factory.AMQPClient.send_correlation_ids[msg['properties']['correlation_id']]['time_sent'] = datetime.now()
                    # logger.debug("exchange={exchange_name}, routing_key={routing_key}, body={body}, properties={properties}",
                    #             exchange_name=msg['exchange_name'], routing_key= msg['routing_key'], body=msg['body'], properties=msg['properties'])
                    msg['properties'] = pika.BasicProperties(**msg['properties'])
                    yield self.channel.basic_publish(exchange=msg['exchange_name'], routing_key=msg['routing_key'], body=msg['body'], properties=msg['properties'])

                except Exception as error:
                    logger.warn("--------==(Error: While sending message.     )==--------")
                    logger.warn("--------------------------------------------------------")
                    logger.warn("{error}", error=sys.exc_info())
                    logger.warn("---------------==(Traceback)==--------------------------")
                    logger.warn("{trace}", trace=traceback.print_exc(file=sys.stdout))
                    logger.warn("--------------------------------------------------------")

            except IndexError:
                break

    def _register_consumer_success(self, tossaway, queue_name):
        self.factory.consumers[queue_name]['subscribed'] = True

    def receive_item(self, item, queue, queue_no_ack, callback):
        """
        This function is called with EVERY incoming message. We don't have logic here, just send to factory.
        """
        (channel, deliver, props, msg,) = item
        # print "protocol1: receive_item"
        # print "protocol: item %s" % item
        # print "protocol: queue %s" % queue
        # print "channel: queue_no_ack %s" % queue_no_ack
        # print "deliver: callback %s" % callback
        # print "props: deliver %s" % deliver
        # print "props: props %s" % props
        # print "props: msg %s" % msg
        # print "msg: item %s" % msg

        if props.correlation_id in self.factory.AMQPClient.send_correlation_ids:
            correlation = self.factory.AMQPClient.send_correlation_ids[props.correlation_id]
            correlation['time_received'] = datetime.now()
        else:
            correlation = None

        d = queue.get()  # get the queue again, so we can add another callback to get the next message.
        d.addCallback(self.receive_item, queue, queue_no_ack, callback)
        d.addErrback(self.receive_item_err)  # todo: use supplied error callback...  which one?

        self._local_log("debug", "PikaProtocol::receive_item, callback: %s" % callback)

#        print "send_correlation_ids: %s" % self.factory.AMQPClient.send_correlation_ids
        if props.correlation_id in self.factory.AMQPClient.send_correlation_ids:
            time_info = self.factory.AMQPClient.send_correlation_ids[props.correlation_id]
            date_time = time_info['time_received'] - time_info['time_sent']
            milliseconds = (date_time.days * 24 * 60 * 60 + date_time.seconds) * 1000 + date_time.microseconds / 1000.0
            logger.debug("Time between sending and receiving a response:: {milliseconds}", milliseconds=milliseconds)

        # if message has a direct callbackk, call that instead of the queue callback
        already_calledback = False
        if correlation is not None:
            if correlation['callback'] is not None:
                if callable(correlation['callback']) is True:
                    logger.warn("calling message callback, not incoming queue callback")
                    already_calledback = True
                    local_callback = correlation['callback']
                    d = defer.maybeDeferred(local_callback, props, msg, correlation)

        if already_calledback is False:
            d = defer.maybeDeferred(callback, props, msg, correlation)
            logger.debug('Called callback: {callback}', callback=callback)

        if not queue_no_ack:
            # if it gets here, it's passed basic checks.
            # logger.debug("AMQP Sending {status} due to valid request. Tag: {tag}",
            #              status='ACK', tag=deliver.delivery_tag)
            d.addCallback(self._basic_ack, channel, deliver.delivery_tag)
            d.addErrback(self._basic_nack, channel, deliver.delivery_tag)

    def receive_item_err(self, error):
        """
        Is caled when an un-caught exception happens while processing an incoming message.

        :param error:
        :return:
        """
        # if error.value == ""
        # if
        if error.value[0] == 200:
            return
        self._local_log("debug", "PikaProtocol::receive_item_err", "Error: %s" % error.__dict__)

    def _basic_ack(self, tossaway, channel, tag):
        self._local_log("debug", "PikaProtocol::_basic_ack", "Tag: %s" % tag)
        channel.basic_ack(tag)

    def _basic_nack(self, error, channel, tag):
        self._local_log("info", "PikaProtocol::_basic_nack for client: %s   Tag: %s" % (self.factory.AMQPClient.client_id, tag))
        logger.error("AMQP nack'd on error: {error}", error=error)
        channel.basic_nack(tag, False, False)
