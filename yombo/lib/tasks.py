# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Tasks @ Library Documentation <https://yombo.net/docs/libraries/tasks>`_

Performs various tasks as needed. Usually used to run various processes at startup.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2017-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/tasks.html>`_
"""
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

logger = get_logger("library.tasks")


class Task(Entity, LibraryDBChildMixin):
    """
    Represent a single task.
    """
    _Entity_type: ClassVar[str] = "Task"
    _Entity_label_attribute: ClassVar[str] = "machine_label"


class Tasks(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages recurring tasks. Tasks are run during various startup/shutdown before and after modules are
    started and shurdown. These are not periodic tasks like CronTab.
    """
    tasks: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "task_id"
    _storage_attribute_name: ClassVar[str] = "tasks"
    _storage_label_name: ClassVar[str] = "task"
    _storage_class_reference: ClassVar = Task
    _storage_search_fields: ClassVar[str] = [
        "task_id", "label", "machine_label", "description", "run_once", "phase", "component",
        "function_name", "ars", "kwargs", "source"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "machine_label"

    @inlineCallbacks
    def _init_(self, **kwargs):
        yield self.load_from_database()
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
            yield self.check_tasks("unload")

    @inlineCallbacks
    def check_tasks(self, section):
        tasks = yield self.db_select(where={"run_section": section})
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