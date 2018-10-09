from yombo.constants.devicetypes.light import *
from yombo.constants.commands import COMMAND_OFF, COMMAND_ON
from yombo.constants.features import (FEATURE_BRIGHTNESS, FEATURE_COLOR_TEMP, FEATURE_EFFECT, FEATURE_PERCENT,
    FEATURE_RGB_COLOR, FEATURE_TRANSITION, FEATURE_WHITE_VALUE, FEATURE_XY_COLOR, FEATURE_NUMBER_OF_STEPS)
from yombo.constants.inputs import INPUT_BRIGHTNESS
from yombo.constants.platforms import PLATFORM_BASE_LIGHT, PLATFORM_COLOR_LIGHT, PLATFORM_LIGHT
from yombo.constants.status_extra import STATUS_EXTRA_BRIGHTNESS, STATUS_EXTRA_RGB_COLOR

from yombo.lib.devices._device import Device
import yombo.utils.color as color_util
from yombo.utils.converters import translate_int_value


class Light(Device):
    """
    A generic light device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = PLATFORM_BASE_LIGHT
        self.PLATFORM = PLATFORM_LIGHT
        self.TOGGLE_COMMANDS = [COMMAND_ON, COMMAND_OFF]  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            FEATURE_BRIGHTNESS: True,
            FEATURE_PERCENT: True,
            FEATURE_COLOR_TEMP: False,
            FEATURE_EFFECT: False,
            FEATURE_RGB_COLOR: False,
            FEATURE_XY_COLOR: False,
            FEATURE_WHITE_VALUE: False,
            FEATURE_TRANSITION: False,
            FEATURE_NUMBER_OF_STEPS: 255
        })
        self.MACHINE_STATUS_EXTRA_FIELDS[STATUS_EXTRA_BRIGHTNESS] = True
        self.MACHINE_STATUS_EXTRA_FIELDS[STATUS_EXTRA_RGB_COLOR] = True

    def set_brightness(self, brightness, **kwargs):
        """
        Set the brightness of the light, but the application or sender must know how many steps
        the light can handle (100, 256, 1045, etc.)  Typically, light devices are controlled by
        percentage and should actually use the set_percent() methid.


        :param brightness:
        :param kwargs:
        :return:
        """
        if brightness <= 0:
            command = COMMAND_OFF
        else:
            command = COMMAND_ON

        if 'inputs' not in kwargs:
            kwargs['inputs'] = {}
        kwargs['inputs'][INPUT_BRIGHTNESS] = brightness
        return self.command(command, **kwargs)

    def set_percent(self, percent, **kwargs):
        """
        Set the light based on a percent. Basically, just converts brightness to the devices
        step range, and forwards request to set_brightness()

        :param percent:
        :param user_id:
        :param component:
        :param gateway_id:
        :return:
        """
        brightness = translate_int_value(percent,
                                         0, 100,
                                         0, self.FEATURES[FEATURE_NUMBER_OF_STEPS])
        return self.set_brightness(brightness, **kwargs)

    def set_color(self, rgb, **kwargs):
        """
        Set the color of a light.

        :param rgb: a list of 3 integers representing red, green, blue.
        :return:
        """
        command = COMMAND_ON
        if 'inputs' not in kwargs:
            kwargs['inputs'] = {}

        kwargs['inputs'][ATR_RGB_COLOR] = rgb
        return self.command(command, **kwargs)

    @property
    def is_dimmable(self):
        return True

    @property
    def brightness(self):
        """
        Return the brightness of this light. Returns a range between 0 and 100, converts based on the
        'number_of_steps'.
        """
        if len(self.status_history) > 0:
            machine_status_extra = self.status_history[0].machine_status_extra
            if STATUS_EXTRA_BRIGHTNESS in machine_status_extra:
                return machine_status_extra[STATUS_EXTRA_BRIGHTNESS]
            else:
                return 0
        return None

    @property
    def percent(self):
        """
        Return the brightness as a percent for this light. Returns a range between 0 and 100, converts based on the
        'number_of_steps'.
        """
        if len(self.status_history) > 0:
            machine_status_extra = self.status_history[0].machine_status_extra
            if STATUS_EXTRA_BRIGHTNESS in machine_status_extra:
                return translate_int_value(machine_status_extra[STATUS_EXTRA_BRIGHTNESS],
                                           0, self.FEATURES[FEATURE_NUMBER_OF_STEPS],
                                           0, 100)
            else:
                return 0
        return None

    def calc_percent(self, machine_status_extra):
        """
        Like percent property, but accepts machine_status as input
        """
        if STATUS_EXTRA_BRIGHTNESS in machine_status_extra:
            return translate_int_value(machine_status_extra[STATUS_EXTRA_BRIGHTNESS],
                                       0, self.FEATURES[FEATURE_NUMBER_OF_STEPS],
                                       0, 100)
        else:
            return 0

    @property
    def hsv_color(self):
        """
        Return the HS color value [float, float, float].
        """
        return color_util.color_RGB_to_hsv(*self.rgb_color)

    @property
    def hs_color(self):
        """
        Return the HS color value [float, float, float].
        """
        return color_util.color_RGB_to_hsv(*self.rgb_color)

    @property
    def xy_color(self):
        """
        Return the HS color value [float, float, float].
        """
        return color_util.color_RGB_to_xy(*self.rgb_color)

    @property
    def xy_color_brightness(self):
        """
        Return the HS color value [float, float, float].
        """
        return color_util.color_RGB_to_xy_brightness(*self.rgb_color)

    @property
    def rgb_color(self):
        """
        Return the RGB color value [int, int, int].
        """
        if len(self.status_history) > 0:
            machine_status_extra = self.status_history[0].machine_status_extra
            if STATUS_EXTRA_RGB_COLOR in machine_status_extra:
                rgb = machine_status_extra[STATUS_EXTRA_RGB_COLOR]
                return rgb
            else:
                return 0, 0, 0
        return None

    @property
    def rgb_hex(self):
        return color_util.color_rgb_to_hex(*self.rgb_color)

    @property
    def color_temp(self):
        """
        Return the CT color value in mireds.
        """
        return None

    @property
    def min_mireds(self):
        """
        Return the coldest color_temp that this light supports.
        """
        return 154

    @property
    def max_mireds(self):
        """
        Return the warmest color_temp that this light supports.
        """
        return 500

    @property
    def white_value(self):
        """
        Return the white value of this light between 0..255.
        """
        return None

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return None

    @property
    def effect(self):
        """
        Return the current effect.
        """
        return None

    @property
    def status_attributes(self):
        """
        Return optional status attributes.
        """
        data = {}
        status = self.status_history[0].machine_status_extra
        if self.is_on:
            for prop, value in status.items():
                if value is not None:
                    data[prop] = value

            if ATR_RGB_COLOR not in data and ATR_XY_COLOR in data and ATR_BRIGHTNESS in data:
                data[ATR_RGB_COLOR] = color_util.color_xy_brightness_to_RGB(
                    data[ATR_XY_COLOR][0], data[ATR_XY_COLOR][1],
                    data[ATR_BRIGHTNESS])
        return data

    def toggle(self, **kwargs):
        if self.status_history[0].machine_status == 0:
            return self.command(COMMAND_ON, **kwargs)
        else:
            return self.command(COMMAND_OFF, **kwargs)

    def turn_on(self, **kwargs):
        return self.command(COMMAND_ON, **kwargs)

    def turn_off(self, **kwargs):
        return self.command(COMMAND_OFF, **kwargs)

    def generate_human_status(self, machine_status, machine_status_extra):
        return str(self.calc_percent(machine_status_extra)) + '%'

    def generate_human_message(self, machine_status, machine_status_extra):
        return "%s is now %s%%" % (self.area_label, self.calc_percent(machine_status_extra))

class Color_Light(Light):
    """
    A generic light device.
    """
    PLATFORM = PLATFORM_COLOR_LIGHT

    TOGGLE_COMMANDS = [COMMAND_ON, COMMAND_OFF]  # Put two command machine_labels in a list to enable toggling.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = PLATFORM_COLOR_LIGHT
        self.FEATURES[FEATURE_BRIGHTNESS] = True
        self.FEATURES[FEATURE_COLOR_TEMP] = False
        self.FEATURES[FEATURE_EFFECT] = False
        self.FEATURES[FEATURE_RGB_COLOR] = True
        self.FEATURES[FEATURE_XY_COLOR] = False
        self.FEATURES[FEATURE_TRANSITION] = False
        self.FEATURES[FEATURE_WHITE_VALUE] = False
        self.FEATURES[FEATURE_NUMBER_OF_STEPS] = 255
