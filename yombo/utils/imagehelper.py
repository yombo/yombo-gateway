# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Used to load and convert images from one type to another. Typically used to
generate thumbs, load images from disk/buffer, auto detect image type, etc.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
import io
import os.path
from PIL import Image as PILImage
from time import time

from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, Deferred

from yombo.classes.image import Image
from yombo.core.exceptions import YomboWarning
from yombo.utils import mime_type_from_buffer, read_file
from yombo.utils.filehelper import FileHelper

IMAGE_BMP = "image/bmp"
IMAGE_GIF = "image/gif"
IMAGE_JPEG = "image/jpeg"
IMAGE_PNG = "image/png"

PIL_MAP = {
    IMAGE_BMP: "BMP",
    IMAGE_GIF: "GIF",
    IMAGE_JPEG: "JPEG",
    IMAGE_PNG: "PNG",
}

TYPE_MAP = {
    "bmp": "image/bmp",
    "jpeg": "image/JPEG",
    "jpg": "image/JPEG",
    "png": "image/png",
}


class ImageHelper(FileHelper):
    """
    Load an image from either file or from variable.
    """
    @inlineCallbacks
    def set(self, image):
        """
        Load the the 'image' can be bytes to represent the raw image, it will automatically be detected.
        The 'image' can also be a string representing a file to load.

        :param image:
        :return:
        """
        yield super().set(image)

        if self.content_type.startswith("image"):
            self.image_pil = PILImage.open(io.BytesIO(image))

    @inlineCallbacks
    def get(self, image_type=None, **kwargs):
        """
        Return the image a JPG.

        :return:
        """
        if self.content_type.startswith("image") is False:
            results = yield super().get()
            return results

        if image_type is None:
            image_type = self.content_type
        else:
            image_type = image_type.lower()
            if image_type not in TYPE_MAP:
                raise YomboWarning(f"Unknown image_type to output to: {iamge_type}")

        results = yield self.get_contents(self.image_pil, image_type)
        return results

    @inlineCallbacks
    def thumbnail(self, size=None, image_type=None, **kwargs):
        """
        Create a thumbnail version of the image.

        :param size:
        :param quality:
        :return:
        """
        if self.content_type.startswith("image") is False:
            raise YomboWarning("Cannot create thumb from non-image type.")

        if size is None:
            size = (300, 300)
        else:
            size = (size, size)
        if image_type is None:
            image_type = self.content_type
        else:
            image_type = image_type.lower()
            if image_type not in TYPE_MAP:
                raise YomboWarning(f"Unknown image_type to output to: {iamge_type}")

        if "quality" not in kwargs:
            kwargs["quality"] = 50
        thumb_pil = self.image_pil.copy()
        thumb_pil.thumbnail(size, PILImage.BICUBIC)
        results = yield self.get_contents(thumb_pil, image_type)
        return results

    @inlineCallbacks
    def get_contents(self, image, image_type, **kwargs):
        """
        Internal function to convert PIL image to raw variable.

        :param image_type:
        :return:
        """
        def _get_contents(image2, image_type2, **kwargs2):
            contents = None
            with io.BytesIO() as output:
                image2.save(output, PIL_MAP[image_type2])
                contents = output.getvalue()
            return Image(self.content_type, contents)

        tmp = image.copy()
        results = yield threads.deferToThread(_get_contents, tmp, image_type, **kwargs)
        return results
