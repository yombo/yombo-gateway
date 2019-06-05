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
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.core.log import get_logger
from yombo.mixins.sync_to_everywhere import SyncToEverywhere
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.locations")

class Locations(YomboLibrary, LibrarySearchMixin):
    """
    Manages locations for a gateway.
    """
    locations = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_attribute_name = "locations"
    _class_storage_fields = [
        "location_id", "label", "machine_label"
    ]
    _class_storage_sort_key = "machine_label"

    @property
    def location_id(self):
        return self.gateway_location.location_id

    @property
    def area_id(self):
        return self.gateway_area.location_id

    @property
    def location(self):
        return self.gateway_location

    @property
    def area(self):
        return self.gateway_area.location_id

    def __contains__(self, location_requested):
        """
        Checks to if a provided location ID or machine_label exists.

            >>> if "0kas02j1zss349k1" in self._Locations:
            >>> if "area:0kas02j1zss349k1" in self._Locations:

        or:

            >>> if "some_location_name" in self._Locations:

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

            >>> location = self._Locations["0kas02j1zss349k1"]  # by id
            >>> location = self._Locations["area:0kas02j1zss349k1"]  # include location type

        or:

            >>> location = self._Locations["alpnum"]  #by name

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
    def _load_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self._started = False

        yield self._load_locations_from_database()

        detected_location_info = self._Configs.detected_location_info
        if detected_location_info["ip"] is not None:
            self._States.set("detected_location.source", detected_location_info["source"],
                             value_type="string", source=self)
            self._States.set("detected_location.ip", detected_location_info["ip"],
                             value_type="string", source=self)
            self._States.set("detected_location.country_code", detected_location_info["country_code"],
                             value_type="string", source=self)
            self._States.set("detected_location.country_name", detected_location_info["country_name"],
                             value_type="string", source=self)
            self._States.set("detected_location.region_code", detected_location_info["region_code"],
                             value_type="string", source=self)
            self._States.set("detected_location.region_name", detected_location_info["region_name"],
                             value_type="string", source=self)
            self._States.set("detected_location.city", detected_location_info["city"],
                             value_type="string", source=self)
            self._States.set("detected_location.zip_code", detected_location_info["zip_code"],
                             value_type="string", source=self)
            self._States.set("detected_location.time_zone", detected_location_info["time_zone"],
                             value_type="string", source=self)
            self._States.set("detected_location.latitude", detected_location_info["latitude"],
                             value_type="float", source=self)
            self._States.set("detected_location.longitude", detected_location_info["longitude"],
                             value_type="float", source=self)
            self._States.set("detected_location.elevation", detected_location_info["elevation"],
                             value_type="int", source=self)
            self._States.set("detected_location.isp", detected_location_info["isp"],
                             value_type="string", source=self)
            self._States.set("detected_location.use_metric", detected_location_info["use_metric"],
                             value_type="bool", source=self)

            data = {
                "latitude": float(self._Configs.get("location", "latitude", detected_location_info["latitude"], False)),
                "longitude": float(self._Configs.get("location", "longitude", detected_location_info["longitude"], False)),
                "elevation": int(self._Configs.get("location", "elevation", detected_location_info["elevation"], False)),
                "city": str(self._Configs.get("location", "city", detected_location_info["city"], False)),
                "country_code": str(self._Configs.get("location", "country_code",  detected_location_info["country_code"], False)),
                "country_name": str(self._Configs.get("location", "country_name", detected_location_info["country_name"], False)),
                "region_code": str(self._Configs.get("location", "region_code", detected_location_info["region_code"], False)),
                "region_name": str(self._Configs.get("location", "region_name", detected_location_info["region_name"], False)),
                "time_zone": str(self._Configs.get("location", "time_zone", detected_location_info["time_zone"], False)),
                "zip_code": str(self._Configs.get("location", "zip_code", detected_location_info["zip_code"], False)),
            }
            for label, value in data.items():
                if value in (None, "", "None"):
                    self._Configs.set("location", label, detected_location_info[label])

            if self._Configs.get("location", "searchbox", None, False) in (None, "", "None"):
                searchbox = f"{detected_location_info['city']}, {detected_location_info['region_code']}, " \
                            f"{detected_location_info['country_code']}"
                self._Configs.set("location", "searchbox", searchbox)
        else:
            self._States.set("detected_location.source", None, source=self)
            self._States.set("detected_location.ip", None, source=self)
            self._States.set("detected_location.country_code", None, source=self)
            self._States.set("detected_location.country_name", None, source=self)
            self._States.set("detected_location.region_code", None, source=self)
            self._States.set("detected_location.region_name", None, source=self)
            self._States.set("detected_location.city", None, source=self)
            self._States.set("detected_location.zip_code", None, source=self)
            self._States.set("detected_location.time_zone", None, source=self)
            self._States.set("detected_location.latitude", None, source=self)
            self._States.set("detected_location.longitude", None, source=self)
            self._States.set("detected_location.isp", None, source=self)
            self._States.set("detected_location.elevation", 800, value_type="int", source=self)
            self._States.set("detected_location.use_metric", True, value_type="bool", source=self)

        # Gateway logical location.  House, bedroom, etc.
        self.gateway_location = self.get_default("location")
        self.gateway_area = self.get_default("area")

    def _start_(self, **kwargs):
        self._started = True

    @inlineCallbacks
    def _load_locations_from_database(self):
        """
        Loads locations from database and sends them to
        :py:meth:`_load_location_into_memory <Locations._load_location_into_memory>`

        This can be triggered either on system startup or when new/updated locations have been saved to the
        database and we need to refresh existing locations.
        """
        locations = yield self._LocalDB.get_locations()
        for location in locations:
            self._load_location_into_memory(location.__dict__)

        # Have "none" site location and area locations as defaults.
        self.locations["area_none"] = Location(self, {
            "id": "area_none",
            "location_type": "area",
            "machine_label": "none",
            "label": "None",
            "description": "Default when no 'area' location is assigned.",
            "updated_at": int(time()),
            "created_at": int(time()),
        })
        self.locations["location_none"] = Location(self, {
            "id": "location_none",
            "location_type": "location",
            "machine_label": "none",
            "label": "None",
            "description": "Default when no 'location' location is assigned.",
            "updated_at": int(time()),
            "created_at": int(time()),
        })

    def _load_location_into_memory(self, location, test_location=False):
        """
        Add a new locations to memory or update an existing locations.

        **Hooks called**:

        * _location_before_load_ : If added, sends location dictionary as "location"
        * _location_before_update_ : If updated, sends location dictionary as "location"
        * _location_loaded_ : If added, send the location instance as "location"
        * _location_updated_ : If updated, send the location instance as "location"

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
            global_invoke_all("_locations_before_import_",
                              called_by=self,
                              location_id=location_id,
                              location=location,
                              )
        if location_id not in self.locations:
            if self._started is True:
                global_invoke_all("_location_before_load_",
                              called_by=self,
                              location_id=location_id,
                              location=location,
                              )
            self.locations[location_id] = Location(self, location)
            if self._started is True:
                global_invoke_all("_location_loaded_",
                              called_by=self,
                              location_id=location_id,
                              location=self.locations[location_id],
                              )

        elif location_id not in self.locations:
            if self._started is True:
                global_invoke_all("_location_before_update_",
                              called_by=self,
                              location_id=location_id,
                              location=self.locations[location_id],
                              )
            self.locations[location_id].update_attributes(location)
            if self._started is True:
                global_invoke_all("_location_updated_",
                              called_by=self,
                              location_id=location_id,
                              location=self.locations[location_id],
                              )
        if self._started is True:
            global_invoke_all("_locations_imported_",
                          called_by=self,
                          location_id=location_id,
                          location=location,
                          )

    def area_label(self,
                   area_id: {'type': str, 'help': "Area ID (location) to use for prepending to label"},
                   label: {'type': str, 'help': "Label to prepend Area to."}
                   ) -> {'type': str, 'help': "The result of:  area + label"}:
        """
        Adds an area label to a provided string (label).
        """
        if area_id in self.locations:
            area_label = self.locations[area_id].label
            if area_label.lower() != "none" and area_label is not None:
                return f"{area_label} {label}"
        return label

    def full_label(self,
                   location_id: {'type': str, 'help': "Location ID to use for prepending to label"},
                   area_id: {'type': str, 'help': "Area ID (location) to use for prepending to label"},
                   label: {'type': str, 'help': "Label to prepend Location and Area to."}
                   ) -> {'type': str, 'help': "The result of:  location + area + label"}:
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
                return f"{output} {area_label} {label}"
        return f"{output} {label}"

    def get_default(self, location_type):
        """
        Get a default location. This only work when there is only one other location other than None. Returns
        "none" location if there are multiple.

        :param location_type:
        :return:
        """
        if location_type not in ("area", "location"):
            raise YomboWarning(f"Unknown location_type: {location_type}")

        default_id = self._Configs.get("location", "{location_type}_id", None, True)
        if default_id is not None:
            try:
                print(f"searching for: {default_id}")
                location = self.get(default_id)
                self._Configs.set("location", f"{location_type}_id", location.location_id)
                return location
            except KeyError:
                pass

        none_id = None
        for location_id, location in self.locations.items():
            if location.location_type != location_type:
                continue

            if location.machine_label == "none":
                none_id = location
                continue

            if location.machine_label != "none":
                self._Configs.set("location", f"{location_type}_id", location.location_id)
                return location

        if none_id is None:
            raise KeyError("Unknown location...")
        return none_id

    @inlineCallbacks
    def add_location(self, data, **kwargs):
        """
        Add a location at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            location_results = yield self._YomboAPI.request("POST", "/v1/location",
                                                            data,
                                                            session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't add location: {e.message}",
                "apimsg": f"Couldn't add location: {e.message}",
                "apimsghtml": f"Couldn't add location: {e.html_message}",
            }

        data["id"] = location_results["data"]["id"]
        data["updated_at"] = time()
        data["created_at"] = time()
        self._LocalDB.insert_locations(data)
        self._load_location_into_memory(data)

        return {
            "status": "success",
            "msg": "Location type added.",
            "location_id": location_results["data"]["id"],
        }

    @inlineCallbacks
    def edit_location(self, location_id, data, **kwargs):
        """
        Edit a location at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        if data["machine_label"] == "none":
            return {
                "status": "failed",
                "msg": "Cannot edit default locations.",
                "apimsg": "Cannot edit default locations.",
                "apimsghtml": "Cannot edit default locations.",
            }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            location_results = yield self._YomboAPI.request("PATCH", f"/v1/location/{location_id}",
                                                            data,
                                                            session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't edit location: {e.message}",
                "apimsg": f"Couldn't edit location: {e.message}",
                "apimsghtml": f"Couldn't edit location: {e.html_message}",
            }

        if location_id in self.locations:
            self.locations[location_id].update_attributes(data)

        global_invoke_all("_locations_updated_",
                          called_by=self,
                          location_id=location_id,
                          location=self.locations[location_id],
                          )

        return {
            "status": "success",
            "msg": "Device type edited.",
            "location_id": location_results["data"]["id"],
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
        if location["machine_label"] == "none":
            return {
                "status": "failed",
                "msg": "Cannot delete default locations.",
                "apimsg": "Cannot delete default locations.",
                "apimsghtml": "Cannot delete default locations.",
            }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            yield self._YomboAPI.request("DELETE", f"/v1/location/{location.location_id}",
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't delete location: {e.message}",
                "apimsg": f"Couldn't delete location: {e.message}",
                "apimsghtml": f"Couldn't delete location: {e.html_message}",
            }

        if location_id in self.locations:
            del self.locations[location_id]

        global_invoke_all("_locations_deleted_",
                          called_by=self,
                          location_id=location_id,
                          location=self.locations[location_id],
                          )

        self._LocalDB.delete_locations(location_id)
        return {
            "status": "success",
            "msg": "Location deleted.",
            "location_id": location_id,
        }


class Location(Entity, SyncToEverywhere):
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
        self._internal_label = "locations"  # Used by mixins
        super().__init__(parent)

        #: str: ID for the location.
        self.location_id = location["id"]

        # below are configure in update_attributes()
        #: str: Type of location, one of: area, location
        self.location_type = None
        self.machine_label = None
        self.label = None
        self.description = None
        self.updated_at = None
        self.created_at = None
        self.update_attributes(location, source="database")
        self.start_data_sync()

    def update_attributes(self, incoming, source=None):
        """
        Sets various values from an incoming dictionary. This can be called when either new or
        when updating.

        :param incoming:
        :return:
        """
        if "incoming_type" in incoming:
            if incoming["incoming_type"].lower() not in ("area", "incoming", "none"):
                raise YomboWarning(
                    f"incoming_type must be one of: area, incoming.  Received: {incoming['incoming_type']}")
            incoming["incoming_type"] = incoming["incoming_type"].lower()

        super().update_attributes(incoming, source=source)

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
    #         "location_id": str(self.location_id),
    #         "location_type": str(self.location_type),
    #         "machine_label": str(self.machine_label),
    #         "label": str(self.label),
    #         "description": int(self.description),
    #         "created_at": int(self.created_at),
    #         "updated_at": str(self.updated_at),
    #     }
