# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This handler library is responsible for handling control messages received from amqpyombo library.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/amqpyombo/control.html>`_
"""
# Import python libraries
from typing import Any, ClassVar, Dict, List, Optional, Union
import json

# Import twisted libraries

# Import 3rd party extensions

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.lib.amqpyombo.amqphandlerbase import AmqpHandlerBase

logger = get_logger("library.amqpyombo.control")


class AmqpControl(Entity, AmqpHandlerBase):
    """
    Handles interactions with Yombo servers through the AMQP library.
    """
    _Entity_type: ClassVar[str] = "AMQP control"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_system_control: bool = \
            self._Configs.get("security.amqp.allow_system_control", True, instance=True)
        self.allow_device_control: bool = \
            self._Configs.get("security.amqp.allow_device_control", True, instance=True)

    def amqp_incoming_requests(self, **kwargs) -> None:
        request_sub_type = kwargs["message_headers"]["request_sub_type"]
        if request_sub_type == "system":
            self.process_system_control(**kwargs)
        elif request_sub_type == "device":
            self.process_device_control(**kwargs)
        else:
            logger.warn("AMQP:Handler:Control - Received unknown request_type: {request_sub_type}",
                        request_sub_type=request_sub_type)

    def process_system_control(self, message=None, message_headers=None, **kwargs) -> None:
        logger.warn("received system control request: {message}", message=message)

        # Todo: Do system command
        # Todo: Come up with a list of system commands. =)
        return

    def process_device_control(self, message=None, message_headers=None, **kwargs) -> None:
        logger.warn("received device control request: {message}", message=message)
        device_id = message["device_id"]
        command_id = message["command_id"]

        if device_id not in self._Devices:
            logger.warn("Unable to process remote device command request, device_id is invalid.")
            return
        if command_id not in self._Commands:
            logger.warn("Unable to process remote device command request, device_id is invalid.")
            return

        # Todo: do device command....
