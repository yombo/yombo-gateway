"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.lib.localdb import ModuleDeviceType


class DB_ModuleDeviceTypes(object):

    @inlineCallbacks
    def get_module_device_types(self):
        records = yield ModuleDeviceType.find()
        return self.process_get_results(records)

    @inlineCallbacks
    def save_module_device_types(self, data):
        """
        Attempts to find the provided module device type in the database. If it's found, it's updated. Otherwise, a new
        one is created.

        :param data: A module device type instance.
        :return:
        """
        module_device_type = yield ModuleDeviceType.find(data.input_type_id)
        if module_device_type is None:  # If none is found, create a new one.
            module_device_type = ModuleDeviceType()
            module_device_type.id = data.input_type_id

        for field in self.db_fields("module_device_types"):
            setattr(module_device_type, field, getattr(data, field))

        yield module_device_type.save()
