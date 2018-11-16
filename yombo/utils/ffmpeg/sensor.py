# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Use ffmpeg as motion or video sensor. These can be used as triggers to perform various events.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""

import re
from time import time

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

from .ffmpeg import YBOFFmpeg

logger = get_logger("utils.ffmpeg.sensor")


class FFmpegSensorBase(YBOFFmpeg):
    """
    The base class for using ffmpeg as a sensor. 
    """
    STATE_NONE = 0
    STATE_HIGH = 1

    @property
    def state(self):
        if self._state == self.STATE_NONE:
            return self._state
        if (time() - self._sensor_high_last_time) > self._low_timeout:
            self._state = self.STATE_NONE
        return self._state

    @state.setter
    def state(self, val):
        self._state = val

    def __init__(self, parent, sensor_callback, connected_callback=None, closed_callback=None, **kwargs):
        """
        Setup the sensor.

        :param parent: 
        :param sensor_callback: The method to call when the sensor is on/off. 
        :param connected_callback: A method to call when connected.
        :param closed_callback: A method to call when disconnected.
        :param kwargs: Additional arguments to send to class YBOFFmpeg
        """
        super().__init__(parent, stdout_callback=self.process_output, closed_callback=closed_callback, **kwargs)

        self._connected_callback = connected_callback  # Don't let YBOFFmpeg directly handle connected_callback.
        self._sensitivity = None  # How much noise or sound is required before tripping the sensor.
        self._reactivate_timeout = None
        self._low_timeout = None  # How many seconds of quite/no motion must occur before sending state=False
        self._reactivate_timeout = None
        self._sensor_callback = sensor_callback

        self._sensor_high_start_time = 0
        self._sensor_high_last_time = 0
        self._sensor_high_trip_count = 0
        self._sensor_stopped_calllater = None
        self._state = self.STATE_NONE
        self.sensor_trip_start_time = None
        self.sensor_connected_callback_called = None

    def close(self):
        """
        Set sensor_connected_callback_called as false when connection is closed.
        :return:
        """
        self.sensor_connected_callback_called = False
        super().close()

    def reset_delay(self):
        """
        The reset delay is called after a stable connection. This can also be used to send the _connect_callback.

        :return:
        """
        super().reset_delay()
        if self.sensor_connected_callback_called is False:
            self.sensor_connected_callback_called = True
            if self._connected_callback is not None:
                self._connected_callback()

    def _sensor_tripped(self):
        # print(f"sensor_tripped: {self.sensor_type}, count: {self._sensor_high_trip_count}")
        if self.sensor_connected_callback_called is False:  # toss away the first frame. Call connected_callback if it's not called.
            if self._connected_callback is not None:
                self._connected_callback()
            return
            self.sensor_connected_callback_called = True

        self._sensor_high_last_time = time()
        # print("adding 1 _sensor_high_trip_count")
        self._sensor_high_trip_count += 1
        if self._state == self.STATE_NONE:  # Start of noise begin.
            self._sensor_high_start_time = time()
            self._state = self.STATE_HIGH
            self._sensor_high()

    def _sensor_high(self):
        # print("setting _sensor_high_trip_count to 1")
        self._sensor_high_trip_count = 1
        self._sensor_callback(state=self.state, duration=0, trip_count=0)

    def _sensor_low(self):
        self.state = self.STATE_NONE
        duration = round(float(time()) - self._sensor_high_start_time, 3)
        self._sensor_callback(state=self.state, duration=duration, trip_count=self._sensor_high_trip_count)
        # print("setting _sensor_high_trip_count to 0, final.")
        self._sensor_high_trip_count = 0

    def process_output(self, data):
        """
        Any results from FFmpeg standard output will be sent here. This method must be overridden by a child.

        :param data:
        :return:
        """
        raise NotImplementedError


