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
    def get_device_types(self, always_load=None):
        if always_load is None:
            always_load = False

        if always_load == True:
            records = yield self.dbconfig.select("device_types", where=["always_load = ?", 1])
            return records
        elif always_load is False:
            records = yield self.dbconfig.select("device_types", where=["always_load = ? OR always_load = ?", 1, 0])
            return records
        else:
            return []

    @inlineCallbacks
    def get_module_device_types(self, module_id):
        results = yield ModuleDeviceTypesView.find(where=["module_id = ?", module_id])
        records = []
        for item in results:
            temp = clean_dict(item.__dict__)
            del temp["errors"]
            records.append(temp)
        return records

    @inlineCallbacks
    def get_device_type(self, devicetype_id):
        records = yield DeviceType.find(where=["id = ?", devicetype_id])
        return records

    @inlineCallbacks
    def get_addable_device_types(self):
        records = yield self.dbconfig.select("addable_device_types_view")
        return records

    @inlineCallbacks
    def get_device_type_commands(self, device_type_id):
        """
        Gets available variables for a given device_id.

        Called by: library.Devices::_init_

        :param variable_type:
        :param foreign_id:
        :return:
        """
        records = yield DeviceTypeCommand.find(
            where=["device_type_id = ?", device_type_id])
        commands = []
        for record in records:
            if record.command_id not in commands:
                commands.append(record.command_id)

        return commands
