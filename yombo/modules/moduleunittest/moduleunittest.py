"""
Module unit test aims to test all the libraries and core functions. Inspiration
for this came from adding various features to the manhole module. These tests
should be automatic.

:copyright: 2013 Yombo
:license: Yombo RPL 1.5
"""
from collections import namedtuple
import time

from twisted.internet import reactor
from yombo.core.module import YomboModule
from yombo.core.helpers import getTimes, getConfigValue
from yombo.core.log import getLogger
from yombo.core.sqldict import SQLDict
from yombo.lib.loader import getTheLoadedComponents # Don't use this!

logger = getLogger("module.test")

class ModuleUnitTest(YomboModule):
    """
    ModuleUnitTest
    """
    def init(self):
        """
        Init the module.  Don't use __init__ as that will override the
        setup functions of the base YomboModule class.
        
        Startup phase 1 of 3.
        """
        self._ModDescription = "Insteon API command interface"
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "http://www.yombo.net"

        self.reactors = SQLDict(self, "testr")

        self.components = getTheLoadedComponents()
        self.libraries = self.components['yombo.gateway.lib.loader'].libraryNames
        self.modules = self.components['yombo.gateway.lib.loader'].moduleNames
        
        # place to store our commands.
        self.availableCommands = {}
        self.availableCommands['open'] = self.libraries['Commands']['open']
        self.availableCommands['close'] = self.libraries['Commands']['close']
        self.availableCommands['on'] = self.libraries['Commands']['on']
        self.availableCommands['off'] = self.libraries['Commands']['off']
        
        # store our devices
        self.devices = {}
        
        # track messages we send.  Give it structure
        self.outMsg = namedtuple('outMsg', "time, deviceUUID, message")
        self.outMessages = {}

    def load(self):
        """
        After this phase, module should be able to
        processing incoming messages.
        
        In this example, we call the self.loaded function after 2 seconds.
        This load function doesn't really do anything.
        
        Startup phase 2 of 3.
        """
        deviceCmds = []
        for cmd in self.availableCommands:
            deviceCmds.append(self.availableCommands[cmd].cmdUUID)
        

        # Don't ever do this in a real module. But add some test devices.
        record = {'description'    : "Test device 1.",
                  'created'        : int(time.time())-10,
                  'updated'        : int(time.time()),
                  'devicetypeuuid' : "zZzZzZzZzZzZzZzZzZzZzZ01",
                  'pintimeout'     : 100,
                  'deviceuuid'     : "01zZzZzZzZzZzZzZzZzZzZzZ",
                  'label'          : "tstdvc1",
                  'pinnumber'      : 1234,
                  'pinrequired'    : 0,
                  'modulelabel'    : "ModuleUnitTest",
                  'voicecmd'       : "tstdvc01 [on, off, open, close]",
                  'voicecmdorder'  : "verbnoun",
                  'status'         : 1,
                 }
       
        self.devices[1] = self.libraries['Devices']._addDevice(record, True)
        self.libraries['Devices'].yombodevices['01zZzZzZzZzZzZzZzZzZzZzZ'].availableCommands = deviceCmds

        record = {'description'   : "Test device 2.  Number in front t test fuzzy searches.",
                  'created'       : int(time.time()),
                  'updated'        : int(time.time()),
                  'devicetypeuuid': "zZzZzZzZzZzZzZzZzZzZzZ01",
                  'pintimeout'    : 100,
                  'deviceuuid'    : "02zZzZzZzZzZzZzZzZzZzZzZ",
                  'label'         : "2dvctst",
                  'pinnumber'     : 1234,
                  'pinrequired'   : 0,
                  'modulelabel'   : "ModuleUnitTest",
                  'voicecmd'      : "2dvctst [on, off, open, close]",
                  'voicecmdorder'  : "nounverb",
                  'status'         : 1,
                 }
       
        self.devices[2]= self.libraries['Devices']._addDevice(record, True)
        self.libraries['Devices'].yombodevices['02zZzZzZzZzZzZzZzZzZzZzZ'].availableCommands = deviceCmds
        
    def start(self):
        """
        Assume all other modules are loaded, we can start
        sending messages to other modules.  Here, is where we enable or turn on
        message sending from within our module.
        
        Startup phase 3 of 3.
        """
        reactor.callLater(2, self.started) # so we can see our results easier

    def started(self):

        logger.info("isDay: %s" % self.libraries['Times'].isDay)
        logger.info("isLight: %s" % self.libraries['Times'].isLight)
        logger.info("isTwilight: %s" % self.libraries['Times'].isTwilight)

        logger.info("isDark: %s" % self.libraries['Times'].isDark)
        logger.info("isNight: %s" % self.libraries['Times'].isNight)

        logger.info("Time is now: %f" % time.time())

        logger.info("My longitude is: %s " % str(getConfigValue('location', 'latitude', 0)) )

        if self.libraries['Times'].isLight:
          delayed = int( self.libraries['Times'].CLnowDark.getTime() - time.time() )
          logger.info("It will be dark in %d seconds." % delayed )
        else:
          delayed = int( self.libraries['Times'].CLnowLight.getTime() - time.time() )
          logger.info("It will be light in %d seconds." % int(time.time()) )

        # test times
        if self.libraries['Times'].isLight == self.libraries['Times'].isDark:
            logger.error("It can't be light and dark at same time!!")
        if self.libraries['Times'].isDay == self.libraries['Times'].isNight:
            logger.error("It can't be day and night at same time!!")

#        self.outMsg = namedtuple('outMsg', "time, deviceUUID, message")
#        self.outMessages = {}
        msg = self.devices[1].getMessage(self, cmdobj=self.availableCommands['open'])
        self.outMessages[msg.msgUUID] = self.outMsg(time.time(), self.devices[1].deviceUUID, msg)
        
    
    def stop(self):
        """
        Stop sending messages.  Other components are unable to receive
        messages.  Queue up or pause functionality.
        """
        pass
    
    def unload(self):
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
        
        
            
            
