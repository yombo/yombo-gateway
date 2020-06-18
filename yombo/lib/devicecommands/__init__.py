# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Device Commands @ Library Documentation <https://yombo.net/docs/libraries/device_commands>`_

Stores commands that have been sent to device - device commands. This is not to be confused with all possible commands
for a device, that is stored in device type commands.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devicecommands/__init__.html>`_
"""
from copy import copy
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

import weakref

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants.device_commands import DEVICE_COMMAND_STATUS_NEW
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.schemas import DeviceCommandSchema
from yombo.lib.commands import Command
from yombo.lib.devices.device import Device
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.core.log import get_logger
from yombo.utils import sleep, random_string
from yombo.utils.caller import caller_string
from .devicecommand import DeviceCommand

logger = get_logger("library.device_commands")


class DeviceCommands(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Stores and track commands sent to devices (device commands). Device commands and their status will be broadcast
    to the gateway cluster. This allows one gateway to send commands to a device attached to a different gateway.
    """
    mqtt: ClassVar = None  # An MQTT connection to process device command requests.

    device_commands = {}  # tracks commands being sent to devices. Also tracks if a command is delayed.
    _startup_queue = {}  # Any device commands sent before the system is ready will be stored here.

    _storage_primary_field_name: ClassVar[str] = "device_command_id"
    _storage_primary_length: ClassVar[int] = 25

    # The remaining attributes are used by various mixins.
    _storage_attribute_name: ClassVar[str] = "device_commands"
    _storage_default_where: ClassVar[list] = ["status = ? OR status = ?", 1, 0]
    _storage_label_name: ClassVar[str] = "device_command"
    _storage_class_reference: ClassVar = DeviceCommand
    _storage_schema: ClassVar = DeviceCommandSchema()
    _storage_pickled_fields: ClassVar[Dict[str, str]] = {
        "inputs": "msgpack_zip",
        "history": "msgpack_zip"
    }
    _storage_primary_field_name_extra: ClassVar[list] = ["device", "command", "pin"]
    _new_items_require_authentication: ClassVar[bool] = True
    _storage_search_fields: ClassVar[List[str]] = [
        "device_type_id", "machine_label", "command_id", "input_type_id", "machine_label", "label", "live_update",
        "value_required", "encryption"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "created_at"
    _storage_attribute_sort_key_order: ClassVar[str] = "desc"

    @inlineCallbacks
    def _init_(self, **kwargs) -> None:
        """
        Setups up the basic framework. Loads the device commands from the database.
        """
        # used to store delayed queue for restarts. It'll be a bare, dehydrated version.
        # store the above, but after hydration.
        self.clean_device_commands_loop = None

        load_history_depth = self._Configs.get("devices.load_device_command_history", 40)
        for device_id, device in self._Devices.devices.items():
            items = yield self.load_from_database(
                return_data=True,
                db_args={"where": {"created_at": [time() - 60*60*24*180, ">"],
                                   "device_id": device_id},
                         "limit": load_history_depth,
                         "orderby": "created_at DESC"
                         }
            )
            yield self.load_db_items_to_memory(items, load_source="database")

    def load_an_item_to_memory_pre_process(self, incoming: dict, **kwargs) -> None:
        """
        Ensure that the device_id exists before being loaded into memory.

        :param incoming: The dictionary loaded from the database.
        :param kwargs:
        :return:
        """
        print("DC: load_an_item_to_memory_pre_process.. 1")
        if "device_id" in incoming:
            incoming["device"] = self._Devices[incoming["device_id"]]
        if incoming["device"] is None:
            raise YomboWarning("Device Command must have either a device or device_id")

        print("DC: load_an_item_to_memory_pre_process.. a")
        if "command_id" in incoming:
            incoming["command"] = self._Devices[incoming["command_id"]]
        if incoming["command"] is None:
            raise YomboWarning("Device Command must have either command or command_id.")
        print("DC: load_an_item_to_memory_pre_process.. z")

    def load_an_item_to_memory_post_process(self, instance: DeviceCommand) -> None:
        """
        All device commands are stored here. Additionally, weak references to the device commands is stored local within
        the device instance. This allows devices to quickly find device command sent, while not having to mess with
        tracking references too much.

        The weakref module is used to handle this task. This method creates the weakref links, and adding a callback
        to cleanup the device weakref when it's time to cleanup the number of device commands sent.

        :param instance: device command instance
        :return:
        """
        print("DC: load_an_item_to_memory_post_process.. 1")
        print(instance.__dict__)

        instance.device.device_commands.appendleft(weakref.proxy(instance))
        print("DC: load_an_item_to_memory_post_process.. a")
        f = weakref.finalize(instance,
                             self.remove_weakref_device_command,
                             copy(instance.device_id),
                             copy(instance.device_command_id))
        print("DC: load_an_item_to_memory_post_process.. b")
        f.atexit = False
        print("DC: load_an_item_to_memory_post_process.. z")

    def remove_weakref_device_command(self, device_id: str, device_command_id: str) -> None:
        """
        This is called by the weakref module when the primary reference has been removed. This removes
        the reference within the device instance.

        :param device_id:
        :param device_command_id:
        :return:
        """
        device = self._Devices[device_id]

        for i, obj in enumerate(device.device_commands):
            try:
                if obj.device_command_id == device_command_id:
                    del device.device_commands[i]
            except ReferenceError:
                del device.device_commands[i]

    def _modules_prestarted_(self, **kwargs) -> None:
        """
        Once the gateway has loaded all the modules and is about to start the modules, this hook checks to see
        if there are any device commands that need to be started as well as any items in the startup queue that should
        be sent.

        Modules should be ready to handle any commands after their _load_ is done. This is called after _load_ and
        before _start_.
        """
        for device_command_id, device_command in self.device_commands.items():
            reactor.callLater(0.0001, device_command.start_device_command)

        for command, request in self._startup_queue.items():
            self.command(request["device_id"],
                         request["command_id"],
                         not_before=request["not_before"],
                         max_delay=request["max_delay"],
                         **request["kwargs"])
        self._startup_queue = None

    def mqtt_incoming(self, topic: str, payload, qos: int, retain):
        """
        Handle incoming device command from other gateways.

        :param topic:
        :param payload:
        :param qos:
        :param retain:
        :return:
        """
        # Not implemented yet.
        pass

    @inlineCallbacks
    def new(self, device: Type[Device] = None, command: Optional[Command] = None,
            gateway_id: Optional[str] = None, inputs: Optional[List[dict]] = None,
            status: Optional[str] = None, idempotence: Optional[str] = None, request_by: Optional[str] = None,
            request_by_type: Optional[str] = None, request_context: Optional[str] = None,
            authentication=None, device_command_id: Optional[str] = None, persistent_request_id: Optional[str] = None,
            created_at: Optional[Union[int, float]] = None, broadcast_at: Optional[Union[int, float]] = None,
            accepted_at: Optional[Union[int, float]] = None, sent_at: Optional[Union[int, float]] = None,
            received_at: Optional[Union[int, float]] = None, pending_at: Optional[Union[int, float]] = None,
            finished_at: Optional[Union[int, float]] = None, not_before_at: Optional[Union[int, float]] = None,
            not_after_at: Optional[Union[int, float]] = None, history: Optional[List[dict]] = None,
            uploadable: Optional[bool] = None, load_source: Optional[str] = None) -> DeviceCommand:
        """
        Add a new role to the system.

        To track how the role was created, either request_by and request_by_type or an authentication item
        can be anything with the authmixin, such as a user, websession, or authkey.

        :param device: Device instance, device id, or device machine label.
        :param command: Command instance, command id, or command machine label.
        :param gateway_id:
        :param inputs:
        :param status:
        :param idempotence:
        :param device_command_id:
        :param authentication: An auth item such as a websession or authkey.
        :param request_by: Who created the device command. "alexamodule"
        :param request_by_type: What type of item created it: "module"
        :param request_context: Some additional information about where the request comes from.
        :param created_at:
        :param broadcast_at:
        :param accepted_at:
        :param sent_at:
        :param received_at:
        :param pending_at:
        :param finished_at:
        :param not_before_at:
        :param not_after_at:
        :param history:
        :param persistent_request_id:
        :param uploadable:
        :param load_source: How the role was loaded.
        :return:
        """
        print(f"devicecommand/init: new: {device}")
        if isinstance(device, Device) is False:
            device = self._Devices.get(device)
        if isinstance(command, Command) is False:
            command = self._Commands.get(command)

        if gateway_id is None:
            gateway_id = self._gateway_id

        if device_command_id is None:
            device_command_id = random_string(length=20)

        if status is None:
            status = DEVICE_COMMAND_STATUS_NEW

        if uploadable is None:
            uploadable = True

        if persistent_request_id is not None:  # cancel any previous device requests for this persistent id.
            for search_request_id, search_device_command in self._Parent._DeviceCommands.device_commands.items():
                if search_device_command.persistent_request_id == persistent_request_id:
                    search_device_command.cancel(message="This device command was superseded by a new persistent request.")

        print("device command, about load into memory..")
        try:
            results = yield self.load_an_item_to_memory(
                {
                    "device": device,
                    "command": command,
                    "persistent_request_id": persistent_request_id,
                    "device_command_id": device_command_id,
                    "gateway_id": gateway_id,
                    "inputs": inputs,
                    "status": status,
                    "idempotence": idempotence,
                    "created_at": created_at,
                    "broadcast_at": broadcast_at,
                    "accepted_at": accepted_at,
                    "sent_at": sent_at,
                    "received_at": received_at,
                    "pending_at": pending_at,
                    "finished_at": finished_at,
                    "not_before_at": not_before_at,
                    "not_after_at": not_after_at,
                    "history": history,
                    "request_context": request_context,
                    "uploadable": uploadable,
                    "uploaded": False,
                    "request_by": authentication.accessor_id,
                    "request_by_type": authentication.accessor_type,
                },
                authentication=authentication,
                load_source=load_source,
                generated_source=caller_string())
            print(f"device command, about load into memory..: {results}")
            yield results.start_device_command()
        except Exception as e:
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!device command, caught : {e}")
            return None
        print("device command, about load into memory..done, now call start_device_command")
        return results

    def set_status(self, device_command_id: str, status: str, message: str,
                   log_at: Optional[Union[int, float]] = None, gateway_id: Optional[str] = None) -> None:
        """
        Update the device command status. This is a helper function that calls the device command instance
        to actually set the status.

        :param device_command_id:
        :param status: A text that is one of: DeviceCommand.STATUS_TEXT
        :param message: Message to set for the status.
        :param log_at: Time (int or float) that the status was set at.
        :param gateway_id: Gateway id of the setting gateway. Usually used by gateway coms.

        :return:
        """
        if device_command_id in self.device_commands:
            self.device_commands[device_command_id].set_status(status=status, message=message, log_at=log_at,
                                                               gateway_id=gateway_id)
            return self.device_commands[device_command_id]
        raise KeyError(f"Cannot find device command id: {device_command_id}")

    def find_device_commands(self,
                             gateway_id: Optional[str] = None,
                             device_id: Optional[str] = None) -> List[DeviceCommand]:
        """
        Gets device commands by _either_ gateway_id or device_id.

        :param gateway_id: Gateway id to search for.
        :param device_id: Device id to search for.
        :return:
        """
        results = []
        if (gateway_id is None and device_id is None) or (gateway_id is not None and device_id is not None):
            raise YomboWarning("find_device_commands must have EITHER gateway_id or device_id, not both or neither.")

        for device_command_id, device_command in self.device_commands.items():
            if gateway_id is not None and device_command.device.gateway_id == gateway_id:
                results.append(device_command.to_dict())
            elif device_id is not None and device_command.device.device_id == device_id:
                results.append(device_command.to_dict())
        return results

    def delayed_commands(self, requested_device_id=None) -> Dict[str, DeviceCommand]:
        """
        Returns only device commands that are delayed.

        :return:
        """
        if requested_device_id is not None:
            requested_device = self.get(requested_device_id)
            return requested_device.delayed_commands()
        else:
            device_commands = {}
            for device_id, device in self.devices.items():
                device_commands.update(device.delayed_commands())
            return device_commands

    @inlineCallbacks
    def wait_for_command_to_finish(self, device_command_id: str, timeout: int = 1) -> bool:
        """
        Simply waits for a command to finish by monitoring the device command request status.

        Typically used to wait for one device command to finish before sending a new one.

        :param device_command_id:
        :param timeout: Max number of seconds to wait before returning false.
        :return: True if command completed successfully within the timeout, otherwise false.
        """
        if device_command_id not in self.device_commands:
            return True
        device_command = self.device_commands[device_command_id]
        waiting = True
        waited_time = 0
        while(waiting):
            status_id = device_command.status_id
            if status_id == 100:
                return True
            if status_id > 100:
                return False
            yield sleep(0.05)
            waited_time += 0.05
            if waited_time > timeout:
                return False

    def get_by_ids(self, device_type_id: str, command_id: str) -> Dict[str, DeviceCommand]:
        """
        Returns a dictionary of device commands by searching through items looking for ones that match the
        device_type_id and command_id.

        :param device_type_id:
        :param command_id:
        :return:
        """
        results = {}
        for device_commnad_id, device_command in self.device_commands.items():
            if device_command.device_type_id == device_type_id and device_command.command_id == command_id:
                results[device_commnad_id] = device_command
        return results
