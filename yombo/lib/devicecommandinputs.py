# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Device Command Inputs @ Library Documentation <https://yombo.net/docs/libraries/device_command_inputs>`_

Stores device command inputs in memory. Used by device types to determine what inputs are needed or accepted for
various commands.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/devicecommandinputs.html>`_
"""
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.library_search import LibrarySearch
from yombo.core.log import get_logger
from yombo.mixins.yombobasemixin import YomboBaseMixin
from yombo.mixins.synctoeverywhere import SyncToEverywhere
from yombo.utils import global_invoke_all

logger = get_logger("library.device_command_inputs")


class DeviceCommandInputs(YomboLibrary, LibrarySearch):
    """
    Manages device type command inputs.
    """
    device_command_inputs = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    item_search_attribute = "device_command_inputs"
    item_searchable_attributes = [
        "device_type_id", "label", "machine_label", "command_id", "input_type_id", "machine_label", "label",
        "live_update", "value_required", "encryption"
    ]
    item_sort_key = "machine_label"

    def __contains__(self, device_command_input_requested):
        """
        Checks to if a provided device command input ID or machine_label exists.

            >>> if "0kas02j1zss349k1" in self._DeviceCommandInputs =:
            >>> if "area:0kas02j1zss349k1" in self._DeviceCommandInputs =:

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param device_command_input_requested: The device command input id or machine_label to search for.
        :type device_command_input_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(device_command_input_requested)
            return True
        except:
            return False

    def __getitem__(self, device_command_input_requested):
        """
        Attempts to find the device command input requested using a couple of methods.

            >>> device_command_input = self._DeviceCommandInputs =["0kas02j1zss349k1"]  # by id

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param device_command_input_requested: The device command input ID or machine_label to search for.
        :type device_command_input_requested: string
        :return: A pointer to the device command input instance.
        :rtype: instance
        """
        return self.get(device_command_input_requested)

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
        """ iter device command inputs. """
        return self.device_command_inputs.__iter__()

    def __len__(self):
        """
        Returns an int of the number of device command inputs configured.

        :return: The number of device command inputs configured.
        :rtype: int
        """
        return len(self.device_command_inputs)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo device command inputs library"

    def keys(self):
        """
        Returns the keys (device command input ID's) that are configured.

        :return: A list of device command input IDs.
        :rtype: list
        """
        return list(self.device_command_inputs.keys())

    def items(self):
        """
        Gets a list of tuples representing the device command inputs configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.device_command_inputs.items())

    def values(self):
        return list(self.device_command_inputs.values())

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self._started = False
        yield self._load_device_command_inputs_from_database()

    def _start_(self, **kwargs):
        self._started = True

    @inlineCallbacks
    def _load_device_command_inputs_from_database(self):
        """
        Loads device command inputs from database and sends them to
        :py:meth:`_load_device_command_inputs_into_memory <DeviceCommandInputs._load_device_command_inputs_into_memory>`

        This can be triggered either on system startup or when new/updated device_command_input have been saved to the
        database and we need to refresh existing items.
        """
        device_command_inputs = yield self._LocalDB.get_device_command_inputs()
        for item in device_command_inputs:
            self._load_device_command_inputs_into_memory(item.__dict__, "database")

    def _load_device_command_inputs_into_memory(self, device_command_input, source=None):
        """
        Add a new device command inputs to memory or update an existing.

        **Hooks called**:

        * _device_command_input_before_import_ : When this function starts.
        * _device_command_input_imported_ : When this function finishes.
        * _device_command_input_before_load_ : If added, sends DCI dictionary as "device_command_input"
        * _device_command_input_before_update_ : If updated, sends DCI dictionary as "device_command_input"
        * _device_command_input_loaded_ : If added, send the DCI instance as "device_command_input"
        * _device_command_input_updated_ : If updated, send the DCI instance as "device_command_input"

        :param device_command_input: A dictionary of items required to either setup a new device_command_input or
          update an existing one.
        :type device_command_input: dict
        """

        device_command_input_id = device_command_input["id"]
        # Stop here if not in run mode.
        if self._started is True:
            global_invoke_all("_device_command_input_before_import_",
                              called_by=self,
                              device_command_input_id=device_command_input_id,
                              device_command_input=device_command_input,
                              )
        if device_command_input_id not in self.device_command_inputs:
            if self._started is True:
                global_invoke_all("_device_command_input_before_load_",
                                  called_by=self,
                                  device_command_input_id=device_command_input_id,
                                  device_command_input=device_command_input,
                                  )
            self.device_command_inputs[device_command_input_id] = DeviceCommandInput(self,
                                                                                     device_command_input,
                                                                                     source=source)
            if self._started is True:
                global_invoke_all("_device_command_input_loaded_",
                                  called_by=self,
                                  device_command_input_id=device_command_input_id,
                                  device_command_input=self.device_command_inputs[device_command_input_id],
                                  )

        elif device_command_input_id not in self.device_command_inputs:
            if self._started is True:
                global_invoke_all("_device_command_input_before_update_",
                                  called_by=self,
                                  device_command_input_id=device_command_input_id,
                                  device_command_input=self.device_command_inputs[device_command_input_id],
                                  )
            self.device_command_inputs[device_command_input_id].update_attributes(device_command_input, source=source)
            if self._started is True:
                global_invoke_all("_device_command_input_updated_",
                                  called_by=self,
                                  device_command_input_id=device_command_input_id,
                                  device_command_input=self.device_command_inputs[device_command_input_id],
                                  )
        if self._started is True:
            global_invoke_all("_device_command_input_imported_",
                              called_by=self,
                              device_command_input_id=device_command_input_id,
                              device_command_input=self.device_command_inputs[device_command_input_id],
                              )
        return self.device_command_inputs[device_command_input_id]

    def get_by_ids(self, device_type_id, command_id):
        """
        Returns a dictionary of device command inputs by searching through items looking for ones that match the
        device_type_id and command_id.

        :param device_type_id:
        :param command_id:
        :return:
        """
        results = {}
        for item_id, dci in self.device_command_inputs.items():
            if dci.device_type_id == device_type_id and dci.command_id == command_id:
                results[item_id] = dci
        return results

    @inlineCallbacks
    def add_device_command_input(self, data, **kwargs):
        """
        Add a device command input at the Yombo server level. We'll also request that the new item be loaded
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

            api_results = yield self._YomboAPI.request("POST", "/v1/device_command_inputs",
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't add device command input: {e.message}",
                "apimsg": f"Couldn't add device command input: {e.message}",
                "apimsghtml": f"Couldn't add device command input: {e.html_message}",
            }

        data["id"] = api_results["data"]["id"]
        data["updated_at"] = time()
        data["created_at"] = time()
        dci = self._load_device_command_inputs_into_memory(data, source="amqp")

        global_invoke_all("_device_command_input_added_",
                          called_by=self,
                          device_command_input_id=dci.device_type_command_id,
                          device_command_input=dci,
                          )

        return {
            "status": "success",
            "msg": "Device command input added.",
            "device_command_input_id": api_results["data"]["id"],
        }

    @inlineCallbacks
    def edit_device_command_input(self, device_command_input_id, data, **kwargs):
        """
        Edit the device command input at the Yombo API level as well as the local level.

        :param device_command_input_id:
        :param data:
        :return:
        """
        if data["machine_label"] == "none":
            raise YomboWarning(
                {
                    "title": "Error editing device command input",
                    "detail": "Machine label is missing or was set to 'none'.",
                },
                component="device_command_inputs",
                name="edit_device_command_input")

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            api_results = yield self._YomboAPI.request("PATCH", f"/v1/device_command_inputs/{device_command_input_id}",
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            raise YomboWarning(
                {
                    "title": "Error editing device command input",
                    "detail": e.message,
                },
                component="device_command_inputs",
                name="edit_device_command_input")

        if device_command_input_id in self.device_command_inputs:
            self.device_command_inputs[device_command_input_id].update_attributes(data,
                                                                                  source="amqp",
                                                                                  session=session)  # Simulate AMQP

        return {
            "status": "success",
            "msg": "Device type edited.",
            "device_command_input_id": api_results["data"]["id"],
        }

    @inlineCallbacks
    def delete_device_command_input(self, device_command_input_id, **kwargs):
        """
        Delete a device command input at the Yombo server level, not at the local gateway level.

        :param device_command_input_id: The device command input ID to delete.
        :param kwargs:
        :return:
        """
        device_command_input = self.get(device_command_input_id)
        if device_command_input["machine_label"] == "none":
            raise YomboWarning(
                {
                    "title": "Error deleting device command input",
                    "detail": "Machine label is missing or was set to 'none'.",
                },
                component="device_command_inputs",
                name="delete_device_command_input")

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            yield self._YomboAPI.request("DELETE", f"/v1/device_command_inputs/{device_command_input.device_command_input_id}",
                                         session=session)
        except YomboWarning as e:
            raise YomboWarning(
                {
                    "title": "Error deleting device command input",
                    "detail": e.message,
                },
                component="device_command_inputs",
                name="delete_device_command_input")

        if device_command_input_id in self.device_command_inputs:
            del self.device_command_inputs[device_command_input_id]

        global_invoke_all("_device_command_inputs_deleted_",
                          called_by=self,
                          device_command_input_id=device_command_input_id,
                          device_command_input=self.device_command_inputs[device_command_input_id],
                          )

        self._LocalDB.delete_device_command_inputs(device_command_input)
        return {
            "status": "success",
            "msg": "Location deleted.",
            "device_command_input_id": device_command_input_id,
        }


class DeviceCommandInput(YomboBaseMixin, SyncToEverywhere):
    """
    A class to manage a single device command input.
    """

    def __init__(self, parent, device_command_input, source=None):
        """
        Setup the device command input object using information passed in.

        :param device_command_input: An device command input with all required items to create the class.
        :type device_command_input: dict
        """
        self._internal_label = "device_command_inputs"  # Used by mixins
        super().__init__(parent)

        #: str: ID for the device_command_input.
        self.device_command_input_id = device_command_input["id"]

        # below are configured in update_attributes()
        self.device_type_id = None
        self.command_id = None
        self.input_type_id = None
        self.machine_label = None
        self.label = None
        self.live_update = None
        self.value_required = None
        self.value_max = None
        self.value_min = None
        self.value_casing = None
        self.encryption = None
        self.notes = None
        self.updated_at = None
        self.created_at = None
        self.update_attributes(device_command_input, source=source)
        self.start_data_sync()

    def __str__(self):
        """
        Print a string when printing the class.  This will return the device command input id so that
        the device command input can be identified and referenced easily.
        """
        return self.machine_label
