"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.lib.localdb import DeviceCommandInput


class DB_DeviceCommandInputs(object):

    @inlineCallbacks
    def get_device_command_inputs(self):
        records = yield DeviceCommandInput.find(orderby="label ASC")
        return self._return_empty_if_none(records)

    @inlineCallbacks
    def save_device_command_inputs(self, data):
        """
        Attempts to find the provided device command input in the database. If it's found, it's updated. Otherwise,
        a new one is created.

        :param data: A device command input instance.
        :return:
        """
        dci = yield DeviceCommandInput.find(data.device_command_input_id)
        if dci is None:  # If none is found, create a new one.
            dci = DeviceCommandInput()
            dci.id = data.device_type_id

        for field in self.db_fields("device_command_inputs"):
            setattr(dci, field, getattr(data, field))

        yield dci.save()

    @inlineCallbacks
    def delete_device_command_inputs(self, data):
        """
        Attempts to find the provided device command input in the database and delete it.

        :param data: A device command input instance.
        :return:
        """
        dci = yield DeviceCommandInput.find(data.device_command_input_id)
        if dci is None:
            return None

        dci.delete()
        return True
