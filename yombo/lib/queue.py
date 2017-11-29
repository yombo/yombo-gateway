# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Queues @ command Development <https://yombo.net/docs/Libraries/Queues>`_

This library implements a modified version of a queue developed by Terry Jones
( http://blogs.fluidinfo.com/terry/2011/06/27/a-resizable-dispatch-queue-for-twisted/ ).

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/queue.html>`_
"""
import traceback

# Import twisted libraries
from twisted.internet.defer import Deferred, DeferredList

#Import third party extensions
from yombo.ext.txrdq.rdq import ResizableDispatchQueue

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import collections

logger = get_logger('library.queue')

class Queue(YomboLibrary):
    """
    Allows libraries and modules to implement a FIFO queue with various features. See 
    `Queues @ command Development <https://yombo.net/docs/modules/queues/>`_ for full usage.
    """
    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo queue library"

    def _init_(self, **kwargs):
        """
        Track all the queue created so we can gracefully shut them down.
        """
        self.queues = {}

    def _stop_(self, **kwargs):
        self.unload_deferred = Deferred()
        to_stop = []
        logger.info("Stopping queues. Waiting for in-flight jobs to finish.")
        try:
            for name, queue in self.queues.items():
                to_stop.append(queue.stop())
                if queue.stopped is True:
                    continue
                # print "stopping queue: %s " % name
                # print queue.size()
                # pending = queue.pending()
                # if len(pending) > 0:
                #     for job in pending:
                #         print "job in queue jobarg: %s" % job.__repr__()

            dl = DeferredList(to_stop)
            dl.addCallback(self.unload_deferred.callback)
            # self.unload_deferred.callback(1)
            return self.unload_deferred

        except Exception as e:
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.format_exc())
            logger.error("--------------------------------------------------------")

    def new(self, name, worker_callback, width=None, size=None, save_on_exit=None):
        """
        Create a new queue. Returns the queue itself so that various operations can be
        performed such as pause, resume, stop, etc.

        :param name: A unique name for the queue. Usually: 'module.modulename.queuename'
        :type name: str
        :param worker_callback: The callback to call when it's time to do work.
        :type worker_callback: callable
        :param width: How many callbacks can be running at the same time, default: 1
        :type width: int
        :param size: Max size of the queue.
        :type size: int or None for no limit
        :param save_on_exit: For futureu use: save queue on exit to be re-loaded on startup.
        :type save_on_exit: bool
        :return: A queue instance
        :rtype: object
        """
        if name in self.queues:
            raise YomboWarning("'name' already exists in Queues.")
        if width is None:
            width = 1
        if isinstance(worker_callback, collections.Callable) is False:
            raise YomboWarning("Invalid callable from queues.new...")

        self.queues[name] = ResizableDispatchQueue(worker_callback, width, size, name=name, save_on_exit=save_on_exit)
        return self.queues[name]
