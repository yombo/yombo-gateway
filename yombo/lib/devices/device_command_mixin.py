# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_

Base device functions. Should not be directly inherited by other device types, instead
inherit "Device" from _device.py.

This device inherits from _device_attributes.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devices/device_command.html>`_
"""
# Import python libraries
from time import time
from typing import Any, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants.commands import COMMAND_ON, COMMAND_OFF
from yombo.constants.device_commands import (DEVICE_COMMAND_CALLED_BY, DEVICE_COMMAND_COMMAND,
    DEVICE_COMMAND_COMMAND_ID, DEVICE_COMMAND_DEVICE, DEVICE_COMMAND_DEVICE_COMMAND,
    DEVICE_COMMAND_DEVICE_ID, DEVICE_COMMAND_INPUTS, DEVICE_COMMAND_PIN,
    DEVICE_COMMAND_DEVICE_COMMAND_ID, DEVICE_COMMAND_GATEWAY_ID,
    DEVICE_COMMAND_REQUEST_CONTEXT, DEVICE_COMMAND_REPORTING_SOURCE,
    DEVICE_COMMAND_ENERGY_TYPE, DEVICE_COMMAND_ENERGY_USAGE, DEVICE_COMMAND_HUMAN_MESSAGE,
    DEVICE_COMMAND_HUMAN_STATUS)
from yombo.constants.permissions import AUTH_PLATFORM_DEVICE
from yombo.core.exceptions import YomboPinCodeError, YomboWarning
from yombo.core.log import get_logger
from yombo.lib.commands import Command  # used only to determine class type
from yombo.mixins.auth_mixin import AuthMixin
from yombo.utils import random_string, do_search_instance
from yombo.utils.caller import caller_string

logger = get_logger("library.devices.device_command_mixin")


class DeviceCommandMixin:
    """
    Primarily handles all command processing for the device.

    The primary functions developers should use are:
        * :py:meth:`available_commands <Device.available_commands>` - List available commands for a device.
        * :py:meth:`command <Device.command>` - Send a command to a device.
        * :py:meth:`device_command_received <Device.device_command_received>` - Called by any module processing a command.
        * :py:meth:`device_command_pending <Device.device_command_pending>` - When a module needs more time.
        * :py:meth:`device_command_failed <Device.device_command_failed>` - When a module is unable to process a command.
        * :py:meth:`device_command_done <Device.device_command_done>` - When a command has completed..
        * :py:meth:`energy_get_usage <Device.energy_get_usage>` - Get current energy being used by a device.
        * :py:meth:`get_state <Device.get_state>` - Get a latest device state object.
        * :py:meth:`set_state <Device.set_state>` - Set the device state.
    """

    @inlineCallbacks
    def command(self, command: Union[Command, str, Command], pin: Optional[str] = None,
                persistent_request_id: Optional[str] = None, not_before: Optional[Union[int, float]] = None,
                delay: Optional[Union[int, float]] = None, max_delay: Optional[Union[int, float]] = None,
                authentication: Optional[Type[AuthMixin]] = None, request_by: Optional[str] = None,
                request_by_type: Optional[str] = None, request_context: Optional[str] = None,
                inputs: Optional[Dict[str, Any]] = None, not_after: Optional[Union[int, str]] = None,
                callbacks: Optional[Dict[str, Any]] = None, idempotence: Optional[Union[int, str]] = None,
                **kwargs) -> "yombo.lib.devicecommands.DeviceCommand":
        """
        Tells the device to a command. This in turn calls the hook _device_command_ so modules can process the command
        if they are supposed to.

        If a pin is required, "pin" must be included as one of the arguments. All \\*\\*kwargs are sent with the
        hook call.

        :raises YomboWarning: Raised when:

            - delay or max_delay is not a float or int.

        :raises YomboPinCodeError: Raised when:

            - pin is required but not received one.
            - cmd doesn't exist

        :param command: Command instance, command id, or command machine_label to send.
        :type command: str
        :param pin: A pin to check.
        :type pin: str
        :param persistent_request_id: Can be used to cancel a request, typically used by modules for special neads.
        :type persistent_request_id: str
        :param not_before: An epoch time when the command should be sent. Not to be combined with "delay".
        :type not_before: int or float
        :param delay: How many seconds to delay sending the command. Not to be combined with "not_before"
        :type delay: int or float
        :param max_delay: How many second after the "delay" or "not_before" can the command be send. This can occur
            if the system was stopped when the command was supposed to be send.
        :type max_delay: int or float
        :param authentication: An auth item such as a websession or authkey.
        :param request_by: Who created the device state. "alexamodule"
        :param request_by_type: What type of item created it: "module"
        :param inputs: A dictionary containing the "input_type_id" and any supplied "value".
        :param not_after: An epoch time when the command should be discarded.
        :type not_after: int or float
        :param callbacks: A dictionary of callbacks
        :type callbacks: dict
        :param kwargs: Any additional named arguments will be sent to the module for processing.
        :type kwargs: named arguments
        :return: The request id.
        :rtype: str
        """
        logger.info("device ({label}), command: starting", label=self.full_label)
        if self.status != 1:
            raise YomboWarning("Device cannot be used, it's not enabled.")

        logger.info("device ({label}), command: 2", label=self.full_label)
        if self.pin_required == 1:
            if pin is None:
                raise YomboPinCodeError("'pin' is required, but missing.")
            else:
                if self.pin_code != pin:
                    raise YomboPinCodeError("'pin' supplied is incorrect.")
        logger.info("device ({label}), command: 4", label=self.full_label)
        if self.is_scene_controllable is False:
                raise YomboWarning("This device cannot be controlled. Typically because it's an input type device.")

        logger.info("device ({label}), command: 6", label=self.full_label)
        if "control_method" not in kwargs:
            kwargs["control_method"] = "direct"
        if self.is_direct_controllable is False and kwargs["control_method"] == "direct":
            raise YomboWarning("This device cannot be directly controlled. Set 'control_method'.")

        logger.info("device ({label}), command: a", label=self.full_label)
        device_command = {
            "device": self,
            # "pin": pin,
            "idempotence": idempotence,
        }

        logger.info("device ({label}), command: d", label=self.full_label)
        if isinstance(command, Command) is False:
            command = self._Commands.get(command)
        if command.machine_label == "toggle":
            command = self.get_toggle_command()
        device_command["command"] = command

        logger.info("device ({label}), command: g", label=self.full_label)
        # logger.debug("device::command kwargs: {kwargs}", kwargs=kwargs)
        # logger.debug("device::command requested_by: {requested_by}", requested_by=requested_by)

        # This will raise YomboNoAccess exception if user doesn't have access.
        try:
            request_by, request_by_type = self._Permissions.request_by_info(
                authentication, request_by, request_by_type)
        except YomboWarning:
            logger.warn("Device command received for device {label}, but no user specified."
                        " This will generate errors in future versions.",
                        label=self.full_label)
        else:
            if authentication is None and request_by is not None and request_by_type is not None:
                authentication = self._Permissions.find_authentication_item(request_by, request_by_type)
        logger.info("device ({label}), command: j", label=self.full_label)

        # if authentication is not None:
        #     self._Permissions.is_allowed(AUTH_PLATFORM_DEVICE, "control", self.device_id, authentication)

        if authentication is None:
            authentication = self._Users.system_user

        device_command["authentication"] = authentication
        device_command["request_by"] = request_by
        device_command["request_by_type"] = request_by_type

        if DEVICE_COMMAND_REQUEST_CONTEXT in kwargs:
            device_command[DEVICE_COMMAND_REQUEST_CONTEXT] = kwargs[DEVICE_COMMAND_REQUEST_CONTEXT]
        else:
            device_command[DEVICE_COMMAND_REQUEST_CONTEXT] = caller_string(prefix=f"g=self._gateway_id")

        if str(command.command_id) not in self.available_commands():
            logger.warn("Requested command: {command_id}, but only have: {ihave}",
                        command_id=command.command_id, ihave=self.available_commands())
            raise YomboWarning("Invalid command requested for device.", error_code=103)
        logger.info("device ({label}), command: m", label=self.full_label)

        cur_time = time()
        device_command["created_at"] = cur_time
        device_command["persistent_request_id"] = persistent_request_id

        logger.info("device ({label}), command: p", label=self.full_label)
        if delay is not None or not_before is not None:  # if we have a delay, make sure we have required items
            if max_delay is None and not_after is None:
                logger.info("max_delay and not_after missing when calling with delay or not_before. Setting to 60 seconds.")
                max_delay = 60
            if max_delay is not None and not_after is not None:
                raise YomboWarning("'max_delay' and 'not_after' cannot be set at the same time.")

            # Determine when to call the command
            if not_before is not None:
                if isinstance(not_before, str):
                    try:
                        not_before = float(not_before)
                    except:
                        raise YomboWarning("'not_before' time should be epoch second in the future as an int, float, or parsable string.")
                # if isinstance(not_before, int) or isinstance(not_before, float):
                if not_before < cur_time:
                    raise YomboWarning(f"'not_before' time should be epoch second in the future, not the past. Got: {not_before}")
                device_command["not_before_at"] = not_before

            elif delay is not None:
                if isinstance(delay, str):
                    try:
                        delay = float(delay)
                    except:
                        raise YomboWarning(f"'delay' time must be an int, float, or parsable string. Got: {delay}")
                # if isinstance(not_before, int) or isinstance(not_before, float):
                if delay < 0:
                    raise YomboWarning("'not_before' time should be epoch second in the future, not the past.")
                device_command["not_before_at"] = cur_time + delay

            # determine how late the command can be run. This happens is the gateway was turned off
            if not_after is not None:
                if isinstance(not_after, str):
                    try:
                        not_after = float(not_after)
                    except:
                        raise YomboWarning("'not_after' time should be epoch second in the future after not_before as an int, float, or parsable string.")
                if isinstance(not_after, int) or isinstance(not_after, float):
                    if not_after < device_command["not_before_at"]:
                        raise YomboWarning("'not_after' must occur after 'not_before (or current time + delay)")
                device_command["not_after_at"] = not_after
            elif max_delay is not None:
                # todo: try to convert if it's not. Make a util helper for this, occurs a lot!
                if isinstance(max_delay, str):
                    try:
                        max_delay = float(max_delay)
                    except:
                        raise YomboWarning("'max_delay' time should be an int, float, or parsable string.")
                if isinstance(max_delay, int) or isinstance(max_delay, float):
                    if max_delay < 0:
                        raise YomboWarning("'max_delay' must be positive only.")
                device_command["not_after_at"] = device_command["not_before_at"] + max_delay

        logger.info("device ({label}), command: r", label=self.full_label)

        if inputs is None:
            inputs = {}
        else:
            for input_label, input_value in inputs.items():
                try:
                    inputs[input_label] = \
                        self._Parent._DeviceTypes.validate_command_input(self.device_type_id,
                                                                         command.command_id,
                                                                         input_label,
                                                                         input_value)
                except Exception as e:
                    pass
        device_command["inputs"] = inputs
        if callbacks is not None:
            device_command["callbacks"] = callbacks

        logger.info("device ({label}), command: t", label=self.full_label)


        # print("command source: %s" % device_command[DEVICE_COMMAND_REQUEST_CONTEXT])
        logger.info("device ({label}), command: v - {device_command}", label=self.full_label,
                    device_command=device_command)

        device_command_instance = yield self._Parent._DeviceCommands.new(**device_command)
        self.device_commands.appendleft(device_command_instance.device_command_id)
        return device_command_instance

    @staticmethod
    def energy_translate(value: Union[int, float], left_minimum: Union[int, float], left_maximum: Union[int, float],
                         right_minimum: Union[int, float], right_maximum: Union[int, float]) -> float:
        """
        Calculates the energy consumed based on the energy_map.

        :param value:
        :param left_minimum:
        :param left_maximum:
        :param right_minimum:
        :param right_maximum:
        :return:
        """
        # Figure out how "wide" each range is
        left_span = left_maximum - left_minimum
        right_span = right_maximum - right_minimum
        # Convert the left range into a 0-1 range (float)
        value_scaled = float(value - left_minimum) / float(left_span)
        # Convert the 0-1 range into a value in the right range.
        return right_minimum + (value_scaled * right_span)

    def get_device_commands(self, history: int = 0):
        """
        Gets the last command information.

        :param history: How far back to go. 0 = previous, 1 - the one before that, etc.
        :return:
        """
        return self.device_commands[history]

    def device_user_access(self, access_type=None):
        """
        Gets all users that have access to this device.

        :param access_type: If set to "direct", then gets list of users that are specifically added to this device.
            if set to "roles", returns access based on role membership.
        :return:
        """
        if access_type is None:
            access_type = "direct"

        if access_type == "direct":
            permissions = {}
            for email, user in self._Parent._Users.users.items():
                item_permissions = user.item_permissions
                if "device" in item_permissions and self.machine_label in item_permissions["device"]:
                    if email not in permissions:
                        permissions[email] = []
                    for action in item_permissions["device"][self.machine_label]:
                        if action not in permissions[email]:
                            permissions[email].append(action)
            return permissions
        elif access_type == "roles":
            return {}

    def remove_delayed(self) -> None:
        """
        Remove any messages that might be set to be called later that
        relates to this device.  Easy, just tell the messages library to 
        do that for us.
        """
        delayed_commands = self.delayed_commands()
        for device_command_id, device_command in delayed_commands.items():
            device_command.device_command_cancel()

    def delayed_commands(self) -> Dict[str, "yombo.lib.devicecommands.DeviceCommand"]:
        """
        Get commands that are delayed for this device. This is commands that are set to complete in the
        future, and not pending.
        """
        device_commands = {}
        for device_command_id, device_command in self._Parent._DeviceCommands.device_commands.items():
            if device_command.status == "delayed" and device_command.device.device_id == self.device_id:
                device_commands[device_command_id] = device_command
        return device_commands

    def pending_commands(self, criteria: Optional[dict] = None,
                         sort_key: Optional[str] = None) -> Dict[str, "yombo.lib.devicecommands.DeviceCommand"]:
        """
        Checks Device Commands library for any pending commands for the current device.

        :param criteria: Determines what to search for. Ex: {'status': ['sent', 'received', 'pending', 'done']}
        :param sort_key: How to sort the results, default is 'created_at'
        :return:
        """
        if sort_key is None:
            sort_key = "label"

        results = {}
        for device_command_id, device_command in self._Parent._DeviceCommands.device_commands.items():
            if criteria is None:
                if device_command.device.device_id == self.device_id:
                    if device_command.status in ("sent", "received", "pending"):
                        results[device_command_id] = device_command
            else:
                matches = True
                for key, value in criteria.items():
                    if hasattr(device_command, key):
                        test_value = getattr(device_command, key)
                        if isinstance(value, list):
                            if test_value not in value:
                                matches = False
                                break
                        else:
                            if test_value != value:
                                matches = False
                                break
                if matches:
                    results[device_command_id] = device_command
        # returns results sorted, default is by created
        return dict(sorted(iter(results.items()), key=lambda i: getattr(i[1], sort_key)))

    def validate_command(self, command_requested):
        available_commands = self.available_commands()
        try:
            command_requested = self.get(command_requested)
        except KeyError:
            pass
        else:
            if command_requested.command_id in available_commands:
                return command_requested

        commands = {}
        for command_id, data in available_commands.items():
            commands[command_id] = data["command"]
        search_attributes = [
            {
                "field": "command_id",
                "value": command_requested,
                "limiter": .96,
            },
            {
                "field": "machine_label",
                "value": command_requested,
                "limiter": .89,
            },
            {
                "field": "label",
                "value": command_requested,
                "limiter": .89,
            },
        ]
        try:
            logger.debug("Get is about to call search...: {command_requested}", command_requested=command_requested)
            results = do_search_instance(search_attributes,
                                         commands,
                                         self._Parent._storage_search_fields,
                                         allowed_keys=self._Parent._Commands._storage_search_fields,
                                         limiter=.89,
                                         max_results=1)

            if results["was_found"]:
                return True
            else:
                return False
        except YomboWarning:
            return False
            # raise KeyError("Searched for %s, but had problems: %s" % (command_requested, e))

    @inlineCallbacks
    def delete(self, session=None):
        """
        Called when the device should delete itself.

        :return: 
        """
        results = yield self._Parent.delete_device(self.device_id, session=session)
        return results

    @inlineCallbacks
    def enable(self, session=None):
        """
        Called when the device should enable itself.

        :return:
        """
        results = yield self._Parent.enable_device(self.device_id, session=session)
        return results

    @inlineCallbacks
    def disable(self, session=None):
        """
        Called when the device should disable itself.

        :return:
        """
        results = yield self._Parent.disable_device(self.device_id, session=session)
        return results

    # @inlineCallbacks
    # def save(self, source=None, session=None):
    #     """
    #     Save this device to the database.
    #
    #     :return:
    #     """
    #     if source is None:
    #         source = self._source
    #
    #     if self._gateway_id != self._gateway_id:
    #         return {
    #             "status": "failed",
    #             "msg": "Can only edit local devices.",
    #             "device_id": self.device_id
    #         }
    #
    #     if self._meta["source"] != "database":
    #         return {
    #             "status": "failed",
    #             "msg": "Can only edit database loaded devices.",
    #             "device_id": self.device_id
    #         }
    #
    #     if source != "amqp":
    #         api_data = {
    #             "device_type_id": str(self.device_type_id),
    #             "machine_label": str(self.machine_label),
    #             "label": str(self.label),
    #             "description": str(self.description),
    #             "location_id": self.location_id,
    #             "area_id": self.area_id,
    #             "notes": str(self.notes),
    #             "pin_code": self.pin_code,
    #             "pin_required": int(self.pin_required),
    #             "pin_timeout": self.pin_timeout,
    #             "statistic_label": str(self.statistic_label),
    #             "statistic_lifetime": str(self.statistic_lifetime),
    #             "statistic_type": str(self.statistic_type),
    #             "statistic_bucket_size": str(self.statistic_bucket_size),
    #             "energy_type": self.energy_type,
    #             "energy_tracker_source_type": self.energy_tracker_source_type,
    #             "energy_tracker_source_id": self.energy_tracker_source_id,
    #             "energy_map": self.energy_map,
    #             "controllable": self.controllable,
    #             "allow_direct_control": self.allow_direct_control,
    #             "status": self.status,
    #             "created_at": int(self.created_at),
    #             "updated_at": int(self.updated_at),
    #         }
    #
    #         if isinstance(self.energy_map, dict):
    #             api_data["energy_map"] = data_pickle(self.energy_map, "json")
    #
    #         api_results = yield self._YomboAPI.request("PATCH",
    #                                                    f"/v1/device/{self.device_id}",
    #                                                    api_data,
    #                                                    session=session)
    #         if api_results["code"] > 299:
    #             return {
    #                 "status": "failed",
    #                 "msg": "Couldn't edit device",
    #                 "apimsg": api_results["content"]["message"],
    #                 "apimsghtml": api_results["content"]["html_message"],
    #                 "device_id": self.device_id,
    #             }
    #
    #     yield self._Parent._LocalDB.upsert_device(self)
    #
    #     return {
    #         "status": "success",
    #         "msg": "Device saved.",
    #         "device_id": self.device_id
    #     }
