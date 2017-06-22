from yombo.core.constants import TEMP_CELSIUS, TEMP_FAHRENHEIT
from yombo.lib.devices._device import Device

class Climate(Device):
    """
    A generic light device.
    """
    PLATFORM = "climate"

    def _start_(self):
        self.add_status_extra_allow('mode', ('heat', 'cool'))
        self.add_status_extra_allow('running', ('heat', 'heat2', 'heat3', 'heat_aux', 'cool', 'cool2', 'cool3', 'heat-cool',
            'idle', 'auto', 'dry', 'fan_only'))
        self.add_status_extra_allow('hold', ('away', 'home'))
        
        self.add_status_extra_any(('temperature', 'humidity', 'fan', 'target_temp', 'target_temp_high',
            'target_temp_low', 'target_temp_step', 'away_mode',
            'aux_heat', 'fan_list', 'target_humidity', 'max_humidity', 'min_humidity', 'hold_mode', 'operation_mode',
            'operation_list', 'swing_mode', 'swing_list', 'heat_delivery', 'heat_source', 'heat2_delivery',
            'heat2_source', 'heat3_delivery', 'heat3_source', 'heat_aux_delivery', 'heat_aux_source', 'cool_delivery',
            'cool_source', 'cool2_delivery', 'cool2_source', 'cool3_delivery', 'cool3_source', 'away_enabled',
            'away_temp_high', 'away_temp_low'))

    def _start_(self):
        self.temperature_unit = 'c' # what temperature unit the device works in.

    @property
    def current_mode(self):
        """
        Return current operation ie. heat, cool, off, auto.
        """
        return self.machine_status_extra['mode']

    @property
    def current_humidity(self):
        """
        Return the current humidity.
        """
        if 'humidity' in self.machine_status_extra:
            return self.machine_status_extra['humidity']
        return None

    @property
    def target_humidity(self):
        """
        Return the humidity we try to reach.
        """
        if 'target_humidity' in self.machine_status_extra:
            return self.machine_status_extra['target_humidity']
        return None

    @property
    def operation_list(self):
        """
        Return the list of available operation modes.
        """
        return self.STATUS_EXTRA['mode']

    @property
    def current_temperature(self):
        """
        Return the current temperature.
        """
        return self.machine_status

    @property
    def target_temperature(self):
        """
        Return the temperature we try to reach.
        """
        if self.current_mode is None:
            return None
        elif self.current_mode is 'cool':
            if 'target_temp_high' in self.machine_status_extra:
                return self.machine_status_extra['target_temp_high']
            else:
                return None
        elif self.current_mode is 'heat':
            if 'target_temp_low' in self.machine_status_extra:
                return self.machine_status_extra['target_temp_low']
            else:
                return None
        return None

    @property
    def target_temperature_range(self):
        """Return the temperature range we try to stay in. Used for auto mode."""
        low = None
        high = None

        if 'target_temp_low' in self.machine_status_extra:
            low = self.machine_status_extra['target_temp_low']
        if 'target_temp_high' in self.machine_status_extra:
            high = self.machine_status_extra['target_temp_high']

        return (low, high)

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        if 'target_temp_step' in self.machine_status_extra:
            return self.machine_status_extra['target_temp_step']
        return None

    @property
    def target_temperature_high(self):
        """Return the highbound target temperature we try to reach."""
        if 'target_temp_high' in self.machine_status_extra:
            return self.machine_status_extra['target_temp_high']
        return None

    @property
    def target_temperature_low(self):
        """Return the lowbound target temperature we try to reach."""
        if 'target_temp_low' in self.machine_status_extra:
            return self.machine_status_extra['target_temp_low']
        return None

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        if 'hold_mode' in self.machine_status_extra:
            return self.machine_status_extra['hold_mode'] == 'away'
        return None

    @property
    def current_hold_mode(self):
        """Return the current hold mode, e.g., home, away, temp."""
        if 'hold_mode' in self.machine_status_extra:
            return self.machine_status_extra['hold_mode']
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
        return convert_temperature(7, TEMP_CELSIUS, self.temperature_unit)

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return convert_temperature(35, TEMP_CELSIUS, self.temperature_unit)

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

    def turn_on(self, cmd, **kwargs):
        return self.command('on', **kwargs)

    def turn_off(self, cmd, **kwargs):
        return self.command('off', **kwargs)
