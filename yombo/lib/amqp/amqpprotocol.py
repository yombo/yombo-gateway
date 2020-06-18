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
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/amqp/ampprotocol.html>`_
"""
# Import python libraries
from pika.spec import BasicProperties
from pika.adapters import twisted_connection
import sys
import traceback
from time import time
from typing import Callable, List, Optional, Union

# Import twisted libraries
from twisted.internet.error import ConnectionDone
from twisted.internet.defer import inlineCallbacks, maybeDeferred, DeferredList

# Import Yombo libraries
from yombo.core.log import get_logger

logger = get_logger("library.amqp.amqpprotocol")


class AMQPProtocol(twisted_connection.TwistedProtocolConnection):
    """
    Responsible for low level handling. Does the actual work of setting up any exchanges, queues, and bindings. Also
    sends greeting and initial handshake.

    On connect, it always sends a message to let Yombo know of it's pertinent information.
    """
    def __init__(self, factory):
        """
        Save pointer to factory and then call it's parent __init__.
        """
        self._channel = None
        self.do_send_types = {
            "queue": self.send_queue_registration,
            "exchange": self.send_exchange_registration,
            "binding": self.send_exchange_queue_bindings,
            "subscribe": self.send_subscribe_request,
            "message": self.publish_message,
        }

        self.factory = factory
        self.is_connected = False
        super(AMQPProtocol, self).__init__(
            parameters=self.factory.AMQPClient.pika_parameters)

    def _local_log(self, level: str, location: str = "", msg: str = ""):
        logit = getattr(logger, level)
        logit("In {location} : {msg}", location=location, msg=msg)

    @inlineCallbacks
    def connectionReady(self):
        """
        Called by the Pika adapter when the connection is ready. This function will create a single channel which
        all AMQP communications will use.
        """
        print("connectionReady!")
        self.factory.resetDelay()  # Per twistd docs, this must be called after successful connection.
        self._channel = yield self.channel()
        yield self._channel.basic_qos(prefetch_count=self.factory.AMQPClient.prefetch_count)
        self._channel._channel.add_on_close_callback(self.on_connection_closed)
        self._channel._channel.add_on_cancel_callback(self.on_consumer_cancelled)
        self.is_connected = True
        yield self.factory.connected()  # Let the factory know we are online!
        print("connectionReady done")

    def on_consumer_cancelled(self, method_frame):
        """
        Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer
        receiving messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame
        """
        logger.warn("Protocol:on_consumer_cancelled - {client_id}: {notes}",
                    client_id=self.factory.AMQPClient.client_id,
                    notes=method_frame)
        if self._channel:
            self._channel.close()

    def on_connection_closed(self, connection, error: str):
        """
        This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.

        :param connection: The closed connection obj
        :param error: The exception/error for why the connection was closed.
        """
        logger.info("AMQP Connection closed. {client_id}: {error}",
                    client_id=self.factory.AMQPClient.client_id,
                    error=error)
        # print(f"on_connection_closed, error type: {type(error).__name__}")
        # print(f"on_connection_closed, connection: {connection}")
        self.is_connected = False
        self.factory.disconnected()

    @inlineCallbacks
    def send_item(self, item):
        """
        Receives items to send to the AMQP server and is received from the AMQPFactory. Multiple items may be in
        flight at once.

        :return:
        """
        yield self.do_send_types[item["type"]](item)

    @inlineCallbacks
    def send_queue_registration(self, item):
        """
        Performs the actual registration of queues.
        """
        fields = item["fields"]

        logger.debug("Protocol:send_queue_registration - {client_id} - {fields}",
                     client_id=self.factory.AMQPClient.client_id,
                     fields=fields)
        queue_name = fields["queue_name"]
        yield self._channel.queue_declare(
            queue=fields["queue_name"],
            durable=fields["queue_durable"],
            arguments=fields["queue_arguments"])
        if queue_name in self.factory.queues:
            self.factory.queues[queue_name]["registered"] = True

    @inlineCallbacks
    def send_exchange_registration(self, item):
        """
        Performs the actual registration of exchanges.
        """
        fields = item["fields"]

        logger.debug("Protocol:send_exchange_registration - {client_id} - {fields}",
                     client_id=self.factory.AMQPClient.client_id,
                     fields=fields)

        # self._local_log("debug", "AMQPProtocol::do_send_exchange")
        exchange_name = fields["exchange_name"]
        yield self._channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=fields["exchange_type"],
            durable=fields["exchange_durable"],
            auto_delete=fields["exchange_auto_delete"])
        if exchange_name in self.factory.exchanges:
            self.factory.exchanges[exchange_name]["registered"] = True

    @inlineCallbacks
    def send_exchange_queue_bindings(self, item):
        """
        Performs the actual registration of exchange_queue_bindings.
        """
        fields = item["fields"]

        logger.debug("Protocol:send_exchange_queue_bindings - {client_id} - {fields}",
                     client_id=self.factory.AMQPClient.client_id,
                     fields=fields)
        queue_name = fields["queue_name"]
        exchange_name = fields["exchange_name"]
        yield self._channel.queue_bind(
            exchange=fields["exchange_name"],
            queue=fields["queue_name"],
            routing_key=fields["routing_key"])
        name = exchange_name+queue_name
        if name in self.factory.exchange_queue_bindings:
            self.factory.exchange_queue_bindings[name]["registered"] = True

    @inlineCallbacks
    def send_subscribe_request(self, item):
        """
        Performs the actual binding of the queue to the AMQP channel.
        """
        fields = item["fields"]

        logger.debug("Protocol:send_subscribe_request - {client_id} - {fields}",
                     client_id=self.factory.AMQPClient.client_id,
                     fields=fields)
        queue_name = fields["queue_name"]
        (queue, consumer_tag) = yield self._channel.basic_consume(queue=queue_name, auto_ack=fields["auto_ack"])

        d = queue.get()
        d.addCallback(self.receive_item, queue, fields["auto_ack"], fields["incoming_callbacks"])
        if fields["error_callbacks"] is not None:
            d.addErrback(fields["error_callbacks"])
        else:
            d.addErrback(self.receive_item_err)
        d.addCallback(self._register_consumer_success, queue_name)
        if queue_name in self.factory.subscriptions:
            self.factory.subscriptions[queue_name]["registered"] = True

    def _register_consumer_success(self, tossaway, queue_name):
        self.factory.subscriptions[queue_name]["registered"] = True

    @inlineCallbacks
    def publish_message(self, item):
        """
        Sends an AMQP message
        """
        fields = item["fields"]
        priority = item["priority"]
        logger.debug("Protocol:publish_message - {client_id} - {priority} - {item}",
                     client_id=self.factory.AMQPClient.client_id,
                     priority=priority,
                     item=item)
        try:
            message_meta = fields["message_meta"]
            fields["properties"] = BasicProperties(**fields["properties"])
            fields["properties"].headers["msg_sent_at"] = str(time())
            # This was not found for sslcert - was published before connection resquest! Find out why.
            yield self._channel.basic_publish(exchange=fields["exchange_name"],
                                              routing_key=fields["routing_key"],
                                              body=fields["body"],
                                              properties=fields["properties"])

            message_meta["msg_sent_at"] = float(time())
            message_meta["send_success"] = True

        except Exception as error:
            logger.warn("--------==(Error: While sending message.     )==--------")
            logger.warn("--------------------------------------------------------")
            logger.warn("{error}", error=sys.exc_info())
            logger.warn("---------------==(Traceback)==--------------------------")
            logger.warn("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.warn("--------------------------------------------------------")
            message_meta["send_success"] = False

    def receive_item(self, item, queue, auto_ack, incoming_callbacks):
        """
        This function is called with EVERY incoming message. We don't have logic here, just send to factory.
        """
        (channel, deliver, properties, message) = item

        queue_deferred = queue.get()  # get the queue again, so we can add another callback to get the next message.
        queue_deferred.addCallback(self.receive_item, queue, auto_ack, incoming_callbacks)
        queue_deferred.addErrback(self.receive_item_err)  # todo: use supplied error callback...  which one?

        received_callbacks = []
        for callback in incoming_callbacks:
            received_callbacks.append(maybeDeferred(callback,
                                                    channel=channel,
                                                    deliver=deliver,
                                                    properties=properties,
                                                    message=message)
                                      )
        if auto_ack is False:
            received = DeferredList(received_callbacks, fireOnOneErrback=True, consumeErrors=True)
            received.addCallback(self._basic_ack, channel, deliver.delivery_tag)
            received.addErrback(self._basic_nack, channel, deliver.delivery_tag)

    def receive_item_err(self, error):
        """
        Is caled when an un-caught exception happens while processing an incoming message.

        :param error:
        :return:
        """
        if hasattr(error, "value") and isinstance(error.value, ConnectionDone):
            logger.debug("receive_item_err due to client has been disconnected.")
            return
        logger.warn("AQMP Client '{client}' has a receive error: {error}",
                    client=self.factory.AMQPClient.client_id, error=error)

    def _basic_ack(self, tossaway, channel, tag):
        self._local_log("debug", "AMQPProtocol::_basic_ack", f"Tag: {tag}")
        channel.basic_ack(tag)

    def _basic_nack(self, error, channel, tag):
        self._local_log("info",
                        f"PikaProtocol::_basic_nack for client: {self.factory.AMQPClient.client_id},"
                        f" Tag: {tag}, Error: {error}")
        logger.error("AMQP nack'd on error: {error}", error=error)
        channel.basic_nack(tag, False, False)
