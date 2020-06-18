# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_


The device state class manages a single state entry for a device.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devicestates/device_state.html>`_
"""
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin

logger = get_logger("library.devices.device")


class DeviceState(Entity, LibraryDBChildMixin):
    """
    The device state class represents a single state data point for a device.
    """
    _Entity_type: ClassVar[str] = "Device state"
    _Entity_label_attribute: ClassVar[str] = "device_state_id"

    _sync_to_api: ClassVar[bool] = False
    _sync_to_db: ClassVar[bool] = True

    command: Type["yombo.lib.commands.Command"] = None
    device: Type["yombo.lib.devices.device.Device"] = None
    device_command: Type["yombo.lib.devicecommand.devicecommand.DeviceCommand"] = None
    device_state_id: str = None
    human_state: str = False
    request_context: str = None
    reporting_source: str = None
    created_at: Union[int, float] = None

    # reporting_source: str = False

    def __str__(self):
        """
        Print a string when printing the class.  This will return the device_id so that
        the device can be identified and referenced easily.
        """
        if self.human_state is None:
            return f"{self.device_state_id}: Unknown"
        return f"{self.device_state_id}: {self.human_state}"

    @property
    def device_id(self) -> Union[str, None]:
        return self.device.device_id

    @property
    def command_id(self) -> Union[str, None]:
        if self.command is None:
            return None
        else:
            print(f"command_id: {self.command}")
            return self.command.command_id

    @property
    def device_command_id(self) -> Union[str, None]:
        if self.device_command is None:
            return None
        else:
            return self.device_command.device_command_id

    def load_attribute_values_pre_process(self, incoming: Dict[str, Any]) -> None:
        """ Setup basic class attributes based on incoming data. """
        if incoming["request_by"] is None or incoming["request_by_type"] is None:
            raise YomboWarning("New device state must have either request_by and request_by_type.")

        search_dict = {}
        if "id" in incoming:
            search_dict["id"] = incoming["id"]
        elif "device_state_id" in incoming:
            search_dict["device_state_id"] = incoming["device_state_id"]
        try:
            found = self._Parent.get_advanced(search_dict, multiple=False)
            raise YomboWarning(f"Found a matching device state: {found.device_state_id} - {found.device.label}")
        except KeyError:
            pass

        self.__dict__["device_command"] = None
        if "device_command_id" in incoming and incoming["device_command_id"] is not None:
            try:
                self.__dict__["device_command"] = self._DeviceCommands.get(incoming["device_command_id"])
            except:
                pass

        if "device_command_id" in incoming and incoming["device_command_id"] is not None:
            self.__dict__["device_command"] = incoming["device_command"]

        if self.device_command is not None:
            self.__dict__["device"] = self.device_command.device
            self.__dict__["command"] = self.device_command.command

        if self.device is None:
            try:
                if "device" in incoming and incoming["device"] is not None:
                    self.__dict__["device"] = incoming["device"]
                    del incoming["device"]
                elif "device_id" in incoming and incoming["device_id"] is not None:
                    self.__dict__["device"] = self._Devices.get(incoming["device_id"])
                    del incoming["device_id"]
                else:
                    raise YomboWarning("Device state must have either a device instance or device_id.")
            except:
                raise YomboWarning("Device state is unable to find a device or device_id that is valid..")

        if self.device is None:
            try:
                if "command" in incoming and incoming["command"] is not None:
                    self.__dict__["command"] = incoming["command"]
                    del incoming["command"]
                elif "command_id" in incoming and incoming["command_id"] is not None:
                    self.__dict__["command"] = self._Commands.get(incoming["command_id"])
                    del incoming["command_id"]
                else:
                    self.__dict__["command"] = None
            except:
                raise YomboWarning("Device state is unable to find a matching command or command_id that is valid.")

        if "created_at" not in incoming or incoming["created_at"] is None:
            incoming["created_at"] = time()

    def update_attributes_post_process(self, incoming: Dict[str, Any]):
        """
        Sets various values from an incoming dictionary. This can be called when either new or
        when updating.

        :param incoming:
        :return:
        """
        if "command" in incoming:
            try:
                incoming["command"] = self._Parent._Commands[incoming["command"]]
            except Exception:
                pass
        elif "command_id" in incoming:
            try:
                incoming["command"] = self._Parent._Commands[incoming["command_id"]]
                del incoming["command_id"]
            except Exception as E:
                pass

        if "device_command" in incoming:
            try:
                incoming["device_command"] = self._DeviceCommands.get(incoming["device_command"])
            except Exception:
                pass
        elif "device_command_id" in incoming:
            try:
                incoming["device_command"] = self._Parent._DeviceCommands[incoming["device_command_id"]]
                del incoming["device_command_id"]
            except Exception as E:
                pass

