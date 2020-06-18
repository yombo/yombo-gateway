"""
Climate device types. Used to monitor and control thermostats.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/devicetypes/platforms/climate.html>`_
"""
from yombo.constants.features import (FEATURE_ALL_ON, FEATURE_ALL_OFF, FEATURE_PINGABLE,
                                      FEATURE_POLLABLE, FEATURE_ALLOW_IN_SCENES, FEATURE_DETECTS_MOTION,
                                      FEATURE_THERMOSTAT, FEATURE_MODES)
from yombo.constants.devicetypes.climate import (FEATURE_AWAY_MODE, FEATURE_AUX_HEAT, FEATURE_DUAL_SETPOINTS,
                                                 FEATURE_HOLD_MODE, FEATURE_ON_OFF, FEATURE_TARGET_HUMIDITY,
                                                 FEATURE_TARGET_HUMIDITY_LOW, FEATURE_TARGET_HUMIDITY_HIGH,
                                                 FEATURE_TARGET_TEMPERATURE, FEATURE_TARGET_TEMPERATURE_LOW,
                                                 FEATURE_TARGET_TEMPERATURE_HIGH, FEATURE_TARGET_TEMPERATURE_STEP)
from yombo.constants.state_extra import (STATE_EXTRA_TEMPERATURE, STATE_EXTRA_MODE, STATE_EXTRA_HUMIDITY,
                                         STATE_EXTRA_TARGET_TEMPERATURE, STATE_EXTRA_TARGET_TEMPERATURE_LOW,
                                         STATE_EXTRA_TARGET_TEMPERATURE_HIGH, STATE_EXTRA_TARGET_HUMIDITY,
                                         STATE_EXTRA_TARGET_HUMIDITY_LOW, STATE_EXTRA_TARGET_HUMIDITY_HIGH,
                                         STATE_EXTRA_TARGET_HUMIDITY
                                         )
from yombo.constants.devicetypes.climate import (MODE_AUTO, MODE_COOL, MODE_HEAT, MODE_AWAY, MODE_OFF, MODE_ON,
    MODE_COOL2, MODE_COOL3, MODE_HEAT2, MODE_HEAT3)
from yombo.constants.platforms import PLATFORM_BASE_CLIMATE, PLATFORM_CLIMATE

from yombo.lib.devices.device import Device


