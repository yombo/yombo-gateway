#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
The FileReader class uses non-blocking code to open and **monitor** a file
for reading lines of text and for monitoring the file for any new lines.

For any lines of the text found, it will send it to the function set
during setup. FileReader will monitor the file for new content and
send any new lines of text to the function define on setup.

**See logreader module for full working example.**

**Usage**:

.. code-block:: python

   from yombo.utils.filereader import FileReader  # load at the top of the file.
  
   class MyModule(YomboModule):
   # don't forget "def init(self)"

   def start(self):
       self.file = FileReader(self, filename="myfile.txt", callback=self.myNewContent))

   def myNewContent(self, theContent):
       logger.info("got new content: {theContent}", theContent=theContent)

   def stop(self):
       self.file.close()  # Tell FileReader to close the file. Very important!

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2013-2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import codecs
import os
from pathlib import Path

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.utils import get_component


class FileReader:
    """
    The file reader class will monitor a file for changes. If any new content
    is found, it will return the new content to the method passed in.

    Typically used to monitor log files.
    """
    def __init__(self, owner_object, filename, **kwargs):
        """
        Generate a new File Reader instance. 

        The params defined refer to kwargs and become class variables.

        :param filename: **Required.** The path and file to monitor.
        :type filename: string
        :param fileid: Assign a unique file id. Used if the filename may change
            in the future, but you want to persist tracking if the filename changes.
            defaults to filename is not supplied.
        :type fileid: string
        :param encoding: If using text, specify the encoding - default: utf-8
        :param callback: **Required.** A function to call with new content found in file.
        :type callback: pointer to function
        :param make_if_missing: If true, will create an empty file if file doesn't
            already exist.  Default: True
        :type make_if_missing: bool
        :param frequency: How often, in seconds, to check for new content. Default: 1
        :type frequency: int
        """
        if "encoding" in kwargs:
            self.encoding = kwargs["encoding"]
        else:
            self.encoding = "utf-8"

        if filename is None or filename == "":
            raise YomboWarning("FileReader requires a file name to read from,", 652321, "__init__", "FileWriter")
        if filename.startswith("/") is False:
            filename = f"./{filename}"

        try:
            self.filename = kwargs["filename"]
        except:
            raise YomboWarning("FileReader requires a filename to read.", 232124, "__init__", "FileReader")

        if os.path.exists(self.filename) is False:
            raise YomboWarning(f"FileReader cannot find the requested file to open for monitoring: {self.filename}",
                               423215, "__init__", "FileReader")
        try:
            self.callback = kwargs["callback"]
        except:
            raise YomboWarning("FileReader requires a callback to send data to.", 654231, "__init__", "FileReader")

        self._owner_object = owner_object

        self.fileid = kwargs.get("fileid", self.filename)
        self.make_if_missing = kwargs.get("make_if_missing", True)
        self.frequency = kwargs.get("frequency", 1)
        self._SQLDict = get_component("yombo.lib.sqldict")
        reactor.callLater(0.001, self.start)

    @inlineCallbacks
    def start(self):
        self.fileInfo = yield self._SQLDict.get("yombo.utils-filereader", "fileInfo")

        if "startLocation" not in self.fileInfo:
            self.fileInfo["startLocation"] = 0
        self.fp_in = None
        self.watch_loop = None

        try:
            if not os.path.exists(self.filename):
                if self.make_if_missing is True:  # if file doesn't exist
                    Path.touch(self.filename)  # Touch the file if it doesn't exists and set the counter to 0.
                    self.fileInfo["startLocation"] = 0
                else:
                    raise YomboWarning("File does not exist, told not cannot create one.",
                                         554224, "__init__", "FileReader")
            else:  # else, exists. If smaller than last run, reset the file pointer.
                file_info = os.stat(self.filename)
                if file_info.st_size < self.fileInfo["startLocation"]:
                    self.fileInfo["startLocation"] = 0
                
            self.fp_in = codecs.open(self.filename, encoding="utf-8")
            self.fp_in.seek(self.fileInfo["startLocation"])
        except IOError as e:
            (errno, strerror) = e.args
            raise YomboWarning(f"FileReader could not open file for reading. Reason: {strerror}",
                                 265743, "__init__", "FileReader")
        else:
            self.watch_loop = LoopingCall(self._watch)
            self.watch_loop.start(self.frequency)

    def close(self):
        """
        Call to close the file from being monitored.
        """
        if self.watch_loop is not None:
            self.watch_loop.stop()

        if self.fp_in is not None:
            self.fp_in.close()

    def _watch(self):
        """
        Watch for file input.
        fp -- file-like object with tell() and readlines() support.
        """
        for line in self.fp_in.readlines():
            self.callback(line)
        location = self.fp_in.tell()  # lets be friendly to SQLDict.
        if location != self.fileInfo["startLocation"]:
            self.fileInfo["startLocation"] = location
