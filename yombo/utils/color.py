"""
Color util methods.

This file comes from the home assistant and has an Apache 2.0 license. This file has been modified to work
with Yombo.
"""
import logging
import math
import colorsys
from typing import Tuple

from yombo.core.log import get_logger

logger = get_logger("utils.color")

# Official CSS3 colors from w3.org:
# https://www.w3.org/TR/2010/PR-css3-color-20101028/#html4
# names do not have spaces in them so that we can compare against
# reuqests more easily (by removing spaces from the requests as well).
# This lets "dark seagreen" and "dark sea green" both match the same
# color "darkseagreen".
COLORS = {
    'alice blue': (240, 248, 255),
    'antique white': (250, 235, 215),
    'aqua': (0, 255, 255),
    'aqua marine': (127, 255, 212),
    'azure': (240, 255, 255),
    'beige': (245, 245, 220),
    'bisque': (255, 228, 196),
    'black': (0, 0, 0),
    'blanched almond': (255, 235, 205),
    'blue': (0, 0, 255),
    'blue violet': (138, 43, 226),
    'brown': (165, 42, 42),
    'burly wood': (222, 184, 135),
    'cadet blue': (95, 158, 160),
    'chart reuse': (127, 255, 0),
    'chocolate': (210, 105, 30),
    'coral': (255, 127, 80),
    'corn flower blue': (100, 149, 237),
    'corn silk': (255, 248, 220),
    'crimson': (220, 20, 60),
    'cyan': (0, 255, 255),
    'dark blue': (0, 0, 139),
    'dark cyan': (0, 139, 139),
    'dark golden rod': (184, 134, 11),
    'dark gray': (169, 169, 169),
    'dark green': (0, 100, 0),
    'dark grey': (169, 169, 169),
    'dark khaki': (189, 183, 107),
    'dark magenta': (139, 0, 139),
    'dark olive green': (85, 107, 47),
    'dark orange': (255, 140, 0),
    'dark orchid': (153, 50, 204),
    'dark red': (139, 0, 0),
    'dark salmon': (233, 150, 122),
    'dark sea green': (143, 188, 143),
    'dark slate blue': (72, 61, 139),
    'dark slate gray': (47, 79, 79),
    'dark slate grey': (47, 79, 79),
    'dark turquoise': (0, 206, 209),
    'dark violet': (148, 0, 211),
    'deep pink': (255, 20, 147),
    'deep sky blue': (0, 191, 255),
    'dim gray': (105, 105, 105),
    'dim grey': (105, 105, 105),
    'dodger blue': (30, 144, 255),
    'fire brick': (178, 34, 34),
    'floral white': (255, 250, 240),
    'forest green': (34, 139, 34),
    'fuchsia': (255, 0, 255),
    'gainsboro': (220, 220, 220),
    'ghost white': (248, 248, 255),
    'gold': (255, 215, 0),
    'golden rod': (218, 165, 32),
    'gray': (128, 128, 128),
    'green': (0, 128, 0),
    'green yellow': (173, 255, 47),
    'grey': (128, 128, 128),
    'honey dew': (240, 255, 240),
    'hot pink': (255, 105, 180),
    'indian red': (205, 92, 92),
    'indigo': (75, 0, 130),
    'ivory': (255, 255, 240),
    'khaki': (240, 230, 140),
    'lavender': (230, 230, 250),
    'lavender blush': (255, 240, 245),
    'lawn green': (124, 252, 0),
    'lemon chiffon': (255, 250, 205),
    'light blue': (173, 216, 230),
    'light coral': (240, 128, 128),
    'light cyan': (224, 255, 255),
    'light golden rod yellow': (250, 250, 210),
    'light gray': (211, 211, 211),
    'light green': (144, 238, 144),
    'light grey': (211, 211, 211),
    'light pink': (255, 182, 193),
    'light salmon': (255, 160, 122),
    'light seagreen': (32, 178, 170),
    'light sky blue': (135, 206, 250),
    'light slate gray': (119, 136, 153),
    'light slate grey': (119, 136, 153),
    'light steel blue': (176, 196, 222),
    'light yellow': (255, 255, 224),
    'lime': (0, 255, 0),
    'lime green': (50, 205, 50),
    'linen': (250, 240, 230),
    'magenta': (255, 0, 255),
    'maroon': (128, 0, 0),
    'medium aqua marine': (102, 205, 170),
    'medium blue': (0, 0, 205),
    'medium orchid': (186, 85, 211),
    'medium purple': (147, 112, 219),
    'medium sea green': (60, 179, 113),
    'medium slate blue': (123, 104, 238),
    'medium spring green': (0, 250, 154),
    'medium turquoise': (72, 209, 204),
    'medium violet red': (199, 21, 133),
    'midnight blue': (25, 25, 112),
    'mint cream': (245, 255, 250),
    'misty rose': (255, 228, 225),
    'moccasin': (255, 228, 181),
    'navajo white': (255, 222, 173),
    'navy': (0, 0, 128),
    'navy blue': (0, 0, 128),
    'old lace': (253, 245, 230),
    'olive': (128, 128, 0),
    'olive drab': (107, 142, 35),
    'orange': (255, 165, 0),
    'orange red': (255, 69, 0),
    'orchid': (218, 112, 214),
    'pale golden rod': (238, 232, 170),
    'pale green': (152, 251, 152),
    'pale turquoise': (175, 238, 238),
    'pale violet red': (219, 112, 147),
    'papaya whip': (255, 239, 213),
    'peach puff': (255, 218, 185),
    'peru': (205, 133, 63),
    'pink': (255, 192, 203),
    'plum': (221, 160, 221),
    'powder blue': (176, 224, 230),
    'purple': (128, 0, 128),
    'red': (255, 0, 0),
    'rosy brown': (188, 143, 143),
    'royal blue': (65, 105, 225),
    'saddle brown': (139, 69, 19),
    'salmon': (250, 128, 114),
    'sandy brown': (244, 164, 96),
    'sea green': (46, 139, 87),
    'seashell': (255, 245, 238),
    'sienna': (160, 82, 45),
    'silver': (192, 192, 192),
    'sky blue': (135, 206, 235),
    'slate blue': (106, 90, 205),
    'slate gray': (112, 128, 144),
    'slate grey': (112, 128, 144),
    'snow': (255, 250, 250),
    'spring green': (0, 255, 127),
    'steel blue': (70, 130, 180),
    'tan': (210, 180, 140),
    'teal': (0, 128, 128),
    'thistle': (216, 191, 216),
    'tomato': (255, 99, 71),
    'turquoise': (64, 224, 208),
    'violet': (238, 130, 238),
    'wheat': (245, 222, 179),
    'white': (255, 255, 255),
    'white smoke': (245, 245, 245),
    'yellow': (255, 255, 0),
    'yellow green': (154, 205, 50),
}