class SensorNoise(FFmpegSensorBase):
    """
    Detects noise from the provided URL.
    """
    def __init__(self, parent, sensor_callback,
                 sensitivity=None, reactivate_timeout=None, low_timeout=None,
                 connected_callback=None, closed_callback=None, **kwargs):
        """
        Setup a noise listening sensor.

        Low Timeout - This is the number of seconds that it takes after hearing a noise and calling
        the sensor_callback with 'False' again.

        **WARNING** Using a high low timeout will
        
        The sensor_callback will receive these named arguments:
          * state - True if noise is present, other was False.
          * duration - How long the noise persisted for, will be 0 if state is high.

        :param parent: A library or module reference to this caller.
        :param sensor_callback: The method to call when the sensor is on/off. 
        :param sensitivity: How loud something needs to be before activing sensor_callback
        :param reactivate_timeout: How many seconds after the last sound trip before the next one can be sent.
        :param low_timeout: How many seconds after the last sound detection before sending all clear.
        :param connected_callback: This is called once FFMPEG is connected and listening to audio.
        :param closed_callback: Called when FFMEP stops listening.
        """
        super().__init__(parent, sensor_callback, connected_callback=connected_callback,
                         closed_callback=closed_callback, **kwargs)

        # tweak FFmpegSensorBase - where we get the data from, defaults to stdout.
        self.stdout_callback = None
        self.errout_callback = self.process_output

        self.sensor_type = "ffmpeg noise"

        self.set_options(
            sensitivity=sensitivity or -25,
            reactivate_timeout=reactivate_timeout or 30,
            low_timeout=low_timeout or 30,
        )

        # print(f"sensor: low_timeout: {self._low_timeout}")

        self.re_start = re.compile("silence_start")
        self.re_end = re.compile("silence_end")

    def set_options(self, sensitivity=None, reactivate_timeout=None, low_timeout=None):
        """
        Update sensor parameters.
        """
        if sensitivity is not None:
            self._sensitivity = abs(sensitivity)*-1
        if reactivate_timeout is not None:
            self._reactivate_timeout = reactivate_timeout
        if low_timeout is not None:
            if low_timeout < 2:
                low_timeout = 2
            self._low_timeout = low_timeout

    @inlineCallbacks
    def open_sensor(self, input_source, extra_cmd=None):
        """
        Starts ffmep to monitor for noise.

        :param input_source:
        :param extra_cmd:
        :return:
        """
        commands = [
            "-vn",
            "-filter:a",
            f"silencedetect=n={self._sensitivity}dB:d={1}"
        ]
        if extra_cmd is None:
            extra_cmd = ""
        extra_cmd += " -f null"

        yield self.open(input_source, commands, output="-", extra_cmd=extra_cmd)

    def process_output(self, in_line):
        """
        Lines of output come here...
        """
        in_line = in_line.decode("utf-8")
        # print(f"noise sensor, process_out: received: {in_line}")

        if self.re_end.search(in_line):  # Start of noise
            self._sensor_tripped()

        if self.re_start.search(in_line):  # Start of silence.
            if self.sensor_connected_callback_called is False:
                self.sensor_connected_callback_called = True
                if self._connected_callback is not None:
                    self._connected_callback()

            if self.state == self.STATE_HIGH:  # Setup motion stopped timer.
                if self._sensor_stopped_calllater is not None and self._sensor_stopped_calllater.active():
                    self._sensor_stopped_calllater.reset(self._low_timeout)
                else:
                    self._sensor_stopped_calllater = reactor.callLater(self._low_timeout, self._sensor_low)


