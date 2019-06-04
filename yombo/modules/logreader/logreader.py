"""
This module demonstrates two features of the Yombo Gateway:

1. Using the pre-made FileReader to open a file for reading. The FileReader opens
  the file in a non-blocking style and sends new lines back to the module.
  The FileReader also keeps track of where it left off between restarts so
  duplicate lines are not sent. It's smart enough to start at the top if the
  file is smaller than were it left off before.

2. Treats the incoming logfile as a stream of commands. This provides a simple method to allow
   other processes to trigger actions, such as "open garage door".

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2013-2017 by Yombo.
:license: LICENSE for details.
"""
from yombo.core.exceptions import YomboFileError
from yombo.core.log import get_logger
from yombo.core.module import YomboModule
from yombo.utils.filereader import FileReader

logger = get_logger("modules.logreader")


class LogReader(YomboModule):
    """
    Monitors a file for intents and sends them to the intents library for processing.

    :ivar fileReader: A yombo :doc:`FileReader <../utils/filereader>` that reads text files
      delivers lines of text to callable.
    """
    def _init_(self, **kwargs):
        """
        Init the module.
        """
        self.fileReader = None  # Used to test if file reader is running on stop.

    def _load_(self, **kwargs):
        # Make sure YomboBot is loaded and available.
        try:
            self.YomboBot = self._Modules["yombobot"]
        except:
            logger.warn("Logreader module can't start due to no YomboBot module loaded.")
            return

        # Get a file name to monitor.
        if "logfile" in self.module_variables:
            self.fileName = self.module_variables["logfile"]["data"][0]
        else:
            logger.warn("No 'logfile' set for logreader, using default: 'logreader.txt'")
            self.fileName = "logreader.txt"

    def _start_(self, **kwargs):
        """
        Setups the file to be read. FileReader does the heavy lifting.

        * Get the YomboBot, and register the log reader as a user, even though it's blank.
        * Use the FileReader to open the file and monitor it for new lines.
        * Send any lines of text from the file reader to the YomboBot.
        """

        # Register with YomboBot.
        self.YomboBot.registerConnection(source=self, sessionid='logreader', authuser="UNKNOWN", remoteuser='None')

        # Setup the FileReader and tell it to send new text to "newContent()"
        try:
            self.fileReader = FileReader(self, filename=self.fileName, callback=self.newContent)
            self.fileReader.start()
            self.isRunning = True
        except YomboFileError as e:
            self.fileReader = None
            logger.warn("Error with FileReader: %s" % e)

    def newContent(self, linein):
        """
        Receives new lines of text from the FileReader here.

        Just pass the raw string to YomboBot for parsing.
        """
        pass

    def _stop_(self):
        """
        Module is shutting down. If a FileReader was setup, delete it. FileReader will close the file
        and save it's current location. This will be used next time as a starting point.
        """
        if self.fileReader is not None:
            self.fileReader.close()

    def _unload_(self):
        """
        Nothing to do, move along.
        """
        pass
