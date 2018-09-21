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


:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/tree/master/yombo/constants>`_
"""
MAJOR_VERSION = 0
MINOR_VERSION = 22
PATCH_VERSION = 0
__short_version__ = '{}.{}'.format(MAJOR_VERSION, MINOR_VERSION)
__version__ = '{}.{}'.format(__short_version__, PATCH_VERSION)

REQUIRED_PYTHON_VER = (3, 5, 3)

# Yombo gateway version number
VERSION = __version__

# Days of the week
WEEKDAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

# Measurement systems
MISC_UNIT_SYSTEM_METRIC = 'metric'  # type: str
MISC_UNIT_SYSTEM_IMPERIAL = 'imperial'  # type: str

# Temperature systems
TEMP_CELSIUS = '°C'
TEMP_FAHRENHEIT = '°F'

# Misc Attributes

ATR_ICON = 'icon'
ATR_CODE = 'code'

# #### STATUS ####
STATUS_ON = 'on'
STATUS_OFF = 'off'
STATUS_HOME = 'home'
STATUS_NOT_HOME = 'not_home'
STATUS_UNKNOWN = 'unknown'
STATUS_OPEN = 'open'
STATUS_OPENING = 'opening'
STATUS_CLOSED = 'closed'
STATUS_CLOSING = 'closing'
STATUS_PLAYING = 'playing'
STATUS_PAUSED = 'paused'
STATUS_IDLE = 'idle'
STATUS_STANDBY = 'standby'
STATUS_ALARM_DISARMED = 'disarmed'
STATUS_ALARM_ARMED_HOME = 'armed_home'
STATUS_ALARM_ARMED_AWAY = 'armed_away'
STATUS_ALARM_ARMED_NIGHT = 'armed_night'
STATUS_ALARM_ARMED_CUSTOM_BYPASS = 'armed_custom_bypass'
STATUS_ALARM_PENDING = 'pending'
STATUS_ALARM_ARMING = 'arming'
STATUS_ALARM_DISARMING = 'disarming'
STATUS_ALARM_TRIGGERED = 'triggered'
STATUS_LOCKED = 'locked'
STATUS_UNLOCKED = 'unlocked'
STATUS_UNAVAILABLE = 'unavailable'
STATUS_OK = 'ok'
STATUS_PROBLEM = 'problem'

# Length units
LENGTH_CENTIMETERS = 'cm'  # type: str
LENGTH_METERS = 'm'  # type: str
LENGTH_KILOMETERS = 'km'  # type: str

LENGTH_INCHES = 'in'  # type: str
LENGTH_FEET = 'ft'  # type: str
LENGTH_YARD = 'yd'  # type: str
LENGTH_MILES = 'mi'  # type: str

# Volume units
VOLUME_LITERS = 'L'  # type: str
VOLUME_MILLILITERS = 'mL'  # type: str

VOLUME_GALLONS = 'gal'  # type: str
VOLUME_FLUID_OUNCE = 'fl. oz.'  # type: str

# Mass units
MASS_GRAMS = 'g'  # type: str
MASS_KILOGRAMS = 'kg'  # type: str

MASS_OUNCES = 'oz'  # type: str
MASS_POUNDS = 'lb'  # type: str

# UV Index units
UNIT_UV_INDEX = 'UV index'  # type: str

URL_ROOT = '/'
URL_API = '/api/'
URL_API_STREAM = '/api/stream'
URL_API_CONFIG = '/api/config'
URL_API_DISCOVERY_INFO = '/api/discovery_info'
URL_API_STATES = '/api/states'
URL_API_STATES_ENTITY = '/api/states/{}'
URL_API_EVENTS = '/api/events'
URL_API_EVENTS_EVENT = '/api/events/{}'
URL_API_SERVICES = '/api/services'
URL_API_SERVICES_SERVICE = '/api/services/{}/{}'
URL_API_COMPONENTS = '/api/components'
URL_API_ERROR_LOG = '/api/error_log'
URL_API_LOG_OUT = '/api/log_out'
URL_API_TEMPLATE = '/api/template'

PERMISSION_PLATFORMS = ('atom', 'automation', 'device', 'gateway', 'location', 'location', 'module',
                        'notification', 'panel', 'scene', 'state', 'statistic', 'location', 'user', 'authkey',
                        'gateway', 'system_options', 'user')
ITEMIZED_PERMISSION_PLATFORMS = ('device', 'automation', 'scene')
AUTOMATION_ACTIONS = ('allow_view', 'allow_edit', 'allow_enable', 'allow_disable',
                  'deny_view', 'deny_edit', 'deny_enable', 'deny_disable')

DEVICE_ACTIONS = ('allow_view', 'allow_control', 'allow_edit', 'allow_enable', 'allow_disable',
                  'deny_view', 'deny_control', 'deny_edit', 'deny_enable', 'deny_disable')

SCENE_ACTIONS = ('allow_view', 'allow_start', 'allow_stop', 'allow_edit', 'allow_enable', 'allow_disable',
                  'deny_view', 'deny_start', 'deny_stop', 'deny_edit', 'deny_enable', 'deny_disable')

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_MOVED_PERMANENTLY = 301
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_METHOD_NOT_ALLOWED = 405
HTTP_UNPROCESSABLE_ENTITY = 422
HTTP_INTERNAL_SERVER_ERROR = 500

CONTENT_TYPE_JSON = 'application/json'
CONTENT_TYPE_MSGPACK = 'application/msgpack'
CONTENT_TYPE_MULTIPART = 'multipart/x-mixed-replace; boundary={}'
CONTENT_TYPE_TEXT_PLAIN = 'text/plain'

# The exit code to send to request a restart
RESTART_EXIT_CODE = 127
QUIT_ERROR_EXIT_CODE = 1
QUIT_EXIT_CODE = 0

# Session types
AUTH_TYPE_AUTHKEY = 'authkey'
AUTH_TYPE_WEBSESSION = 'websession'
