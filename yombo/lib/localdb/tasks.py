"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.lib.localdb import Tasks
from yombo.utils import instance_properties, data_pickle, data_unpickle


class DB_Tasks(object):

    @inlineCallbacks
    def get_tasks(self, section):
        """
        Get all tasks for a given section.

        :return:
        """
        records = yield Tasks.find(where=["run_section = ?", section])

        results = []
        for record in records:
            data = record.__dict__
            data["task_arguments"] = data_unpickle(data["task_arguments"], "msgpack_base85_zip")
            results.append(data)  # we need a dictionary, not an object
        return results

    @inlineCallbacks
    def del_task(self, id):
        """
        Delete a task id.

        :return:
        """
        records = yield self.dbconfig.delete("tasks", where=["id = ?", id])
        return records

    @inlineCallbacks
    def add_task(self, data):
        """
        Get all tasks for a given section.

        :return:
        """
        data["task_arguments"] = data_pickle(data["task_arguments"], "msgpack_base85_zip")
        results = yield self.dbconfig.insert("tasks", data, None, "OR IGNORE")
        return results
