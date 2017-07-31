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
from yombo.utils import is_true_false
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
        self.source_gateway_id = data.get('source_gateway_id', self._Parent.gateway_id)
        self.local_gateway_id = self._Parent.gateway_id
        self.request_id = data['request_id']
        if 'device' in data:
            self.device = data['device']
        elif 'device_id' in data:
            self.device = parent.get(data['device_id'])
        else:
            raise ValueError("Must have either device reference, or device_id")
        if 'command' in data:
            self.command = data['command']
        elif 'command_id' in data:
            self.command = parent._Commands.get(data['command_id'])
        else:
            raise ValueError("Must have either command reference, or command_id")
        self.inputs = data.get('inputs', None)
        if 'history' in data:
            self.history = data['history']
        else:
            self.history = []
        self.requested_by = data['requested_by']
        self.status = data.get('status', 'new')

        self.command_status_received = is_true_false(data.get('command_status_received', False))  # if a status has been reported against this request
        self.persistent_request_id = data.get('persistent_request_id', None)
        self.broadcast_time = data.get('broadcast_time', None)  # time when command was sent through hooks.
        self.sent_time = data.get('sent_time', None)  # when a module or receiver sent the command to final end-point
        self.received_time = data.get('received_time', None)  # when the command was received by the final end-point
        self.pending_time = data.get('pending_time', None)  # if command takes a while to process time, this is the timestamp of last update
        self.finished_time = data.get('finished_time', None)  # when the command is finished and end-point has changed state
        self.not_before_time = data.get('not_before_time', None)
        self.not_after_time = data.get('not_after_time', None)
        self.call_later = None
        self.created_time = data.get('created_time', time())
        self.dirty = is_true_false(data.get('dirty', True))
        self.source = data.get('_source', None)
        self.started = data.get('started', False)

        if self.source == 'database':
            self.dirty = False
            self.in_db = True
        elif self.source == 'gateway_coms':
            self.dirty = False
            self.in_db = False
            reactor.callLater(0.001, self.check_if_device_command_in_database)

        else:
            self.history.append((self.created_time, self.status, 'Created.', self.local_gateway_id))
            self.in_db = False

        if self.device.gateway_id == self.local_gateway_id:
            # print("I should start....")
            self.started = False
            start = True

        if start is None or start is True:
            reactor.callLater(0.001, self.start)

    @inlineCallbacks
    def check_if_device_command_in_database(self):
        where = {
            'request_id': self.request_id,
        }
        device_commands = yield self._Parent._LocalDB.get_device_commands(where)
        if len(device_commands) > 0:
            self.in_db = True
            self.save_to_db()

    def update_attributes(self, data):
        if 'command_status_received' in data:
            self.command_status_received = data['command_status_received']
        if 'broadcast_time' in data:
            self.broadcast_time = data['broadcast_time']
        if 'sent_time' in data:
            self.sent_time = data['sent_time']
        if 'received_time' in data:
            self.received_time = data['received_time']
        if 'pending_time' in data:
            self.pending_time = data['pending_time']
        if 'finished_time' in data:
            self.finished_time = data['finished_time']
        if 'not_before_time' in data:
            self.not_before_time = data['not_before_time']
        if 'not_after_time' in data:
            self.not_after_time = data['not_after_time']
        if 'history' in data:
            self.history = data['history']
        if 'status' in data:
            self.history = data['status']

    def start(self):
        if self.started is True:
            return
        # print("starting command!!!!!!!!!!!??!?!?!?!!?!?!?!?!?!?!? %s - %s - %s" % (self.request_id, self.device.label, self.command.label))
        self.started = True
        if self.source == 'database' and self.status == 'sent':
            logger.debug(
                "Discarding a device command message loaded from database it's already been sent.")
            self.set_sent()
            return

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
                    self.device._do_command_hook(self)
                else:
                    self.call_later = reactor.callLater(when, self.device._do_command_hook, self)
                    self.set_status('delayed')
                return True
        else:
            if self.source == 'database':  # Nothing should be loaded from the database that not a delayed command.
                logger.debug("Discarding a device command message loaded from database because it's not meant to be called later.")
                self.set_failed(message="Was loaded from database, but not meant to be called later.");
            else:
                self.device._do_command_hook(self)
                return True

    def last_message(self):
        return self.history[-1]

    def set_broadcast(self, broadcast_time=None, message=None):
        self.dirty = True
        if broadcast_time is None:
            broadcast_time = time()
        self.broadcast_time = broadcast_time
        self.status = 'broadcast'
        if message is None:
            message='Command broadcasted to hooks and gateway coms.'
        self.history.append((broadcast_time, self.status, message, self.local_gateway_id))

    def set_sent(self, sent_time=None, message=None):
        self.dirty = True
        if sent_time is None:
            sent_time = time()
        self.sent_time = sent_time
        self.status = 'sent'
        if message is None:
            message='Command sent to device or processing sub-system.'
        self.history.append((sent_time, self.status, message, self.local_gateway_id))

    def set_received(self, received_time=None, message=None):
        self.dirty = True
        if received_time is None:
            received_time = time()
        self.received_time = received_time
        self.status = 'received'
        if message is None:
            message='Command received by the device or processing sub-system.'
        self.history.append((received_time, self.status, message, self.local_gateway_id))

    def set_pending(self, pending_time=None, message=None):
        self.dirty = True
        if pending_time is None:
            pending_time = time()
        self.pending_time = pending_time
        self.status = 'pending'
        if message is None:
            message='Command processing or being completed by the device or processing sub-system.'
        if self.set_sent is None:
            self.set_sent = pending_time
            self.history.append((pending_time, 'sent', 'Command sent to device or processing sub-system. Back filled by pending action.', self.local_gateway_id))
        if self.received_time is None:
            self.received_time = pending_time
            self.history.append((pending_time, 'received', 'Command received by the device or processing sub-system. Back filled by pending action.', self.local_gateway_id))
        self.history.append((pending_time, self.status, message, self.local_gateway_id))

    def set_finished(self, finished_time=None, status=None, message=None):
        self.dirty = True
        if finished_time is None:
            finished_time = time()
        self.finished_time = finished_time
        if status is None:
            status = 'finished'
        self.status = status
        if self.set_sent is None:
            self.set_sent = finished_time
            self.history.append((finished_time, 'sent', 'Command sent to device or processing sub-system. Back filled by finished action.', self.local_gateway_id))
        if message is None:
            message = "Finished."
        self.history.append((finished_time, self.status, message, self.local_gateway_id))

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
        self.set_finished(finished_time=finished_time, status='delay_expired', message=message)

    def set_status(self, status, message=None, log_time=None):
        self.dirty = True
        self.status = status
        if log_time is None:
            log_time = time()
        self.history.append((log_time, status, message, self.local_gateway_id))

    def gw_coms_set_status(self, src_gateway_id, log_time, status, message):
        self.dirty = True
        self.status = status
        if hasattr(self, '%s_time' % status):
            setattr(self, '%s_time' % status, log_time)
        self.history.append((log_time, status, message, src_gateway_id, self.local_gateway_id))

    def set_message(self, message):
        self.dirty = True
        self.message = message
        self.history.append((time(), self.status, message, self.local_gateway_id))

    def status_received(self):
        self.command_status_received = True
        self.set_message('status_received')

    def cancel(self, finished_time=None, status=None, message=None):
        if status is None:
            status = 'canceled'
        self.set_finished(finished_time, status, message)

    @inlineCallbacks
    def save_to_db(self, forced = None):
        if self.device.gateway_id != self._Parent.gateway_id and self._Parent.is_master is not True:
            self.dirty = False
            return
        if self.dirty or forced is True:
            yield self._Parent._LocalDB.save_device_command(self)
            self.dirty = False
            self.in_db = True

    def dump(self):
        return {
            "source_gateway_id": self.source_gateway_id,
            "device_id": self.device.device_id,
            "command_id": self.command.command_id,
            "request_id": self.request_id,
            "inputs": self.inputs,
            "history": self.history,
            "requested_by": self.requested_by,
            "status": self.status,
            "persistent_request_id": self.persistent_request_id,
            "created_time": self.created_time,
            "received_time": self.received_time,
            "sent_time": self.sent_time,
            "pending_time": self.pending_time,
            "finished_time": self.finished_time,
            "not_before_time": self.not_before_time,
            "not_after_time": self.not_after_time,
            "command_status_received": self.command_status_received,
            "dirty": self.dirty,
            "started": self.started,
        }

    def __repr__(self):
        return "Device command for '%s': %s" % (self.device.label, self.command.label)

