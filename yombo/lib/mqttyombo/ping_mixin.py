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
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/mqttyombo/atoms.html>`_
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

logger = get_logger("library.mqttyombo.atoms")


class PingMixin:

    def send_presence(self):
        self.publish_yombo(f"gw/{self._gateway_id}", None, topic_prefix="yombo_presence")
        self.publish_yombo_gw("presence", None)

    @inlineCallbacks
    def ping_gateways(self):
        """
        Pings all the known gateways.

        :return:
        """
        my_gateway_id = self._gateway_id
        for gateway_id, gateway in self._Gateways.gateways.items():
            if gateway_id in ("local", "all", "cluster", my_gateway_id) or len(gateway_id) < 13:
                continue
            current_time = time()
            ping_request_id = self.publish_data(destination_id=gateway_id,
                                                component_type="lib", component_name="system_ping",
                                                payload=time(), message_type="req")
            self._Gateways.gateways[gateway_id].ping_request_id = ping_request_id
            self._Gateways.gateways[gateway_id].ping_request_at = current_time
            yield sleep(0.2)
