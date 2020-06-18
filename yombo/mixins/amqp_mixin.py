"""
Mixin class allows libraries and modules to easily interact with the AMQPYombo library. This mixin
can receive the raw AMQP message, process it through AMQPYombo.incoming_raw, and then call either
amqp_incoming_request or amqp_incoming_response depending on the message type.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/mixins/amqp_mixin.html>`_
"""
from twisted.internet.defer import inlineCallbacks, maybeDeferred

from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("mixins.amqp_mixin")


class AMQPMixin:
    @inlineCallbacks
    def amqp_incoming(self, channel, deliver, properties, message):
        """
        Receives the raw AMQP message from the AMQP server. First, call 'AMQPYombo::incoming_raw' to validate and get
        something usable. Then, route the message to the proper handler.

        This callback is setup from the subscribe() method when the gateway is connected.

        :param channel:
        :param deliver:
        :param properties:
        :param message:
        :return:
        """
        data = self._AMQPYombo.incoming_raw(channel, deliver, properties, message)

        # logger.info("Received incoming message: {headers}", body=headers)
        # logger.info("Received incoming message: {body}", body=body)

        # Do one last final check.
        message_headers = data["message_headers"]
        if message_headers["message_type"] == "request":
            if "request_type" not in message_headers:
                raise YomboWarning("Discarding request message, header 'request_type' is missing.")
        if message_headers["message_type"] == "response":
            if "response_type" not in message_headers:
                raise YomboWarning("Discarding request message, header 'response_type' is missing.")

        yield self.amqp_incoming_routing(**data)

    @inlineCallbacks
    def amqp_incoming_routing(self, **kwargs):
        """
        Route the incoming message

        :param channel:
        :param deliver:
        :param properties:
        :param message:
        :param data:
        :return:
        """
        message_headers = kwargs["message_headers"]
        if message_headers["message_type"] == "request":
            yield maybeDeferred(self.amqp_incoming_request, **kwargs)
        if message_headers["message_type"] == "response":
            yield maybeDeferred(self.amqp_incoming_response, **kwargs)

    def amqp_incoming_request(self, message=None, message_headers=None, **kwargs):
        """
        This method should be implemented by any modules expecting to receive amqp incoming requests.
        """
        pass

    def amqp_incoming_request(self, message=None, message_headers=None, **kwargs):
        """
        This method should be implemented by any modules expecting to receive amqp incoming responses.
        """
        pass
