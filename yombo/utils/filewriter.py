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
       self.file = FileWriter(self, filename="myfile.txt"))
       self.file.write("some more text....")

   def stop(self):
       self.file.close()  # Tell FileWriter to close the file. Very important!

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2013-2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import codecs
import os

# Import twisted libraries
from twisted.internet import reactor, threads
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboFileError
from yombo.utils import get_component


class FileWriter:
    """
    The file writer will open and keep a file open for writing.

    Typically used for log files.
    """
    def __init__(self, filename, **kwargs):
        """
        Generate a new File Writer instance.

        The params defined refer to kwargs and become class variables.

        :param filename: **Required.** The path and file to monitor.
        :type filename: string
        :param fileid: Assign a unique file id. Used if the filename may change
            in the future, but you want to persist tracking if the filename changes.
            defaults to filename is not supplied.
        :type fileid: string
        :param make_if_missing: If true, will create an empty file if file doesn't
            already exist.  Default: True
        :type make_if_missing: bool
        """
        try:
            self.filename = filename
        except:
            raise YomboFileError("filename not set.", 101, '__init__', 'FileWriter')

        self.fileid = kwargs.get('fileid', self.filename)
        self.make_if_missing = kwargs.get('make_if_missing', True)

        self.write_queue = []
        try:
            if not os.path.exists(self.filename):
                if self.make_if_missing is True:  # if file doesn't exist
                    open(self.filename, 'w').close()  # create it and then close.
                else:
                    raise YomboFileError("File does not exist, told not cannot create one.",
                                         103, '__init__', 'FileReader')

            self.fp_in = codecs.open(self.filename, 'a', encoding='utf-8')
        except IOError as e:
            (errno, strerror) = e.args
            raise YomboFileError("Logreader could not open file for reading. Reason: %s" % strerror,
                                 104, '__init__', 'FileReader')

        self.check_write_queue_running = False
        self.check_write_queue_loop = LoopingCall(self.check_write_queue)
        self.check_write_queue_loop.start(1)

    def close(self):
        """
        Call to close the file from being monitored.
        """
        if self.fp_in is not None:
            self.fp_in.close()

    def write(self, output):
        """
        Write something to the file.
        """
        self.write_queue.append(output)

    @inlineCallbacks
    def check_write_queue(self):
        if self.check_write_queue_running:
            return
        self.check_write_queue_running = True
        while len(self.write_queue) > 0:
            yield threads.deferToThread(self._write, self.write_queue.pop(0))
        self.check_write_queue_running = False

    def _write(self, output):
        """
        Does the actual writing. This is called in a separate thread.

        :param output:
        :return:
        """
        if self.fp_in is not None:
            self.fp_in.write(output)
