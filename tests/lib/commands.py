import pyximport; pyximport.install()

import time

from yombo.core.exceptions import CommandError
from yombo.core.helpers import getComponent
from yombo.lib.commands import Command

from .. import ExpectingTestCase

class CommandsTests(ExpectingTestCase):
    """
    Test class for messages.
    """
    def setUp(self):
        self._Commands = getComponent("yombo.gateway.lib.commands")

    def testCreateCommand(self):
        """
        Simulates creating a command from sql. Insetad of asking sql, we supply
        the 'record' as it would come from SQL.
        """
        record = {'description'    : "Test command 1.",
#                  'created'        : int(time.time())-10,
#                  'updated'        : int(time.time()),
                  'liveupdate'     : 0,
                  'cmduuid'        : "yYyYyYyYyYyYyYyYyYyYyY01",
                  'cmd'            : "testcmd1",
                  'label'          : "Test Cmd 1",
                  'inputtypeid'    : 1,
                  'voicecmd'       : "test command 1",
                 }

        cmd = self._Commands._addCommand(record, True)
        
        self.expectTrue(isinstance(cmd, Command), "Asked to create a commnad, didn't get one.", first=True)
        self.expectEqual(record['description'], cmd.description, "Command didn't init with correct description.")
#        self.expectEqual(record['created'], dev.created, "Device didn't init with correct create time.")
        #self.expectEqual(record['updated'], dev.updated, "Device didn't init with correct update time.")
        self.expectEqual(record['liveupdate'], cmd.liveUpdate, "Command didn't init with correct liveupdate.")
        self.expectEqual(record['cmduuid'], cmd.cmdUUID, "Command didn't init with correct cmduuid.")
        self.expectEqual(record['cmd'], cmd.cmd, "Command didn't init with correct cmd.")
        self.expectEqual(record['label'], cmd.label, "Command didn't init with correct label.")
        self.expectEqual(record['inputtypeid'], cmd.inputTypeID, "Command didn't init with correct inputtypeid.")
        self.expectEqual(record['voicecmd'], cmd.voiceCmd, "Command didn't init with correct voicecmd.")

    def testCommandDump(self):
        """
        Validates that command.dump() function outputs expected results.
        """
        record = {'description'    : "Test command 2.",
#                  'created'        : int(time.time())-10,
#                  'updated'        : int(time.time()),
                  'liveupdate'     : 0,
                  'cmduuid'        : "yYyYyYyYyYyYyYyYyYyYyY02",
                  'cmd'            : "testcmd2",
                  'label'          : "Test Cmd 2",
                  'inputtypeid'    : 1,
                  'voicecmd'       : "test command 2",
                 }

        cmd = self._Commands._addCommand(record, True)
        dump = cmd.dump()

        self.expectTrue(isinstance(dump, dict), "Dump should return dict, not %s." % type(dump), first=True)
        self.expectEqual(record['description'], dump['description'], "Command didn't init with correct description.")
#        self.expectEqual(record['created'], dump['created'], "Device didn't init with correct create time.")
#        self.expectEqual(record['updated'], dump['updated'], "Device didn't init with correct update time.")
        self.expectEqual(record['liveupdate'], dump['liveUpdate'], "Command didn't init with correct liveUpdate.")
        self.expectEqual(record['cmduuid'], dump['cmdUUID'], "Command didn't init with correct cmdUUID.")
        self.expectEqual(record['cmd'], dump['cmd'], "Command didn't init with correct cmd.")
        self.expectEqual(record['label'], dump['label'], "Command didn't init with correct label.")
        self.expectEqual(record['inputtypeid'], dump['inputTypeID'], "Command didn't init with correct inputTypeID.")
        self.expectEqual(record['voicecmd'], dump['voiceCmd'], "Command didn't init with correct voicecmd.")

if __name__ == '__main__':
    main()
