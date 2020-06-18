"""
Base handler for AMQP incoming items.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/amqpyombo/amqpbase.html>`_
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred

# Import Yombo libraries
from yombo.core.log import get_logger

logger = get_logger("library.amqpyombo.amqphandlerbase")


class AmqpHandlerBase:
    """
    Handles interactions with Yombo servers through the AMQP library.
    """
    @inlineCallbacks
    def amqp_incoming(self, **kwargs) -> None:
        message_type = kwargs["message_headers"]["message_type"]
        if message_type == "request":
            results = yield maybeDeferred(self.amqp_incoming_request, **kwargs)
            return results
        if message_type == "response":
            results = yield maybeDeferred(self.amqp_incoming_response, **kwargs)
            return results
        logger.warn("AMQP:Base - Received unknown message_type: {message_type}",
                    message_type=message_type)

    def _stop_(self) -> None:
        pass
