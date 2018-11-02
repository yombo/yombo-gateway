# Import python libraries
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.log import get_logger
# Import 3rd-party libs
from yombo.ext.twistar.registry import Registry
from yombo.ext.twistar.utils import dictToWhere
from yombo.lib.localdb import States
from yombo.utils import clean_dict

logger = get_logger("library.localdb.variables")


class DB_States(object):
    @inlineCallbacks
    def get_states(self, name=None):
        """
        Gets the last version of a state. Note: Only returns states that were set within the last 60 days.

        :param name:
        :return:
        """
        if name is not None:
            extra_where = f"AND name = {name}"
        else:
            extra_where = ""

        sql = """SELECT name, gateway_id, value, value_type, live, created_at, updated_at
    FROM states s1
    WHERE created_at = (SELECT MAX(created_at) from states s2 where s1.id = s2.id)
    %s
    AND created_at > %s
    GROUP BY name""" % (extra_where, str(int(time()) - 60 * 60 * 24 * 60))
        states = yield Registry.DBPOOL.runQuery(sql)
        results = []
        for state in states:
            results.append({
                "name": state[0],
                "gateway_id": state[1],
                "value": state[2],
                "value_type": state[3],
                "live": state[4],
                "created_at": state[5],
                "updated_at": state[6],
            })
        return results

    @inlineCallbacks
    def get_state_count(self, name=None, gateway_id=None):
        """
        Get a count of historical values for state

        :param name:
        :return:
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        count = yield States.count(where=["name = ? and gateway_id = ?", name, gateway_id])
        return count

    @inlineCallbacks
    def del_state(self, name=None, gateway_id=None):
        """
        Deletes all history of a state. (Deciding to implement)

        :param name:
        :return:
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        count = yield self.dbconfig.delete("states", where=["name = ? and gateway_id = ?", name, gateway_id])
        return count

    @inlineCallbacks
    def get_state_history(self, name, limit=None, offset=None, gateway_id=None):
        """
        Get an state history.

        :param name:
        :param limit:
        :param offset:
        :return:
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        if limit is None:
            limit = 1

        if offset is not None:
            limit = (limit, offset)

        where = {
            "name": name,
        }
        sql_where = dictToWhere(where)

        results = yield States.find(where=sql_where, limit=limit)
        records = []
        for item in results:
            temp = clean_dict(item.__dict__)
            del temp["errors"]
            records.append(temp)
        return records

    @inlineCallbacks
    def save_state(self, name, values):
        if values["live"] is True:
            live = 1
        else:
            live = 0

        if values["gateway_id"] == "local":
            return
        yield States(
            gateway_id=values["gateway_id"],
            name=name,
            value=values["value"],
            value_type=values["value_type"],
            live=live,
            created_at=values["created_at"],
            updated_at=values["updated_at"],
        ).save()

    @inlineCallbacks
    def save_state_bulk(self, states):
        results = yield self.dbconfig.insertMany("states", states)
        return results