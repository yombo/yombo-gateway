#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
The ReadStream class should be called through the Files Library and is not intended to be called
be directly.

ReadStream class will monitor the file for new content and send any new content of text to the
function defined within the callback variable.

This class will keep the file open, so be sure to close this file when done using `yield reference.close()`

**See logreader module for full working example.**

**Usage**:

.. code-block:: python

   class MyModule(YomboModule):
       @inlineCallbacks
       def _start_(self):
           self.file = yield self._Files.read_stream(filename="myfile.txt", callback=self.my_new_content))

       def my_new_content(self, the_content):
           logger.info("got new content: {the_content}", the_content=the_content)

       @inlineCallbacks
       def _stop_(self):
           yield self.file.close()  # Tell ReadStream to close the file. Very important!

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.23.0
   Created as FileReader under the utilities directory.
.. versionadded:: 0.24.0
   Renamed from FileReader and moved under the Files library.

:copyright: Copyright 2013-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/files/read_stream.html>`_
"""
# Import python libraries
import codecs
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning


class ReadStream:
    """
    The file reader class will monitor a file for changes. If any new content
    is found, it will return the new content to the method passed in.

    Typically used to monitor log files.
    """
    def __init__(self, parent, filename: str, callback: Callable, file_id_hash: str,
                 start_location: Optional[int] = None, encoding: Optional[str] = None,
                 frequency: Optional[int] = None):
        """
        Generate a new File Reader instance. 

        The params defined refer to kwargs and become class variables.

        :param parent: A reference to the Files library.
        :param filename: The full path to the file to stream from.
        :param callback: Callback to call when new data is available.
        :param start_location: If positive, will attempt to skip to this location. If length exceeds file size,
            will read from the start.
        :param encoding: If using text, specify the encoding - default: utf-8
        :param frequency: How often, in seconds, to check for new content. Default: 1
        """
        self.fp_in = None
        self.check_file_for_content_loop = None

        self._Parent = parent
        self.filename = filename
        self.callback = callback
        self.file_id_hash = file_id_hash
        self.start_location = start_location
        self.encoding = encoding or "utf-8"
        self.frequency = frequency or 1
        self.check_file_for_content_loop = LoopingCall(self.check_file_for_content)
        reactor.callLater(0.001, self.complete_init)

    @inlineCallbacks
    def complete_init(self):
        try:
            self.fp_in = codecs.open(self.filename, encoding=self.encoding)
            self.fp_in.seek(self.start_location)
        except IOError as e:
            (errno, strerror) = e.args
            raise YomboWarning(f"ReadStream could not open file for reading. Reason: {strerror}",
                                 265743, "complete_init", "ReadStream")
        else:
            self.start()

    def start(self):
        """
        Start monitoring the file.

        :return:
        """
        self.check_file_for_content_loop.start(self.frequency)

    def pause(self):
        """
        Pause monitoring the file.

        :return:
        """
        if self.check_file_for_content_loop is not None:
            self.check_file_for_content_loop.stop()

    @inlineCallbacks
    def close(self):
        """
        Call to close the file from being monitored.
        """
        self.pause()
        if self.fp_in is not None:
            self.fp_in.close()

    def check_file_for_content(self):
        """
        Watch for file input.
        fp -- file-like object with tell() and readlines() support.
        """
        for line in self.fp_in.readlines():
            self.callback(line)
        location = self.fp_in.tell()  # get current location
        self._Parent.read_stream_location(self.file_id_hash, location)
