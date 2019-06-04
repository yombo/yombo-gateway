"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.lib.localdb import DeviceTypeCommand


class DB_DeviceTypeCommands(object):

    @inlineCallbacks
    def get_device_type_commands(self):
        records = yield DeviceTypeCommand.find()
        return records

    @inlineCallbacks
    def save_device_type_commands(self, data):
        """
        Attempts to find the provided input_type in the database. If it's found, it's updated. Otherwise, a new
        one is created.

        :param data: A input_type instance.
        :return:
        """
        device_type_command = yield DeviceTypeCommand.find(data.input_type_id)
        if device_type_command is None:  # If none is found, create a new one.
            device_type_command = DeviceTypeCommand()
            device_type_command.id = data.input_type_id

        for field in self.db_fields("device_type_commands"):
            setattr(device_type_command, field, getattr(data, field))

        yield device_type_command.save()
