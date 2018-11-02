# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_


The device status class manages a single status entry for a device.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
#from collections import OrderedDict
from time import time

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.log import get_logger
from yombo.utils import random_string, data_pickle
logger = get_logger("library.devices.device")

class Device_Status(object):
    """
    The device status class represents a single status data point for a device.
    """

    def __str__(self):
        """
        Print a string when printing the class.  This will return the device_id so that
        the device can be identified and referenced easily.
        """
        return self.human_status

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

    def __init__(self, _Parent, device, data, source=None, test_device=None):
        logger.debug("Creating new Device_Status... {data}", data=data)
        self._FullName = "yombo.gateway.lib.Devices.DeviceStatus"
        self._Name = "Devices.DeviceStatus"
        self._Parent = _Parent
        self.source = source

        self.device = device
        self.command = None
        if "status_id" in data:
            self.status_id = data["status_id"]
            del data["status_id"]
        else:
            self.status_id = random_string(length=15, char_set="extended")

        self.set_at = time()
        self.energy_usage = None
        self.energy_type = None
        self.human_status = None
        self.human_message = None
        self.machine_status = None
        self.machine_status_extra = None
        self.auth_id = None
        self.requesting_source = None
        self.reporting_source = None
        self.request_id = None
        self.uploaded = None
        self.uploadable = None
        self.fake_data = False
        self._dirty = True
        self._in_db = None

        if self.source == "database":
            self._in_db = True
            self.update_attributes(data)
            self._dirty = False
        else:  # includes "gateway_coms"
            self.update_attributes(data)
            self._in_db = False
            self._dirty = True
            reactor.callLater(1, self.check_if_device_status_in_database)

        # print("device status: in db: %s, dirty: %s" % (self._in_db, self._dirty))

    @inlineCallbacks
    def check_if_device_status_in_database(self):
        where = {
            "status_id": self.status_id,
        }
        device_status = yield self._Parent._LocalDB.get_device_status(where)
        # print("check_if_device_status_in_database: %s" % device_status)
        if len(device_status) > 0:
            self._in_db = True
            self.save_to_db()

    def update_attributes(self, device):
        """
        Sets various values from a device dictionary. This can be called when the device is first being setup or
        when being updated by the AMQP service.

        This does not set any device state or status attributes.
        :param device: 
        :return: 
        """
        if "command" in device:
            try:
                self.command = self._Parent._Commands[device["command"]]
            except Exception as E:
                pass
        elif "command_id" in device:
            try:
                self.command = self._Parent._Commands[device["command_id"]]
            except Exception as E:
                pass
        if "status_id" in device:
            self.status_id = device["status_id"]
        if "set_at" in device:
            self.set_at = float(device["set_at"])
        if "energy_usage" in device:
            self.energy_usage = device["energy_usage"]
        if "energy_type" in device:
            self.energy_type = device["energy_type"]
        if "human_status" in device:
            self.human_status = device["human_status"]
        if "human_message" in device:
            self.human_message = device["human_message"]
        if "machine_status" in device:
            self.machine_status = device["machine_status"]
        if "machine_status_extra" in device:
            self.machine_status_extra = device["machine_status_extra"]
        if "auth_id" in device:
            self.auth_id = device["auth_id"]
        if "requesting_source" in device:
            self.requesting_source = device["requesting_source"]
        if "reporting_source" in device:
            self.reporting_source = device["reporting_source"]
        if "request_id" in device:
            self.request_id = device["request_id"]
        if "uploaded" in device:
            self.uploaded = device["uploaded"]
        if "uploadable" in device:
            self.uploadable = device["uploadable"]
        if "fake_data" in device:
            self.fake_data = device["fake_data"]

        if self.source != "database" and self.fake_data is not True:
            self._dirty = True
            logger.debug("device status, done with update attr: {attrs}", attrs=self.asdict(True))
            reactor.callLater(1, self.save_to_db)

    def asdict(self, full=None):
        """
        Returns this item as a dictionary.
        :return:
        """
        results = {
            "status_id": self.status_id,
            "device_id": self.device_id,
            "command_id": self.command_id,
            "set_at": self.set_at,
            "energy_usage": self.energy_usage,
            "energy_type": self.energy_type,
            "human_status": self.human_status,
            "human_message": self.human_message,
            "machine_status": self.machine_status,
            "machine_status_extra": self.machine_status_extra,
            "auth_id": self.auth_id,
            "requesting_source": self.requesting_source,
            "reporting_source": self.reporting_source,
            "request_id": self.request_id,
            "uploaded": self.uploaded,
            "uploadable": self.uploadable,
            "fake_data": self.fake_data,
        }
        if full is True:
            results["dirty"] = self._dirty
            results["in_db"] = self._in_db
            results["source"] = self.source
        return results

    def save_to_db(self, forced=None):
        # print("device status: save_to_db,,, in db: %s, dirty: %s, machine_status: %s" % (self._in_db, self._dirty, self.machine_status))

        if self.fake_data is True or self.machine_status is None or self.device.gateway_id != self._Parent.gateway_id:
            self._dirty = False
            return

        # print("status: %s, dirty: %s" % (self.status_id, self._dirty))
        if self._dirty or forced is True:
            data = self.asdict()
            if "fake_data" in data:
                del data["fake_data"]

            data["machine_status_extra"] = data_pickle(self.machine_status_extra)

            if self._in_db is True:
                # print("device status update, save to database... %s" % self.asdict(True))
                self._Parent._LocalDB.add_bulk_queue("device_status", "update", data, "status_id")
            else:
                # print("device status insert, save to database... %s" % self.asdict(True))
                self._Parent._LocalDB.add_bulk_queue("device_status", "insert", data, "status_id")
            self._dirty = False
            self._in_db = True
