"""
Defines a simple, and nearly empty starter module.  This module
requests the Times_ library to display various times on startup.

:copyright: 2012 Yombo
:license: GPL
"""
from twisted.internet import reactor

from yombo.core.module import YomboModule
from yombo.core.helpers import getTimes
from yombo.core.log import getLogger

logger = getLogger("module.empty")

class Empty(YomboModule):
    """
    Empty base module
    """

    def _init_(self):
        """
        Init the module.  Don't use __init__ as that will override the
        setup functions of the base YomboModule class.
        
        Startup phase 1 of 3.
        """
        self._ModDescription = "Empty module, copy to get started building a new module."
        self._ModAuthor = "Mitch Schwenk @ Yombo"
        self._ModUrl = "http://www.yombo.net"

        # get a reference to the times instance so we can check ifDark later.
        self.times = getTimes()
        
    def _load_(self):
        """
        After this phase, module should be able to
        processing incoming messages.
        
        In this example, we call the self.loaded function after 2 seconds.
        This load function doesn't really do anything.
        
        Startup phase 2 of 3.
        """
        logger.debug("Empty module is loading.")
        if self._ModVariables != {}:
            logger.info("Empty module has the following module variables:")
            for variable in self._ModVariables:
                # Remember, each variable can be multi-valued. Internally,
                # variables are treated the same if allowed to hav multiple
                # values or not. Hence the [0]
                logging.info("%s", self._ModVariables[variable][0])
        else:
            logger.debug("Empty module has no defined variables.")

        # an example to call a function at a later time. This example calles
        # self.loaded 2 seconds from now.
        reactor.callLater(2, self.loaded)

    def loaded(self):  #called from delayedcall
        """
        This method isn't required, but it's here for demonstation purposes.
        
        This is called from :meth:`load` 2 seconds after load was called.

        Due to asyncronous style of Twisted, the callLater cannot guarantee this
        is called exactly in two seconds.  It won't be called earlier, but may
        be called later if there was blocking code.
        """
        logger.debug("yombo.modules.empty.loaded() has been called.")
    
        
    def _start_(self):
        """
        Assume all other modules are loaded, we can start
        sending messages to other modules.  Here, is where we enable or turn on
        message sending from within our module.
        
        Startup phase 3 of 3.
        """
        logger.debug("Is Light: %s", self.times.isLight)
        logger.debug("Is Dark: %s", self.times.isDark)
        logger.debug("Is Day: %s", self.times.isDay)
        logger.debug("Is Night: %s", self.times.isNight)
        logger.debug("Mars Next Rise: %s", self.times.objRise(dayOffset=1, object='Mars'))
    
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
        pass
        
        
            
            
