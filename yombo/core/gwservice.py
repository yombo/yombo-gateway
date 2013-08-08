#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
This is the main class the is responsible for getting everything started.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""

from twisted.internet import reactor
from twisted.application.service import Service

from yombo.lib.loader import getLoader, stopLoader, setupLoader
from yombo.core.log import getLogger

logger = getLogger('core.gwservice')

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
        self.loaderCallID = reactor.callWhenRunning(setupLoader)
        self.loaderCallID2 = reactor.callWhenRunning(self.getLoader)

    def startService(self):
        """
        Get the service started.  Shouldn't be called by anyone!
        """
        Service.startService(self)

    def getLoader(self):
        """
        Get the loader class and then call it's load function. The
        loader's load function does all the actual work.
        """
        self.loader = getLoader()
        self.loader.load()
        self.loader.start()
        
    def stopService(self):
        """
        Stop the service, shouldn't be called by anyone!
        
        If the service needs to be stoped due to error, use an L{exceptions}.
        """
        logger.info("Yombo Gateway stopping.")
        stopLoader()
        logger.info("Yombo Gateway stopped.")
