# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Gateways @ Module Development <https://yombo.net/docs/libraries/gateways>`_

The gateway class.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.19.1

:copyright: Copyright 2018-2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/gateways.html>`_
"""
from collections import deque
from time import time

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.log import get_logger
from yombo.mixins.sync_to_everywhere import SyncToEverywhere

logger = get_logger("library.gateways.gateway")


class Gateway(Entity, SyncToEverywhere):
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
    @property
    def is_real(self):
        if self.machine_label in ("local", "cluster"):
            return False
        return True
    
    def __init__(self, parent, gateway, source=None):
        """
        Setup the gateway object using information passed in.

        :param gateway: An gateway with all required items to create the class.
        :type gateway: dict

        """
        self._internal_label = "gateways"  # Used by mixins
        super().__init__(parent)

        logger.debug("gateway info: {gateway}", gateway=gateway)
        self.gateway_id = gateway["id"]
        self.machine_label = gateway["machine_label"]

        # below are configure in update_attributes()
        self.is_master = None
        self.master_gateway_id = None
        self.label = None
        self.description = None
        self.user_id = None
        self.mqtt_auth = None
        self.mqtt_auth_prev = None
        self.mqtt_auth_next = None
        self.mqtt_auth_last_rotate_at = None
        self.dns_name = None
        self.internal_ipv4 = None
        self.external_ipv4 = None
        self.internal_ipv6 = None
        self.external_ipv6 = None
        self.internal_http_port = None
        self.external_http_port = None
        self.internal_http_secure_port = None
        self.external_http_secure_port = None
        self.internal_mqtt = None
        self.internal_mqtt_le = None
        self.internal_mqtt_ss = None
        self.internal_mqtt_ws = None
        self.internal_mqtt_ws_le = None
        self.internal_mqtt_ws_ss = None
        self.external_mqtt = None
        self.external_mqtt_le = None
        self.external_mqtt_ss = None
        self.external_mqtt_ws = None
        self.external_mqtt_ws_le = None
        self.external_mqtt_ws_ss = None
        self.status = None
        self.updated_at = None
        self.created_at = None
        self.version = None
        self.ping_request_id = None  # The last ID for the ping request
        self.ping_request_at = None  # Time the ping was requested
        self.ping_response_at = None  # When we got a response back
        self.ping_time_offset = None  # Time offset relating to current gateway
        self.ping_roundtrip = None  # How many millisecond for last round trip.

        # communications information
        self.last_communications = deque([], 30)  # stores times and topics of the last few communications

        self.update_attributes(gateway, source="database")
        self.start_data_sync()

    def __str__(self):
        """
        Print a string when printing the class.  This will return the gateway id so that
        the gateway can be identified and referenced easily.
        """
        return self.gateway_id

    def asdict(self):
        """
        Export gateway variables as a dictionary.
        """
        return {
            "gateway_id": str(self.gateway_id),
            "dns_name": str(self.dns_name),
            "is_master": self.is_master,
            "master_gateway_id": str(self.master_gateway_id),
            "machine_label": str(self.machine_label),
            "label": str(self.label),
            "description": str(self.description),
            "com_status": str(self.com_status),
            "internal_ipv4": str(self.internal_ipv4),
            "external_ipv4": str(self.external_ipv4),
            "internal_http_port": str(self.internal_http_port),
            "external_http_port": str(self.external_http_port),
            "internal_http_secure_port": str(self.internal_http_secure_port),
            "external_http_secure_port": str(self.external_http_secure_port),
            "internal_mqtt": str(self.internal_mqtt),
            "internal_mqtt_le": str(self.internal_mqtt_le),
            "internal_mqtt_ss": str(self.internal_mqtt_ss),
            "internal_mqtt_ws": str(self.internal_mqtt_ws),
            "internal_mqtt_ws_le": str(self.internal_mqtt_ws_le),
            "internal_mqtt_ws_ss": str(self.internal_mqtt_ws_ss),
            "external_mqtt": str(self.external_mqtt),
            "external_mqtt_le": str(self.external_mqtt_le),
            "external_mqtt_ss": str(self.external_mqtt_ss),
            "external_mqtt_ws": str(self.external_mqtt_ws),
            "external_mqtt_ws_le": str(self.external_mqtt_ws_le),
            "external_mqtt_ws_ss": str(self.external_mqtt_ws_ss),
            "version": str(self.version),
            "status": str(self.status),
            "created_at": int(self.created_at),
            "updated_at": int(self.updated_at),
        }

    def __repl__(self):
        """
        Export gateway variables as a dictionary.
        """
        return {
            "gateway_id": str(self.gateway_id),
            "dns_name": str(self.dns_name),
            "is_master": self.is_master,
            "master_gateway_id": str(self.master_gateway_id),
            "machine_label": str(self.machine_label),
            "label": str(self.label),
            "description": str(self.description),
            "status": int(self.status),
            "com_status": str(self.com_status),
            "created_at": int(self.created_at),
            "updated_at": int(self.updated_at),
        }

    @property
    def com_status(self):
        if self.gateway_id == self._Parent.gateway_id:
            return "online"

        if self.gateway_id in self._Parent.gateway_status:
            return self._Parent.gateway_status[self.gateway_id]["com_status"]
        else:
            return None

    @com_status.setter
    def com_status(self, val):
        if self.gateway_id == self._Parent.gateway_id:
            return

        if self.gateway_id not in self._Parent.gateway_status:
            self._Parent.gateway_status[self.gateway_id] = {
                "com_status": val,
                "last_scene": None,
            }
        else:
            self._Parent.gateway_status[self.gateway_id]["com_status"] = val

    @property
    def last_scene(self):
        if self.gateway_id == self._Parent.gateway_id:
            return time()

        if self.gateway_id in self._Parent.gateway_status:
            return self._Parent.gateway_status[self.gateway_id]["last_scene"]
        else:
            return None

    @last_scene.setter
    def last_scene(self, val):
        if self.gateway_id == self._Parent.gateway_id:
            return

        if self.gateway_id not in self._Parent.gateway_status:
            self._Parent.gateway_status[self.gateway_id] = {
                "com_status": None,
                "last_scene": val,
            }
        else:
            self._Parent.gateway_status[self.gateway_id]["last_scene"] = val
