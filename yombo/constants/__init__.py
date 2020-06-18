# -*- coding: utf-8 -*-
#  This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Various constants used throughout the system. These allow various values to be easily referenced
throughout the Yombo Gateway framework to maintain consistency.

The constant values are not fully documented here, see the
`constants source code <https://github.com/yombo/yombo-gateway/tree/master/yombo/constants>`_ for a full list.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.17.0


:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
"""
MAJOR_VERSION = 0
MINOR_VERSION = 24
PATCH_VERSION = "0-alpha-7"
PATCH_VERSION_NUMBER = "0.7"
__short_version__ = f"{MAJOR_VERSION}.{MINOR_VERSION}"
__version__ = f"{__short_version__}.{PATCH_VERSION_NUMBER}"

# Yombo gateway version number
VERSION = __version__
VERSION_NUMBER = f"{__short_version__}.{PATCH_VERSION}"

MODULE_API_VERSION = 1

# Used to detect defaults that include None.
SENTINEL = object()

LOCAL_SOURCES = ["local", "database", "yombo", "system"]
# Days of the week
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Measurement systems
MISC_UNIT_SYSTEM_METRIC = "metric"  # type: str
MISC_UNIT_SYSTEM_IMPERIAL = "imperial"  # type: str

# Temperature systems
TEMP_CELSIUS = "°C"
TEMP_FAHRENHEIT = "°F"

# Misc Attributes

ATR_ICON = "icon"
ATR_CODE = "code"

# #### Status values
DISABLED = "disabled"
ENABLED = "enabled"
DELETED = "deleted"

STATUS_PAST = {
    0: DISABLED,
    1: ENABLED,
    2: DELETED
}

DISABLE = "disable"
ENABLE = "enable"
DELETE = "delete"

STATUS = {
    0: DISABLE,
    1: ENABLE,
    2: DELETE
}

# #### States ####
STATE_ON = "on"
STATE_OFF = "off"
STATE_HOME = "home"
STATE_NOT_HOME = "not_home"
STATE_UNKNOWN = "unknown"
STATE_OPEN = "open"
STATE_OPENING = "opening"
STATE_CLOSED = "closed"
STATE_CLOSING = "closing"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_IDLE = "idle"
STATE_STANDBY = "standby"
STATE_ALARM_DISARMED = "disarmed"
STATE_ALARM_ARMED_HOME = "armed_home"
STATE_ALARM_ARMED_AWAY = "armed_away"
STATE_ALARM_ARMED_NIGHT = "armed_night"
STATE_ALARM_ARMED_CUSTOM_BYPASS = "armed_custom_bypass"
STATE_ALARM_PENDING = "pending"
STATE_ALARM_ARMING = "arming"
STATE_ALARM_DISARMING = "disarming"
STATE_ALARM_TRIGGERED = "triggered"
STATE_LOCKED = "locked"
STATE_UNLOCKED = "unlocked"
STATE_UNAVAILABLE = "unavailable"
STATE_OK = "ok"
STATE_PROBLEM = "problem"

# Length units
LENGTH_CENTIMETERS = "cm"  # type: str
LENGTH_METERS = "m"  # type: str
LENGTH_KILOMETERS = "km"  # type: str

LENGTH_INCHES = "in"  # type: str
LENGTH_FEET = "ft"  # type: str
LENGTH_YARD = "yd"  # type: str
LENGTH_MILES = "mi"  # type: str

# Volume units
VOLUME_LITERS = "L"  # type: str
VOLUME_MILLILITERS = "mL"  # type: str

VOLUME_GALLONS = "gal"  # type: str
VOLUME_FLUID_OUNCE = "fl. oz."  # type: str

# Mass units
MASS_GRAMS = "g"  # type: str
MASS_KILOGRAMS = "kg"  # type: str

MASS_OUNCES = "oz"  # type: str
MASS_POUNDS = "lb"  # type: str

# UV Index units
UNIT_UV_INDEX = "UV index"  # type: str

URL_ROOT = "/"
URL_API = "/api/"
URL_API_STREAM = "/api/stream"
URL_API_CONFIG = "/api/config"
URL_API_DISCOVERY_INFO = "/api/discovery_info"
URL_API_STATES = "/api/states"
URL_API_STATES_ENTITY = "/api/states/{}"
URL_API_EVENTS = "/api/events"
URL_API_EVENTS_EVENT = "/api/events/{}"
URL_API_SERVICES = "/api/services"
URL_API_SERVICES_SERVICE = "/api/services/{}/{}"
URL_API_COMPONENTS = "/api/components"
URL_API_ERROR_LOG = "/api/error_log"
URL_API_LOG_OUT = "/api/log_out"
URL_API_TEMPLATE = "/api/template"

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_MOVED_PERMANENTLY = 301
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_METHOD_NOT_ALLOWED = 405
HTTP_UNPROCESSABLE_ENTITY = 422
HTTP_INTERNAL_SERVER_ERROR = 500

CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_MSGPACK = "application/msgpack"
CONTENT_TYPE_MULTIPART = "multipart/x-mixed-replace; boundary={}"
CONTENT_TYPE_TEXT_PLAIN = "text/plain"
CONTENT_TYPE_TEXT_HTML = "text/html"

RESTART_EXIT_CODE = 4  # This code is monitored by yombo_tac.sh to restart. Only this will number will restart it.
QUIT_ERROR_EXIT_CODE = 1
QUIT_EXIT_CODE = 0

# Auth types
AUTH_TYPE_AUTHKEY = "authkey"
AUTH_TYPE_USER = "user"  # an actual user object
AUTH_TYPE_WEBSESSION = "websession"

ENERGY_NONE = "none"
ENERGY_ELECTRIC = "electric"
ENERGY_GAS = "gas"
ENERGY_WATER = "water"
ENERGY_NOISE = "noise"

ENERGY_TYPES = (ENERGY_NONE, ENERGY_ELECTRIC, ENERGY_GAS, ENERGY_WATER, ENERGY_NOISE)
