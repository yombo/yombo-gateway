# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This is a simple helper library to manage device type mapping. This is a mapping between modules, device types,
and commands.

This library keeps track of what modules can access what device types, and what commands those device types can perform.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue

# Import Yombo libraries
from yombo.core.exceptions import YomboFuzzySearchError, YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils.fuzzysearch import FuzzySearch
from yombo.utils import global_invoke_all

logger = get_logger('library.devicetypes')


class DeviceTypes(YomboLibrary):
    """
    Manages device type database tabels. Just simple update a module's device types or device type's available commands
    and any required database tables are updated. Also maintains a list of module device types and device type commands
    in memory for access.
    """
    def __getitem__(self, device_type_requested):
        """
        Return a device type, searching first by command ID and then by command
        function (on, off, bright, dim, open, close, etc).  Modules should use
        `self._Commands` to search with:

            >>> self._DeviceTypes['137ab129da9318']  #by id
            
        or:
        
            >>> self._DeviceTypes['x10_appliance']  #by name

        :param commandRequested: The device type ID or device type label to search for.
        :type commandRequested: string
        """
        return self.get(device_type_requested)

    def __len__(self):
        return len(self.device_types_by_id)

    def __contains__(self, device_type_requested):
        try:
            self.get(device_type_requested)
            return True
        except:
            return False

    def __iter__(self):
        return self.device_types_by_id.iteritems()

    def _init_(self):
        """
        Setups up the basic framework. Nothing is loaded in here until the :poy:ref:_load_ stage.
        """
        self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.
        self.run_state = 1

        self.device_types_by_id = FuzzySearch({}, .99)
        self.device_types_by_name = FuzzySearch({}, .89)

        self._LocalDB = self._Libraries['localdb']

    def _load_(self):
        self.run_state = 2
        self._load_device_types()
        self.load_deferred = Deferred()
        return self.load_deferred

    def _start_(self):
        """
        Loads all device types from DB to various arrays for quick lookup.
        """
        self.run_state = 3

    def _started_(self):
        # print "device types info:"
        # for dt, data in self.device_types_by_id.iteritems():
        #     print "dt: %s, commands: %s" % (data.label, data.commands)
        pass

    def get(self, device_type_requested):
        """
        Gets a device type be device type id or by device type label.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find commands: `self._DeviceTypes['8w3h4sa']`

        :raises YomboWarning: Raised when device type cannot be found.
        :param device_type_requested: The device type ID ID or device type label to search for.
        :type device_type_requested: string
        :return: A DeviceType instance.
        :rtype: dict
        """
        # print "device_types_by_name: %s" % self.device_types_by_name
        if device_type_requested in self.device_types_by_id:
            return self.device_types_by_id[device_type_requested]
        else:
            try:
                return self.device_types_by_name[device_type_requested]
            except YomboFuzzySearchError, e:
                raise YomboWarning('Searched for %s, but no good matches found.' % e.searchFor)

    @inlineCallbacks
    def ensure_loaded(self, device_type_id):
        """
        Called by the device class to make sure the requsted device type id is loaded. This happens in
        the background.

        :param device_type_id:
        :return:
        """
        if device_type_id not in self.device_types_by_id:
            dt = yield self._LocalDB.get_device_type(device_type_id)
            self.add_device_type(dt[0])

    def devices_by_device_type(self, requested_device_type):
        """
        A list of devices types for a given device type.

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
        if device_type_id in self.device_types_by_id:
            return self.device_types_by_id[device_type_id].commands
        else:
            raise YomboWarning("Device type id doesn't exist: %s" % device_type_id, 200,
                'device_type_commands', 'DeviceTypes')

    def get_local_devicetypes(self):
        """
        Return a dictionary with all the public device types.

        :return:
        """
        results = {}
        for item_id, item in self.device_types_by_id.iteritems():
            if item.public <= 1:
                results[item_id] = item
        return results

    def get_public_devicetypes(self):
        """
        Return a dictionary with all the public commands.

        :return:
        """
        results = {}
        for item_id, item in self.device_types_by_id.iteritems():
            if item.public == 2:
                results[item_id] = item
        return results

    @inlineCallbacks
    def _load_device_types(self):
        """
        Load device types into memory.
        """
        dts = yield self._LocalDB.get_device_types()
        # print "zzz 222: %s" % dts

        for dt in dts:
            yield self.add_device_type(dt)
        #
        # for module_id, klass in self._Modules._moduleClasses.iteritems():
        #     print "device types: module_id"
        logger.debug("Done _load_device_types: {dts}", dts=dts)
        self.load_deferred.callback(10)

    def _stop_(self):
        if self.load_deferred is not None and self.load_deferred.called is False:
            self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    def add_device_type(self, record, test_device_type = False):
        """
        Add a device_type based on data from a row in the SQL database.

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :param test_device_type: If true, is a test device type not from SQL, only used for unittest.
        :type test_device_type: bool
        :returns: Pointer to new device type. Only used during unittest
        """
        logger.debug("record: {record}", record=record)
        record = record.__dict__
        dt_id = record['id']
        self.device_types_by_id[dt_id] = DeviceType(record, self)
        d = self.device_types_by_id[dt_id]._init_()
        self.device_types_by_name[record['machine_label']] = self.device_types_by_id[dt_id]

#        if test_device_type:
#            return self.__yombocommands[cmdUUID]

    @inlineCallbacks
    def dev_device_type_add(self, data, **kwargs):
        """
        Add a module at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        device_type_results = yield self._YomboAPI.request('POST', '/v1/device_type', data)
        # print("dt_results: %s" % device_type_results)

        if device_type_results['code'] != 200:
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
        device_type_results = yield self._YomboAPI.request('PATCH', '/v1/device_type/%s' % (device_type_id), data)
        # print("module edit results: %s" % module_results)

        if device_type_results['code'] != 200:
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

        if device_type_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete device type",
                'apimsg': device_type_results['content']['message'],
                'apimsghtml': device_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Command deleted.",
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
        #        print "enabling device_type: %s" % device_type_id
        api_data = {
            'status': 1,
        }

        device_type_results = yield self._YomboAPI.request('PATCH', '/v1/device_type/%s' % device_type_id, api_data)

        if device_type_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't enable device type",
                'apimsg': device_type_results['content']['message'],
                'apimsghtml': device_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Command enabled.",
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
#        print "disabling device_type: %s" % device_type_id
        api_data = {
            'status': 0,
        }

        device_type_results = yield self._YomboAPI.request('PATCH', '/v1/device_type/%s' % device_type_id, api_data)
 #       print("disable device_type results: %s" % device_type_results)

        if device_type_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable device_type",
                'apimsg': device_type_results['content']['message'],
                'apimsghtml': device_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Command disabled.",
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
        #        print "enabling device_type: %s" % device_type_id
        api_data = {
            'device_type_id': device_type_id,
            'command_id': command_id,
        }

        device_type_results = yield self._YomboAPI.request('POST', '/v1/device_type_command', api_data)
        if device_type_results['code'] != 200:
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
        #        print "enabling device_type: %s" % device_type_id
        api_data = {
            'device_type_id': device_type_id,
            'command_id': command_id,
            'input_type_id': input_type_id,
            'live_update': data['live_update'],
            'value_required':  data['value_required'],
            'value_max':  data['value_max'],
            'value_min':  data['value_min'],
            'notes': data['notes'],
        }

        device_type_results = yield self._YomboAPI.request('POST', '/v1/device_command_input', api_data)
        if device_type_results['code'] != 200:
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
        #        print "enabling device_type: %s" % device_type_id
        api_data = {
            # 'device_type_id': device_type_id,
            # 'command_id': command_id,
            # 'input_type_id': input_type_id,
            'live_update': data['live_update'],
            'value_required':  data['value_required'],
            'value_max':  data['value_max'],
            'value_min':  data['value_min'],
            'value_casing':  data['value_casing'],
            'encryption':  data['encryption'],
            'notes': data['notes'],
        }

        device_type_results = yield self._YomboAPI.request('PATCH', '/v1/device_command_input/%s/%s/%s' % (device_type_id, command_id, input_type_id), api_data)
        if device_type_results['code'] != 200:
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
        if device_type_results['code'] != 200:
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

        if device_type_results['code'] != 200:
            # print "device_type_results: %s" % device_type_results
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