def ct_to_hs(temp):
    """Convert color temperature (mireds) to hs."""
    colorlist = list(
        color_temperature_to_hs(
            color_temperature_mired_to_kelvin(temp)))
    return [int(val) for val in colorlist]


def ct_to_rgb(temp):
    """Convert color temperature (mireds) to RGB."""
    colorlist = list(
        color_temperature_to_rgb(color_temperature_mired_to_kelvin(temp)))
    return [int(val) for val in colorlist]


def color_name_to_rgb(color_name):
    """Convert color name to RGB hex value."""
    # COLORS map has no spaces in it, so make the color_name have no
    # spaces in it as well for matching purposes
    hex_value = COLORS.get(color_name.replace(' ', '').lower())
    if not hex_value:
        raise ValueError('Unknown color')

    return hex_value


def rgb_to_brighess(iR: int, iG: int, iB: int) -> int:
    """
    Converts RGB input to a range of 0 to 255 as a level of brightness.

    :param iR:
    :param iG:
    :param iB:
    :return:
    """
    return round(0.299*iR + 0.587*iG + 0.114*iB)


def color_RGB_to_xy(iR: int, iG: int, iB: int) -> Tuple[float, float]:
    """Convert from RGB color to XY color."""
    return color_RGB_to_xy_brightness(iR, iG, iB)[:2]


# Taken from:
# http://www.developers.meethue.com/documentation/color-conversions-rgb-xy
# License: Code is given as is. Use at your own risk and discretion.
# pylint: disable=invalid-name
def color_RGB_to_xy_brightness(
        iR: int, iG: int, iB: int) -> Tuple[float, float, int]:
    """Convert from RGB color to XY color."""
    if iR + iG + iB == 0:
        return 0.0, 0.0, 0

    R = iR / 255
    B = iB / 255
    G = iG / 255

    # Gamma correction
    R = pow((R + 0.055) / (1.0 + 0.055),
            2.4) if (R > 0.04045) else (R / 12.92)
    G = pow((G + 0.055) / (1.0 + 0.055),
            2.4) if (G > 0.04045) else (G / 12.92)
    B = pow((B + 0.055) / (1.0 + 0.055),
            2.4) if (B > 0.04045) else (B / 12.92)

    # Wide RGB D65 conversion formula
    X = R * 0.664511 + G * 0.154324 + B * 0.162028
    Y = R * 0.283881 + G * 0.668433 + B * 0.047685
    Z = R * 0.000088 + G * 0.072310 + B * 0.986039

    # Convert XYZ to xy
    x = X / (X + Y + Z)
    y = Y / (X + Y + Z)

    # Brightness
    Y = 1 if Y > 1 else Y
    brightness = round(Y * 255)

    return round(x, 3), round(y, 3), brightness


