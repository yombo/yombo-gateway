# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Queues @ Library Documentation <https://yombo.net/docs/libraries/queues>`_

This library implements a modified version of a queue developed by Terry Jones
( http://blogs.fluidinfo.com/terry/2011/06/27/a-resizable-dispatch-queue-for-twisted/ ).

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/queue.html>`_
"""
import traceback
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import Deferred, DeferredList, inlineCallbacks, maybeDeferred

#Import third party extensions
from yombo.ext.txrdq.rdq import ResizableDispatchQueue

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import collections

logger = get_logger("library.queue")


class Queue(YomboLibrary):
    """
    Allows libraries and modules to implement a FIFO queue with various features. See 
    `Queues @ command Development <https://yombo.net/docs/libraries/queues>`_ for full usage.
    """
    queues: ClassVar[dict] = {}

    def _stop_(self, **kwargs):
        self.unload_deferred = Deferred()
        to_stop = []
        try:
            for name, queue in self.queues.items():
                queue_size = queue.size()
                if queue.stopped is True:
                    print("queue stopped")
                    continue
                if queue_size[0] == 0 and queue_size[1] == 0:
                    continue
                to_stop.append(queue.stop())
            if len(to_stop) > 0:
                logger.info("Stopping queues. Waiting for in-flight jobs to finish.")
                dl = DeferredList(to_stop)
                dl.addCallback(self.unload_deferred.callback)
                # self.unload_deferred.callback(1)
                return self.unload_deferred

        except Exception as e:
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.format_exc())
            logger.error("--------------------------------------------------------")

    @inlineCallbacks
    def run_job(self, func, *args, **kwargs):
        results = yield maybeDeferred(func, *args, **args)
        return results

    def new(self, name, worker_callback, width=None, size=None, save_on_exit=None):
        """
        Create a new queue. Returns the queue itself so that various operations can be
        performed such as pause, resume, stop, etc.

        :param name: A unique name for the queue. Usually: "module.modulename.queuename"
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
