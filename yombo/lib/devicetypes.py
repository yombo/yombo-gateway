# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Device Type @ Module Development <https://yombo.net/docs/modules/device_types/>`_

This is a simple helper library to manage device type mapping. This is a mapping between modules, device types,
and commands.

This library keeps track of what modules can access what device types, and what commands those device types can perform.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
"""
import inspect

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue

# Import Yombo libraries
from yombo.utils.decorators import memoize_ttl
from yombo.core.exceptions import YomboFuzzySearchError, YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils.fuzzysearch import FuzzySearch
from yombo.utils import search_instance, do_search_instance, global_invoke_all
import collections
from functools import reduce

logger = get_logger('library.devicetypes')

BASE_PLATFORMS = [
    ['yombo.lib.devices._device', 'Device'],
    ['yombo.lib.devices.appliance', 'Appliance'],
    ['yombo.lib.devices.light', 'Light'],
    ['yombo.lib.devices.relay', 'Relay'],
]


class DeviceTypes(YomboLibrary):
    """
    Manages device type database tabels. Just simple update a module's device types or device type's available commands
    and any required database tables are updated. Also maintains a list of module device types and device type commands
    in memory for access.
    """
    def __contains__(self, device_type_requested):
        """
        .. note:: The device type must be enabled to be found using this method. Use :py:meth:`get <DeviceTypes.get>`
           to set status allowed.

        Checks to if a provided device type id, label, or machine_label exists.

        Simulate a dictionary when requested with:

            >>> if 'SDjs2a01k7czf12' in self._DeviceTypes:  #by id

        or:

            >>> if 'x10_appliance' in self._DeviceTypes:  #by label

        :raises YomboWarning: Raised when request is malformed.
        :param device_type_requested: The device type ID, label, or machine_label to search for.
        :type device_type_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(device_type_requested)
            return True
        except:
            return False

    def __getitem__(self, device_type_requested):
        """
        .. note:: The device type must be enabled to be found using this method. Use :py:meth:`get <DeviceTypes.get>`
           to set status allowed.

        Attempts to find the device type requested using a couple of methods.

        Simulate a dictionary when requested with:

            >>> my_light = self._Devices['SDjs2a01k7czf12']  #by id

        or:

            >>> my_light = self._Devices['x10_appliance']  #by name

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param device_type_requested: The device type ID, label, or machine_label to search for.
        :type device_type_requested: string
        :return: A pointer to the device type instance.
        :rtype: instance
        """
        return self.get(device_type_requested)

    def __setitem__(self, device_type_requested, value):
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
        """ iter device_types. """
        return self.device_types.__iter__()

    def __len__(self):
        """
        Returns an int of the number of device types configured.

        :return: The number of device types configured.
        :rtype: int
        """
        return len(self.device_types)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo device types library"

    def keys(self):
        """
        Returns the keys (device type ID's) that are configured.

        :return: A list of device types IDs. 
        :rtype: list
        """
        return list(self.device_types.keys())

    def items(self):
        """
        Gets a list of tuples representing the device types configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.device_types.items())

    def iteritems(self):
        return iter(self.device_types.items())

    def iterkeys(self):
        return iter(self.device_types.keys())

    def itervalues(self):
        return iter(self.device_types.values())

    def values(self):
        return list(self.device_types.values())

    def _init_(self, **kwargs):
        """
        Sets up basic attributes.
        """
        self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.
        self.device_types = {}
        self.device_type_search_attributes = ['device_type_id', 'input_type_id', 'category_id', 'label', 'machine_label', 'description',
            'status', 'always_load', 'public']
        self.platforms = {}  # This is filled in lib.modules::do_import_modules

    def _load_(self, **kwargs):
        """
        Loads device types from the database and imports them.
        
        :return: 
        """
        self.load_deferred = Deferred()
        self._load_device_types_from_database()
        return self.load_deferred

    @inlineCallbacks
    def _start_(self, **kwargs):
        self.load_platforms(BASE_PLATFORMS)
        platforms = yield global_invoke_all('_device_platforms_', called_by=self)
        for component, item in platforms.items():
            self.load_platforms(item)

    def _stop_(self, **kwargs):
        """
        Cleans up any pending deferreds.
        """
        if self.load_deferred is not None and self.load_deferred.called is False:
            self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    @inlineCallbacks
    def _load_device_types_from_database(self):
        """
        Loads device types from database and sends them to
        :py:meth:`import_device_types <DeviceTypes.import_device_types>`

        This can be triggered either on system startup or when new/updated device types have been saved to the
        database and we need to refresh existing device types.
        """
        device_types = yield self._LocalDB.get_device_types()
        logger.debug("device_types: {device_types}", device_types=device_types)
        for device_type in device_types:
            yield self.import_device_types(device_type)
        self.load_deferred.callback(10)

    def load_platforms(self, platforms):
        """
        Load the platforms and prep them for usage.

        :param platforms: 
        :return: 
        """
        # print("platforms: %s" % platforms)
        for item in platforms:
            item_key = item[1].lower()
            if item_key.startswith('_'):
                item_key = item_key[1:]
            # print(" item_key2: %s" % type(item_key))

            module_root = __import__(item[0], globals(), locals(), [], 0)
            module_tail = reduce(lambda p1, p2: getattr(p1, p2), [module_root, ] + item[0].split('.')[1:])
            klass = getattr(module_tail, item[1])
            if not isinstance(klass, collections.Callable):
                logger.warn("Unable to load device platform '{name}', it's not callable.", name=item[1])
                continue
            self.platforms[item_key] = klass

    @inlineCallbacks
    def import_device_types(self, device_type, test_device_type=False):
        """
        Add a new device types to memory or update an existing device types.

        **Hooks called**:

        * _device_type_before_load_ : If added, sends device type dictionary as 'device_type'
        * _device_type_before_update_ : If updated, sends device type dictionary as 'device_type'
        * _device_type_loaded_ : If added, send the device type instance as 'device_type'
        * _device_type_updated_ : If updated, send the device type instance as 'device_type'

        :param device_type: A dictionary of items required to either setup a new device type or update an existing one.
        :type device: dict
        :param test_device_type: Used for unit testing.
        :type test_device_type: bool
        :returns: Pointer to new device. Only used during unittest
        """
        logger.debug("device_type: {device_type}", device_type=device_type)

        global_invoke_all('_device_types_before_import_', called_by=self, **{'device_type': device_type})
        device_type_id = device_type["id"]
        if device_type_id not in self.device_types:
            global_invoke_all('_device_type_before_load_', called_by=self, **{'device_type': device_type})
            self.device_types[device_type_id] = DeviceType(device_type, self)
            yield self.device_types[device_type_id]._init_()
            global_invoke_all('_device_type_loaded_',
                              called_by=self,
                              **{'device_type': self.device_types[device_type_id]})
        elif device_type_id not in self.device_types:
            global_invoke_all('_device_type_before_update_', called_by=self, **{'device_type': device_type})
            self.device_types[device_type_id].update_attributes(device_type)
            yield self.device_types[device_type_id]._init_()
            global_invoke_all('_device_type_updated_',
                              called_by=self,
                              **{'device_type': self.device_types[device_type_id]})

    def get(self, device_type_requested, limiter=None, status=None):
        """
        Performs the actual search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find devices:

            >>> self._DeviceTypes['13ase45']

        or:

            >>> self._DeviceTypes['numeric']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param device_type_requested: The device type ID or device type label to search for.
        :type device_type_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the device type to check for.
        :type status: int
        :return: Pointer to requested device type.
        :rtype: dict
        """
        if inspect.isclass(device_type_requested):
            if isinstance(device_type_requested, DeviceType):
                return device_type_requested
            else:
                raise ValueError("Passed in an unknown object")

        if limiter is None:
            limiter = .89

        if limiter > .99999999:
            limiter = .99
        elif limiter < .10:
            limiter = .10

        if device_type_requested in self.device_types:
            item = self.device_types[device_type_requested]
            if status is not None and item.status != status:
                raise KeyError("Requested device type found, but has invalid status: %s" % item.status)
            return item
        else:
            attrs = [
                {
                    'field': 'device_type_id',
                    'value': device_type_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'label',
                    'value': device_type_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'machine_label',
                    'value': device_type_requested,
                    'limiter': limiter,
                }
            ]
            try:
                logger.debug("Get is about to call search...: %s" % device_type_requested)
                # found, key, item, ratio, others = self._search(attrs, operation="highest")
                found, key, item, ratio, others = do_search_instance(attrs, self.device_types,
                                                                     self.device_type_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest")
                logger.debug("found device type by search: {device_type_id}", device_type_id=key)
                if found:
                    return item
                else:
                    raise KeyError("Device type not found: %s" % device_type_requested)
            except YomboWarning as e:
                raise KeyError('Searched for %s, but had problems: %s' % (device_type_requested, e))

    def search(self, _limiter=None, _operation=None, **kwargs):
        """
        Search for device type based on attributes for all device types.

        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :return: 
        """
        return search_instance(kwargs,
                               self.device_types,
                               self.device_type_search_attributes,
                               _limiter,
                               _operation)

    @inlineCallbacks
    def ensure_loaded(self, device_type_id):
        """
        Called by the device class to make sure the requsted device type id is loaded. This happens in
        the background.

        :param device_type_id:
        :return:
        """
        if device_type_id not in self.device_types:
            device_type = yield self._LocalDB.get_device_type(device_type_id)
            yield self.import_device_types(device_type[0])

    def devices_by_device_type(self, requested_device_type):
        """
        A list of devicess for a given device type.

        :raises YomboWarning: Raised when module_id is not found.
        :param requested_device_type: A device type by either ID or Label.
        :return: A dictionary of devices for a given device type.
        :rtype: list
        """
        device_type = self.get(requested_device_type)
        return device_type.get_devices()

    def device_type_commands(self, device_type_id):
        """
        A list of commands for a given device type.

        :raises YomboWarning: Raised when device_type_id is not found.
        :param device_type_id: The Device Type ID to return device types for.
        :return: A list of command id's.
        :rtype: list
        """
        if device_type_id in self.device_types:
            return self.device_types[device_type_id].commands
        else:
            raise YomboWarning("Device type id doesn't exist: %s" % device_type_id, 200,
                'device_type_commands', 'DeviceTypes')

    def get_local_devicetypes(self):
        """
        Return a dictionary with all the public device types.

        :return:
        """
        results = {}
        for item_id, item in self.device_types.items():
            if item.public <= 1:
                results[item_id] = item
        return results

    def get_public_devicetypes(self):
        """
        Return a dictionary with all the public device types.

        :return:
        """
        results = {}
        for item_id, item in self.device_types.items():
            if item.public == 2:
                results[item_id] = item
        return results

    def validate_command_input(self, device_type_id, command_id, dtc_machine_label, value):
        """
        Validates an input value.
        :param device_type_id:
        :param command_id:
        :param dtc_machine_label: 
        :return:
        """
        if device_type_id not in self.device_types:
            raise KeyError("Device Type Id not found.")
        if command_id not in self.device_types[device_type_id].commands:
            raise KeyError("Command ID not found in specified device type id.")
        if dtc_machine_label not in self.device_types[device_type_id].commands[command_id]['inputs']:
            raise KeyError("machine label not found in specified command_id for the provided device type id.")

        input_type_id = self.device_types[device_type_id].commands[command_id]['inputs'][dtc_machine_label]['input_type_id']
        return self._InputTypes[input_type_id].validate(value)

    @inlineCallbacks
    def dev_device_type_add(self, data, **kwargs):
        """
        Add a module at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        try:
            for key in list(data.keys()):
                if data[key] == "":
                    data[key] = None
                elif key in ['status']:
                    if data[key] is None or (isinstance(data[key], str) and data[key].lower() == "none"):
                        del data[key]
                    else:
                        data[key] = int(data[key])
        except Exception as e:
            results = {
                'status': 'failed',
                'msg': "Couldn't add device type",
                'apimsg': e,
                'apimsghtml': e,
                'device_id': '',
            }
            returnValue(results)

        device_type_results = yield self._YomboAPI.request('POST', '/v1/device_type', data)
        # print("dt_results: %s" % device_type_results)

        if device_type_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't add device type",
                'apimsg': device_type_results['content']['message'],
                'apimsghtml': device_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Device type added.",
            'device_type_id': device_type_results['data']['id'],
        }
        returnValue(results)

    @inlineCallbacks
    def dev_device_type_edit(self, device_type_id, data, **kwargs):
        """
        Edit a module at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """

        try:
            for key in list(data.keys()):
                if data[key] == "":
                    data[key] = None
                elif key in ['status']:
                    if data[key] is None or (isinstance(data[key], str) and data[key].lower() == "none"):
                        del data[key]
                    else:
                        data[key] = int(data[key])
        except Exception as e:
            results = {
                'status': 'failed',
                'msg': "Couldn't add device type",
                'apimsg': e,
                'apimsghtml': e,
                'device_id': '',
            }
            returnValue(results)

        device_type_results = yield self._YomboAPI.request('PATCH', '/v1/device_type/%s' % (device_type_id), data)
        # print("module edit results: %s" % module_results)

        if device_type_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit device type",
                'apimsg': device_type_results['content']['message'],
                'apimsghtml': device_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Device type edited.",
            'device_type_id': device_type_results['data']['id'],
        }
        returnValue(results)

    @inlineCallbacks
    def dev_device_type_delete(self, device_type_id, **kwargs):
        """
        Delete a device_type at the Yombo server level, not at the local gateway level.

        :param device_type_id: The device_type ID to delete.
        :param kwargs:
        :return:
        """
        device_type_results = yield self._YomboAPI.request('DELETE', '/v1/device_type/%s' % device_type_id)

        if device_type_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete device type",
                'apimsg': device_type_results['content']['message'],
                'apimsghtml': device_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Device type deleted.",
            'device_type_id': device_type_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_device_type_enable(self, device_type_id, **kwargs):
        """
        Enable a device_type at the Yombo server level, not at the local gateway level.

        :param device_type_id: The device_type ID to enable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 1,
        }

        device_type_results = yield self._YomboAPI.request('PATCH', '/v1/device_type/%s' % device_type_id, api_data)

        if device_type_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't enable device type",
                'apimsg': device_type_results['content']['message'],
                'apimsghtml': device_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Device type enabled.",
            'device_type_id': device_type_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_device_type_disable(self, device_type_id, **kwargs):
        """
        Enable a device_type at the Yombo server level, not at the local gateway level.

        :param device_type_id: The device_type ID to disable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 0,
        }

        device_type_results = yield self._YomboAPI.request('PATCH', '/v1/device_type/%s' % device_type_id, api_data)

        if device_type_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable device_type",
                'apimsg': device_type_results['content']['message'],
                'apimsghtml': device_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Device type disabled.",
            'device_type_id': device_type_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_command_add(self, device_type_id, command_id, **kwargs):
        """
        Add a command to device type at the Yombo server level, not at the local gateway level.

        :param device_type_id: The device_type ID to enable.
        :param command_id: The command_id ID to add/associate.
        :param kwargs:
        :return:
        """
        api_data = {
            'device_type_id': device_type_id,
            'command_id': command_id,
        }

        device_type_results = yield self._YomboAPI.request('POST', '/v1/device_type_command', api_data)
        if device_type_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't associate command to device type",
                'apimsg': device_type_results['content']['message'],
                'apimsghtml': device_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Associated command to device type.",
            'device_type_id': device_type_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_command_input_add(self, device_type_id, command_id, input_type_id, data, **kwargs):
        """
        Associate an input type to a device type command at the Yombo server level, not at the local gateway level.

        :param device_type_id: The device_type ID to enable.
        :param command_id: The command_id ID to add/associate.
        :param kwargs:
        :return:
        """
        api_data = {
            'device_type_id': device_type_id,
            'command_id': command_id,
            'input_type_id': input_type_id,
            'label': data['label'],
            'machine_label': data['machine_label'],
            'encryption': data['encryption'],
            'value_casing': data['value_casing'],
            'live_update': data['live_update'],
            'value_required':  data['value_required'],
            'value_max':  data['value_max'],
            'value_min':  data['value_min'],
            'notes': data['notes'],
        }

        device_type_results = yield self._YomboAPI.request('POST', '/v1/device_command_input', api_data)
        if device_type_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't associate input to device type command",
                'apimsg': device_type_results['content']['message'],
                'apimsghtml': device_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Associated input to device type command",
            'device_type_id': device_type_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_command_input_edit(self, device_type_id, command_id, input_type_id, data, **kwargs):
        """
        Associate an input type to a device type command at the Yombo server level, not at the local gateway level.

        :param device_type_id: The device_type ID to enable.
        :param command_id: The command_id ID to add/associate.
        :param kwargs:
        :return:
        """
        api_data = {
            # 'device_type_id': device_type_id,
            # 'command_id': command_id,
            # 'input_type_id': input_type_id,
            'label': data['label'],
            'machine_label': data['machine_label'],
            'encryption': data['encryption'],
            'value_casing': data['value_casing'],
            'live_update': data['live_update'],
            'value_required':  data['value_required'],
            'value_max':  data['value_max'],
            'value_min':  data['value_min'],
            'value_casing':  data['value_casing'],
            'encryption':  data['encryption'],
            'notes': data['notes'],
        }

        device_type_results = yield self._YomboAPI.request('PATCH', '/v1/device_command_input/%s/%s/%s' % (device_type_id, command_id, input_type_id), api_data)
        if device_type_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't update device type command input.",
                'apimsg': device_type_results['content']['message'],
                'apimsghtml': device_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Updated associated input to device type command",
            'device_type_id': device_type_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_command_input_remove(self, device_type_id, command_id, input_type_id, **kwargs):
        """
        Associate an input type to a device type command at the Yombo server level, not at the local gateway level.

        :param device_type_id: The device_type ID to enable.
        :param command_id: The command_id ID to add/associate.
        :param kwargs:
        :return:
        """
        device_type_results = yield self._YomboAPI.request('DELETE', '/v1/device_command_input/%s/%s/%s' % (device_type_id, command_id, input_type_id))
        if device_type_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't remove input from device type command",
                'apimsg': device_type_results['content']['message'],
                'apimsghtml': device_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Removed input from device type command",
            'device_type_id': device_type_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_command_remove(self, device_type_id, command_id, **kwargs):
        """
        Remove a command from device type at the Yombo server level, not at the local gateway level.

        :param device_type_id: The device_type ID to enable.
        :param command_id: The command_id ID to add/associate.
        :param kwargs:
        :return:
        """
        device_type_results = yield self._YomboAPI.request('DELETE', '/v1/device_type_command/%s/%s' % (device_type_id, command_id))

        if device_type_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't remove command from device type",
                'apimsg': device_type_results['content']['message'],
                'apimsghtml': device_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Removed command from device type.",
            'device_type_id': device_type_id,
        }
        returnValue(results)