def color_xy_to_RGB(vX: float, vY: float) -> Tuple[int, int, int]:
    """Convert from XY to a normalized RGB."""
    return color_xy_brightness_to_RGB(vX, vY, 255)


# Converted to Python from Obj-C, original source from:
# http://www.developers.meethue.com/documentation/color-conversions-rgb-xy
def color_xy_brightness_to_RGB(vX: float, vY: float,
                               ibrightness: int) -> Tuple[int, int, int]:
    """Convert from XYZ to RGB."""
    brightness = ibrightness / 255.
    if brightness == 0:
        return (0, 0, 0)

    Y = brightness

    if vY == 0:
        vY += 0.00000000001

    X = (Y / vY) * vX
    Z = (Y / vY) * (1 - vX - vY)

    # Convert to RGB using Wide RGB D65 conversion.
    r = X * 1.656492 - Y * 0.354851 - Z * 0.255038
    g = -X * 0.707196 + Y * 1.655397 + Z * 0.036152
    b = X * 0.051713 - Y * 0.121364 + Z * 1.011530

    # Apply reverse gamma correction.
    r, g, b = map(
        lambda x: (12.92 * x) if (x <= 0.0031308) else
        ((1.0 + 0.055) * pow(x, (1.0 / 2.4)) - 0.055),
        [r, g, b]
    )

    # Bring all negative components to zero.
    r, g, b = map(lambda x: max(0, x), [r, g, b])

    # If one component is greater than 1, weight components by that value.
    max_component = max(r, g, b)
    if max_component > 1:
        r, g, b = map(lambda x: x / max_component, [r, g, b])

    ir, ig, ib = map(lambda x: int(x * 255), [r, g, b])

    return (ir, ig, ib)


def color_hsb_to_RGB(fH: float, fS: float, fB: float) -> Tuple[int, int, int]:
    """Convert a hsb into its rgb representation."""
    if fS == 0:
        fV = fB * 255
        return (fV, fV, fV)

    r = g = b = 0
    h = fH / 60
    f = h - float(math.floor(h))
    p = fB * (1 - fS)
    q = fB * (1 - fS * f)
    t = fB * (1 - (fS * (1 - f)))

    if int(h) == 0:
        r = int(fB * 255)
        g = int(t * 255)
        b = int(p * 255)
    elif int(h) == 1:
        r = int(q * 255)
        g = int(fB * 255)
        b = int(p * 255)
    elif int(h) == 2:
        r = int(p * 255)
        g = int(fB * 255)
        b = int(t * 255)
    elif int(h) == 3:
        r = int(p * 255)
        g = int(q * 255)
        b = int(fB * 255)
    elif int(h) == 4:
        r = int(t * 255)
        g = int(p * 255)
        b = int(fB * 255)
    elif int(h) == 5:
        r = int(fB * 255)
        g = int(p * 255)
        b = int(q * 255)

    return (int(r), int(g), int(b))


def color_RGB_to_hsv(iR: int, iG: int, iB: int) -> Tuple[float, float, float]:
    """Convert an rgb color to its hsv representation.
    Hue is scaled 0-360
    Sat is scaled 0-100
    Val is scaled 0-100
    """
    fHSV = colorsys.rgb_to_hsv(iR/255.0, iG/255.0, iB/255.0)
    return round(fHSV[0]*360, 3), round(fHSV[1]*100, 3), round(fHSV[2]*100, 3)


def color_RGB_to_hs(iR: int, iG: int, iB: int) -> Tuple[float, float]:
    """Convert an rgb color to its hs representation."""
    return color_RGB_to_hsv(iR, iG, iB)[:2]


def color_hsv_to_RGB(iH: float, iS: float, iV: float) -> Tuple[int, int, int]:
    """Convert an hsv color into its rgb representation.
    Hue is scaled 0-360
    Sat is scaled 0-100
    Val is scaled 0-100
    """
    fRGB = colorsys.hsv_to_rgb(iH/360, iS/100, iV/100)
    return (int(fRGB[0]*255), int(fRGB[1]*255), int(fRGB[2]*255))


def color_hs_to_RGB(iH: float, iS: float) -> Tuple[int, int, int]:
    """Convert an hsv color into its rgb representation."""
    return color_hsv_to_RGB(iH, iS, 100)


