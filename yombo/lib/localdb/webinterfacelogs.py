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
from yombo.lib.localdb import User
from yombo.utils import instance_properties, data_pickle, data_unpickle


class DB_WebinterfaceLogs(object):

    @inlineCallbacks
    def webinterface_save_logs(self, logs):
        yield self.dbconfig.insertMany("webinterface_logs", logs)

    @inlineCallbacks
    def search_webinterface_logs_for_datatables(self, order_column, order_direction, start, length, search=None):
        # print("search weblogs... order_column: %s, order_direction: %s, start: %s, length: %s, search:%s" %
        #       (order_column, order_direction, start, length, search))

        select_fields = [
            "request_at",
            '(CASE secure WHEN 1 THEN \'TLS/SSL\' ELSE \'Unsecure\' END || "<br>" || method || "<br>" || hostname || "<br>" || path) as request_info',
            # '(method || "<br>" || hostname || "<br>" || path) as request_info',
            "auth_id as user",
            '(ip || "<br>" || agent || "<br>" || referrer) as client_info',
            '(response_code || "<br>" || response_size) as response',
        ]

        if search in (None, ""):
            records = yield self.dbconfig.select(
                "webinterface_logs",
                select=", ".join(select_fields),
                limit=(length, start),
                orderby=f"{order_column} {order_direction}",
            )

            cache_name_total = "total"
            if cache_name_total in self.webinterface_counts:
                total_count = self.webinterface_counts[cache_name_total]
            else:
                total_count_results = yield self.dbconfig.select(
                    "webinterface_logs",
                    select="count(*) as count",
                )
                total_count = total_count_results[0]["count"]
                self.webinterface_counts[cache_name_total] = total_count
            return records, total_count, total_count

        else:
            where_fields = [f"request_at LIKE '%%{search}%%'",
                            f"request_protocol LIKE '%%{search}%%'",
                            f"referrer LIKE '%%{search}%%'",
                            f"agent LIKE '%%{search}%%'",
                            f"ip LIKE '%%{search}%%'",
                            f"hostname LIKE '%%{search}%%'",
                            f"method LIKE '%%{search}%%'",
                            f"path LIKE '%%{search}%%'",
                            f"secure LIKE '%%{search}%%'",
                            f"auth_id LIKE '%%{search}%%'",
                            f"response_code LIKE '%%{search}%%'",
                            f"response_size LIKE '%%{search}%%'"]

            if re.match("^[ \w-]+$", search) is None:
                raise YomboWarning("Invalid search string contents.")
            where_attrs_str = " OR ".join(where_fields)

            records = yield self.dbconfig.select(
                "webinterface_logs",
                select=", ".join(select_fields),
                where=[str(where_attrs_str)],
                limit=(length, start),
                orderby=f"{order_column} {order_direction}",
                debug=True
            )

            cache_name_total = "total"
            if cache_name_total in self.webinterface_counts:
                total_count = self.webinterface_counts[cache_name_total]
            else:
                total_count_results = yield self.dbconfig.select(
                    "webinterface_logs",
                    select="count(*) as count",
                )
                total_count = total_count_results[0]["count"]
                self.webinterface_counts[cache_name_total] = total_count

            cache_name_filtered = f"filtered {search}"
            if cache_name_filtered in self.webinterface_counts:
                filtered_count = self.webinterface_counts[cache_name_filtered]
            else:
                filtered_count_results = yield self.dbconfig.select(
                    "webinterface_logs",
                    select="count(*) as count",
                    where=[str(where_attrs_str)],
                    limit=(length, start),
                )
                filtered_count = filtered_count_results[0]["count"]
                self.webinterface_counts[cache_name_filtered] = filtered_count

            return records, total_count, filtered_count
