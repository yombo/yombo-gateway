# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/modules/devices/>`_

The device class is responsible for managing a single device.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries


try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

import copy
from collections import deque, namedtuple
from time import time
from collections import OrderedDict

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue

# Import Yombo libraries
from yombo.core.exceptions import YomboPinCodeError, YomboWarning
from yombo.core.log import get_logger
from yombo.utils import random_string, global_invoke_all, do_search_instance
from yombo.lib.commands import Command  # used only to determine class type
from ._device_command import Device_Command

logger = get_logger('library.devices.device')

class Device(object):
    """
    A class to manage a single device. This clas contains various attributes about the
    device as well as several functions. For exaqmple, a command be easily sent using the
    :py:meth:`command <Device.command>` function.


    The primary functions developers should use are:
        * :py:meth:`available_commands <Device.available_commands>` - List available commands for a device.
        * :py:meth:`command <Device.command>` - Send a command to a device.
        * :py:meth:`device_command_received <Device.device_command_received>` - Called by any module processing a command.
        * :py:meth:`device_command_pending <Device.device_command_pending>` - When a module needs more time.
        * :py:meth:`device_command_failed <Device.device_command_failed>` - When a module is unable to process a command.
        * :py:meth:`device_command_done <Device.device_command_done>` - When a command has completed..
        * :py:meth:`energy_get_usage <Device.energy_get_usage>` - Get current energy being used by a device.
        * :py:meth:`get_status <Device.get_status>` - Get a named tuple containing the device status.
        * :py:meth:`set_status <Device.set_status>` - Set the device status.
        * :py:meth:`get_status <Device.get_status>` - Get a named tuple containing the device status.
        * :py:meth:`get_status <Device.get_status>` - Get a named tuple containing the device status.
    """

    PLATFORM = "device"

    SUPPORT_BRIGHTNESS = False
    SUPPORT_ALL_ON = False
    SUPPORT_ALL_OFF = False
    SUPPORT_COLOR = False
    SUPPORT_COLOR_MODE = None  # rgb....
    SUPPORT_PINGABLE = False
    SUPPORT_BROADCASTS_UPDATES = False
    SUPPORT_NUMBER_OF_STEPS = 4096

    TOGGLE_COMMANDS = None  # Put two command machine_labels in a list to enable toggling.

    def __str__(self):
        """
        Print a string when printing the class.  This will return the device_id so that
        the device can be identified and referenced easily.
        """
        return self.device_id

    ## <start dict emulation>
    def __getitem__(self, key):
        return self.__dict__[key]

    def __repr__(self):
        return repr(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    def has_key(self, k):
        return k in self.__dict__

    def keys(self):
        return list(self.__dict__.keys())

    def values(self):
        return list(self.__dict__.values())

    def items(self):
        return list(self.__dict__.items())

    def __cmp__(self, dict):
        return cmp(self.__dict__, dict)

    def __contains__(self, item):
        return item in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)

    ##  <end dict emulation>

    def __init__(self, device, _Parent, test_device=None):
        """
        :param device: *(list)* - A device as passed in from the devices class. This is a
            dictionary with various device attributes.
        :ivar callBeforeChange: *(list)* - A list of functions to call before this device has it's status
            changed. (Not implemented.)
        :ivar callAfterChange: *(list)* - A list of functions to call after this device has it's status
            changed. (Not implemented.)
        :ivar device_id: *(string)* - The UUID of the device.
        :type device_id: string
        :ivar device_type_id: *(string)* - The device type UUID of the device.
        :ivar label: *(string)* - Device label as defined by the user.
        :ivar description: *(string)* - Device description as defined by the user.
        :ivar pin_required: *(bool)* - If a pin is required to access this device.
        :ivar pin_code: *(string)* - The device pin number.
            system to deliver commands and status update requests.
        :ivar created: *(int)* - When the device was created; in seconds since EPOCH.
        :ivar updated: *(int)* - When the device was last updated; in seconds since EPOCH.
        :ivar last_command: *(dict)* - A dictionary of up to the last 30 command messages.
        :ivar status_history: *(dict)* - A dictionary of strings for current and up to the last 30 status values.
        :ivar device_variables: *(dict)* - The device variables as defined by various modules, with
            values entered by the user.
        :ivar available_commands: *(list)* - A list of command_id's that are valid for this device.
        """
        self._FullName = 'yombo.gateway.lib.Devices.Device'
        self._Name = 'Devices.Device'
        self._Parent = _Parent
        # logger.debug("New device - info: {device}", device=device)

        self.StatusTuple = namedtuple('Status',
                                      "device_id, set_time, energy_usage, energy_type, human_status, human_message, "
                                      "last_command, machine_status, machine_status_extra, requested_by, "
                                      "reported_by, request_id, uploaded, uploadable")

        self.CommandTuple = namedtuple('Command',
                                       "set_time, command_id, requested_by, reported_by, request_id, uploaded, "
                                       "uploadable")

        self.call_before_command = []
        self.call_after_command = []

        self.device_id = device["id"]
        if test_device is None:
            self.test_device = False
        else:
            self.test_device = test_device

        self.last_command = deque({}, 50)
        self.status_history = deque({}, 50)
        self.device_variables = {}
        self.device_type_id = None
        self.machine_label = None
        self.label = None
        self.description = None
        self.pin_required = None
        self.pin_code = None
        self.pin_timeout = None
        self.voice_cmd = None
        self.voice_cmd_order = None
        self.statistic_label = None
        self.statistic_lifetime = None
        self.status = None
        self.created = None
        self.updated = None
        self.updated_srv = None
        self.energy_tracker_device = None
        self.energy_tracker_source = None
        self.energy_map = None
        self.energy_type = None
        self.attributes = []

        self.device_is_new = True
        self.update_attributes(device)

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Performs items that require deferreds.

        :return:
        """
        # print("getting device variables for: %s" % self.device_id)
        self.device_variables = yield self._Parent._Variables.get_variable_fields_data(
            data_relation_type='device',
            data_relation_id=self.device_id
        )
        yield self._Parent._DeviceTypes.ensure_loaded(self.device_type_id)

        if self.test_device is False and self.device_is_new is True:
            self.device_is_new = False
            yield self.load_history(35)

    def update_attributes(self, device):
        """
        Sets various values from a device dictionary. This can be called when either new or
        when updating.

        :param device: 
        :return: 
        """
        if 'device_type_id' in device:
            self.device_type_id = device["device_type_id"]
        if 'machine_label' in device:
            self.machine_label = device["machine_label"]
        if 'label' in device:
            self.label = device["label"]
        if 'description' in device:
            self.description = device["description"]
        if 'pin_required' in device:
            self.pin_required = int(device["pin_required"])
        if 'pin_code' in device:
            self.pin_code = device["pin_code"]
        if 'pin_timeout' in device:
            try:
                self.pin_timeout = int(device["pin_timeout"])
            except:
                self.pin_timeout = None
        if 'voice_cmd' in device:
            self.voice_cmd = device["voice_cmd"]
        if 'voice_cmd_order' in device:
            self.voice_cmd_order = device["voice_cmd_order"]
        if 'statistic_label' in device:
            self.statistic_label = device["statistic_label"]  # 'myhome.groundfloor.kitchen'
        if 'statistic_lifetime' in device:
            self.statistic_lifetime = device["statistic_lifetime"]  # 'myhome.groundfloor.kitchen'
        if 'attributes' in device:
            self.set_attributes(device["attributes"])
        if 'status' in device:
            self.status = int(device["status"])
        if 'created' in device:
            self.created = int(device["created"])
        if 'updated' in device:
            self.updated = int(device["updated"])
        if 'updated_srv' in device:
            self.updated_srv = int(device["updated_srv"])
        if 'energy_tracker_device' in device:
            self.energy_tracker_device = device['energy_tracker_device']
        if 'energy_tracker_source' in device:
            self.energy_tracker_source = device['energy_tracker_source']

        if 'energy_type' in device:
            self.energy_type = device['energy_type']

        if 'energy_map' in device:
            if device['energy_map'] is not None:
                # create an energy map from a dictionary
                energy_map_final = {}
                for percent, rate in device['energy_map'].items():
                    energy_map_final[self._Validate.number(percent)] = self._Validate.number(rate)
                energy_map_final = OrderedDict(sorted(list(energy_map_final.items()), key=lambda x_y: float(x_y[0])))
                self.energy_map = energy_map_final
            else:
                self.energy_map = None

        if self.device_is_new is True:
            global_invoke_all('_device_updated_', called_by=self, **{'device': self})

            # if 'variable_data' in device:
            # print("device.update_attributes: new: %s: " % device['variable_data'])
            # print("device.update_attributes: existing %s: " % self.device_variables)

    def set_attributes(self, new_attributes, replace=None):
        """
        Set device attributes. New attributes should be a string seperated by
        commas.
        
        :param new_attributes: 
        :param replace: 
        :return: 
        """
        if replace is None:
            replace = True

        if isinstance(new_attributes, str) is False:
            return False
        new_attributes = "".join(new_attributes.split())  # we don't like spaces
        attributes = new_attributes.split(',')
        if replace is True:
            self.attributes = attributes
            return True
        else:
            for new_a in new_attributes:
                if new_a not in self.attributes:
                    self.attributes.append(new_a)
            return True

    def commands_pending(self, criteria = None, limit = None):
        device_commands = self._Parent.device_commands
        results = OrderedDict()
        for id, DC in device_commands.items():
            # print("DC: %s"  % DC.__dict__)
            if criteria is None:
                if DC.device.device_id == self.device_id:
                    if DC.status in ('sent', 'received', 'pending'):
                        results[id] = DC
            else:
                matches = True
                for key, value in criteria.items():
                    # print("commands_pending testing criteria: %s: %s" % (key, value))
                    if hasattr(DC, key):
                        test_value = getattr(DC, key)
                        # print("test_value: %s" % test_value)
                        if isinstance(value, list):
                            print("got a list.. %s" % value)
                            if test_value not in value:
                                matches = False
                                break
                        else:
                            if test_value != value:
                                matches = False
                                break
                if matches:
                    results[id] = DC

            if limit is not None and len(results) == limit:
                return results
        return results

    def get_toggle_command(self):
        """
        If a device is toggleable, return True. It's toggleable if a device only has two commands.
        :return: 
        """

        if isinstance(self.TOGGLE_COMMANDS, list) and len(self.TOGGLE_COMMANDS) == 2:
            if self.last_command[0].command_id is None:
                raise YomboWarning("Device cannot be toggled, device is in unknown state.")
            last_command_id = self.last_command[0].command_id
            for command_id in self.TOGGLE_COMMANDS:
                if command_id == last_command_id:
                    continue
                return self._Parent._Commands[command_id]
        else:
            raise YomboWarning(
                "Device cannot be toggled, it's not enabled for this device.")

    def available_commands(self):
        """
        Returns available commands for the current device.
        :return: 
        """
        return self._Parent._DeviceTypes.device_type_commands(self.device_type_id)

    def dump(self):
        """
        Export device variables as a dictionary.
        """
        return {'device_id': str(self.device_id),
                'device_type_id': str(self.device_type_id),
                'machine_label': str(self.machine_label),
                'label': str(self.label),
                'description': str(self.description),
                'statistic_label': str(self.statistic_label),
                'statistic_lifetime': str(self.statistic_lifetime),
                'pin_code': "********",
                'pin_required': int(self.pin_required),
                'pin_timeout': int(self.pin_timeout),
                'voice_cmd': str(self.voice_cmd),
                'voice_cmd_order': str(self.voice_cmd_order),
                'created': int(self.created),
                'updated': int(self.updated),
                'last_command': copy.copy(self.last_command),
                'status_history': copy.copy(self.status_history),
                }

    def command(self, cmd, pin=None, request_id=None, not_before=None, delay=None, max_delay=None, requested_by=None,
                inputs=None, not_after=None, **kwargs):
        """
        Tells the device to a command. This in turn calls the hook _device_command_ so modules can process the command
        if they are supposed to.

        If a pin is required, "pin" must be included as one of the arguments. All **kwargs are sent with the
        hook call.

        :raises YomboWarning: Raised when:

            - delay or max_delay is not a float or int.

        :raises YomboPinCodeError: Raised when:

            - pin is required but not recieved one.
            - cmd doesn't exist

        :param cmd: Command ID or Label to send.
        :type cmd: str
        :param pin: A pin to check.
        :type pin: str
        :param request_id: Request ID for tracking. If none given, one will be created.
        :type request_id: str
        :param delay: How many seconds to delay sending the command. Not to be combined with 'not_before'
        :type delay: int or float
        :param not_before: An epoch time when the command should be sent. Not to be combined with 'delay'.
        :type not_before: int or float
        :param max_delay: How many second after the 'delay' or 'not_before' can the command be send. This can occur
            if the system was stopped when the command was supposed to be send.
        :type max_delay: int or float
        :param inputs: A list of dictionaries containing the 'input_type_id' and any supplied 'value'.
        :type input: list of dictionaries
        :param kwargs: Any additional named arguments will be sent to the module for processing.
        :type kwargs: named arguments
        :return: The request id.
        :rtype: str
        """
        if self.status != 1:
            raise YomboWarning("Device cannot be used, it's not enabled.")

        if self.pin_required == 1:
            if pin is None:
                raise YomboPinCodeError("'pin' is required, but missing.")
            else:
                if self.pin_code != pin:
                    raise YomboPinCodeError("'pin' supplied is incorrect.")
        device_command = {
            "device": self,
        }
        if isinstance(cmd, Command):
            command = cmd
        else:
            command = self._Parent._Commands.get(cmd)
        if command.machine_label == 'toggle':
            command = self.get_toggle_command()
        device_command['command'] = command

        # logger.debug("device::command kwargs: {kwargs}", kwargs=kwargs)
        # logger.debug("device::command requested_by: {requested_by}", requested_by=requested_by)
        if requested_by is None:  # soon, this will cause an error!
            requested_by = {
                'user_id': 'Unknown',
                'component': 'Unknown',
                'gateway': 'Unknown'
            }
        device_command['requested_by'] = requested_by

        if str(command.command_id) not in self.available_commands():
            logger.warn("Requested command: {command_id}, but only have: {ihave}",
                        command_id=command.command_id, ihave=self.available_commands())
            raise YomboWarning("Invalid command requested for device.", errorno=103)

        cur_time = time()
        device_command['created_time'] = cur_time

        persistent_request_id = kwargs.get('persistent_request_id', None)
        device_command['persistent_request_id'] = persistent_request_id

        if persistent_request_id in self._Parent.device_commands_persistent:
            previous_request_id = self._Parent.device_commands_persistent[persistent_request_id]
            if previous_request_id in self._Parent.device_commands:
                logger.debug("found a previous persistent request. Canceling it and creating a new one.")
                self._Parent.device_commands[previous_request_id].set_finished(status="superseded", message="Replacement request created.")
        elif request_id is None:
            request_id = random_string(length=18)  # print("in device command: rquest_id 2: %s" % request_id)

        device_command['request_id'] = request_id

        if delay is not None or not_before is not None:  # if we have a delay, make sure we have required items
            if max_delay is None and not_after is None:
                logger.warn("max_delay and not_after missing when calling with delay or not_before. Setting to 60 seconds.")
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
                    raise YomboWarning("'not_before' time should be epoch second in the future, not the past. Got: %s" % not_before)
                device_command['not_before_time'] = not_before

            elif delay is not None:
                if isinstance(delay, str):
                    try:
                        delay = float(delay)
                    except:
                        raise YomboWarning("'delay' time must be an int, float, or parsable string. Got: %s" % delay)
                # if isinstance(not_before, int) or isinstance(not_before, float):
                if delay < 0:
                    raise YomboWarning("'not_before' time should be epoch second in the future, not the past.")
                device_command['not_before_time'] = cur_time + delay

            # determine how late the command can be run. This happens is the gateway was turned off
            if not_after is not None:
                if isinstance(not_after, str):
                    try:
                        not_after = float(not_after)
                    except:
                        raise YomboWarning("'not_after' time should be epoch second in the future after not_before as an int, float, or parsable string.")
                if isinstance(not_after, int) or isinstance(not_after, float):
                    if not_after < device_command['not_before_time']:
                        raise YomboWarning("'not_after' must occur after 'not_before (or current time + delay)")
                device_command['not_after_time'] = not_after
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
                device_command['not_after_time'] = device_command['not_before_time'] + max_delay

        device_command['params'] = kwargs.get('params', None)
        if inputs is None:
            inputs = {}
        device_command['inputs'] = inputs

        self.last_command.appendleft({
            'command_id': command.command_id,
            'machine_label': command.machine_label,
            'label': command.label,
            'request_id': request_id,
        })
        self._Parent.device_commands[request_id] = Device_Command(device_command, self._Parent)
        self._Parent.device_commands.move_to_end(request_id, last=False)  # move to the front.
        return request_id

    @inlineCallbacks
    def do_command_hook(self, device_command):
        """
        Performs the actual sending of a device command. This calls the hook "_device_command_". Any modules that
        have implemented this hook can monitor or act on the hook.

        When a device changes state, whatever module changes the state of a device, or is responsible for reporting
        those changes, it *must* call "self._Devices['devicename/deviceid'].set_state()

        **Hooks called**:

        * _devices_command_ : Sends kwargs: *device*, the device object and *command*. This receiver will be
          responsible for obtaining whatever information it needs to complete the action being requested.

        :param device_command: device_command instance with all our required values.
        :return:
        """
        items = {
            'command': device_command.command,
            'device': self,
            'inputs': device_command.inputs,
            'request_id': device_command.request_id,
            'device_command': device_command,
            'called_by': self,
        }
        device_command.set_sent()
        logger.debug("calling _device_command_, request_id: {request_id}", request_id=device_command.request_id)
        # print(self._Parent.device_commands)
        results = yield global_invoke_all('_device_command_', **items)
        for component, result in results.items():
            if result is True:
                device_command.set_received(message="Received by: %s" % component)
        self._Parent._Statistics.increment("lib.devices.commands_sent", anon=True)

    def device_command_received(self, request_id, **kwargs):
        """
        Called by any module that intends to process the command and deliver it to the automation device.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get('message', None)
        self._Parent.device_commands[request_id].set_received(message=message)
        global_invoke_all('_device_command_status_', called_by=self, device_command=self._Parent.device_commands[request_id])

    def device_command_pending(self, request_id, **kwargs):
        """
        This should only be called if command processing takes more than 1 second to complete. This lets applications,
        users, and everyone else know it's pending. Calling this excessively can cost a lot of local CPU cycles.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get('message', None)
        self._Parent.device_commands[request_id].set_pending(message=message)
        global_invoke_all('_device_command_status_', called_by=self, device_command=self._Parent.device_commands[request_id])

    def device_command_failed(self, request_id, **kwargs):
        """
        Should be called when a the command cannot be completed for whatever reason.

        A status can be provided: send a named parameter of 'message' with any value.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get('message', None)
        self._Parent.device_commands[request_id].set_failed(message=message)

        if message is not None:
            logger.warn('Device ({label}) command failed: {message}', label=self.label, message=message)
        global_invoke_all('_device_command_status_', called_by=self, device_command=self._Parent.device_commands[request_id])

    def device_command_done(self, request_id, **kwargs):
        """
        Called by any module that has completed processing of a command request.

        A status can be provided: send a named parameter of 'message' with any value.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get('message', None)
        self._Parent.device_commands[request_id].set_finished(message=message)
        global_invoke_all('_device_command_status_', called_by=self, device_command=self._Parent.device_commands[request_id])

    def get_request(self, request_id):
        """
        Returns a request instance for a provide request_id.

        :raises KeyError: When an invalid request_id is requested.        
        :param request_id: A request id returned from a 'command()' call. 
        :return: Device_Request instance
        """
        return self._Parent.device_commands[request_id]

    def energy_translate(self, value, leftMin, leftMax, rightMin, rightMax):
        """
        Calculates the energy consumed based on the energy_map.

        :param value:
        :param leftMin:
        :param leftMax:
        :param rightMin:
        :param rightMax:
        :return:
        """
        # Figure out how 'wide' each range is
        leftSpan = leftMax - leftMin
        rightSpan = rightMax - rightMin
        # Convert the left range into a 0-1 range (float)
        valueScaled = float(value - leftMin) / float(leftSpan)
        # Convert the 0-1 range into a value in the right range.
        return rightMin + (valueScaled * rightSpan)

    def get_status(self, history=0):
        """
        Gets the history of the device status.

        :param history: How far back to go. 0 = previoius, 1 - the one before that, etc.
        :return:
        """
        return self.status_history[history]

    def get_last_command(self, history=0):
        """
        Gets the last command information.

        :param history: How far back to go. 0 = previoius, 1 - the one before that, etc.
        :return:
        """
        return self.last_command[history]

    def set_status(self, **kwargs):
        """
        Usually called by the device's command/logic module to set/update the
        device status. This can also be called externally as needed.

        :raises YomboWarning: Raised when:

            - If no valid status sent in. Errorno: 120
            - If statusExtra was set, but not a dictionary. Errorno: 121
        :param kwargs: Named arguments:

            - human_status *(int or string)* - The new status.
            - human_message *(string)* - A human friendly text message to display.
            - command *(string)* - Command label from the last command.
            - machine_status *(int or string)* - The new status.
            - machine_status_extra *(dict)* - Extra status as a dictionary.
            - request_id *(string)* - Request ID that this should correspond to.
            - requested_by *(string)* - A dictionary containing user_id, component, and gateway.
            - silent *(any)* - If defined, will not broadcast a status update
              message; atypical.
        """
        logger.info("set_status called...: {kwargs}", kwargs=kwargs)
        self._set_status(**kwargs)
        if 'silent' not in kwargs:
            self.send_status(**kwargs)

    def _set_status(self, **kwargs):
        """
        A private function used to do the work of setting the status.
        :param kwargs: 
        :return: 
        """
        machine_status = None
        if 'machine_status' not in kwargs:
            raise YomboWarning("set_status was called without a real machine_status!", errorno=120)

        human_status = kwargs.get('human_status', machine_status)
        human_message = kwargs.get('human_message', machine_status)
        machine_status = kwargs['machine_status']
        machine_status_extra = kwargs.get('machine_status_extra', None)
        uploaded = kwargs.get('uploaded', 0)
        uploadable = kwargs.get('uploadable', 0)
        set_time = time()

        requested_by_default = {
            'user_id': 'Unknown',
            'component': 'Unknown',
            'gateway': 'Unknown'
        }

        if "request_id" in kwargs and kwargs['request_id'] in self._Parent.device_commands:
            request_id = kwargs['request_id']
            requested_by = self._Parent.device_commands[request_id].requested_by
            kwargs['command'] = self._Parent.device_commands[request_id].command
        elif "requested_by" in kwargs:
            request_id = None
            requested_by = kwargs['requested_by']
            if isinstance(requested_by, dict) is False:
                kwargs['requested_by'] = requested_by_default
            else:
                if 'user_id' not in requested_by:
                    requested_by['user_id'] = 'Unknown'
                if 'component' not in requested_by:
                    requested_by['component'] = 'Unknown'
                if 'gateway' not in requested_by:
                    requested_by['gateway'] = 'Unknown'
        else:
            request_id = None
            requested_by = requested_by_default
        kwargs['requested_by'] = requested_by

        reported_by = kwargs.get('reported_by', 'Unknown')

        kwargs['reported_by'] = reported_by

        message = {
            'device_id': self.device_id,
            'device_machine_label': self.machine_label,
            'device_label': self.label,
            'machine_status': machine_status,
            'machine_status_extra': machine_status_extra,
            'human_message': human_message,
            'human_status': human_status,
            'time': set_time,
            'requested_by': requested_by,
            'reported_by': reported_by,
        }

        if 'command' in kwargs:
            command = self._Parent._Commands[kwargs['command']]
            command_machine_label = command.machine_label
            message['last_command'] = command.machine_label
            message['command_machine_label'] = command.machine_label
            message['command_label'] = command.label
            message['command_id'] = command.command_id
            energy_usage, energy_type = self.energy_calc(command=command,
                                                         machine_status=machine_status,
                                                         machine_status_extra=machine_status_extra,
                                                         )
        else:
            command_machine_label = machine_status
            energy_usage, energy_type = self.energy_calc(machine_status=machine_status,
                                                         machine_status_extra=machine_status_extra,
                                                         )

        message['energy_usage'] = energy_usage
        message['energy_type'] = energy_type

        if self.statistic_label is not None and self.statistic_label != "":
            self._Parent._Statistics.datapoint("devices.%s" % self.statistic_label, machine_status)
            self._Parent._Statistics.datapoint("energy.%s" % self.statistic_label, energy_usage)

        new_status = self.StatusTuple(self.device_id, set_time, energy_usage, energy_type, human_status, human_message,
                                      command_machine_label, machine_status, machine_status_extra, requested_by,
                                      reported_by, request_id, uploaded, uploadable)
        self.status_history.appendleft(new_status)
        if self.test_device is False:
            self._Parent._LocalDB.save_device_status(**new_status._asdict())
        self._Parent.check_trigger(self.device_id, new_status)

        # self._Parent.mqtt.publish("yombo/devices/%s/status" % self.machine_label, json.dumps(message), 1)

    def send_status(self, **kwargs):
        """
        Sends current status. Use set_status() to set the status, it will call this method for you.

        Calls the _device_status_ hook to send current device status. Useful if you just want to send a status of
        a device without actually changing the status.

        :param kwargs:
        :return:
        """

        message = {
            'device': self,
        }

        if 'command' in kwargs:
            message['command'] = kwargs['command']
        else:
            message['command'] = None

        if len(self.status_history) == 1:
            message['status'] = self.status_history[0]
            message['previous_status'] = None
        else:
            message['status'] = self.status_history[0]
            message['previous_status'] = self.status_history[1]

        global_invoke_all('_device_status_', called_by=self, **message)

    def remove_delayed(self):
        """
        Remove any messages that might be set to be called later that
        relates to this device.  Easy, just tell the messages library to 
        do that for us.
        """
        self._Parent._MessageLibrary.device_delay_cancel(self.device_id)

    def get_delayed(self):
        """
        List messages that are to be sent at a later time.
        """
        self._Parent._MessageLibrary.device_delay_list(self.device_id)

    @inlineCallbacks
    def load_history(self, limit=40):
        """
        Loads device history into the device instance. This method gets the data from the db and adds a callback
        to _do_load_history to actually set the values.

        :param limit: int - How many history items should be loaded. Default: 35
        :return:
        """
        if limit is None:
            limit = False

        records = yield self._Parent._Libraries['LocalDB'].get_device_status(id=self.device_id, limit=limit)
        if len(records) == 0:
            requested_by = {
                'user_id': 'Unknown',
                'component': 'Unknown',
                'gateway': 'Unknown'
            }
            self.status_history.appendleft(
                self.StatusTuple(self.device_id, int(time()), 0, self.energy_type, 'Unknown', 'Unknown status for device', None, None, {},
                                 requested_by, None, 'Unknown', 0, 1))
        else:
            for record in records:
                self.status_history.appendleft(
                    self.StatusTuple(record['device_id'], record['set_time'], record['energy_usage'], record['energy_type'],
                                     record['human_status'], record['human_message'], record['last_command'],
                                     record['machine_status'], record['machine_status_extra'], record['requested_by'],
                                     record['reported_by'], record['request_id'], record['uploaded'], record['uploadable']))
                #                              self.StatusTuple = namedtuple('Status',  "device_id,           set_time,          energy_usage,     energy_type,      human_status,           human_message,           machine_status,          machine_status_extra,           requested_by,           reported_by,           uploaded,           uploadable")

                # logger.debug("Device load history: {device_id} - {status_history}", device_id=self.device_id, status_history=self.status_history)

    def validate_command(self, command_requested):
        available_commands = self.available_commands()
        if command_requested in available_commands:
            return available_commands[command_requested]
        else:
            commands = {}
            print("available_commands: %s" % available_commands)
            for command_id, data in available_commands.items():
                commands[command_id] = data['command']
            attrs = [
                {
                    'field': 'command_id',
                    'value': command_requested,
                    'limiter': .96,
                },
                {
                    'field': 'label',
                    'value': command_requested,
                    'limiter': .89,
                },
                {
                    'field': 'machine_label',
                    'value': command_requested,
                    'limiter': .89,
                }
            ]
            try:
                logger.debug("Get is about to call search...: %s" % command_requested)
                found, key, item, ratio, others = do_search_instance(attrs, commands,
                                                                     self._Parent._Commands.command_search_attributes,
                                                                     limiter=.89,
                                                                     operation="highest")
                logger.debug("found command by search: {command_id}", command_id=key)
                if found:
                    return True
                else:
                    return False
            except YomboWarning as e:
                return False
                # raise KeyError('Searched for %s, but had problems: %s' % (command_requested, e))

    # def update(self, record):
    #
    #     # check if device_type_id changes.
    #     if 'device_type_id' in record:
    #         if record['device_type_id'] != self.device_type_id:
    #             self.device_type_id = record['device_type_id']
    #
    #     # global_invoke_all('_devices_update_', **{'id': record['id']})  # call hook "device_update" when adding a new device.

    def delete(self):
        """
        Called when the device should delete itself.

        :return: 
        """
        # print("deleting device.....")
        self._Parent._LocalDB.set_device_status(self.device_id, 2)
        global_invoke_all('_device_deleted_', called_by=self, **{'device': self})  # call hook "devices_delete" when deleting a device.
        self.status = 2

    def enable(self):
        """
        Called when the device should delete itself.

        :return:
        """
        self._Parent._LocalDB.set_device_status(self.device_id, 1)
        global_invoke_all('_device_enabled_', called_by=self, **{'device': self})  # call hook "devices_delete" when deleting a device.
        self.status = 1

    def disable(self):
        """
        Called when the device should delete itself.

        :return:
        """
        self._Parent._LocalDB.set_device_status(self.device_id, 0)
        global_invoke_all('_device_disabled_', called_by=self, **{'device': self})  # call hook "devices_delete" when deleting a device.
        self.status = 0

    ####################################################
    # The functions below here are meant to be overridden by child classes.
    ####################################################

    def energy_calc(self, **kwargs):
        """
        Returns the energy being used based on a percentage the device is on.  Inspired by:
        http://stackoverflow.com/questions/1969240/mapping-a-range-of-values-to-another

        Supply the machine_status, machine_status_extra,and last command. If these are not supplied, it will
        be taken from teh device history.

        :param machine_status:
        :param map:
        :return:
        """
        # map = {
        #     0: 1,
        #     0.5: 100,
        #     1: 400,
        # }

        if 'machine_status' in kwargs:
            machine_status = kwargs['machine_status']
        else:
            machine_status = self.status_history[0]['machine_status']

        if machine_status is None:
            raise ValueError("Machine status cannot be none.")

        if self.energy_tracker_source != 'calc':
            return [0, self.energy_type]

        if self.energy_map == None:
            return [0, self.energy_type]  # if no map is found, we always return 0

        items = list(self.energy_map.items())
        for i in range(0, len(self.energy_map) - 1):
            if items[i][0] <= machine_status <= items[i + 1][0]:
                # print "translate(key, items[counter][0], items[counter+1][0], items[counter][1], items[counter+1][1])"
                # print "%s, %s, %s, %s, %s" % (key, items[counter][0], items[counter+1][0], items[counter][1], items[counter+1][1])
                value = self.energy_translate(machine_status, items[i][0], items[i + 1][0], items[i][1],
                                              items[i + 1][1])
                return [value, self.energy_type]
        raise ValueError("Unable to determine enery usage.")


    def can_toggle(self):
        """
        If a device is toggleable, return True. It's toggleable if a device only has two commands.
        :return:
        """
        if self.TOGGLE_COMMANDS is False:
            return False

        available_commands = self.available_commands()
        if len(available_commands) == 2:
            return True
        else:
            return False

    def is_dimmable(self):
        return self.SUPPORT_BRIGHTNESS

    def is_on(self):
        if self.status_history[0].machine_status > 0:
            return True
        else:
            return False

    def is_off(self):
        return not self.is_on()

    def toggle(self):
        return self.command('toggle')
