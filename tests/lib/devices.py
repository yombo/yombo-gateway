import pyximport; pyximport.install()

import time
import mock

from yombo.core.exceptions import Yombopin_codeError, DeviceError
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
                  'device_type_id' : "zZzZzZzZzZzZzZzZzZzZzZ01",
                  'pin_required'    : 0,
                  'pin_code'      : "1234",
                  'pin_timeout'     : 100,
                  'device_id'     : "01zZzZzZzZzZzZzZzZzZzZ01",
                  'label'          : "tstdvc1",
                  'status'         : 1, #device enabled or not, not device status
                  'module_label'    : "ModuleUnitTest",
                  'voice_cmd'       : "tstdvc01 [on, off, open, close]",
                  'voice_cmdorder'  : "verbnoun",
                 }

        dev = self._Devices._addDevice(record, True)
        
        self.expectTrue(isinstance(dev, Device), "Asked to create a device, didn't get one.", first=True)
        self.expectEqual(record['description'], dev.description, "Device didn't init with correct description.")
        self.expectEqual(record['created'], dev.created, "Device didn't init with correct create time.")
        self.expectEqual(record['updated'], dev.updated, "Device didn't init with correct update time.")
        self.expectEqual(record['device_type_id'], dev.device_type_id, "Device didn't init with correct device_type_id.")
        self.expectEqual(record['pin_timeout'], dev.pin_timeout, "Device didn't init with correct pin_timeout.")
        self.expectEqual(record['device_id'], dev.device_id, "Device didn't init with correct device_id.")
        self.expectEqual(record['label'], dev.label, "Device didn't init with correct label.")
        self.expectEqual(record['pin_code'], dev.pin_code, "Device didn't init with correct pin_code.")
        self.expectEqual(record['pin_required'], dev.pin_required, "Device didn't init with correct pin_required.")
        self.expectEqual(record['module_label'], dev.module_label, "Device didn't init with correct module_label.")
        self.expectEqual(record['voice_cmd'], dev.voice_cmd, "Device didn't init with correct voice_cmd.")
        self.expectEqual(record['voice_cmdorder'], dev.voice_cmdOrder, "Device didn't init with correct voice_cmdorder.")
        self.expectEqual(record['status'], dev.enabled, "Device didn't init with correct enable status.")

    def testDeviceDump(self):
        """
        Validates that device.dump() function outputs expected results.
        """
        record = {'description'    : "Test device 2.",
                  'created'        : int(time.time())-9,
                  'updated'        : int(time.time()),
                  'device_type_id' : "zZzZzZzZzZzZzZzZzZzZzZ02",
                  'pin_required'   : 0,
                  'pin_timeout'    : 100,
                  'pin_code'       : "1234",
                  'device_id'      : "01zZzZzZzZzZzZzZzZzZzZ02",
                  'label'          : "tstdvc2",
                  'status'         : 1, #device enabled or not, not device status
                  'module_label'    : "ModuleUnitTest",
                  'voice_cmd'      : "tstdvc01 [on, off, open, close]",
                  'voice_cmd_order' : "verbnoun",
                  'Voice_cmd_src'  : "manual",
                 }

        dev = self._Devices._addDevice(record, True)
        dump = dev.dump()

        self.expectTrue(isinstance(dump, dict), "Dump should return dict, not %s." % type(dump), first=True)
        self.expectEqual(record['description'], dump['description'], "Device didn't init with correct description.")
        self.expectEqual(record['created'], dump['created'], "Device didn't init with correct create time.")
        self.expectEqual(record['updated'], dump['updated'], "Device didn't init with correct update time.")
        self.expectEqual(record['device_type_id'], dump['device_type_id'], "Device didn't init with correct device_type_id.")
        self.expectEqual(record['pin_timeout'], dump['pin_timeout'], "Device didn't init with correct pin_timeout.")
        self.expectEqual(record['device_id'], dump['device_id'], "Device didn't init with correct device_id.")
        self.expectEqual(record['label'], dump['label'], "Device didn't init with correct label.")
        self.expectEqual(record['pin_required'], dump['pin_required'], "Device didn't init with correct pin_required.")
        self.expectEqual(record['module_label'], dump['module_label'], "Device didn't init with correct module_label.")
        self.expectEqual(record['voice_cmd'], dump['voice_cmd'], "Device didn't init with correct voice_cmd.")
        self.expectEqual(record['voice_cmdorder'], dump['voice_cmdOrder'], "Device didn't init with correct voice_cmdorder.")
#        self.expectEqual(record['status'], dev.enabled, "Device didn't init with correct enable status.")


    def testDeviceGetMessage(self):
        """
        Validates device.get_message().
        """
        record = {'description'    : "Test device 2.",
                  'created'        : int(time.time())-9,
                  'updated'        : int(time.time()),
                  'device_id'     : "01zZzZzZzZzZzZzZzZzZzZ03",
                  'device_type_id' : "zZzZzZzZzZzZzZzZzZzZzZ03",
                  'pin_required'    : 1,
                  'pin_timeout'     : 100,
                  'pin_code'        : "1234",
                  'label'          : "tstdvc3",
                  'status'         : 1, #device enabled or not, not device status
                  'module_label'    : "ModuleUnitTest",
                  'voice_cmd'       : "tstdvc01 [on, off, open, close]",
                  'voice_cmdorder'  : "verbnoun",
                 }

        dev = self._Devices._addDevice(record, True)  # create dummy device
        with self.expectRaises(Yombopin_codeError):       # Pin is required, so, it should toss an error
            dev.get_message('yombo.gateway.tests.devices')

        with self.expectRaises(DeviceError): # no cmd, cmdUUID, or cmdobj submitted.
            dev.get_message('yombo.gateway.tests.devices', pin_code="1234")

        command = {'description'    : "Test command 3.",
#                  'created'        : int(time.time())-10,
#                  'updated'        : int(time.time()),
                  'liveupdate'     : 0,
                  'cmduuid'        : "yYyYyYyYyYyYyYyYyYyYyY03",
                  'cmd'            : "testcmd3",
                  'label'          : "Test Cmd 3",
                  'inputtypeid'    : 1,
                  'voice_cmd'       : "test command 3",
                 }

        _Commands = getComponent("yombo.gateway.lib.commands")
        _Commands._addCommand(command, True)

        dev.availableCommands = ['yYyYyYyYyYyYyYyYyYyYyY03'] # force this command to work with device
        
        tempObj = mock.Mock()
        tempObj._FullName = "yombo.gateway.tests.devices"
        dev.get_message(tempObj, pin_code="1234", cmd="Test Cmd 3")

if __name__ == '__main__':
    main()
