# Import python libraries
from time import time
import re

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
# Import 3rd-party libs
from yombo.ext.twistar.registry import Registry
from yombo.ext.twistar.utils import dictToWhere
from yombo.lib.localdb import Storage
from yombo.utils import clean_dict, data_pickle, data_unpickle, is_yes_no
from yombo.utils.datatypes import coerce_value

logger = get_logger("library.localdb.storage")


class DB_Storage(object):

    @inlineCallbacks
    def get_storage(self, storage_id):
        """
        Returns a db object representing the storage item.

        :param storage_id:
        :return:
        """
        record = yield Storage.find(storage_id)
        if record is None:
            raise KeyError(f"Storage not found in database: {storage_id}", errorno=8657)
        record.variables = data_unpickle(record.variables)
        return record

    @inlineCallbacks
    def get_expired_storage(self):
        """
        Get expired storage items.

        :param storage_id:
        :return:
        """
        records = yield Storage.find(where=["expires > 0 and expires < ?", int(time())], limit=50)
        for record in records:
            record.variables = data_unpickle(record.variables)
        return records

    @inlineCallbacks
    def save_storage(self, storage):
        # logger.debug("save_web_session: session.auth_id: {auth_id}", auth_id=session._auth_id)
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
            "variables": data_pickle(storage['variables']),
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
