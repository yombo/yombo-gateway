# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Use ffmpeg to convert any supported video to h.264 and attempt to create a streamable video.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""

from twisted.internet.defer import inlineCallbacks, Deferred

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.classes.image import Image

from .ffmpeg import YBOFFmpeg

logger = get_logger("utils.ffmpeg.mjpeg")

IMAGE_JPEG = 'jpeg'
IMAGE_PNG = 'png'


class H264(YBOFFmpeg):
    """
    Use FFMPEG to create h.264 video out.
    """
    def __init__(self, parent, video_url, framerate=None, video_bitrate=None, video_profile=None, video_preset=None,
                 audio_bitrate=None, audio_type=None,
                 ):
        """
        Setup the video capture class.

        :param video_url: File path or URL of the video.
        :param framerate: How many frames per second to try to return.
        :param video_bitrate: Bitrate of the video, in kilobytes
        :param audio_bitrate: Bitrate of the audio, in kilobytes
        :param audio_type: Type of audio, default to aac.
        :param audio_type: Video encoding profile.
        :param parent: Library or module reference.
        """
        super().__init__(parent)
        self.video_url = video_url

        if isinstance(framerate, str):
            framerate = int(framerate)
        if framerate is None or isinstance(framerate, int) is False or framerate < 1 or framerate > 25:
            framerate = 8
        self.framerate = framerate

        if isinstance(video_bitrate, str):
            video_bitrate = int(video_bitrate)
        if video_bitrate is None or isinstance(video_bitrate, int) is False or video_bitrate < 100 or video_bitrate > 10000:
            video_bitrate = 768
        self.video_bitrate = video_bitrate

        if isinstance(video_profile, str) is False:
            video_profile = "baseline"
        else:
            if video_profile not in ("baseline", "main", "high"):
                video_profile = "baseline"
        self.video_profile = video_profile

        if isinstance(video_preset, str) is False:
            video_preset = "superfast"
        else:
            if video_preset not in ("ultrafast", "superfast", "veryfast", "faster", "faster", "medium", "slow",
                                    "slower", "veryslow"):
                video_preset = "superfast"
        self.video_preset = video_preset

        if isinstance(audio_bitrate, str):
            audio_bitrate = int(video_bitrate)
        if audio_bitrate is None or isinstance(audio_bitrate, int) is False or audio_bitrate < 16 or audio_bitrate > 256:
            audio_bitrate = 128
        self.audio_bitrate = audio_bitrate

        if isinstance(audio_bitrate, str) is False:
            audio_type = "aac"
        else:
            if audio_type not in ("aac"):
                audio_type = "aac"
        self.audio_type = audio_type

        self.detected_video_type = None
        self._already_streaming = False

        try:
            self.ffprobe_bin = self._Parent._Atoms.get("ffprobe_bin")

        except KeyError:
            self.ffprobe_bin = None
            raise YomboWarning(
                "ffprobe was not found, check that ffmpeg is installed and accessible from your path environment variable.")

        # reactor.callLater(1, self._detect_video_type)

    @inlineCallbacks
    def get_stream(self, stream_callback=None, callback_args=None, results_final_callback=None):
        """
        Starts the connection to the video feed, and then calls "results_callback" with every new image received.

        :param results_callback: The callback to send images to.
        :param callback_args: Arguments to send the to results_callback.
        :param results_final_callback: Called whenever the connection ends, or requested to end.
        :return:
        """
        if callable(stream_callback) is False:
            raise YomboWarning("results_callback must be a callable.")
        if self._already_streaming is True:
            raise YomboWarning("Already streaming images.")
        self._already_streaming = True

        args = [
            "-v",
            "error",
            "-c:v",
            "libx264",
            "-b:v",
            f"{self.video_bitrate}k",
            "-profile:v",
            self.video_profile,
            "-preset",
            self.video_preset,
            "-level",
            "3.0",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            self.audio_type,
            "-ac",
            "2",
            "-b:a",
            f"{self.audio_bitrate}k",
            "-movflags",
            "faststart",
        ]

        stream_deferred = Deferred()
        self.stdout_callback = stream_callback
        yield self.open(self.video_url, commands=args, output="-f mpegts -", auto_reconnect=False)
        images_results = yield stream_deferred
        return images_results
