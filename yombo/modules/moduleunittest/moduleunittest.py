"""
Module unit test is used to test loaded modules using their included _unittest
method.  You can functionality to your module to include unittests by defining
a _unittest method. 

:copyright: 2013 Yombo
:license: Yombo RPL 1.5
"""
import time
from collections import namedtuple

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall

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
        self.expected_tests = 0
        self.completed_tests = 0
        self.displayed_tests = 0
        self.displayed_tests = 0
        self.display_saw_new_items = 0
        self.display_no_new_items = 0
        self.good = []
        self.bad = []
        self.display_results_loop = LoopingCall(self.display_results)


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
        reactor.callLater(1, self.started) # so we can see our results easier

    def started(self):
        self.display_results_loop.start(1)
        logger.info("Module unit test running.")
        self.test_nodes()
        self.test_queues()

    @inlineCallbacks
    def test_nodes(self):
        try:
            node_base = self._Nodes['main_page']  # web interfaces should create the if it doesn't exist.
        except KeyError as e:
            logger.warn("Skipping node testing, cannot find main_menu")
            self.testAddBad("Node 'main_menu' not found.", 'main_manu node not found')
            return

        # print "unittest has node: %s" % node_base

        self.expected_tests += 2

        node = yield self._Nodes.get('main_page')
        self.assertIsEqual(node_base.node_id, node.node_id, "Node id's should match.")
        # print "unittest has node2: %s" % node
        node = yield self._Nodes.get('main_page', 'webinterface_page')
        self.assertIsEqual(node_base.node_id, node.node_id, "Node id's should match.")
        # print "unittest has node3: %s" % node

    def test_queues(self):
        self.expected_tests += 6

        self.assertNotEqual(self._Times.isTwilight, None, "self._Times.isTwilight should not be None")

        q1 = self._Queue.new('module.unittest.1', self.queue_worker1)  # test calls to things that don't return deferred
        q1.put('letsdoit', self.queue_results)
        q1.put('letsdoit', self.queue_results)
        q1.put('letsdoit', self.queue_results)

        q2 = self._Queue.new('module.unittest.2', self.queue_worker2)  # test calls which return deferreds
        q2.put('letsdoit', self.queue_results)
        q2.put('letsdoit', self.queue_results)
        q2.put('letsdoit', self.queue_results)

    def queue_worker1(self, arguments):
        self.assertIsEqual(arguments, 'letsdoit', "queue_worker() arguments should be the same.")
        return "someresults"

    @inlineCallbacks
    def queue_worker2(self, arguments):
        yield sleep(1)
        self.assertIsEqual(arguments, 'letsdoit', "queue_worker() arguments should be the same.")
        returnValue("someresults")

    def queue_results(self, args, results):
        self.assertIsEqual(results, "someresults", "queue_results(), results should match.")

        self.display_saw_new_items = 0
        self.display_no_new_items = 0

    def display_results(self):
        if self.displayed_tests != self.completed_tests:
            # print "DR - got difference.... %s  " % self.display_saw_new_items
            self.display_no_new_items = 0
            self.displayed_tests = self.completed_tests
            self.display_saw_new_items += 1

            if self.display_saw_new_items >= 5:
                logger.info("Appears tests still running, count so far: Good - {good}, Bad - {bad}", good=len(self.good), bad=len(self.bad))
                self.display_saw_new_items = 0

        else:  # we don't have new data.
            # print "DR - got same.... %s  " % self.display_no_new_items
            self.display_no_new_items += 1
            if self.display_no_new_items == 15:
                logger.info("Appears tests are done. Good - {good}, Bad - {bad}", good=len(self.good), bad=len(self.bad))
                if len(self.bad) > 0:
                    logger.warn("Details for bad tests:")
                    for result in self.bad:
                        logger.warn("- Test:{test}    Description:{description}", test=result['test'], description=result['description'])

    def testAddBad(self, description, test_output):
        # self.display_results_loop.reset()
        self.completed_tests += 1
        self.bad.append({'description':description, 'test': test_output})

    def assertNotEqual(self, val1, val2, description):
        # self.display_results_loop.reset()
        self.completed_tests += 1
        if val1 != val2:
            test = "%s != %s" % (val1, val2)
            logger.debug("Module unit test found good test: {description} :: {test}", description=description, test=test)
            self.good.append({'description':description, 'test': test})
        else:
            test = "%s == %s" % (val1, val2)
            logger.warn("Module unit test found bad test: {description} :: {test}", description=description, test=test)
            self.bad.append({'description':description, 'test': test})

    def assertIsEqual(self, val1, val2, description):
        # self.display_results_loop.reset()
        self.completed_tests += 1
        if val1 == val2:
            test = "%s == %s" % (val1, val2)
            logger.debug("Module unit test found good test: {description} :: {test}", description=description, test=test)
            self.good.append({'description':description, 'test': test})
        else:
            test = "%s != %s" % (val1, val2)
            logger.warn("Module unit test found bad test: {description} :: {test}", description=description, test=test)
            self.bad.append({'description':description, 'test': test})

    def assertNone(self, val1, description):
        self.assertEqual(val1, None, description)

    def assertNotNone(self, val1, description):
        self.assertNotEqual(val1, None, description)

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
        
        
            
            
