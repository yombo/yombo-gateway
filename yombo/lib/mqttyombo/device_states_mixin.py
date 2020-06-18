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
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/mqttyombo/devices.html>`_
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

logger = get_logger("library.mqttyombo.devices")


class DeviceStatesMixin:

    def _device_state_(self, arguments, **kwargs):
        """
        Publish a new device state, if it's from ourselves.

        :param arguments:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return

        gateway_id = arguments["gateway_id"]
        if gateway_id != self._gateway_id and gateway_id not in ("global", "cluster"):
            return

        source = arguments.get("source", None)
        if source == "gateway_coms":
            return
        device = arguments["device"]
        device_id = device.device_id

        if self._gateway_id != device.gateway_id:
            return

        self.publish_data(destination_id="all",
                          component_type="lib", component_name="device_states",
                          payload=[device.state_all.to_dict()])

    def incoming_data_device_states(self, body):
        """
        Handles incoming device status.

        :param body:
        :return:
        """
        payload = body["payload"]
        source_id = body["source_id"]

        for status in payload:
            device_id = status["device_id"]
            if device_id not in self._Devices:
                logger.info("MQTT Received device status for a device that doesn't exist, dropping: {device_id}",
                            device_id=device_id)
                continue
            device = self._Devices[device_id]
            status["source"] = "gateway_coms"
            device.set_state_internal(status)
        return True

    def send_device_states(self, destination_id=None, device_id=None):
        gateway_id = self._gateway_id
        return_gw = self.get_return_destination(destination_id)
        message = []
        if device_id is None:
            for device_id, device in self._Devices.devices.items():
                if device.gateway_id == gateway_id or device.status != 1:
                    continue
                message.append(device.state_all.to_dict())
        else:
            if device_id in self._Devices:
                device = self._Devices[device_id]
                if device.gateway_id == gateway_id or device.status != 1:
                    return
                message.append(device.state_all.to_dict())
        if len(message) > 0:
            self.publish_data(destination_id=destination_id,
                              component_type="lib", component_name="device_states",
                              payload=message)
