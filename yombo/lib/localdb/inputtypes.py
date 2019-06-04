"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.lib.localdb import InputType


class DB_InputTypes(object):

    @inlineCallbacks
    def get_input_types(self):
        records = yield InputType.find(orderby="label ASC")
        return records

    @inlineCallbacks
    def save_input_types(self, data):
        """
        Attempts to find the provided input_type in the database. If it's found, it's updated. Otherwise, a new
        one is created.

        :param data: A input_type instance.
        :return:
        """
        input_type = yield InputType.find(data.input_type_id)
        if input_type is None:  # If none is found, create a new one.
            input_type = InputType()
            input_type.id = data.input_type_id

        for field in self.db_fields("input_types"):
            setattr(input_type, field, getattr(data, field))

        yield input_type.save()
