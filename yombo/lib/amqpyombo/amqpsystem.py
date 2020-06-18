# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This handler library is responsible for handling system messages received from amqpyombo library.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/amqpyombo/system.html>`_
"""
# Import python libraries
from typing import Any, ClassVar, Dict, List, Optional, Union

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.log import get_logger
from yombo.lib.amqpyombo.amqphandlerbase import AmqpHandlerBase

logger = get_logger("library.amqpyombo.amqpsystem")


class AmqpSystem(Entity, AmqpHandlerBase):
    """
    Handles interactions with Yombo servers through the AMQP library.
    """
    _Entity_type: ClassVar[str] = "AMQP System"

    def _stop_(self):
        pass

    def amqp_incoming_requests(self, **kwargs) -> None:
        """
        Handles requests from the Yombo server.
        """
        request_type = kwargs["message_headers"]["request_type"]
        if request_type == "ping":
            self.process_request_ping(**kwargs)
        else:
            logger.warn("AMQP:Handler:System - Received unknown request_type: {response_type}",
                        request_type=request_type)

    def amqp_incoming_response(self, **kwargs) -> None:
        """
        Handles responses to system calls to yombo servers.
        """
        response_type = kwargs["message_headers"]["response_type"]
        if response_type == "ping":
            self.process_response_ping(**kwargs)
        elif response_type == "connected":
            self.process_response_connected(**kwargs)
        else:
            logger.warn("AMQP:Handler:System - Received unknown response_type: {response_type}",
                        response_type=response_type)

    def process_request_ping(self, **kwargs) -> None:
        logger.warn("received ping request...we currently don't respond to these.")

    def process_response_connected(self, **kwargs) -> None:
        logger.warn("Yombo AMQP connection response accepted, now what?")

