import json
import time

from yombo.core.module import YomboModule
from yombo.core.log import get_logger

logger = get_logger("modules.logwriter")

class LogWriter(YomboModule):
    """
    Simple log writer module - save yombo messages to log file.

    .. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

    :copyright: Copyright 2012-2020 by Yombo.
    :license: LICENSE for details.
    """

    def _init_(self, **kwargs):
        # Get a file name save data to..
        if "logfile" in self._ModVariables:
          self.fileName = self._ModVariables["logfile"]['values'][0]
        else:
          logger.warn("No 'logfile' set for log writing, using default: 'logwriter.txt'")
          self.fileName = "logwriter.txt"

        self.fp_out = None

    def _load_(self, **kwargs):
        """
        Simple file open.
        """
        try:
            self.fp_out = open(self.fileName, "a")
            logger.info("logwriter opened file: %s" % self.fileName)
        except IOError as e:
            (errno, strerror) = e.args
            logger.warn("Lowriter could not open file for writing. Reason: %s" % strerror)
            self.fp_out = None
            callLater(10, self.load)

    def _start_(self, **kwargs):
        """
        Nothing to start, move along.
        """
        pass

    def _stop_(self, **kwargs):
        """
        Nothing to stop.
        """
        pass

    def _unload_(self, **kwargs):
        """
        Flush and close the output log file.
        """
        if self.fp_out != None:
          try:
            self.fp_out.flush()
            self.fp_out.close()
          except:
            pass

    def _configs_set_(self, arguments, **kwargs):
        """
        Receive configuruation updates and adjust as needed.

        :param arguments: section, option(key), value
        :return:
        """
        section = arguments['section']
        option = arguments['option']
        value = arguments['value']

        self.fp_out.write("%s\n" % json.dumps(
            {'time': int(time.time()),
             'type': 'config_set',
             'section': section,
             'option': option,
             'value': value,
             }
        ))

    def _device_command_(self, arguments, **kwargs):
        """
        Received a device command.
        :param arguments: Contains 'device' and 'command'.
        :return: None
        """
        device = arguments['device']
        command = arguments['command']

        self.fp_out.write("%s\n" % json.dumps(
            {'time':int(time.time()),
             'type':'device_command',
             'device_id': device.device_id,
             'device_label': device.label,
             'command_id': command.command_id,
             'command_label': command.label,
             }
        ))

    def _device_state_(self, arguments, **kwargs):
        device = arguments['device']
        status = arguments['status']

        self.fp_out.write("%s\n" % json.dumps(
            {'time': int(time.time()),
             'type': 'device_command',
             'device_id': device.device_id,
             'status': status['human_state'],
             }
        ))

