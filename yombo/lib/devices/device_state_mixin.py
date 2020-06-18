# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_

Handles device state changes.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devices/device_state_mixin.html>`_
"""
# Import python libraries
from collections import OrderedDict
from copy import copy
from time import time

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants.commands import COMMAND_ON, COMMAND_OFF
from yombo.constants.device_commands import (DEVICE_COMMAND_CALLED_BY, DEVICE_COMMAND_COMMAND,
    DEVICE_COMMAND_COMMAND_ID, DEVICE_COMMAND_DEVICE, DEVICE_COMMAND_DEVICE_COMMAND,
    DEVICE_COMMAND_DEVICE_ID, DEVICE_COMMAND_INPUTS, DEVICE_COMMAND_PIN,
    DEVICE_COMMAND_DEVICE_COMMAND_ID, DEVICE_COMMAND_GATEWAY_ID,
    DEVICE_COMMAND_REPORTING_SOURCE, DEVICE_COMMAND_ENERGY_TYPE, DEVICE_COMMAND_ENERGY_USAGE,
    DEVICE_COMMAND_HUMAN_MESSAGE, DEVICE_COMMAND_HUMAN_STATUS, DEVICE_COMMAND_REQUEST_BY,
    DEVICE_COMMAND_REQUEST_BY_TYPE, DEVICE_COMMAND_REQUEST_CONTEXT)
from yombo.constants.permissions import AUTH_PLATFORM_DEVICE
from yombo.core.exceptions import YomboPinCodeError, YomboWarning
from yombo.core.log import get_logger
from yombo.utils.caller import caller_string
from yombo.utils.dictionaries import recursive_dict_merge, dict_diff
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.devices.device")


class DeviceStateMixin:
    def set_state_process(self, **kwargs):
        """
        A place for modules to process any state updates. Make any last minute changes before it's saved and
        distributed.

        :param kwargs:
        :return:
        """
        logger.debug("device ({label}), set_state_process kwargs: {kwargs}", label=self.full_label, kwargs=kwargs)
        if len(self.state_history) == 0:
            previous_extra = {}
        else:
            previous_extra = self.state_history[0].machine_state_extra

        if isinstance(previous_extra, dict) is False:
            previous_extra = {}

        # filter out previous invalid status extra values.
        # for extra_key in list(previous_extra.keys()):
        #     if extra_key not in self.MACHINE_STATE_EXTRA_FIELDS:
        #         del previous_extra[extra_key]

        new_extra = kwargs.get("machine_state_extra", {})

        # filter out new invalid status extra values.
        for extra_key in list(new_extra.keys()):
            if extra_key not in self.MACHINE_STATE_EXTRA_FIELDS:
                logger.warn(
                    f"For device '{self.full_label}', the machine status extra field '{extra_key}' was removed"
                    f" on status update. This field is not apart of the approved machine status extra fields. "
                    f"Device type: {self.device_type.label}")
                del new_extra[extra_key]

        for key, value in previous_extra.items():
            if key in new_extra:
                continue
            new_extra[key] = value

        kwargs["machine_state_extra"] = new_extra
        return kwargs

    def generate_human_state(self, machine_state, machine_state_extra):
        return machine_state

    def generate_human_message(self, machine_state, machine_state_extra):
        human_state = self.generate_human_state(machine_state, machine_state_extra)
        return f"{self.area_label} is now {human_state}"

    def set_state_machine_extra(self, **kwargs):
        pass

    def command_from_status(self, machine_state, machine_state_extra=None):
        """
        Attempt to find a command based on the status of a device.

        :param machine_state:
        :return:
        """
        # print("attempting to get command_from_status - relay: %s - %s" % (machine_state, machine_state_extra))
        if machine_state == int(1):
            return self._Commands[COMMAND_ON]
        elif machine_state == int(0):
            return self._Commands[COMMAND_OFF]
        return None

    def set_state_delayed(self, delay=None, **kwargs):
        """
        Accepts all the arguments of set_status, but delays submitting to set_status. This
        is used by devices that set several attributes separately, but quickly.

        :param kwargs:
        :return:
        """
        if delay is None:
            delay = 0.1
        if kwargs is None:
            raise ImportError("Must supply status arguments...")

        self.state_delayed = recursive_dict_merge(self.state_delayed, kwargs)
        if DEVICE_COMMAND_REPORTING_SOURCE not in self.state_delayed:
            self.state_delayed[DEVICE_COMMAND_REPORTING_SOURCE] = caller_string(prefix=f"g=self._gateway_id")

        if self.state_delayed_calllater is not None and self.state_delayed_calllater.active():
            self.state_delayed_calllater.cancel()

        self.state_delayed_calllater = reactor.callLater(delay, self.do_set_state_delayed)

    @inlineCallbacks
    def do_set_state_delayed(self):
        """
        Sends the actual delayed state to set_state(). This was called using a callLater function
        from set_state_delayed().

        :return:
        """
        if "machine_state" not in self.state_delayed:
            self.state_delayed["machine_state"] = self.machine_state
        yield self.set_state(**self.state_delayed)
        self.state_delayed.clear()

    @inlineCallbacks
    def set_state(self, **kwargs):
        """
        Usually called by the device's command/logic module to set/update the
        device status. This can also be called externally as needed.

        :raises YomboWarning: Raised when:

            - If no valid status sent in. error_code: 120
            - If statusExtra was set, but not a dictionary. error_code: 121
        :param kwargs: Named arguments:

            - human_state *(int or string)* - The new status.
            - human_message *(string)* - A human friendly text message to display.
            - command *(string)* - Command label from the last command.
            - machine_state *(decimal)* - The new status.
            - machine_state_extra *(dict)* - Extra status as a dictionary.
            - silent *(any)* - If defined, will not broadcast a status update message; atypical.

        """
        self.state_delayed = recursive_dict_merge(self.state_delayed, kwargs)
        if DEVICE_COMMAND_REPORTING_SOURCE not in self.state_delayed:
            self.state_delayed[DEVICE_COMMAND_REPORTING_SOURCE] = caller_string(prefix=f"g=self._gateway_id")

        delayed_args = copy(self.state_delayed)
        self.state_delayed.clear()

        kwargs_delayed = self.set_state_process(**delayed_args)
        try:
            kwargs_delayed, device_state = yield self._set_state(**kwargs_delayed)
        except YomboWarning as e:
            logger.info("{e}", e=e)
            return
        # print(f")_set_state done, got kwargs_delayed: {kwargs_delayed}")
        # print(f")_set_state done, got device_state: {device_state}")
        # print(f"device state as asdict: {device_state.asdict()}")
        # print(f"device state as dict: {device_state.__dict__}")
        # print(f"device state device: {device_state.device}")
        # print(f"device state device_id: {device_state.device_id}")

        if "silent" not in kwargs_delayed and device_state is not None:
            self.send_state(device_state)

        if self.state_delayed_calllater is not None and self.state_delayed_calllater.active():
            self.state_delayed_calllater.cancel()
        return device_state

    @inlineCallbacks
    def _set_state(self, **kwargs):
        """
        A private function used to do the work of setting the state.

        :param kwargs:
        :return:
        """
        if "machine_state" not in kwargs:
            raise YomboWarning("set_status was called without a real machine_state!", error_code=120)
        logger.info("_set_state called...: {kwargs}", kwargs=kwargs)
        machine_state = kwargs["machine_state"]
        machine_state_extra = kwargs.get("machine_state_extra", {})
        kwargs["machine_state_extra"] = machine_state_extra
        if machine_state == self.machine_state:
            if self.machine_state_extra is not None:
                added, removed, modified, same = dict_diff(machine_state_extra, self.machine_state_extra)
                if len(added) == 0 and len(removed) == 0 and len(modified) == 0:
                    logger.info("Was asked to set state for device ({label}), but state matches. Aborting..",
                                label=self.full_label)
                    raise YomboWarning("Device state is the same, not going to create new device state.")

        kwargs[DEVICE_COMMAND_HUMAN_STATUS] = kwargs.get(DEVICE_COMMAND_HUMAN_STATUS, self.generate_human_state(machine_state, machine_state_extra))
        kwargs[DEVICE_COMMAND_HUMAN_MESSAGE] = kwargs.get(DEVICE_COMMAND_HUMAN_MESSAGE, self.generate_human_message(machine_state, machine_state_extra))
        uploaded = kwargs.get("uploaded", 0)
        uploadable = kwargs.get("uploadable", 1)
        created_at = kwargs.get("created_at", time())
        if "gateway_id" not in kwargs:
            kwargs["gateway_id"] = self.gateway_id

        device_command = None
        device_command_id = None
        command = None
        if DEVICE_COMMAND_DEVICE_COMMAND in kwargs:
            device_command = kwargs[DEVICE_COMMAND_DEVICE_COMMAND]
        elif DEVICE_COMMAND_DEVICE_COMMAND_ID in kwargs and \
                kwargs[DEVICE_COMMAND_DEVICE_COMMAND_ID] in self._Parent._DeviceCommands.device_commands:
            device_command = self._Parent._DeviceCommands.device_commands[kwargs[DEVICE_COMMAND_DEVICE_COMMAND_ID]]

        if device_command is not None:
            command = device_command.command
            device_command_id = device_command.device_command_id
            kwargs[DEVICE_COMMAND_REQUEST_CONTEXT] = device_command.request_context
            kwargs[DEVICE_COMMAND_COMMAND] = device_command.command
            kwargs[DEVICE_COMMAND_REQUEST_BY] = device_command.request_by
            kwargs[DEVICE_COMMAND_REQUEST_BY_TYPE] = device_command.request_by_type
        else:
            kwargs[DEVICE_COMMAND_REQUEST_CONTEXT] = None
            kwargs[DEVICE_COMMAND_COMMAND] = None
            try:
                kwargs[DEVICE_COMMAND_REQUEST_BY], kwargs[DEVICE_COMMAND_REQUEST_BY_TYPE] = \
                    self._Permissions.search_request_by_info(kwargs)
            except YomboWarning:
                kwargs[DEVICE_COMMAND_REQUEST_BY] = self._Users.system_user.accessor_id
                kwargs[DEVICE_COMMAND_REQUEST_BY_TYPE] = self._Users.system_user.accessor_type

        kwargs[DEVICE_COMMAND_DEVICE_COMMAND_ID] = device_command_id

        if command is None:
            if DEVICE_COMMAND_COMMAND in kwargs and kwargs[DEVICE_COMMAND_COMMAND] is not None:
                command = kwargs[DEVICE_COMMAND_COMMAND]
            elif DEVICE_COMMAND_COMMAND_ID in kwargs and kwargs[DEVICE_COMMAND_COMMAND_ID] is not None:
                command = self._Parent._Commands[kwargs[DEVICE_COMMAND_COMMAND]]
            else:
                command = self.command_from_status(machine_state, machine_state_extra)

        kwargs[DEVICE_COMMAND_COMMAND] = command

        kwargs[DEVICE_COMMAND_ENERGY_USAGE], kwargs[DEVICE_COMMAND_ENERGY_TYPE] = \
        energy_usage, energy_type = self.energy_calc(command=kwargs["command"],
                                                     machine_state=machine_state,
                                                     machine_state_extra=machine_state_extra,
                                                     )

        if self.statistic_type not in (None, "", "None", "none"):
            if self.statistic_type.lower() == "datapoint" or self.statistic_type.lower() == "average":
                statistic_label_slug = self.statistic_label_slug
            if self.statistic_type.lower() == "datapoint":
                self._Parent._Statistics.datapoint(f"devices.{statistic_label_slug}", machine_state)
                if self.energy_type not in (None, "", "none", "None"):
                    self._Parent._Statistics.datapoint(f"energy.{statistic_label_slug}", energy_usage)
            elif self.statistic_type.lower() == "average":
                self._Parent._Statistics.averages(f"devices.{statistic_label_slug}",
                                                  machine_state,
                                                  int(self.statistic_bucket_size))
                if self.energy_type not in (None, "", "none", "None"):
                    self._Parent._Statistics.averages(f"energy.{statistic_label_slug}",
                                                      energy_usage,
                                                      int(self.statistic_bucket_size))

        logger.warn("_set_state - about to call _DeviceStates.....")
        self.set_state_machine_extra(**kwargs)
        device_state = yield self._DeviceStates.new(
            self,
            command=kwargs["command"],
            machine_state=machine_state,
            machine_state_extra=machine_state_extra,
            human_state=kwargs[DEVICE_COMMAND_HUMAN_STATUS],
            human_message=kwargs[DEVICE_COMMAND_HUMAN_MESSAGE],
            energy_usage=energy_usage,
            energy_type=energy_type,
            gateway_id=kwargs["gateway_id"],
            request_by=kwargs[DEVICE_COMMAND_REQUEST_BY],
            request_by_type=kwargs[DEVICE_COMMAND_REQUEST_BY_TYPE],
            request_context=kwargs[DEVICE_COMMAND_REQUEST_CONTEXT],
            reporting_source=kwargs[DEVICE_COMMAND_REPORTING_SOURCE],
            device_command=device_command,
            created_at=created_at,
            uploaded=uploaded,
            uploadable=uploadable,
        )

        # Yombo doesn't currently have the capacity to collect these....In the future...
        # if self._security_send_device_states() is True:
        #     request_msg = self._Parent._AMQPYombo.generate_message_request(
        #         exchange_name="ysrv.e.gw_device_status",
        #         source="yombo.gateway.lib.devices.base_device",
        #         destination="yombo.server.device_status",
        #         body={
        #             "created_at": datetime.fromtimestamp(time()).strftime("%Y-%m-%d %H:%M:%S.%f"),
        #             "device_id": self.device_id,
        #             "energy_usage": energy_usage,
        #             "energy_type": energy_type,
        #             "human_state": kwargs["human_state"],
        #             "human_message": kwargs["human_message"],
        #             "machine_state": machine_state,
        #             "machine_state_extra": machine_state_extra,
        #             "user_id": user_id,
        #             "user_type": user_type,
        #             "reporting_source": kwargs["reporting_source"],
        #         },
        #         request_type="save_device_status",
        #     )
        #     self._Parent._AMQPYombo.publish(**request_msg)

        return kwargs, device_state

    def send_state(self, device_state):
        """
        Calls the _device_state_ hook to send current device status. Useful if you just want to send a status of
        a device without actually changing the status.

        :param kwargs:
        :return:
        """
        command = device_state.command
        command_id = None
        command_label = None
        command_machine_label = None
        if command is not None:
            command_id = command.command_id
            command_label = command.label
            command_machine_label = command.machine_label

        try:
            previous_state = self.state_history[1].to_dict()
        except Exception as e:
            previous_state = None
        device_type = self.device_type

        message = {
            "item": device_state,
            "device": self,
            "command": command,
            "device_command_id": device_state.device_command_id,
            "request_context": device_state.request_context,
            "reporting_source": device_state.reporting_source,
            "event": {
                "area": self.area,
                "location": self.location,
                "area_label": self.area_label,
                "full_label": self.full_label,
                "device_id": self.device_id,
                "device_label": self.label,
                "device_machine_label": self.machine_label,
                "device_type_id": self.device_type_id,
                "device_type_label": device_type.machine_label,
                "device_type_machine_label": device_type.machine_label,
                "command_id": command_id,
                "command_label": command_label,
                "command_machine_label": command_machine_label,
                "status_current": self.state_history[0].to_dict(),
                "status_previous": previous_state,
                "gateway_id": self.gateway_id,
                "device_features": self.features,  # lowercase version only shows active features.
            },
        }

        if len(self.state_history) == 1:
            message["previous_state"] = None
        else:
            message["previous_state"] = self.state_history[1]

        self._Scenes.trigger_monitor("device",
                                         device=self,
                                         action="set_status")
        global_invoke_all("_device_state_",
                          called_by=self,
                          arguments=message,
                          )
