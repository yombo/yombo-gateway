from yombo.constants.devicetypes.fan import *
from yombo.constants.features import (FEATURE_NUMBER_OF_STEPS,
    FEATURE_ALL_OFF, FEATURE_ALL_ON, FEATURE_PINGABLE, FEATURE_POLLABLE, FEATURE_SEND_UPDATES)
from yombo.constants.commands import COMMAND_OFF, COMMAND_ON, COMMAND_SET_SPEED, COMMAND_SET_DIRECTION
from yombo.constants.inputs import INPUT_DIRECTION, INPUT_SPEED
from yombo.constants.status_extra import (STATUS_EXTRA_DIRECTION, STATUS_EXTRA_SPEED,
    STATUS_EXTRA_OSCILLATING)

from yombo.core.exceptions import YomboWarning
from yombo.lib.devices._device import Device


class Fan(Device):
    """
    A generic fan device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = "fan"
        self.TOGGLE_COMMANDS = [COMMAND_ON, COMMAND_OFF]  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            FEATURE_ALL_ON: False,
            FEATURE_ALL_OFF: False,
            FEATURE_PINGABLE: True,
            FEATURE_POLLABLE: True,
            FEATURE_SEND_UPDATES: False,
            FEATURE_NUMBER_OF_STEPS: 4  # # 0 = off, 4 = high
        })
        self.STATUS_EXTRA[STATUS_EXTRA_DIRECTION] = True
        self.STATUS_EXTRA[STATUS_EXTRA_OSCILLATING] = True
        self.STATUS_EXTRA[STATUS_EXTRA_SPEED] = True

        self.FAN_SPEED_NAME_TO_INT = {
            SPEED_OFF: 0,
            SPEED_LOW: 1,
            SPEED_MEDIUM: 2,
            SPEED_HIGH: 3,
        }

        self.FAN_SPEED_INT_TO_NAME = {
            0: SPEED_OFF,
            1: SPEED_LOW,
            2: SPEED_MEDIUM,
            3: SPEED_HIGH,
        }

    @property
    def speed(self):
        """
        Return the current speed of a fan.
        """
        if len(self.status_history) > 0:
            machine_status_extra = self.status_history[0].machine_status_extra
            if STATUS_EXTRA_SPEED in machine_status_extra:
                return machine_status_extra[STATUS_EXTRA_SPEED]
            else:
                return 0
        return None

    @property
    def direciton(self):
        """
        Return the current direciton of a fan.
        """
        if len(self.status_history) > 0:
            machine_status_extra = self.status_history[0].machine_status_extra
            if STATUS_EXTRA_DIRECTION in machine_status_extra:
                return machine_status_extra[STATUS_EXTRA_DIRECTION]
            else:
                return None
        return None

    def toggle(self, **kwargs):
        if self.status_history[0].machine_status == 0:
            if 'previous_on_speed' in self.meta:
                return self.command(COMMAND_ON, inputs={INPUT_SPEED: self.meta['previous_on_speed']})
            else:
                return self.command(COMMAND_ON, inputs={INPUT_SPEED: 4})
        else:
            return self.command(COMMAND_OFF)

    def fan_speed_to_int(self, speed):
        try:
            speed = int(speed)
        except:
            pass
        if isinstance(speed, int):
            if speed >= 0 and speed <= 3:
                return speed
            raise KeyError("Invalid fan integer speed: %s" % speed)
        if speed in self.FAN_SPEED_NAME_TO_INT:
            return self.FAN_SPEED_NAME_TO_INT[speed]
        else:
            raise KeyError('Unknown fan speed: %s' % speed)

    def check_set_speed(self, speed):
        if speed in (SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH):
            return True
        else:
            return False

    def set_speed(self, speed, user_id=None, component=None, gateway_id=None, callbacks=None):
        """
        Set the speed of a fan. Typically, these are the speeds:
        0=off
        1=slow
        2=medium
        3=fast

        :param speed:
        :param user_id:
        :param component:
        :param gateway_id:
        :param callbacks:
        :return:
        """
        # print("setting brightness for %s to %s" % (self.full_label, val))
        speed = self.fan_speed_to_int(speed)

        if gateway_id is None:
            gateway_id = self.gateway_id
        if component is None:
            component = "%s.%s" % (self.PLATFORM, self.SUB_PLATFORM)

        if speed <= 0:
            command = COMMAND_OFF
        else:
            command = COMMAND_SET_SPEED

        return self.command(
            cmd=command,
            requested_by={
                'user_id': user_id,
                'component': component,
                'gateway': gateway_id
            },
            inputs={INPUT_SPEED: speed},
            callbacks=callbacks,
        )

    def check_set_direction(self, direction):
        """
        Checks if a given direction value is valid.

        :param direction:
        :return:
        """
        if direction == DIRECTION_FORWARD or direction == DIRECTION_REVERSE:
            return True
        return False

    def set_direction(self, direction, user_id=None, component=None, gateway_id=None, callbacks=None):
        """
        Set the direction of the fan. There are two directions (can be relabeled by children).
        forward
        reverse

        :param direction:
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
            component = "%s.%s" % (self.PLATFORM, self.SUB_PLATFORM)

        if self.check_direction(direction) is False:
            raise YomboWarning("Fan direction is invalid.")

        return self.command(
            cmd=COMMAND_SET_SPEED,
            requested_by={
                'user_id': user_id,
                'component': component,
                'gateway': gateway_id
            },
            inputs={INPUT_DIRECTION: direction},
            callbacks=callbacks,
        )

    def turn_on(self, **kwargs):
        return self.command(COMMAND_ON, **kwargs)

    def turn_off(self, **kwargs):
        return self.command(COMMAND_OFF, **kwargs)
