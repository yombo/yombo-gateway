# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. warning::

   This library is not intended to be accessed by module developers or end users. These functions, variables,
   and classes were not intended to be accessed directly by modules. These are documented here for completeness.

.. note::

  * For library documentation, see: `MQTTYombo @ Library Documentation <https://yombo.net/docs/libraries/mqttyombo>`_

Handles sending states.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/mqttyombo/states.html>`_
"""
# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.classes.jsonapi import JSONApi
from yombo.core.library import YomboLibrary
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import random_int, random_string, sleep

logger = get_logger("library.mqttyombo.states")


class StatesMixin:
    def _states_set_(self, arguments, **kwargs):
        """
        Publish a new state, if it's from ourselves.

        :param arguments:
        :return:
        """
        if self.ok_to_publish_updates is False:
            return

        gateway_id = arguments["gateway_id"]
        if gateway_id not in (self._gateway_id, "global", "cluster"):
            return
        self.publish_yombo_gw("states", JSONApi(arguments["item"]).to_dict("to_database"))
        print(f'mqtt _states_set_: {JSONApi(arguments["item"]).to_dict("to_external")}')
        self.publish_yombo("states", JSONApi(arguments["item"]).to_dict("to_external"), jsonapi=True)

    @inlineCallbacks
    def incoming_states(self, topic, payload, headers, properties):
        """
        Incoming states from various gateways. This sets global and cluster level states.

        :param payload:
        :param kwargs:
        :return:
        """
        print("incoming states")
        pass

    def send_states(self, destination=None, state_id=None, target_topics=None, reply_correlation_id=None):
        """
        Sends one or more states to a destination. Set 'target_topics' to contol if this should go to gateways and/or
        IoT devices.

        :param destination: Where to send the data to, a gateway_id.
        :param state_id: Which state to send.
        :param target_topics: String or list of strings for where to send this. Eg: ["yombo_gw", "yombo"]
        :return:
        """
        if target_topics is None:
            target_topics = ["yombo_gw"]

        if state_id is None or state_id == "#":
            return self.send_items(self._States.get("#", instance=True),
                                   "states", destination,
                                   target_topics=target_topics,
                                   reply_correlation_id=reply_correlation_id)
        else:
            return self.send_items(self._States.get("state_id", instance=True),
                                   "states",
                                   destination=destination,
                                   target_topics=target_topics,
                                   reply_correlation_id=reply_correlation_id)
