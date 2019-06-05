# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.ext.twistar.utils import dictToWhere
from yombo.lib.localdb import Device
# Import Yombo libraries
from yombo.utils import data_pickle, data_unpickle

PICKLED_FIELDS = [
    "machine_state_extra", "energy_map"
]

class DB_Devices(object):

    @inlineCallbacks
    def get_devices(self, status=None):
        if status == True:
            records = yield Device.find(orderby="label ASC")
        #            return records
        elif status is None:
            records = yield Device.find(where=["status = ? OR status = ?", 1, 0], orderby="label ASC")
        else:
            records = yield Device.find(where=["status = ? ", status], orderby="label ASC")
        if records is None:
            return []

        for record in records:
            record = record.__dict__
            if record["energy_map"] is None:
                record["energy_map"] = {"0.0": 0, "1.0": 0}
            else:
                try:
                    record["energy_map"] = data_unpickle(record["energy_map"], encoder="json")
                except:
                    record["energy_map"] = {"0.0": 0, "1.0": 0}
        return records

    @inlineCallbacks
    def save_devices(self, data):
        """
        Attempts to find the provided device in the database. If it's found, update it. Otherwise, a new
        one is created.

        :param data: A device state instance.
        :return:
        """
        device = yield Device.find(data.device_id)
        if device is None:  # If none is found, create a new one.
            device = Device()
            device.id = data.device_id

        fields = self.get_table_fields("devices")
        for field in fields:
            if field in PICKLED_FIELDS:
                setattr(device, field, data_pickle(getattr(data, field), encoder="json"))
            else:
                setattr(device, field, getattr(data, field))
        results = yield device.save()
        new_device = yield Device.find("aWpBzyrK0WQUZwgdvmZ4")
