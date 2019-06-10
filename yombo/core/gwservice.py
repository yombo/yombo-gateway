# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `GW Service Core @ Module Development <https://yombo.net/docs/core/gwservice>`_


This is the main class the is responsible for getting everything started. This calls the loader
library to get everything started.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/module.html>`_
"""
import multiprocessing

# Import twisted libraries
from twisted.internet import reactor
from twisted.application.service import Service
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.loader import setup_loader
from yombo.core.log import get_logger
from yombo.utils import set_twisted_logger as utils_logger
from yombo.utils.decorators.deprecation import set_twisted_logger as utils_decorators_logger

logger = get_logger("core.gwservice")

from os import getcwd
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
        # Threads are used for multiple items within the Yombo Gateway. They are used to prevent
        # blocking code. We need at least 40 threads to make things run smoothly.
        utils_logger(get_logger("utils"))
        utils_decorators_logger(get_logger("utils"))

        thread_count = multiprocessing.cpu_count() * 10
        if thread_count < 50:
            thread_count = 50
        reactor.suggestThreadPoolSize(thread_count)
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
        
        If the service needs to be stopped due to error, use an L{exceptions}.
        """
        logger.info("Yombo Gateway stopping.")
        yield self.loader.unload()
