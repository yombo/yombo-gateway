# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Used to load and convert images from one type to another. Typically used to
generate thumbs, load images from disk/buffer, auto detect image type, etc.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/classes/imagecontainer.html>`_
"""
import io
from PIL import Image as PILImage
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union

from twisted.internet import reactor, threads
from twisted.internet.defer import inlineCallbacks

from yombo.classes.filecontainer import FileContainer
from yombo.core.exceptions import YomboWarning

IMAGE_BMP = "image/bmp"
IMAGE_GIF = "image/gif"
IMAGE_JPEG = "image/jpeg"
IMAGE_PNG = "image/png"

PIL_MAP = {
    IMAGE_BMP: "bmp",
    IMAGE_GIF: "gif",
    IMAGE_JPEG: "jpeg",
    IMAGE_PNG: "png",
}

TYPE_MAP = {
    "bmp": IMAGE_BMP,
    "gif": IMAGE_GIF,
    "jpeg": IMAGE_JPEG,
    "png": IMAGE_PNG,
}


class ImageContainer(FileContainer):
    """
    Load an image from either file or from variable.

    If the mime_type or charset is not provided, it will eventually be determined. If you
    want it to be determined right away, just simply create an empty version of this class
    and then use the .set() method.
    """
    def __init__(self, content: Optional[Union[bytes, str]] = None, mime_type: Optional[str] = None,
                 charset: Optional[str] = None, created_at: Optional[Union[int, float]] = None) -> None:
        """
        Setup the image contents along with it's meta data.

        :param content:
        :param mime_type:
        :param charset:
        :param created_at:
        """
        self.image_pil = None  # Image stored in PIL class.
        self.image_out = None  # Cached output
        self.image_out_mime_type = None  # Mime type of the output image.
        super().__init__(content, mime_type, charset, created_at)

    @inlineCallbacks
    def get(self, image_type=None, **kwargs) -> bytes:
        """
        Return the image as a JPG, regardless of input. Set image_type argument to the desired image type.

        :param image_type: Default is jpeg. Accepted: bmp, gif, jpeg, png or the full mime type
          versions such as: image/jpeg
        :param kwargs: Additional options to send the the PIL module.
        :return:
        """
        if self.mime_type.startswith("image") is False:
            return self.content

        results = yield self.generate_image(self.image_pil, image_type, **kwargs)
        return results

    @inlineCallbacks
    def set(self, content: Optional[Union[bytes, str]] = None, mime_type: Optional[str] = None,
            charset: Optional[str] = None, created_at: Optional[Union[int, float]] = None) -> None:
        """
        Load the 'image'. Content can  can be bytes to represent the raw image, it will automatically be detected.
        The 'image' can also be a string representing a file to load.

        :param content: Contents to store.
        :param mime_type:
        :param charset:
        :param created_at:
        """
        yield super().set(content, mime_type, charset, created_at)

        if self.mime_type.startswith("image"):
            self.image_pil = PILImage.open(io.BytesIO(self.content))
        else:
            raise YomboWarning("ImageContainer received non-image content or mime_type is wrong. Use"
                               " FileContainer instead.")

    def validate_image_type(self, image_type: str) -> str:
        """Internal function to validate the image_type."""
        if image_type is None:
            image_type = self.mime_type
        image_type = image_type.lower()
        if image_type in PIL_MAP:
            return PIL_MAP[image_type]
        if image_type in TYPE_MAP:
            return image_type
        raise YomboWarning(f"Unknown image_type to output to: {image_type}")

    @inlineCallbacks
    def thumbnail(self, size: Optional[Union[Tuple[int, int], int]] = None, image_type: str = None,
                  quality: Optional[int] = None, **kwargs) -> bytes:
        """
        Create a thumbnail version of the image.

        :param size: A int for both X/Y size, or a tuple of ints representing x,y size of the image.
        :param quality:
        :return:
        """
        if self.mime_type.startswith("image") is False:
            raise YomboWarning("Cannot create thumb from non-image type.")

        if size is None:
            size = (300, 300)
        elif isinstance(size, int):
            size = (size, size)
        elif isinstance(size, tuple or isinstance(size, list)):
            size = (size[0], size[1])

        image_type = self.validate_image_type(image_type)

        if "quality" is None:
            kwargs["quality"] = 50
        else:
            kwargs["quality"] = quality
        thumb_pil = self.image_pil.copy()
        thumb_pil.thumbnail(size, PILImage.BICUBIC)
        results = yield self.generate_image(thumb_pil, image_type, **kwargs)
        return results

    @inlineCallbacks
    def generate_image(self, image_source, image_type: Optional[str] = None, **kwargs) -> bytes:
        """
        Internal function to convert PIL image to raw variable.

        :param image_type:
        :return:
        """
        image_type = self.validate_image_type(image_type)
        @inlineCallbacks
        def _create_image(image2, image_type2, **kwargs2):
            raw_image = None
            with io.BytesIO() as output:
                image2.save(output, PIL_MAP[image_type2])
                contents = output.getvalue()
            new_image = ImageContainer()
            yield new_image.set(raw_image)
            return new_image

        image_source_temp = image_source.copy()
        results = yield threads.deferToThread(_create_image, image_source_temp, image_type, **kwargs)
        return results
