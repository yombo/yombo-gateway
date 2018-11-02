# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This handler library is responsible for handling control messages received from amqpyombo library.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/handler/amqpcontrol.py>`_
"""
# Import python libraries
import json

# Import twisted libraries

# Import 3rd party extensions

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger("library.amqpyomb_handlers.amqpcontrol")


class AmqpControlHandler(YomboLibrary):
    """
    Handles interactions with Yombo servers through the AMQP library.
    """

    def __init__(self, amqpyombo):
        """
        Loads various variables and calls :py:meth:connect() when it's ready.

        :return:
        """
        self.parent = amqpyombo
        self._Devices = self.parent._Devices

    def amqp_incoming_request(self, headers, body, **kwargs):
        request_type = headers["request_type"]
        if request_type == "control":
            self.process_request_control(headers, **kwargs)
        else:
            logger.warn("AMQP:Handler:Control - Received unknown request_type: {request_type}",
                        request_type=request_type)


    def process_request_control(self, deliver, properties, headers, body, **kwargs):
        logger.warn("recieved device-command request: {body}", body=body)
        request = body["request"]
        print(f"Process control: {request}")
        device_id = request["device"]["id"]

        if device_id in self._Devices:
            device = self._Devices[request["device"]["id"]]
            device.command(request["command"]["id"])

    def _stop_(self):
        pass
