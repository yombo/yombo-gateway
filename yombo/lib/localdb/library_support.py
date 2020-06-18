"""
Adds support for various helper functions for sql type connections.

Todo: Redo the calling functions to remove these calls.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/localdb/connections/sqlbase.html>`_
"""
# Import python libraries
import re
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils.datatypes import coerce_value

logger = get_logger("library.localdb.sqlbase_libraries")


class LibrarySupport:

    @inlineCallbacks
    def save_storage(self, storage):
        args = {
            "id": storage["id"],
            "scheme": storage["scheme"],
            "username": storage["username"],
            "password": storage["password"],
            "netloc": storage["netloc"],
            "port": storage["port"],
            "path": storage["path"],
            "params": storage["params"],
            "query": storage["query"],
            "fragment": storage["fragment"],
            "mangle_id": storage["mangle_id"],
            "expires": storage["expires"],
            "public": coerce_value(storage["public"], "bool"),
            "internal_url": storage["internal_url"],
            "external_url": storage["external_url"],
            "internal_thumb_url": storage["internal_thumb_url"],
            "external_thumb_url": storage["external_thumb_url"],
            "content_type": storage["content_type"],
            "charset": storage["charset"],
            "size": storage["size"],
            "file_path": storage["file_path"],
            "file_path_thumb": storage["file_path_thumb"],
            "variables": self._Tools.data_pickle(storage['variables']),
            "created_at": storage["created_at"],
        }
        yield self.dbconfig.insert("storage", args)

    @inlineCallbacks
    def search_storage_for_datatables(self, order_column, order_direction, start, length, search=None):

        def format_records():
            """
            Format the results for display.

            :return:
            """
            output = []
            for record in records:
                # print(f"record: {record}")
                output.append({
                    "file_id": f'<a href="/storage/{record["id"]}/details">{record["id"]}</a>',
                    "mime_information":
                        f'{record["content_type"]}; {record["charset"]}<hr>'
                        f'Internal: <br><a href="{record["internal_url"]}">{record["internal_url"]}</a><br>&nbsp;<br>'
                        f'External: <br><a href="{record["external_url"]}">{record["external_url"]}</a>',
                    "thumbnail": f'<img src="{record["external_thumb_url"]}">',
                    "public": is_yes_no(record["public"]),
                    "created_at": record["created_at"],
                })
            return output

        if search in (None, ""):
            records = yield self.dbconfig.select(
                "storage",
                select="*",
                # where=["event_type = ? and event_subtype = ?", event_type, event_subtype],
                limit=(length, start),
                orderby=f"{order_column} {order_direction}",
            )

            if "total_count" in self.storage_counts:
                total_count = self.storage_counts["total_count"]
            else:
                total_count_results = yield self.dbconfig.select(
                    "storage",
                    select="count(*) as count",
                )
                total_count = total_count_results[0]["count"]
                self.storage_counts["total_count"] = total_count
            return format_records(), total_count, total_count

        else:
            if re.match("^[ \w-]+$", search) is None:
                raise YomboWarning("Invalid search string contents.")

            fields = ["id", "scheme", "netloc", "path", "params", "query", "fragment",
                      "mangle_id", "expires", "public", "internal_url", "external_url", "internal_thumb_url",
                      "external_thumb_url", "content_type", "charset", "file_path", "file_path_thumb", "created_at"]

            where_attrs = []
            for field in fields:
                where_attrs.append(f"attr{field} LIKE '%%{search}%%'")
            where_attrs_str = " OR ".join(where_attrs)

            records = yield self.dbconfig.select(
                "storage",
                select="*",
                where=[where_attrs_str],
                limit=(length, start),
                orderby="%s %s" % (order_column, order_direction),
            )

            if "total_count" in self.storage_counts:
                total_count = self.storage_counts["total_count"]
            else:
                total_count_results = yield self.dbconfig.select(
                    "storage",
                    select="count(*) as count",
                )
                total_count = total_count_results[0]["count"]
                self.storage_counts["total_count"] = total_count

            cache_name_filtered = f"filtered {search}"
            if cache_name_filtered in self.storage_counts:
                filtered_count = self.storage_counts[cache_name_filtered]
            else:
                filtered_count_results = yield self.dbconfig.select(
                    "storage",
                    select="count(*) as count",
                    where=[where_attrs_str],
                )
                filtered_count = filtered_count_results[0]["count"]
                self.storage_counts[cache_name_filtered] = filtered_count

            return format_records(), total_count, filtered_count

    @inlineCallbacks
    def search_events_for_datatables(self, event_type, event_subtype, order_column, order_direction, start,
                                     length, search=None):

        event_types = self._Events.event_types
        if event_type not in event_types:
            raise YomboWarning("Invalid event type")
        if event_subtype not in event_types[event_type]:
            raise YomboWarning("Invalid event subtype")

        event = event_types[event_type][event_subtype]
        attrs = []
        for i in range(1, len(event["attributes"]) + 1):
            attrs.append(f"attr{i} as {event['attributes'][i-1]}")
        fields = ["created_at", "priority", "source",  "auth_id as user"] + attrs
        if search in (None, ""):
            records = yield self.dbconfig.select(
                "events",
                select=", ".join(fields),
                where=["event_type = ? and event_subtype = ?", event_type, event_subtype],
                limit=(length, start),
                orderby=f"{order_column} {order_direction}",
            )

            cache_name_total = f"total {event_type}:{event_subtype}"
            if cache_name_total in self.event_counts:
                total_count = self.event_counts[cache_name_total]
            else:
                total_count_results = yield self.dbconfig.select(
                    "events",
                    select="count(*) as count",
                    where=["event_type = ? and event_subtype = ?", event_type, event_subtype],
                )
                total_count = total_count_results[0]["count"]
                self.event_counts[cache_name_total] = total_count
            return records, total_count, total_count

        else:
            if re.match("^[ \w-]+$", search) is None:
                raise YomboWarning("Invalid search string contents.")
            where_attrs = [f"source LIKE '%%{search}%%'", f"auth_id LIKE '%%{search}%%'"]
            for i in range(1, len(event["attributes"]) + 1):
                where_attrs.append(f"attr{i} LIKE '%%{search}%%'")
            where_attrs_str = " OR ".join(where_attrs)

            records = yield self.dbconfig.select(
                "events",
                select=", ".join(fields),
                where=[f"(event_type = ? and event_subtype = ?) and ({where_attrs_str})",
                       event_type, event_subtype],
                limit=(length, start),
                orderby="%s %s" % (order_column, order_direction),
            )

            cache_name_total = f"total {event_type}:{event_subtype}"
            if cache_name_total in self.event_counts:
                total_count = self.event_counts[cache_name_total]
            else:
                total_count_results = yield self.dbconfig.select(
                    "events",
                    select="count(*) as count",
                    where=["event_type = ? and event_subtype = ?", event_type, event_subtype],
                )
                total_count = total_count_results[0]["count"]
                self.event_counts[cache_name_total] = total_count

            cache_name_filtered = f"filtered {event_type}:{event_subtype}:{search}"
            if cache_name_filtered in self.event_counts:
                filtered_count = self.event_counts[cache_name_filtered]
            else:
                filtered_count_results = yield self.dbconfig.select(
                    "events",
                    select="count(*) as count",
                    where=[f"(event_type = ? and event_subtype = ?) and ({where_attrs_str})",
                           event_type, event_subtype],
                )
                filtered_count = filtered_count_results[0]["count"]
                self.event_counts[cache_name_filtered] = filtered_count

            return records, total_count, filtered_count

    @inlineCallbacks
    def get_distinct_stat_names(self, name=None, search_name_all=None, search_name_start=None,
                                search_name_end=None, bucket_type=None):
        where = {}
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

        records = yield self.datbase.db_select(
            "statistics",
            where=self.where_to_string(where),
            columns="bucket_name, bucket_type, bucket_size, bucket_lifetime, MIN(bucket_time) as bucket_time_min,"
                   " MAX(bucket_time) as bucket_time_max, count(*) as count",
            groupby="bucket_name")
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
        records = yield self.db_pool.runQuery(sql)
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
        stats = yield self.db_pool.runQuery(sql)
        results = {}
        for stat in stats:
            results[stat[0]] = stat[1]
        return results

    @inlineCallbacks
    def save_statistic_bulk(self, buckets):
        yield self._LocalDB.database.db_insert("statistics", buckets)
        return

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
            args["bucket_average_data"] = self._Tools.data_pickle(bucket["average_data"], separators=(",", ":"))

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
        stats = yield self.db_pool.runQuery(sql)
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
        anonymous_allowed = self._Configs.get("statistics.anonymous", True)
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
                    s[averagedata_name] = self._Tools.data_unpickle(s[averagedata_name])
        else:
            stats[averagedata_name] = self._Tools.data_unpickle(stats[averagedata_name])

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

############### Modules
    @inlineCallbacks
    def install_module(self, data):
        results = yield ModuleInstalled(module_id=data["module_id"],
                                        installed_branch=data["installed_branch"],
                                        installed_commit=data["installed_commit"],
                                        install_at=data["install_at"],
                                        last_check_at=data["last_check_at"],
                                        ).save()
        return results

    @inlineCallbacks
    def set_module_status(self, module_id, status):
        """
        Used to set the status of a module. Shouldn't be used by developers.
        Used to load a list of deviceType routing information.

        Called by: lib.Modules::enable, disable, and delete

        :param module_id: Id of the module to updates
        :type module_id: string
        :param status: Value to set the status field.
        :type status: int
        """

        modules = yield Modules.find(where=["id = ?", module_id])
        if modules is None:
            return None
        module = modules[0]
        module.status = status
        results = yield module.save()
        return results