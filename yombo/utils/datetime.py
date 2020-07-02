"""
Various datetime / date /time utilities.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018-2020 by Yombo.
:license: See LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/datetime.html>`_
"""

import datetime as dt
import parsedatetime as pdt
import pytz
import re
from time import time
from typing import Any, Dict, Union, Optional, Tuple

from yombo.utils.decorators import static_var

DATE_STR_FORMAT = "%Y-%m-%d"
UTC = DEFAULT_TIME_ZONE = pytz.utc  # type: dt.tzinfo


# This re.compile string is copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
# https://github.com/django/django/blob/master/LICENSE
DATETIME_RE = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"
    r"[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})"
    r"(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?"
    r"(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?$"
)


def get_age(time: Any) -> str:
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like "an hour ago", "Yesterday", "3 months ago",
    "just now", etc

    Make sure date is not in the past, or else it won't work.

    Modified from: http://stackoverflow.com/questions/1551382/user-friendly-time-format-in-python
    """

    now = dt.datetime.now()
    if type(time) is float:
        time = int(round(time))
    if type(time) is int:
        diff = now - dt.datetime.fromtimestamp(time)
    elif isinstance(time, dt.datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ""

    if day_diff == 0:
        if second_diff < 5:
            return "just now"
        if second_diff < 60:
            time_count = second_diff
            time_ago = "seconds ago"
            return "%s %s" % (time_count, time_ago)
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            time_count = second_diff // 60
            time_ago = "minutes ago"
            if time_count == 1:
                time_ago = "minute ago"
            return "%s %s" % (time_count, time_ago)
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff // 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        time_count = day_diff
        time_ago = "days ago"
        if time_count == 1:
            time_ago = "day ago"
        return "%s %s" % (time_count, time_ago)
    if day_diff < 60:
        time_count = day_diff // 7
        time_ago = "weeks ago"
        if time_count == 1:
            time_ago = "week ago"
        return "%s %s" % (time_count, time_ago)
    if day_diff < 365:
        time_count = day_diff // 30
        time_ago = "months ago"
        if time_count == 1:
            time_ago = "month ago"
        return "%s %s" % (time_count, time_ago)
    return str(day_diff // 365) + " years ago"


# Found in this gist: https://gist.github.com/zhangsen/1199964
def get_age_exact(time: Any) -> str:
    """
    Take a datetime and return its "age" as a string.

    The age can be in second, minute, hour, day, month or year. Only the
    biggest unit is considered, e.g. if it's 2 days and 3 hours, "2 days" will
    be returned.
    Make sure date is not in the future, or else it won't work.
    """

    def formatn(number: int, unit: str) -> str:
        """Add "unit" if it's plural."""
        if number == 1:
            return f"1 {unit}"
        elif number > 1:
            return f"{number:d} {unit}s"

    # pylint: disable=invalid-sequence-index
    def q_n_r(first: int, second: int) -> Tuple[int, int]:
        """Return quotient and remaining."""
        return first // second, first % second

    now = dt.datetime.now()
    if type(time) is float:
        time = int(round(time))
    if type(time) is int:
        diff = now - dt.datetime.fromtimestamp(time)
    elif isinstance(time, dt.datetime):
        diff = now - time
    elif not time:
        diff = now - now

    second_diff = diff.seconds
    day_diff = diff.days

    year, day = q_n_r(day_diff, 365)
    if year > 0:
        return formatn(year, "year")

    month, day = q_n_r(day, 30)
    if month > 0:
        return formatn(month, "month")
    if day > 0:
        return formatn(day, "day")

    hour, second = q_n_r(second_diff, 3600)
    if hour > 0:
        return formatn(hour, "hour")

    minute, second = q_n_r(second, 60)
    if minute > 0:
        return formatn(minute, "minute")

    return formatn(second, "second") if second > 0 else "0 seconds"


def utc_from_timestamp(timestamp: float) -> dt.datetime:
    """
    Gets UTC from a provided timestamp.
    """
    return dt.datetime.utcfromtimestamp(timestamp).replace(tzinfo=UTC)


def as_local(value: dt.datetime) -> dt.datetime:
    """
    Convert a UTC datetime object to local time zone.
    """
    if value.tzinfo == DEFAULT_TIME_ZONE:
        return value
    elif value.tzinfo is None:
        value = UTC.localize(value)

    return value.astimezone(DEFAULT_TIME_ZONE)