class DeviceType:
    """
    A class to manage a single device type.
    :ivar label: Command label
    :ivar description: The description of the command.
    :ivar inputTypeID: The type of input that is required as a variable.
    :ivar voice_cmd: The voice command of the command.
    """
    def __init__(self, device_type, device_type_library):
        """
        A device type object used to lookup more information. Any changes to this record will be updated
        into the database.

        :cvar device_type_id: (string) The id of the device type.

        :param device_type: A device type as passed in from the device types class. This is a
            dictionary with various device type attributes.
        :type command: dict
        """
        logger.debug("DeviceType::__init__: {device_type}", device_type=device_type)

        self._DTLibrary = device_type_library
        self.device_type_id = device_type['id']
        self.category_id = device_type['category_id']
        self.machine_label = device_type['machine_label']
        self.label = device_type['label']
        self.description = device_type['description']
        self.public = device_type['public']
        self.status = device_type['status']
        self.created = device_type['created']
        self.updated = device_type['updated']
        # if len(device_type['commands']) > 0:
        #     self.commands = device_type['commands'].split(',')
        # else:
        #     self.commands = []
        self.commands = {}

#        self.updated_srv = device_type.updated_srv

    def _init_(self):
        """
        Loads any related commands for the given device type.

        :return:
        """

        def set_commands(command_ids):
            logger.debug("Device type received command ids: {command_ids}", command_ids=command_ids)
            for command_id in command_ids:
                self.commands[command_id] = self._DTLibrary._Commands[command_id]
            # self.commands = vars

        def gotException(failure):
           logger.warn("Exception 1: {failure}", failure=failure)
           return 100  # squash exception, use 0 as value for next stage

        # d = self._DevicesLibrary._Libraries['localdb'].get_commands_for_device_type(self.device_type_id)
        # d.addCallback(set_commands)
        # d.addErrback(gotException)
        # d.addCallback(lambda ignored: self._DevicesLibrary._Libraries['localdb'].get_variables('device', self.device_id))

        d = self._DTLibrary._Libraries['localdb'].get_device_type_commands(self.device_type_id)
        d.addErrback(gotException)
        d.addCallback(set_commands)
        d.addErrback(gotException)
        return d

    def __getitem__(self, key):
        print 'devicetype __getitem__: ', key
        print 'devicetype repsonse __getitem__: ', getattr(self, key)
        print 'devicetype repsonse __getitem__: ', type(getattr(self, key))
        return getattr(self, key)

    def __str__(self):
        """
        Print a string when printing the class.  This will return the cmdUUID so that
        the command can be identified and referenced easily.
        """
        return self.device_type_id

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
            return self._DTLibrary._Devices.search(_limiter=1, device_type_id=self.device_type_id)
        except YomboWarning, e:
            raise KeyError('Get devices had problems: %s' % e)

    def get_modules(self, return_value='id'):
        """
        Return a list of modules for a given device_type
        :return:
        """
        if return_value == 'id':
            return self.registered_modules.keys()
        elif return_value == 'label':
            return self.registered_modules.values()
        else:
            raise YomboWarning("get_modules requires either 'id' or 'label'")

    def dump(self):
        """
        Export command variables as a dictionary.
        """
        return {
            'device_type_id': str(self.device_type_id),
            'machine_label' : str(self.machine_label),
            'label'         : str(self.label),
            'description'   : str(self.description),
            'public'        : int(self.public),
            'status'        : int(self.status),
            'created'       : int(self.created),
            'updated'       : int(self.updated),
        }
