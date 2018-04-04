from yombo.constants.devicetypes.light import *
from yombo.constants.features import (FEATURE_BRIGHTNESS, FEATURE_COLOR_TEMP, FEATURE_EFFECT, FEATURE_PERCENT,
    FEATURE_RGB_COLOR, FEATURE_TRANSITION, FEATURE_WHITE_VALUE, FEATURE_XY_COLOR, FEATURE_NUMBER_OF_STEPS)
from yombo.constants.status_extra import STATUS_EXTRA_BRIGHTNESS
from yombo.constants.commands import COMMAND_OFF, COMMAND_ON
from yombo.constants.inputs import INPUT_BRIGHTNESS

from yombo.lib.devices._device import Device
import yombo.utils.color as color_util
from yombo.utils import translate_int_value


class Light(Device):
    """
    A generic light device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = "light"
        self.PLATFORM = "light"
        self.TOGGLE_COMMANDS = ['on', 'off']  # Put two command machine_labels in a list to enable toggling.
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
        self.STATUS_EXTRA[STATUS_EXTRA_BRIGHTNESS] = True

    @property
    def brightness(self):
        """
        Return the brightness of this light. Returns a range between 0 and 100, converts based on the
        'number_of_steps'.
        """
        if len(self.status_history) > 0:
            machine_status_extra = self.status_history[0].machine_status_extra
            if STATUS_EXTRA_BRIGHTNESS in machine_status_extra:
                return translate_int_value(machine_status_extra[STATUS_EXTRA_BRIGHTNESS],
                                           0, self.FEATURES[FEATURE_BRIGHTNESS],
                                           0, 100)
            else:
                return 0
        return None

    def set_brightness(self, brightness, user_id=None, component=None, gateway_id=None, callbacks=None):
        """
        Set the brightness of the light, but the application or sender must know how many steps
        the light can handle (100, 256, 1045, etc.)  Typically, light devices are controlled by
        percentage and should actually use the set_percent() methid.

        :param brightness:
        :param user_id:
        :param component:
        :param gateway_id:
        :param callbacks:
        :return:
        """
        # print("setting brightness for %s to %s" % (self.full_label, val))
        if gateway_id is None:
            gateway_id = self.gateway_id
        if component is None:
            component = "yombo.gateway.lib.devices.light"

        if brightness <= 0:
            command = COMMAND_OFF
        else:
            command = COMMAND_ON

        return self.command(
            cmd=command,
            requested_by={
                'user_id': user_id,
                'component': component,
                'gateway': gateway_id
            },
            inputs={INPUT_BRIGHTNESS: brightness},
            callbacks=callbacks,
        )

    def set_percent(self, percent, user_id=None, component=None, gateway_id=None, callbacks=None):
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
        return self.set_brightness(brightness, user_id, component, gateway_id, callbacks)

    @property
    def xy_color(self):
        """
        Return the XY color value [float, float].
        """
        return None

    @property
    def rgb_color(self):
        """
        Return the RGB color value [int, int, int].
        """
        return None

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
        if 'brightness' not in machine_status_extra or machine_status_extra[STATUS_EXTRA_BRIGHTNESS] is None:
            return "Unknown"
        return str(translate_int_value(machine_status_extra[STATUS_EXTRA_BRIGHTNESS],
                                       0, self.FEATURES[FEATURE_NUMBER_OF_STEPS], 0, 100)) + '%'

    def generate_human_message(self, machine_status, machine_status_extra):
        human_status = str(translate_int_value(machine_status_extra[STATUS_EXTRA_BRIGHTNESS],
                                               0, self.FEATURES[FEATURE_NUMBER_OF_STEPS], 0, 100))
        return "%s is now %s%%" % (self.area_label, human_status)

class Color_Light(Light):
    """
    A generic light device.
    """
    PLATFORM = "colorlight"

    TOGGLE_COMMANDS = [COMMAND_ON, COMMAND_OFF]  # Put two command machine_labels in a list to enable toggling.

    def _start_(self, **kwargs):
        super()._start_()
        self.FEATURES[FEATURE_BRIGHTNESS] = True
        self.FEATURES[FEATURE_COLOR_TEMP] = False
        self.FEATURES[FEATURE_EFFECT] = False
        self.FEATURES[FEATURE_RGB_COLOR] = True
        self.FEATURES[FEATURE_XY_COLOR] = False
        self.FEATURES[FEATURE_TRANSITION] = False
        self.FEATURES[FEATURE_WHITE_VALUE] = False
        self.FEATURES[FEATURE_NUMBER_OF_STEPS] = 255
