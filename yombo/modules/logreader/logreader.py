from yombo.core.exceptions import FileError
from yombo.core.filereader import FileReader
from yombo.core.module import YomboModule
from yombo.core.helpers import getComponent, generateUUID
from yombo.core.log import getLogger

logger = getLogger("modules.logreader")

class LogReader(YomboModule):
    """
    Monitors a file for voice commands and send them to yombobot for processing.
    """
    def init(self):
        self._ModDescription = "Logread monitors a file for voice commands."
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "http://www.yombo.net"

        self.fileReader = None # Used to test if file reader is running on stop.

    def load(self):
        """
        Nothing to do here, move along.
        """
        pass

    def start(self):
        """
        Setups the file to be read. FileReader does the heavy lifting.

        * Get the YomboBot, and register the log reader as a user, even though it's blank.
        * Use the FileReader to open the file and monitor it for new lines.
        * Send any lines of text from the file reader to the YomboBot.
        """
        # Make sure YomboBot is loaded and available.
        try:
            self.YomboBot = getComponent('yombo.gateway.modules.yombobot')
        except:
            logger.warning("Jabber module can't start due to no YomboBot module loaded.")
            return

        # Get a file name to monitor.
        if "logfile" in self._ModVariables:
          self.fileName = self._ModVariables["logfile"][0]
        else:
          logger.warning("No 'logfile' set for logreader, using default: 'logreader.txt'")
          self.fileName = "logreader.txt"

        # Register with YomboBot.
        self.YomboBot.registerConnection(source=self, sessionid='logreader', authuser="UNKNOWN", remoteuser='None')

        # Setup the FileReader and tell it to send new text to "newContent()"
        try:
            self.fileReader = FileReader(self, filename=self.fileName, callback=self.newContent)
            self.isRunning = True
        except FileError, e:
            self.fileReader = None
            logger.warning("Error with FileReader: %s" % e)

    def newContent(self, linein):
        """
        Recieves new lines of text from the FileReader here.
        """
        self.YomboBot.incoming(returncall=self.yomboBotReturn, linein=linein, msgid=generateUUID(), sessionid='logreaderSession')

    def yomboBotReturn(self, **kwargs):
        """
        Had to tell YomboBot where to return results, however, we don't really care about them.
        Just discard it. All is good.
        """
        pass


    def stop(self):
        """
        Module is shutting down. If a FileReader was setup, delete it. FileReader will close the file
        and save it's current location. This will be used next time as a starting point.
        """
        if self.fileReader != None:
            self.fileReader.close()

    def unload(self):
        """
        Nothing to do, move along.
        """
        pass

    def message(self, message):
        """
        We don't do anything with messages, move along.
        """
        pass
