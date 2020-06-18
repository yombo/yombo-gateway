"""
The ReadStream class uses non-blocking code to open and write to a file.

This class will keep the file open, so be sure to close this file when done!

**Usage**:

.. code-block:: python

   class MyModule(YomboModule):
       @inlineCallbacks
       def _start_(self):
           self.file = yield self._Files.save_stream(filename="myfile.txt")
           self.file.write("some more text....")

       @inlineCallbacks  # <----  This is required as it saves contents in a different thread.
       def _stop_(self):
           yield self.file.close()  # Tell save_stream to close the file. Very important!

If you want to open a file, write some data, and wait for it to finish saving before moving on:

.. code-block:: python

   # This needs @inlineCallbacks decorator for the function doing this.
   file_out = yield self._Files.save_stream(filename="myfile.txt", mode="a")  # open in append mode.
   file_out.write("Some data....")
   yield file_out.close()


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.23.0
   Created as FileWriter under the utilities directory.
.. versionadded:: 0.24.0
   Renamed from FileWriter and moved under the Files library.

:copyright: Copyright 2013-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/files/save_stream.html>`_
"""
# Import python libraries
import codecs
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import threads
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning


class SaveStream:
    """
    The file writer will open and keep a file open for writing.

    Typically used for log files.
    """
    def __init__(self, parent, filename: str, mode: Optional[str] = None, frequency: Optional[int] = None):
        """
        Generate a new File Writer instance.

        The params defined refer to kwargs and become class variables.

        The mode can be specified as well, the default mode is "a" for "append".  You can use 2 write modes:
        w - create a new file
        a - append file

        :param parent: A reference to the Files library.
        :param filename: The full path to the file to stream from.
        :param mode: The full path to the file to stream from.
        :param frequency: How often the file should be checked for data to write, in seconds.
        """
        self.close_when_done = False

        self._Parent = parent
        self.filename = filename
        mode = mode or "a"
        self.frequency = frequency or 1

        self.write_queue = []

        try:
            self.fp_out = codecs.open(self.filename, mode)
        except IOError as e:
            (errno, strerror) = e.args
            raise YomboWarning(f"SaveStream could not open file for writing ({self.filename}). Reason: {strerror}",
                                 435121, "__init__", "SaveStream")

        self.save_running = False
        self.save_loop = LoopingCall(self.save)
        self.save_loop.start(frequency)

    @inlineCallbacks
    def close(self):
        """
        Call to close the file from being monitored.
        """
        if self.save_loop.running is True:
            self.save_loop.stop()
        yield self.save(close_when_done=True)

    def write(self, output):
        """
        Write something to the file.
        """
        self.write_queue.append(output)

    @inlineCallbacks
    def save(self, close_when_done: Optional[bool] = None):
        if close_when_done is True:
            self.close_when_done = True
        if self.save_running:
            return
        self.save_running = True
        if len(self.write_queue) > 0:

            save_data = ""
            while len(self.write_queue) > 0:
                save_data += self.write_queue.pop(0)
            yield threads.deferToThread(self.do_write, save_data)
        if self.close_when_done is True:
            if self.fp_out is not None:
                self.fp_out.close()
                self.fp_out = None
        self.save_running = False

    def do_write(self, output):
        """
        Does the actual writing. This is called in a separate thread.

        :param output:
        :return:
        """
        if self.fp_out is not None:
            self.fp_out.write(output)
