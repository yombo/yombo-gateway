# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `GW Service Core @ Module Development <https://yombo.net/docs/core/gwservice>`_

This is the main class the is responsible for getting everything started. This calls the loader
library which loads the rest of the system.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/gwservice.html>`_
"""
import multiprocessing
import sys
import traceback

# Import twisted libraries
from twisted.internet import reactor
from twisted.application.service import Service
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.loader import setup_loader
from yombo.core.log import get_logger
from yombo.utils import set_twisted_logger as set_twisted_logger_utils
from yombo.utils.decorators.deprecation import set_twisted_logger as set_twisted_logger_decorators


class GWService(Service):
    """
    Responsible for starting/stopping the entire Yombo Gateway service.  This is called from yombo.tac.
    """
    loader = None

    def start(self) -> None:
        """
        After twisted is running to get, call loader library and various starter functions
        to get everything started.
        """
        set_twisted_logger_utils(get_logger("utils"))
        set_twisted_logger_decorators(get_logger("utils"))

        # Threads are used for multiple items within the Yombo Gateway. They are used to prevent
        # blocking code and diverting some of the workload off the main thread to keep things
        # running more smooth.
        thread_count = multiprocessing.cpu_count() * 10
        if thread_count < 40:
            thread_count = 40
        reactor.suggestThreadPoolSize(thread_count)
        reactor.callWhenRunning(self.start_loader_library)

    def startService(self) -> None:
        """
        Get the service started.  Shouldn't be called by anyone other than yombo.tac.
        """
        Service.startService(self)

    @inlineCallbacks
    def start_loader_library(self):
        """
        Sets up the loader library and then start it.
        """
        try:
            self.loader = setup_loader()
        except Exception as e:
            print(f"Error starting the gateway: {e}")
            print("--------------------------------------------------------")
            print(f"{sys.exc_info()}")
            print("---------------==(Traceback)==--------------------------")
            print(f"{traceback.print_exc(file=sys.stdout)}")
            print("--------------------------------------------------------")

        yield self.loader.start_the_gateway()

    @inlineCallbacks
    def stopService(self):
        """
        Stop the service, shouldn't be called by anyone!
        
        If the service needs to be stopped due to error, use an L{exceptions}.
        """
        print("Yombo Gateway stopping. (gwsvc-ss)")
        yield self.loader.unload()
