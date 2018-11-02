# Import python libraries
import re

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning


class DB_Events(object):
    @inlineCallbacks
    def save_events_bulk(self, events):
        yield self.dbconfig.insertMany("events", events)

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
