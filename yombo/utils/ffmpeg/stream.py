# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Use ffmpeg to connect to remote

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.utils import getProcessOutput

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

from .ffmpeg import YBOFFmpeg

logger = get_logger("utils.ffmpeg.image")

IMAGE_JPEG = 'jpeg'
IMAGE_PNG = 'png'


class Stream(YBOFFmpeg):
    """
    Stream video from various source to various types.
    """
    def __init__(self, parent, video_url, output_format=None, quality=None):
        """
        Setup the sensor. The quality setting will only be used for streams that are not MJPEG, these will
        be directly pulled from the video stream unmodified for best results.

        :param video_url: File path or URL of the video.
        :param quality: The quality of the jpg, ranging from 1 to 32, 1 being best. Suggested: 2-5.

        :param parent: Library or module reference.
        """
        super().__init__(parent)
        self.video_url = video_url
        self.output_format = output_format or IMAGE_JPEG
        if self.output_format not in (IMAGE_JPEG, IMAGE_PNG):
            raise YomboWarning("output_format must be 'jpeg' or 'png'.")
        self.quality = quality

        self.detected_type = None
        self._already_streaming = False

        try:
            self.ffprobe_bin = self._Parent._Atoms.get("ffprobe_bin")
        except KeyError:
            self.ffprobe_bin = None
            raise YomboWarning(
                "ffprobe was not found, check that ffmpeg is installed and accessible from your path environment variable.")

        # reactor.callLater(1, self._detect_video_type)

    @inlineCallbacks
    def stream_mpeg(self, results_callback=None):
        """
        Capture an image from the video stream, results will be the im

        :param results_callback: If results_callback is a function, results will be streamed to it as they are received.
        :param results_final_callback: If results_callback is set, this must be set and will be called when finished.
        :return:
        """
        if self.detected_type is None:
            yield self._detect_video_type()

        streaming = False
        if callable(results_callback) is True and callable(results_final_callback) is False:
            raise YomboWarning("If results_callback is a callable, results_final_callback must be callable.")
        if callable(results_callback) is True and callable(results_final_callback) is True:
            if self._already_streaming is True:
                raise YomboWarning("Already streaming an image.")
            self._already_streaming = True
            streaming = True

        if self.detected_type == "mjpeg":  # we can capture a jpeg right from the stream, no changes.
            args = [
                "-v",
                "error",
                "-codec:v",
                "copy",
                "-frames:v",
                "1",
            ]
            if self.output_format == IMAGE_JPEG:
                args.extend(("-bsf:v", "mjpeg2jpeg"))
            else:
                args.extend(("-c:v", "png"))
        else:
            args = [
                "-v",
                "error",
                "-an",
                "-frames:v",
                "1",
                "-c:v",
                self.output_format,
            ]

        output_buffer = b""

        def collect_results(output):
            nonlocal output_buffer
            output_buffer += output

        def collect_results_final(*args, **kargs):
            """
            Calls the stream deferred so requester can finish.

            :param args:
            :param kargs:
            :return:
            """
            nonlocal image_deferred
            nonlocal output_buffer
            try:
                image_deferred.callback(output_buffer)
            except Exception as e:
                print("collect_results_final Exception:")
                print(e)

        if streaming is True:  # Don't autoreconnect, end of image...is end of image.
            self.stdout_callback = results_callback
            self.closed_callback = results_final_callback
            results = yield self.open(self.video_url, commands=args, output="-f image2pipe -", auto_reconnect=False)
        else:
            image_deferred = Deferred()
            self.stdout_callback = collect_results
            self.closed_callback = collect_results_final
            results = yield self.open(self.video_url, commands=args, output="-f image2pipe -", auto_reconnect=False)
            image = yield image_deferred
            return image
