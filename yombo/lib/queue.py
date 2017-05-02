# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Queues @ command Development <https://yombo.net/docs/modules/queues/>`_

A library to create simple work queues. Useful when you need a simple FIFO queue to handle lots of tasks.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
"""
import Queue
import traceback

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, DeferredQueue, maybeDeferred

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('library.queue')

class Queue(YomboLibrary):
    """
    Allows libraries and modules to implement a simple FIFO queue.
    """
    def _init_(self):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.queues = {}

    def _unload_(self):
        for name, work in self.workers.iteritems():
            self.workers[name]['running'] = False

    def new(self, name, worker_callback, workers = None):
        if name in self.queues:
            raise YomboWarning("'name' already exists in Queues.")
        if workers is None:
            workers = 1
        if callable(worker_callback) is False:
            raise YomboWarning("Invalid callable from queues.new...")

        self.queues[name] = YomboQueue(self, name, worker_callback, workers)
        return self.queues[name]


class YomboQueue(object):

    def __init__(self, parent, name, worker_callback, workers):
        self._Parent = parent
        self.name = name
        self.worker_callback = worker_callback
        self.workers = workers
        self.queue = DeferredQueue()
        self.running = True
        self.do_work()

    def width(self, workers = None):
        if workers is None:
            raise YomboWarning("Must set 'workers'.")
        self.workers = workers

    def put(self, worker_args = None, work_done_callback = None, done_args = None, description = None):
        if callable(work_done_callback) is False:
            raise YomboWarning("Invalid callable from queues.put...")
        if description is None:
            description = "No description."

        self.queue.put( Job(worker_args, work_done_callback, done_args, description) )

    @inlineCallbacks
    def do_work(self):
        while self.running:
            job = yield self.queue.get() # wait for a url from the queue
            try:
                # print "calling worker function: %s" % self.worker_callback
                # print "calling worker args: %s" % job.worker_args
                results = yield maybeDeferred(self.worker_callback, job.worker_args)
            except Exception as e:
                logger.error("Received error while calling worker function: {e}", e=e)
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.format_exc())
                logger.error("--------------------------------------------------------")
                return

            if job.work_done_callback is callable(job.work_done_callback):
                try:
                    yield maybeDeferred(job.work_done_callback, job.done_args, results)
                except Exception as e:
                    logger.error("Received error while calling worker done function: {e}", e=e)
                    logger.error("---------------==(Traceback)==--------------------------")
                    logger.error("{trace}", trace=traceback.format_exc())
                    logger.error("--------------------------------------------------------")


class Job(object):
    """
    A simple class to store extra data about a job.
    """
    def __init__(self, worker_args, work_done_callback, done_args, description):
        self.worker_args = worker_args
        self.work_done_callback = work_done_callback
        self.done_args = done_args
        self.description = description


