# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Gateways @ Module Development <https://yombo.net/docs/libraries/gateways>`_

The gateway class.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.19.1

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/gateways.html>`_
"""
from collections import deque
from time import time

# Import Yombo libraries
from yombo.core.log import get_logger

logger = get_logger('library.gateways.gateway')


class Gateway:
    """
    A class to manage a single gateway.
    :ivar gateway_id: (string) The unique ID.
    :ivar label: (string) Human label
    :ivar machine_label: (string) A non-changable machine label.
    :ivar category_id: (string) Reference category id.
    :ivar input_regex: (string) A regex to validate if user input is valid or not.
    :ivar always_load: (int) 1 if this item is loaded at startup, otherwise 0.
    :ivar status: (int) 0 - disabled, 1 - enabled, 2 - deleted
    :ivar public: (int) 0 - private, 1 - public pending approval, 2 - public
    :ivar created_at: (int) EPOCH time when created
    :ivar updated: (int) EPOCH time when last updated
    """

    def __init__(self, parent, gateway):
        """
        Setup the gateway object using information passed in.

        :param gateway: An gateway with all required items to create the class.
        :type gateway: dict

        """
        logger.debug("gateway info: {gateway}", gateway=gateway)
        self._Parent = parent
        self.gateway_id = gateway['id']
        self.machine_label = gateway['machine_label']

        # below are configure in update_attributes()
        self.is_master = None
        self.master_gateway = None
        self.label = None
        self.description = None
        self.mqtt_auth = None
        self.mqtt_auth_prev = None
        self.mqtt_auth_next = None
        self.mqtt_auth_last_rotate = None
        self.fqdn = None
        self.internal_ipv4 = None
        self.external_ipv4 = None
        self.internal_port = None
        self.external_port = None
        self.internal_secure_port = None
        self.external_secure_port = None
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
        self.ping_request = None  # Time the ping was requested
        self.ping_response = None  # When we got a response back
        self.ping_time_offset = None  # Time offset relating to current gateway

        # communications information
        self.last_communications = deque([], 30)  # stores times and topics of the last few communications

        self.update_attributes(gateway)

    def update_attributes(self, gateway):
        """
        Sets various values from a gateway dictionary. This can be called when either new or
        when updating.

        :param gateway:
        :return: 
        """
        if 'gateway_id' in gateway:
            self.gateway_id = gateway['gateway_id']
        if 'is_master' in gateway:
            self.is_master = gateway['is_master']
        if 'master_gateway' in gateway:
            self.master_gateway = gateway['master_gateway']
        if 'label' in gateway:
            self.label = gateway['label']
        if 'description' in gateway:
            self.description = gateway['description']
        if 'mqtt_auth' in gateway:
            self.mqtt_auth = gateway['mqtt_auth']
        if 'mqtt_auth_next' in gateway:
            self.mqtt_auth_next = gateway['mqtt_auth_next']
        if 'internal_ipv4' in gateway:
            self.internal_ipv4 = gateway['internal_ipv4']
        if 'external_ipv4' in gateway:
            self.external_ipv4 = gateway['external_ipv4']
        if 'internal_port' in gateway:
            self.internal_port = gateway['internal_port']
        if 'external_port' in gateway:
            self.external_port = gateway['external_port']
        if 'fqdn' in gateway:
            self.fqdn = gateway['fqdn']
        if 'internal_secure_port' in gateway:
            self.internal_secure_port = gateway['internal_secure_port']
        if 'external_secure_port' in gateway:
            self.external_secure_port = gateway['external_secure_port']
        if 'internal_mqtt' in gateway:
            self.internal_mqtt = gateway['internal_mqtt']
        if 'internal_mqtt_le' in gateway:
            self.internal_mqtt_le = gateway['internal_mqtt_le']
        if 'internal_mqtt_ss' in gateway:
            self.internal_mqtt_ss = gateway['internal_mqtt_ss']
        if 'internal_mqtt_ws' in gateway:
            self.internal_mqtt_ws = gateway['internal_mqtt_ws']
        if 'internal_mqtt_ws_le' in gateway:
            self.internal_mqtt_ws_le = gateway['internal_mqtt_ws_le']
        if 'internal_mqtt_ws_ss' in gateway:
            self.internal_mqtt_ws_ss = gateway['internal_mqtt_ws_ss']
        if 'external_mqtt' in gateway:
            self.external_mqtt = gateway['external_mqtt']
        if 'external_mqtt_le' in gateway:
            self.external_mqtt_le = gateway['external_mqtt_le']
        if 'external_mqtt_ss' in gateway:
            self.external_mqtt_ss = gateway['external_mqtt_ss']
        if 'external_mqtt_ws' in gateway:
            self.external_mqtt_ws = gateway['external_mqtt_ws']
        if 'external_mqtt_ws_le' in gateway:
            self.external_mqtt_ws_le = gateway['external_mqtt_ws_le']
        if 'external_mqtt_ws_ss' in gateway:
            self.external_mqtt_ws_ss = gateway['external_mqtt_ws_ss']
        if 'status' in gateway:
            self.status = gateway['status']
        if 'created_at' in gateway:
            self.created_at = gateway['created_at']
        if 'updated_at' in gateway:
            self.updated_at = gateway['updated_at']
        if 'version' in gateway:
            self.version = gateway['version']

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
            'gateway_id': str(self.gateway_id),
            'fqdn': str(self.fqdn),
            'is_master': self.is_master,
            'master_gateway': str(self.master_gateway),
            'machine_label': str(self.machine_label),
            'label': str(self.label),
            'description': str(self.description),
            'com_status': str(self.com_status),
            'internal_ipv4': str(self.internal_ipv4),
            'external_ipv4': str(self.external_ipv4),
            'internal_port': str(self.internal_port),
            'external_port': str(self.external_port),
            'internal_secure_port': str(self.internal_secure_port),
            'external_secure_port': str(self.external_secure_port),
            'internal_mqtt': str(self.internal_mqtt),
            'internal_mqtt_le': str(self.internal_mqtt_le),
            'internal_mqtt_ss': str(self.internal_mqtt_ss),
            'internal_mqtt_ws': str(self.internal_mqtt_ws),
            'internal_mqtt_ws_le': str(self.internal_mqtt_ws_le),
            'internal_mqtt_ws_ss': str(self.internal_mqtt_ws_ss),
            'external_mqtt': str(self.external_mqtt),
            'external_mqtt_le': str(self.external_mqtt_le),
            'external_mqtt_ss': str(self.external_mqtt_ss),
            'external_mqtt_ws': str(self.external_mqtt_ws),
            'external_mqtt_ws_le': str(self.external_mqtt_ws_le),
            'external_mqtt_ws_ss': str(self.external_mqtt_ws_ss),
            'version': str(self.version),
            'status': str(self.status),
            'created_at': int(self.created_at),
            'updated_at': int(self.updated_at),
        }

    def __repl__(self):
        """
        Export gateway variables as a dictionary.
        """
        return {
            'gateway_id': str(self.gateway_id),
            'fqdn': str(self.fqdn),
            'is_master': self.is_master,
            'master_gateway': str(self.master_gateway),
            'machine_label': str(self.machine_label),
            'label': str(self.label),
            'description': str(self.description),
            'status': int(self.status),
            'com_status': str(self.com_status),
            'created_at': int(self.created_at),
            'updated_at': int(self.updated_at),
        }

    @property
    def com_status(self):
        if self.gateway_id == self._Parent.gateway_id:
            return 'online'

        if self.gateway_id in self._Parent.gateway_status:
            return self._Parent.gateway_status[self.gateway_id]['com_status']
        else:
            return None

    @com_status.setter
    def com_status(self, val):
        if self.gateway_id == self._Parent.gateway_id:
            return

        if self.gateway_id not in self._Parent.gateway_status:
            self._Parent.gateway_status[self.gateway_id] = {
                'com_status': val,
                'last_scene': None,
            }
        else:
            self._Parent.gateway_status[self.gateway_id]['com_status'] = val

    @property
    def last_scene(self):
        if self.gateway_id == self._Parent.gateway_id:
            return time()

        if self.gateway_id in self._Parent.gateway_status:
            return self._Parent.gateway_status[self.gateway_id]['last_scene']
        else:
            return None

    @last_scene.setter
    def last_scene(self, val):
        if self.gateway_id == self._Parent.gateway_id:
            return

        if self.gateway_id not in self._Parent.gateway_status:
            self._Parent.gateway_status[self.gateway_id] = {
                'com_status': None,
                'last_scene': val,
            }
        else:
            self._Parent.gateway_status[self.gateway_id]['last_scene'] = val
