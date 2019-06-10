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
from yombo.mixins.library_db_model_mixin import LibraryDBModelMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.core.log import get_logger
from yombo.utils import sleep

from .devicecommand import DeviceCommand

logger = get_logger("library.device_commands")


class DeviceCommands(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Stores and track commands sent to devices. This also tracks across gateways within the cluster.
    """
    device_commands = {}  # tracks commands being sent to devices. Also tracks if a command is delayed.

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "device_command"
    _class_storage_load_db_class = DeviceCommand
    _class_storage_attribute_name = "device_commands"
    _class_storage_search_fields = [
        "device_type_id", "command_status_received", "machine_label", "command_id", "input_type_id", "machine_label", "label",
        "live_update", "value_required", "encryption"
    ]
    _class_storage_sort_key = "machine_label"

    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.mqtt = None
        self.startup_queue = {}  # Place device commands here until we are ready to process device commands

        # used to store delayed queue for restarts. It'll be a bare, dehydrated version.
        # store the above, but after hydration.
        self.clean_device_commands_loop = None

    @inlineCallbacks
    def _start_(self, **kwags):
        """
        Loads the device commands from the database.

        :param kwags:
        :return:
        """
        yield self._class_storage_load_from_database(where={"created_at": [time() - 60*60*24, ">"]})

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

    def _modules_prestarted_(self, **kwargs):
        """
        On start, sends all queued messages. Then, check delayed messages for any messages that were missed. Send
        old messages and prepare future messages to run.
        """
        for command, request in self.startup_queue.items():
            self.command(request["device_id"],
                         request["command_id"],
                         not_before=request["not_before"],
                         max_delay=request["max_delay"],
                         **request["kwargs"])
        self.startup_queue.clear()

    def _modules_started_(self, **kwargs):
        """
        Tells any applicable device commands to fire.

        :param kwargs:
        :return:
        """
        for request_id, device_command in self.device_commands.items():
            device_command.start()

    def _class_storage_preprocess_load(self, item, **kwargs):
        """
        Receive the item before being loading to memory.

        Lets make that the target device is still around, otherwise, discard the device command.

        :param item:
        :param kwargs:
        :return:
        """
        if item["device_id"] not in self._Devices.devices:
            raise YomboWarning(f"Seems a device id we were tracking is gone..{devicecommand['device_id']}")

    def mqtt_incoming(self, topic, payload, qos, retain):
        pass

    def add_device_command_from_db(self, input, start=None):
        """
        Add a new device command.

        :param device_command:
        :return:
        """
        return self.add_device_command(input.__dict__, start=start)
        # device_command = DeviceCommand(input, self, start=start)
        # self.device_commands[device_command.request_id] = device_command

    def add_device_command(self, device_command, start=None):
        """
        Insert a new device command from a dictionary. Usually called by the gateways coms system.

        :param device_command:
        :param called_from_mqtt_coms:
        :return:
        """
        return self._class_storage_load_db_items_to_memory(input, start=start)
        # self.device_commands[device_command["request_id"]] = Device_Command(device_command, self, start=True)

    def set_status(self, device_commnad_id, status, message=None, log_time=None, gateway_id=None):
        """
        Update device command information based on dictionary items. Usually called by the gateway coms systems.

        :param device_command:
        :return:
        """
        if device_commnad_id in self.device_commands:
            self.device_commands[device_commnad_id].set_status(status, message, log_time, gateway_id)
            return self.device_commands[device_commnad_id]
        raise KeyError(f"Cannot find device command id: {device_commnad_id}")

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
