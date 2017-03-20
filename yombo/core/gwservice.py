#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
This is the main class the is responsible for getting everything started.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import twisted libraries
from twisted.internet import reactor
from twisted.application.service import Service
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.loader import setup_loader
from yombo.core.log import get_logger

logger = get_logger('core.gwservice')

class GWService(Service):
    """
    Responsible for starting/stopping the entire Yombo Gateway service.  This is called from Yombo.tac.
    """
    loader = None
   
    def start(self):
        """
        After twisted is running to get, call loader library and various starter functions
        to get everything started.
        """
        reactor.callWhenRunning(self.start_loader_library)

    def startService(self):
        """
        Get the service started.  Shouldn't be called by anyone!
        """
        Service.startService(self)

    @inlineCallbacks
    def start_loader_library(self):
        """
        Sets up the loader library and then start it.
        """
        self.loader = setup_loader()
        yield self.loader.start()

    @inlineCallbacks
    def stopService(self):
        """
        Stop the service, shouldn't be called by anyone!
        
        If the service needs to be stoped due to error, use an L{exceptions}.
        """
        logger.info("Yombo Gateway stopping.")
        yield self.loader.unload()
