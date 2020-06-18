# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Device States @ Library Documentation <https://yombo.net/docs/libraries/device_states>`_

Manages device states.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devicestates/__init__.html>`_
"""
from copy import copy
from decimal import Decimal
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union
import weakref

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants.device_states import DEVICESTATE_ID_LENGTH
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import DeviceStateSchema
from yombo.lib.commands import Command
from yombo.lib.devices.device import Device
from yombo.lib.devicecommands import DeviceCommand
from yombo.mixins.auth_mixin import AuthMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.utils.caller import caller_string
from yombo.utils.decorators import cached
from .device_state import DeviceState

logger = get_logger("library.device_commands")


class DeviceStates(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Stores and track device states.
    """
    device_states: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "device_state_id"

    _storage_attribute_name: ClassVar[str] = "device_states"
    _storage_label_name: ClassVar[str] = "device_state"
    _storage_class_reference: ClassVar = DeviceState
    _storage_schema: ClassVar = DeviceStateSchema()
    _storage_pickled_fields: ClassVar[Dict[str, str]] = {"machine_state_extra": "msgpack"}
    _storage_search_fields: ClassVar[List[str]] = [
        "device_state_id", "device_id", "command_id", "device_command_id", "request_context",
        "reporting_source", "uploaded", "uploadable"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "created_at"
    _storage_attribute_sort_key_order: ClassVar[str] = "desc"

    def _init_(self, **kwargs) -> None:
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.clean_device_state_loop = None

        load_history_depth = self._Configs.get("devices.load_history_depth", 30)
        for device_id, device in self._Devices.devices.items():
            items = yield self.load_from_database(
                return_data=True,
                db_args={"where": {"created_at": [time() - 60*60*24*180, ">"],
                                   "device_id": device_id},
                         "limit": load_history_depth,
                         }
            )
            # print(f"devices states starting - for device {device.label} - {items}")
            yield self.load_db_items_to_memory(items, load_source="database")

    def load_an_item_to_memory_pre_process(self, incoming: dict, **kwargs) -> None:
        """
        Receive the item before being loading to memory.

        Lets make that the target device is still around, otherwise, discard the device command.

        :param incoming: A dict of data to store.
        :param kwargs:
        :return:
        """
        if "device" in incoming:
            device_id = incoming["device"].device_id
        else:
            device_id = incoming["device_id"]
        if device_id not in self._Devices.devices:
            raise YomboWarning(f"Seems a device id we were tracking is gone..{incoming['device_id']}")

    def load_an_item_to_memory_post_process(self, instance: DeviceState) -> None:
        """
        Used to create a weakref to the local device.state_history. This allows each device to keep it's state
        history, but at the same time, that list will be cleaned up if the primary reference has been removed.

        :param instance: device state instance
        :return:
        """
        instance.device.state_history.appendleft(weakref.proxy(instance))
        f = weakref.finalize(instance, self.remove_weakref_state_history, copy(instance.device_id), copy(instance.device_state_id))
        f.atexit = False

    def remove_weakref_state_history(self, device_id: str, device_state_id: str) -> None:
        """
        This is called buy the weakref module when the primary reference has been removed. This removes
        the reference within the device instance.

        :param device_id:
        :param device_state_id:
        :return:
        """
        device = self._Devices[device_id]

        for i, obj in enumerate(device.state_history):
            try:
                if obj.device_state_id == device_state_id:
                    del device.state_history[i]
            except ReferenceError:
                del device.state_history[i]

    def mqtt_incoming(self, topic, payload, qos, retain) -> None:
        pass

    @inlineCallbacks
    def new(self, device: Union[str, Device], command: Union[str, Command],
            machine_state: Any, machine_state_extra: Optional[dict] = None,
            device_command: Union[str, DeviceCommand] = None, created_at: Optional[Union[int, float]] = None,
            energy_usage: Optional[str] = None, energy_type: Optional[str] = None,
            human_state: Optional[str] = None, human_message: Optional[str] = None,
            gateway_id: Optional[str] = None, reporting_source: Optional[str] = None,
            request_by: Optional[str] = None, request_by_type: Optional[str] = None,
            request_context: Optional[str] = None,
            authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None,
            uploaded: Optional[bool] = None, uploadable: Optional[bool] = None,
            _fake_data: Optional[bool] = None, load_source: Optional[str] = None,
            device_state_id: Optional[str] = None) -> DeviceState:
        """
        Create a new device state.

        To track how the device state was created, either request_by and request_by_type or an authentication item
        can be anything with the authmixin, such as a user, websession, or authkey.

        :param device:
        :param command:
        :param device_command:
        :param created_at:
        :param energy_usage:
        :param energy_type:
        :param human_state:
        :param human_message:
        :param machine_state:
        :param machine_state_extra:
        :param gateway_id:
        :param reporting_source: Which module or library is reporting this state.
        :param request_by: Who created the Authkey. "alexamodule"
        :param request_by_type: What type of item created it: "module"
        :param request_context: Some additional information about where the request comes from.
        :param authentication: An auth item such as a websession or authkey.
        :param uploaded:
        :param uploadable:
        :param _fake_data:
        :param load_source: How the authkey was loaded.
        :param device_state_id: Device state id to use, not normally set.
        :return:
        """
        if device_state_id is not None:
            try:
                found = self.get_advanced({"device_state_id": device_state_id}, multiple=False)
                raise YomboWarning(f"Found a matching device_state_id: {found.machine_label} - {found.label}")
            except KeyError:
                pass

        if device_command is not None:
            if isinstance(device_command, DeviceCommand) is False:
                device_command = self._DeviceCommands.get(device_command)

        try:
            request_by, request_by_type = self._Permissions.request_by_info(
                authentication, request_by, request_by_type, device_command)
        except YomboWarning:
            logger.warn("Device states accepted a state without any authentication information.")
        if request_context is None:
            request_context = caller_string()  # get the module/class/function name of caller

        if isinstance(machine_state, float):
            machine_state = Decimal(machine_state)
        # print({
        #         "id": device_state_id,
        #         "device": device,
        #         "command": command,
        #         "device_command": device_command,
        #         "energy_usage": energy_usage,
        #         "energy_type": energy_type,
        #         "human_state": human_state,
        #         "human_message": human_message,
        #         "machine_state": machine_state,
        #         "machine_state_extra": machine_state_extra,
        #         "gateway_id": gateway_id,
        #         "reporting_source": reporting_source,
        #         "uploaded": uploaded,
        #         "uploadable": uploadable,
        #         "request_by": request_by,
        #         "request_by_type": request_by_type,
        #         "request_context": request_context,
        #         "created_at": created_at,
        #         "_fake_data": _fake_data,
        #     })

        results = yield self.load_an_item_to_memory(
            {
                "id": device_state_id,
                "device": device,
                "command": command,
                "machine_state": machine_state,
                "machine_state_extra": machine_state_extra,
                "human_state": human_state,
                "human_message": human_message,
                "device_command": device_command,
                "energy_usage": energy_usage,
                "energy_type": energy_type,
                "gateway_id": gateway_id,
                "reporting_source": reporting_source,
                "uploaded": uploaded,
                "uploadable": uploadable,
                "request_by": request_by,
                "request_by_type": request_by_type,
                "request_context": request_context,
                "created_at": created_at,
                "_fake_data": _fake_data,
            },
            load_source=load_source)
        return results

    @cached(1)  # memoize for 5 seconds
    def state(self, device_id):
        """
        Returns a list of device states for a given device, but only those loaded in memory.

        :param device_id:
        :return:
        """
        results = []
        for device_state_id, device_state in self.device_states.items():
            if device_state.device_id == device_id:
                results.append(device_state)
        return results
