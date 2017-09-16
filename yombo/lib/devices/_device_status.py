# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/modules/devices/>`_

The device status class manages a single status entry for a device.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from collections import OrderedDict
from time import time

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.log import get_logger
from yombo.utils import random_string, data_pickle
logger = get_logger('library.devices.device')

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

    ## <start dict emulation>
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
        self._FullName = 'yombo.gateway.lib.Devices.DeviceStatus'
        self._Name = 'Devices.DeviceStatus'
        self._Parent = _Parent
        self._source = source

        self.device = device
        self.command = None
        if 'status_id' in data:
            self.status_id = data['status_id']
            del data['status_id']
        else:
            self.status_id = random_string(length=15, char_set='extended')

        self.gateway_id = self._Parent.gateway_id
        self.set_at = time()
        self.energy_usage = None
        self.energy_type = None
        self.human_status = None
        self.human_message = None
        self.machine_status = None
        self.machine_status_extra = None
        self.requested_by = None
        self.reported_by = None
        self.request_id = None
        self.uploaded = None
        self.uploadable = None
        self.fake_data = False

        if self._source == 'database':
            self._dirty = False
            self._in_db = True
        else: # includes 'gateway_coms'
            self._dirty = True
            self._in_db = False
            reactor.callLater(1, self.check_if_device_status_in_database)

        # print("device status: in db: %s, dirty: %s" % (self._in_db, self._dirty))
        self.update_attributes(data, source='self')
        reactor.callLater(1, self.save_to_db)

    @inlineCallbacks
    def check_if_device_status_in_database(self):
        where = {
            'status_id': self.status_id,
        }
        device_status = yield self._Parent._LocalDB.get_device_status(where)
        # print("check_if_device_status_in_database: %s" % device_status)
        if len(device_status) > 0:
            self._in_db = True
            self.save_to_db()

    def update_attributes(self, device, source=None):
        """
        Sets various values from a device dictionary. This can be called when the device is first being setup or
        when being updated by the AMQP service.

        This does not set any device state or status attributes.
        :param device: 
        :return: 
        """
        if 'command' in device:
            try:
                self.command = self._Parent._Commands[device['command']]
            except Exception as E:
                pass
        elif 'command_id' in device:
            try:
                self.command = self._Parent._Commands[device['command_id']]
            except Exception as E:
                pass
        if 'gateway_id' in device:
            self.gateway_id = device["gateway_id"]
        if 'status_id' in device:
            self.status_id = device["status_id"]
        if 'set_at' in device:
            self.set_at = float(device["set_at"])
        if 'energy_usage' in device:
            self.energy_usage = device["energy_usage"]
        if 'energy_type' in device:
            self.energy_type = device["energy_type"]
        if 'human_status' in device:
            self.human_status = device["human_status"]
        if 'human_message' in device:
            self.human_message = device["human_message"]
        if 'machine_status' in device:
            self.machine_status = device["machine_status"]
        if 'machine_status_extra' in device:
            self.machine_status_extra = device["machine_status_extra"]
        if 'requested_by' in device:
            self.requested_by = device["requested_by"]
        if 'reported_by' in device:
            self.reported_by = device["reported_by"]
        if 'request_id' in device:
            self.request_id = device["request_id"]
        if 'uploaded' in device:
            self.uploaded = device["uploaded"]
        if 'uploadable' in device:
            self.uploadable = device["uploadable"]
        if 'fake_data' in device:
            self.fake_data = device["fake_data"]
        self._dirty = True
        reactor.callLater(1, self.save_to_db)

    def asdict(self):
        """
        Returns this item as a dictionary.
        :return:
        """
        return OrderedDict({
            'status_id': self.status_id,
            'device_id': self.device_id,
            'command_id': self.command_id,
            'gateway_id': self.gateway_id,
            'set_at': self.set_at,
            'energy_usage': self.energy_usage,
            'energy_type': self.energy_type,
            'human_status': self.human_status,
            'human_message': self.human_message,
            'machine_status': self.machine_status,
            'machine_status_extra': self.machine_status_extra,
            'requested_by': self.requested_by,
            'reported_by': self.reported_by,
            'request_id': self.request_id,
            'uploaded': self.uploaded,
            'uploadable': self.uploadable,
        })

    def save_to_db(self, forced = None):
        # print("device status, save to database... %s" % self.asdict())
        # print("device status: save_to_db,,, in db: %s, dirty: %s, machine_status: %s" % (self._in_db, self._dirty, self.machine_status))

        if self.fake_data is True:
            # print("not updating db, it's fake data!")
            self._dirty = False
            return

        if self.device.gateway_id != self._Parent.gateway_id and self._Parent.is_master is not True:
            self._dirty = False
            return

        if self._dirty or forced is True:
            data = self.asdict()
            # if self.inputs is None:
            #     data['inputs'] = None
            # else:
            data['machine_status_extra'] = data_pickle(self.machine_status_extra)
            data['requested_by'] = data_pickle(self.requested_by)

            if self._in_db is True:
                self._Parent._LocalDB.add_bulk_queue('device_status', 'update', data, 'status_id')
            else:
                self._Parent._LocalDB.add_bulk_queue('device_status', 'insert', data, 'status_id')
            self._dirty = False
            self._in_db = True
