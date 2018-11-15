# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Use ffmpeg to capture individual images from a video stream only to reassemble them into a MJPEG video
with the intended target HTTP.

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


class MJPEG(YBOFFmpeg):
    """
    Returns series of images to create an Motion JPEG (MJPEG) video.
    """
    jpeg_start_of_image = soi = b'\xff\xd8\xff\xe0'
    jpeg_jfif_id = b'JFIF\x00'
    jpeg_diffie_quant_marker = b'\xff\xdb'
    jpeg_diffie_huffman_marker = b'\xff\xc4'
    jpeg_frame_marker = b'\xff\xc0'
    jpeg_scan_marker = b'\xff\xda'
    jpeg_end_of_image = eoi = b'\xff\xd9'

    def __init__(self, parent, video_url, framerate=None, quality=None):
        """
        Setup the video capture class.

        :param video_url: File path or URL of the video.
        :param framerate: How many frames per second to try to return.
        :param quality: The quality of the jpg, ranging from 1 to 32, 1 being best. Suggested: 2-5.
        :param parent: Library or module reference.
        """
        super().__init__(parent)
        self.video_url = video_url

        if isinstance(framerate, str):
            framerate = int(framerate)
        if framerate is None or isinstance(framerate, int) is False or framerate < 1 or framerate > 25:
            framerate = 8
        self.framerate = framerate

        if isinstance(quality, str):
            quality = int(quality)
        if quality is None or isinstance(quality, int) is False or quality < 1 or quality > 32:
            quality = 3
        self.quality = quality

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
    def get_images(self, images_callback=None, callback_args=None, results_final_callback=None):
        """
        Starts the connection to the video feed, and then calls "images_callback" with every new image received.

        :param images_callback: The callback to send images to.
        :param callback_args: Arguments to send the to images_callback.
        :param results_final_callback: Called whenever the connection ends, or requested to end.
        :return:
        """
        if callable(images_callback) is False:
            raise YomboWarning("images_callback must be a callable.")
        if self._already_streaming is True:
            raise YomboWarning("Already streaming images.")
        self._already_streaming = True

        #-r 1 -frames:v 50 -y -f image2pipe -
        args = [
            "-v",
            "error",
            "-r",
            str(self.framerate),
            "-qscale:v",
            str(self.quality),
        ]

        output_buffer = b""

        def slice_image(img):
            """Find the EOI marker assuming we are at the beginning of a jpeg file."""
            dqm_loc = img.find(self.jpeg_diffie_quant_marker)
            dhm_loc = img.find(self.jpeg_diffie_huffman_marker, dqm_loc)
            frm_loc = img.find(self.jpeg_frame_marker, dhm_loc)
            smk_loc = img.find(self.jpeg_scan_marker, frm_loc)
            eoi_loc = img.find(self.jpeg_end_of_image, smk_loc)
            return img[:eoi_loc + 2]

        def collect_results(output):
            nonlocal output_buffer
            output_buffer += output

            check_again = True
            while check_again:
                have_soi = False
                have_eoi = False
                if have_soi is False and self.soi in output_buffer:
                    have_soi = True
                if have_eoi is False and self.eoi in output_buffer:
                    have_eoi = True
                # print(f"Have_soi: {have_soi}. Have eoi: {have_eoi}")

                if have_soi and have_eoi:  # looks like we have one already.
                    img_loc = output_buffer.find(self.soi)
                    img = output_buffer[img_loc:]
                    if self.jpeg_jfif_id not in img[:11]:
                        # Doesn't appear to be a jpeg, drop data and continue.
                        output_buffer = output_buffer[img_loc + 1:]
                        return
                    image_raw = slice_image(img)
                    # print(f"image size: {len(image_raw)}")
                    output_buffer = output_buffer[img_loc + len(image_raw):]
                    image = Image("image/jpeg", image_raw)
                    images_callback(image, callback_args)
                else:
                    check_again = False

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

        image_deferred = Deferred()
        self.stdout_callback = collect_results
        self.closed_callback = collect_results_final
        yield self.open(self.video_url, commands=args, output="-f image2pipe -", auto_reconnect=False)
        images_results = yield image_deferred
        return images_results
