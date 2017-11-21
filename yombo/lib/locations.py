# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Locations @ Module Development <https://docs.yombo.net/Libraries/Locations>`_


Stores location and area information in memory.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.14.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://docs.yombo.net/gateway/html/current/_modules/yombo/lib/locations.html>`_
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

logger = get_logger('library.locations')

class Locations(YomboLibrary):
    """
    Manages locations for a gateway.
    """
    @property
    def locations_sorted(self):
        return OrderedDict(sorted(self.locations.items(), key=lambda x: x[1].label))

    def __contains__(self, location_requested):
        """
        Checks to if a provided location ID or machine_label exists.

            >>> if '0kas02j1zss349k1' in self._Locations:

        or:

            >>> if 'some_location_name' in self.Locations:

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param location_requested: The location id or machine_label to search for.
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
        Attempts to find the location requested using a couple of methods.

            >>> location = self.Locations['0kas02j1zss349k1']  #by uuid

        or:

            >>> location = self.Locations['alpnum']  #by name

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param location_requested: The location ID or machine_label to search for.
        :type location_requested: string
        :return: A pointer to the location type instance.
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
        """ iter locations. """
        return self.locations.__iter__()

    def __len__(self):
        """
        Returns an int of the number of locations configured.

        :return: The number of locations configured.
        :rtype: int
        """
        return len(self.locations)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return self.locations.__str__()

    def keys(self):
        """
        Returns the keys (location ID's) that are configured.

        :return: A list of location IDs.
        :rtype: list
        """
        return list(self.locations.keys())

    def items(self):
        """
        Gets a list of tuples representing the locations configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.locations.items())

    def values(self):
        return list(self.locations.values())

    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.
        self.locations = {}
        self.location_search_attributes = ['location_id', 'gateway_id', 'location', 'machine_label', 'destination',
            'data_type', 'status']
        self.load_deferred = Deferred()
        self._load_locations_from_database()
        return self.load_deferred

    # def _load_(self):
    #     """
    #     Loads all locations from DB to various arrays for quick lookup.
    #     """

    def _stop_(self, **kwargs):
        """
        Cleans up any pending deferreds.
        """
        if hasattr(self, 'load_deferred'):
            if self.load_deferred is not None and self.load_deferred.called is False:
                self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    @inlineCallbacks
    def _load_locations_from_database(self):
        """
        Loads locations from database and sends them to
        :py:meth:`import_location <Locations.import_location>`

        This can be triggered either on system startup or when new/updated locations have been saved to the
        database and we need to refresh existing locations.
        """
        locations = yield self._LocalDB.get_locations()
        for location in locations:
            self.import_location(location.__dict__)
        self.load_deferred.callback(10)

    def import_location(self, location, test_location=False):
        """
        Add a new locations to memory or update an existing locations.

        **Hooks called**:

        * _location_before_load_ : If added, sends location dictionary as 'location'
        * _location_before_update_ : If updated, sends location dictionary as 'location'
        * _location_loaded_ : If added, send the location instance as 'location'
        * _location_updated_ : If updated, send the location instance as 'location'

        :param location: A dictionary of items required to either setup a new location or update an existing one.
        :type input: dict
        :param test_location: Used for unit testing.
        :type test_location: bool
        :returns: Pointer to new input. Only used during unittest
        """
        # logger.debug("location: {location}", location=location)

        location_id = location["id"]
        global_invoke_all('_locations_before_import_',
                          called_by=self,
                          location_id=location_id,
                          location=location,
                          )
        if location_id not in self.locations:
            global_invoke_all('_location_before_load_',
                              called_by=self,
                              location_id=location_id,
                              location=location,
                              )
            self.locations[location_id] = Location(self, location)
            global_invoke_all('_location_loaded_',
                              called_by=self,
                              location_id=location_id,
                              location=self.locations[location_id],
                              )
        elif location_id not in self.locations:

            global_invoke_all('_location_before_update_',
                              called_by=self,
                              location_id=location_id,
                              location=self.locations[location_id],
                              )
            self.locations[location_id].update_attributes(location)
            global_invoke_all('_location_updated_',
                              called_by=self,
                              location_id=location_id,
                              location=self.locations[location_id],
                              )

    def remove_location(self, location_id):
        """
        Remove a location from memory.
        
        :param location_id: 
        :return: 
        """
        if location_id in self.locations:
            del self.locations[location_id]

    def area_label(self,
                   area_id: dict(type=str, help="Area ID (location) to use for prepending to label"),
                   label: dict(type=str, help="Label to prepend Area to.")
                   ) -> dict(type=str, help="The result of:  area + label"):
        """
        Adds an area label to a provided string (label).
        """
        if area_id in self.locations:
            area_label = self.locations[area_id].label
            if area_label.lower() != "none" and area_label is not None:
                return "%s %s" % (area_label, label)
        return label

    def full_label(self,
                   location_id: dict(type=str, help="Location ID to use for prepending to label"),
                   area_id: dict(type=str, help="Area ID (location) to use for prepending to label"),
                   label: dict(type=str, help="Label to prepend Location and Area to.")
                   ) -> dict(type=str, help="The result of:  location + area + label"):
        """
        Adds location and area to a provided string (label).
        """
        output = ""
        if location_id in self.locations:
            location_label = self.locations[location_id].label
            if location_label.lower() != "none" and location_label is not None:
                output = location_label

        if area_id in self.locations:
            area_label = self.locations[area_id].label
            if area_label.lower() != "none" and area_label is not None:
                return "%s %s %s" % (output, area_label, label)
        return "%s %s" % (output, label)

    def get_all(self):
        """
        Returns a copy of the locations list.
        :return:
        """
        return self.locations.copy()

    def get(self, location_requested, location_type=None, limiter=None, status=None):
        """
        Performs the actual search.

        .. note::

           Can use the built in methods below or use get_meta/get to include 'location_type' limiter:

            >>> self.Locations['13ase45']

        or:

            >>> self.Locations['numeric']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param location_requested: The location ID or location label to search for.
        :type location_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the location to check for.
        :type status: int
        :return: Pointer to requested location.
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

        if location_requested in self.locations:
            item = self.locations[location_requested]
            if item.status != status:
                raise KeyError("Requested location found, but has invalid status: %s" % item.status)
            return item
        else:
            attrs = [
                {
                    'field': 'location_id',
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
                found, key, item, ratio, others = do_search_instance(attrs, self.locations,
                                                                     self.location_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest")
                # logger.debug("found location by search: others: {others}", others=others)
                if location_type is not None:
                    for other in others:
                        if other['value'].location_type == location_type and other['ratio'] > limiter:
                            return other['value']
                else:
                    if found:
                        return item
                raise KeyError("Location not found: %s" % location_requested)
            except YomboWarning as e:
                raise KeyError('Searched for %s, but had problems: %s' % (location_requested, e))

    def search(self, _limiter=None, _operation=None, **kwargs):
        """
        Search for location based on attributes for all locations.

        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the location to check for.
        :return: 
        """
        return search_instance(kwargs,
                               self.locations,
                               self.location_search_attributes,
                               _limiter,
                               _operation)

    @inlineCallbacks
    def add_location(self, data, **kwargs):
        """
        Add a location at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        location_results = yield self._YomboAPI.request('POST', '/v1/location', data)

        if location_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't add location",
                'apimsg': location_results['content']['message'],
                'apimsghtml': location_results['content']['html_message'],
            }
            return results

        results = {
            'status': 'success',
            'msg': "Location type added.",
            'location_id': location_results['data']['id'],
        }
        data['id'] = location_results['data']['id']
        data['updated_at'] = time()
        data['created_at'] = time()
        self._LocalDB.insert_locations(data)
        self.import_location(data)
        return results

    @inlineCallbacks
    def edit_location(self, location_id, data, **kwargs):
        """
        Edit a location at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """

        location_results = yield self._YomboAPI.request('PATCH', '/v1/location/%s' % (location_id), data)

        if location_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit location",
                'apimsg': location_results['content']['message'],
                'apimsghtml': location_results['content']['html_message'],
            }
            return results

        results = {
            'status': 'success',
            'msg': "Device type edited.",
            'location_id': location_results['data']['id'],
        }

        if location_id in self.locations:
            self.locations[location_id].update_attributes(data)
            self.locations[location_id].save_to_db(data)

        return results

    @inlineCallbacks
    def delete_location(self, location_id, **kwargs):
        """
        Delete a location at the Yombo server level, not at the local gateway level.

        :param location_id: The location ID to delete.
        :param kwargs:
        :return:
        """
        location_results = yield self._YomboAPI.request('DELETE', '/v1/location/%s' % location_id)

        if location_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete location",
                'apimsg': location_results['content']['message'],
                'apimsghtml': location_results['content']['html_message'],
            }
            return results

        results = {
            'status': 'success',
            'msg': "Location deleted.",
            'location_id': location_id,
        }

        self.remove_location(location_id)
        self._LocalDB.delete_locations(location_id)
        return results


