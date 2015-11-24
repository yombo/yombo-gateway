#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
"""
The FileReader class uses non-blocking code to open and monitor a file
for reading lines of text and for monitoring the file for any new lines.

For any lines of the text found, it will send it to the function set
during setup. FileReader will monitor the file for new content and
send any new lines of text to the function define on setup.

**See logreader module for full working example.**

**Usage**:

.. code-block:: python

   from yombo.core.filereader import FileReader  #load at the top of the file.
  
   class MyModule(YomboModule):
   # don't forget "def init(self)"

   def start(self):
       self.file = FileReader(self, filename="myfile.txt", callback=self.myNewContent))

   def myNewContent(self, theContent):
       logger.info("got new content: %s" % theContent)

   def stop(self):
       self.file.close()  # Tell FileReader to close the file. Very important!

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2013-2015 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import codecs
import os # used to create the file if it doesn't exist.

# Import twisted libraries
# from twisted.internet.reactor import callLater
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboFileError
from yombo.core.log import getLogger
from yombo.core.sqldict import SQLDict

logger = getLogger("core.filewatcher")

class BlankFileReader(object):
    pass

class FileReader:
    """
    The file reader class will monitor a file for changes. If any new content
    is found, it will return the new content to the method passed in.

    Typically used to monitor log files.
    """
    def __init__(self, instanceObj, **kwargs):
        """
        Generate a new File Reader instance. 

        The params defined refer to kwargs and become class variables.

        :param filename: **Required.** The path and file to monitor.
        :type filename: string
        :param fileid: Assign a unique file id. Used if the filename may change
            in the future, but you want to persist tracking if the filename changes.
            defaults to filename is not supplied.
        :type fileid: string
        :param callback: **Required.** A function to call with new content found in file.
        :type callback: pointer to function
        :param makeexist: If true, will create an empty file if file doesn't
            already exist.  Default: True
        :type makeexist: bool
        :param frequency: How often, in seconds, to check for new content. Default: 1
        :type frequency: int
        """
        try:
          self.filename       = kwargs['filename']
        except:
          raise FileError("filename not set.", 'FileWatcher API')

        try:
          self.callback       = kwargs['callback']
        except:
          raise FileError("callback not set.", 'FileWatcher API')

        self.fileid    = kwargs.get('fileid', self.filename)
        self.makeexist = kwargs.get('makeexist', True)
        self.frequency = kwargs.get('frequency', 1)

        blankObj = BlankFileReader()
        blankObj._FullName = "gateway.core.filereader-" + instanceObj._FullName.lower()

        self.fileInfo = SQLDict(blankObj, self.fileid) # Track file position

        if 'startLocation' not in self.fileInfo:
            self.fileInfo['startLocation'] = 0
        self.fp_in = None
        self.filestartable = False
        self.fileOpened = False
        self.timer = None

        try:
            if not os.path.exists(self.filename):
                if self.makeexist == True: # if file doesn't exist
                    open(self.filename, 'w').close()  # create it and then close.
                    self.fileInfo['startLocation'] = 0
                else:
                    raise FileError("File does not exist and not allowed to create.", 'FileWatcher API')
            else: # else, exists. If smaller than last run, reset the file pointer.
                fileInfo = os.stat(self.filename)
                if fileInfo.st_size < self.fileInfo['startLocation']:
                    self.fileInfo['startLocation'] = 0
                
            self.fp_in = codecs.open(self.filename, encoding='utf-8')
            self.fp_in.seek(self.fileInfo['startLocation'])
        except IOError as (errno, strerror):
            raise YomboFileError("Logreader could not open file for reading. Reason: %s" % strerror)
            self.fileOpened = None
            callLater(10, self.load)

        self.timer = LoopingCall(self._watch)
        self.timer.start(self.frequency)

    def close(self):
        """
        Call to close the file from being monitored.
        """
        if self.timer != None:
            self.timer.stop()

        if self.fp_in != None:
            self.fp_in.close()

    def _watch(self):
        """
        Watch for file input.
        fp -- file-like object with tell() and readlines() support.
        """
        for line in self.fp_in.readlines():
            self.callback(line)
 
        self.fileInfo['startLocation'] = self.fp_in.tell()
