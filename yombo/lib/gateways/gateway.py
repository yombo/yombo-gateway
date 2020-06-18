# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Gateways @ Module Development <https://yombo.net/docs/libraries/gateways>`_

The gateway class.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.19.1

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/gateways/gateway.html>`_
"""
from collections import deque
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union


# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin

logger = get_logger("library.gateways.gateway")


class Gateway(Entity, LibraryDBChildMixin):
    """
    A class to manage a single gateway.
    :ivar gateway_id: (string) The unique ID.
    :ivar label: (string) Human label
    :ivar machine_label: (string) A non-changable machine label.
    :ivar category_id: (string) Reference category id.
    :ivar input_regex: (string) A regex to validate if user input is valid or not.
    :ivar status: (int) 0 - disabled, 1 - enabled, 2 - deleted
    :ivar public: (int) 0 - private, 1 - public pending approval, 2 - public
    :ivar created_at: (int) EPOCH time when created
    :ivar updated: (int) EPOCH time when last updated
    """
    _Entity_type: ClassVar[str] = "Gateway"
    _Entity_label_attribute: ClassVar[str] = "machine_label"
    _additional_to_dict_fields: ClassVar[list] = ["is_real", "com_status", "last_seen", "version", "ping_request_id",
                                                  "ping_request_at", "ping_time_offset", "ping_roundtrip"]

    @property
    def is_real(self) -> bool:
        if self.machine_label in ("local", "cluster"):
            return False
        return True

    @property
    def com_status(self) -> str:
        if self.gateway_id == self._Parent._gateway_id:
            return "Online"

        if self.gateway_id in self._Parent.gateway_status:
            return self._Parent.gateway_status[self.gateway_id]["com_status"]
        else:
            return "Not available"

    @com_status.setter
    def com_status(self, val: str) -> None:
        if self.gateway_id == self._Parent._gateway_id:
            return

        if self.gateway_id not in self._Parent.gateway_status:
            self._Parent.gateway_status[self.gateway_id] = {
                "com_status": val,
                "last_seen": None,
            }
        else:
            self._Parent.gateway_status[self.gateway_id]["com_status"] = val

    @property
    def last_seen(self) -> int:
        if self.gateway_id == self._Parent._gateway_id:
            return time()

        if self.gateway_id in self._Parent.gateway_status:
            return self._Parent.gateway_status[self.gateway_id]["last_seen"]
        else:
            return None

    @last_seen.setter
    def last_seen(self, val: int) -> None:
        if self.gateway_id == self._Parent._gateway_id:
            return

        if self.gateway_id not in self._Parent.gateway_status:
            self._Parent.gateway_status[self.gateway_id] = {
                "com_status": None,
                "last_seen": val,
            }
        else:
            self._Parent.gateway_status[self.gateway_id]["last_seen"] = val

    def __init__(self, parent, **kwargs) -> None:
        """
        Setup the gateway object using information passed in.

        :param gateway: An gateway with all required items to create the class.
        :type gateway: dict

        """
        super().__init__(parent, **kwargs)

        self.version = None
        self.ping_request_id = None  # The last ID for the ping request
        self.ping_request_at = None  # Time the ping was requested
        self.ping_response_at = None  # When we got a response back
        self.ping_time_offset = None  # Time offset relating to current gateway
        self.ping_roundtrip = None  # How many millisecond for last round trip.

        self.last_communications = deque([], 30)  # stores times and topics of the last few communications

    # def to_dict_postprocess(self, incoming, to_database: Optional[bool] = None, **kwargs):
    #     """ Add some additional data to send. """
    #     if to_database is False:
    #         incoming["data"]["is_real"] = self.is_real
    #         incoming["data"]["com_status"] = self.com_status
    #         incoming["data"]["last_seen"] = self.last_seen
    #         incoming["data"]["version"] = self.version
    #         incoming["data"]["ping_request_id"] = self.version
    #         incoming["data"]["ping_request_at"] = self.version
    #         incoming["data"]["ping_time_offset"] = self.version
    #         incoming["data"]["ping_roundtrip"] = self.version