class Climate(Device):
    """
    A generic light device.
    """
    def __init__(self, *args, **kwargs):
        self._additional_to_dict_fields = self._additional_to_dict_fields + [
            "current_mode", "current_humidity", "target_humidity", "modes_available", "current_temperature",
            "target_temperature", "target_temperature_range", "target_temperature_step", "target_temperature_high",
            "target_temperature_low", "is_away_mode_on", "current_hold_mode", "is_aux_heat_on", "current_fan_mode",
            "fan_list", "current_swing_mode", "swing_list", "min_temp", "max_temp", "min_humidity", "max_humidity"
        ]
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = PLATFORM_BASE_CLIMATE
        self.PLATFORM = PLATFORM_CLIMATE
        self.FEATURES.update({
            FEATURE_ALL_ON: True,
            FEATURE_ALL_OFF: True,
            FEATURE_PINGABLE: True,
            FEATURE_POLLABLE: True,
            FEATURE_ALLOW_IN_SCENES: True,
            FEATURE_DETECTS_MOTION: False,
            FEATURE_THERMOSTAT: True,
            FEATURE_AWAY_MODE: True,
            FEATURE_AUX_HEAT: False,
            FEATURE_DUAL_SETPOINTS: False,
            FEATURE_HOLD_MODE: False,
            FEATURE_ON_OFF: False,
            FEATURE_TARGET_HUMIDITY: False,
            FEATURE_TARGET_HUMIDITY_LOW: False,
            FEATURE_TARGET_HUMIDITY_HIGH: False,
            FEATURE_TARGET_TEMPERATURE: True,
            FEATURE_TARGET_TEMPERATURE_LOW: False,
            FEATURE_TARGET_TEMPERATURE_HIGH: False,
            FEATURE_MODES: [MODE_ON, MODE_OFF, MODE_AUTO, MODE_COOL, MODE_HEAT, MODE_AWAY]
        })
        self.MACHINE_STATE_EXTRA_FIELDS[STATE_EXTRA_TEMPERATURE] = True
        self.MACHINE_STATE_EXTRA_FIELDS[STATE_EXTRA_MODE] = True

        self.temperature_unit = "c"  # what temperature unit the device works in. Either "c" or "f".

    @property
    def current_mode(self):
        """ Return current operation ie. heat, cool, off, auto. """
        return self.get_state_extra(STATE_EXTRA_MODE)

    @property
    def current_humidity(self):
        """ Return the current humidity. """
        return self.get_state_extra(STATE_EXTRA_HUMIDITY)

    @property
    def current_temperature(self):
        """ Return the current temperature. """
        return self.get_state_extra(STATE_EXTRA_TEMPERATURE)

    @property
    def target_humidity(self):
        """ Return the humidity we try to reach. """
        return self.get_state_extra(STATE_EXTRA_TARGET_HUMIDITY)

    @property
    def target_humidity_high(self):
        """ Return the humidity we try to reach. """
        return self.get_state_extra(STATE_EXTRA_TARGET_HUMIDITY_LOW)

    @property
    def target_humidity_low(self):
        """ Return the humidity we try to reach. """
        return self.get_state_extra(STATE_EXTRA_TARGET_HUMIDITY_LOW)

    @property
    def modes_available(self):
        """ Return the list of available operation modes. """
        return self.FEATURES[FEATURE_MODES]

    @property
    def target_temperature(self):
        """
        Return the temperature we try to reach.
        """
        if self.current_mode is None:
            return None
        if len(self.state_history) > 0:
            current_mode = self.current_mode
            if self.has_device_feature(FEATURE_DUAL_SETPOINTS) in False:
                return self.get_state_extra(STATE_EXTRA_TARGET_TEMPERATURE)

            if current_mode in (MODE_COOL, MODE_COOL2, MODE_COOL3, MODE_AUTO):
                target = self.get_state_extra(FEATURE_TARGET_TEMPERATURE_HIGH)
                if target is None:
                    return None
                else:
                    return target
            elif current_mode in (MODE_HEAT, MODE_HEAT2, MODE_HEAT3, MODE_AUTO):
                target = self.get_state_extra(FEATURE_TARGET_TEMPERATURE_HIGH)
                if target is None:
                    return None
                else:
                    return target
        return None

    @property
    def target_temperature_range(self):
        """Return the temperature range we try to stay in. Used for auto mode."""
        if self.has_device_feature(FEATURE_DUAL_SETPOINTS) in False:
            target = self.get_state_extra(STATE_EXTRA_TARGET_TEMPERATURE)
            return target, target

        low = self.get_state_extra(FEATURE_TARGET_TEMPERATURE_LOW)
        high = self.get_state_extra(FEATURE_TARGET_TEMPERATURE_HIGH)
        return low, high

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        if len(self.state_history) > 0:
            status_current = self.machine_state_extra[0]
            if "target_temp_step" in status_current:
                return status_current[FEATURE_TARGET_TEMPERATURE_STEP]
        return None

    @property
    def target_temperature_high(self):
        """Return the highbound target temperature we try to reach."""
        if len(self.state_history) > 0:
            status_current = self.machine_state_extra[0]
            if "target_temp_high" in status_current:
                return status_current[FEATURE_TARGET_TEMPERATURE_HIGH]
        return None

    @property
    def target_temperature_low(self):
        """Return the lowbound target temperature we try to reach."""
        if len(self.state_history) > 0:
            status_current = self.machine_state_extra[0]
            if "target_temp_low" in status_current:
                return status_current[FEATURE_TARGET_TEMPERATURE_LOW]
        return None

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        if len(self.state_history) > 0:
            status_current = self.machine_state_extra[0]
            if FEATURE_HOLD_MODE in status_current:
                return status_current[FEATURE_HOLD_MODE] == MODE_AWAY
        return None

    @property
    def current_hold_mode(self):
        """Return the current hold mode, e.g., home, away, temp."""
        if len(self.state_history) > 0:
            status_current = self.machine_state_extra[0]
            if FEATURE_HOLD_MODE in status_current:
                return status_current[FEATURE_HOLD_MODE]
        return None

    @property
    def is_aux_heat_on(self):
        """Return true if aux heater is running."""
        return None

    @property
    def current_fan_mode(self):
        """Return the fan setting. Usually: on, auto, off"""
        return None

    @property
    def fan_list(self):
        """Return the list of available fan modes."""
        return None

    @property
    def current_swing_mode(self):
        """Return the fan setting."""
        return None

    @property
    def swing_list(self):
        """Return the list of available swing modes."""
        return None

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._Localize.display_temperature(7, "c", self.temperature_unit)

    @property
    def max_temp(self):
        """Return the maximum temp
        erature."""
        return self._Localize.display_temperature(35, "c", self.temperature_unit)

    @property
    def min_humidity(self):
        """Return the minimum humidity."""
        return 30

    @property
    def max_humidity(self):
        """Return the maximum humidity."""
        return 99

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        raise NotImplementedError()

    def set_humidity(self, humidity):
        """Set new target humidity."""
        raise NotImplementedError()

    def set_fan_mode(self, fan):
        """Set new target fan mode."""
        raise NotImplementedError()

    def set_operation_mode(self, operation_mode):
        """Set new target operation mode."""
        raise NotImplementedError()

    def set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        raise NotImplementedError()

    def turn_away_mode_on(self):
        """Turn away mode on."""
        raise NotImplementedError()

    def turn_away_mode_off(self):
        """Turn away mode off."""
        raise NotImplementedError()

    def set_hold_mode(self, hold_mode):
        """Set new target hold mode."""
        raise NotImplementedError()

    def turn_aux_heat_on(self):
        """Turn auxillary heater on."""
        raise NotImplementedError()

    def turn_aux_heat_off(self):
        """Turn auxillary heater off."""
        raise NotImplementedError()

    def can_toggle(self):
        return False

    def turn_on(self, **kwargs):
        return self.command("on", **kwargs)

    def turn_off(self, **kwargs):
        return self.command("off", **kwargs)
