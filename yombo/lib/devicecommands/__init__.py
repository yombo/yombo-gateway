# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Device Commands @ Library Documentation <https://yombo.net/docs/libraries/device_commands>`_

Stores commands that have been sent to device - device commands. This is not to be confused with all possible commands
for a device, that is stored in device type commands.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/devicecommands.html>`_
"""
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.library_search import LibrarySearch
from yombo.core.log import get_logger
from yombo.utils import global_invoke_all, sleep

from .device_command import Device_Command

logger = get_logger("library.device_commands")


class DeviceCommands(YomboLibrary, LibrarySearch):
    """
    Stores and track commands sent to devices. This also tracks across gateways within the cluster.
    """
    device_commands = {}  # tracks commands being sent to devices. Also tracks if a command is delayed.

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    item_search_attribute = "device_commands"
    item_searchable_attributes = [
        "device_type_id", "label", "machine_label", "command_id", "input_type_id", "machine_label", "label",
        "live_update", "value_required", "encryption"
    ]
    item_sort_key = "machine_label"

    def __contains__(self, device_command_requested):
        """
        Checks to if a provided device command ID or machine_label exists.

            >>> if "0kas02j1zss349k1" in self._DeviceCommandInputs =:
            >>> if "area:0kas02j1zss349k1" in self._DeviceCommandInputs =:

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param device_command_requested: The device command id or machine_label to search for.
        :type device_command_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(device_command_requested)
            return True
        except:
            return False

    def __getitem__(self, device_command_requested):
        """
        Attempts to find the device command requested using a couple of methods.

            >>> device_command = self._DeviceCommandInputs =["0kas02j1zss349k1"]  # by id
            >>> device_command = self._DeviceCommandInputs =["area:0kas02j1zss349k1"]  # include device command type

        or:

            >>> device_command = self._DeviceCommandInputs =["alpnum"]  #by name

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param device_command_requested: The device command ID or machine_label to search for.
        :type device_command_requested: string
        :return: A pointer to the device command instance.
        :rtype: instance
        """
        return self.get(device_command_requested)

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
        """ iter device commands. """
        return self.device_commands.__iter__()

    def __len__(self):
        """
        Returns an int of the number of device commands configured.

        :return: The number of device commands configured.
        :rtype: int
        """
        return len(self.device_commands)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo device commands library"

    def keys(self):
        """
        Returns the keys (device command ID's) that are configured.

        :return: A list of device command IDs.
        :rtype: list
        """
        return list(self.device_commands.keys())

    def items(self):
        """
        Gets a list of tuples representing the device commands configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.device_commands.items())

    def values(self):
        return list(self.device_commands.values())

    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self._started = False
        self.mqtt = None
        self.startup_queue = {}  # Place device commands here until we are ready to process device commands

        # used to store delayed queue for restarts. It'll be a bare, dehydrated version.
        # store the above, but after hydration.
          # the automation system can always request the same command to be performed but ensure only one is
          # is n the queue between restarts.
        self.clean_device_commands_loop = None

    @inlineCallbacks
    def _start_(self, **kwags):
        """
        Loads the device commands from the database.

        :param kwags:
        :return:
        """
        yield self._load_device_commands_from_database()
        self._started = True

    def _started_(self, **kwargs):
        """
        Sets up the looping call to cleanup device commands. Also, subscribes to
        MQTT topics for IoT interactions.

        :return:
        """
        if self._Loader.operating_mode == "run":
            self.mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming,
                                       client_id=f"Yombo-devices-commands-{self.gateway_id}")
            self.mqtt.subscribe("yombo/devices/+/cmd")

    def _unload_(self, **kwargs):
        """
        Save any device commands that need to be saved.

        :return:
        """
        for request_id, device_command in self.device_commands.items():
            device_command.flush_sync()

    def _modules_started_(self, **kwargs):
        """
        Tells any applicable device commands to fire.

        :param kwargs:
        :return:
        """
        for request_id, device_command in self.device_commands.items():
            device_command.start()

    def _modules_prestarted_(self, **kwargs):
        """
        On start, sends all queued messages. Then, check delayed messages for any messages that were missed. Send
        old messages and prepare future messages to run.
        """
        self.processing_commands = True
        for command, request in self.startup_queue.items():
            self.command(request["device_id"],
                         request["command_id"],
                         not_before=request["not_before"],
                         max_delay=request["max_delay"],
                         **request["kwargs"])
        self.startup_queue.clear()

    @inlineCallbacks
    def _load_device_commands_from_database(self):
        """
        Actually loads the device commands from the database.
        :return:
        """
        where = {
            "created_at": [time() - 60*60*24, ">"],
        }
        device_commands = yield self._LocalDB.get_device_commands(where)
        for device_command in device_commands:
            self._load_device_commands_into_memory(device_command.__dict__)

    def _load_device_commands_into_memory(self, device_command):
        """
        Add a new device commands to memory or update an existing.

        **Hooks called**:

        * _device_command_before_import_ : When this function starts.
        * _device_command_imported_ : When this function finishes.
        * _device_command_before_load_ : If added, sends DCI dictionary as "device_command"
        * _device_command_before_update_ : If updated, sends DCI dictionary as "device_command"
        * _device_command_loaded_ : If added, send the DCI instance as "device_command"
        * _device_command_updated_ : If updated, send the DCI instance as "device_command"

        :param device_command: A dictionary of items required to either setup a new device_command or update an existing one.
        :type device_command: dict
        """
        if device_command["device_id"] not in self.devices:
            logger.warn("Seems a device id we were tracking is gone..{id}", id=device_command["device_id"])
            return

        device_command_id = device_command["id"]

        # Stop here if not in run mode.
        if self._started is True:
            global_invoke_all("_device_command_before_import_",
                              called_by=self,
                              device_command_id=device_command_id,
                              device_command=device_command,
                              )
        if device_command_id not in self.device_commands:
            if self._started is True:
                global_invoke_all("_device_command_before_load_",
                              called_by=self,
                              device_command_id=device_command_id,
                              device_command=device_command,
                              )
            self.device_commands[device_command_id] = Device_Command(device_command, self, start=False)
            if self._started is True:
                global_invoke_all("_device_command_loaded_",
                              called_by=self,
                              device_command_id=device_command_id,
                              device_command=self.device_commands[device_command_id],
                              )

        elif device_command_id not in self.device_commands:
            if self._started is True:
                global_invoke_all("_device_command_before_update_",
                              called_by=self,
                              device_command_id=device_command_id,
                              device_command=self.device_commands[device_command_id],
                              )
            self.device_commands[device_command_id].update_attributes(device_command)
            if self._started is True:
                global_invoke_all("_device_command_updated_",
                              called_by=self,
                              device_command_id=device_command_id,
                              device_command=self.device_commands[device_command_id],
                              )
        if self._started is True:
            global_invoke_all("_device_command_imported_",
                          called_by=self,
                          device_command_id=device_command_id,
                              device_command=self.device_commands[device_command_id],
                              )

    def mqtt_incoming(self, topic, payload, qos, retain):
        pass

    def add_device_command_by_object(self, input, start=None):
        """
        Simply append a device command object to the list of tracked device commands.

        :param device_command:
        :return:
        """
        device_command = Device_Command(input, self, start)
        self.device_commands[device_command.request_id] = device_command

    def add_device_command(self, device_command):
        """
        Insert a new device command from a dictionary. Usually called by the gateways coms system.

        :param device_command:
        :param called_from_mqtt_coms:
        :return:
        """
        self.device_commands[device_command["request_id"]] = Device_Command(device_command, self, start=True)

    def update_device_command(self, request_id, status, message=None, log_time=None, gateway_id=None):
        """
        Update device command information based on dictionary items. Usually called by the gateway coms systems.

        :param device_command:
        :return:
        """
        if request_id in self.device_commands:
            self.device_commands[request_id].set_state(status, message, log_time, gateway_id)

    def get_gateway_device_commands(self, gateway_id):
        """
        Gets all the device command for a gateway_id.

        :param dest_gateway_id:
        :return:
        """
        results = []
        for device_command_id, device_command in self.device_commands.items():
            if device_command.device.gateway_id == gateway_id:
                results.append(device_command.asdict())
        return results

    def get_device_commands_list(self):
        """
        Get a list of all device commands.

        :return:
        """
        results = []
        for device_command_id, device_command in self.device_commands.items():
            results.append(device_command.asdict())
        return results

    def delayed_commands(self, requested_device_id=None):
        """
        Returns only device commands that are delayed.

        :return:
        """
        if requested_device_id is not None:
            requested_device = self.get(requested_device_id)
            return requested_device.delayed_commands()
        else:
            commands = {}
            for device_id, device in self.devices.items():
                commands.update(device.delayed_commands())
            return commands

    @inlineCallbacks
    def wait_for_command_to_finish(self, request_id, timeout=1):
        """
        Simply waits for a command to finish by monitoring the device command
        request status.

        :param request_id:
        :param timeout:
        :return:
        """
        if request_id not in self.device_commands:
            return True
        device_command = self.device_commands[request_id]
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

    def get_by_ids(self, device_type_id, command_id):
        """
        Returns a dictionary of device commands by searching through items looking for ones that match the
        device_type_id and command_id.

        :param device_type_id:
        :param command_id:
        :return:
        """
        results = {}
        for id, dci in self.device_commands.items():
            if dci.device_type_id == device_type_id and dci.command_id == command_id:
                results[id] = dci
        return results

    @inlineCallbacks
    def add_device_command(self, data, **kwargs):
        """
        Add a device command at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            api_results = yield self._YomboAPI.request("POST", "/v1/device_commands",
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't add device command: {e.message}",
                "apimsg": f"Couldn't add device command: {e.message}",
                "apimsghtml": f"Couldn't add device command: {e.html_message}",
            }

        data["id"] = api_results["data"]["id"]
        data["updated_at"] = time()
        data["created_at"] = time()
        self._load_device_commands_into_memory(data, save=True)

        return {
            "status": "success",
            "msg": "Location type added.",
            "device_command_id": api_results["data"]["id"],
        }

    @inlineCallbacks
    def edit_device_command(self, device_command_id, data, **kwargs):
        """
        Edit a device command at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        if data["machine_label"] == "none":
            raise YomboWarning(
                {
                    "title": "Error editing device command",
                    "detail": "Machine label is missing or was set to 'none'.",
                },
                component="device_commands",
                name="edit_device_command")

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            api_results = yield self._YomboAPI.request("PATCH", f"/v1/device_commands/{device_command_id}",
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            raise YomboWarning(
                {
                    "title": "Error editing device command",
                    "detail": e.message,
                },
                component="device_commands",
                name="edit_device_command")

        if device_command_id in self.device_commands:
            self.device_commands[device_command_id].update_attributes(data)

        global_invoke_all("_device_commands_updated_",
                          called_by=self,
                          device_command_id=device_command_id,
                          device_command=self.device_commands[device_command_id],
                          )

        return {
            "status": "success",
            "msg": "Device type edited.",
            "device_command_id": api_results["data"]["id"],
        }

    @inlineCallbacks
    def delete_device_command(self, device_command_id, **kwargs):
        """
        Delete a device command at the Yombo server level, not at the local gateway level.

        :param device_command_id: The device command ID to delete.
        :param kwargs:
        :return:
        """
        device_command = self.get(device_command_id)
        if device_command["machine_label"] == "none":
            raise YomboWarning(
                {
                    "title": "Error deleting device command",
                    "detail": "Machine label is missing or was set to 'none'.",
                },
                component="device_commands",
                name="delete_device_command")

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            yield self._YomboAPI.request("DELETE", f"/v1/device_commands/{device_command.device_command_id}",
                                         session=session)
        except YomboWarning as e:
            raise YomboWarning(
                {
                    "title": "Error deleting device command",
                    "detail": e.message,
                },
                component="device_commands",
                name="delete_device_command")

        if device_command_id in self.device_commands:
            del self.device_commands[device_command_id]

        global_invoke_all("_device_commands_deleted_",
                          called_by=self,
                          device_command_id=device_command_id,
                          device_command=self.device_commands[device_command_id],
                          )

        self._LocalDB.delete_device_commands(device_command_id)
        return {
            "status": "success",
            "msg": "Location deleted.",
            "device_command_id": device_command_id,
        }