def timestamp_custom(value, date_format="%Y-%m-%d", local=True):
    """
    Create a timestamp from a value. First, attempts to convert input to a datetime
    and then applies date_format to it.
    """
    try:
        date = utc_from_timestamp(value)

        if local:
            date = as_local(date)

        return date.strftime(date_format)
    except (ValueError, TypeError):
        # If timestamp can't be converted
        return value


def timestamp_local(value):
    """
    Filter to convert given timestamp to local date/time.
    """
    try:
        return as_local(
            utc_from_timestamp(value)).strftime(DATE_STR_FORMAT)
    except (ValueError, TypeError):
        # If timestamp can't be converted
        return value


def timestamp_utc(value):
    """
    Filter to convert given timestamp to UTC date/time.
    """
    try:
        return utc_from_timestamp(value).strftime(DATE_STR_FORMAT)
    except (ValueError, TypeError):
        # If timestamp can't be converted
        return value


def forgiving_as_timestamp(value):
    """
    Try to convert value to timestamp.
    """
    try:
        return as_timestamp(value)
    except (ValueError, TypeError):
        return None


def now(time_zone: dt.tzinfo = None) -> dt.datetime:
    """
    Get time now in in the specified time zone.
    """
    return dt.datetime.now(time_zone or DEFAULT_TIME_ZONE)


def utcnow() -> dt.datetime:
    """
    Get time now in UTC time.

    :return:
    """
    return dt.datetime.now(UTC)


def as_utc(value: dt.datetime) -> dt.datetime:
    """Return a datetime as UTC time.

    Assumes datetime without tzinfo to be in the DEFAULT_TIME_ZONE.
    """
    if value.tzinfo == UTC:
        return value
    elif value.tzinfo is None:
        value = DEFAULT_TIME_ZONE.localize(value)

    return value.astimezone(UTC)


def as_timestamp(dt_value):
    """Convert a date/time into a unix time (seconds since 1970)."""
    if hasattr(dt_value, "timestamp"):
        parsed_dt = dt_value
    else:
        parsed_dt = parse_datetime(str(dt_value))
        if not parsed_dt:
            raise ValueError("not a valid date/time.")
    return parsed_dt.timestamp()


@static_var("calendar", pdt.Calendar())
def time_from_string(time_string: str, source_time=None) -> tuple:
    """
    Using the parsedatetime library, use human terms to get various dates and times. This method
    returns epoch times UTC, but does consider the system local time zone and daylight savings times.

    Also, check out :py:meth:`get_next_time() <get_next_time>` if you want the next a specific time of
    day occurs.

    .. code-block:: python

        a_time = self._Times.time_from_string("tomorrow 10pm")
        a_time = self._Times.time_from_string("1 hour ago")

    :param time_string: A human time to convert to epoch, considering local timezone.
    :type time_string: str
    :return: A tuple. First item is EPOCH in seconds, second a datetime instance.
    :rtype: tuple
    """
    if source_time is None:
        source_time = dt.datetime.fromtimestamp(time())
    if isinstance(time_string, str) is False:
        time_string = str(time_string) + "s"
    # print("aaaa 111: %s (%s)", (time_string, type(time_string)))
    time_struct, what = time_from_string.calendar.parse(time_string, source_time)
    # print("aaaa 112: %s (%s)" % (time_struct, type(time_struct)))

    output = None

    # what was returned (see http://code-bear.com/code/parsedatetime/docs/)
    # 0 = failed to parse
    # 1 = date (with current time, as a struct_time)
    # 2 = time (with current date, as a struct_time)
    # 3 = datetime
    if what in (1, 2, 3):
        # result is struct_time
        output = dt.datetime(*time_struct[:6])
    elif what == 3:
        # result is a datetime
        output = time_struct
    return int(output.strftime("%s")), output


@static_var("calendar", pdt.Calendar())
def get_next_time(some_time, max=None):
    """
    This is used when trying to get the next time it's a specific time. If it's passed for today, it
    prepends "tomorrow" to the request to get tomorrow's specific time.

    .. code-block:: python

        a_time = self._Times.get_next_time("1:15pm")

    :param some_time: A human time to convert to epoch, considering local timezone.
    :type some_time: str
    :return: A tuple. First item is EPOCH in seconds, second a datetime instance.
    :rtype: tuple
    """
    a_time = time_from_string(some_time)
    cur_time = time()
    if a_time[0] < cur_time:
        a_time = time_from_string("tomorrow " + some_time)

    if isinstance(max, int) and max > 0:
        max_time = cur_time + max
        if a_time > max_time:
            return a_time
        else:
            return max_time
    return a_time


