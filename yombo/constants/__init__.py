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
MINOR_VERSION = 19
PATCH_VERSION = '1.dev0'
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
