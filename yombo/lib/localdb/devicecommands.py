"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.ext.twistar.utils import dictToWhere
from yombo.lib.localdb import DeviceCommand

# Import Yombo libraries
from yombo.utils import data_pickle, data_unpickle

PICKLED_FIELDS = [
    "history", "inputs"
]


class DB_DeviceCommands(object):

    @inlineCallbacks
    def get_device_commands(self):
        records = yield DeviceCommand.all(orderby="created_at DESC")
        for record in records:
            for pickled in PICKLED_FIELDS:
                setattr(record, pickled, data_unpickle(getattr(record, pickled)))
        return records

    @inlineCallbacks
    def save_device_commands(self, data):
        """
        Attempts to find the provided command in the database. If it's found, it's updated. Otherwise, a new
        one is created.

        :param data: A command instance.
        :return:
        """
        device_command = yield DeviceCommand.find(data.command_id)
        if device_command is None:  # If none is found, create a new one.
            device_command = DeviceCommand()
            device_command.request_id = data.request_id

        fields = self.get_table_fields("device_commands")
        for field in fields:
            if field in PICKLED_FIELDS:
                setattr(device_command, field, data_pickle(getattr(data, field)))
            else:
                setattr(device_command, field, getattr(data, field))

        yield device_command.save()
