# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Device Locations @ Module Development <https://yombo.net/docs/modules/locations/>`_

Stores location and area information in memory.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.14.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
"""
from collections import OrderedDict
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import search_instance, do_search_instance, global_invoke_all

logger = get_logger('library.device_locations')

class DeviceLocations(YomboLibrary):
    """
    Manages device locations for a gateway.
    """
    @property
    def device_locations_sorted(self):
        return OrderedDict(sorted(self.device_locations.items(), key=lambda x: x[1].label))

    def __contains__(self, location_requested):
        """
        Checks to if a provided device location ID or machine_label exists.

            >>> if '0kas02j1zss349k1' in self._DeviceLocations:

        or:

            >>> if 'some_device_location_name' in self.Device_Locations:

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param location_requested: The device location id or machine_label to search for.
        :type location_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get_meta(location_requested)
            return True
        except:
            return False

    def __getitem__(self, location_requested):
        """
        Attempts to find the device requested using a couple of methods.

            >>> device_location = self.Device_Locations['0kas02j1zss349k1']  #by uuid

        or:

            >>> device_location = self.Device_Locations['alpnum']  #by name

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param location_requested: The device location ID or machine_label to search for.
        :type location_requested: string
        :return: A pointer to the device type instance.
        :rtype: instance
        """
        return self.get_meta(location_requested)

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
        """ iter device types. """
        return self.device_types.__iter__()

    def __len__(self):
        """
        Returns an int of the number of device types configured.

        :return: The number of device locations configured.
        :rtype: int
        """
        return len(self.device_locations)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return self.device_locations.__str__()

    def keys(self):
        """
        Returns the keys (device type ID's) that are configured.

        :return: A list of device type IDs. 
        :rtype: list
        """
        return list(self.device_locations.keys())

    def items(self):
        """
        Gets a list of tuples representing the device types configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.device_locations.items())

    def values(self):
        return list(self.device_locations.values())

    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.
        self.device_locations = {}
        self.device_location_search_attributes = ['device_location_id', 'gateway_id', 'device_location', 'machine_label', 'destination',
            'data_type', 'status']
        self.load_deferred = Deferred()
        self._load_device_locations_from_database()
        return self.load_deferred

    # def _load_(self):
    #     """
    #     Loads all device locations from DB to various arrays for quick lookup.
    #     """

    def _stop_(self, **kwargs):
        """
        Cleans up any pending deferreds.
        """
        if self.load_deferred is not None and self.load_deferred.called is False:
            self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    @inlineCallbacks
    def _load_device_locations_from_database(self):
        """
        Loads device locations from database and sends them to
        :py:meth:`import_device_location <DeviceLocations.import_device_location>`

        This can be triggered either on system startup or when new/updated device locations have been saved to the
        database and we need to refresh existing device locations.
        """
        device_locations = yield self._LocalDB.get_device_locations()
        for device_location in device_locations:
            self.import_device_location(device_location.__dict__)
        self.load_deferred.callback(10)

    def import_device_location(self, device_location, test_device_location=False):
        """
        Add a new device locations to memory or update an existing device_locations.

        **Hooks called**:

        * _device_location_before_load_ : If added, sends device location dictionary as 'device_location'
        * _device_location_before_update_ : If updated, sends device location dictionary as 'device_location'
        * _device_location_loaded_ : If added, send the device location instance as 'device_location'
        * _device_location_updated_ : If updated, send the device location instance as 'device_location'

        :param device_location: A dictionary of items required to either setup a new device location or update an existing one.
        :type input: dict
        :param test_device_location: Used for unit testing.
        :type test_device_location: bool
        :returns: Pointer to new input. Only used during unittest
        """
        # logger.debug("device_location: {device_location}", device_location=device_location)

        global_invoke_all('_device_locations_before_import_', called_by=self, **{'device_location': device_location})
        device_location_id = device_location["id"]
        if device_location_id not in self.device_locations:
            global_invoke_all('_device_location_before_load_', called_by=self, **{'device_location': device_location})
            self.device_locations[device_location_id] = DeviceLocation(self, device_location)
            global_invoke_all('_device_location_loaded_', called_by=self, **{'device_location': self.device_locations[device_location_id]})
        elif device_location_id not in self.device_locations:
            global_invoke_all('_device_location_before_update_', called_by=self, **{'device_location': device_location})
            self.device_locations[device_location_id].update_attributes(device_location)
            global_invoke_all('_device_location_updated_', called_by=self, **{'device_location': self.device_locations[device_location_id]})

    def remove_device_location(self, device_location_id):
        """
        Remove a device location from memory.
        
        :param device_location_id: 
        :return: 
        """
        if device_location_id in self.device_locations:
            del self.device_locations[device_location_id]

    def get_device_label(self, device_location_id, label):
        if device_location_id in self.device_locations:
            location_label = self.device_locations[device_location_id].label
            if location_label.lower() == "none" or location_label is None:
                return label
            else:
                return "%s %s" % (location_label, label)
        else:
            return ""

    def get_all(self):
        """
        Returns a copy of the device_locations list.
        :return:
        """
        return self.device_locations.copy()

    def get(self, location_requested, location_type=None, limiter=None, status=None):
        """
        Performs the actual search.

        .. note::

           Can use the built in methods below or use get_meta/get to include 'location_type' limiter:

            >>> self.Device_Locations['13ase45']

        or:

            >>> self.Device_Locations['numeric']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param location_requested: The device location ID or device location label to search for.
        :type location_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the device location to check for.
        :type status: int
        :return: Pointer to requested device_location.
        :rtype: dict
        """
        if limiter is None:
            limiter = .89

        if limiter > .99999999:
            limiter = .99
        elif limiter < .10:
            limiter = .10

        if status is None:
            status = 1

        if location_requested in self.device_locations:
            item = self.device_locations[location_requested]
            if item.status != status:
                raise KeyError("Requested device location found, but has invalid status: %s" % item.status)
            return item
        else:
            attrs = [
                {
                    'field': 'device_location_id',
                    'value': location_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'machine_label',
                    'value': location_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'label',
                    'value': location_requested,
                    'limiter': limiter,
                }
            ]
            try:
                # logger.debug("Get is about to call search...: %s" % location_requested)
                # found, key, item, ratio, others = self._search(attrs, operation="highest")
                found, key, item, ratio, others = do_search_instance(attrs, self.device_locations,
                                                                     self.device_location_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest")
                # logger.debug("found device location by search: others: {others}", others=others)
                if location_type is not None:
                    for other in others:
                        if other['value'].location_type == location_type and other['ratio'] > limiter:
                            return other['value']
                else:
                    if found:
                        return item
                raise KeyError("Device Location not found: %s" % location_requested)
            except YomboWarning as e:
                raise KeyError('Searched for %s, but had problems: %s' % (location_requested, e))

    def search(self, _limiter=None, _operation=None, **kwargs):
        """
        Search for device location based on attributes for all device locations.

        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the device location to check for.
        :return: 
        """
        return search_instance(kwargs,
                               self.device_locations,
                               self.device_location_search_attributes,
                               _limiter,
                               _operation)

    @inlineCallbacks
    def add_device_location(self, data, **kwargs):
        """
        Add a device location at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        device_location_results = yield self._YomboAPI.request('POST', '/v1/device_location', data)

        if device_location_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't add device location",
                'apimsg': device_location_results['content']['message'],
                'apimsghtml': device_location_results['content']['html_message'],
            }
            return results

        results = {
            'status': 'success',
            'msg': "Device Location type added.",
            'device_location_id': device_location_results['data']['id'],
        }
        data['id'] = device_location_results['data']['id']
        data['updated'] = time()
        data['created'] = time()
        self._LocalDB.insert_device_locations(data)
        self.import_device_location(data)
        return results

    @inlineCallbacks
    def edit_device_location(self, device_location_id, data, **kwargs):
        """
        Edit a device location at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """

        device_location_results = yield self._YomboAPI.request('PATCH', '/v1/device_location/%s' % (device_location_id), data)

        if device_location_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit device location",
                'apimsg': device_location_results['content']['message'],
                'apimsghtml': device_location_results['content']['html_message'],
            }
            return results

        results = {
            'status': 'success',
            'msg': "Device type edited.",
            'device_location_id': device_location_results['data']['id'],
        }

        if device_location_id in self.device_locations:
            self.device_locations[device_location_id].update_attributes(data)
            self.device_locations[device_location_id].save_to_db(data)

        return results

    @inlineCallbacks
    def delete_device_location(self, device_location_id, **kwargs):
        """
        Delete a device location at the Yombo server level, not at the local gateway level.

        :param device_location_id: The device location ID to delete.
        :param kwargs:
        :return:
        """
        device_location_results = yield self._YomboAPI.request('DELETE', '/v1/device_location/%s' % device_location_id)

        if device_location_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete device location",
                'apimsg': device_location_results['content']['message'],
                'apimsghtml': device_location_results['content']['html_message'],
            }
            return results

        results = {
            'status': 'success',
            'msg': "Device Location deleted.",
            'device_location_id': device_location_id,
        }

        self.remove_device_location(device_location_id)
        self._LocalDB.delete_device_locations(device_location_id)
        return results


class DeviceLocation:
    """
    A class to manage a single device location.
    :ivar device_location_id: (string) The unique ID.
    :ivar label: (string) Human label
    :ivar machine_label: (string) A non-changable machine label.
    :ivar category_id: (string) Reference category id.
    :ivar input_regex: (string) A regex to validate if user input is valid or not.
    :ivar always_load: (int) 1 if this item is loaded at startup, otherwise 0.
    :ivar status: (int) 0 - disabled, 1 - enabled, 2 - deleted
    :ivar public: (int) 0 - private, 1 - public pending approval, 2 - public
    :ivar created: (int) EPOCH time when created
    :ivar updated: (int) EPOCH time when last updated
    """

    def __init__(self, parent, device_location):
        """
        Setup the device location object using information passed in.

        :param device_location: An device location with all required items to create the class.
        :type device_location: dict

        """
        # logger.debug("DeviceLocation info: {device_location}", device_location=device_location)

        self._Parent = parent
        self.device_location_id = device_location['id']

        # below are configure in update_attributes()
        self.location_type = None
        self.machine_label = None
        self.label = None
        self.description = None
        self.updated = None
        self.created = None
        self.update_attributes(device_location)

    def update_attributes(self, device_location):
        """
        Sets various values from a device location dictionary. This can be called when either new or
        when updating.

        :param device_location: 
        :return: 
        """
        if 'location_type' in device_location:
            self.location_type = device_location['location_type']
        if 'machine_label' in device_location:
            self.machine_label = device_location['machine_label']
        if 'label' in device_location:
            self.label = device_location['label']
        if 'description' in device_location:
            self.description = device_location['description']
        if 'created' in device_location:
            self.created = device_location['created']
        if 'updated' in device_location:
            self.updated = device_location['updated']

    def save_to_db(self):
        self._Parent._LocalDB.update_device_locations(self)

    def __str__(self):
        """
        Print a string when printing the class.  This will return the device location id so that
        the device location can be identified and referenced easily.
        """
        return self.machine_label

    # def __repl__(self):
    #     """
    #     Export device location variables as a dictionary.
    #     """
    #     return {
    #         'device_location_id': str(self.device_location_id),
    #         'location_type': str(self.location_type),
    #         'machine_label': str(self.machine_label),
    #         'label': str(self.label),
    #         'description': int(self.description),
    #         'created': int(self.created),
    #         'updated': str(self.updated),
    #     }
