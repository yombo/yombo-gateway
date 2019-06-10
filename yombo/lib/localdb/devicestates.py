# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.ext.twistar.utils import dictToWhere
from yombo.lib.localdb import DeviceState

# Import Yombo libraries
from yombo.utils import data_pickle, data_unpickle

PICKLED_COLUMNS = [
    "machine_state_extra"
]


class DB_DevicesStates(object):

    @inlineCallbacks
    def get_device_states(self, where, **kwargs):
        limit = self._get_limit(**kwargs)

        records = yield DeviceState.find("device_states",
                                         where=dictToWhere(where),
                                         orderby="set_at DESC",
                                         limit=limit)
        return self.process_get_results(records, PICKLED_COLUMNS)

    @inlineCallbacks
    def save_device_states(self, data):
        """
        Attempts to find the provided device state in the database. If it's found, update it. Otherwise, a new
        one is created.

        :param data: A device state instance.
        :return:
        """
        device_command = yield DeviceState.find(data.command_id)
        if device_command is None:  # If none is found, create a new one.
            device_command = DeviceState()
            device_command.id = data.state_id

        fields = self.get_table_columns("device_states")
        print(f"device state fields: {fields}")
        print(f"data: {data.__dict__}")
        print(f"data: fake data: {data._fake_data}")
        for field in fields:
            if field in PICKLED_COLUMNS:
                setattr(device_command, field, data_pickle(getattr(data, field)))
            else:
                setattr(device_command, field, getattr(data, field))

        yield device_command.save()
