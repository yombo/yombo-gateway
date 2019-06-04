# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.ext.twistar.utils import dictToWhere
from yombo.lib.localdb import Device
# Import Yombo libraries
from yombo.utils import data_pickle, data_unpickle


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
        if len(records) > 0:
            for record in records:
                record = record.__dict__
                if record["energy_map"] is None:
                    record["energy_map"] = {"0.0": 0, "1.0": 0}
                else:
                    record["energy_map"] = data_unpickle(record["energy_map"], encoder="json")
        return records

    @inlineCallbacks
    def upsert_device(self, device, **kwargs):
        args = {
            "gateway_id": device.gateway_id,
            "device_type_id": device.device_type_id,
            "location_id": device.location_id,
            "area_id": device.area_id,
            "machine_label": device.machine_label,
            "label": device.label,
            "description": device.description,
            "notes": device.notes,
            "statistic_label": device.statistic_label,
            "statistic_lifetime": device.statistic_lifetime,
            # "data": device.data,
            # "attributes": device.attributes,
            "energy_type": device.energy_type,
            "energy_tracker_source": device.energy_tracker_source,
            "energy_tracker_device": device.energy_tracker_device,
            "energy_map": data_pickle(device.energy_map, encoder="json"),
            "controllable": device.controllable,
            "allow_direct_control": device.allow_direct_control,
            "controllable": device.controllable,
            "pin_required": device.pin_required,
            "pin_code": device.pin_code,
            "pin_timeout": device.pin_timeout,
            "status": device.status,
            "created_at": device.created_at,
            "updated_at": device.updated_at,
        }
        if device.is_in_db:
            # print(f"updating device db: {args}")
            results = yield self.dbconfig.update("devices", args, where=["id = ?", device.device_id])
        else:
            # print(f"inserting device into db: {args}")
            results = yield self.dbconfig.insert("devices", args)

        return results

    @inlineCallbacks
    def get_device_by_id(self, device_id, status=1):
        records = yield Device.find(where=["id = ? and status = ?", device_id, status])
        results = []
        for record in records:
            results.append(record.__dict__)  # we need a dictionary, not an object
        return results

    @inlineCallbacks
    def get_device_commands(self, where, **kwargs):
        limit = self._get_limit(**kwargs)
        records = yield self.dbconfig.select("device_commands",
                                             where=dictToWhere(where),
                                             orderby="created_at DESC",
                                             limit=limit)
        data = []
        for record in records:
            record["source"] = "database"
            record["inputs"] = data_unpickle(record["inputs"])
            record["history"] = data_unpickle(record["history"])
            data.append(record)
        return data
