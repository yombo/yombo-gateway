"""
Various camera type devices.
"""
from time import time

from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboWarning
from yombo.constants.features import (FEATURE_NUMBER_OF_STEPS, FEATURE_ALL_ON, FEATURE_ALL_OFF, FEATURE_PINGABLE,
                                      FEATURE_POLLABLE, FEATURE_ALLOW_IN_SCENES, FEATURE_DETECTS_MOTION)
from yombo.constants.commands import COMMAND_STOP, COMMAND_RECORD, COMMAND_ON, COMMAND_OFF
from yombo.constants.platforms import PLATFORM_BASE_CAMERA, PLATFORM_CAMERA, PLATFORM_VIDEO_CAMERA
from yombo.constants.state_extra import SEVALUE_IDLE, SEVALUE_RECORDING
from yombo.core.log import get_logger
from yombo.lib.devices._device import Device
from yombo.utils import sleep
from yombo.utils.ffmpeg.getimage import GetImage
from yombo.utils.ffmpeg.mjpeg import MJPEG
from yombo.utils.ffmpeg.h264 import H264
from yombo.classes.image import Image

DEFAULT_CONTENT_TYPE = "image/jpeg"

CONFIG_MJPEG_URL = "mjpeg_url"
CONFIG_STILL_IMAGE_URL = "still_image_url"
logger = get_logger("modules.android_ipwebcam.device")



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
        self.image_url_proxy = f"/api/v1/camera/{self.device_id}/snap"
        self.image_update_interface = 5
        self.last_image = None

        self._protocol = "http"
        self._host = None
        self._port = None
        self._username = None
        self._password = None
        self._request_auth = None

        # self.MACHINE_STATE_EXTRA_FIELDS["mode"] = ["idle", "streaming", "recording"]

    def toggle(self):
        if self.status_history[0].machine_state == SEVALUE_IDLE:
            return self.command(COMMAND_RECORD)
        elif self.status_history[0].machine_state == SEVALUE_RECORDING:
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
            return f"{self._protocol}://{self._host}:{self._port}"
        else:
            return f"{self._protocol}://{self._host}"

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

    @inlineCallbacks
    def get_camera_image(self):
        """
        Connect to the device and get a single image.

        :return: Image
        """
        if self.image_url is not None:
            # print(f"get_camera_image about to get image from: {self.image_url}")
            image_results = yield self._Requests.request('get', self.image_url, auth=self.request_auth)
            # print("get_camera_image: got an image: %s" % image_results['headers']['content-type'][0])
            image = Image(content_type=image_results['headers']['content-type'][0], image=image_results['content'])
            return image
        else:
            raise YomboWarning("00Unable to fetch image URL, image_url is not defined.")

    @inlineCallbacks
    def stream_http_mjpeg_video(self, image_callback, framerate=None, quality=None, **kwargs):
        """
        Collects images from the remove device as individual images, and returns them to the image_callback
        function.

        :param image_callback: The callback to send images to.
        :param framerate: How many frames per second to try to return.
        :param quality: The quality of the jpg, ranging from 1 to 32, 1 being best. Suggested: 2-5.
        :param kwargs:
        :return:
        """
        interval = 0.200
        # print("stream_mjpeg starting..")
        while True:
            start_time = time()
            print("stream_mjpeg: requesting image")
            image = yield self.get_camera_image()
            print("stream_mjpeg: have image.")
            duration = float(time() - start_time)

            print(f"stream_mjpeg: Duration of fetch: {duration}")
            image_callback(image)
            # print(image_results['response'].history())
            # print(f"got image: {image_results['headers']['content-size'][0]} bytes")
            if duration < interval:
                yield sleep(interval - round(duration, 3))

    def write_to_http_mjpeg_stream(self, request, image):
        """
        Takes an image instance and writes it to the HTTP request instance.
        """
        # print("write_to_mpeg_stream: request: %s" % request)
        # print("write_to_mpeg_stream: image: %s" % image)
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
        self._mjpeg_streams = {}  # Tracking active streams

    @property
    def video_url(self):
        """ The video URL to pull from."""
        raise None

    @inlineCallbacks
    def get_camera_image(self):
        # print(f"vC: get_camera iamge, {self.image_url}, {self.video_url}")
        if self.image_url is not None:
            # print(f"vC: From parent")
            results = yield super().get_camera_image()
            return results
        elif self.video_url is not None:
            # print(f"vC: From video")
            image_getter = GetImage(self, self.video_url)
            image = yield image_getter.get_image()
            return image
        else:
            raise YomboWarning("11Unable to fetch image URL, image_url or video_url is not defined.")

    @inlineCallbacks
    def stream_http_mjpeg_video(self, image_callback, framerate=None, quality=None, **kwargs):
        """
        Returns a web/HTTP MJPEG stream by stitching together JPEG images.

        We try to connect to the video stream, collect JPEG images, and then stream them using MJPEG. Seems so 1990s.

        :param image_callback: The callback to send images to.
        :param framerate: How many frames per second to try to return.
        :param quality: The quality of the jpg, ranging from 1 to 32, 1 being best. Suggested: 2-5.
        :param kwargs:
        :return:
        """
        print("video camera: stream_mjpeg starting..")
        mpeg_streamer = MJPEG(self, self.video_url, framerate=framerate, quality=quality)
        images_results = yield mpeg_streamer.get_images(images_callback=image_callback)
        return images_results

    @inlineCallbacks
    def stream_http_264_video(self, stream_callback, framerate=None, video_bitrate=None, video_profile=None,
                              audio_bitrate=None,
                              **kwargs):
        """
        Returns a video stream that is 264 encoded.

        We try to connect to the video stream, collect JPEG images, and then stream them using MJPEG. Seems so 1990s.

        :param stream_callback: The callback to send video data to.
        :param framerate: How many frames per second to try to return.
        :param video_bitrate: The max bitrate in kilobtyes for video
        :param audio_bitrate: The audio bitrate.
        :param kwargs:
        :return:
        """

        print("video camera: stream_http_264_video starting..")
        mpeg_streamer = H264(self, self.video_url, framerate=framerate,
                             video_bitrate=video_bitrate, video_profile=video_profile,
                             audio_bitrate=audio_bitrate)
        print("video camera: stream_http_264_video starting..")
        images_results = yield mpeg_streamer.get_stream(stream_callback=stream_callback)
        return images_results


class MjpegCamera(VideoCamera):
    """
    A camera capable of MPEG output and is accessible via a URL.
    """
    pass
