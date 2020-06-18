# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. warning::

   This library is not intended to be accessed by module developers or end users. These functions, variables,
   and classes were not intended to be accessed directly by modules. These are documented here for completeness.

.. note::

  * For library documentation, see: `MQTTYombo @ Library Documentation <https://yombo.net/docs/libraries/mqttyombo>`_

Handles sending atoms.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2020 by Yombo.
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


class AtomsMixin:

    def incoming_atoms(self, source, destination, payload, **kwargs):
        """
        Incoming atoms from various gateways. This sets global and cluster level atoms.

        :param payload:
        :param kwargs:
        :return:
        """
        pass

    def send_atoms(self, destination=None, atom_id=None, target_topics=None, reply_correlation_id=None):
        """
        Sends one or more atoms to a destination.

        :param destination: Where to send the data to, a gateway_id.
        :param atom_id: Which atom to send.
        :param target_topics: String or list of strings for where to send this. Eg: ["yombo_gw", "yombo"]
        :return:
        """
        if target_topics is None:
            target_topics = ["yombo_gw"]

        if atom_id is None or atom_id == "#":
            return self.send_items(self._Atoms.get("#", instance=True),
                                   "atoms", destination,
                                   target_topics=target_topics,
                                   reply_correlation_id=reply_correlation_id)
        else:
            return self.send_items(self._Atoms.get("atom_id", instance=True),
                                   "states",
                                   destination=destination,
                                   target_topics=target_topics,
                                   reply_correlation_id=reply_correlation_id)
