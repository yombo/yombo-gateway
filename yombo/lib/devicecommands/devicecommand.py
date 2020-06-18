# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_

The device class is responsible for managing a single device.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devicecommands/devicecommand.html>`_
"""
# Import python libraries
from time import time
from typing import Any, ClassVar, Callable, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants.device_commands import *
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.utils import is_true_false
from yombo.utils.caller import caller_string
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.devices.device_commands.device_command")

STATUS_TEXT = {
    DEVICE_COMMAND_STATUS_UNKNOWN: 0,
    DEVICE_COMMAND_STATUS_NEW: 100,
    DEVICE_COMMAND_STATUS_ACCEPTED: 200,
    DEVICE_COMMAND_STATUS_BROADCAST: 300,
    DEVICE_COMMAND_STATUS_SENT: 400,
    DEVICE_COMMAND_STATUS_RECEIVED: 500,
    DEVICE_COMMAND_STATUS_DELAYED: 600,
    DEVICE_COMMAND_STATUS_PENDING: 700,
    DEVICE_COMMAND_STATUS_DONE: 1000,
    DEVICE_COMMAND_STATUS_CANCELED: 2000,
    DEVICE_COMMAND_STATUS_FAILED: 2100,
    DEVICE_COMMAND_STATUS_EXPIRED: 2200,
}

STATUS_IDS = {
    0: DEVICE_COMMAND_STATUS_UNKNOWN,
    100: DEVICE_COMMAND_STATUS_NEW,
    200: DEVICE_COMMAND_STATUS_ACCEPTED,
    300: DEVICE_COMMAND_STATUS_BROADCAST,
    400: DEVICE_COMMAND_STATUS_SENT,
    500: DEVICE_COMMAND_STATUS_RECEIVED,
    600: DEVICE_COMMAND_STATUS_DELAYED,
    700: DEVICE_COMMAND_STATUS_PENDING,
    1000: DEVICE_COMMAND_STATUS_DONE,
    2000: DEVICE_COMMAND_STATUS_CANCELED,
    2100: DEVICE_COMMAND_STATUS_FAILED,
    2200: DEVICE_COMMAND_STATUS_EXPIRED,
}


class DeviceCommand(Entity, LibraryDBChildMixin):
    """
    A class that manages requests for a given device. This class is instantiated by the
    device class. Librarys and modules can use this instance to get the details of a given
    request.
    """
    _sync_to_api: ClassVar[bool] = False

    _Entity_type: ClassVar[str] = "Device command"
    _Entity_label_attribute: ClassVar[str] = "machine_label"
    _sync_data_delay: ClassVar[int] = 10

    @property
    def status_id(self) -> int:
        """ Lookup the status_id using the status field and STATUS_TEXT."""
        if self._status not in STATUS_TEXT:
            logger.warn("Device command {id} has invalid status: {status}",
                        id=self.device_command_id, status=self._status)
            self._status = "unknown"
            return 0
        else:
            return STATUS_TEXT[self._status]

    @status_id.setter
    def status_id(self, val) -> None:
        """ Set the status ID using either ID number or text."""
        if val in STATUS_IDS:
            self._status = STATUS_IDS[val]
            return
        if val in STATUS_TEXT:
            self._status = val
            return
        logger.warn("Device command {id} tried to set an invalid status: {status}",
                    id=self.device_command_id, status=val)
        raise Exception(f"Invalid status_id: {val}")

    @property
    def status(self) -> str:
        """ Return the device command status."""
        return self._status

    @status.setter
    def status(self, val) -> None:
        """ Set the status using either text or id number. """
        if val in STATUS_TEXT:
            self._status = val
        elif val in STATUS_IDS:
            self._status = STATUS_IDS[val]
        else:
            logger.warn("Device command {id} tried to set an invalid status: {status}",
                        id=self.device_command_id, status=val)
            raise Exception(f"Invalid status_id: {val}")

        if val in self.callbacks:
            if len(self.callbacks[val]) > 0:
                for callback in self.callbacks[val]:
                    callback(self)

    @property
    def command_id(self) -> Union[None, str]:
        """ If a valid command exists, return it's ID, otherwise None. """
        if self.command is None:
            return None
        return self.command.command_id

    @property
    def device_id(self) -> str:
        """ If a valid device exists, return it's ID, otherwise None. """
        if self.device is None:
            return None
        return self.device.device_id

    @property
    def label(self) -> str:
        """ A combined command and device label. """
        return self.__repr__()

    def __repr__(self) -> str:
        """ A combined command and device label. """
        return f"{self.command.label} -> {self.device.full_label}"

    def __init__(self, parent, start: Union[None, bool] = None, **kwargs) -> None:
        """
        Get the instance setup.

        :param incoming: Basic details about the device command to get started.
        :param parent: A pointer to the device types instance.
        """
        self._status = "unknown"

        super().__init__(parent, **kwargs)
        self.__dict__["history"] = []
        self.callbacks = {}

        if len(self.history) == 0:
            self.__dict__["history"].append(self.history_dict(self.created_at,
                                                              self.status,
                                                              "Created.",
                                                              self._gateway_id)
                                            )

        if self.broadcast_at is not None and self.broadcast_at > 0:
            self.__dict__["started"] = False

    def load_attribute_values_pre_process(self, incoming: dict) -> None:
        """ Setup basic class attributes based on incoming data. """

        self.__dict__["callbacks"] = {
            "broadcast": [],
            "accepted": [],
            "sent": [],
            "received": [],
            "pending": [],
            "failed": [],
            "canceled": [],
            "done": [],
        }

        # Default values
        self.__dict__["started"] = False
        self.__dict__["status"] = DEVICE_COMMAND_STATUS_NEW
        self.__dict__["created_at"] = time()
        self.__dict__["call_later"] = None
        self.__dict__["started"] = incoming.get("started", False)
        self.__dict__["idempotence"] = incoming.get("idempotence", None)
        self.__dict__["history"] = []
        self.__dict__["started"] = False
        self.__dict__["uploadable"] = True  # Todo: Make this settable.
        if "uploaded" in incoming:
            self.__dict__["uploaded"] = is_true_false(incoming["uploaded"], only_bool=True)
        else:
            self.__dict__["uploaded"] = False
        self.gateway_id = incoming.get("gateway_id", self._gateway_id)
        if self.gateway_id is None:
            self.gateway_id = self._gateway_id

        self.update_attributes_pre_process(incoming)

    def update_attributes_pre_process(self, incoming: dict) -> None:
        """
        Modify this instance after the update_attributes has completed.
        :param incoming:
        :return:
        """
        # Allows various callbacks to be called when status changes.
        if "callbacks" in incoming and incoming["callbacks"] is not None:
            for cb_status, cb_callback in incoming["callbacks"].items():
                self.add_callback(cb_status, cb_callback)
            del incoming["callbacks"]

    @staticmethod
    def history_dict(timestamp: Union[int, float], status: str, message: Optional[str], gateway_id: str,
                     source: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a history dictionary based on arguments.

        :param timestamp:
        :param status:
        :param message:
        :param gateway_id:
        :param source:
        :return:
        """
        if source is None:
            source = ""

        return {
            "time": timestamp,
            "status": status,
            "message": message,
            "gwid": gateway_id,
            "source": source,
        }

    def add_callback(self, status: str, callback: Callable) -> None:
        """
        Add a callback to be called when the status changes to a particular status.

        :param status: The status to monitor. One of: yombo.constants.device_command: DEVICE_COMMAND_STATUS_*
        :param callback:
        :return:
        """
        if status in self.callbacks:
            if isinstance(callback, list):
                for cb in callback:
                    self.__dict__["callbacks"][status].append(cb)
            else:
                self.__dict__["callbacks"][status].append(callback)

    @inlineCallbacks
    def start_device_command(self):
        """
        Send the device command to the device's command processor, which calls the "_device_command_".

        :return:
        """
        print(f"start_device_command 0 - self.broadcast_at : {self.broadcast_at}")
        source = caller_string()
        if self.started is True:
            print("start_device_command 1")
            return
        if (self.broadcast_at is not None and self.broadcast_at > 0) or self.status_id >= 200:
            print("start_device_command 2")
            self.started = True
            return
        print("start_device_command a")
        self.started = True
        # if self.source == "database" and self.status == "sent":
        #     logger.debug(
        #         "Discarding a device command message loaded from database it's already been sent.")
        #     self.set_sent()
        #     return

        print(f"start_device_command d - self.broadcast_at : {self.broadcast_at}")
        if self.broadcast_at is not None:
            return

        print(f"start_device_command e - self.not_before_at : {self.not_before_at}")
        if self.not_before_at is not None:
            print("start_device_command g")
            cur_at = time()
            if self.not_after_at < cur_at:
                self.set_delay_expired(
                    message=f'Unable to send message due to request being expired by "{cur_at - self.not_after_at}" seconds.'
                )
                if self._meta["load_source"] != "database":  # Nothing should be loaded from the database that not a delayed command.
                    raise YomboWarning("Cannot setup delayed device command, it's already expired.")
            else:
                print("start_device_command l")
                when = self.not_before_at - cur_at
                if when < 0:
                    yield self._start_device_command()
                else:
                    self.call_later = reactor.callLater(when, self.device._start_device_command)
                    self.set_state("delayed")
                return True
        else:
            print(f"start_device_command w")
            if self._meta["load_source"] == "database":  # Nothing should be loaded from the database that not a delayed command.
                logger.debug("Discarding a device command message loaded from database because it's not meant to be called later.")
                self.set_failed(message="Was loaded from database, but not meant to be called later.");
            else:
                print(f"start_device_command y")
                yield self._start_device_command()
                return True

    @inlineCallbacks
    def _start_device_command(self) -> None:
        """
        Performs the actual sending of a device command. This calls the hook "_device_command_". Any modules that
        have implemented this hook can monitor or act on the hook.

        When a device changes state, whatever module changes the state of a device, or is responsible for reporting
        those changes, it *must* call "self._Devices["devicename/deviceid"].set_state()

        **Hooks called**:

        * _devices_command_ : Sends kwargs: *device*, the device object and *command*. This receiver will be
          responsible for obtaining whatever information it needs to complete the action being requested.

        :return:
        """
        print("_start_device_command")
        items = {
            DEVICE_COMMAND_COMMAND: self.command,
            DEVICE_COMMAND_COMMAND_ID: self.command.command_id,
            DEVICE_COMMAND_DEVICE: self.device,
            DEVICE_COMMAND_DEVICE_ID: self.device_id,
            DEVICE_COMMAND_INPUTS: self.inputs,
            DEVICE_COMMAND_DEVICE_COMMAND_ID: self.device_command_id,
            DEVICE_COMMAND_DEVICE_COMMAND: self,
            DEVICE_COMMAND_PIN: self.pin,
            DEVICE_COMMAND_GATEWAY_ID: self.gateway_id,
            DEVICE_COMMAND_REQUEST_BY: self.request_by,
            DEVICE_COMMAND_REQUEST_BY_TYPE: self.request_by_type,
            DEVICE_COMMAND_REQUEST_CONTEXT: self.request_context,
        }
        # logger.debug("calling _device_command_, device_command_id: {device_command_id}", device_command_id=device_command.device_command_id)
        self.set_broadcast()
        print("_start_device_command: _device_command_")
        print(items)
        results = yield global_invoke_all("_device_command_", called_by=self, arguments=items,
                                          _force_debug=True)
        for component, result in results.items():
            if result is True:
                self.set_received(message=f"Received by: {component}")
        self._Parent._Statistics.increment("lib.devices.commands_sent", anon=True)

    def broadcast_status(self) -> None:
        """
        Broadcasts the current device state. Typically called internally by this class.
        """
        last_history = self.history[-1]
        print(f"broadcast_status, hisytory: {last_history}")
        global_invoke_all("_device_command_status_",
                          called_by=self,
                          arguments={
                              "device_command": self,
                              "status": last_history["status"],
                              "status_id": STATUS_TEXT[last_history["status"]],
                              "status_at": last_history["time"],
                              "message": last_history["message"],
                              "gateway_id": last_history["gwid"],
                              "source": last_history["source"],
                              }
                          )

    def device_command_processing(self, **kwargs) -> None:
        """
        A shortcut to calling device_comamnd_sent and device_command_received together.

        This will trigger two calls of the same hook "_device_command_state_". Once for state
        of "received" and another for "sent".

        :param device_command_id: The device_command_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        self.set_sent(message=message, sent_at=log_time)
        self.set_received(message=message, received_at=log_time, source=source)
        self.broadcast_status()
        # global_invoke_all("_device_command_status_",
        #                   called_by=self,
        #                   device_command=self,
        #                   status=self.status,
        #                   status_id=self.status_id,
        #                   message=message,
        #                   source=source,
        #                   )

    def device_command_accepted(self, **kwargs) -> None:
        """
        Called by any module that accepts the command for processing.

        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        self.set_accepted(message=message, accepted_at=log_time, source=source)
        self.broadcast_status()
        # global_invoke_all("_device_command_status_",
        #                   called_by=self,
        #                   device_command=self,
        #                   status=self.status,
        #                   status_id=self.status_id,
        #                   message=message,
        #                   source=source,
        #                   )

    def device_command_sent(self, **kwargs) -> None:
        """
        Called by any module that has sent the command to an end-point.

        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        self.set_sent(message=message, sent_at=log_time, source=source)
        self.broadcast_status()
        # global_invoke_all("_device_command_status_",
        #                   called_by=self,
        #                   device_command=self,
        #                   status=self.status,
        #                   status_id=self.status_id,
        #                   message=message,
        #                   source=source,
        #                   )

    def device_command_received(self, **kwargs) -> None:
        """
        Called by any module that intends to process the command and deliver it to the automation device.

        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        self.set_received(message=message, received_at=log_time, source=source)
        self.set_received(message=message, received_at=log_time, source=source)
        self.broadcast_status()
        # global_invoke_all("_device_command_status_",
        #                   called_by=self,
        #                   device_command=self,
        #                   status=self.status,
        #                   status_id=self.status_id,
        #                   message=message,
        #                   source=source,
        #                   )

    def device_command_pending(self, **kwargs) -> None:
        """
        This should only be called if command processing takes more than 1 second to complete. This lets applications,
        users, and everyone else know it's pending. Calling this excessively can cost a lot of local CPU cycles.

        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        self.set_pending(message=message, pending_at=log_time, source=source)
        self.broadcast_status()
        # global_invoke_all("_device_command_status_",
        #                   called_by=self,
        #                   device_command=self,
        #                   status=self.status,
        #                   status_id=self.status_id,
        #                   message=message,
        #                   source=source,
        #                   )

    def device_command_failed(self, **kwargs) -> None:
        """
        Should be called when a the command cannot be completed for whatever reason.

        A status can be provided: send a named parameter of "message" with any value.

        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        self.set_failed(message=message, finished_at=log_time, source=source)
        if message is not None:
            logger.warn("Device ({label}) command failed: {message}", label=self.label, message=message,
                        state="failed")
        self.broadcast_status()
        # global_invoke_all("_device_command_status_",
        #                   called_by=self,
        #                   device_command=self,
        #                   status=self.status,
        #                   status_id=self.status_id,
        #                   message=message,
        #                   source=source,
        #                   )

    def device_command_cancel(self, **kwargs) -> None:
        """
        Cancel a device command request. Cannot guarantee this will happen. Unable to cancel if status is "done" or
        "failed".

        :return:
        """
        log_time = kwargs.get("log_time", None)
        message = kwargs.get("message", None)
        source = kwargs.get("source", None)
        self.set_canceled(message=message, finished_at=log_time, source=source)
        if message is not None:
            logger.debug("Device ({label}) command failed: {message}", label=self.label, message=message)
        self.broadcast_status()
        # global_invoke_all("_device_command_status_",
        #                   called_by=self,
        #                   device_command=self,
        #                   status=self.status,
        #                   status_id=self.status_id,
        #                   message=message,
        #                   source=source,
        #                   )

    def device_delay_expired(self, **kwargs) -> None:
        """
        This is called on system bootup when a device command was set for a delayed execution,
        but the time limit for executing the command has elasped.

        :return:
        """
        log_time = kwargs.get("log_time", None)
        message = kwargs.get("message", None)
        source = kwargs.get("source", None)
        self.set_delay_expired(message=message, finished_at=log_time, source=source)
        if message is not None:
            logger.debug("Device ({label}) command failed: {message}", label=self.label, message=message)
        self.broadcast_status()
        # global_invoke_all("_device_command_status_",
        #                   called_by=self,
        #                   device_command=self,
        #                   status=self.status,
        #                   status_id=self.status_id,
        #                   message=message,
        #                   source=source,
        #                   )

    def device_command_done(self, **kwargs) -> None:
        """
        Called by any module that has completed processing of a command request.

        A status can be provided: send a named parameter of "message" with any value.

        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        self.set_finished(message=message, finished_at=log_time, source=source)
        self.broadcast_status()
        # global_invoke_all("_device_command_status_",
        #                   called_by=self,
        #                   device_command=self,
        #                   status=self.status,
        #                   status_id=self.status_id,
        #                   message=message,
        #                   source=source,
        #                   )

    def last_history(self):
        return self.history[-1]

    def set_broadcast(self, broadcast_at: Optional[Union[int, float]] = None,
                      message: Optional[str] = None,
                      source: Optional[str] = None) -> None:
        if broadcast_at is None:
            broadcast_at = time()
        self.broadcast_at = broadcast_at
        self.status = "broadcast"
        if message is None:
            message="Command broadcasted to hooks and gateway coms."
        self.history.append(self.history_dict(broadcast_at, self.status, message, self._gateway_id, source))

    def set_accepted(self, accepted_at: Optional[Union[int, float]] = None, message: Optional[str] = None,
                     source: Optional[str] = None) -> None:
        if accepted_at is None:
            accepted_at = time()
        self.accepted_at = accepted_at
        self.status = "accepted"
        if message is None:
            message="Command sent to device or processing sub-system."
        self.history.append(self.history_dict(accepted_at, self.status, message, self._gateway_id, source))

    def set_sent(self, sent_at: Optional[Union[int, float]] = None, message: Optional[str] = None,
                 source: Optional[str] = None) -> None:
        if sent_at is None:
            sent_at = time()
        self.sent_at = sent_at
        self.status = "sent"
        if message is None:
            message="Command sent to device or processing sub-system."
        self.history.append(self.history_dict(sent_at, self.status, message, self._gateway_id, source))

    def set_received(self, received_at: Optional[Union[int, float]] = None, message: Optional[str] = None,
                     source: Optional[str] = None) -> None:
        if received_at is None:
            received_at = time()
        self.received_at = received_at
        self.status = "received"
        if message is None:
            message = "Command received by the device or processing sub-system."
        self.history.append(self.history_dict(received_at, self.status, message, self._gateway_id, source))

    def set_pending(self, pending_at: Optional[Union[int, float]] = None, message: Optional[str] = None,
                    source: Optional[str] = None) -> None:
        if pending_at is None:
            pending_at = time()
        self.pending_at = pending_at
        self.status = "pending"
        if message is None:
            message = "Command processing or being completed by the device or processing sub-system."
        if self.pending_at is None:
            self.pending_at = pending_at
            self.history.append(self.history_dict(pending_at,
                                                  "sent",
                                                  "Command sent to device or processing sub-system. Back filled by pending action.",
                                                  self._gateway_id,
                                                  source))
        if self.received_at is None:
            self.received_at = pending_at
            self.history.append(self.history_dict(pending_at,
                                                  "received",
                                                  "Command received by the device or processing sub-system. Back filled by pending action.",
                                                  self._gateway_id, source))
        self.history.append(self.history_dict(pending_at, self.status, message, self._gateway_id, source))

    def set_finished(self, finished_at: Optional[Union[int, float]] = None, status: Optional[str] = None,
                     message: Optional[str] = None, source: Optional[str] = None) -> None:
        if finished_at is None:
            finished_at = time()
        self.finished_at = finished_at
        if status is None:
            status = "done"
        self.status = status
        if self.finished_at is None:
            self.finished_at = finished_at
            self.history.append(self.history_dict(finished_at,
                                                  "sent",
                                                  "Command sent to device or processing sub-system. Back filled by finished action.",
                                                  self._gateway_id,
                                                  source))
        if message is None:
            message = "Finished."
        self.history.append(self.history_dict(finished_at, self.status, message, self._gateway_id, source))

        try:
            self.call_later.cancel()
        except:
            pass

    def set_canceled(self, finished_at: Optional[Union[int, float]] = None, message: Optional[str] = None,
                     source: Optional[str] = None) -> None:
        if message is None:
            message = "Request canceled."
        self.set_finished(finished_at=finished_at, status="canceled", message=message, source=source)

    def set_failed(self, finished_at: Optional[Union[int, float]] = None, message: Optional[str] = None,
                   source: Optional[str] = None) -> None:
        if message is None:
            message = "System reported command failed."
        self.set_finished(finished_at=finished_at, status="failed", message=message, source=source)

    def set_delay_expired(self, finished_at: Optional[Union[int, float]] = None, message: Optional[str] = None,
                          source: Optional[str] = None) -> None:
        if message is None:
            message = "System reported command failed."
        self.set_finished(finished_at=finished_at, status="delay_expired", message=message, source=source)

    def set_status(self, status: str, message: Optional[str] = None, log_at: Optional[Union[int, float]] = None,
                   gateway_id: Optional[str] = None, source: Optional[str] = None) -> None:
        logger.debug("device ({label}) has new status: {status}", label=self.device.full_label, status=status)
        if gateway_id is None:
            gateway_id = self._gateway_id
        self.status = status
        if hasattr(self, f"{status}_at"):
            setattr(self, f"status_at", log_at)
        if log_at is None:
            log_at = time()
        self.history.append(self.history_dict(log_at, status, message, gateway_id, source))

    def set_message(self, message: str, source: Optional[str] = None) -> None:
        self.history.append(self.history_dict(time(), self.status, message, self._gateway_id, source))

    def cancel(self, finished_at: Optional[Union[int, float]] = None, status: Optional[str] = None,
                     message: Optional[str] = None, source: Optional[str] = None) -> None:
        if status is None:
            status = "canceled"
        self.set_finished(finished_at, status, message, source)

    def sync_allowed(self) -> bool:
        if self.device.gateway_id != self._gateway_id and self._Parent.is_master is not True:
            return False
        return True
