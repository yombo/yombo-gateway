import pyximport; pyximport.install()

import time
import mock

from yombo.core.exceptions import PinNumberError, DeviceError
from yombo.core.helpers import getComponent
from yombo.lib.devices import Device

from .. import ExpectingTestCase

class DevicesTests(ExpectingTestCase):
    """
    Test class for messages.
    """
    def setUp(self):
        self._Devices = getComponent("yombo.gateway.lib.devices")

    def testCreateDevice(self):
        """
        Simulates creating a device from sql. Insetad of asking sql, we supply
        the 'record' as it would come from SQL.
        """
        record = {'description'    : "Test device 1.",
                  'created'        : int(time.time())-10,
                  'updated'        : int(time.time()),
                  'devicetypeuuid' : "zZzZzZzZzZzZzZzZzZzZzZ01",
                  'pintimeout'     : 100,
                  'deviceuuid'     : "01zZzZzZzZzZzZzZzZzZzZ01",
                  'label'          : "tstdvc1",
                  'pinnumber'      : 1234,
                  'status'         : 1, #device enabled or not, not device status
                  'pinrequired'    : 0,
                  'modulelabel'    : "ModuleUnitTest",
                  'voicecmd'       : "tstdvc01 [on, off, open, close]",
                  'voicecmdorder'  : "verbnoun",
                 }

        dev = self._Devices._addDevice(record, True)
        
        self.expectTrue(isinstance(dev, Device), "Asked to create a device, didn't get one.", first=True)
        self.expectEqual(record['description'], dev.description, "Device didn't init with correct description.")
        self.expectEqual(record['created'], dev.created, "Device didn't init with correct create time.")
        self.expectEqual(record['updated'], dev.updated, "Device didn't init with correct update time.")
        self.expectEqual(record['devicetypeuuid'], dev.deviceTypeUUID, "Device didn't init with correct devicetypeuuid.")
        self.expectEqual(record['pintimeout'], dev.pintimeout, "Device didn't init with correct pintimeout.")
        self.expectEqual(record['deviceuuid'], dev.deviceUUID, "Device didn't init with correct deviceuuid.")
        self.expectEqual(record['label'], dev.label, "Device didn't init with correct label.")
        self.expectEqual(record['pinnumber'], dev.pinnumber, "Device didn't init with correct pinnumber.")
        self.expectEqual(record['pinrequired'], dev.pinrequired, "Device didn't init with correct pinrequired.")
        self.expectEqual(record['modulelabel'], dev.moduleLabel, "Device didn't init with correct modulelabel.")
        self.expectEqual(record['voicecmd'], dev.voiceCmd, "Device didn't init with correct voicecmd.")
        self.expectEqual(record['voicecmdorder'], dev.voiceCmdOrder, "Device didn't init with correct voicecmdorder.")
        self.expectEqual(record['status'], dev.enabled, "Device didn't init with correct enable status.")

    def testDeviceDump(self):
        """
        Validates that device.dump() function outputs expected results.
        """
        record = {'description'    : "Test device 2.",
                  'created'        : int(time.time())-9,
                  'updated'        : int(time.time()),
                  'devicetypeuuid' : "zZzZzZzZzZzZzZzZzZzZzZ02",
                  'pintimeout'     : 100,
                  'deviceuuid'     : "01zZzZzZzZzZzZzZzZzZzZ02",
                  'label'          : "tstdvc2",
                  'pinnumber'      : 1234,
                  'status'         : 1, #device enabled or not, not device status
                  'pinrequired'    : 0,
                  'modulelabel'    : "ModuleUnitTest",
                  'voicecmd'       : "tstdvc01 [on, off, open, close]",
                  'voicecmdorder'  : "verbnoun",
                 }

        dev = self._Devices._addDevice(record, True)
        dump = dev.dump()

        self.expectTrue(isinstance(dump, dict), "Dump should return dict, not %s." % type(dump), first=True)
        self.expectEqual(record['description'], dump['description'], "Device didn't init with correct description.")
        self.expectEqual(record['created'], dump['created'], "Device didn't init with correct create time.")
        self.expectEqual(record['updated'], dump['updated'], "Device didn't init with correct update time.")
        self.expectEqual(record['devicetypeuuid'], dump['deviceTypeUUID'], "Device didn't init with correct devicetypeuuid.")
        self.expectEqual(record['pintimeout'], dump['pintimeout'], "Device didn't init with correct pintimeout.")
        self.expectEqual(record['deviceuuid'], dump['deviceUUID'], "Device didn't init with correct deviceuuid.")
        self.expectEqual(record['label'], dump['label'], "Device didn't init with correct label.")
        self.expectEqual(record['pinrequired'], dump['pinrequired'], "Device didn't init with correct pinrequired.")
        self.expectEqual(record['modulelabel'], dump['moduleLabel'], "Device didn't init with correct modulelabel.")
        self.expectEqual(record['voicecmd'], dump['voiceCmd'], "Device didn't init with correct voicecmd.")
        self.expectEqual(record['voicecmdorder'], dump['voiceCmdOrder'], "Device didn't init with correct voicecmdorder.")
#        self.expectEqual(record['status'], dev.enabled, "Device didn't init with correct enable status.")


    def testDeviceGetMessage(self):
        """
        Validates device.getMessage().
        """
        record = {'description'    : "Test device 2.",
                  'created'        : int(time.time())-9,
                  'updated'        : int(time.time()),
                  'devicetypeuuid' : "zZzZzZzZzZzZzZzZzZzZzZ03",
                  'pintimeout'     : 100,
                  'deviceuuid'     : "01zZzZzZzZzZzZzZzZzZzZ03",
                  'label'          : "tstdvc3",
                  'pinnumber'      : 1234,
                  'status'         : 1, #device enabled or not, not device status
                  'pinrequired'    : 1,
                  'modulelabel'    : "ModuleUnitTest",
                  'voicecmd'       : "tstdvc01 [on, off, open, close]",
                  'voicecmdorder'  : "verbnoun",
                 }

        dev = self._Devices._addDevice(record, True)  # create dummy device
        with self.expectRaises(PinNumberError):       # Pin is required, so, it should toss an error
            dev.getMessage('yombo.gateway.tests.devices')

        with self.expectRaises(DeviceError): # no cmd, cmdUUID, or cmdobj submitted.
            dev.getMessage('yombo.gateway.tests.devices', pinnumber=1234)

        command = {'description'    : "Test command 3.",
#                  'created'        : int(time.time())-10,
#                  'updated'        : int(time.time()),
                  'liveupdate'     : 0,
                  'cmduuid'        : "yYyYyYyYyYyYyYyYyYyYyY03",
                  'cmd'            : "testcmd3",
                  'label'          : "Test Cmd 3",
                  'inputtypeid'    : 1,
                  'voicecmd'       : "test command 3",
                 }

        _Commands = getComponent("yombo.gateway.lib.commands")
        _Commands._addCommand(command, True)

        dev.availableCommands = ['yYyYyYyYyYyYyYyYyYyYyY03'] # force this command to work with device
        
        tempObj = mock.Mock()
        tempObj._FullName = "yombo.gateway.tests.devices"
        dev.getMessage(tempObj, pinnumber=1234, cmd="Test Cmd 3")

if __name__ == '__main__':
    main()
