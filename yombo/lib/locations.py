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
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.sync_to_everywhere_mixin import SyncToEverywhereMixin
from yombo.mixins.library_db_model_mixin import LibraryDBModelMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

logger = get_logger("library.locations")


class Location(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
    """
    A class to manage a single location.

    :ivar machine_label: (string) A non-changable machine label.
    :ivar label: (string) Human label
    :ivar description: (string) Description of the location or area.
    :ivar created_at: (int) EPOCH time when created
    :ivar updated_at: (int) EPOCH time when last updated
    """
    _primary_column = "location_id"  # Used by mixins

    def __init__(self, parent, incoming, source=None):
        """
        Setup the location object using information passed in.

        :param location: An location with all required items to create the class.
        :type location: dict
        """
        self._Entity_type = "Location"
        self._Entity_label_attribute = "machine_label"
        super().__init__(parent)
        self._setup_class_model(incoming, source=source)

    def __repr__(self):
        """
        Returns some info about the current child object.

        :return: Returns some info about the current child object.
        :rtype: string
        """
        return f"<Location: {self.location_id}:{self.machine_label}>"

    def update_attributes_preprocess(self, incoming):
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


class Locations(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Manages locations for a gateway.
    """
    locations = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "location"
    _class_storage_load_db_class = Location
    _class_storage_attribute_name = "locations"
    _class_storage_search_fields = [
        "location_id", "machine_label", "label"
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


    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        yield self._class_storage_load_from_database()

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
            print(self.__repr__)
            print(self.locations)
            raise KeyError("Unknown location...")
        return none_id
