# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `device type commands @ Library Documentation <https://yombo.net/docs/libraries/device_type_commands>`_

Device type commands provides a mapping between what commands each device type can perform.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/devicetypecommands.html>`_
"""
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.core.log import get_logger
from yombo.mixins.sync_to_everywhere import SyncToEverywhere
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.device_type_commands")


class DeviceTypeCommands(YomboLibrary, LibrarySearchMixin):
    """
    Manages device type commands.
    """
    device_type_commands = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_attribute_name = "device_type_commands"
    _class_storage_fields = [
        "device_type_id", "command_id"
    ]
    _class_storage_sort_key = "device_type_id"

    def __contains__(self, device_type_command_requested):
        """
        Checks if there's any records for a given device type id - and if it has records.

            >>> if "0kas02j1zss349k1" in self._DeviceTypeCommands =:

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param device_type_command_requested: The device type command id or machine_label to search for.
        :type device_type_command_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            if len(self.get(device_type_command_requested)) > 0:
                return True
        except:
            pass
        return False

    def __getitem__(self, device_type_command_requested):
        """
        Gets all commands for a provided device type id.

            >>> device_type_command = self._DeviceTypeCommands =["0kas02j1zss349k1"]  # by id

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param device_type_command_requested: The device type command ID or machine_label to search for.
        :type device_type_command_requested: string
        :return: A pointer to the device type command instance.
        :rtype: instance
        """
        return self.get(device_type_command_requested)

    def __setitem__(self, **kwargs):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, **kwargs):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter device type commands. """
        return self.device_type_commands.__iter__()

    def __len__(self):
        """
        Returns an int of the number of device type commands configured.

        :return: The number of device type commands configured.
        :rtype: int
        """
        return len(self.device_type_commands)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo device type commands library"

    def keys(self):
        """
        Returns the keys (device type command ID's) that are configured.

        :return: A list of device type command IDs.
        :rtype: list
        """
        return list(self.device_type_commands.keys())

    def items(self):
        """
        Gets a list of tuples representing the device type commands configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.device_type_commands.items())

    def values(self):
        return list(self.device_type_commands.values())

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self._started = False
        yield self._load_device_type_commands_from_database()

    def _start_(self, **kwargs):
        self._started = True

    @inlineCallbacks
    def _load_device_type_commands_from_database(self):
        """
        Loads device type commands from database and sends them to
        :py:meth:`_load_device_type_commands_into_memory <DeviceCommandInputs._load_device_type_commands_into_memory>`

        This can be triggered either on system startup or when new/updated device_type_command have been saved to the
        database and we need to refresh existing items.
        """
        device_type_commands = yield self._LocalDB.get_device_type_commands()
        for item in device_type_commands:
            self._load_device_type_commands_into_memory(item.__dict__, "database")

    def _load_device_type_commands_into_memory(self, device_type_command, source=None):
        """
        Add a new device type commands to memory or update an existing.

        **Hooks called**:

        * _device_type_command_before_import_ : When this function starts.
        * _device_type_command_imported_ : When this function finishes.
        * _device_type_command_before_load_ : If added, sends DTC dictionary as "device_type_command"
        * _device_type_command_before_update_ : If updated, sends DTC dictionary as "device_type_command"
        * _device_type_command_loaded_ : If added, send the DTC instance as "device_type_command"
        * _device_type_command_updated_ : If updated, send the DTC instance as "device_type_command"

        :param device_type_command: A dictionary of items required to either setup a new device_type_command or update
          an existing one.
        :type device_type_command: dict
        """

        device_type_command_id = device_type_command["id"]
        # Stop here if not in run mode.
        if self._started is True:
            global_invoke_all("_device_type_command_before_import_",
                              called_by=self,
                              device_type_command_id=device_type_command_id,
                              device_type_command=device_type_command,
                              )
        if device_type_command_id not in self.device_type_commands:
            if self._started is True:
                global_invoke_all("_device_type_command_before_load_",
                                  called_by=self,
                                  device_type_command_id=device_type_command_id,
                                  device_type_command=device_type_command,
                                  )
            self.device_type_commands[device_type_command_id] = DeviceCommandInput(self,
                                                                                   device_type_command,
                                                                                   source=source)
            if self._started is True:
                global_invoke_all("_device_type_command_loaded_",
                                  called_by=self,
                                  device_type_command_id=device_type_command_id,
                                  device_type_command=self.device_type_commands[device_type_command_id],
                                  )

        else:
            if self._started is True:
                global_invoke_all("_device_type_command_before_update_",
                                  called_by=self,
                                  device_type_command_id=device_type_command_id,
                                  device_type_command=self.device_type_commands[device_type_command_id],
                                  )
            self.device_type_commands[device_type_command_id].update_attributes(device_type_command, source=source)
            if self._started is True:
                global_invoke_all("_device_type_command_updated_",
                                  called_by=self,
                                  device_type_command_id=device_type_command_id,
                                  device_type_command=self.device_type_commands[device_type_command_id],
                                  )
        if self._started is True:
            global_invoke_all("_device_type_command_imported_",
                              called_by=self,
                              device_type_command_id=device_type_command_id,
                              device_type_command=self.device_type_commands[device_type_command_id],
                              )
        return self.device_type_commands[device_type_command_id]

    def get(self, device_type_id):
        """
        Returns a dictionary of commands the specified device type can send.

        :param device_type_id:
        :return:
        """
        results = {}
        for item_id, dtc in self.device_type_commands.items():
            if dtc.device_type_id == device_type_id:
                try:
                    command = self._Commands.get(dtc.command_id)
                    if command.command_id not in results:
                        results[command.command_id] = []
                    results[command.command_id].append(command)
                except:
                    logger.warning("Error getting command '{command_id}' for a device type.",
                                   command_id=dtc.command_id)
                    pass
        return results

    def get_by_command_id(self, command_id):
        """
        Returns a dictionary of device types a specified command id belongs to.

        :param command_id:
        :return:
        """
        results = {}
        for item_id, dtc in self.device_type_commands.items():
            if dtc.command_id == command_id:
                try:
                    device_type = self._DeviceTypes.get(dtc.device_type_id)
                    if device_type.device_type_id not in results:
                        results[device_type.device_type_id] = []
                    results[device_type.device_type_id].append(device_type)
                except:
                    logger.warning("Error getting command '{command_id}' for a device type.",
                                   command_id=dtc.command_id)
                    pass


        for item_id, dtc in self.device_type_commands.items():
            if dtc.command_id == command_id:
                results[item_id] = dtc
        return results

    @inlineCallbacks
    def add_device_type_command(self, data, **kwargs):
        """
        Add a device type command at the Yombo server level. We'll also request that the new item be loaded
        into memory.

        :param data:
        :param kwargs:
        :return:
        """
        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            api_results = yield self._YomboAPI.request("POST", "/v1/device_type_commands",
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't add device type command: {e.message}",
                "apimsg": f"Couldn't add device type command: {e.message}",
                "apimsghtml": f"Couldn't add device type command: {e.html_message}",
            }

        data["id"] = api_results["data"]["id"]
        data["updated_at"] = time()
        data["created_at"] = time()
        dtc = self._load_device_type_commands_into_memory(data, source="amqp")

        return {
            "status": "success",
            "msg": "device type command added.",
            "device_type_command_id": api_results["data"]["id"],
        }

    @inlineCallbacks
    def edit_device_type_command(self, device_type_command_id, data, **kwargs):
        """
        Edit the device type command at the Yombo API level as well as the local level.

        :param data:
        :param kwargs:
        :return:
        """
        if data["machine_label"] == "none":
            raise YomboWarning(
                {
                    "title": "Error editing device type command",
                    "detail": "Machine label is missing or was set to 'none'.",
                },
                component="device_type_commands",
                name="edit_device_type_command")

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            api_results = yield self._YomboAPI.request("PATCH", f"/v1/device_type_commands/{device_type_command_id}",
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            raise YomboWarning(
                {
                    "title": "Error editing device type command",
                    "detail": e.message,
                },
                component="device_type_commands",
                name="edit_device_type_command")

        if device_type_command_id in self.device_type_commands:
            self.device_type_commands[device_type_command_id].update_attributes(data,
                                                                                source="amqp",
                                                                                session=session)  # Simulate AMQP

        global_invoke_all("_device_type_command_updated_",
                          called_by=self,
                          device_type_command_id=device_type_command_id,
                          device_type_command=self.device_type_commands[device_type_command_id],
                          )

        return {
            "status": "success",
            "msg": "Device type edited.",
            "device_type_command_id": api_results["data"]["id"],
        }

    @inlineCallbacks
    def delete_device_type_command(self, device_type_command_id, **kwargs):
        """
        Delete a device type command at the Yombo server level, not at the local gateway level.

        :param device_type_command_id: The device type command ID to delete.
        :param kwargs:
        :return:
        """
        device_type_command = self.get(device_type_command_id)
        if device_type_command["machine_label"] == "none":
            raise YomboWarning(
                {
                    "title": "Error deleting device type command",
                    "detail": "Machine label is missing or was set to 'none'.",
                },
                component="device_type_commands",
                name="delete_device_type_command")

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            yield self._YomboAPI.request("DELETE", f"/v1/device_type_commands/{device_type_command.device_type_command_id}",
                                         session=session)
        except YomboWarning as e:
            raise YomboWarning(
                {
                    "title": "Error deleting device type command",
                    "detail": e.message,
                },
                component="device_type_commands",
                name="delete_device_type_command")

        if device_type_command_id in self.device_type_commands:
            del self.device_type_commands[device_type_command_id]

        global_invoke_all("_device_type_command_deleted_",
                          called_by=self,
                          device_type_command_id=device_type_command_id,
                          device_type_command=self.device_type_commands[device_type_command_id],
                          )

        self._LocalDB.delete_device_type_commands(device_type_command)
        return {
            "status": "success",
            "msg": "Location deleted.",
            "device_type_command_id": device_type_command_id,
        }


class DeviceCommandInput(Entity, SyncToEverywhere):
    """
    A class to manage a single device type command.
    """

    def __init__(self, parent, device_type_command, source=None):
        """
        Setup the device type command object using information passed in.

        :param device_type_command: An device type command with all required items to create the class.
        :type device_type_command: dict
        """
        self._internal_label = "device_type_commands"  # Used by mixins
        super().__init__(parent)

        #: str: ID for the device_type_command.
        self.device_type_command_id = device_type_command["id"]

        # below are configured in update_attributes()
        self.device_type_id = None
        self.device_type_id = None
        self.created_at = None
        self.update_attributes(device_type_command, source=source)
        self.start_data_sync()

    def __str__(self):
        """
        Print a string when printing the class.  This will return the device type command id so that
        the device type command can be identified and referenced easily.
        """
        return self.machine_label
