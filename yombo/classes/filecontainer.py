"""
Used to store file contents. Once contents have been set, this class will try to automatically determine
the type contents and set the mime_type and charset attributes.

If mime_type and charset is needed immediately after creating an instance, us the "set" method instead
of setting the content when instantiating the object due to not being able to yield on __init__'s.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.23.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/classes/filecontainer.html>`_
"""
import os.path
from time import time
from typing import Optional, Union

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred

from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning


class FileContainer(Entity):
    """
    Represents a single file along with it's mime_type and charset.

    If the mime_type or charset is not provided, it will eventually be determined. If you
    want it to be determined right away, just simply create an empty version of this class
    and then use the .set() method.
    """

    def __init__(self, content: Optional[Union[bytes, str]] = None, mime_type: Optional[str] = None,
                 charset: Optional[str] = None, created_at: Optional[Union[int, float]] = None) -> None:
        """
        Setup the file contents along with it's meta data. Incoming content will always be stored as the content,
        unlike

        :param content:
        :param mime_type:
        :param charset:
        :param created_at:
        """
        super().__init__(None)
        self.content = content  # The raw content.
        self.mime_type = mime_type  # Mime type info about this content.
        self.charset = charset  # Charset information
        if self.content is not None and (mime_type is None or charset is None):
            reactor.callLater(0.0001, self.determine_type, mime_type, charset)
        self.created_at = created_at or time()

    @inlineCallbacks
    def get(self):
        """
        Return the raw data.

        This returns a deferred to keep it consistent with downstream classes.

        :return:
        """
        def get2(item):
            return item
        results = yield maybeDeferred(get2, self.content)
        return results

    @inlineCallbacks
    def set(self, content: Union[bytes, str], mime_type: Optional[str] = None,
            charset: Optional[str] = None, created_at: Optional[Union[int, float]] = None) -> None:
        """
        Set the content for the class. The content can accept two input types:
          * str - If a string, it's assumed the content is a pathname to read and load into memory.
          * bytes - Store contents directly into memory without reading any files.

        :param content: Str filename to read, or bytes to store.
        :param mime_type:
        :param charset:
        :param created_at:
        """
        if isinstance(content, bytes):  # we have a raw image:
            pass
        elif isinstance(content, str):  # we should have a file path:
            if os.path.exists(self.yombo_toml_path) is False:
                raise YomboWarning(f"String types must be a path/filename to an file to load.")
            content = yield self._Files.read(content)
        else:
            raise YomboWarning("Unknown input type.")

        if mime_type is None or charset is None:
            meta = yield self._Files.mime_type_from_buffer(content)
        self.content = content
        self.mime_type = mime_type or meta["mime_type"]
        self.charset = charset or meta["charset"]
        self.created_at = created_at or time()

    @inlineCallbacks
    def determine_type(self, mime_type: Optional[str] = None, charset: Optional[str] = None):
        """
        Attempts to determine the mime_type and charset based off the content.

        :return:
        """
        if mime_type is None or charset is None:
            meta = yield self._File.mime_type_from_buffer(self.content)
        self.mime_type = mime_type or meta["mime_type"]
        self.charset = charset or meta["charset"]