def color_xy_to_hs(vX: float, vY: float) -> Tuple[float, float]:
    """Convert an xy color to its hs representation."""
    h, s, _ = color_RGB_to_hsv(*color_xy_to_RGB(vX, vY))
    return (h, s)


def color_hs_to_xy(iH: float, iS: float) -> Tuple[float, float]:
    """Convert an hs color to its xy representation."""
    return color_RGB_to_xy(*color_hs_to_RGB(iH, iS))


def _match_max_scale(input_colors: Tuple[int, ...],
                     output_colors: Tuple[int, ...]) -> Tuple[int, ...]:
    """Match the maximum value of the output to the input."""
    max_in = max(input_colors)
    max_out = max(output_colors)
    if max_out == 0:
        factor = 0.0
    else:
        factor = max_in / max_out
    return tuple(int(round(i * factor)) for i in output_colors)


def color_rgb_to_rgbw(r, g, b):
    """Convert an rgb color to an rgbw representation."""
    # Calculate the white channel as the minimum of input rgb channels.
    # Subtract the white portion from the remaining rgb channels.
    w = min(r, g, b)
    rgbw = (r - w, g - w, b - w, w)

    # Match the output maximum value to the input. This ensures the full
    # channel range is used.
    return _match_max_scale((r, g, b), rgbw)


def color_rgbw_to_rgb(r, g, b, w):
    """Convert an rgbw color to an rgb representation."""
    # Add the white channel back into the rgb channels.
    rgb = (r + w, g + w, b + w)

    # Match the output maximum value to the input. This ensures the
    # output doesn't overflow.
    return _match_max_scale((r, g, b, w), rgb)


def color_rgb_to_hex(r, g, b):
    """Return a RGB color from a hex color string."""
    return '{0:02x}{1:02x}{2:02x}'.format(round(r), round(g), round(b))


def rgb_hex_to_rgb_list(hex_string):
    """Return an RGB color value list from a hex color string."""
    return [int(hex_string[i:i + len(hex_string) // 3], 16)
            for i in range(0,
                           len(hex_string),
                           len(hex_string) // 3)]


def color_temperature_to_hs(color_temperature_kelvin):
    """Return an hs color from a color temperature in Kelvin."""
    return color_RGB_to_hs(*color_temperature_to_rgb(color_temperature_kelvin))


def color_temperature_to_rgb(color_temperature_kelvin):
    """
    Return an RGB color from a color temperature in Kelvin.
    This is a rough approximation based on the formula provided by T. Helland
    http://www.tannerhelland.com/4435/convert-temperature-rgb-algorithm-code/
    """
    # range check
    if color_temperature_kelvin < 1000:
        color_temperature_kelvin = 1000
    elif color_temperature_kelvin > 40000:
        color_temperature_kelvin = 40000

    tmp_internal = color_temperature_kelvin / 100.0

    red = _get_red(tmp_internal)

    green = _get_green(tmp_internal)

    blue = _get_blue(tmp_internal)

    return (red, green, blue)


def _bound(color_component: float, minimum: float = 0,
           maximum: float = 255) -> float:
    """
    Bound the given color component value between the given min and max values.
    The minimum and maximum values will be included in the valid output.
    i.e. Given a color_component of 0 and a minimum of 10, the returned value
    will be 10.
    """
    color_component_out = max(color_component, minimum)
    return min(color_component_out, maximum)


def _get_red(temperature: float) -> float:
    """Get the red component of the temperature in RGB space."""
    if temperature <= 66:
        return 255
    tmp_red = 329.698727446 * math.pow(temperature - 60, -0.1332047592)
    return _bound(tmp_red)


def _get_green(temperature: float) -> float:
    """Get the green component of the given color temp in RGB space."""
    if temperature <= 66:
        green = 99.4708025861 * math.log(temperature) - 161.1195681661
    else:
        green = 288.1221695283 * math.pow(temperature - 60, -0.0755148492)
    return _bound(green)


def _get_blue(temperature: float) -> float:
    """Get the blue component of the given color temperature in RGB space."""
    if temperature >= 66:
        return 255
    if temperature <= 19:
        return 0
    blue = 138.5177312231 * math.log(temperature - 10) - 305.0447927307
    return _bound(blue)


def color_temperature_mired_to_kelvin(mired_temperature):
    """Convert absolute mired shift to degrees kelvin."""
    return math.floor(1000000 / mired_temperature)


def color_temperature_kelvin_to_mired(kelvin_temperature):
    """Convert degrees kelvin to mired shift."""
    return math.floor(1000000 / kelvin_temperature)