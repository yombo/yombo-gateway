# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_

The device class is responsible for managing a single device.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from time import time

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.utils import is_true_false, data_pickle

from yombo.core.log import get_logger
logger = get_logger('library.devices.device_command')


class Device_Command(object):
    """
    A class that manages requests for a given device. This class is instantiated by the
    device class. Librarys and modules can use this instance to get the details of a given
    request.
    """
    status_ids = {
        'unknown': 0,
        'new': 10,
        'accepted': 20,
        'broadcast': 30,
        'sent': 40,
        'received': 50,
        'delayed': 55,
        'pending': 60,
        'done': 100,
        'canceled': 200,
        'failed': 220,
        'expired': 240,
    }

    @property
    def status_id(self):
        if self._status not in self.status_ids:
            logger.warn("Device command {id} has invalid status: {status}",
                        id=self.request_id, status=self._status)
            self.status = 'unknown'
            return 0
        else:
            return self.status_ids[self._status]

    @status_id.setter
    def status_id(self, val):
        for key, key_id in self.status_ids.items():
            if key_id == val:
                self._status = key
                break
        raise Exception("Invalid status_id: %s" % val)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, val):
        try:
            status = val.lower()
            if status not in self.status_ids:
                logger.warn("Device command {id} tried to set an invalid status: {status}",
                            id=self.request_id, status=val)
                self._status = 'unknown'
            else:
                self._status = status
        except AttributeError as e:
            logger.warn("Error setting device command {id} tried to set an invalid status: {status}, error: {error}",
                        id=self.request_id, status=val, error=e)
            self._status = 'unknown'

        if val in self.callbacks:
            if len(self.callbacks[val]) > 0:
                for callback in self.callbacks[val]:
                    callback(self)

    def __init__(self, data, parent, start=None):
        """
        Get the instance setup.

        :param data: Basic details about the device command to get started.
        :param parent: A pointer to the device types instance.
        """
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
        self.callbacks = {
            'broadcast': [],
            'accepted': [],
            'sent': [],
            'received': [],
            'pending': [],
            'failed': [],
            'canceled': [],
            'done': [],
        }
        self.user_id = data['user_id']
        self.user_type = data['user_type']
        self.requesting_source = data['requesting_source']
        self._status = data.get('status', 'new')

        self.command_status_received = is_true_false(data.get('command_status_received', False))  # if a status has been reported against this request
        self.persistent_request_id = data.get('persistent_request_id', None)
        self.broadcast_at = data.get('broadcast_at', None)  # time when command was sent through hooks.
        self.accepted_at = data.get('accepted_at', None)  # when a module accepts the device command for processing
        self.sent_at = data.get('sent_at', None)  # when a module or receiver sent the command to final end-point
        self.received_at = data.get('received_at', None)  # when the command was received by the final end-point
        self.pending_at = data.get('pending_at', None)  # if command takes a while to process time, this is the timestamp of last update
        self.finished_at = data.get('finished_at', None)  # when the command is finished and end-point has changed state
        self.not_before_at = data.get('not_before_at', None)
        self.not_after_at = data.get('not_after_at', None)
        self.pin = data.get('pin', None)
        self.call_later = None
        self.created_at = data.get('created_at', time())
        self._dirty = is_true_false(data.get('dirty', True))
        self.source = data.get('source', None)
        self.started = data.get('started', False)
        self.idempotence = data.get('idempotence', None)

        if self.source == 'database':
            self._dirty = False
            self._in_db = True
        elif self.source == 'gateway_coms':
            self._dirty = False
            self._in_db = False
            reactor.callLater(1, self.check_if_device_command_in_database)

        else:
            self.history.append(self.history_dict(self.created_at, self.status, 'Created.', self.local_gateway_id))
            self._in_db = False

        if self.device.gateway_id == self.local_gateway_id:
            self.started = False
            start = True

        # Allows various callbacks to be called when status changes.
        if 'callbacks' in data and data['callbacks'] is not None:
            for cb_status, cb_callback in data['callbacks'].items():
                self.add_callback(cb_status, cb_callback)

        if start is None or start is True:
            reactor.callLater(0.0001, self.start)

    def history_dict(self, timestamp, status, message, gateway_id):
        """
        Create a history dictionary based on arguments.

        :param timestamp:
        :param status:
        :param message:
        :param gateway_id:
        :return:
        """
        return {
            'time': timestamp,
            'status': status,
            'msg': message,
            'gid': gateway_id,
        }

    def add_callback(self, status, callback):
        if status in self.callbacks:
            if isinstance(callback, list):
                for cb in callback:
                    self.callbacks[status].append(cb)
            else:
                self.callbacks[status].append(callback)

    @inlineCallbacks
    def check_if_device_command_in_database(self):
        where = {
            'request_id': self.request_id,
        }
        device_commands = yield self._Parent._LocalDB.get_device_commands(where)
        if len(device_commands) > 0:
            self._in_db = True
            self.save_to_db()

    def update_attributes(self, data):
        if 'command_status_received' in data:
            self.command_status_received = data['command_status_received']
        if 'broadcast_at' in data:
            self.broadcast_at = data['broadcast_at']
        if 'accepted_at' in data:
            self.accepted_at = data['accepted_at']
        if 'sent_at' in data:
            self.sent_at = data['sent_at']
        if 'received_at' in data:
            self.received_at = data['received_at']
        if 'pending_at' in data:
            self.pending_at = data['pending_at']
        if 'finished_at' in data:
            self.finished_at = data['finished_at']
        if 'not_before_at' in data:
            self.not_before_at = data['not_before_at']
            # print("in device command, setting not before: %s (currently: %s_" % (self.not_before_at, time()))
        if 'not_after_at' in data:
            self.not_after_at = data['not_after_at']
        if 'history' in data:
            self.history = data['history']
        if 'status' in data:
            self.status = data['status']

    def start(self):
        """
        Send the device command to the device's command processor, which calls the '_device_command_'.

        :return:
        """
        if self.started is True:
            return
        self.started = True
        if self.source == 'database' and self.status == 'sent':
            logger.debug(
                "Discarding a device command message loaded from database it's already been sent.")
            self.set_sent()
            return
        if self.broadcast_at is not None:
            return

        if self.not_before_at is not None:
            cur_at = time()
            if self.not_after_at < cur_at:
                self.set_delay_expired(message='Unable to send message due to request being expired by "%s" seconds.'
                                    % str(cur_at - self.not_after_at))
                if self.source != 'database':  # Nothing should be loaded from the database that not a delayed command.
                    raise YomboWarning("Cannot setup delayed device command, it's already expired.")
            else:
                when = self.not_before_at - cur_at
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

    def last_history(self):
        return self.history[-1]

    def set_broadcast(self, broadcast_at=None, message=None):
        self._dirty = True
        if broadcast_at is None:
            broadcast_at = time()
        self.broadcast_at = broadcast_at
        self.status = 'broadcast'
        if message is None:
            message='Command broadcasted to hooks and gateway coms.'
        self.history.append(self.history_dict(broadcast_at, self.status, message, self.local_gateway_id))

    def set_accepted(self, accepted_at=None, message=None):
        self._dirty = True
        if accepted_at is None:
            accepted_at = time()
        self.accepted_at = accepted_at
        self.status = 'accepted'
        if message is None:
            message='Command sent to device or processing sub-system.'
        self.history.append(self.history_dict(accepted_at, self.status, message, self.local_gateway_id))

    def set_sent(self, sent_at=None, message=None):
        self._dirty = True
        if sent_at is None:
            sent_at = time()
        self.sent_at = sent_at
        self.status = 'sent'
        if message is None:
            message='Command sent to device or processing sub-system.'
        self.history.append(self.history_dict(sent_at, self.status, message, self.local_gateway_id))

    def set_received(self, received_at=None, message=None):
        self._dirty = True
        if received_at is None:
            received_at = time()
        self.received_at = received_at
        self.status = 'received'
        if message is None:
            message='Command received by the device or processing sub-system.'
        self.history.append(self.history_dict(received_at, self.status, message, self.local_gateway_id))

    def set_pending(self, pending_at=None, message=None):
        self._dirty = True
        if pending_at is None:
            pending_at = time()
        self.pending_at = pending_at
        self.status = 'pending'
        if message is None:
            message='Command processing or being completed by the device or processing sub-system.'
        if self.set_sent is None:
            self.set_sent = pending_at
            self.history.append(self.history_dict(pending_at, 'sent', 'Command sent to device or processing sub-system. Back filled by pending action.', self.local_gateway_id))
        if self.received_at is None:
            self.received_at = pending_at
            self.history.append(self.history_dict(pending_at, 'received', 'Command received by the device or processing sub-system. Back filled by pending action.', self.local_gateway_id))
        self.history.append(self.history_dict(pending_at, self.status, message, self.local_gateway_id))

    def set_finished(self, finished_at=None, status=None, message=None):
        self._dirty = True
        if finished_at is None:
            finished_at = time()
        self.finished_at = finished_at
        if status is None:
            status = 'done'
        self.status = status
        if self.set_sent is None:
            self.set_sent = finished_at
            self.history.append(self.history_dict(finished_at, 'sent', 'Command sent to device or processing sub-system. Back filled by finished action.', self.local_gateway_id))
        if message is None:
            message = "Finished."
        self.history.append(self.history_dict(finished_at, self.status, message, self.local_gateway_id))

        try:
            self.call_later.cancel()
        except:
            pass
        self.save_to_db()

    def set_canceled(self, finished_at=None, message=None):
        if message is None:
            message = "Request canceled."
        self.set_finished(finished_at=finished_at, status='canceled', message=message)

    def set_failed(self, finished_at=None, message=None):
        if message is None:
            message = "System reported command failed."
        self.set_finished(finished_at=finished_at, status='failed', message=message)

    def set_delay_expired(self, finished_at=None, message=None):
        if message is None:
            message = "System reported command failed."
        self.set_finished(finished_at=finished_at, status='delay_expired', message=message)

    def set_status(self, status, message=None, log_at=None, gateway_id=None):
        logger.debug("device ({label}) has new status: {status}", label=self.device.full_label, status=status)
        if gateway_id is None:
            gateway_id = self.local_gateway_id
        self._dirty = True
        self.status = status
        if hasattr(self, '%s_at' % status):
            setattr(self, '%s_at' % status, log_at)
        if log_at is None:
            log_at = time()
        self.history.append(self.history_dict(log_at, status, message, gateway_id))

    def set_message(self, message):
        self._dirty = True
        self.message = message
        self.history.append(self.history_dict(time(), self.status, message, self.local_gateway_id))

    def status_received(self):
        self.command_status_received = True
        self.set_message('status_received')

    def cancel(self, finished_at=None, status=None, message=None):
        if status is None:
            status = 'canceled'
        self.set_finished(finished_at, status, message)

    # @inlineCallbacks
    def save_to_db(self, forced = None):
        if self.device.gateway_id != self._Parent.gateway_id and self._Parent.is_master is not True:
            self._dirty = False
            return
        if self._dirty or forced is True:
            data = self.asdict()
            del data['started']
            # if self.inputs is None:
            #     data['inputs'] = None
            # else:
            data['history'] = data_pickle(self.history)
            data['inputs'] = data_pickle(self.inputs)

            if self._in_db is True:
                self._Parent._LocalDB.add_bulk_queue('device_commands', 'update', data, 'request_id')
            else:
                self._Parent._LocalDB.add_bulk_queue('device_commands', 'insert', data, 'request_id')

            self._dirty = False
            self._in_db = True

    def asdict(self):
        return {
            "request_id": self.request_id,
            "persistent_request_id": self.persistent_request_id,
            "source_gateway_id": self.source_gateway_id,
            "device_id": self.device.device_id,
            "command_id": self.command.command_id,
            "inputs": self.inputs,
            "created_at": self.created_at,
            "broadcast_at": self.broadcast_at,
            "accepted_at": self.accepted_at,
            "sent_at": self.sent_at,
            "received_at": self.received_at,
            "pending_at": self.pending_at,
            "finished_at": self.finished_at,
            "not_before_at": self.not_before_at,
            "not_after_at": self.not_after_at,
            "started": self.started,
            "command_status_received": self.command_status_received,
            "history": self.history,
            "status": self.status,
            "user_id": self.user_id,
            "user_type": self.user_type,
            "requesting_source": self.requesting_source,
            "idempotence": self.idempotence,
        }

    def __repr__(self):
        return "Device command for '%s': %s" % (self.device.label, self.command.label)
