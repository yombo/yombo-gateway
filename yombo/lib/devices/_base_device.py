# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_

Base device functions. Should not be directly inherited by other device types, instead
inherit 'Device' from _device.py.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from collections import deque, OrderedDict
from datetime import datetime
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboPinCodeError, YomboWarning
from yombo.core.log import get_logger
from yombo.utils import random_string, global_invoke_all, do_search_instance
from yombo.lib.commands import Command  # used only to determine class type
from ._device_command import Device_Command
from ._device_status import Device_Status
logger = get_logger('library.devices.device')

class Base_Device(object):
    """
    The base device contains all the core functions for devices. This calls should only be
    inherited by 'Device' class.

    The primary functions developers should use are:
        * :py:meth:`available_commands <Device.available_commands>` - List available commands for a device.
        * :py:meth:`command <Device.command>` - Send a command to a device.
        * :py:meth:`device_command_received <Device.device_command_received>` - Called by any module processing a command.
        * :py:meth:`device_command_pending <Device.device_command_pending>` - When a module needs more time.
        * :py:meth:`device_command_failed <Device.device_command_failed>` - When a module is unable to process a command.
        * :py:meth:`device_command_done <Device.device_command_done>` - When a command has completed..
        * :py:meth:`energy_get_usage <Device.energy_get_usage>` - Get current energy being used by a device.
        * :py:meth:`get_status <Device.get_status>` - Get a latest device status object.
        * :py:meth:`set_status <Device.set_status>` - Set the device status.
    """
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
        :ivar created_at: *(int)* - When the device was created; in seconds since EPOCH.
        :ivar updated_at: *(int)* - When the device was last updated; in seconds since EPOCH.
        :ivar status_history: *(dict)* - A dictionary of strings for current and up to the last 30 status values.
        :ivar device_variables_cached: *(dict)* - The device variables as defined by various modules, with
            values entered by the user.
        :ivar available_commands: *(list)* - A list of command_id's that are valid for this device.
        """
        self._FullName = 'yombo.gateway.lib.Devices.Device'
        self._Name = 'Devices.Device'
        self._Parent = _Parent
        self.gateway_id = _Parent.gateway_id
        self.call_before_command = []
        self.call_after_command = []
        self._security_send_device_status = self._Configs.get2("security", "amqpsenddevicestatus", True)

        self.device_id = device["id"]
        if test_device is None:
            self.test_device = False
        else:
            self.test_device = test_device

        memory_sizing = {
            'x_small': {'other_device_commands': 2,  #less then 256mb
                           'other_status_history': 2,
                           'local_device_commands': 5,
                           'local_status_history': 5},
            'small': {'other_device_commands': 5,  #About 512mb
                           'other_status_history': 5,
                           'local_device_commands': 25,
                           'local_status_history': 25},
            'medium': {'other_device_commands': 25,  # About 1024mb
                      'other_status_history': 25,
                      'local_device_commands': 75,
                      'local_status_history': 75},
            'large': {'other_device_commands': 50,  # About 2048mb
                       'other_status_history': 50,
                       'local_device_commands': 125,
                       'local_status_history': 125},
            'x_large': {'other_device_commands': 100,  # About 4092mb
                      'other_status_history': 100,
                      'local_device_commands': 250,
                      'local_status_history': 250},
            'xx_large': {'other_device_commands': 200,  # About 8000mb
                        'other_status_history': 200,
                        'local_device_commands': 500,
                        'local_status_history': 500},
        }

        sizes = memory_sizing[self._Parent._Atoms['mem.sizing']]
        if device["gateway_id"] != self.gateway_id:
            self.device_commands = deque({}, sizes['other_device_commands'])
            self.status_history = deque({}, sizes['other_status_history'])
        else:
            self.device_commands = deque({}, sizes['local_device_commands'])
            self.status_history = deque({}, sizes['local_status_history'])

        self.device_variables_cached = {}
        # self.device_variables = self.device_variables
        # self.device_variables = partial(self.device_variables)

        #The following items are set from the databsae, module, or AMQP service.
        self.device_type_id = None
        self.gateway_id = None
        self.location_id = None
        self.area_id = None
        self.machine_label = None
        self.label = None
        self.description = None
        self.pin_required = None
        self.pin_code = None
        self.pin_timeout = None
        self.voice_cmd = None
        self.voice_cmd_order = None
        self.statistic_label = None
        self.statistic_type = None
        self.statistic_bucket_size = None
        self.statistic_lifetime = None
        self.enabled_status = None  # not to be confused for device state. see status_history
        self.created_at = None
        self.updated_at = None
        self.energy_tracker_device = None
        self.energy_tracker_source = None
        self.energy_map = None
        self.energy_type = None
        self.device_is_new = True
        self.device_serial = device["id"]
        self.device_mfg = "Yombo"
        self.device_model = "Yombo"

        self.update_attributes(device, source='parent')

    @inlineCallbacks
    def _init0_(self, **kwargs):
        """
        Performs items that require deferreds. This is for system use only.

        :return:
        """
        yield self.device_variables()
        self.device_variables_cached = yield self._Parent._Variables.get_variable_fields_data(
            group_relation_type='device_type',
            group_relation_id=self.device_type_id,
            data_relation_id=self.device_id
        )
        if self.test_device is None or self.test_device is False:
            self.meta = yield self._SQLDict.get('yombo.lib.device', 'meta_' + self.device_id)
        else:
            self.meta = {}

        yield self._Parent._DeviceTypes.ensure_loaded(self.device_type_id)

        if self.test_device is False and self.device_is_new is True:
            self.device_is_new = False
            yield self.load_status_history(35)
            yield self.load_device_commands_history(35)

    def _init_(self, **kwargs):
        """
        Used by devices to run their init. This is called after the system _init0_ is called.

        :return:
        """
        pass

    def _start0_(self, **kwargs):
        """
        This is called by the devices library when a new device is loaded for system use only.

        :param kwargs:
        :return:
        """
        pass

    def _start_(self, **kwargs):
        """
        This is called by the devices library when a new device is loaded and is used by devices that need
        to run any start up items.

        :param kwargs:
        :return:
        """
        pass

    def _unload_(self, **kwargs):
        """
        About to unload. Lets save all the device status items.

        :param kwargs:
        :return:
        """
        for status in self.status_history:
            status.save_to_db()

    @inlineCallbacks
    def device_variables(self):
        self.device_variables_cached = yield self._Parent._Variables.get_variable_fields_data(
            group_relation_type='device_type',
            group_relation_id=self.device_type_id,
            data_relation_id=self.device_id
        )
        return self.device_variables_cached

    def update_attributes(self, device, source=None):
        """
        Sets various values from a device dictionary. This can be called when the device is first being setup or
        when being updated by the AMQP service.

        This does not set any device state or status attributes.
        :param device: 
        :return: 
        """
        if 'device_type_id' in device:
            self.device_type_id = device["device_type_id"]
        if 'gateway_id' in device:
            self.gateway_id = device["gateway_id"]
        if 'location_id' in device:
            self.location_id = device["location_id"]
        if 'area_id' in device:
            self.area_id = device["area_id"]
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
        if 'statistic_type' in device:
            self.statistic_type = device["statistic_type"]
        if 'statistic_bucket_size' in device:
            self.statistic_bucket_size = device["statistic_bucket_size"]
        if 'statistic_lifetime' in device:
            self.statistic_lifetime = device["statistic_lifetime"]
        if 'status' in device:
            self.enabled_status = int(device["status"])
        if 'created_at' in device:
            self.created_at = int(device["created_at"])
        if 'updated_at' in device:
            self.updated_at = int(device["updated_at"])
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
                if isinstance(device['energy_map'], dict) is False:
                    device['energy_map'] = {"0.0":0,"1.0":0}

                for percent, rate in device['energy_map'].items():
                    energy_map_final[self._Parent._InputTypes.check('percent', percent)] = self._Parent._InputTypes.check('number' , rate)
                energy_map_final = OrderedDict(sorted(list(energy_map_final.items()), key=lambda x_y: float(x_y[0])))
                self.energy_map = energy_map_final
            else:
                self.energy_map = None

        if self.device_is_new is True:
            global_invoke_all('_device_updated_',
                              called_by=self,
                              id=self.device_id,
                              device=self,
                              )

        if source != "parent":
            self._Parent.edit_device(device, source="node")

    def add_to_db(self):
        if self._Parent.gateway_id == self.gateway_id:
            self._Parent._LocalDB.add_device(self)

    def save_to_db(self):
        if self._Parent.gateway_id == self.gateway_id:
            self._Parent._LocalDB.update_device(self)

    @inlineCallbacks
    def get_variable_fields(self):
        variable_fields = self._Parent._DeviceTypes[self.device_type_id].get_variable_fields()
        return variable_fields

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
                            # print("got a list.. %s" % value)
                            if test_value not in value:
                                matches = False
                                break
                        else:
                            if test_value != value:
                                matches = False
                                break
                if matches:
                    results[id] = DC

            # if limit is not None and len(results) == limit:
            #     return results
        return results

    def available_commands(self):
        """
        Returns available commands for the current device.
        :return: 
        """
        return self._Parent._DeviceTypes.device_type_commands(self.device_type_id)

    def in_available_commands(self, command):
        """
        Checks if a command label, machine_label, or command_id is a possible command for the given device.
        :param command: 
        :return: 
        """
        self.commands.get(command, command_list=self.available_commands())

    def asdict(self):
        """
        Export device variables as a dictionary.
        """
        if len(self.status_history) > 0:
            status_current = self.status_history[0].asdict()
        else:
            status_current = None

        if len(self.status_history) > 1:
            status_previous = self.status_history[1].asdict()
        else:
            status_previous = None
        # print("device commands: %s" % self.device_commands)
        # out_device_commands = {}
        # for device_command_id in list(self.device_commands):
        #     command = self._Commands[device_command_id]
        #     out_device_commands[device_command_id] = {
        #         'machine_label': command['machine_label'],
        #         'label': command['label'],
        #     }
        return {
            'area': self.area,
            'location': self.location,
            'area_label': self.area_label,
            'full_label': self.full_label,
            'device_id': str(self.device_id),
            'device_type_id': str(self.device_type_id),
            'device_type_label': self._DeviceTypes[self.device_type_id].machine_label,
            'machine_label': str(self.machine_label),
            'label': str(self.label),
            'description': str(self.description),
            'statistic_label': str(self.statistic_label),
            'statistic_type': str(self.statistic_type),
            'statistic_bucket_size': str(self.statistic_bucket_size),
            'statistic_lifetime': str(self.statistic_lifetime),
            'pin_code': "********",
            'pin_required': int(self.pin_required),
            'pin_timeout': self.pin_timeout,
            'voice_cmd': str(self.voice_cmd),
            'voice_cmd_order': str(self.voice_cmd_order),
            'created_at': int(self.created_at),
            'updated_at': int(self.updated_at),
            'device_commands': list(self.device_commands),
            'status_current': status_current,
            'status_previous': status_previous,
            'device_serial': self.device_serial,
            'device_mfg': self.device_mfg,
            'device_model': self.device_model,
            'device_platform': self.PLATFORM,
            'device_sub_platform': self.SUB_PLATFORM,
            'device_features': self.FEATURES,
            'device_variables': self.device_variables_cached,
            'enabled_status': self.enabled_status,
            }

    def to_mqtt_coms(self):
        """
        Export device variables as a dictionary.
        """
        # def take(n, iterable):
        #     return list(islice(iterable, n))

        if len(self.device_commands) > 0:
            request_id = self.device_commands[0]
            device_command = self._Parent.device_commands[request_id].asdict()
        else:
            device_command = []

        if len(self.status_history) > 0:
            status_history = self.status_history[0].asdict()
        else:
            status_history = None

        return {
            'device_id': str(self.device_id),
            'device_command': device_command,
            'status_history': status_history,
            }

    def command(self, cmd, pin=None, request_id=None, not_before=None, delay=None, max_delay=None,
                requested_by=None, inputs=None, not_after=None, callbacks=None, **kwargs):
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
        :param request_id: Request ID for tracking. If none given, one will be created_at.
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
        if self.enabled_status != 1:
            raise YomboWarning("Device cannot be used, it's not enabled.")

        if self.pin_required == 1:
            if pin is None:
                raise YomboPinCodeError("'pin' is required, but missing.")
            else:
                if self.pin_code != pin:
                    raise YomboPinCodeError("'pin' supplied is incorrect.")
        device_command = {
            "device": self,
            "pin": pin,
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
            }
        device_command['requested_by'] = requested_by

        if str(command.command_id) not in self.available_commands():
            logger.warn("Requested command: {command_id}, but only have: {ihave}",
                        command_id=command.command_id, ihave=self.available_commands())
            raise YomboWarning("Invalid command requested for device.", errorno=103)

        cur_time = time()
        device_command['created_at'] = cur_time

        persistent_request_id = kwargs.get('persistent_request_id', None)
        device_command['persistent_request_id'] = persistent_request_id

        if persistent_request_id is not None:  # cancel any previous device requests for this persistent id.
            for search_request_id, search_device_command in self._Parent.device_commands.items():
                if search_device_command.persistent_request_id == persistent_request_id:
                    search_device_command.cancel(message="This device command was superseded by a new persistent request.")

        if request_id is None:
            request_id = random_string(length=18)  # print("in device command: request_id 2: %s" % request_id)

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
        else:
            for input_label, input_value in inputs.items():
                # print("checking input: %s (%s)" % (input_label, type(input_label)))
                try:
                    inputs[input_label] = self._Parent._DeviceTypes.validate_command_input(self.device_type_id, command.command_id, input_label, input_value)
                    # print("checking input: %s (%s)" % (input_label, type(input_label)))
                except Exception as e:
                    # print("error checking input value: %s" % e)
                    pass
        device_command['inputs'] = inputs
        if callbacks is not None:
            device_command['callbacks'] = callbacks

        self.device_commands.appendleft(request_id)

        self._Parent.add_device_command_by_object(Device_Command(device_command, self._Parent))
        return request_id

    @inlineCallbacks
    def _do_command_hook(self, device_command):
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
            'device_id': self.device_id,
            'command_id': device_command.command.command_id,
            'command': device_command.command,
            'device': self,
            'inputs': device_command.inputs,
            'request_id': device_command.request_id,
            'device_command': device_command,
            'requested_by': device_command.requested_by,
            'called_by': self,
            'pin': device_command.pin,
            'stoponerror': False,
        }
        # logger.debug("calling _device_command_, request_id: {request_id}", request_id=device_command.request_id)
        # print(self._Parent.device_commands)
        device_command.set_broadcast()
        results = yield global_invoke_all('_device_command_', **items)
        for component, result in results.items():
            if result is True:
                device_command.set_received(message="Received by: %s" % component,)
        self._Parent._Statistics.increment("lib.devices.commands_sent", anon=True)

    def device_command_processing(self, request_id, **kwargs):
        """
        A shortcut to calling device_comamnd_sent and device_command_received together.

        This will trigger two calls of the same hook "_device_command_status_". Once for status
        of 'received' and another for 'sent'.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get('message', None)
        log_time = kwargs.get('log_time', None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_sent(message=message, sent_at=log_time)
            global_invoke_all('_device_command_status_',
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              )
            device_command.set_received(message=message, received_at=log_time)
            global_invoke_all('_device_command_status_',
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              )
        else:
            return

    def device_command_accepted(self, request_id, **kwargs):
        """
        Called by any module that accepts the command for processing.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get('message', None)
        log_time = kwargs.get('log_time', None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_accepted(message=message, accepted_at=log_time)
            global_invoke_all('_device_command_status_',
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              )
        else:
            return

    def device_command_sent(self, request_id, **kwargs):
        """
        Called by any module that has sent the command to an end-point.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get('message', None)
        log_time = kwargs.get('log_time', None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_sent(message=message, sent_at=log_time)
            global_invoke_all('_device_command_status_',
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              )
        else:
            return

    def device_command_received(self, request_id, **kwargs):
        """
        Called by any module that intends to process the command and deliver it to the automation device.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get('message', None)
        log_time = kwargs.get('log_time', None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_received(message=message, received_at=log_time)
            global_invoke_all('_device_command_status_',
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              )
        else:
            return

    def device_command_pending(self, request_id, **kwargs):
        """
        This should only be called if command processing takes more than 1 second to complete. This lets applications,
        users, and everyone else know it's pending. Calling this excessively can cost a lot of local CPU cycles.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get('message', None)
        log_time = kwargs.get('log_time', None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_pending(message=message, pending_at=log_time)
            global_invoke_all('_device_command_status_',
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              )
        else:
            return

    def device_command_failed(self, request_id, **kwargs):
        """
        Should be called when a the command cannot be completed for whatever reason.

        A status can be provided: send a named parameter of 'message' with any value.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get('message', None)
        log_time = kwargs.get('log_time', None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_failed(message=message, finished_at=log_time)
            if message is not None:
                logger.warn('Device ({label}) command failed: {message}', label=self.label, message=message,
                            state='failed')
            global_invoke_all('_device_command_status_',
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              )
        else:
            return

    def device_command_cancel(self, request_id, **kwargs):
        """
        Cancel a device command request. Cannot guarentee this will happen. Unable to cancel if status is 'done' or
        'failed'.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        log_time = kwargs.get('log_time', None)
        message = kwargs.get('message', None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_canceled(message=message, finished_at=log_time)
            if message is not None:
                logger.debug('Device ({label}) command failed: {message}', label=self.label, message=message)
            global_invoke_all('_device_command_status_',
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              )
        else:
            return

    def device_delay_expired(self, request_id, **kwargs):
        """
        This is called on system bootup when a device command was set for a delayed execution,
        but the time limit for executing the command has elasped.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        log_time = kwargs.get('log_time', None)
        message = kwargs.get('message', None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_delay_expired(message=message, finished_at=log_time)
            if message is not None:
                logger.debug('Device ({label}) command failed: {message}', label=self.label, message=message)
            global_invoke_all('_device_command_status_',
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              )
        else:
            return


    def device_command_done(self, request_id, **kwargs):
        """
        Called by any module that has completed processing of a command request.

        A status can be provided: send a named parameter of 'message' with any value.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get('message', None)
        log_time = kwargs.get('log_time', None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_finished(message=message, finished_at=log_time)
            global_invoke_all('_device_command_status_',
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              )
        else:
            return

    def get_request(self, request_id):
        """
        Returns a request instance for a provided request_id.

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

    def get_device_commands(self, history=0):
        """
        Gets the last command information.

        :param history: How far back to go. 0 = previoius, 1 - the one before that, etc.
        :return:
        """
        return self.device_commands[history]

    def set_status_process(self, **kwargs):
        """
        A place for modules to process any status updates. Make any last minute changes before it's saved and
        distributed.

        :param kwargs:
        :return:
        """
        if len(self.status_history) == 0:
            previous_extra = {}
        else:
            previous_extra = self.status_history[0].machine_status_extra

        if isinstance(previous_extra, dict) is False:
            previous_extra = {}

        new_extra = kwargs.get('machine_status_extra', {})
        for key, value in new_extra.items():
            previous_extra[key] = value

        kwargs['machine_status_extra'] = previous_extra
        return kwargs

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
        kwargs = self.set_status_process(**kwargs)
        kwargs, status_id = self._set_status(**kwargs)
        # logger.info("set_status called...3: {kwargs}", kwargs=kwargs)
        if 'silent' not in kwargs:
            self.send_status(**kwargs)

    def generate_human_status(self, machine_status, machine_status_extra):
        return machine_status

    def generate_human_message(self, machine_status, machine_status_extra):
        return "%s is now %s" % (self.area_label, machine_status)

    def set_status_machine_extra(self, **kwargs):
        pass

    def _set_status(self, **kwargs):
        """
        A private function used to do the work of setting the status.
        :param kwargs: 
        :return: 
        """
        if 'machine_status' not in kwargs:
            raise YomboWarning("set_status was called without a real machine_status!", errorno=120)
        # logger.info("_set_status called...: {kwargs}", kwargs=kwargs)
        command = None
        machine_status = kwargs['machine_status']
        machine_status_extra = kwargs.get('machine_status_extra', {})
        human_status = kwargs.get('human_status', self.generate_human_status(machine_status, machine_status_extra))
        human_message = kwargs.get('human_message', self.generate_human_message(machine_status, machine_status_extra))
        uploaded = kwargs.get('uploaded', 0)
        uploadable = kwargs.get('uploadable', 1)
        set_at = kwargs.get('set_at', time())
        if 'gateway_id' not in kwargs:
            kwargs['gateway_id'] = self.gateway_id

        # logger.info("setting final machine_status_extra:  called...h: {machine_status_extra}",
        #             machine_status_extra=machine_status_extra)

        requested_by_default = {
            'user_id': 'Unknown',
            'component': 'Unknown',
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
        else:
            request_id = None
            requested_by = requested_by_default

        if command is None:
            if 'command' in kwargs:
                command = self._Parent._Commands[kwargs['command']]
            else:
                # print("trying to get command_from_Status")
                command = self.command_from_status(machine_status, machine_status_extra)
        else:
            # print("set status - command found!")
            kwargs['command'] = command

        energy_usage, energy_type = self.energy_calc(command=command,
                                                     machine_status=machine_status,
                                                     machine_status_extra=machine_status_extra,
                                                     )

        kwargs['request_id'] = request_id
        kwargs['requested_by'] = requested_by

        reported_by = kwargs.get('reported_by', 'Unknown')
        kwargs['reported_by'] = reported_by

        if self.statistic_type not in (None, "", "None", "none"):
            if self.statistic_type.lower() == "datapoint" or self.statistic_type.lower() == "average":
                statistic_label_slug = self.statistic_label_slug
            if self.statistic_type.lower() == "datapoint":
                self._Parent._Statistics.datapoint("devices.%s" % statistic_label_slug, machine_status)
                if self.energy_type not in (None, "", "none", "None"):
                    self._Parent._Statistics.datapoint("energy.%s" % statistic_label_slug, energy_usage)
            elif self.statistic_type.lower() == "average":
                self._Parent._Statistics.averages("devices.%s" % statistic_label_slug, machine_status, int(self.statistic_bucket_size))
                if self.energy_type not in (None, "", "none", "None"):
                    self._Parent._Statistics.averages("energy.%s" % statistic_label_slug, energy_usage, int(self.statistic_bucket_size))

        new_status = Device_Status(self._Parent, self, {
            'command': command,
            'set_at': set_at,
            'energy_usage': energy_usage,
            'energy_type': energy_type,
            'human_status': human_status,
            'human_message': human_message,
            'machine_status': machine_status,
            'machine_status_extra': machine_status_extra,
            'gateway_id': kwargs['gateway_id'],
            'requested_by': requested_by,
            'reported_by': reported_by,
            'request_id': request_id,
            'uploaded': uploaded,
            'uploadable': uploadable,
            }
        )

        self.status_history.appendleft(new_status)
        self.set_status_machine_extra(**kwargs)

        if self._security_send_device_status() is True:
            # print("SHOULD SEND UPDATED DEVIE STATUS!!!!!!")
            request_msg = self._Parent._AMQPYombo.generate_message_request(
                exchange_name='ysrv.e.gw_device_status',
                source='yombo.gateway.lib.devices.base_device',
                destination='yombo.server.device_status',
                body={
                    'status_set_at': datetime.fromtimestamp(time()).strftime("%Y-%m-%d %H:%M:%S.%f"),
                    'device_id': self.device_id,
                    'energy_usage': energy_usage,
                    'energy_type': energy_type,
                    'human_status': human_status,
                    'human_message': human_message,
                    'machine_status': machine_status,
                    'machine_status_extra': machine_status_extra,
                },
                request_type='save_device_status',
            )
            self._Parent._AMQPYombo.publish(**request_msg)
        # if self.test_device is False:
        #     save_status = new_status.asdict()
        #     save_status['machine_status_extra'] = data_pickle(save_status['machine_status_extra'])
        #     save_status['requested_by'] = data_pickle(save_status['requested_by'])
        #     # print("requested by before: %s" % save_status['requested_by'])
        #     # print("requested by after: %s" % save_status['requested_by'])
        #     self._Parent._LocalDB.add_bulk_queue('device_status', 'insert', save_status, 'device_id')
        self._Parent.check_trigger(self.device_id, new_status)

        if self._Parent.mqtt != None:
            mqtt_message = {
                'device_id': self.device_id,
                'device_machine_label': self.machine_label,
                'device_label': self.label,
                'machine_status': machine_status,
                'machine_status_extra': machine_status_extra,
                'human_message': human_message,
                'human_status': human_status,
                'time': set_at,
                'gateway_id': kwargs['gateway_id'],
                'requested_by': requested_by,
                'reported_by': reported_by,
                'energy_usage': energy_usage,
                'energy_type': energy_type,
            }

            if command is not None:
                mqtt_message['command_id'] = command.command_id
                mqtt_message['command_machine_label'] = command.machine_label
            else:
                # print("set status - no command found!")
                mqtt_message['command_id'] = None
                mqtt_message['command_machine_label'] = None
            self._Parent.mqtt.publish("yombo/devices/%s/status" % self.machine_label, json.dumps(mqtt_message), 1)
        return kwargs, new_status['status_id']

    def set_status_from_gateway_communications(self, payload):
        """
        Used by the gateway library to directly inject a new device status.

        :param new_status:
        :return:
        """
        new_status = Device_Status(self._Parent, self, payload['status'])
        self.status_history.appendleft(new_status)
        # save_status = new_status.asdict()
        # save_status['requested_by'] = data_pickle(save_status['requested_by'])
        # save_status['machine_status_extra'] = data_pickle(save_status['machine_status_extra'])
        # if self.test_device is False and self._Parent.is_master is True:
        #     self._Parent._LocalDB.add_bulk_queue('device_status', 'insert', save_status, 'device_id')
        self._Parent.check_trigger(self.device_id, new_status)
        self.send_status(**payload)

    def send_status(self, **kwargs):
        """
        Sends current status. Use set_status() to set the status, it will call this method for you.

        Calls the _device_status_ hook to send current device status. Useful if you just want to send a status of
        a device without actually changing the status.

        :param kwargs:
        :return:
        """
        command_id = None
        command_label = None
        command_machine_label = None
        if 'command' in kwargs:
            command = kwargs['command']
            if isinstance(command, str):
                try:
                    command = self._Parent._Commands[command]
                except Exception as e:
                    command = None
        elif 'command_id' in kwargs:
            try:
                command = self._Parent._Commands[kwargs['command_id']]
            except Exception as e:
                command = None
        else:
            command = None

        if command is not None:
            command_id = command.command_id
            command_label = command.label
            command_machine_label = command.machine_label

        try:
            previous_status = self.status_history[1].asdict()
        except Exception as e:
            previous_status = None
        device_type = self._Parent._DeviceTypes[self.device_type_id]

        message = {
            'device': self,
            'command': command,
            'request_id': kwargs.get('request_id', None),
            'reported_by': kwargs.get('reported_by', None),
            'gateway_id': kwargs.get('gateway_id', self.gateway_id),
            'event': {
                'area': self.area,
                'location': self.location,
                'area_label': self.area_label,
                'full_label': self.full_label,
                'device_id': self.device_id,
                'device_label': self.label,
                'device_machine_label': self.machine_label,
                'device_type_id': self.device_type_id,
                'device_type_label': device_type.machine_label,
                'device_type_machine_label': device_type.machine_label,
                'command_id': command_id,
                'command_label': command_label,
                'command_machine_label': command_machine_label,
                'status_current': self.status_history[0].asdict(),
                'status_previous': previous_status,
                'gateway_id': kwargs.get('gateway_id', self.gateway_id),
                'device_features': self.FEATURES,
            },
        }

        if len(self.status_history) == 1:
            message['previous_status'] = None
        else:
            message['previous_status'] = self.status_history[1]

        global_invoke_all('_device_status_',
                          called_by=self,
                          **message,
                          )

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
    def load_status_history(self, limit=40):
        """
        Loads device history into the device instance. This method gets the
         data from the db to actually set the values.

        :param limit: int - How many history items should be loaded. Default: 40
        :return:
        """
        if limit is None:
            limit = False

        where = {
            'device_id': self.device_id,
        }
        records = yield self._Parent._Libraries['LocalDB'].get_device_status(where, limit=limit)
        if len(records) > 0:
            for record in records:
                self.status_history.appendleft(Device_Status(self._Parent, self, record, source='database'))

    @inlineCallbacks
    def load_device_commands_history(self, limit=40):
        """
        Loads device command history into the device instance. This method gets the
        data from the db to actually set the values.

        :param limit: int - How many history items should be loaded. Default: 40
        :return:
        """
        if limit is None:
            limit = False

        where = {
            'id': self.device_id,
        }
        records = yield self._Parent._Libraries['LocalDB'].get_device_commands(where, limit=limit)
        if len(records) > 0:
            for record in records:
                if record['request_id'] not in self._Parent.device_commands:
                    self._Parent.add_device_command_by_object(Device_Command(record, self, start=False))

    def validate_command(self, command_requested):
        available_commands = self.available_commands()
        if command_requested in available_commands:
            return available_commands[command_requested]
        else:
            commands = {}
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

    def delete(self, called_by_parent=None):
        """
        Called when the device should delete itself.

        :return: 
        """
        if called_by_parent is not True:
            self._Parent.delete_device(self.device_id, True)
        self._Parent._LocalDB.set_device_status(self.device_id, 2)
        self.enabled_status = 2

    def enable(self, called_by_parent=None):
        """
        Called when the device should enable itself.

        :return:
        """
        if called_by_parent is not True:
            self._Parent.enable_device(self.device_id, True)
        self._Parent._LocalDB.set_device_status(self.device_id, 1)

        self.enabled_status = 1

    def disable(self, called_by_parent=None):
        """
        Called when the device should disable itself.

        :return:
        """
        if called_by_parent is not True:
            self._Parent.disable_device(self.device_id, True)
        self._Parent._LocalDB.set_device_status(self.device_id, 0)
        self.enabled_status = 0

    def add_features(self, features):
        """
        Adds additional features to a device.

        :param features: A dictionary of additional features.
        :return:
        """
        for feature in features:
            self.FEATURES[feature[0]] = feature[1]

    def delete_features(self, features):
        """
        Removes features from a device. Accepts a list or a string for a single item.

        :param features: A list of features to remove from device.
        :return:
        """
        if isinstance(features, list):
            for feature in features:
                del self.FEATURES[feature[0]]
        else:
            del self.FEATURES[features]

    def add_status_extra_allow(self, status, values):
        if status not in self.STATUS_EXTRA:
            self.STATUS_EXTRA[status] = []
        else:
            if isinstance(self.STATUS_EXTRA[status], list) is False:
                self.STATUS_EXTRA[status] = []

        if isinstance(values, list):
            for value in values:
                self.STATUS_EXTRA[status].append(value)
        else:
            self.STATUS_EXTRA[status].append(values)

    def add_status_extra_any(self, items):
        for item in items:
            self.STATUS_EXTRA[item] = True

    def delete_status_extra(self, items):
        if isinstance(items, list):
            for item in items:
                del self.FEATURES[item]
        else:
            del self.FEATURES[items]
