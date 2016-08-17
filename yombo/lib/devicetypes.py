# This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
This is a simple helper library to manage device type mapping. This is a mapping between modules, device types,
and commands.

This library keeps track of what modules can access what device types, and what commands those device types can perform.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred

# Import Yombo libraries
from yombo.core.exceptions import YomboFuzzySearchError, YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils.fuzzysearch import FuzzySearch
from yombo.utils import global_invoke_all

logger = get_logger('library.devicetypes')


class DeviceTypes(YomboLibrary):
    """
    Manages device type database tabls. Just simple update a module's device types or device type's available commands
    and any required database tables are updated. Also maintains a list of module device types and device type commands
    in memory for access.
    """
    def __getitem__(self, device_type_requested):
        """
        Return a command, searching first by command UUID and then by command
        function (on, off, bright, dim, open, close, etc).  Modules should use
        `self._Commands` to search with:

            >>> self._Commands['137ab129da9318]  #by uuid
        or::
            >>> self._Commands['living room light']  #by name

        See: :func:`yombo.core.helpers.getCommands` for full usage example.

        :param commandRequested: The command UUID or command label to search for.
        :type commandRequested: string
        """
        return self.get_device_type(device_type_requested)

    def __len__(self):
        return len(self.device_types_by_id)

    def __contains__(self, device_type_requested):
        try:
            self.get_device_type(device_type_requested)
            return True
        except:
            return False

    def _init_(self):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        :param loader: A pointer to the L{Loader<yombo.lib.loader.Loader>}
        library.
        :type loader: Instance of Loader
        """
        self.run_state = 1

        self.device_types_by_id = FuzzySearch({}, .99)
        self.device_types_by_name = FuzzySearch({}, .89)

        self.local_db = self._Libraries['localdb']

    def _load_(self):
        self.run_state = 2

    def _start_(self):
        """
        Loads all device types from DB to various arrays for quick lookup.
        """
        self.run_state = 3

        # print "zzz 111"
        self._load_device_types()
        self.start_defer = Deferred()
        return self.start_defer

    def _started_(self):
        # print "device types info:"
        # for dt, data in self.device_types_by_id.iteritems():
        #     print "dt: %s, commands: %s" % (data.label, data.commands)
        #     print "dt: %s, registered_devices: %s" % (data.label, data.registered_devices)
        #     print "dt: %s, registered_modules: %s" % (data.label, data.registered_modules)
        pass

    def get_device_type(self, device_type_requested):
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

    def module_devices(self, module_id):
        """
        A list of devices types for a given module id.

        :raises YomboWarning: Raised when module_id is not found.
        :param module_id: The Module ID to return device types for.
        :return: A list of device type id's.
        :rtype: list
        """
        temp = []
        if module_id in self._Modules._moduleClasses:
            # print "dt..module_id: %s" % module_id
            # print "dt..self._Modules._moduleClasses[module_id].device_types: %s" % self._Modules._moduleClasses[module_id].device_types
            for dt in self._Modules._moduleClasses[module_id].device_types:
                temp.extend(self.device_types_by_id[dt].get_devices())

        return temp

    def devices_by_device_type(self, requested_device_type, return_value='id'):
        """
        A list of devices types for a given device type.

        :raises YomboWarning: Raised when module_id is not found.
        :param requested_device_type: A device type by either ID or Label.
        :return: A list of device id's.
        :rtype: list
        """
        device_type = self.get_device_type(requested_device_type)
        return device_type.get_devices(return_value)

    def device_type_commands(self, device_type_id):
        """
        A list of commands for a given device type.

        :raises YomboWarning: Raised when device_type_id is not found.
        :param device_type_id: The Device Type ID to return device types for.
        :return: A list of command id's.
        :rtype: list
        """
        if device_type_id in self.device_type_commands:
            return self.device_types_by_id.commands
        else:
            raise YomboWarning("Device type id doesn't exist: %s" % device_type_id, 200,
                'device_type_commands', 'DeviceTypes')

    @inlineCallbacks
    def _load_device_types(self):
        """
        Load device types into memory.
        """
        dts = yield self.local_db.get_device_types()
        # print "zzz 222: %s" % dts

        for dt in dts:
            self._load_device_type(dt)

        for module_id, klass in self._Modules._moduleClasses.iteritems():
            print "device types: module_id"
        logger.debug("Done _load_device_types: {dts}", dts=dts)
        self.start_defer.callback(10)

    def _load_device_type(self, record, test_device_type = False):
        """
        Add a device_type based on data from a row in the SQL database.

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :param test_device_type: If true, is a test device type not from SQL, only used for unittest.
        :type test_device_type: bool
        :returns: Pointer to new device type. Only used during unittest
        """
        logger.debug("record: {record}", record=record)
        dt_id = record['id']
        self.device_types_by_id[dt_id] = DeviceType(record, self)
        self.device_types_by_name[record['machine_label']] = self.device_types_by_id[dt_id]

#        if test_device_type:
#            return self.__yombocommands[cmdUUID]

    def update_registered_device(self, old, new):
        self.del_registered_device(old)
        return self.add_registered_device(new)

    def add_registered_device(self, device):
        if device.device_type_id in self.device_types_by_id:
            self.device_types_by_id[device.device_type_id].registered_devices[device.device_id] = device.label
            return True
        else:
            return False

    def del_registered_device(self, device):
        if device.device_type_id in self.device_types_by_id:
            del self.device_types_by_id[device.device_type_id].registered_devices[device.device_id]
            return True
        return False


    def update_registered_module(self, old, new):
        self.del_registered_module(old)
        self.add_registered_module(new)

    def add_registered_module(self, module):
        results = None
        for device_type_id in module.device_types:
            if device_type_id in self.device_types_by_id:
                self.device_types_by_id[device_type_id].registered_modules[module.module_id] = module.label
                if results is not False:
                    results = True
            else:
                results = False
        if results is None:
            return False
        return results

    def del_registered_module(self, module):
        results = None
        for device_type_id in module.device_types:
            if device_type_id in self.device_types_by_id:
                del self.device_types_by_id[device_type_id].registered_modules[module.module_id]
                if results is not False:
                    results = True
            else:
                results = False
        if results is None:
            return False
        return results

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
        self.uri = device_type['uri']
        self.label = device_type['machine_label']
        self.description = device_type['description']
        self.device_class = device_type['device_class']
        self.live_update = device_type['live_update']
        self.public = device_type['public']
        self.status = device_type['status']
        self.created = device_type['created']
        self.updated = device_type['updated']
        if len(device_type['commands']) > 0:
            self.commands = device_type['commands'].split(',')
        else:
            self.commands = []

        self.registered_devices = {}
        self.registered_modules = {}
#        self.updated_srv = device_type.updated_srv

    def __str__(self):
        """
        Print a string when printing the class.  This will return the cmdUUID so that
        the command can be identified and referenced easily.
        """
        return self.device_type_id

    def get_devices(self, return_value='id'):
        """
        Return a list of devices for a given device_type
        :return:
        """
        if return_value == 'id':
            return self.registered_devices.keys()
        elif return_value == 'label':
            return self.registered_devices.values()
        else:
            raise YomboWarning("get_devices requires either 'id' or 'label'")

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
            'uri'           : str(self.uri),
            'label'         : str(self.label),
            'description'   : str(self.description),
            'device_class'  : str(self.device_class),
            'live_update'   : int(self.live_update),
            'public'        : int(self.public),
            'status'        : int(self.status),
            'created'       : int(self.created),
            'updated'       : int(self.updated),
        }
