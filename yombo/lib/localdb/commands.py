# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.ext.twistar.utils import dictToWhere
from yombo.lib.localdb import Device
# Import Yombo libraries
from yombo.utils import data_pickle, data_unpickle


class DB_Commands(object):

    @inlineCallbacks
    def get_commands(self):
        records = yield self.dbconfig.select("commands")
        return records
