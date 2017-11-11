# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This handler library is responsible for handling system messages received from amqpyombo library.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/handler/amqpcontrol.py>`_
"""
# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

# Import twisted libraries

# Import 3rd party extensions

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('library.handler.amqpcontrol')


class AmqpSystemHandler(YomboLibrary):
    """
    Handles interactions with Yombo servers through the AMQP library.
    """

    def __init__(self, amqpyombo):
        """
        Loads various variables and calls :py:meth:connect() when it's ready.

        :return:
        """
        self.parent = amqpyombo

    def _stop_(self):
        pass

    def amqp_incoming_requests(self, headers, body, properties, **kwargs):
        """
        Handles requests from the Yombo server.
        """
        request_type = headers['request_type']
        if request_type == "ping":
            self.process_request_ping(headers, body, properties, **kwargs)
        else:
            logger.warn("AMQP:Handler:System - Received unknown request_type: {response_type}",
                        request_type=request_type)

    def amqp_incoming_response(self, headers, body, properties, **kwargs):
        """
        Handles responses to system calls to yombo servers.
        """

        response_type = headers['response_type']
        if response_type == "ping":
            self.process_response_ping(headers, body, properties, **kwargs)
        else:
            logger.warn("AMQP:Handler:System - Received unknown response_type: {response_type}",
                        response_type=response_type)

    def process_request_ping(self, deliver, properties, headers, body, **kwargs):
        print("received ping request....")

    def process_response_ping(self, headers, body, properties, **kwargs):
        print("received ping response....")

