"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.lib.localdb import Command


class DB_Commands(object):

    @inlineCallbacks
    def get_commands(self):
        records = yield Command.find(orderby="label ASC")
        return records

    @inlineCallbacks
    def save_commands(self, data):
        """
        Attempts to find the provided command in the database. If it's found, it's updated. Otherwise, a new
        one is created.

        :param data: A command instance.
        :return:
        """
        command = yield Command.find(data.command_id)
        if command is None:  # If none is found, create a new one.
            command = Command()
            command.id = data.command_id

        for field in self.db_fields("commands"):
            setattr(command, field, getattr(data, field))

        yield command.save()
