"""
Generic SQL functions.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/localdb/connections/mysql.html>`_
"""
from hashlib import sha224
import sys
from time import time
import traceback
from typing import Any, Callable, ClassVar, Dict, List, Type, Optional, Union
from yoyo import read_migrations, get_backend

from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, maybeDeferred

from yombo.core.log import get_logger
from yombo.core.exceptions import YomboWarning
from yombo.mixins.database_mixin.connections.connectionbase import ConnectionBase
from yombo.utils import sleep, bytes_to_unicode

logger = get_logger("mixins.database_mixin.connections.sqlbase")


class SQLBase(ConnectionBase):
    """
    Base class for all database connections.
    """
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.variable_placeholder: ClassVar[str] = "%s"

    @inlineCallbacks
    def init(self) -> None:
        """
        Setup the database. First, perform any migrations and then setup the connection pool.

        :return:
        """
        yield maybeDeferred(self.db_connect_to_pool)
        yield maybeDeferred(self.db_migrate)

    @property
    def connection_string(self) -> str:
        """ This must be implemented in the final class, such as SQLite or MySQL. """
        raise NotImplemented

    def db_migrate_pre(self):
        """Do actions before migration."""
        pass

    def db_migrate_post(self):
        """Do actions before migration."""
        pass

    @inlineCallbacks
    def db_migrate(self) -> None:
        """
        This runs all the database migrations against the database to ensure the tables are setup correctly.

        :return:
        """
        logger.debug("Checking Yombo database structure and performing migrations.")
        if hasattr(self._Parent, "database_migration_path") is False:
            return

        def migrate_now():
            backend = get_backend(self.connection_string)
            migrations = read_migrations(self._Parent.database_migration_path)
            with backend.lock():
                backend.apply_migrations(backend.to_apply(migrations))

        yield maybeDeferred(self.db_migrate_pre)
        yield threads.deferToThread(migrate_now)
        yield maybeDeferred(self.db_migrate_post)

    def db_connect_to_pool(self) -> None:
        raise NotImplemented

    ########################
    # Basic SQL Operations #
    ########################
    @inlineCallbacks
    def db_all(self, table, columns: Optional[str] = None):
        """
        Get all table items. This is a simple wrapper to the db_select() method.

        :param table:
        :param columns: Which columns to select, default is '*'.
        :return:
        """
        results = yield self.db_select(table, columns=columns)
        yield results

    @inlineCallbacks
    def db_delete(self, table: str, where: Optional[Union[list, dict, str]] = None, row_id: Optional[str] = None):
        """
        Delete item(s) from table.

        :param table: Table to delete from.
        :param row_id: If provided, builds a where statement to include this id.
        :param where: A list of arguments. The first item is a string for formatting, remaining items are the arguments.
        :return: A Deferred.
        """
        if row_id is not None:
            if where is None:
                where = [f"id = {self.variable_placeholder}", row_id]
            else:
                where = self.join_wheres(where, [f"id = {self.variable_placeholder}", row_id])

        query = f"DELETE FROM {table}"
        args = []
        if where is not None:
            wherestr, args = self.where_to_string(where)
            query += " WHERE " + wherestr

        results = yield self.run_operation(query, args)
        return results

    @inlineCallbacks
    def db_delete_many(self, table: str, ids: list, id_column: Optional[str] = None):
        """
        Delete many values (id's) from table.

        :param table: Table to delete from.
        :param ids: Id's to delete
        :param id_column: Id column to use.
        :return: A Deferred.
        """
        id_column = id_column if id_column is not None else "id"
        query = "DELETE FROM %s WHERE %s IN ('%s')" % (table, id_column, "', '".join(ids))
        # query = query.replace("= ?", f"= {self.variable_placeholder}")
        results = yield self.run_operation(query)
        return results

    @inlineCallbacks
    def db_drop(self, table: str):
        """
        Drop a database table.

        :param table: Table to drop (erase).
        :return: A Deferred.
        """
        results = yield self.run_operation(f"DROP TABLE {table}")
        return results

    @inlineCallbacks
    def db_insert(self, table: str, vals: Union[dict, List[dict]], txn=None, prefix: Optional[str] = None):
        """
        Insert into table, the vals provided in vals.

        yield self._LocalDB.database.db_insert("events", data)

        :param table: Table to insert a row into.
        :param vals: A dictionary or list of dictionaries of values to insert.
        :param txn: If txn is given it will be used for the query, otherwise a typical runQuery will be used
        :return: A Deferred that calls a callback with the id of new row.
        """
        if len(vals) == 0:
            logger.info("sql insert for table '{table}' received no values, skipping.", table=table)
            return

        params, values = self.create_insert_segments(vals)
        if params is None:
            logger.info("sql insert for table '{table}' has no values, skipping.", table=table)
            return

        if isinstance(vals, dict):
            escaped_colnames = self.escape_col_names(vals.keys())
        elif isinstance(vals, list):
            escaped_colnames = self.escape_col_names(vals[0].keys())

        colnames = "(" + ",".join(escaped_colnames) + ")"
        params = f"VALUES {params}"

        insert_prefix = ''
        if prefix is not None:
            insert_prefix = ' ' + prefix + ' '
        query = f"INSERT {insert_prefix} INTO {table} {colnames} {params}"

        # if we have a transaction use it
        if txn is not None:
            yield self.execute_transaction(txn, query, list(values))
            return self.get_last_insert_id(txn)

        def _insert(txn, query, vals):
            self.execute_transaction(txn, query, list(values))
            return self.get_last_insert_id(txn)

        results = yield self.run_interaction(_insert, query, vals)
        return results

    @inlineCallbacks
    def db_select(self, table: str, columns: Optional[str] = None, where: Optional[Union[list, dict, str]] = None,
                  groupby: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None,
                  orderby: Optional[str] = None, row_id: Optional[str] = None,
                  to_unicode: Optional[bool] = None):
        """
        Select table rows. This builds a select statement compatible with various SQL base databases.

        results = yield select("some_table", where=["label = ? AND status = ?", "mylabel", 1])

        :param table: The database table to get rows from
        :param columns: Which columns to select, default is '*'.
        :param where: A list of arguments. The first item is a string for formatting, remaining items are the arguments.
        :param groupby: AKA GROUP BY - A group by string.
        :param limit: Limit the number of results. If limit is 1, then results will be a single dictionary item,
          otherwise a list of dictionaries will be returned.
        :param offset: An int to offset, must be used with limit.
        :param orderby: String describing how to order the results.
        :param to_unicode: Coverts results to unicode. Default is True
        :param row_id: If provided, builds a where statement to include this id.

        :return: If limit is 1 or id is set, then one dictionary or None if not found is returned. Otherwiwse,
          a list of dictionaries are returned.
        """
        return_one = False
        columns = columns or "*"

        if row_id is not None:
            if where is None:
                where = [f"id = {self.variable_placeholder}", row_id]
            else:
                where = self.join_wheres(where, [f"id = {self.variable_placeholder}", row_id])
            return_one = True

        if not isinstance(limit, tuple) and limit is not None and int(limit) == 1:
            return_one = True

        query = f"SELECT {columns} FROM {table}"
        args = []
        if where is not None:
            where_string, args = self.where_to_string(where)
            query += " WHERE " + where_string
        if groupby is not None:
            query += " GROUP BY " + groupby
        if orderby is not None:
            query += " ORDER BY " + orderby

        if isinstance(limit, int):
            if isinstance(offset, int):
                query += f" LIMIT limit OFFSET offset"
        elif limit is not None:
            query += f" LIMIT limit"

        # print(f"sqlbase, select, query: {query} - {args}")
        cache_hash = sha224(f"{table}:{columns}".encode()).digest()
        results = yield self.run_interaction(self._do_select, query, args, return_one, cache_hash)
        if to_unicode is not False:
            return bytes_to_unicode(results)
        else:
            return results

    def _do_select(self, txn, query: str, args: list, return_one: bool, cache_hash: str):
        """
        Does the actual select in a transaction. This gets the raw database and then converts it to a more usable
        dictionary (or list of dictionaries if return_one is not True.

        :param txn: The db transaction
        :param query: Query string
        :param args: Arguments for the query string.
        :param return_one: If true, only return the first record.
        :param cache_hash: A string to be used for storing table column names.
        :return:
        """
        self.execute_transaction(txn, query, args)

        if return_one:
            result = txn.fetchone()
            if not result:
                return None
            vals = self.convert_to_dict(txn, result, cache_hash)
            return vals

        results = []
        for result in txn.fetchall():
            vals = self.convert_to_dict(txn, result, cache_hash)
            results.append(vals)
        return results

    def db_truncate(self, table: str):
        """
        Truncate the given table.

        :param table: The database table to get rows from
        :return: A C{Deferred}.
        """
        results = yield self.run_operation(f"DROP TABLE {table}")
        return results

    def update_args_to_string(self, args):
        """
        Convert dictionary of arguments to form needed for DB update query.  This method will
        vary by database driver.
        """
        colnames = self.escape_col_names(list(args.keys()))
        # setstring = ",".join([key + " = %s" for key in colnames])
        setstring = ",".join([key + f" = {self.variable_placeholder}" for key in colnames])
        return setstring, list(args.values())

    @inlineCallbacks
    def db_update(self, table: str, args: Dict[str, Any], where: list = None, txn=None,
                  limit: int = None, string_only=None):
        """
        Update a row into the given table.

        :param table: Table to update.
        :param args: Values to update.  Should be a dictionary in the form of
          {'name': value, 'othername': value}.
        :param where: Conditional of the same form as the where parameter nearly everywhere else.
        :param txn: If txn is given it will be used for the query, otherwise a typical runQuery will be used
        :param limit: If limit is given it will limit the number of rows that are updated.
        :return: A Deferred
        """
        set_string, args = self.update_args_to_string(args)
        query = f"UPDATE {table} SET {set_string} "
        if where is not None:
            wherestr, whereargs = self.where_to_string(where)
            query += " WHERE " + wherestr
            args += whereargs
        if limit is not None:
            query += " LIMIT " + str(limit)
        if string_only is True:
            return query

        # print(f"sqlbase: query: {query}")
        # print(f"sqlbase: args: {args}")
        if txn is not None:
            return self.execute_transaction(txn, query, args)
        results = yield self.run_operation(query, args)
        return results

    @inlineCallbacks
    def db_update_many(self, table: str, the_items: list, where_column: Optional[str] = None):
        """
        Update many rows into a given table.

        :param table: Table to update.
        :param the_items: The items to update.
        :param where_column: The column to use for update selection.
        :return: A Deferred
        """
        where_column = where_column or "id"

        for item in the_items:
            where = [f"{where_column} = {self.variable_placeholder}", item[where_column]]
            yield self.db_update(table, item, where)

    def db_backup(self) -> None:
        """
        Make a backup of the database. Each database connection is responsible for handling this request.

        :return:
        """
        pass

    #####################
    # Tools and helpers #
    #####################
    @inlineCallbacks
    def db_cleanup(self, *args, section=None, **kwargs):
        """
        Cleans out old data and optimizes the database.
        :return:
        """
        logger.info("db cleanup starting, section : {section}...", section=section)
        if self.db_cleanup_running is True:
            logger.info("Cleanup database already running.")
        self.db_cleanup_running = True

        if section is None:
            section = "all"
        timer = 0

        # Delete old device commands
        if section in ("device_commands", "all"):
            yield sleep(5)
            start_time = time()
            for device_command_id in list(self._DeviceCommands.device_commands.keys()):
                device_command = self._DeviceCommands.device_commands[device_command_id]
                if device_command.finished_at is not None:
                    if device_command.finished_at > start_time - 3600:  # keep 60 minutes worth.
                        found_dc = False
                        for device_id, device in self._Devices.devices.items():
                            if device_command_id in device.device_commands:
                                found_dc = True
                                break
                        if found_dc is False:
                            yield device_command.save_to_db()
                            del self._DeviceCommands.device_commands[device_command_id]
            yield self.db_delete("device_commands", where=[f"created_at < {self.variable_placeholder}",
                                                        time() - (86400 * 45)])
            timer += time() - start_time

        # Lets delete any device status after 90 days. Long term data should be in the statistics.
        if section in ("device_states", "all"):
            yield sleep(5)
            start_time = time()
            yield self.db_delete("device_states", where=[f"created_at < {self.variable_placeholder}",
                                                      time() - (86400 * 90)])
            timer += time() - start_time

        # Cleanup events.
        if section in ("events", "all"):
            yield sleep(5)
            for event_type, event_data in self._Events.event_types.items():
                for event_subtype, event_subdata in event_data.items():
                    if event_subdata["expires"] == 0:  # allow data collection for forever.
                        continue
                    yield sleep(1)  # There's no race
                    start_time = time()
                    results = yield self.db_delete(
                        "events",
                        where=[
                            f"event_type = {self.variable_placeholder} AND event_subtype = {self.variable_placeholder} AND "
                            f"created_at < {self.variable_placeholder}",
                            event_type, event_subtype, time() - (86400 * event_subdata["expires"])])
                    timer += time() - start_time

        # Clean notifications
        if section in ("notifications", "all"):
            yield sleep(5)
            start_time = time()
            for id in list(self._Notifications.notifications.keys()):
                if self._Notifications.notifications[id].expire_at == "Never":
                    continue
                if self._Notifications.notifications[id].expire_at is not None and \
                        start_time > self._Notifications.notifications[id].expire_at:
                    del self._Notifications.notifications[id]
            yield self.db_delete("notifications", where=[f"expire_at < {self.variable_placeholder}", time()])
            timer += time() - start_time

        # Clean states
        if section in ("states", "all"):
            yield sleep(5)
            # Delete unused states older than 1 year
            sql = f"DELETE FROM states WHERE updated_at < {int(time() - 31104000)}"
            start_time = time()
            yield self.db_pool.runQuery(sql)
            timer += time() - start_time
            #
            # yield sleep(5)
            # start_time = time()
            # sql = """DELETE FROM states WHERE id IN
            #       (SELECT id
            #        FROM states AS s
            #        WHERE s.id = states.id
            #        ORDER BY created_at DESC
            #        LIMIT -1 OFFSET 100)"""
            # yield self.db_pool.runQuery(sql)
            # timer += time() - start_time

        self._Events.new(event_type="localdb",
                         event_subtype="cleaning",
                         attributes=(section, timer),
                         _request_context=self._FullName,
                         _authentication=self._Parent.AUTH_USER
                         )

        if section == "all":
            yield sleep(5)
            if hasattr(self, "make_backup"):
                yield maybeDeferred(self.make_backup)
            yield sleep(10)
            if hasattr(self, "db_cleanup_post_process"):
                yield maybeDeferred(self.db_cleanup_post_process)
        self.db_cleanup_running = False

    @inlineCallbacks
    def db_generic_item_get(self, library_reference, db_args, **kwargs):
        """
        A generic getter for accessing records from the database. the db_args allows callers
        to specify where, ordery, limit, and pickled_columns.

        :return:
        """
        if "where" in db_args:
            where = db_args["where"]
        elif hasattr(library_reference, "_storage_default_where"):
            where = library_reference._storage_default_where
        else:
            where = None
        # if isinstance(where, dict):
        #     where_string, args = self.where_to_string(where)
        #     where = self.where_to_string(where)

        if "orderby" in db_args:
            orderby = db_args["orderby"]
        elif hasattr(library_reference, "_db_sort_key"):
            orderby = library_reference._storage_attribute_sort_key
        else:
            orderby = "id"
        if hasattr(library_reference, "_storage_attribute_sort_keyorder"):
            orderby = f"{orderby} {library_reference._storage_attribute_sort_keyorder}"
        else:
            orderby = f"{orderby} asc"

        if "limit" in kwargs:
            limit = self._get_limit(**db_args)
        else:
            limit = None

        records = yield self.db_select(library_reference._storage_attribute_name,
                                       where=where,
                                       orderby=orderby,
                                       limit=limit,
                                       )

        if records is None:
            return []
        return records

    def _get_limit(self, **kwargs):
        limit = kwargs.get("limit", None)
        offset = kwargs.get("offset", None)
        if limit is None:
            return None
        if offset is None:
            return limit
        else:
            return (limit, offset)

    # @inlineCallbacks
    # def db_generic_item_save(self, instance):
    #     """
    #     This function interacts with the database to save a library item.
    #
    #     :return:
    #     """
    #
    #     db_item = yield self.select(library_reference._storage_attribute_name, row_id=data._primary_field_id)
    #     if db_item is None:  # If none is found, create a new one.
    #         db_item.id = self._primary_field_id
    #
    #     columns = self.db_get_table_columns(library_reference._storage_attribute_name)
    #     for column in columns:
    #         if column in instance._storage_pickled_fields:
    #             setattr(db_item, column, data_pickle(getattr(data, column)))
    #         else:
    #             setattr(db_item, column, getattr(data, column))
    #
    #     yield db_item.db_save()
    #     return db_item

    # @inlineCallbacks
    # def db_generic_item_delete(self, name, data):
    #     """
    #     This function interacts with the database to delete an item.
    #
    #     :return:
    #     """
    #     attrs = GENERIC_ATTRIBUTES[name]
    #     # print(f"Saving generic items: {name}")
    #
    #     primary_id = getattr(data, attrs["primary_column_name"])
    #
    #     db_item = yield attrs["class"].find(primary_id)
    #     if db_item is not None:  # If found, delete it.
    #         yield db_item.delete()

    def convert_to_dict(self, txn, values: list, cache_hash: Optional[str] = None):
        """
        Converts a row (list) from a database query (select) into a dictionary.

        :param txn: The sql transaction.
        :param values: A row from a db.
        :param cache_hash: A sha256 hash key for the cache lookup.
        """
        if cache_hash is not None and cache_hash in self._columns_cache:
            columns_cache = self._columns_cache[cache_hash]
        else:
            columns_cache = [row[0] for row in txn.description]
            self._columns_cache[cache_hash] = columns_cache

        results = {}
        for index in list(range(len(values))):
            colname = columns_cache[index]
            results[colname] = values[index]
        return results

    def create_insert_segments(self, vals: Union[List[Dict[str, Any]], Dict[str, Any]]) -> Union[str, None]:
        """
        A helper function for "insert()". This converts a list of dictionaries or a single dictionary into
        soemthing that be used to insert into a database. For example:

        {"name": "value", "name2": "value2"} would return a string: (value, value2)

        :param vals: A dictionary or list of dictionaries of values to insert.
        """
        def generate_values(input):
            if len(input):
                return "(" + ",".join([self.variable_placeholder for _ in input.items()]) + ")"
            raise YomboWarning("sql insert has no values, skipping.")

        if isinstance(vals, dict):
            try:
                return generate_values(vals), list(vals.values())
            except YomboWarning:
                return None
        elif isinstance(vals, list):
            result_string = []
            result_values = []

            for val in vals:
                try:
                    result_string.append(generate_values(val))
                    result_values = result_values + list(val.values())
                except YomboWarning:
                    continue
            if len(result_string):
                return ", ".join(result_string), result_values
        return None

    def escape_col_names(self, colnames: List[str]) -> List[str]:
        """
        Escape column names for insertion into SQL statement.

        :param colnames: A list of string column names.
        :return: A list of string escaped column names.
        """
        return [f"`{x}`" for x in colnames]

    @staticmethod
    def join_wheres(one: list, two: list, operator: Optional[str] = "AND") -> list:
        """
        Joins to where lists together into one.

        :param one: Where list one
        :param two: Where list two
        :param operator: How to join the wheres, either AND or OR.
        :return: A list with one and two properly joined.
        """

        statement = [f"({one[0]}) {operator} ({two[0]})"]
        args = one[1:] + two[1:]
        return statement + args

    def where_to_string(self, where: Union[list, dict, str], operator: Optional[str] = None) -> str:
        """
        Accepts either a list or a dictionary and converts them to a string.

        Convert a conditional to the proper form required by the various DBAPI's. Most database APIs need it in '%s'.
        This function simply replaces all ?'s to %s.

        This function should be overridden needed by child classes.

        :param where: Standard conditional format of: where=["label = ? AND status = ?", 'mylabel', 1]
        :param operator: The operator to join where statements, default: AND
        """
        operator = operator or "AND"
        if isinstance(where, str):
            return where

        if isinstance(where, dict):
            if len(where) == 0:
                return ""

            columns = []
            values = []
            for column, where_input in where.items():
                if isinstance(where_input, list):
                    comparator = where_input[1]
                    value = where_input[0]
                else:
                    comparator = 'is' if where_input is None else '='
                    value = where_input
                columns.append(f"{column} {comparator} {self.variable_placeholder}")
                values.append(value)
            where = [f" {operator} ".join(list(columns))] + values

        query = where[0]
        query = query.replace(" ?", f" {self.variable_placeholder}")
        args = where[1:]
        # print(f"sqlbase, where_to_string: query: {query}")
        # print(f"sqlbase, where_to_string: args: {args}")
        return query, args

    # Database interactions.
    @inlineCallbacks
    def run_query(self, query):
        """
        Run a simple query within a transaction. Returns the results of the query.

        :param query: Query string to run.
        :return: A Deferred that returns None.
        """
        results = yield self.db_pool.runQuery(query)
        return results

    @inlineCallbacks
    def run_interaction(self, interaction: Callable, *args, **kwargs):
        """
        Runs an interaction using the db_pool.

        :param interaction: The callable to use to run the interaction, for transactions.
        :param args: Arguments to send to interaction.
        :param kwargs: KWArgs to send to interaction.
        :return:
        """
        try:
            results = yield self.db_pool.runInteraction(interaction, *args, **kwargs)
            return results
        except Exception as e:
            logger.error("-----------==(SQLite: run_interaction)==----------------")
            logger.error("{e}", e=e)
            logger.error("----------------==(call details)==----------------------")
            logger.error("interaction: {interaction}", interaction=interaction)
            logger.error("args: {args}", args=args)
            logger.error("kwargs: {kwargs}", kwargs=kwargs)
            logger.error("------------------==(Error)==---------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("----------------==(Traceback)==-------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")

    def run_operation(self, query: str, *args, **kwargs):
        """
        Simply makes same twisted.enterprise.dbapi.ConnectionPool.runOperation call.
        """
        try:
            results = self.db_pool.runOperation(query, *args, **kwargs)
            return results
        except Exception as e:
            logger.error("------------==(SQLite: run_operation)==-----------------")
            logger.error("{e}", e=e)
            logger.error("----------------==(call details)==----------------------")
            logger.error("interaction: {query}", query=query)
            logger.error("args: {args}", args=args)
            logger.error("kwargs: {kwargs}", kwargs=kwargs)
            logger.error("------------------==(Error)==---------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("----------------==(Traceback)==-------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")

    @inlineCallbacks
    def execute_transaction(self, txn, query: str, *args, **kwargs):
        """
        Execute given query within the given transaction.

        :param txn: A transaction pointer
        :param query: Query string.
        :param args: Arguments to send to interaction.
        :param kwargs: KWArgs to send to interaction.
        """
        try:
            results = yield txn.execute(query, *args, **kwargs)
            return results
        except Exception as e:
            logger.error("------------==(SQLite execute_transaction)==------------")
            logger.error("{e}", e=e)
            logger.error("----------------==(call details)==----------------------")
            logger.error("interaction: {query}", query=query)
            logger.error("args: {args}", args=args)
            logger.error("kwargs: {kwargs}", kwargs=kwargs)
            logger.error("------------------==(Error)==---------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("----------------==(Traceback)==-------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")

    @staticmethod
    def get_last_insert_id(txn) -> int:
        """
        Using the given txn, get the id of the last inserted row.

        :return: The integer id of the last inserted row.
        """
        return txn.lastrowid
