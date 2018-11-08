"""
Various camera type devices.
"""
from time import time

from twisted.internet.defer import inlineCallbacks

from yombo.constants.features import (FEATURE_NUMBER_OF_STEPS, FEATURE_ALL_ON, FEATURE_ALL_OFF, FEATURE_PINGABLE,
                                      FEATURE_POLLABLE, FEATURE_ALLOW_IN_SCENES, FEATURE_DETECTS_MOTION)
from yombo.constants.commands import COMMAND_STOP, COMMAND_RECORD, COMMAND_ON, COMMAND_OFF
from yombo.constants.platforms import PLATFORM_BASE_CAMERA, PLATFORM_CAMERA, PLATFORM_VIDEO_CAMERA
from yombo.constants.status_extra import SEVALUE_IDLE, SEVALUE_RECORDING
from yombo.lib.devices._device import Device
from yombo.utils import sleep

DEFAULT_CONTENT_TYPE = "image/jpeg"

CONFIG_MJPEG_URL = "mjpeg_url"
CONFIG_STILL_IMAGE_URL = "still_image_url"


class Image(object):
    """Represent an image."""
    def __init__(self, content_type, image, created_at=None):
        self.content_type = content_type
        self.content = image
        self.created_at = created_at or time()


class Camera(Device):
    """
    The base class for all camera devices, including video recoding.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM_BASE = PLATFORM_BASE_CAMERA
        self.PLATFORM = PLATFORM_CAMERA
        self.TOGGLE_COMMANDS = [COMMAND_ON, COMMAND_OFF]  # Put two command machine_labels in a list to enable toggling.
        self.FEATURES.update({
            FEATURE_ALL_ON: False,
            FEATURE_ALL_OFF: False,
            FEATURE_PINGABLE: True,
            FEATURE_POLLABLE: True,
            FEATURE_NUMBER_OF_STEPS: 2,
            FEATURE_ALLOW_IN_SCENES: False,
            FEATURE_DETECTS_MOTION: False,
        })
        self.image_url_proxy = f"/api/v1/device_camera/{self.device_id}"
        self.image_update_interface = 5
        self.last_image = None

        self._http_protocol = "http"
        self._host = None
        self._port = None
        # self.MACHINE_STATUS_EXTRA_FIELDS["mode"] = ["idle", "streaming", "recording"]

    def toggle(self):
        if self.status_history[0].machine_status == SEVALUE_IDLE:
            return self.command(COMMAND_RECORD)
        elif self.status_history[0].machine_status == SEVALUE_RECORDING:
            return self.command(COMMAND_STOP)

    def turn_on(self, **kwargs):
        return self.command(COMMAND_RECORD, **kwargs)

    def turn_off(self, **kwargs):
        return self.command(COMMAND_STOP, **kwargs)

    # Everything below should be overridden.
    @property
    def request_auth(self):
        """ Auth for making web requests. """
        return self._request_auth

    @property
    def frame_interval(self):
        """ When creating an MJPEG stream, set the iterval to collect still images. """
        return 0.5

    def camera_image(self):
        """ Return an Image class representing the latest camera image. """
        raise NotImplementedError()

    @property
    def base_url(self):
        """ Get the base URL webcam endpoint."""
        if self._port is not None:
            return f"{self._http_protocol}://{self._host}:{self._port}"
        else:
            return f"{self._http_protocol}://{self._host}"

    @property
    def image_url(self):
        """ Single image (snapshot) url."""
        return None

    @property
    def audio_url(self):
        """ URL for the audio stream. """
        return None

    @property
    def has_motion_detection(self):
        return False

    @property
    def motion_detection(self):
        """Return the camera motion detection status."""
        return False

    @property
    def motion_detection(self):
        """Return the camera motion detection status."""
        return False

    def set_motion_detection(self, value):
        """
        Set value to either True of False. This may return a deferred, so call with
        "yield maybeDeferred(device.set_motion_detection(True)"

        :param value:
        :return:
        """
        pass

    @property
    def is_recording(self):
        """Return true if the device is recording."""
        return False

    @property
    def is_recording(self):
        """Return true if the device is recording."""
        return False

    @inlineCallbacks
    def get_camera_image(self):
        """
        Connect to the device and get a single image.

        :return: Image
        """
        print(f"get_camera_image about to get image from: {self.image_url}")
        image_results = yield self._Requests.request('get', self.image_url, auth=self.request_auth)
        print("get_camera_image: got an image: %s" % image_results['headers']['content-type'][0])
        image = Image(content_type=image_results['headers']['content-type'][0], image=image_results['content'])
        return image

    @inlineCallbacks
    def stream_mjpeg(self, request, **kwargs):
        """
        Returns a web/HTTP MJPEG stream by stitching together JPEG images.

        This collects the images, returns

        :param request: HTTP request.
        :param kwargs:
        :return:
        """
        interval = 0.500
        print("stream_mjpeg starting..")
        request.setHeader("Content-Type", "multipart/x-mixed-replace; boundary=--frameboundary")
        while True:
            start_time = time()
            print("stream_mjpeg: requesting image")
            image = yield self.get_camera_image()
            print("stream_mjpeg: have image.")
            duration = float(time() - start_time)

            print(f"stream_mjpeg: Duration of fetch: {duration}")
            self.write_to_mpeg_stream(request, image)
            # print(image_results['response'].history())
            # print(f"got image: {image_results['headers']['content-size'][0]} bytes")
            if duration < interval:
                yield sleep(interval - round(duration, 3))

    def write_to_mpeg_stream(self, request, image):
        """
        Takes an image instance and writes it to the HTTP request instance.
        """
        print("write_to_mpeg_stream: request: %s" % request)
        print("write_to_mpeg_stream: image: %s" % image)
        request.write(bytes(
            '--frameboundary\r\n'
            f'Content-Type: {image.content_type}\r\n'
            f'Content-Length: {len(image.content)}\r\n\r\n',
            'utf-8') + image.content + b'\r\n')


class VideoCamera(Camera):
    """
    Adds video streaming from the device.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PLATFORM = PLATFORM_VIDEO_CAMERA

    @property
    def video_url(self):
        """ The MJPEG URL """
        raise NotImplementedError()

class MjpegCamera(VideoCamera):
    """
    A camera capable of MPEG output and is accessible via a URL.
    """
    pass
