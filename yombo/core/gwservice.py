#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
This is the main class the is responsible for getting everything started.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2015 by Yombo.
:license: LICENSE for details.
"""
# Import twisted libraries
from twisted.internet import reactor
from twisted.application.service import Service
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.loader import get_loader, stop_loader, setup_loader
from yombo.core.log import get_logger

logger = get_logger('core.gwservice')

class GWService(Service):
    """
    Responsible for starting/stopping the entire service.
    """
    loader = None
   
    def start(self):
        """
        After twisted is running to get, call various starter functions
        to get everything started.
        """
        self.loaderCallID = reactor.callWhenRunning(setup_loader)
        self.loaderCallID2 = reactor.callWhenRunning(self.get_real_loader)

    def startService(self):
        """
        Get the service started.  Shouldn't be called by anyone!
        """
        Service.startService(self)

    @inlineCallbacks
    def get_real_loader(self):
        """
        Get the loader class and then call it's load function. The
        loader's load function does all the actual work.
        """
        self.loader = get_loader()
        yield self.loader.load()
        yield self.loader.start()
#        self.loader.connect()
        
    @inlineCallbacks
    def stopService(self):
        """
        Stop the service, shouldn't be called by anyone!
        
        If the service needs to be stoped due to error, use an L{exceptions}.
        """
        logger.info("Yombo Gateway stopping.")
        yield self.loader.unload()
        logger.info("Yombo Gateway stopped.")
