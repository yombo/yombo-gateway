"""
Module unit test is used to test loaded modules using their included _unittest
method.  You can functionality to your module to include unittests by defining
a _unittest method. 

:copyright: 2013 Yombo
:license: Yombo RPL 1.5
"""
import time
from collections import namedtuple

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.core.log import get_logger
from yombo.core.module import YomboModule
from yombo.utils import sleep

logger = get_logger("module.test")

class ModuleUnitTest(YomboModule):
    """
    ModuleUnitTest
    """
    def _init_(self):
        """
        """

        # place to store our commands.
        self.available_commands = {}

        # store our devices
        self.devices = {}
        
        # track messages we send.  Give it structure
        self.outMsg = namedtuple('outMsg', "time, device_id, message")
        self.outMessages = {}

        # track success and failures
        self.good = []
        self.bad = []

    def _load_(self):
        """
        After this phase, module should be able to
        processing incoming messages.
        
        In this example, we call the self.loaded function after 2 seconds.
        This load function doesn't really do anything.
        
        Startup phase 2 of 3.
        """
        # deviceCmds = []
        # for cmd in self.available_commands:
        #     deviceCmds.append(self.available_commands[cmd].cmdUUID)
        #
        #
        # # Don't ever do this in a real module. But add some test devices.
        # record = {'description'    : "Test device 1.",
        #           'created'        : int(time.time())-10,
        #           'updated'        : int(time.time()),
        #           'device_type_id' : "zZzZzZzZzZzZzZzZzZzZzZ01",
        #           'pin_timeout'     : 100,
        #           'device_id'     : "01zZzZzZzZzZzZzZzZzZzZzZ",
        #           'label'          : "tstdvc1",
        #           'pin_code'        : "1234",
        #           'pin_required'    : 0,
        #           'module_label'    : "ModuleUnitTest",
        #           'voice_cmd'       : "tstdvc01 [on, off, open, close]",
        #           'voice_cmd_order'  : "verbnoun",
        #           'status'         : 1,
        #          }
        #
        # self.devices[1] = self.libraries['Devices']._addDevice(record, True)
        # self.libraries['Devices'].yombodevices['01zZzZzZzZzZzZzZzZzZzZzZ'].available_commands = deviceCmds
        #
        # record = {'description'   : "Test device 2.  Number in front t test fuzzy searches.",
        #           'created'       : int(time.time()),
        #           'updated'        : int(time.time()),
        #           'device_type_id': "zZzZzZzZzZzZzZzZzZzZzZ01",
        #           'pin_timeout'    : 100,
        #           'device_id'    : "02zZzZzZzZzZzZzZzZzZzZzZ",
        #           'label'         : "2dvctst",
        #           'pin_code'       : "1234",
        #           'pin_required'   : 0,
        #           'module_label'   : "ModuleUnitTest",
        #           'voice_cmd'      : "2dvctst [on, off, open, close]",
        #           'voice_cmd_order'  : "nounverb",
        #           'status'         : 1,
        #          }
        #
        # self.devices[2]= self.libraries['Devices']._addDevice(record, True)
        # self.libraries['Devices'].yombodevices['02zZzZzZzZzZzZzZzZzZzZzZ'].available_commands = deviceCmds
        
    def _start_(self):
        """
        Assume all other modules are loaded, we can start
        sending messages to other modules.  Here, is where we enable or turn on
        message sending from within our module.
        
        Startup phase 3 of 3.
        """
        reactor.callLater(2, self.started) # so we can see our results easier

    def started(self):

        self.assertNotEqual(self._Times.isTwilight, None, "self._Times.isTwilight should not be None")

        q1 = self._Queue.new('module.unittest.1', self.queue_worker1)
        q1.put('letsdoit', self.queue_results)
        q1.put('letsdoit', self.queue_results)
        q1.put('letsdoit', self.queue_results)

        q2 = self._Queue.new('module.unittest.2', self.queue_worker2)
        q2.put('letsdoit', self.queue_results)
        q2.put('letsdoit', self.queue_results)
        q2.put('letsdoit', self.queue_results)
        q2.put('letsdoit', self.show_results)

    def queue_worker1(self, arguments):
        print "queue_worker1 got arguments: %s" % arguments
        self.assertIsEqual(arguments, 'letsdoit', "queue_worker() arguments should be the same.")
        return "someresults"

    @inlineCallbacks
    def queue_worker2(self, arguments):
        print "queue_worker2 got arguments: %s" % arguments
        yield sleep(1)
        self.assertIsEqual(arguments, 'letsdoit', "queue_worker() arguments should be the same.")
        returnValue("someresults")

    def queue_results(self, args, results):
        self.assertIsEqual(results, "someresults", "queue_results(), results should match.")

    def show_results(self, dumpit = None, dumpit2 = None):
        print "Module Unit Test results:"
        print "Good results: %s" % len(self.good)
        print "Bad results: %s" % len(self.bad)
        for result in self.bad:
            print "%s - %s" % (result['test'], result['description'])

    def assertNotEqual(self, val1, val2, description):
        if val1 != val2:
            self.good.append({'description':description, 'test': "%s != %s" % (val1, val2)})
        else:
            self.good.append({'description':description, 'test': "%s == %s" % (val1, val2)})

    def assertIsEqual(self, val1, val2, description):
        if val1 == val2:
            self.good.append({'description':description, 'test': "%s == %s" % (val1, val2)})
        else:
            self.good.append({'description':description, 'test': "%s != %s" % (val1, val2)})

            #
#         logger.info("isDay: %s" % self._Times.isDay)
#         logger.info("isLight: %s" % self.libraries['Times'].isLight)
#         logger.info("isTwilight: %s" % self.libraries['Times'].isTwilight)
#
#         logger.info("isDark: %s" % self.libraries['Times'].isDark)
#         logger.info("isNight: %s" % self.libraries['Times'].isNight)
#
#         logger.info("Time is now: %f" % time.time())
#
#         logger.info("My longitude is: %s " % str(getConfigValue('location', 'latitude', 0)) )
#
#         if self.libraries['Times'].isLight:
#           delayed = int( self.libraries['Times'].CLnowDark.getTime() - time.time() )
#           logger.info("It will be dark in %d seconds." % delayed )
#         else:
#           delayed = int( self.libraries['Times'].CLnowLight.getTime() - time.time() )
#           logger.info("It will be light in %d seconds." % int(time.time()) )
#
#         # test times
#         if self.libraries['Times'].isLight == self.libraries['Times'].isDark:
#             logger.error("It can't be light and dark at same time!!")
#         if self.libraries['Times'].isDay == self.libraries['Times'].isNight:
#             logger.error("It can't be day and night at same time!!")
#
# #        self.outMsg = namedtuple('outMsg', "time, device_id, message")
# #        self.outMessages = {}
#         msg = self.devices[1].getMessage(self, cmdobj=self.available_commands['open'])
#         self.outMessages[msg.msgUUID] = self.outMsg(time.time(), self.devices[1].device_id, msg)
        
    
    def _stop_(self):
        """
        Stop sending messages.  Other components are unable to receive
        messages.  Queue up or pause functionality.
        """
        pass
    
    def _unload_(self):
        """
        Called just before the gateway is about to shutdown
        or reload all the modules.  Should assume gateway is going down.
        """
        pass

    def message(self, message):
        """
        Incomming Yombo Messages from the gateway or remote sources will
        be sent here.
        """
        logger.info("we go something:%s" % message.dump())
        pass
        
        
            
            
