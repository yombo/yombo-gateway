"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from time import time
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.lib.localdb import Tasks
from yombo.utils import instance_properties, data_pickle, data_unpickle


class DB_SqlDict(object):

    @inlineCallbacks
    def get_sql_dict(self, component, dict_name):
        records = yield self.dbconfig.select("sqldict", select="dict_data",
                                             where=["component = ? AND dict_name = ?", component, dict_name])
        for record in records:
            try:
                before = len(record["dict_data"])
                record["dict_data"] = data_unpickle(record["dict_data"], "msgpack_base85_zip")
                # logger.debug("SQLDict Compression. With: {withcompress}, Without: {without}",
                #              without=len(record["dict_data"]), withcompress=before)
            except:
                pass
        return records

    @inlineCallbacks
    def set_sql_dict(self, component, dict_name, dict_data):
        """
        Used to save SQLDicts to the database. This is from a loopingcall as well as
        shutdown of the gateway.

        Called by: lib.Loader::save_sql_dict

        :param component: Module/Library that is storing the data.
        :param dictname: Name of the dictionary that is used within the module/library
        :param key1: Key
        :param data1: Data
        :return: None
        """
        dict_data = data_pickle(dict_data, "msgpack_base85_zip")

        args = {"component": component,
                "dict_name": dict_name,
                "dict_data": dict_data,
                "updated_at": int(time()),
                }
        records = yield self.dbconfig.select("sqldict", select="dict_name",
                                             where=["component = ? AND dict_name = ?", component, dict_name])
        if len(records) > 0:
            results = yield self.dbconfig.update("sqldict", args,
                                                 where=["component = ? AND dict_name = ?", component, dict_name])
        else:
            args["created_at"] = args["updated_at"]
            results = yield self.dbconfig.insert("sqldict", args, None, "OR IGNORE")
        return results
