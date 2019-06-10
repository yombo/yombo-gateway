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
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.sync_to_everywhere_mixin import SyncToEverywhereMixin
from yombo.utils import is_true_false

logger = get_logger("library.devices.device_commands.device_command")

STATUS_IDS = {
    "unknown": 0,
    "new": 100,
    "accepted": 200,
    "broadcast": 300,
    "sent": 400,
    "received": 500,
    "delayed": 600,
    "pending": 700,
    "done": 1000,
    "canceled": 2000,
    "failed": 2100,
    "expired": 2200,
}

STATUS_TEXT = {
    0: "unknown",
    100: "new",
    200: "accepted",
    300: "broadcast",
    400: "sent",
    500: "received",
    600: "delayed",
    700: "pending",
    1000: "done",
    2000: "canceled",
    2100: "failed",
    2200: "expired",
}


class DeviceCommand(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
    """
    A class that manages requests for a given device. This class is instantiated by the
    device class. Librarys and modules can use this instance to get the details of a given
    request.
    """
    _primary_column = "device_command_id"  # Used by mixins

    @property
    def status_id(self):
        if self._status not in STATUS_IDS:
            logger.warn("Device command {id} has invalid status: {status}",
                        id=self.request_id, status=self._status)
            self.status = "unknown"
            return 0
        else:
            return STATUS_IDS[self._status]

    @status_id.setter
    def status_id(self, val):
        if val in STATUS_IDS:
            self.status = STATUS_IDS[val]
            return
        if val in STATUS_TEXT:
            self.status = val
            return
        logger.warn("Device command {id} tried to set an invalid status: {status}",
                    id=self.request_id, status=val)
        raise Exception(f"Invalid status_id: {val}")

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, val):
        if val in STATUS_TEXT:
            self.status = val
        elif val in STATUS_IDS:
            self.status = STATUS_IDS[val]
        else:
            logger.warn("Device command {id} tried to set an invalid status: {status}",
                        id=self.request_id, status=val)
            raise Exception(f"Invalid status_id: {val}")

        if val in self.callbacks:
            if len(self.callbacks[val]) > 0:
                for callback in self.callbacks[val]:
                    callback(self)

    @property
    def command_id(self):
        if self.command is None:
            return None
        return self.command.command_id

    @property
    def device_id(self):
        if self.device is None:
            return None
        return self.device.device_id

    @property
    def label(self):
        return f"{self.command.label} -> {self.device.full_label}"

    def __init__(self, parent, incoming, source=None, start=None):
        """
        Get the instance setup.

        :param data: Basic details about the device command to get started.
        :param parent: A pointer to the device types instance.
        """
        self._Entity_type = "Device command"
        self._Entity_label_attribute = "machine_label"
        self._syncs_to_yombo = False

        super().__init__(parent)
        self.callbacks = {
            "broadcast": [],
            "accepted": [],
            "sent": [],
            "received": [],
            "pending": [],
            "failed": [],
            "canceled": [],
            "done": [],
        }

        self.source_gateway_id = incoming.get("source_gateway_id", self.gateway_id)
        self._setup_class_model(incoming, source=source)
        if self.source != "database":
            self.sync_item_data()

    def update_attributes_postprocess(self, incoming):
        try:
            if "device" in incoming:
                self.device_id = incoming["device"].device_id
            elif "device_id" in incoming:
                self.device = self._Devices.get(incoming["device_id"])
            else:
                raise YomboWarning("Device command must have either a device instance or device_id.")
        except:
            raise YomboWarning("Device command is unable to find a matching device for the provided device command.")

        try:
            if "command" in incoming:
                self.command_id = incoming["command"].command_id
            elif "command_id" in incoming:
                self.command = self._Commands.get(incoming["command_id"])
            else:
                raise YomboWarning("Device command must have either a command instance or command_id.")
        except:
            raise YomboWarning("Device command is unable to find a matching command for the provided device command.")

        if self.history is None:
            self.history = []

        # TODO: Check to make sure there's some from of auth_id - system or user.
        # if "auth_id" in incoming:
        #     self.auth_id = incoming["auth_id"]

        if self.status is None:
            self.status = "new"
        if self.created_at is None:
            self.created_at = time()

        if isinstance(self.command_status_received, bool) is False:
            self.command_status_received = is_true_false(self.command_status_received)

        self.call_later = None

        self.started = incoming.get("started", False)
        self.idempotence = incoming.get("idempotence", None)

        if len(self.history) == 0:
            self.history.append(self.history_dict(self.created_at,
                                                  self.status,
                                                  "Created.",
                                                  self.gateway_id))

        if self.device.gateway_id == self.gateway_id:
            self.started = False
            start = True

        # Allows various callbacks to be called when status changes.
        if "callbacks" in incoming and incoming["callbacks"] is not None:
            for cb_status, cb_callback in incoming["callbacks"].items():
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
            "time": timestamp,
            "status": status,
            "msg": message,
            "gid": gateway_id,
        }

    def add_callback(self, status, callback):
        if status in self.callbacks:
            if isinstance(callback, list):
                for cb in callback:
                    self.callbacks[status].append(cb)
            else:
                self.callbacks[status].append(callback)

    def start(self):
        """
        Send the device command to the device's command processor, which calls the "_device_command_".

        :return:
        """
        if self.started is True:
            return
        self.started = True
        if self.source == "database" and self.status == "sent":
            logger.debug(
                "Discarding a device command message loaded from database it's already been sent.")
            self.set_sent()
            return

        if self.broadcast_at is not None:
            return

        if self.not_before_at is not None:
            cur_at = time()
            if self.not_after_at < cur_at:
                self.set_delay_expired(
                    message=f'Unable to send message due to request being expired by "{cur_at - self.not_after_at}" seconds.'
                )
                if self.source != "database":  # Nothing should be loaded from the database that not a delayed command.
                    raise YomboWarning("Cannot setup delayed device command, it's already expired.")
            else:
                when = self.not_before_at - cur_at
                if when < 0:
                    self.device._do_command(self)
                else:
                    self.call_later = reactor.callLater(when, self.device._do_command, self)
                    self.set_state("delayed")
                return True
        else:
            if self.source == "database":  # Nothing should be loaded from the database that not a delayed command.
                logger.debug("Discarding a device command message loaded from database because it's not meant to be called later.")
                self.set_failed(message="Was loaded from database, but not meant to be called later.");
            else:
                self.device._do_command(self)
                return True

    def last_history(self):
        return self.history[-1]

    def set_broadcast(self, broadcast_at=None, message=None):
        if broadcast_at is None:
            broadcast_at = time()
        self.broadcast_at = broadcast_at
        self.status = "broadcast"
        if message is None:
            message="Command broadcasted to hooks and gateway coms."
        self.history.append(self.history_dict(broadcast_at, self.status, message, self.gateway_id))

    def set_accepted(self, accepted_at=None, message=None):
        if accepted_at is None:
            accepted_at = time()
        self.accepted_at = accepted_at
        self.status = "accepted"
        if message is None:
            message="Command sent to device or processing sub-system."
        self.history.append(self.history_dict(accepted_at, self.status, message, self.gateway_id))

    def set_sent(self, sent_at=None, message=None):
        if sent_at is None:
            sent_at = time()
        self.sent_at = sent_at
        self.status = "sent"
        if message is None:
            message="Command sent to device or processing sub-system."
        self.history.append(self.history_dict(sent_at, self.status, message, self.gateway_id))

    def set_received(self, received_at=None, message=None):
        if received_at is None:
            received_at = time()
        self.received_at = received_at
        self.status = "received"
        if message is None:
            message="Command received by the device or processing sub-system."
        self.history.append(self.history_dict(received_at, self.status, message, self.gateway_id))

    def set_pending(self, pending_at=None, message=None):
        if pending_at is None:
            pending_at = time()
        self.pending_at = pending_at
        self.status = "pending"
        if message is None:
            message="Command processing or being completed by the device or processing sub-system."
        if self.set_sent is None:
            self.set_sent = pending_at
            self.history.append(self.history_dict(pending_at,
                                                  "sent",
                                                  "Command sent to device or processing sub-system. Back filled by pending action.",
                                                  self.gateway_id))
        if self.received_at is None:
            self.received_at = pending_at
            self.history.append(self.history_dict(pending_at,
                                                  "received",
                                                  "Command received by the device or processing sub-system. Back filled by pending action.",
                                                  self.gateway_id))
        self.history.append(self.history_dict(pending_at, self.status, message, self.gateway_id))

    def set_finished(self, finished_at=None, status=None, message=None):
        if finished_at is None:
            finished_at = time()
        self.finished_at = finished_at
        if status is None:
            status = "done"
        self.status = status
        if self.set_sent is None:
            self.set_sent = finished_at
            self.history.append(self.history_dict(finished_at,
                                                  "sent",
                                                  "Command sent to device or processing sub-system. Back filled by finished action.",
                                                  self.gateway_id))
        if message is None:
            message = "Finished."
        self.history.append(self.history_dict(finished_at, self.status, message, self.gateway_id))

        try:
            self.call_later.cancel()
        except:
            pass
        self.sync_to_database()

    def set_canceled(self, finished_at=None, message=None):
        if message is None:
            message = "Request canceled."
        self.set_finished(finished_at=finished_at, status="canceled", message=message)

    def set_failed(self, finished_at=None, message=None):
        if message is None:
            message = "System reported command failed."
        self.set_finished(finished_at=finished_at, status="failed", message=message)

    def set_delay_expired(self, finished_at=None, message=None):
        if message is None:
            message = "System reported command failed."
        self.set_finished(finished_at=finished_at, status="delay_expired", message=message)

    def set_status(self, status, message=None, log_at=None, gateway_id=None):
        logger.debug("device ({label}) has new status: {status}", label=self.device.full_label, status=status)
        if gateway_id is None:
            gateway_id = self.gateway_id
        self.status = status
        if hasattr(self, f"{status}_at"):
            setattr(self, f"status_at", log_at)
        if log_at is None:
            log_at = time()
        self.history.append(self.history_dict(log_at, status, message, gateway_id))

    def set_message(self, message):
        self.message = message
        self.history.append(self.history_dict(time(), self.status, message, self.gateway_id))

    def status_received(self):
        self.command_status_received = True
        self.set_message("status_received")

    def cancel(self, finished_at=None, status=None, message=None):
        if status is None:
            status = "canceled"
        self.set_finished(finished_at, status, message)

    def sync_allowed(self):
        if self.device.gateway_id != self.gateway_id and self._Parent.is_master is not True:
            return False
        return True

    def asdict(self):
        return {
            "id": self.request_id,
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
            "auth_id": self.auth_id,
            "requesting_source": self.requesting_source,
            "idempotence": self.idempotence,
        }