class DeviceType(object):
    """
    A class to manage a single device type.
    :ivar label: Device type label
    :ivar description: The description of the device type.
    :ivar inputTypeID: The type of input that is required as a variable.
    """
    def __init__(self, device_type, _DeviceTypes):
        """
        A device type object used to lookup more information. Any changes to this record will be updated
        into the database.

        :cvar device_type_id: (string) The id of the device type.

        :param device_type: A device type as passed in from the device types class. This is a
            dictionary with various device type attributes.
        """
        logger.debug("DeviceType::__init__: {device_type}", device_type=device_type)

        self._DeviceTypes = _DeviceTypes
        self.commands = {}
        self.device_type_id = device_type['id']

        # the below are setup during update_attributes()
        self.category_id = None
        self.platform = 'device'
        self.machine_label = None
        self.label = None
        self.description = None
        self.public = None
        self.status = None
        self.created = None
        self.updated = None

        self.update_attributes(device_type)

    def update_attributes(self, device_type):
        """
        Sets various values from a device type dictionary. This can be called when either new or
        when updating.

        :param device_type: 
        :return: 
        """
        self.category_id = device_type['category_id']
        self.machine_label = device_type['machine_label']
        self.label = device_type['label']
        self.description = device_type['description']
        self.public = device_type['public']
        self.status = device_type['status']
        self.created = device_type['created']
        self.updated = device_type['updated']
        if 'platform' in device_type:
            if device_type["platform"] is None or device_type["platform"] == "":
                self.platform = "device"
            else:
                self.platform = device_type["platform"]

    @inlineCallbacks
    def _init_(self):
        """
        Loads available commands from the database. This should only be called when a device type is loaded,
        notification that device type has been updated, or when device type commands have changed.

        """
        command_ids = yield self._DeviceTypes._LocalDB.get_device_type_commands(self.device_type_id)
        self.commands.clear()
        logger.debug("Device type received command ids: {command_ids}", command_ids=command_ids)
        for command_id in command_ids:
            self.commands[command_id] = {
                'command': self._DeviceTypes._Commands[command_id],
                'inputs': {}
            }
            inputs = yield self._DeviceTypes._LocalDB.device_type_command_inputs_get(self.device_type_id, command_id)
            for input in inputs:
                self.commands[command_id]['inputs'][input.machine_label] = {
                    'input_type_id': input.input_type_id,
                    'device_type_id': input.device_type_id,
                    'command_id': input.command_id,
                    'label': input.label,
                    'machine_label': input.machine_label,
                    'live_update': input.live_update,
                    'value_required': input.value_required,
                    'value_max': input.value_max,
                    'value_min': input.value_min,
                    'value_casing': input.value_casing,
                    'encryption': input.encryption,
                    'notes': input.notes,
                    'updated': input.updated,
                    'created': input.created,
                }

    @inlineCallbacks
