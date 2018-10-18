# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Locations @ Library Documentation <https://yombo.net/docs/libraries/locations>`_

Stores location and area information in memory.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.14.0

:copyright: Copyright 2017-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/locations.html>`_
"""
from collections import OrderedDict
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.yombobasemixin import YomboBaseMixin
from yombo.utils import search_instance, do_search_instance, global_invoke_all

logger = get_logger('library.locations')

class Locations(YomboLibrary):
    """
    Manages locations for a gateway.
    """
    @property
    def locations_sorted(self):
        return OrderedDict(sorted(self.locations.items(), key=lambda x: x[1].label))

    @property
    def location_id(self):
        return self.gateway_location_id()

    @property
    def area_id(self):
        return self.gateway_area_id()

    @property
    def location(self):
        location = self.gateway_location_id()
        return self.get(location)

    @property
    def area(self):
        location = self.gateway_area_id()
        return self.get(location)

    def __contains__(self, location_requested):
        """
        Checks to if a provided location ID or machine_label exists.

            >>> if '0kas02j1zss349k1' in self._Locations:
            >>> if 'area:0kas02j1zss349k1' in self._Locations:

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
            self.get(location_requested)
            return True
        except:
            return False

    def __getitem__(self, location_requested):
        """
        Attempts to find the location requested using a couple of methods.

            >>> location = self.Locations['0kas02j1zss349k1']  # by id
            >>> location = self.Locations['area:0kas02j1zss349k1']  # include location type

        or:

            >>> location = self.Locations['alpnum']  #by name

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param location_requested: The location ID or machine_label to search for.
        :type location_requested: string
        :return: A pointer to the location type instance.
        :rtype: instance
        """
        return self.get(location_requested)

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
        return "Yombo locations library"

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

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self._started = False
        self.locations = {}
        self.location_search_attributes = ['location_id', 'label', 'machine_label']

        yield self._load_locations_from_database()

        location_info = self._Configs.location_info
        if location_info['ip'] is not None:
            self._States.set('detected_location.source', location_info['source'],
                             value_type='string', source=self)
            self._States.set('detected_location.ip', location_info['ip'],
                             value_type='string', source=self)
            self._States.set('detected_location.country_code', location_info['country_code'],
                             value_type='string', source=self)
            self._States.set('detected_location.country_name', location_info['country_name'],
                             value_type='string', source=self)
            self._States.set('detected_location.region_code', location_info['region_code'],
                             value_type='string', source=self)
            self._States.set('detected_location.region_name', location_info['region_name'],
                             value_type='string', source=self)
            self._States.set('detected_location.city', location_info['city'],
                             value_type='string', source=self)
            self._States.set('detected_location.zip_code', location_info['zip_code'],
                             value_type='string', source=self)
            self._States.set('detected_location.time_zone', location_info['time_zone'],
                             value_type='string', source=self)
            self._States.set('detected_location.latitude', location_info['latitude'],
                             value_type='float', source=self)
            self._States.set('detected_location.longitude', location_info['longitude'],
                             value_type='float', source=self)
            self._States.set('detected_location.elevation', location_info['elevation'],
                             value_type='int', source=self)
            self._States.set('detected_location.isp', location_info['isp'],
                             value_type='string', source=self)
            self._States.set('detected_location.use_metric', location_info['use_metric'],
                             value_type='bool', source=self)

            data = {
                'latitude': float(self._Configs.get('location', 'latitude', location_info['latitude'], False)),
                'longitude': float(self._Configs.get('location', 'longitude', location_info['longitude'], False)),
                'elevation': int(self._Configs.get('location', 'elevation', location_info['elevation'], False)),
                'city': str(self._Configs.get('location', 'city', location_info['city'], False)),
                'country_code': str(self._Configs.get('location', 'country_code',  location_info['country_code'], False)),
                'country_name': str(self._Configs.get('location', 'country_name', location_info['country_name'], False)),
                'region_code': str(self._Configs.get('location', 'region_code', location_info['region_code'], False)),
                'region_name': str(self._Configs.get('location', 'region_name', location_info['region_name'], False)),
                'time_zone': str(self._Configs.get('location', 'time_zone', location_info['time_zone'], False)),
                'zip_code': str(self._Configs.get('location', 'zip_code', location_info['zip_code'], False)),
            }
            for label, value in data.items():
                if value in (None, '', 'None'):
                    self._Configs.set('location', label, location_info[label])

            if self._Configs.get('location', 'searchbox', None, False) in (None, '', 'None'):
                searchbox = "%s, %s, %s" % (location_info['city'],
                                          location_info['region_code'],
                                          location_info['country_code'])
                self._Configs.set('location', 'searchbox', searchbox)
        else:
            self._States.set('detected_location.source', None, source=self)
            self._States.set('detected_location.ip', None, source=self)
            self._States.set('detected_location.country_code', None, source=self)
            self._States.set('detected_location.country_name', None, source=self)
            self._States.set('detected_location.region_code', None, source=self)
            self._States.set('detected_location.region_name', None, source=self)
            self._States.set('detected_location.city', None, source=self)
            self._States.set('detected_location.zip_code', None, source=self)
            self._States.set('detected_location.time_zone', None, source=self)
            self._States.set('detected_location.latitude', None, source=self)
            self._States.set('detected_location.longitude', None, source=self)
            self._States.set('detected_location.isp', None, source=self)
            self._States.set('detected_location.elevation', 800, value_type='int', source=self)
            self._States.set('detected_location.use_metric', True, value_type='bool', source=self)

        # Gateway logical location.  House, bedroom, etc.
        self.gateway_location_id = self._Configs.get2('location', 'location_id', self.get_default('location'), True)
        self.gateway_area_id = self._Configs.get2('location', 'area_id', self.get_default('area'), True)

    def _start_(self, **kwargs):
        self._started = True

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

        # Stop here if not in run mode.
        if self._Loader.operating_mode != 'run':
            return

        # Now check to make sure we have bare minimum locations for none.
        try:
            location = self.get("area:none")
        except KeyError:
            logger.warn("No default 'area' location, creating one...")
            yield self.add_location({
                'machine_label': 'none',
                'label': 'none',
                'location_type': 'area',
                'description': "Default when no 'area' location is assigned.",
            })

        try:
            location = self.get("location:none")
        except KeyError:
            logger.warn("No default 'location' location, creating one...")
            yield self.add_location({
                'machine_label': 'none',
                'label': 'none',
                'location_type': 'location',
                'description': "Default when no 'location' location is assigned.",
            })

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
        # Stop here if not in run mode.
        if self._started is True:
            global_invoke_all('_locations_before_import_',
                              called_by=self,
                              location_id=location_id,
                              location=location,
                              )
        if location_id not in self.locations:
            if self._started is True:
                global_invoke_all('_location_before_load_',
                              called_by=self,
                              location_id=location_id,
                              location=location,
                              )
            self.locations[location_id] = Location(self, location)
            if self._started is True:
                global_invoke_all('_location_loaded_',
                              called_by=self,
                              location_id=location_id,
                              location=self.locations[location_id],
                              )

        elif location_id not in self.locations:
            if self._started is True:
                global_invoke_all('_location_before_update_',
                              called_by=self,
                              location_id=location_id,
                              location=self.locations[location_id],
                              )
            self.locations[location_id].update_attributes(location)
            if self._started is True:
                global_invoke_all('_location_updated_',
                              called_by=self,
                              location_id=location_id,
                              location=self.locations[location_id],
                              )
        if self._started is True:
            global_invoke_all('_locations_imported_',
                          called_by=self,
                          location_id=location_id,
                          location=location,
                          )

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

    def get_default(self, location_type):
        """
        Get a default location. This only work when there is only one other location other than None. Returns
        'none' location if there are multiple.

        :param location_type:
        :return:
        """
        if location_type not in ('area', 'location'):
            raise YomboWarning("Unknown location_type: %s" % location_type)

        found_id = None
        for location_id, location in self.locations.items():
            if location.location_type != location_type:
                continue
            if found_id is None or location.machine_label != 'none':
                found_id = location_id

        return found_id

    def get(self, location_requested, location_type=None, limiter=None):
        """
        Performs the actual search.

        .. note::

           Modules can also simply treat this library as a dictionary to lookup items, however, this will search
           any location type.

            >>> self.Locations['13ase45']

        or:

            >>> self.Locations['numeric']

        To specify a location type, use this format for the string:   location_type:location_id

            >>> self.Locations['area:13ase45']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param location_requested: The location ID or location label to search for.
        :type location_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :return: Pointer to requested location.
        :rtype: dict
        """
        if limiter is None:
            limiter = .89

        if limiter > .99999999:
            limiter = .99
        elif limiter < .10:
            limiter = .10

        if ":" in location_requested:
            location_type, location_requested = location_requested.split(':', 1)

        if location_requested in self.locations:
            item = self.locations[location_requested]
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
                logger.debug("Get is about to call search...: %s" % location_requested)
                # found, key, item, ratio, others = self._search(attrs, operation="highest")
                found, key, item, ratio, others = do_search_instance(attrs, self.locations,
                                                                     self.location_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest")
                logger.debug("found location by search: others: {others}", others=others)
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
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            location_results = yield self._YomboAPI.request('POST', '/v1/location',
                                                            data,
                                                            session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't add location: %s" % e.message,
                'apimsg': "Couldn't add location: %s" % e.message,
                'apimsghtml': "Couldn't add location: %s" % e.html_message,
            }

        data['id'] = location_results['data']['id']
        data['updated_at'] = time()
        data['created_at'] = time()
        self._LocalDB.insert_locations(data)
        self.import_location(data)

        return {
            'status': 'success',
            'msg': "Location type added.",
            'location_id': location_results['data']['id'],
        }

    @inlineCallbacks
    def edit_location(self, location_id, data, **kwargs):
        """
        Edit a location at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        if data['machine_label'] == 'none':
            return {
                'status': 'failed',
                'msg': "Cannot edit default locations.",
                'apimsg': "Cannot edit default locations.",
                'apimsghtml': "Cannot edit default locations.",
            }

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            location_results = yield self._YomboAPI.request('PATCH', '/v1/location/%s' % (location_id),
                                                            data,
                                                            session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't edit location: %s" % e.message,
                'apimsg': "Couldn't edit location: %s" % e.message,
                'apimsghtml': "Couldn't edit location: %s" % e.html_message,
            }

        if location_id in self.locations:
            self.locations[location_id].update_attributes(data)
            self.locations[location_id].save_to_db()

        global_invoke_all('_locations_updated_',
                          called_by=self,
                          location_id=location_id,
                          location=self.locations[location_id],
                          )

        return {
            'status': 'success',
            'msg': "Device type edited.",
            'location_id': location_results['data']['id'],
        }

    @inlineCallbacks
    def delete_location(self, location_id, **kwargs):
        """
        Delete a location at the Yombo server level, not at the local gateway level.

        :param location_id: The location ID to delete.
        :param kwargs:
        :return:
        """
        location = self.get(location_id)
        if location['machine_label'] == 'none':
            return {
                'status': 'failed',
                'msg': "Cannot delete default locations.",
                'apimsg': "Cannot delete default locations.",
                'apimsghtml': "Cannot delete default locations.",
            }

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            yield self._YomboAPI.request('DELETE', '/v1/location/%s' % location.location_id,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't delete location: %s" % e.message,
                'apimsg': "Couldn't delete location: %s" % e.message,
                'apimsghtml': "Couldn't delete location: %s" % e.html_message,
            }

        if location_id in self.locations:
            del self.locations[location_id]

        global_invoke_all('_locations_deleted_',
                          called_by=self,
                          location_id=location_id,
                          location=self.locations[location_id],
                          )

        self._LocalDB.delete_locations(location_id)
        return {
            'status': 'success',
            'msg': "Location deleted.",
            'location_id': location_id,
        }


class Location(YomboBaseMixin):
    """
    A class to manage a single location.

    :ivar machine_label: (string) A non-changable machine label.
    :ivar label: (string) Human label
    :ivar description: (string) Description of the location or area.
    :ivar created_at: (int) EPOCH time when created
    :ivar updated_at: (int) EPOCH time when last updated
    """

    def __init__(self, parent, location):
        """
        Setup the location object using information passed in.

        :param location: An location with all required items to create the class.
        :type location: dict
        """
        super().__init__(parent)

        # logger.debug("Location info: {location}", location=location)

        #: str: ID for the location.
        self.location_id = location['id']

        # below are configure in update_attributes()
        #: str: Type of location, one of: area, location
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
            if location['location_type'].lower() not in ('area', 'location', 'none'):
                raise YomboWarning("location_type must be one of: area, location.  Received: %s" % location['location_type'])
            self.location_type = location['location_type'].lower()
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
