"""
Various helpers dealing with locations.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018 by Yombo.
:license: See LICENSE for details.
"""
import math
import treq
from typing import Any, Optional, Tuple, Dict

from twisted.internet.defer import inlineCallbacks

from yombo.utils import data_unpickle

# These URLS are used to fetch IP Address information. There is a primary and 2 backup methods to get what we need.

# Max mind provides the most information and is easiest to consume.
MAXMIND_API = 'https://www.maxmind.com/geoip/v2.0/city_isp_org/{0}'

# Provides limited information, but has still has what we need.
IPAPI_API = 'http://ip-api.com/json'

# IP Stack proves what we need, however, we need an IP address.
IPIFY_API = 'https://api.ipify.org'  # get out ip address
IPSTACK_API = 'https://ipstack.com/ipstack_api.php?ip={0}'  # get more details about the IP

# Used to get out elevation. Returns 800 feet if none is found.
ELEVATION_URL = 'http://maps.googleapis.com/maps/api/elevation/json'

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


@inlineCallbacks
def detect_location_info():
    """Detect location information."""
    data = yield _get_maxmind()
    if data is None:
        data = yield _get_ip_api()
    if data is None:
        data = yield _get_using_ipify_ipstack()

    if data is None:
        data = {
            'ip': None,
            'country_code': None,
            'country_name': None,
            'region_code': None,
            'region_name': None,
            'city': None,
            'zip_code': None,
            'time_zone': None,
            'latitude': None,
            'longitude': None,
            'isp': None,
            'elevation': None,
            'use_metric': True,
        }
    else:
        data['use_metric'] = data['country_code'] not in ('US', 'MM', 'LR')

    data['elevation'] = yield elevation(data['latitude'], data['longitude'])

    return data


def distance(lat1, lon1, lat2, lon2):
    """Calculate the distance in meters between two points.

    Async friendly.
    """
    return vincenty((lat1, lon1), (lat2, lon2)) * 1000

# Author: https://github.com/maurycyp
# Source: https://github.com/maurycyp/vincenty
# License: https://github.com/maurycyp/vincenty/blob/master/LICENSE
# pylint: disable=invalid-name, unused-variable, invalid-sequence-index
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


@inlineCallbacks
def _get_maxmind(location: str = None) -> Optional[Dict[str, Any]]:
    """Query maxmind for location data."""
    if location is None:
        location = 'me'

    url = MAXMIND_API.format(location)
    try:
        response = yield treq.get(url, timeout=5, params={'demo': 1})
    except Exception as e:
        return None
    content = yield treq.content(response)
    raw_info = data_unpickle(content, 'json')

    return {
        'source': 'maxmind',
        'ip': raw_info.get('traits').get('ip_address'),
        'country_code': raw_info.get('country', {}).get('iso_code'),
        'country_name': raw_info.get('country', {}).get('names', {}).get('en'),
        'region_code': raw_info.get('subdivisions', [{}])[0].get('iso_code'),
        'region_name': raw_info.get('subdivisions', [{}])[0].get('names', {}).get('en'),
        'city': raw_info.get('city', {}).get('names', {}).get('en'),
        'zip_code': raw_info.get('postal', {}).get('code'),
        'time_zone': raw_info.get('location').get('time_zone'),
        'latitude': float(raw_info.get('location').get('latitude')),
        'longitude': float(raw_info.get('location').get('longitude')),
        'isp': raw_info.get('traits').get('isp'),
    }


@inlineCallbacks
def _get_ip_api() -> Optional[Dict[str, Any]]:
    """Query ip-api.com for location data."""
    try:
        response = yield treq.get(IPAPI_API, timeout=5)
    except Exception:
        return None
    content = yield treq.content(response)
    raw_info = data_unpickle(content, 'json')

    return {
        'source': 'ip_api',
        'ip': raw_info.get('query'),
        'country_code': raw_info.get('countryCode'),
        'country_name': raw_info.get('country'),
        'region_code': raw_info.get('region'),
        'region_name': raw_info.get('regionName'),
        'city': raw_info.get('city'),
        'zip_code': raw_info.get('zip'),
        'time_zone': raw_info.get('timezone'),
        'latitude': float(raw_info.get('lat')),
        'longitude': float(raw_info.get('lon')),
        'isp': raw_info.get('isp'),
    }


@inlineCallbacks
def _get_using_ipify_ipstack():
    """
    The last resort is to ask someone for out external IP address, and then feed this to IPStack
    to get more details.
    """
    response = yield treq.get(IPIFY_API)
    content = yield treq.content(response)
    ip = content.decode().strip()
    url = MAXMIND_API.format(ip)
    try:
        response = yield treq.get(url, timeout=5)
    except Exception:
        return None
    content = yield treq.content(response)
    raw_info = data_unpickle(content, 'json')

    return {
        'source': 'ipify_ipstack',
        'ip': raw_info.get('query'),
        'country_code': raw_info.get('country_code'),
        'country_name': raw_info.get('country_name'),
        'region_code': raw_info.get('region_code'),
        'region_name': raw_info.get('region_name'),
        'city': raw_info.get('city'),
        'zip_code': raw_info.get('zip'),
        'time_zone': raw_info.get('time_zone', {}).get('id'),
        'latitude': float(raw_info.get('latitude')),
        'longitude': float(raw_info.get('longitude')),
        'isp': raw_info.get('connection', {}).get('isp'),
    }