#    @memoize_ttl(5)
    def get_variable_fields(self):
        """
        Get variable groups and fields from the database.
        :return: Dictionary of dicts containing variable fields.
        """
        variables = yield self._Parent._Variables.get_variable_fields_data(
            group_relation_type='device',
            group_relation_id=self.device_type_id
        )
        return variables

    def __getitem__(self, key):
        # print('devicetype __getitem__: ', key)
        # print('devicetype repsonse __getitem__: ', getattr(self, key))
        # print('devicetype repsonse __getitem__: ', type(getattr(self, key)))
        return getattr(self, key)

    def get_devices(self):
        """
        Return a dictionary of devices for a given device_type
        :return:
        """

        attrs = [
            {
                'field': 'device_type_id',
                'value': self.device_type_id,
                'limiter': 1,
            }
        ]

        try:
            found, key, item, ratio, others = do_search_instance(attrs, self._DeviceTypes._Devices.devices,
                                      self._DeviceTypes.device_type_search_attributes)
            if found:
                devices = {}
                for item in others:
                    device = item['value']
                    devices[device['device_id']] = device
                return devices
            else:
                return {}
        except YomboWarning as e:
            raise KeyError('Get devices had problems: %s' % e)

    def get_modules(self, return_value='id'):
        """
        Return a list of modules for a given device_type
        :return:
        """
        if return_value == 'id':
            return list(self.registered_modules.keys())
        elif return_value == 'label':
            return list(self.registered_modules.values())
        else:
            raise YomboWarning("get_modules requires either 'id' or 'label'")

    def __str__(self):
        """
        Print a string when printing the class.  This will return the device type id so that
        the device type can be identified and referenced easily.
        """
        return self.device_type_id

    def __repl__(self):
        """
        Export device type variables as a dictionary.
        """
        return {
            'device_type_id': str(self.device_type_id),
            'machine_label': str(self.machine_label),
            'label': str(self.label),
            'description': str(self.description),
            'public': int(self.public),
            'status': int(self.status),
            'created': int(self.created),
            'updated': int(self.updated),
        }
