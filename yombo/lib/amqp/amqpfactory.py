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
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/amqp/amqpfactory.html>`_
"""
# Import python libraries
from collections import deque
from hashlib import sha256
from os import getcwd
from random import uniform
from time import time
from typing import Callable, List, Optional, Union

# Import twisted libraries
from twisted.internet import protocol, reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.lib.amqp.amqpprotocol import AMQPProtocol
from yombo.utils import sleep, random_string, unicode_to_bytes

logger = get_logger("library.amqp.amqpfactory")


class AMQPFactory(protocol.ReconnectingClientFactory):
    """
    Responsible for setting up the factory, building the protocol and then connecting.
    """
    @property
    def is_connected(self):
        if hasattr(self, "AMQPProtocol") and self.AMQPProtocol is not None and self.AMQPProtocol.is_connected is True:
            return True
        return False

    def __init__(self, AMQPClient):
        self._local_log("debug", "AMQPFactory::__init__")
        self._Name = self.__class__.__name__
        self._ClassPath = __file__[len(getcwd())+1:].split(".")[0].replace("/", ".")
        self._FullName = f"{self._ClassPath}:{self._Name}"

        # DO NOT CHANGE THESE!  Mitch Schwenk @ yombo.net
        # These are used for when reconnecting to the gateway, not the first connection.
        # Its used to randomly reconnect back between ~.5 and ~9 seconds, and then backs-off
        # after continued non-connections. This gives some breathing room for the servers
        # so that not all clients reconnect at the same exact time.
        self.initialDelay = uniform(.5, 8)
        self.jitter = 0.25  # How much to randomly increment the delay time between retries.
        self.factor = 1.513  # How much to jump to the next higher delay value.
        self.maxDelay = 60  # This puts retries around 55-60 seconds

        self.AMQPClient = AMQPClient
        self.AMQPProtocol = None

        self.send_queue = deque()  # stores any received items like publish and subscribe until fully connected
        self.exchanges = {}  # store a list of exchanges, will try to re-establish on reconnect.
        self.queues = {}  # store a list of queue, will try to re-establish on reconnect.
        self.exchange_queue_bindings = {}  # store a list of exchange queue bindings, will try to re-establish.
        self.subscriptions = {}  # store a list of consumers, will try to re-establish on reconnect.

        logger.debug(f"AMQPProtocol __init__ - about to setup delivery_queue")
        self.delivery_queue = {
            "registrations": deque(),  # queues, exchanges
            "bindings": deque(),   # bindings
            "subscriptions": deque(),  # subsciptions
            "high": deque(),
            "normal": deque(),
            "low": deque(),
            }
        self.check_delivery_queue_running = False
        self.registration_types = {
            "queue": {"priority": "registrations", "ref": self.queues},
            "exchange": {"priority": "registrations", "ref": self.exchanges},
            "binding": {"priority": "bindings", "ref": self.exchange_queue_bindings},
            "subscribe": {"priority": "subscriptions", "ref": self.subscriptions},
        }

    def _local_log(self, level, location, msg=""):
        logit = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    def buildProtocol(self, addr):
        """Build the AMQPProtocol."""
        self._local_log("info", "AMQPFactory::buildProtocol")
        self.delay = 2
        self.retries = 0
        self._callID = None
        self.continueTrying = 1
        self.AMQPProtocol = AMQPProtocol(self)
        return self.AMQPProtocol

    def close(self):
        """
        Called from AMQPYombo._unload_, usually when gateway is shutting down.
        :return:
        """
        self._local_log("debug", "!!!!AMQPFactory::close")
        self.AMQPProtocol.close()

    @inlineCallbacks
    def connected(self) -> None:
        """
        Called by AMQPProtocol when the connection is ready to use. We'll take this time to deliver any
        queued items.
        """
        self.check_registrations("queue", call_check_delivery=False)
        self.check_registrations("exchange", call_check_delivery=False)
        yield sleep(0.07)
        self.check_registrations("binding", call_check_delivery=False)
        self.check_registrations("subscribe", call_check_delivery=False)
        yield sleep(0.03)

        yield self.do_check_delivery_queue()  # Send any queued items to the server.
        self.AMQPClient.connected()  # Let the factory know we are online!

    def disconnected(self):
        """
        Called by AMQPProtocol when the connection closes. This resets all items that needs to be
        re-registered with the AMQP server, such as subscriptions (consumers).

        :return:
        """
        logger.debug("AQMP disconnected, resetting persistent actions.")
        for queue in [self.exchanges, self.queues, self.exchange_queue_bindings, self.subscriptions]:
            for item_key, queued_item in queue.items():
                if queued_item["register_persist"]:
                    queued_item["registered"] = False
                    queued_item["queued"] = False

        self.AMQPClient.disconnected()

    #############################################################################
    # These methods are meant to be called externally to perform various tasks. #
    #############################################################################
    def register_queue(self, queue_name: str, queue_durable: bool, queue_arguments: bool, register_persist: bool):
        """
        Request a new queue. Simply adds to the queue to be processed when the connection
        is fully established.

        :param queue_name:
        :param queue_durable:
        :param queue_arguments:
        :param register_persist:
        :return:
        """
        logger.debug("Factory:register_queue - {queue_name}", queue_name=queue_name)

        if queue_name in self.queues:
            raise YomboWarning(
                f"AMQP Protocol {self.AMQPClient.client_id} - Already has a queue: {queue_name}",
                    200, "register_exchange", "AMQPFactory")

        self.queues[queue_name] = {
            "registered": False,
            "queued": False,
            "queue_name": queue_name,
            "queue_durable": queue_durable,
            "queue_arguments": queue_arguments,
            "register_persist": register_persist,
        }
        self.check_registrations("queue")

    def register_exchange(self, exchange_name: str, exchange_type: str, exchange_durable: bool,
                          register_persist: bool, exchange_auto_delete: bool):
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
        logger.debug("Factory:register_exchange - {exchange_name}", exchange_name=exchange_name)
        if exchange_name in self.exchanges:
            raise YomboWarning(
                f"AMQP Protocol:{self.AMQPClient.client_id} - Already has an exchange_name: {exchange_name}",
                200, "register_exchange", "AMQPFactory")

        self.exchanges[exchange_name] = {
            "registered": False,
            "queued": False,
            "exchange_name": exchange_name,
            "exchange_type": exchange_type,
            "exchange_durable": exchange_durable,
            "register_persist": register_persist,
            "exchange_auto_delete": exchange_auto_delete,
        }
        self.check_registrations("exchange")

    def register_exchange_queue_binding(self, exchange_name: str, queue_name: str, routing_key: str,
                                        register_persist: bool):
        """
        Request a new exchange->queue binding. Simply adds to the queue to be processed when the
        connection is fully established.

        :param exchange_name:
        :param queue_name:
        :param routing_key:
        :param register_persist:
        :return:
        """
        logger.debug("Factory:register_exchange_queue_binding - exchange_name:{exchange_name}, queue_name:{queue_name}",
                     exchange_name=exchange_name, queue_name=queue_name)
        eqb_name = sha256(unicode_to_bytes(exchange_name + queue_name + routing_key)).hexdigest()
        if eqb_name in self.exchange_queue_bindings:
            raise YomboWarning(
                f"AMQP Protocol:{self.AMQPClient.client_id} - Already has an exchange-queue-routing key binding: "
                f"{exchange_name}-{queue_name}-{routing_key}", 200, "register_exchange", "AMQPFactory")

        self.exchange_queue_bindings[exchange_name+queue_name] = {
            "registered": False,
            "queued": False,
            "exchange_name": exchange_name,
            "queue_name": queue_name,
            "routing_key": routing_key,
            "register_persist": register_persist,
        }
        self.check_registrations("binding")

    def subscribe(self, queue_name: str, incoming_callbacks: Union[List[Callable], Callable],
                  error_callbacks: Union[List[Callable], Callable], auto_ack: bool, register_persist: bool):
        """
        Setups of a new subscription. Creates a new queue items to completed when the connection is
        up.

        :param queue_name:
        :param incoming_callbacks:
        :param error_callbacks:
        :param auto_ack:
        :param register_persist:
        :return:
        """
        logger.debug("Factory:subscribe - {queue_name}", queue_name=queue_name)
        if queue_name in self.subscriptions:
            raise YomboWarning(
                f"AMQP Protocol:{self.AMQPClient.client_id} - Already subscribed to queue_name: {queue_name}",
                200, "subscribe", "AMQPFactory")

        self.subscriptions[queue_name] = {
            "registered": False,
            "queued": False,
            "queue_name": queue_name,
            "incoming_callbacks": incoming_callbacks,
            "error_callbacks": error_callbacks,
            "auto_ack": auto_ack,
            "register_persist": register_persist,
        }
        self.check_registrations("subscribe")

    def publish(self, **kwargs):
        """
        Queues up the message, and asks the protocol to send if connected.
        """
        logger.debug("factory:publish: {kwargs}", kwargs=kwargs)

        properties = kwargs.get("properties", {})

        callback_type = None
        callback_name = None
        callback_function = None
        callback = kwargs.get("callback", None)
        if callback is not None:
            if isinstance(callback, dict):
                try:
                    callback_type = callback["callback_component_type"]
                    callback_name = callback["callback_component_type_name"]
                    callback_function = callback["callback_component_type_function"]
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
            elif callable(callback) is False:
                raise YomboWarning(
                    f"AMQP Client:{self.client_id} - If callback is set, it must be be callable.",
                    201, "publish", "AMQPClient")

        else:
            callback_type = None
            callback_name = None
            callback_function = None
            callback = None

        exchange_name = kwargs.get("exchange_name", None)
        if exchange_name is None:
            raise YomboWarning(
                    "AMQP Client:{client_id} - Must have exchange_name to publish to." % self.client_id,
                    202, "publish", "AMQPClient")

        body = kwargs.get("body", None)
        if body is None:
            raise YomboWarning(
                    "AMQP Client:{client_id} - Must have a body." % self.client_id,
                    203, "publish", "AMQPClient")

        kwargs["routing_key"] = kwargs.get("routing_key", "*")
        correlation_id = None
        if "correlation_id" in properties:
            correlation_id = properties["correlation_id"]

        if callback is not None:
            if correlation_id is None:
                correlation_id = random_string(length=24)
                properties["correlation_id"] = correlation_id

        reply_correlation_id = None
        if "reply_correlation_id" in properties:
            reply_correlation_id = properties["reply_correlation_id"]

        properties["user_id"] = self.AMQPClient.username
        kwargs["properties"] = properties

        message_meta = {
            "content_type": None,
            "msg_created_at": time(),
            "msg_sent_at": None,
            "received_at": None,
            "direction": "outgoing",
            "correlation_id": correlation_id,
            "reply_correlation_id": reply_correlation_id,
            "reply_at": None,
            "round_trip_timing": None,
            "payload_size": len(body),
            "uncompressed_size": None,
            "compression_percent": None,
        }
        if "content_encoding" in properties:
            message_meta["content_encoding"] = properties["content_encoding"]
        if "content_type" in properties:
            message_meta["content_type"] = properties["content_type"]

        meta = kwargs.get("meta", {})
        if len(meta) > 0:
            message_meta.update(meta)

        if message_meta["msg_created_at"] is None:
            meta["msg_created_at"] = time()

        correlation_info = None
        if correlation_id is not None:
            correlation_info = {
                "callback": callback,
                "callback_component_type": callback_type,  # module or component
                "callback_component_type_name": callback_name,  # module of component name
                "callback_component_type_function": callback_function,  # name of the function to call
                "correlation_id": correlation_id,
                "correlation_at": time()
            }

        kwargs["message_meta"] = message_meta
        if "callback" in kwargs:
            del kwargs["callback"]

        priority = "normal"
        if "priority" in properties:
            priority = properties["priority"]

        self.delivery_queue[priority].append({
            "type": "message",
            "priority": priority,
            "fields": kwargs,
        })

        self.check_delivery_queue()

        return {
            "message_meta": message_meta,
            "correlation_info": correlation_info,
        }

    ##########################################################################
    # From here on, these are internal methods to handle queuing and sending #
    # items to the AMQP server.                                              #
    ##########################################################################
    def check_delivery_queue(self):
        """
        This simply calls do_check_delivery_queue, but without the burden of a deferred.
        """
        reactor.callLater(0.0001, self.do_check_delivery_queue)

    @inlineCallbacks
    def do_check_delivery_queue(self):
        """
        Checks if there are items in the queue that need to be sent, and sends them. This should be called whenever
        a queue, exchange, binding, subscription or even messages.
        """
        # Don't do anything if we're not connected yet.
        if self.AMQPProtocol is None or self.AMQPClient.is_connected is False:
            return

        def _get_delivery_item():
            """
            Get a single item to be delivered to the AMQP broker.
            :return:
            """
            for priority in ["registrations", "bindings", "subscriptions", "high", "normal", "low"]:
                if len(self.delivery_queue[priority]) > 0:
                    return self.delivery_queue[priority].popleft()
            return None

        if self.check_delivery_queue_running is True:
            return None
        self.check_delivery_queue_running = True

        while True:
            item = _get_delivery_item()
            if item is None:
                break
            try:

                yield self.AMQPProtocol.send_item(item)
            except Exception as e:
                logger.warn("Unable to send item, putting back into queue: {e}", e=e)
                self.delivery_queue[item["priority"]].appendleft(item)
                break

        self.check_delivery_queue_running = False

    def check_registrations(self, register_type: str = None, call_check_delivery: Optional[bool] = None):
        """
        Looks through various items to register, and adds them to the queue.

        :param register_type: Type of registration: queue, exchange, binding, subscribe
        :param call_check_delivery: If False, won't call "check_delivery_queue"
        """
        logger.debug("check_registrations, todo: {register_type}", register_type=register_type)
        to_process = self.registration_types[register_type]["ref"]
        priority = self.registration_types[register_type]["priority"]
        pending = False
        for register_item in list(to_process.keys()):
            fields = to_process[register_item]
            if fields["queued"] is True:
                continue
            if fields["registered"] is False:
                logger.debug("check_registrations, adding to {register_type}: fields - {fields}",
                             register_type=register_type, fields=fields)
                pending = True
                self.delivery_queue[priority].append({
                    "priority": priority,
                    "type": register_type,
                    "fields": fields,
                })
                fields["queued"] = True
            if fields["register_persist"] is False:
                del to_process[register_item]
        if pending and call_check_delivery in (None, True):
            self.check_delivery_queue()
