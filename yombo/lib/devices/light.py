from yombo.lib.devices._device import Device
import yombo.utils.color as color_util

# Brightness of the light, 0..255 or percentage
ATR_BRIGHTNESS = "brightness"
ATR_BRIGHTNESS_PCT = "brightness_pct"

# Integer that represents transition time in seconds to make change.
ATR_TRANSITION = "transition"

# Lists holding color values
ATR_RGB_COLOR = "rgb_color"
ATR_XY_COLOR = "xy_color"
ATR_COLOR_TEMP = "color_temp"
ATR_KELVIN = "kelvin"
ATR_MIN_MIREDS = "min_mireds"
ATR_MAX_MIREDS = "max_mireds"
ATR_COLOR_NAME = "color_name"
ATR_WHITE_VALUE = "white_value"


class Light(Device):
    """
    A generic light device.
    """
    PLATFORM = "light"

    TOGGLE_COMMANDS = ['on', 'off']  # Put two command machine_labels in a list to enable toggling.

    def _start_(self, **kwargs):
        super()._start_()
        self.FEATURES['brightness'] = True
        self.FEATURES['color_temp'] = False
        self.FEATURES['effect'] = False
        self.FEATURES['rgb_color'] = False
        self.FEATURES['xy_color'] = False
        self.FEATURES['transition'] = False
        self.FEATURES['white_value'] = False
        self.FEATURES['number_of_steps'] = 255

    @property
    def brightness(self):
        """
        Return the brightness of this light between 0..255.
        """
        if len(self.status_history) > 0:
            status_current = self.status_history[0]
            return status_current.machine_status

        return None

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

            if ATR_RGB_COLOR not in data and ATR_XY_COLOR in data and \
                            ATR_BRIGHTNESS in data:
                data[ATR_RGB_COLOR] = color_util.color_xy_brightness_to_RGB(
                    data[ATR_XY_COLOR][0], data[ATR_XY_COLOR][1],
                    data[ATR_BRIGHTNESS])
        return data

    def toggle(self):
        if self.status_history[0].machine_state == 0:
            return self.command('on')
        else:
            return self.command('off')

    def turn_on(self, cmd, **kwargs):
        return self.command('on', **kwargs)

    def turn_off(self, cmd, **kwargs):
        return self.command('off', **kwargs)


class Color_Light(Light):
    """
    A generic light device.
    """
    PLATFORM = "light"

    TOGGLE_COMMANDS = ['on', 'off']  # Put two command machine_labels in a list to enable toggling.

    def _start_(self, **kwargs):
        super()._start_()
        self.FEATURES['brightness'] = True
        self.FEATURES['color_temp'] = False
        self.FEATURES['effect'] = False
        self.FEATURES['rgb_color'] = True
        self.FEATURES['xy_color'] = False
        self.FEATURES['transition'] = False
        self.FEATURES['white_value'] = False
        self.FEATURES['number_of_steps'] = 255