def get_time_zone(time_zone_str: str) -> Optional[dt.tzinfo]:
    """
    Get time zone from string. Return None if unable to determine.

    Async friendly.
    :param time_zone_str: String to get timezone from.
    :return: pytz timezone.
    :rtype: timezone
    """
    try:
        return pytz.timezone(time_zone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        return None


def day_of_week(year, month, day):
    """
    Get the day of the week.
    From: http://stackoverflow.com/questions/9847213/which-day-of-week-given-a-date-python

    :param year: Any year after 1700
    :type year: int
    :param month: The month
    :type month: int
    :param day: The day
    :type day: int
    :return: Day of the week in english.
    :rtype: str
    """
    offset = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    week = ["Sunday",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday"]
    afterFeb = 1
    if month > 2: afterFeb = 0
    aux = year - 1700 - afterFeb
    # dayOfWeek for 1700/1/1 = 5, Friday
    dayOfWeek = 5
    # partial sum of days betweem current date and 1700/1/1
    dayOfWeek += (aux + afterFeb) * 365
    # leap year correction
    dayOfWeek += aux / 4 - aux / 100 + (aux + 100) / 400
    # sum monthly and day offsets
    dayOfWeek += offset[month - 1] + (day - 1)
    dayOfWeek %= 7
    return dayOfWeek, week[dayOfWeek]


def start_of_local_day(dt_or_d:
                       Union[dt.date, dt.datetime]=None) -> dt.datetime:
    """Return local datetime object of start of day from date or datetime."""
    if dt_or_d is None:
        date = now().date()  # type: dt.date
    elif isinstance(dt_or_d, dt.datetime):
        date = dt_or_d.date()
    return DEFAULT_TIME_ZONE.localize(dt.datetime.combine(date, dt.time()))


# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
# https://github.com/django/django/blob/master/LICENSE
def parse_datetime(dt_str: str) -> dt.datetime:
    """Parse a string and return a datetime.datetime.

    This function supports time zone offsets. When the input contains one,
    the output uses a timezone with a fixed offset from UTC.
    Raises ValueError if the input is well formatted but not a valid datetime.
    Returns None if the input isn"t well formatted.
    """
    match = DATETIME_RE.match(dt_str)
    if not match:
        return None
    kws = match.groupdict()  # type: Dict[str, Any]
    if kws["microsecond"]:
        kws["microsecond"] = kws["microsecond"].ljust(6, "0")
    tzinfo_str = kws.pop("tzinfo")

    tzinfo = None  # type: Optional[dt.tzinfo]
    if tzinfo_str == "Z":
        tzinfo = UTC
    elif tzinfo_str is not None:
        offset_mins = int(tzinfo_str[-2:]) if len(tzinfo_str) > 3 else 0
        offset_hours = int(tzinfo_str[1:3])
        offset = dt.timedelta(hours=offset_hours, minutes=offset_mins)
        if tzinfo_str[0] == "-":
            offset = -offset
        tzinfo = dt.timezone(offset)
    else:
        tzinfo = None
    kws = {k: int(v) for k, v in kws.items() if v is not None}
    kws["tzinfo"] = tzinfo
    return dt.datetime(**kws)


def parse_date(dt_str: str) -> dt.date:
    """Convert a date string to a date object."""
    try:
        return dt.datetime.strptime(dt_str, DATE_STR_FORMAT).date()
    except ValueError:  # If dt_str did not match our format
        return None


def parse_time(time_str):
    """Parse a time string (00:20:00) into Time object.

    Return None if invalid.
    """
    parts = str(time_str).split(":")
    if len(parts) < 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) > 2 else 0
        return dt.time(hour, minute, second)
    except ValueError:
        # ValueError if value cannot be converted to an int or not in range
        return None


def strptime(string, fmt):
    """
    Primarily used for templates as a filter. Parse a time string to datetime.

    :param string:
    :param fmt:
    :return:
    """
    try:
        return dt.strptime(string, fmt)
    except (ValueError, AttributeError):
        return string  # return input if value cannot be processed.