# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Call Later @ Library Documentation <https://yombo.net/docs/libraries/calllater>`_

Tracks reactor callLater items. Primarily used for debugging and quickly creating callLater items without
having to import twisted reactor.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.25.0

:copyright: Copyright 2017-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/tasks.html>`_
"""
from random import randint
from time import time

# Import twisted libraries
from twisted.internet import reactor
# from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
# from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import random_string

logger = get_logger("library.callater")


class Calllater(YomboLibrary):
    """
    Tracks callLater calls.
    """
    def _init_(self, **kwargs):
        self.calllater = {}
        self.all_calls = reactor._delayedCalls  # used by the web interface to list all unregistered call later's.

        self.cleanup_expired_loop = LoopingCall(self.cleanup_expired)
        self.cleanup_expired_loop.start(randint(120, 180), False)

    def cleanup_expired(self):
        """
        Removed called/expired call later
        :return:
        """
        for calllater_id in list(self.calllater.keys()):
            task = self.calllater[calllater_id].task
            if task.active() is False:
                del self.calllater[calllater_id]

    def new(self, delay, func, *args, _task_description=None, **kwargs):
        """
        A wrapper around twisted's callLater. This keeps track of call later events for debugging.

        :param delay:
        :param func:
        :param args:
        :param _task_description:
        :param kw:
        :return:
        """
        calllater_id = random_string(length=12)
        self.calllater[calllater_id] = Call_Later(calllater_id, _task_description,
                                                  reactor.callLater(delay, func, *args, **kwargs),
                                                  func
                                                  )
        return self.calllater[calllater_id].task

    def cancel(self, calllater_id):
        """
        Stop/cancel a call later task.

        :param calllater_id:
        :return:
        """
        if calllater_id not in self.calllater:
            raise KeyError(f"'task_id' not found: {task_id}")

        task = self.calllater[calllater_id].task
        if task is not None and task.active():
            task.cancel()
        del self.calllater[calllater_id]


class Call_Later(object):
    def __init__(self, calllater_id, description, task, func):
        self.calllater_id = calllater_id
        self.description = description
        self.task = task
        self.created_at = time()
        self.func = func
