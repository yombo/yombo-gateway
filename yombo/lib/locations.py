# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Locations @ Library Documentation <https://yombo.net/docs/libraries/locations>`_

Stores location and area information in memory.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.14.0

:copyright: Copyright 2017-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/locations.html>`_
"""
import ipaddress
import math
import pycountry
from time import time
import treq
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import LocationSchema
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

# IPIFY provides our external IP address.
IPIFY_API4 = "https://api.ipify.org"  # get our IPv4 address
IPIFY_API6 = "https://api6.ipify.org"  # get our IPv6 address, returns IPV4 if IPv6 is missing

# These additional details about the ip addresses, such as location information. This information is used
# internally to set the default location for the gateway.
IPINFO_API = "https://ipinfo.io/{0}"

# Cannot find a free elevation API, if you find one please submit a PR or sent a link to supprt@yombo.net

# Constants from https://github.com/maurycyp/vincenty
# Earth ellipsoid according to WGS 84
# Axis a of the ellipsoid (Radius of the earth in meters)
AXIS_A = 6378137
# Flattening f = (a-b) / a
FLATTENING = 1 / 298.257223563
# Axis b of the ellipsoid in meters.
AXIS_B = 6356752.314245

MILES_PER_KILOMETER = 0.621371
MAX_ITERATIONS = 200
CONVERGENCE_THRESHOLD = 1e-12

logger = get_logger("library.locations")


class Location(Entity, LibraryDBChildMixin):
    """
    A class to manage a single location.

    :ivar machine_label: (string) A non-changable machine label.
    :ivar label: (string) Human label
    :ivar description: (string) Description of the location or area.
    :ivar created_at: (int) EPOCH time when created
    :ivar updated_at: (int) EPOCH time when last updated
    """
    _Entity_type: ClassVar[str] = "Location"
    _Entity_label_attribute: ClassVar[str] = "machine_label"

    def __repr__(self):
        """
        Returns some info about the current child object.

        :return: Returns some info about the current child object.
        :rtype: string
        """
        return f"<Location: {self.location_id}:{self.machine_label}>"

    def load_an_item_to_memory_pre_process(self, incoming: dict, **kwargs) -> None:
        self.update_attributes_pre_process(incoming, **kwargs)

    def update_attributes_pre_process(self, incoming, **kwargs):
        """
        Sets various values from an incoming dictionary. This can be called when either new or
        when updating.

        :param incoming:
        :return:
        """
        if "location_type" in incoming:
            if incoming["location_type"].lower() not in ("area", "locaiton"):
                raise YomboWarning(
                    f"location_type must be one of: area, location.  Received: {incoming['location_type']}")
            incoming["location_type"] = incoming["location_type"].lower()


class Locations(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages locations for a gateway.
    """
    locations: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "location_id"
    _storage_class_reference: ClassVar = Location
    _storage_schema: ClassVar = LocationSchema()
    _storage_attribute_name: ClassVar[str] = "locations"
    _storage_label_name: ClassVar[str] = "location"
    _storage_search_fields: ClassVar[List[str]] = [
        "location_id", "machine_label", "label"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "label"
    _storage_attribute_sort_key_order: ClassVar[str] = "asc"

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
    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        yield self.load_from_database()
        try:
            self.get_by_type("area", "none")
        except KeyError:
            yield self.load_an_item_to_memory({
                "id": "area_none",
                "user_id": "yombo_system_account",
                "location_type": "area",
                "machine_label": "none",
                "label": "None",
                "description": "Default when no 'area' location is assigned.",
                "updated_at": int(time()),
                "created_at": int(time()),
                },
                load_source="local",
                request_context="locations::init",
                authentication=self.AUTH_USER
            )

        try:
            self.get_by_type("location", "none")
        except KeyError:
            yield self.load_an_item_to_memory({
                "id": "location_none",
                "user_id": "yombo_system_account",
                "location_type": "location",
                "machine_label": "none",
                "label": "None",
                "description": "Default when no 'location' location is assigned.",
                "updated_at": int(time()),
                "created_at": int(time()),
                },
                load_source="local",
                request_context="locations::init",
                authentication=self.AUTH_USER
            )

        detected_location_info = self._Configs.detected_location_info
        if detected_location_info["source"] is not None:
            yield self._States.set_yield("detected_location.source", detected_location_info["source"],
                                         value_type="string", authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.ipv4", detected_location_info["ipv4"],
                                         value_type="string", authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.ipv6", detected_location_info["ipv6"],
                                         value_type="string", authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.country_code", detected_location_info["country_code"],
                                         value_type="string", authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.country_name", detected_location_info["country_name"],
                                         value_type="string", authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.region_name", detected_location_info["region_name"],
                                         value_type="string", authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.city", detected_location_info["city"],
                                         value_type="string", authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.time_zone", detected_location_info["time_zone"],
                                         value_type="string", authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.latitude", detected_location_info["latitude"],
                                         value_type="float", authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.longitude", detected_location_info["longitude"],
                                         value_type="float", authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.elevation", detected_location_info["elevation"],
                                         value_type="int", authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.isp", detected_location_info["isp"],
                                         value_type="string", authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.use_metric", detected_location_info["use_metric"],
                                         value_type="bool", authentication=self.AUTH_USER)

            data = {
                "latitude": float(self._Configs.get("location.latitude", detected_location_info["latitude"], False)),
                "longitude": float(self._Configs.get("location.longitude", detected_location_info["longitude"], False)),
                "elevation": int(self._Configs.get("location.elevation", detected_location_info["elevation"], False)),
                "city": str(self._Configs.get("location.city", detected_location_info["city"], False)),
                "country_code": str(self._Configs.get("location.country_code",  detected_location_info["country_code"], False)),
                "country_name": str(self._Configs.get("location.country_name", detected_location_info["country_name"], False)),
                "region_name": str(self._Configs.get("location.region_name", detected_location_info["region_name"], False)),
                "time_zone": str(self._Configs.get("location.time_zone", detected_location_info["time_zone"], False)),
            }
            for label, value in data.items():
                if value in (None, "", "None"):
                    self._Configs.set(f"location.{label}", detected_location_info[label], ref_source=self)

            if self._Configs.get("location.searchbox", None, False) in (None, "", "None"):
                searchbox = f"{detected_location_info['city']}, {detected_location_info['region_name']}, " \
                            f"{detected_location_info['country_code']}"
                self._Configs.set("location.searchbox", searchbox, ref_source=self)
        else:
            yield self._States.set_yield("detected_location.source", None, authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.ipv4", None, authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.ipv6", None, authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.country_code", None, authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.country_name", None, authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.region_name", None, authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.city", None, authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.zip_code", None, authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.time_zone", None, authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.latitude", None, authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.longitude", None, authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.isp", None, authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.elevation", 800, value_type="int",
                                         authentication=self.AUTH_USER)
            yield self._States.set_yield("detected_location.use_metric", True, value_type="bool",
                                         authentication=self.AUTH_USER)

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

    def get_by_type(self, location_type: str, machine_label: Optional[str] = None) -> Union[dict, Location]:
        """
        Get location by it's type (area or location). If machine_label is supplied, will search for that.

        :param machine_label:
        :return:
        """
        if location_type not in ("area", "location"):
            raise YomboWarning("location_type must be one of: area or lcoation")
        results = {}
        for location_id, location in self.locations.items():
            if location.location_type == location_type:
                if machine_label is None:
                    results[location_id] = location
                elif machine_label == location.machine_label:
                    return location
        if machine_label is not None:
            raise KeyError(f"Location not found: {location_type} - {machine_label}")
        return results

    def get_default(self, location_type):
        """
        Get a default location. This only work when there is only one other location other than None. Returns
        "none" location if there are multiple.

        :param location_type:
        :return:
        """
        if location_type not in ("area", "location"):
            raise YomboWarning(f"Unknown location_type: {location_type}")

        default_id = self._Configs.get(f"location.{location_type}_id", None, True)
        if default_id is not None:
            try:
                location = self.get(default_id)
                self._Configs.set(f"location.{location_type}_id", location.location_id)
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
                self._Configs.set(f"location.{location_type}_id", location.location_id)
                return location

        if none_id is None:
            raise KeyError("Unknown location...")
        return none_id

    @classmethod
    def distance(cls, lat1, lon1, lat2, lon2):
        """Calculate the distance in meters between two points.

        Async friendly.
        """
        return cls.vincenty((lat1, lon1), (lat2, lon2)) * 1000

    # Author: https://github.com/maurycyp
    # Source: https://github.com/maurycyp/vincenty
    # License: https://github.com/maurycyp/vincenty/blob/master/LICENSE
    # pylint: disable=invalid-name, unused-variable, invalid-sequence-index
    @staticmethod
    def vincenty(point1: Tuple[float, float], point2: Tuple[float, float],
                 miles: bool = True) -> Optional[float]:
        """
        Vincenty formula (inverse method) to calculate the distance.

        Result in kilometers or miles between two points on the surface of a
        spheroid.

        Async friendly.
        """
        # short-circuit coincident points
        if point1[0] == point2[0] and point1[1] == point2[1]:
            return 0.0

        U1 = math.atan((1 - FLATTENING) * math.tan(math.radians(point1[0])))
        U2 = math.atan((1 - FLATTENING) * math.tan(math.radians(point2[0])))
        L = math.radians(point2[1] - point1[1])
        Lambda = L

        sinU1 = math.sin(U1)
        cosU1 = math.cos(U1)
        sinU2 = math.sin(U2)
        cosU2 = math.cos(U2)

        for _ in range(MAX_ITERATIONS):
            sinLambda = math.sin(Lambda)
            cosLambda = math.cos(Lambda)
            sinSigma = math.sqrt((cosU2 * sinLambda) ** 2 +
                                 (cosU1 * sinU2 - sinU1 * cosU2 * cosLambda) ** 2)
            if sinSigma == 0:
                return 0.0  # coincident points
            cosSigma = sinU1 * sinU2 + cosU1 * cosU2 * cosLambda
            sigma = math.atan2(sinSigma, cosSigma)
            sinAlpha = cosU1 * cosU2 * sinLambda / sinSigma
            cosSqAlpha = 1 - sinAlpha ** 2
            try:
                cos2SigmaM = cosSigma - 2 * sinU1 * sinU2 / cosSqAlpha
            except ZeroDivisionError:
                cos2SigmaM = 0
            C = FLATTENING / 16 * cosSqAlpha * (4 + FLATTENING * (4 - 3 *
                                                                  cosSqAlpha))
            LambdaPrev = Lambda
            Lambda = L + (1 - C) * FLATTENING * sinAlpha * (sigma + C * sinSigma *
                                                            (cos2SigmaM + C *
                                                             cosSigma *
                                                             (-1 + 2 *
                                                              cos2SigmaM ** 2)))
            if abs(Lambda - LambdaPrev) < CONVERGENCE_THRESHOLD:
                break  # successful convergence
        else:
            return None  # failure to converge

        uSq = cosSqAlpha * (AXIS_A ** 2 - AXIS_B ** 2) / (AXIS_B ** 2)
        A = 1 + uSq / 16384 * (4096 + uSq * (-768 + uSq * (320 - 175 * uSq)))
        B = uSq / 1024 * (256 + uSq * (-128 + uSq * (74 - 47 * uSq)))
        deltaSigma = B * sinSigma * (cos2SigmaM +
                                     B / 4 * (cosSigma * (-1 + 2 *
                                                          cos2SigmaM ** 2) -
                                              B / 6 * cos2SigmaM *
                                              (-3 + 4 * sinSigma ** 2) *
                                              (-3 + 4 * cos2SigmaM ** 2)))
        s = AXIS_B * A * (sigma - deltaSigma)

        s /= 1000  # Conversion of meters to kilometers
        if miles:
            s *= MILES_PER_KILOMETER  # kilometers to miles

        return round(s, 6)

    @classmethod
    @inlineCallbacks
    def detect_location_info(cls):
        """Detect location information."""
        data = None
        ipv4, ipv6 = yield cls._get_ipify()
        try:
            data = yield cls._get_ipinfo()
        except Exception as e:
            logger.warn(f"Unable to get ip information from ipinfo: {e}")

        if data is None:
            data = {
                "source": None,
                "city": None,
                "region_name": None,
                "country_code": None,
                "latitude": None,
                "longitude": None,
                "time_zone": None,
                "isp": None,
                "elevation": 800,
                "use_metric": True,
            }
        else:
            data["use_metric"] = data["country_code"] not in ("US", "MM", "LR")
            data["elevation"] = 800  # Just a made up elevation until an open API can be found.

        data["ipv4"] = ipv4
        data["ipv6"] = ipv6
        return data

    @classmethod
    @inlineCallbacks
    def _get_ipify(cls) -> list:
        """Query ipify.org ip address information."""
        try:
            response = yield treq.get(IPIFY_API4, timeout=5)
            ipv4 = yield response.text()
        except Exception as e:
            ipv4 = None
        try:
            response = yield treq.get(IPIFY_API6, timeout=5)
            ipv6 = yield response.text()
        except Exception as e:
            ipv6 = None

        #IPIFY returns None address if IPV6 is not found.
        if ipv6 is not None:
            ip_v6_test = ipaddress.ip_address(ipv6)
            if ip_v6_test.version != 6:
                ipv6 = None
        return ipv4, ipv6

    @classmethod
    @inlineCallbacks
    def _get_ipinfo(cls, ip_address: str = None) -> Optional[Dict[str, Any]]:
        """Query ipinfo.io for IP address location data."""
        if ip_address is None:
            ip_address = "json"

        url = IPINFO_API.format(ip_address)
        try:
            response = yield treq.get(url, timeout=5)
        except Exception as e:
            return None
        content = yield treq.content(response)
        raw_info = cls._Tools.data_unpickle(content, "json")
        latitude, longitude = raw_info["loc"].split(",", 1)
        if len(raw_info["country"]) == 0:
            country_name = ""
        else:
            country = pycountry.countries.get(alpha_2=raw_info.get("country", "").upper())
            country_name = country.name

        return {
            "source": "ipinfo",
            "city": raw_info.get("city", ""),
            "region_name": raw_info.get("region", ""),
            "country_code": raw_info.get("country", "").upper(),
            "country_name": country_name,
            "latitude": latitude,
            "longitude": longitude,
            "time_zone": raw_info.get("timezone", ""),
            "isp": raw_info.get("org", ""),
        }