@inlineCallbacks
def elevation(latitude, longitude):
    """Return elevation for given latitude and longitude."""
    try:
        response = yield treq.get(
            ELEVATION_URL,
            params={
                'locations': '{},{}'.format(latitude, longitude),
                'sensor': 'false',
            },
            timeout=10)
    except Exception:
        return 800

    if response.code != 200:
        return 800

    content = yield treq.content(response)
    raw_info = data_unpickle(content, 'json')

    try:
        return int(float(raw_info['results'][0]['elevation']))
    except (ValueError, KeyError, IndexError):
        return 800

# Google elevation results
# {
#   "results": [
#     {
#       "elevation": 602.7864379882812,
#       "location": {
#         "lat": 21.667639,
#         "lng": 13.304194
#       },
#       "resolution": 152.7032318115234
#     }
#   ],
#   "status": "OK"
# }

# Maxmind output:
# {
#   "location": {
#     "accuracy_radius": "10",
#     "latitude": 42.6833,
#     "longitude": 23.3167,
#     "time_zone": "Europe/Sofia"
#   },
#   "traits": {
#     "autonomous_system_number": "8866",
#     "autonomous_system_organization": "Vivacom",
#     "domain": "btc-net.bg",
#     "isp": "Next Generation Services Ltd.",
#     "organization": "Next Generation Services Ltd.",
#     "ip_address": "10.10.10.10"
#   },
#   "city": {
#     "geoname_id": 727011,
#     "names": {
#       "en": "Sofia",
#       "es": "Sofía",
#       "fr": "Sofia",
#       "ja": "ソフィア",
#       "pt-BR": "Sófia",
#       "ru": "София",
#       "de": "Sofia"
#     }
#   },
#   "continent": {
#     "code": "EU",
#     "geoname_id": 6255148,
#     "names": {
#       "pt-BR": "Europa",
#       "ru": "Европа",
#       "zh-CN": "欧洲",
#       "de": "Europa",
#       "en": "Europe",
#       "es": "Europa",
#       "fr": "Europe",
#       "ja": "ヨーロッパ"
#     }
#   },
#   "country": {
#     "is_in_european_union": true,
#     "iso_code": "BG",
#     "geoname_id": 732800,
#     "names": {
#       "pt-BR": "Bulgária",
#       "ru": "Болгария",
#       "zh-CN": "保加利亚",
#       "de": "Bulgarien",
#       "en": "Bulgaria",
#       "es": "Bulgaria",
#       "fr": "Bulgarie",
#       "ja": "ブルガリア共和国"
#     }
#   },
#   "postal": {
#     "code": "1000"
#   },
#   "registered_country": {
#     "is_in_european_union": true,
#     "iso_code": "BG",
#     "geoname_id": 732800,
#     "names": {
#       "pt-BR": "Bulgária",
#       "ru": "Болгария",
#       "zh-CN": "保加利亚",
#       "de": "Bulgarien",
#       "en": "Bulgaria",
#       "es": "Bulgaria",
#       "fr": "Bulgarie",
#       "ja": "ブルガリア共和国"
#     }
#   },
#   "subdivisions": [
#     {
#       "iso_code": "22",
#       "geoname_id": 731061,
#       "names": {
#         "en": "Sofia-Capital"
#       }
#     }
#   ]
# }

# ip-api results (some details changed to protect privacy)
# {
#   "as": "AS7922 Comcast Cable Communications, LLC",
#   "city": "Folsom",
#   "country": "United States",
#   "countryCode": "US",
#   "isp": "Comcast Cable",
#   "lat": 42.6833,
#   "lon": 23.3167,
#   "org": "Comcast Cable",
#   "query": "10.10.10.10",
#   "region": "CA",
#   "regionName": "California",
#   "status": "success",
#   "timezone": "America/Los_Angeles",
#   "zip": "95670"
# }

# IP Stack:
# {
#   "ip": "10.10.10.10",
#   "hostname": "c-10.10.10.10.hsd1.ca.comcast.net",
#   "type": "ipv4",
#   "continent_code": "NA",
#   "continent_name": "North America",
#   "country_code": "US",
#   "country_name": "United States",
#   "region_code": "CA",
#   "region_name": "California",
#   "city": "Yuba City",
#   "zip": "95991",
#   "latitude": 40.6000,
#   "longitude": -120.6000,
#   "location": {
#     "geoname_id": 5411015,
#     "capital": "Washington D.C.",
#     "languages": [
#       {
#         "code": "en",
#         "name": "English",
#         "native": "English"
#       }
#     ],
#     "country_flag": "http://assets.ipstack.com/flags/us.svg",
#     "country_flag_emoji": "🇺🇸",
#     "country_flag_emoji_unicode": "U+1F1FA U+1F1F8",
#     "calling_code": "1",
#     "is_eu": false
#   },
#   "time_zone": {
#     "id": "America/Los_Angeles",
#     "current_time": "2018-08-07T12:56:01-07:00",
#     "gmt_offset": -25200,
#     "code": "PDT",
#     "is_daylight_saving": true
#   },
#   "currency": {
#     "code": "USD",
#     "name": "US Dollar",
#     "plural": "US dollars",
#     "symbol": "$",
#     "symbol_native": "$"
#   },
#   "connection": {
#     "asn": 7922,
#     "isp": "Comcast Cable Communications, LLC"
#   },
#   "security": {
#     "is_proxy": false,
#     "proxy_type": null,
#     "is_crawler": false,
#     "crawler_name": null,
#     "crawler_type": null,
#     "is_tor": false,
#     "threat_level": "low",
#     "threat_types": null
#   }
# }
