# Import python libraries

# Import 3rd-party libs

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.log import get_logger
from yombo.lib.localdb import DeviceTypeCommand, ModuleDeviceTypesView, DeviceType
from yombo.utils import clean_dict

logger = get_logger("library.localdb.devicetypes")


class DB_DeviceTypes(object):
    @inlineCallbacks
    def get_device_types(self):
        records = yield DeviceType.find(orderby="label ASC")
        return records

    @inlineCallbacks
    def get_device_type(self, devicetype_id):
        records = yield DeviceType.find(where=["id = ?", devicetype_id])
        return records

    @inlineCallbacks
    def save_device_types(self, data):
        """
        Attempts to find the provided device_type in the database. If it's found, it's updated. Otherwise, a new
        one is created.

        :param data: A device_type instance.
        :return:
        """
        device_type = yield DeviceType.find(data.device_type_id)
        if device_type is None:  # If none is found, create a new one.
            device_type = DeviceType()
            device_type.id = data.device_type_id

        for field in self.db_fields("device_types"):
            setattr(device_type, field, getattr(data, field))

        yield device_type.save()

    @inlineCallbacks
    def get_addable_device_types(self):
        records = yield self.dbconfig.select("addable_device_types_view")
        return records