class Location:
    """
    A class to manage a single location.
    :ivar location_id: (string) The unique ID.
    :ivar label: (string) Human label
    :ivar machine_label: (string) A non-changable machine label.
    :ivar category_id: (string) Reference category id.
    :ivar input_regex: (string) A regex to validate if user input is valid or not.
    :ivar always_load: (int) 1 if this item is loaded at startup, otherwise 0.
    :ivar status: (int) 0 - disabled, 1 - enabled, 2 - deleted
    :ivar public: (int) 0 - private, 1 - public pending approval, 2 - public
    :ivar created_at: (int) EPOCH time when created
    :ivar updated_at: (int) EPOCH time when last updated
    """

    def __init__(self, parent, location):
        """
        Setup the location object using information passed in.

        :param location: An location with all required items to create the class.
        :type location: dict

        """
        # logger.debug("Location info: {location}", location=location)

        self._Parent = parent
        self.location_id = location['id']

        # below are configure in update_attributes()
        self.location_type = None
        self.machine_label = None
        self.label = None
        self.description = None
        self.updated_at = None
        self.created_at = None
        self.update_attributes(location)

    def update_attributes(self, location):
        """
        Sets various values from a location dictionary. This can be called when either new or
        when updating.

        :param location: 
        :return: 
        """
        if 'location_type' in location:
            self.location_type = location['location_type']
        if 'machine_label' in location:
            self.machine_label = location['machine_label']
        if 'label' in location:
            self.label = location['label']
        if 'description' in location:
            self.description = location['description']
        if 'created_at' in location:
            self.created_at = location['created_at']
        if 'updated_at' in location:
            self.updated_at = location['updated_at']

    def save_to_db(self):
        self._Parent._LocalDB.update_locations(self)

    def __str__(self):
        """
        Print a string when printing the class.  This will return the location id so that
        the location can be identified and referenced easily.
        """
        return self.machine_label

    # def __repl__(self):
    #     """
    #     Export location variables as a dictionary.
    #     """
    #     return {
    #         'location_id': str(self.location_id),
    #         'location_type': str(self.location_type),
    #         'machine_label': str(self.machine_label),
    #         'label': str(self.label),
    #         'description': int(self.description),
    #         'created_at': int(self.created_at),
    #         'updated_at': str(self.updated_at),
    #     }
