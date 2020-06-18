# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. warning::

   This library is not intended to be accessed by module developers or end users. These functions, variables,
   and classes were not intended to be accessed directly by modules. These are documented here for completeness.

.. note::

  * For library documentation, see: `MQTTYombo @ Library Documentation <https://yombo.net/docs/libraries/mqttyombo>`_

Handles inter-gateway communications and IoT requests.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/mqttyombo/device_commands.html>`_
"""
from copy import deepcopy
from collections import deque
import socket
from time import time
import traceback
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import random_int, random_string, sleep

logger = get_logger("library.mqttyombo.device_commands")


class DeviceCommandsMixin:

    def _device_command_(self, arguments, **kwargs):
        """
        A new command for a device has been sent. This is used to tell other gateways that either a local device
        is about to do something, other another gateway should do something.

        :param arguments:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return

        device_command = arguments["device_command"].to_dict()
        if device_command["gateway_id"] != self._gateway_id:
            return

        payload = {
            "state": "new",
            "device_command": device_command
        }

        self.publish_data(destination_id="all",
                          component_type="lib", component_name="device_command",
                          payload=payload)

    def _device_command_status_(self, arguments, **kwargs):
        """
        A device command has changed status. Update everyone else.

        :param arguments:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return
        if "source" in arguments and arguments["source"] == "gateway_coms":
            return

        device_command = arguments["device_command"]
        if device_command.gateway_id != self._gateway_id:
            return

        history = device_command.last_history()
        payload = {
            "device_command_id": arguments["device_command"].device_command_id,
            "log_time": history["time"],
            "status": history["status"],
            "message": history["msg"],
        }

        self.publish_data(destination_id="all",
                          component_type="lib", component_name="device_command_status",
                          payload=payload)

    @inlineCallbacks
    def incoming_data_device_command(self, body):
        """
        Handles incoming device commands. Only the master node will store device command information for
        other gateways.

        :param body:
        :return:
        """
        payload = body["payload"]
        source_id = body["source_id"]

        def do_device_command(parent, device_command):
            device = parent._Devices.get(device_command["device_id"])
            if device.gateway_id != parent._gateway_id and parent.is_master is not True:  # if we are not a master, we don't care!
                # print("do_device_command..skipping due to not local gateway and not a master: %s" % parent.is_master)
                # print("dropping device command..  dest gw: %s" % device_command["gateway_id"])
                # print("dropping device command..  self.gateway_id: %s" % self.gateway_id)
                return False
            device_command["broadcast_at"] = None
            device_command["device"] = device
            device_command["gateway_id"] = source_id
            yield parent._DeviceCommands.new(**device_command)

        if isinstance(payload["device_command"], list):
            for device_command in payload["device_command"]:
                do_device_command(device_command)
        else:
            do_device_command(self, payload["device_command"])
        return True

    def incoming_data_device_command_status(self, body):
        """
        Handles incoming device commands.

        :param body:
        :return:
        """
        payload = body["payload"]
        source_id = body["source_id"]

        for device_command_id, data in payload.items():
            if device_command_id not in self._DeviceCommands.device_commands:
                msg = {"device_command_id": device_command_id}
                # self.publish_data("req", source_id, "lib/device_commands", msg)
            else:
                self._DeviceCommands.set_status(
                    device_command_id,
                    data["status"],
                    data["message"],
                    data["log_time"],
                    source_id,
                )
        return True

    def send_device_commands(self, destination_id=None, device_command_id=None):
        return_gw = self.get_return_destination(destination_id)
        if return_gw == "all" and device_command_id is None:
            logger.debug("device commands request must have device_command_id or return gateway id.")
            return
        if device_command_id is None:
            found_device_commands = self._DeviceCommands.find_device_commands(gateway_id=self._gateway_id)
        elif device_command_id in self._DeviceCommands.device_commands:
            if self._DeviceCommands.device_commands[device_command_id].gateway_id == self._gateway_id:
                found_device_commands = {device_command_id: self._DeviceCommands.device_commands[device_command_id].to_dict()}
        self.publish_data(destination_id=destination_id,
                          component_type="lib", component_name="device_command",
                          payload=found_device_commands)