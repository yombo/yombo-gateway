# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Used to determine the type of file other raw data (as bytes) and attempt to determine it's
content type and charset.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.23.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
import io
import os.path
from PIL import Image as PILImage
from time import time

from twisted.internet.defer import inlineCallbacks, maybeDeferred


from yombo.classes.image import Image
from yombo.core.exceptions import YomboWarning
from yombo.utils import mime_type_from_buffer, read_file


class FileHelper(object):
    """Represent the file"""
    @property
    def content(self):
        """
        Return the raw data.

        :return:
        """
        return self.get()

    def __init__(self, created_at=None):
        """
        Init the image, doesn't really do much. Must call 'set' with the image.

        :param image:
        :param created_at:
        """
        self.created_at = created_at or time()
        self.content_type = None
        self.charset = None

        self._content = None

    @inlineCallbacks
    def set(self, content):
        """
        Set the content for the class. It can be bytes to represent the raw input, or it can be a string
        representing a file to load.

        :param content:
        :return:
        """
        if isinstance(content, bytes):  # we have a raw image:
            pass
        elif isinstance(content, str):  # we should have a file path:
            if os.path.exists(self.yombo_ini_path) is False:
                raise YomboWarning(f"String types must be a path/filename to an file to load.")
            image = yield read_file(content)
        else:
            raise YomboWarning("Unknown input type.")

        content_type = yield mime_type_from_buffer(content)

        self.content_type = content_type["content_type"]
        self.charset = content_type["charset"]
        self._content = content

    @inlineCallbacks
    def get(self):
        """
        Return the raw data.

        :return:
        """
        def get2(item):
            return item
        results = yield maybeDeferred(get2, self._content)
        return results
