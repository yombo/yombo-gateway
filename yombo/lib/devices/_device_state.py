# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_


The device state class manages a single state entry for a device.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from time import time

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.log import get_logger
from yombo.mixins.sync_to_everywhere_mixin import SyncToEverywhereMixin
from yombo.utils import random_string

logger = get_logger("library.devices.device")


class Device_State(Entity, SyncToEverywhereMixin):
    """
    The device state class represents a single state data point for a device.
    """

    def __str__(self):
        """
        Print a string when printing the class.  This will return the device_id so that
        the device can be identified and referenced easily.
        """
        return self.human_state

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    def __contains__(self, item):
        return hasattr(self, item)
    ##  <end dict emulation>

    @property
    def device_id(self):
        return self.device.device_id

    @property
    def command_id(self):
        if self.command is None:
            return None
        else:
            return self.command.command_id

    def __init__(self, parent, device, data, source=None):
        logger.debug("Creating new Device_State... {data}", data=data)

        self._internal_label = "device_states"  # Used by mixins
        self._can_have_fake_data = True
        super().__init__(parent)

        self.device = device
        self.command = None

        # database fields
        if "state_id" in data:
            self.state_id = data["state_id"]
            del data["state_id"]
        else:
            self.state_id = random_string(length=20)
        self.request_id = None
        self.set_at = time()
        self.energy_usage = None
        self.energy_type = None
        self.human_state = None
        self.human_message = None
        self.machine_state = None
        self.machine_state_extra = None
        self.auth_id = None
        self.requesting_source = None
        self.reporting_source = None
        self.uploaded = None
        self.uploadable = None

        self.update_attributes(data, source=source)

    def update_attributes(self, device, source=None):
        """
        Sets various values from a device dictionary. This can be called when the device is first being setup or
        when being updated by the AMQP service.

        This does not set any device state or state attributes.
        :param device: 
        :return: 
        """
        if "command" in device:
            try:
                device["command"] = self._Parent._Commands[device["command"]]
            except Exception:
                pass
        elif "command_id" in device:
            try:
                device["command"] = self._Parent._Commands[device["command_id"]]
                del device["command_id"]
            except Exception as E:
                pass

        super().update_attributes(device, source=source)

    def asdict(self, full=None):
        """
        Returns this item as a dictionary.
        :return:
        """
        results = {
            "id": self.status_id,
            "device_id": self.device_id,
            "command_id": self.command_id,
            "set_at": self.set_at,
            "energy_usage": self.energy_usage,
            "energy_type": self.energy_type,
            "human_state": self.human_state,
            "human_message": self.human_message,
            "machine_state": self.machine_state,
            "machine_state_extra": self.machine_state_extra,
            "auth_id": self.auth_id,
            "requesting_source": self.requesting_source,
            "reporting_source": self.reporting_source,
            "request_id": self.request_id,
            "uploaded": self.uploaded,
            "uploadable": self.uploadable,
        }
        if hasattr(self, "_fake_data"):
            results["_fake_data"] = self._fake_data

        if full is True:
            results["dirty"] = self._dirty
            results["in_db"] = self._in_db
            results["source"] = self.source
        return results

