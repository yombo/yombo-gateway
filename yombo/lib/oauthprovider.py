# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `OAuth @ Library Documentation <https://yombo.net/docs/libraries/oauth>`_

Performs various tasks as needed. Usually used to run various processes at startup.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/oauthprovider.html>`_
"""
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger("library.tasks")


class Tasks(YomboLibrary):
    """
    Performs various tasks at startup.
    """
    @inlineCallbacks
    def _init_(self, **kwargs):
        self.loop_tasks = {}
        yield self.check_tasks("init")

    @inlineCallbacks
    def _load_(self, **kwargs):
        yield self.check_tasks("load")

    @inlineCallbacks
    def _start_(self, **kwargs):
        yield self.check_tasks("start")

    @inlineCallbacks
    def _stop_(self, **kwargs):
        if hasattr(self, "self._LocalDB"):  # incase loading got stuck somewhere.
            yield self.check_tasks("stop")

    @inlineCallbacks
    def _unload_(self, **kwargs):
        if hasattr(self, "self._LocalDB"):  # incase loading got stuck somewhere.
            yield self.check_tasks("load")

    @inlineCallbacks
    def check_tasks(self, section):
        tasks = yield self._LocalDB.get_tasks(section)
        for task in tasks:
            try:
                component = getattr(self, task["task_component"])
            except:
                print(f"Component not found: {task['task_component']}")
                continue

            try:
                method = getattr(component, "_process_task_")
                if task["run_interval"] > 0:
                    self.loop_tasks[task["id"]] = LoopingCall(method, task)
                    self.loop_tasks[task["id"]].start(task["run_interval"])
                else:
                    method(task)
            except:
                print(f"Component cannot process tasks: {task['task_component']}")
                continue

            if task["run_once"] == 1:
                self._LocalDB.del_task(task["id"])

    @inlineCallbacks
    def add_task(self, task):
        has_run_once = False
        new_task = []

        if "run_once" in task:
            has_run_once = True
            if task["run_once"] in(0, 1):
                new_task["run_once"] = task["run_once"]
            else:
                raise YomboWarning("run_once must be eitehr 0 or 1")
        else:
            new_task["run_once"] = 0

        if "run_interval" in task:
            if has_run_once is True:
                raise YomboWarning("run_once and run_interval cannot both be set.")

            if isinstance(task["run_interval"], int) is False:
                raise YomboWarning("run_interval must be an interger")
            if task["run_once"] < 0:
                raise YomboWarning("run_interval must be 0 or greater")
            new_task["run_interval"] = task["run_interval"]

        if "run_section" not in task:
            raise YomboWarning("run_section must be set.")
        new_task["run_section"] = task["run_section"]

        if "task_component" not in task:
            raise YomboWarning("task_component must be set.")
        new_task["task_component"] = task["task_component"]

        if "task_name" not in task:
            raise YomboWarning("task_name must be set.")
        new_task["task_name"] = task["task_name"]

        if "task_arguments" not in task:
            new_task["task_arguments"] = {}
        else:
            new_task["task_arguments"] = task["task_arguments"]

        if "task_name" not in task:
            raise YomboWarning("task_name must be set.")
        new_task["task_name"] = task["task_name"]

        if "source" not in task:
            raise YomboWarning("source must be set.")
        new_task["source"] = task["source"]

        new_task["create"] = int(time())

        yield self._LocalDB.add_task(new_task)