class SensorMotion(FFmpegSensorBase):
    """
    Detects motion from the provided URL.
    """
    def __init__(self, parent, sensor_callback, source_type=None,
                 sensitivity=None, reactivate_timeout=None, low_timeout=None,
                 framerate=None, connected_callback=None, closed_callback=None):
        """
        Setup a motion detection sensor.

        The "source_type" must be defined as either 'image'/'still' or 'video'/'movie'. It's preferred
        to use still images url from the camera for lower CPU usage. However, videos can be used too at
        the expense of CPU.  ** Unless someone finds a way to lower the framerate using an ffmpeg input filter.

        Note: The source_type can be defined at init, or in 'open_sensor' call.

        Low Timeout - This is the number of seconds that it takes after detecting motion and calling
        the sensor_callback with 'False' again.

        The sensor_callback will receive these named arguments:
          * state - True if noise is present, other was False.
          * duration - How long the noise persisted for, will be 0 if state is high.

        :param parent: A library or module reference to this caller.
        :param sensor_callback: The method to call when the sensor is on/off.
        :param sensitivity: How loud something needs to be before activing sensor_callback
        :param reactivate_timeout: How many seconds after the last sound trip before the next one can be sent.
        :param low_timeout: How many seconds after the last sound detection before sending all clear. Min: 3 seconds.
        :param framerate: How many frames per second to look for motion, lower uses less CPU.
        :param connected_callback: This is called once FFMPEG is connected and listening to audio.
        :param closed_callback: Called when FFMEP stops listening.
        """
        super().__init__(parent, sensor_callback, connected_callback=connected_callback,
                         closed_callback=closed_callback)

        self.sensor_type = "ffmpeg motion"
        self._source_type = None
        self._framerate = None

        # The first frame is always detected as motion, ignore it. Also used to send connected callback.
        self.set_options(
            sensitivity=sensitivity or 10,
            reactivate_timeout=reactivate_timeout or 30,
            low_timeout=low_timeout or 30,
            source_type=source_type,
            framerate=framerate or 5
        )

        # print(f"sensor: low_timeout: {self._low_timeout}")
        self.last_activity = None

        self.re_data = re.compile(r"\d,.*\d,.*\d,.*\d,.*\d,.*\w")

    def set_options(self, sensitivity=None, reactivate_timeout=None, low_timeout=None,
                    source_type=None, framerate=None):
        """
        Update sensor parameters.
        """
        if sensitivity is not None:
            self._sensitivity = sensitivity
        if reactivate_timeout is not None:
            self._reactivate_timeout = reactivate_timeout
        if low_timeout is not None:
            if low_timeout < 2:
                low_timeout = 2
            self._low_timeout = low_timeout

        if source_type is not None:
            if source_type.lower() in ("still", "image", "jpeg"):
                self._source_type = "image"
            elif source_type.lower() in ("movie", "video"):
                self._source_type = "video"
            else:
                raise YomboWarning("Invalid source_type, must one of: image or video")
        if framerate is not None:
            self._framerate = framerate

    @inlineCallbacks
    def open_sensor(self, input_source, source_type=None, extra_cmd=None):
        """
        Starts ffmep to monitor for motion.

        :param input_source:
        :param source_type: 'still' or 'video'.
        :param extra_cmd:
        :return:
        """
        self.set_options(source_type=source_type)
        if source_type is None:
            raise YomboWarning("source_type must be define at instance creation time or with 'open_sensor()'.")

        if self._source_type == "image":
            input = f"-framerate {self._framerate} -re -loop 1 -i {input_source}"
            commands = [
                "-vf",
                f"select=gt(scene\,{self._sensitivity / 1000})",
                "-f",
                "framemd5",
            ]
        else:
            input = input_source
            commands = [
                "-an",
                "-vf",
                f"select=gt(scene\,{self._sensitivity / 1000})",
                "-f",
                "framemd5",
                # "select=gt(scene\\,{0})".format(self._sensitivity / 1000),
            ]

        results = yield self.open(input, commands, output="-", extra_cmd=extra_cmd)
        return results

    def process_output(self, in_line):
        """
        Lines of output come here...
        """
        in_line = in_line.decode("utf-8")
        # print(f"sensors (motion): process_output: received: {in_line}")
        if self.re_data.search(in_line):  # Setup motion stopped timer.
            if self._sensor_stopped_calllater is not None and self._sensor_stopped_calllater.active():
                self._sensor_stopped_calllater.reset(self._low_timeout)
            else:
                self._sensor_stopped_calllater = reactor.callLater(self._low_timeout, self._sensor_low)

            self._sensor_tripped()
