"""
Covnerts various things to other things.  Helpful huh?
"""
from time import strftime, localtime

from yombo.core.exceptions import YomboWarning


def convert_temp(i_temp):
    """
    Convert a temperature from celsius to fahrenheit and back. Just input a number followed by C or F.

    Example: 32F  returns a tuple of (0,C)

    Useful when you're too lazy to to use unit_convert below.

    :param i_temp: A temperature to convert
    :type i_temp: str
    :return: A tuple containing the value and new unit type
    :rtype: tuple
    """
    degree = float(i_temp[:-1])
    i_convention = i_temp[-1]

    if i_convention.upper() == "C":
        return unit_convert("c_f", degree)
    elif i_convention.upper() == "F":
        return unit_convert("f_c", degree)
    else:
        raise YomboWarning("Invalid temperature requested.")

# This dict of lambda converts allows for quick conversions:
# unit_converters["c_f"](33)  # Convert celsius to fahrenheit
# The format of the unit types is: (from)_(to)
# For example, "g_oz" converts from grams to ounces.
unit_converters = {
    "km_mi": lambda x: x*0.62137119,  # miles
    "mi_km": lambda x: x*1.6093,  # kilometers
    "m_ft": lambda x: x*3.28084,  # feet
    "ft_m": lambda x: x*0.3048,  # meters
    "cm_in": lambda x: x*0.39370079,  # inches
    "in_cm": lambda x: x*2.54,  # inches
    "oz_g": lambda x: x*28.34952,  # grams
    "g_oz": lambda x: x*0.03527396195,  # ounces
    "kg_lb": lambda x: x*2.20462262185,  # pounds
    "lb_kg": lambda x: x*0.45359237,  # pounds
    "f_c": lambda x: float((x - 32) * (5.0/9.0)),  # celsius
    "f_f": lambda x: x,
    "c_f": lambda x: float((x * (9.0/5.0)) + 32),  # fahrenheit
    "c_c": lambda x: x,
    "btu_kwh": lambda x: x*0.00029307107017,  # kilowatt-hour
    "btu_btu": lambda x: x,
    "kwh_btu": lambda x: x*3412.14163312794,  # btu
    "kwh_kwg": lambda x: x,
}


def unit_convert(unit_type, unit_size):
    """
    Helper function to use unit_converters dictionary. Just pass the type of converter to use
    such as "c_f" for celsius to fahrenheit.

    The format of the unit types is: (from)_(to)
    For example, "g_oz" converts from grams to ounces.

    Usage: yombo.utils.unit_convert("km_mi", 10)  # returns 10 km in miles.

    Valid unit_types:
    "km_mi" - kilometers to miles
    "mi_km" - miles to kilometers
    "m_ft" - meters to feet
    "ft_m" - feet to meters
    "cm_in" - centimeter to inches
    "in_cm" - inches to centimeters
    "oz_g" - ounces to grames
    "g_oz" - grames to ounces
    "kg_lb" - kilograms to pounds
    "lb_kg" - pounts to kilograms
    "f_c" - fahrenheit to celsius
    "c_f" - celsius to fahrenheit
    "btu_kwh" - btu"s to kilowatt-hours
    "kwh_btu" - kilowatt-hours to btu's

    :param unit_type: string - unit types to convert from_to
    :param unit_size: int or float - value to convert
    :return: float - converted unit
    """
    return unit_converters[unit_type](unit_size)


def status_to_string(status):
    if status == 0:
        return "ui::common::disabled"
    elif status == 1:
        return "ui::common::enabled"
    elif status == 2:
        return "ui::common::deleted"
    else:
        return "state::default::unknown"


def public_to_string(pubic_value):
    pubic_value = int(pubic_value)
    if pubic_value == 0:
        return "ui::common::private"
    elif pubic_value == 1:
        return "ui::common::public_pending"
    elif pubic_value == 2:
        return "ui::common::public"
    else:
        return "state::default::unknown"


def epoch_to_string(the_time, format_string=None, milliseconds=None):
    if the_time is None:
        return "None"
    if isinstance(the_time, str):
        try:
            the_time = int(the_time)
        except:
            try:
                the_time = float(the_time)
            except:
                return the_time

    if format_string is None:
        if milliseconds is True:
            format_string = "%b %d %Y %H:%M:%S.%%s %Z"
        else:
            format_string = "%b %d %Y %H:%M:%S %Z"

    if milliseconds is True:
        return strftime(format_string, localtime(the_time)) % str(the_time-int(the_time))[2:5]
    else:
        return strftime(format_string, localtime(the_time))


def convert_to_seconds(s):
    seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    return int(s[:-1]) * seconds_per_unit[s[-1]]


def translate_int_value(value, fromMin, fromMax, toMin, toMax):
    """
    Used to translate one scale to another. For example, a light can have 255 steps, but
    we want to display this in percent to a human. This function would return 50:
    .. code-block:: python

       human_status = translate_int_value(127.5, 0, 255, 0, 100)

    From: https://stackoverflow.com/questions/1969240/mapping-a-range-of-values-to-another
    :param value: The value to translate
    :param fromMin: The "from" range, starting position.
    :param fromMax: The "from" range, ending position.
    :param toMin: The "to" range, starting position.
    :param toMax: The "to" range, ending position.
    :return:
    """
    # Figure out how "wide" each range is
    leftSpan = fromMax - fromMin
    rightSpan = toMax - toMin

    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - fromMin) / float(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return int(round(toMin + (valueScaled * rightSpan)))
