# Import python libraries
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
# Import 3rd-party libs
from yombo.ext.twistar.registry import Registry
from yombo.ext.twistar.utils import dictToWhere
from yombo.lib.localdb import Statistics
from yombo.utils import data_pickle, data_unpickle

logger = get_logger("library.localdb.statistics")


class DB_Statistics(object):
    @inlineCallbacks
    def get_distinct_stat_names(self, name=None, search_name_all=None, search_name_start=None,
                                search_name_end=None, bucket_type=None):
        where = {}
        dictToWhere
        if bucket_type is not None:
            where["bucket_type"] = bucket_type
        if name is not None:
            where["bucket_name"] = name
        if search_name_all is not None:
            where["bucket_name"] = [f"%%{search_name_all}%%", "like"]
        if search_name_start is not None:
            where["bucket_name"] = [f"{search_name_start}%%", "like"]
        if search_name_end is not None:
            where["bucket_name"] = [f"%%{search_name_end}", "like"]

        records = yield self.dbconfig.select("statistics",
                                             where=dictToWhere(where),
                                             select="bucket_name, bucket_type, bucket_size, bucket_lifetime, MIN(bucket_time) as bucket_time_min, MAX(bucket_time) as bucket_time_max, count(*) as count",
                                             group="bucket_name")
        return records

    @inlineCallbacks
    def get_statistic(self, where):
        find_where = dictToWhere(where)
        records = yield Statistics.find(where=find_where)
        return records

    @inlineCallbacks
    def statistic_get_range(self, names, start, stop, minimal=None):
        if isinstance(names, list) is False:
            raise YomboWarning("statistic_get_range: names argument expects a list.")
        if isinstance(start, int) is False and isinstance(start, float) is False:
            raise YomboWarning(f"statistic_get_range: start argument expects an int or float, got: {start}")
        if isinstance(stop, int) is False and isinstance(stop, float) is False:
            # print("stop is typE: %s" % type(stop))
            raise YomboWarning(f"statistic_get_range: stop argument expects an int or float, got: {stop}")

        # names_str = ", ".join(map(str, names))
        names_str = ", ".join(f'"{w}"' for w in names)
        sql = """SELECT id, bucket_time, bucket_size, bucket_lifetime, bucket_type, bucket_name,
     bucket_value, bucket_average_data, anon, uploaded, finished, updated_at 
     FROM  statistics WHERE bucket_name in (%s) AND bucket_time >= %s
            AND bucket_time <= %s
            ORDER BY bucket_time""" % (names_str, start, stop)
        # print("statistic_get_range: %s" % sql)
        records = yield Registry.DBPOOL.runQuery(sql)
        results = []
        for record in records:
            if minimal in (None, False):
                results.append({
                    "id": record[0],
                    "bucket_time": record[1],
                    "bucket_size": record[2],
                    "bucket_lifetime": record[3],
                    "bucket_type": record[4],
                    "bucket_name": record[5],
                    "bucket_value": record[6],
                    "bucket_average_data": record[7],
                    "anon": record[8],
                    "uploaded": record[9],
                    "finished": record[10],
                    "updated_at": record[11],
                })
            else:
                results.append({
                    "id": record[0],
                    "bucket_time": record[1],
                    "bucket_size": record[2],
                    "bucket_lifetime": record[3],
                    "bucket_type": record[4],
                    "bucket_name": record[5],
                    "bucket_value": record[6],
                })

        return results

    @inlineCallbacks
    def get_stat_last_datapoints(self):
        sql = """SELECT s1.bucket_name, s1.bucket_value
    FROM  statistics s1
    INNER JOIN
    (
        SELECT Max(updated_at) updated_at, bucket_name
        FROM   statistics
        WHERE bucket_type = 'datapoint'
        GROUP BY bucket_name
    ) AS s2
        ON s1.bucket_name = s2.bucket_name
        AND s1.updated_at = s2.updated_at
    ORDER BY id desc"""
        stats = yield Registry.DBPOOL.runQuery(sql)
        results = {}
        for stat in stats:
            results[stat[0]] = stat[1]
        return results

    @inlineCallbacks
    def save_statistic_bulk(self, buckets):
        results = yield self.dbconfig.insertMany("statistics", buckets)
        return results

    @inlineCallbacks
    def save_statistic(self, bucket, finished=None):
        # print("save_statistic was called directly... sup?!")
        if finished is None:
            finished = False

        args = {"bucket_value": bucket["value"],
                "updated_at": int(time()),
                "anon": bucket["anon"],
                }

        if finished is not None:
            args["finished"] = finished
        else:
            args["finished"] = 0

        if bucket["type"] == "average":
            args["bucket_average_data"] = data_pickle(bucket["average_data"], separators=(",", ":"))

        if "restored_db_id" in bucket:
            results = yield self.dbconfig.update("statistics",
                                                 args,
                                                 where=["id = ?",
                                                        bucket["restored_db_id"]
                                                        ]
                                                 )
        else:
            args["bucket_time"] = bucket["time"]
            args["bucket_type"] = bucket["type"]
            args["bucket_name"] = bucket["bucket_name"]
            results = yield self.dbconfig.insert("statistics", args, None, "OR IGNORE")

        return results

    @inlineCallbacks
    def get_stat_last_records(self):
        #                  0            1             2         3            4                5             6
        sql = """SELECT bucket_type, bucket_time, bucket_name, id, bucket_size, bucket_lifetime, bucket_value,
        bucket_average_data, anon, uploaded, updated_at
        FROM  statistics
        WHERE bucket_time in (
        SELECT max(bucket_time) FROM statistics
        GROUP BY bucket_type, bucket_name
        )"""
        stats = yield Registry.DBPOOL.runQuery(sql)
        results = {}
        for stat in stats:
            if stat[0] not in results:
                results[stat[0]] = {}
            if stat[1] not in results[stat[0]]:
                results[stat[0]][stat[1]] = {}

            #        type     time      name
            results[stat[0]][stat[1]][stat[2]] = {
                "type": stat[0],
                "time": stat[1],
                "name": stat[2],
                "restored_from_db": True,
                "restored_db_id": stat[3],
                "size": stat[4],
                "lifetime": stat[5],
                "value": stat[6],
                "average_data": stat[7],
                "anon": stat[8],
                "uploaded": stat[9],
                "updated_at": stat[10],
                "touched": False
            }

        return results

    @inlineCallbacks
    def get_uploadable_statistics(self, uploaded_type=0):
        anonymous_allowed = self._Configs.get("statistics", "anonymous", True)
        if anonymous_allowed:
            records = yield self.dbconfig.select(
                "statistics",
                 select="id as stat_id, bucket_time, bucket_size, bucket_type, bucket_name, bucket_value, bucket_average_data, bucket_time",
                 where=["finished = 1 AND uploaded = ?", uploaded_type], limit=750)
        else:
            records = yield self.dbconfig.select(
                "statistics", select="*",
                where=["finished = 1 AND uploaded = ? and anon = 0", uploaded_type])

        self._unpickle_stats(records, "bucket_type", "bucket_average_data")

        return records

    @inlineCallbacks
    def set_uploaded_statistics(self, value, the_list):
        where_str = "id in (" + ", ".join(map(str, the_list)) + ")"
        yield self.dbconfig.update("statistics", {"updated_at": int(time()), "uploaded": value},
                                   where=[where_str])

    def _unpickle_stats(self, stats, type_name=None, averagedata_name=None):
        if averagedata_name is None:
            averagedata_name = "bucket_average_data"
        if type_name is None:
            type_name = "bucket_type"
        if isinstance(stats, list):
            for s in stats:
                if s[type_name] == "average":
                    s[averagedata_name] = data_unpickle(s[averagedata_name])
        else:
            stats[averagedata_name] = data_unpickle(stats[averagedata_name])

    @inlineCallbacks
    def get_stats_sums(self, bucket_name, bucket_type=None, bucket_size=None, time_start=None, time_end=None):
        if bucket_size is None:
            bucket_size = 3600

        wheres = []
        values = []

        wheres.append("(bucket_name = ?)")
        values.append(bucket_name)

        if bucket_type is not None:
            wheres.append("(bucket_type > ?)")
            values.append(time_start)

        if time_start is not None:
            wheres.append("(bucket > ?)")
            values.append(time_start)

        if time_end is not None:
            wheres.append("(bucket < ?)")
            values.append(time_end)
        where_final = [(" AND ").join(wheres)] + values

        # records = yield self.dbconfig.select("statistics",
        #             select="sum(value), bucket_name, bucket_type, round(bucket / 3600) * 3600 AS bucket",
        select_fields = f"sum(bucket_value) as value, bucket_name, bucket_type, round(bucket_time / {bucket_size}) * " \
                        f"{bucket_size} AS bucket"

        records = yield self.dbconfig.select("statistics",
                                             select=select_fields,
                                             where=where_final,
                                             group="bucket")
        return records
