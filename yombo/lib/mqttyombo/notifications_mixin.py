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

logger = get_logger("library.mqttyombo.devices")


class NotificationsMixin:

    def _notification_add_(self, arguments, **kwargs):
        """
        Publish a new notification, if it"s from ourselves.

        :param arguments:
        """
        # print("_device_state_: %s" % arguments["command"])
        if self.ok_to_publish_updates is False:
            return

        notice = arguments["notification"]
        if notice.local is True:
            return

        # print("checking if i should send this device_states.  %s != %s" % (self.gateway_id, device.gateway_id))
        if self._gateway_id != notice.gateway_id:
            return

        message = {
            "action": "add",
            "notice": arguments["event"],
        }

        topic = "lib/notification/" + notice.notification_id
        # print("sending _device_state_: %s -> %s" % (topic, message))
        # self.publish_data("gw", "all", topic, message)

    def _notification_delete_(self, arguments, **kwargs):
        """
        Delete a notification, if it's from ourselves.

        :param arguments:
        :return:
        """
        # print("_device_state_: %s" % arguments["command"])
        if self.ok_to_publish_updates is False:
            return

        notice = arguments["notification"]
        if notice.local is True:
            return

        # print("checking if i should send this device_states.  %s != %s" % (self.gateway_id, device.gateway_id))
        if self._gateway_id != notice.gateway_id:
            return

        message = {
            "action": "delete",
            "notice": arguments["event"],
        }

        topic = "lib/notification/" + notice.notification_id
        # print("sending _device_state_: %s -> %s" % (topic, message))
        # self.publish_data("gw", "all", topic, message)

    def incoming_data_notification(self, body):
        """
        Handles incoming device status.

        Todo: Complete this method.

        :param body:
        :return:
        """
        return True
        payload = message["payload"]
        payload["status_source"] = "gateway_coms"