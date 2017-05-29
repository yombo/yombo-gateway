# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/modules/devices/>`_

The device class is responsible for managing a single device.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries

try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from time import time

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
logger = get_logger('library.devices.device_command')


class Device_Command(object):
    """
    A class that manages requests for a given device. This class is instantiated by the
    device class. Librarys and modules can use this instance to get the details of a given
    request.
    """

    def __init__(self, data, parent, start=None):
        """
        Get the instance setup.

        :param data: Basic details about the device command to get started.
        :param parent: A pointer to the device types instance.
        """
        # print("new device_comamnd: %s" % data)
        self._Parent = parent
        self.request_id = data['request_id']
        if 'device' in data:
            self.device = data['device']
        elif 'device_id' in data:
            self.device = parent.get(data['device_id'])
        if 'command' in data:
            self.command = data['command']
        elif 'command_id' in data:
            self.command = parent._Commands.get(data['command_id'])
        self.inputs = data.get('inputs', None)
        if 'history' in data:
            self.history = data['history']
        else:
            self.history = []
        self.requested_by = data['requested_by']
        self.status = 'new'

        self.persistent_request_id = data.get('persistent_request_id', None)
        self.sent_time = data.get('sent_time', None)
        self.received_time = data.get('received_time', None)
        self.pending_time = data.get('pending_time', None)
        self.finished_time = data.get('finished_time', None)
        self.not_before_time = data.get('not_before_time', None)
        self.not_after_time = data.get('not_after_time', None)
        self.call_later = None
        self.created_time = data.get('created_time', time())
        self.dirty = data.get('dirty', True)
        self.source = data.get('_source', None)

        if self.source == 'database':
            self.dirty = False

        if start is None or start is True:
            reactor.callLater(0.001, self.start)

    def start(self):
        if self.not_before_time is not None:
            cur_time = time()
            if self.not_after_time < cur_time:
                self.set_delay_expired(message='Unable to send message due to request being expired by "%s" seconds.'
                                    % str(cur_time - self.not_after_time))
                if self.source != 'database':  # Nothing should be loaded from the database that not a delayed command.
                    raise YomboWarning("Cannot setup delayed device command, it's already expired.")
            else:
                when = self.not_before_time - cur_time
                if when < 0:
                    self.device.do_command_hook(self)
                else:
                    self.call_later = reactor.callLater(when, self.device.do_command_hook, self)
                    self.set_status('delayed')
                return True
        else:
            if self.source == 'database':  # Nothing should be loaded from the database that not a delayed command.
                logger.info("Discarding a device command message loaded from database because it's not meant to be called later.")
                self.set_failed(finished_time = 0);
            else:
                self.device.do_command_hook(self)
                return True

    def last_message(self):
        return self.history[0]

    def set_sent(self, sent_time=None, message=None):
        self.dirty = True
        if sent_time is None:
            sent_time = time()
        self.sent_time = sent_time
        self.status = 'sent'
        if message is None:
            message='command sent'
        self.history.append((sent_time, message))

    def set_received(self, received_time=None, message=None):
        self.dirty = True
        if received_time is None:
            received_time = time()
        self.received_time = received_time
        self.status = 'received'
        if message is None:
            message='command received by the controlling sub-system'
        self.history.append((received_time, message))

    def set_pending(self, pending_time=None, message=None):
        self.dirty = True
        if pending_time is None:
            pending_time = time()
        self.pending_time = pending_time
        self.status = 'pending'
        if message is None:
            message='command pending processing by the controlling sub-system'
        self.history.append((pending_time, message))

    def set_finished(self, finished_time=None, status=None, message=None):
        self.dirty = True
        if finished_time is None:
            finished_time = time()
        self.finished_time = finished_time
        if status is None:
            status = 'done'
        self.status = status
        self.history.append((finished_time, status))
        if message is not None:
            self.set_message(message)

        try:
            self.call_later.cancel()
        except:
            pass
        self.save_to_db()

    def set_canceled(self, finished_time=None, message=None):
        if message is None:
            message = "Request canceled."
        self.set_finished(finished_time=finished_time, status='canceled', message=message)

    def set_failed(self, finished_time=None, message=None):
        if message is None:
            message = "System reported command failed."
        self.set_finished(finished_time=finished_time, status='failed', message=message)

    def set_delay_expired(self, finished_time=None, message=None):
        if message is None:
            message = "System reported command failed."
        # message = "System reported command failed."
        self.set_finished(finished_time=finished_time, status='delay_expired', message=message)

    def set_status(self, status, message=None):
        self.dirty = True
        self.status = status
        self.history.append((time(), status))
        if message is not None:
            self.set_message(message)

    def set_message(self, message):
        self.dirty = True
        self.message = message
        self.history.append((time(), message))

    @inlineCallbacks
    def save_to_db(self, forced = None):
        if self.dirty or forced is True:
            results = yield self._Parent._LocalDB.save_device_command(self)
            self.dirty = False

    def __repr__(self):
        return {
            "device_id": self.device.device_id,
            "command_id": self.command.command_id,
            "request_id": self.request_id,
            "inputs": self.inputs,
            "history": self.history,
            "requested_by": self.request_id,
            "status": self.status,
            "persistent_request_id": self.persistent_request_id,
            "created_time": self.created_time,
            "received_time": self.received_time,
            "sent_time": self.sent_time,
            "pending_time": self.pending_time,
            "finished_time": self.finished_time,
            "not_before_time": self.not_before_time,
            "not_after_time": self.not_after_time,
            "dirty": self.dirty,
        }

