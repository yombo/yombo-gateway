#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
The FileWriter class uses non-blocking code to open and write to a file.
This class will keep the file open, so be sure to close this file when done!

**Usage**:

.. code-block:: python

   from yombo.utils.filewriter import FileWriter  # load at the top of the file.
  
   class MyModule(YomboModule):
   # don't forget "def init(self)"

   def start(self):
       self.file = FileWriter(filename="myfile.txt")
       self.file.write("some more text....")

   @inlineCallbacks  # <----  This is required as it saves contents in a different thread.
   def stop(self):
       yield self.file.close_while_waiting()  # Tell FileWriter to close the file. Very important!

If you want to open a file, write some data, and wait for it to finish saving before moving on:

.. code-block:: python

   from yombo.utils.filewriter import FileWriter  # load at the top of the file.

   # This needs @inlineCallbacks decorator for the function doing this.
   file_out = FileWriter(filename="myfile.txt", mode="a")  # open in append mode.
   file_out.write("Some data....")
   yield file_out.close_while_waiting()


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.23.0

:copyright: Copyright 2013-2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import codecs
import ntpath
import os

# Import twisted libraries
from twisted.internet import threads
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks
from twisted.internet.reactor import callLater

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("utils.filewriter")


class FileWriter:
    """
    The file writer will open and keep a file open for writing.

    Typically used for log files.
    """
    def __init__(self, filename, **kwargs):
        """
        Generate a new File Writer instance.

        The params defined refer to kwargs and become class variables.

        The mode can be specified as well, the default mode is "a" for "append".  You can use 2 write modes:
        w - create a new file
        a - append file

        :param filename: **Required.** The path and file to monitor.
        :type filename: string
        :param mode: Which mode to open the file: w - create new file, a - append
        :param fileid: Assign a unique file id. Used if the filename may change
            in the future, but you want to persist tracking if the filename changes.
            defaults to filename is not supplied.
        :type fileid: string
        :param make_if_missing: If true, will create an empty file if file doesn't
            already exist.  Default: True
        :type make_if_missing: bool
        :param frequency: How often this filewriter should check for data to write, in seconds. If not written to often, set to high.
        """
        if filename is None or filename == "":
            raise YomboWarning("FileWriter requires a file name to write to.", 125473, "__init__", "FileWriter")
        if filename.startswith("/") is False:
            filename = f"./{filename}"
        self.filename = filename

        self.fileid = kwargs.get("fileid", self.filename)
        self.make_if_missing = kwargs.get("make_if_missing", True)

        if "mode" in kwargs:
            mode = kwargs["mode"]
            if mode not in ("a", "w"):
                raise YomboWarning(f"Write must be one of: a, w", 628312, "__init__", "FileWriter")
        else:
            mode = "a"

        self.close_when_done = False  # used when saving files and if it should close when it's done...
        self.write_queue = []
        fileparts = ntpath.split(self.filename)
        try:
            if os.path.exists(fileparts[0]) is False:
                if self.make_if_missing is False:
                    raise YomboWarning("File does not exist, told not to create one.",
                                         121639, "__init__", "FileWriter")
                else:
                    os.makedirs(fileparts[0])

            logger.debug("{fileid}: About to open file: {mode} - {filename}",
                        fileid=self.fileid, mode=mode, filename=self.filename)
            self.fp_out = codecs.open(self.filename, mode)
            logger.debug("{fileid}: File pointer: {fp}", fileid=self.fileid, fp=self.fp_out.__dict__)
        except IOError as e:
            (errno, strerror) = e.args
            raise YomboWarning(f"FileWriter could not open file for writing ({self.filename}). Reason: {strerror}",
                                 435121, "__init__", "FileWriter")

        self.save_running = False
        self.save_loop = LoopingCall(self.save)
        if "frequency" in kwargs:
            frequency = kwargs["frequency"]
        else:
            frequency = 1
        self.save_loop.start(frequency)

    def close(self):
        """
        Call to close the file from being monitored.

        This simply schedules the file to be closed really soon.  If you want it closed immediately, instead call:

        yield filewriter.close_while_waiting()  # note the yield!
        """
        callLater(0.0001, self.close_while_waiting)  # this can be called directly with a yield.

    @inlineCallbacks
    def close_while_waiting(self):
        """
        This
        :return:
        """
        yield self.save(close_when_done=True)

    def write(self, output):
        """
        Write something to the file.
        """
        self.write_queue.append(output)

    @inlineCallbacks
    def save(self, close_when_done=None):
        logger.debug("{fileid}: Save queue count {queue} ", fileid=self.fileid, queue=len(self.write_queue))
        if close_when_done is True:
            self.close_when_done = True
        if self.save_running:
            return
        self.save_running = True
        if len(self.write_queue) > 0:

            save_data = ""
            while len(self.write_queue) > 0:
                save_data += self.write_queue.pop(0)
            yield threads.deferToThread(self._write, save_data)
        if self.close_when_done is True:
            self._close()
        self.save_running = False

    def _close(self):
        """
        Private method, shouldn't called anywhere else.

        This closes the file if it's still valid.
        :return:
        """
        if self.fp_out is not None:
            self.fp_out.close()

    def _write(self, output):
        """
        Does the actual writing. This is called in a separate thread.

        :param output:
        :return:
        """
        self.save_loop.stop()
        if self.fp_out is not None:
            self.fp_out.write(output)
