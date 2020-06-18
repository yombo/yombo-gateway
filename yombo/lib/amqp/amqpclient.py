# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `AMQP @ Library Documentation <https://yombo.net/docs/libraries/amqp>`_

All AMQP connetions are managed by this library. To create a new connection use the
:py:meth:`self._AMQP.new() <AMQP.new>` function to create a new connection. This will return a
:class:`AMQPClient` instance which allows for creating exchanges, queues, queue bindings,
and sending/receiving messages.

To learn more about AMQP, see the `RabbitMQ Tutorials <https://www.rabbitmq.com/getstarted.html>`_.

Yombo Gateway interacts with Yombo servers using AMQPYombo which depends on this library.

.. seealso::

   The :doc:`mqtt library </lib/mqtt>` can connect to MQTT brokers, this a light weight message broker.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2015-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/amqp/amqpclient.html>`_
"""
# Import python libraries
import collections
import pika
from typing import Callable, List, Optional, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet import ssl

# Import Yombo libraries
from yombo.constants import VERSION
from yombo.constants.amqp import KEEPALIVE, PREFETCH_COUNT
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.lib.amqp.amqpfactory import AMQPFactory

logger = get_logger("library.amqp.amqpclient")


class AMQPClient(Entity):
    def __init__(self, parent, client_id: str, hostname: str, port: int, virtual_host: str, username: str,
                 password: str, use_ssl: bool, connected_callbacks: Optional[Union[Callable, List[Callable]]] = None,
                 disconnected_callbacks: Optional[Union[Callable, List[Callable]]] = None,
                 error_callbacks: Optional[Union[Callable, List[Callable]]] = None, keepalive: Optional[int] = None,
                 prefetch_count: Optional[int] = None, critical_connection: Optional[bool] = None):
        """
        Abstracts much of the tasks for AMQP handling. Yombo Gateway libraries and modules should primarily interact
        with these methods.

        Note: Check with your AMQP host to validate you are have permissions before performing many of these tasks.
        Many times, the server will disconnect the session if a request is being made and don't have permission.

        :param parent: Class - A pointer to AMQP library.
        :param client_id: String (default - random) - A client id to use for logging.
        :param hostname: String (required) - IP address or hostname to connect to.
        :param port: Int (required) - Port number to connect to.
        :param virtual_host: String (required) - AMQP virutal host name to connect to.
        :param username: String (Default = None) - Username to connect as. If None, will use the Yombo system username.
          Use "" to not use a username & password.
        :param password: String (Default = None) - Pasword to to connect with. If None, will use the Yombo system
          username. Use "" to not use a password.
        :param use_ssl: bool (Default = True) - Use SSL when attempting to connect to server.
        :param connected_callbacks: method - If you want a function called when connected to server.
        :param disconnected_callbacks: method - If you want a function called when disconnected from server.
        :param error_callbacks: method - A function to call if something goes wrong.
        :param keepalive: Int (default 600) - How many seconds a ping should be performed if there's not recent
          traffic.
        :param prefetch_count: Int (default 10) - How many outstanding messages the client should have at any
          given time.
        """
        super().__init__(parent)

        self._AMQP = parent  # Duplicate reference of self._Parent, for clarity.
        self.client_id = client_id
        self.hostname = hostname
        self.port = port
        self.virtual_host = virtual_host
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.keepalive = keepalive if keepalive is not None else KEEPALIVE
        self.prefetch_count = prefetch_count if prefetch_count is not None else PREFETCH_COUNT
        self.critical_connection = critical_connection if critical_connection is not None else False

        self.connected_callbacks = connected_callbacks
        self.disconnected_callbacks = disconnected_callbacks
        self.error_callbacks = error_callbacks

        self.is_connected = False
        self._connecting = False
        self._disconnecting = False
        self.amqp_factory = AMQPFactory(self)
        self.amqp_factory.noisy = False  # turn off Starting/stopping message

        pika_params = {
            "host": hostname,
            "port": port,
            "virtual_host": virtual_host,
            "heartbeat": keepalive,
            "client_properties": {
                "information": f"https://yombo.net",
                "product": f"Yombo Gateway",
                "version": f"YGW:{VERSION} Pika:{pika.__version__}",
            }
        }

        logger.debug("New pika client: {params}", params=pika_params)
        if username is not None and password is not None:
            self.pika_credentials=pika.PlainCredentials(username, password)
            pika_params["credentials"] = self.pika_credentials
            pika_params["client_properties"]["connection_name"] = username

        self.pika_parameters = pika.ConnectionParameters(**pika_params)

    def _local_log(self, level, location="", msg=""):
        """
        Simple logger function.

        :param level:
        :param location:
        :param msg:
        :return:
        """
        logit = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    def call_callbacks(self, callbacks, *args, **kwargs):
        """
        Calls each callback in a list.

        :param callbacks:
        :return:
        """
        if callbacks is None:
            return

        print(f"call_callbacks, has these to call: {callbacks}")
        for callback in callbacks:
            if callable(callback):
                print(f"call_callbacks: calling callback: {callback}")
                callback(*args, **kwargs)

    def connect(self):
        """
        Called when ready to connect.
        """
        self._local_log("warn", "AMQP::connect")

        if self._connecting is True or self.is_connected is True:
            logger.info(
                    "AMQP Client: {client_id} - Already trying to connect, connect attempt aborted.",
                    client_id=self.client_id)
            return
        self._connecting = True
        if self.use_ssl:
            self.myreactor = reactor.connectSSL(self.hostname, self.port, self.amqp_factory, ssl.ClientContextFactory())
        else:
            self.myreactor = reactor.connectTCP(self.hostname, self.port, self.amqp_factory)

    def connected(self):
        """
        Called by amqp_factory.connected() after successfully registered all queues, exchanges, bindings, and
        subscriptions.
        """
        print("amqpclient - connected..")
        self._AMQP._Events.new("amqp", "connected", (self.client_id,))
        self._local_log("debug", "AMQP Client: {client_id} - Connected")
        self._connecting = False
        self.is_connected = True
        self.timeout_reconnect_task = False

        logger.debug("AMQP Connected...{id}, callbacks: {callbacks}", id=self.client_id, callbacks=self.connected_callbacks)
        self.call_callbacks(self.connected_callbacks)

    def disconnect(self):
        """
        Disconnect from the AMQP service, and tell the connector to not reconnect.
        """
        if self._disconnecting is True or self.is_connected is False:
            return
        self._disconnecting = True

        logger.debug("AMQPClient going to disconnect for client id: {client_id}", client_id=self.client_id)
        self.amqp_factory.stopTrying()
        self.amqp_factory.close()

    def disconnected(self):
        """
        Function is called when the Gateway is disconnected from the AMQP service.
        """
        self._AMQP._Events.new("amqp", "disconnected", (self.client_id, ""))
        logger.info("AMQP Client {client_id} disconnected. Will usually auto-reconnected.", client_id=self.client_id)
        self.is_connected = False
        self.call_callbacks(self.disconnected_callbacks)

    def register_exchange(self, exchange_name: str, exchange_type: str,
                          exchange_durable: Optional[bool] = None, register_persist: Optional[bool] = None,
                          exchange_auto_delete: Optional[bool] = None):
        """
        Register an exchange with the server.

        For details on these actions, please review any AMQP guide.

        :param exchange_name: String (required) - Name of exchange to create
        :param exchange_type: String (required) - Type of AMQP exchange. One of: direct, fanout, topic.
        :param exchange_durable: Bool (default = False) - If the exchange should persist data to disk.
        :param register_persist: Bool (default = True) - If exchange should be re-created on re-connect.
        :param exchange_auto_delete: Bool (default = False) - If the exchange should auto delete when last
           consumer disconnects.
        :return:
        """
        if exchange_durable is None:
            exchange_durable = False
        if register_persist is None:
            register_persist = True
        if exchange_auto_delete is None:
            exchange_auto_delete = False

        self.amqp_factory.register_exchange(exchange_name, exchange_type, exchange_durable, register_persist,
                                            exchange_auto_delete)

    def register_queue(self, queue_name, queue_durable: Optional[bool] = None,
                       queue_arguments: Optional[dict] = None, register_persist: Optional[bool] = None):
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

        self.amqp_factory.register_queue(queue_name, queue_durable, queue_arguments, register_persist)

    def register_exchange_queue_binding(self, exchange_name: str, queue_name: str,
                                        routing_key: Optional[str] = None, register_persist: Optional[bool] = None):
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
                f"AMQP Client '{self.client_id}' - register_exchange_queue_binding must have a routing key!",
                    203, "register_exchange_queue_binding", "AMQPClient")
        if register_persist is None:
            register_persist = False

        self.amqp_factory.register_exchange_queue_binding(exchange_name, queue_name, routing_key,
                                                          register_persist)

    def subscribe(self, queue_name: str, incoming_callbacks: Union[List[Callable], Callable],
                  error_callbacks: Optional[Union[List[Callable], Callable]] = None,
                  auto_ack: Optional[bool] = True, persistent: Optional[bool] = None):
        self._local_log("debug", "AMQPClient::subscribe", f"queue_name: {queue_name}")

        auto_ack = auto_ack if isinstance(auto_ack, bool) else True
        persistent = persistent if isinstance(persistent, bool) else False

        incoming_callbacks = self._AMQP.check_callbacks(incoming_callbacks, "incoming_callbacks")
        error_callbacks = self._AMQP.check_callbacks(error_callbacks, "error_callbacks")
        self.amqp_factory.subscribe(queue_name, incoming_callbacks, error_callbacks, auto_ack, persistent)

    def unsubscribe(self, queue_name: str):
        """Unsubscribe from a queue."""
        self.amqp_factory.unsubscribe(queue_name)

    def publish(self, **kwargs):
        """
        Used to send a message to the AMQP server. Can direct responses back to a callbacks, if defined. Otherwise,
        responses will be tossed to /dev/null.

        The following items in the kwargs are allowed/required.

        :param exchange_name:
        :param properties: Dict - A dictionary of properties that is passed to pika.BasicProperties.
        :param routing_key: String (required) - A routing key is required when sending messages. For security,
          default routing is not allowed.
        :param body: Any - Any data that should be sent in the AMQP message payload.
        """
        # self._local_log("debug", "AMQPClient::send_amqp_message", "Message: %s" % kwargs)
        meta = kwargs.get("meta", {})

        callbacks = kwargs.get("callbacks", None)
        if callbacks is not None:
            if isinstance(callbacks, list) is False:
                callbacks = [callbacks]
            for callback in callbacks:
                if isinstance(callback, collections.Callable) is False:
                    raise YomboWarning(
                        f"AMQP Client '{self.client_id}' - If callbacks is set, it must be be callable.",
                        200, "publish", "AMQPClient")

        exchange_name = kwargs.get("exchange_name", None)
        if exchange_name is None:
            raise YomboWarning(
                f"AMQP Client '{self.client_id}' - Must have exchange_name to publish to.",
                201, "publish", "AMQPClient")

        body = kwargs.get("body", None)
        if body is None:
            raise YomboWarning(
                f"AMQP Client '{self.client_id}' - Must have a body.",
                202, "publish", "AMQPClient")

        kwargs["meta"] = meta
        return self.amqp_factory.publish(**kwargs)
