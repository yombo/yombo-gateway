import json
import time

from yombo.core.module import YomboModule
from yombo.core.log import getLogger

logger = getLogger("modules.logwriter")

class LogWriter(YomboModule):
    """
    Simple log writer module - save yombo messages to log file.

    :author: U{Mitch Schwenk<mitch@ahx.me>}
    :organization: U{Automated Home Exchange (AHX)<http://www.ahx.me>}
    :copyright: 2010-2013 Yombo
    :license: see LICENSE.TXT from Yombo Gateway Software distribution
    """

    def _init_(self):
        self._ModDescription = "Writes message to a log file."
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "http://www.yombo.net"
        self._RegisterDistributions = ['all']

        # Get a file name save data to..
        if "logfile" in self._ModVariables:
          self.fileName = self._ModVariables["logfile"][0]
        else:
          logger.warn("No 'logfile' set for log writing, using default: 'logwriter.txt'")
          self.fileName = "logwriter.txt"

        self.fp_out = None

    def _load_(self):
        """
        Simple file open.
        """
        try:
            self.fp_out = open("logwriter.out", "a")
            logger.info("logwriter opened file: %s" % self.fileName)
        except IOError as (errno, strerror):
            logger.warn("Lowriter could not open file for writing. Reason: %s" % strerror)
            self.fp_out = None
            callLater(10, self.load)

    def _start_(self):
        """
        Nothing to start, move along.
        """
        pass

    def _stop_(self):
        """
        Nothing to stop.
        """
        pass

    def _unload_(self):
        """
        Flush and close the output log file.
        """
        if self.fp_out != None:
          try:
            self.fp_out.flush()
            self.fp_out.close()
          except:
            pass

    def message(self, message):
        """
        Save incoming messages to log file out.
        """
        msg = message.dump() # Lets not mangle the original.
        if 'cmdobj' in msg['payload']:
          msg['payload']['cmdUUID'] = msg['payload']['cmdobj'].cmdUUID
          del msg['payload']['cmdobj']
        if 'deviceobj' in msg['payload']:
          msg['payload']['deviceUUID'] = msg['payload']['deviceobj'].deviceUUID
          del msg['payload']['deviceobj']
        self.fp_out.write("%s\n" % json.dumps({'time':int(time.time()),'message':msg}) )
