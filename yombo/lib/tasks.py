# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Tasks @ Module Development <https://yombo.net/Docs/Libraries/Tasks>`_


Performs various tasks as needed. Usually used to run various processes at startup.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/tasks.html>`_
"""
from time import time
# Import twisted libraries
from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('library.tasks')

class Tasks(YomboLibrary):
    """
    Performs various tasks at startup.
    """
    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo tasks library"

    def _init_(self, **kwargs):
        self.loop_tasks = {}

        self.init_deffered = Deferred()
        self.check_tasks('init', self.init_deffered)
        return self.init_deffered

    def _load_(self, **kwargs):
        self.load_deferred = Deferred()
        self.check_tasks('load', self.load_deferred)
        return self.load_deferred

    def _start_(self, **kwargs):
        self.start_deferred = Deferred()
        self.check_tasks('start', self.start_deferred)
        return self.start_deferred

    def _stop_(self, **kwargs):
        if hasattr(self, 'self._LocalDB'):  # incase loading got stuck somewhere.
            self.stop_deferred = Deferred()
            self.check_tasks('stop', self.stop_deferred)
            return self.stop_deferred

    def _unload_(self, **kwargs):
        if hasattr(self, 'self._LocalDB'):  # incase loading got stuck somewhere.
            self.unload_deferred = Deferred()
            self.check_tasks('load', self.unload_deferred)
            return self.unload_deferred

    @inlineCallbacks
    def check_tasks(self, section, deferred):
        tasks = yield self._LocalDB.get_tasks(section)
        for task in tasks:
            try:
                component = getattr(self, task['task_component'])
            except:
                print("Component not found: %s" % task['task_component'])
                continue

            try:
                method = getattr(component, '_process_task_')
                if task['run_interval'] > 0:
                    self.loop_tasks[task['id']] = LoopingCall(method, task)
                    self.loop_tasks[task['id']].start(task['run_interval'])
                else:
                    method(task)
            except:
                print("Component cannot process tasks: %s" % task['task_component'])
                continue

            if task['run_once'] == 1:
                self._LocalDB.del_task(task['id'])
        deferred.callback(1)

    # def call_task(self, task):

    @inlineCallbacks
    def add_task(self, task):
        has_run_once = False
        new_task = []

        if 'run_once' in task:
            has_run_once = True
            if task['run_once'] in(0, 1):
                new_task['run_once'] = task['run_once']
            else:
                raise YomboWarning('run_once must be eitehr 0 or 1')
        else:
            new_task['run_once'] = 0

        if 'run_interval' in task:
            if has_run_once is True:
                raise YomboWarning("run_once and run_interval cannot both be set.")

            if isinstance(task['run_interval'], int) is False:
                raise YomboWarning('run_interval must be an interger')
            if task['run_once'] < 0:
                raise YomboWarning('run_interval must be 0 or greater')
            new_task['run_interval'] = task['run_interval']

        if 'run_section' not in task:
            raise YomboWarning("run_section must be set.")
        new_task['run_section'] = task['run_section']

        if 'task_component' not in task:
            raise YomboWarning("task_component must be set.")
        new_task['task_component'] = task['task_component']

        if 'task_name' not in task:
            raise YomboWarning("task_name must be set.")
        new_task['task_name'] = task['task_name']

        if 'task_arguments' not in task:
            new_task['task_arguments'] = {}
        else:
            new_task['task_arguments'] = task['task_arguments']

        if 'task_name' not in task:
            raise YomboWarning("task_name must be set.")
        new_task['task_name'] = kwargs['task_name']

        if 'source' not in task:
            raise YomboWarning("source must be set.")
        new_task['source'] = task['source']

        new_task['create'] = int(time())

        yield self._LocalDB.add_task(new_task)