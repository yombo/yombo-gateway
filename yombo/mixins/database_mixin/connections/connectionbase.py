"""
All database connection classes should directly inherit this class.

Adds core methods for handling database connections. See sqlbase and sqlite files for
working examples.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/localdb/connections/connectionbase.html>`_
"""
# Import python libraries
from copy import deepcopy
from typing import Any, Callable, ClassVar, Dict, List, Optional, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("mixins.database_mixin.connections.connectionbase")


class ConnectionBase(Entity):
    """
    Base class for all database connections.
    """
    def __init__(self, parent, *args, **kwargs):
        """
        Setup basic class attributes.
        """
        super().__init__(parent, *args, **kwargs)
        self._columns_cache: Dict[str, List[str]] = {}
        self.variable_placeholder: ClassVar[str] = "%s"
        self.db_cleanup_running: ClassVar[bool] = False
        self.db_pool: ClassVar = None

    def init(self) -> None:
        """ Setup the database connection. """
        raise NotImplemented

    def db_list_tables(self) -> List[str]:
        """
        Gets a list of all tables within the database.
        """
        raise NotImplemented

    def db_list_table_columns(self, table_name: str) -> List[str]:
        """
        Gets a list of all tables within the database.

        :param table_name: The database table to get rows from
        """
        raise NotImplemented

    @inlineCallbacks
    def db_generate_model(self) -> Dict[str, dict]:
        """
        Gets a dictionary or lists to represent all tables and their columns.

        :return:
        """
        tables = yield self.db_list_tables()
        results = {}
        for table in tables:
            columns = yield self.db_list_table_columns(table)
            results[table] = {}
            for column in columns:
                results[table][column["name"]] = {
                    "column": column["name"],
                    "type": column["type"],
                    "notnull": column["notnull"]
                }
        return results

    def db_cleanup(self, *args, **kwargs) -> None:
        """
        Performs any database optimization tasks. This is called periodically to remove old or stale data.

        :return:
        """
        pass

    def db_generic_item_get(self, library_reference, db_args, **kwargs):
        """
        A generic getter for accessing records from the database. the db_args allows callers
        to specify where, ordery, limit, and pickled_columns.

        :return:
        """
        raise NotImplemented("db_generic_item_get must be implemented by a child class.")

    @inlineCallbacks
    def db_generic_item_save(self, name, data):
        """
        This function interacts with the database to save a library item.

        :return:
        """
        raise NotImplemented("db_generic_item_save must be implemented by a child class.")

    @inlineCallbacks
    def db_generic_item_delete(self, name, data):
        """
        This function interacts with the database to delete an item.

        :return:
        """
        raise NotImplemented("db_generic_item_delete must be implemented by a child class.")

    def db_pickle_records(self, records: Union[list, dict], pickled_columns: Union[dict, list]) -> None:
        """
        Pickles record items according to pickled_columns.

        :param records: A list of dictionaries or a single dictionary to pickle.
        :param pickled_columns: List of dictionary of columns that are pickled.
        :return:
        """
        if records is None:
            raise YomboWarning("Unable to pickle records, input is None")

        if len(pickled_columns) == 0 or len(records) == 0:
            return records

        if isinstance(pickled_columns, list):
            temp_pickle = {}
            for key in pickled_columns:
                temp_pickle[key] = "msgpack_base85"
            pickled_columns = temp_pickle

        def do_pickle(columns):
            local_results = deepcopy(columns)
            for column, encoding in pickled_columns.items():
                if column in columns and columns[column] is not None:
                    local_results[column] = self._Tools.data_pickle(columns[column], encoding)
            return local_results

        if isinstance(records, dict):
            return do_pickle(records)
        else:
            results = []
            for record in records:
                results.append(do_pickle(record))
            return results

    # @classmethod
    # def db_unpickle_records(cls, records: Union[list, dict], pickled_columns: Union[dict, list]) -> None:
    #     """
    #     Un-pickles record items according to pickled_columns.
    #
    #     :param records: A list of dictionaries or a single dictionary to unpickle.
    #     :param pickled_columns: List of dictionary of columns that are pickled.
    #     :return:
    #     """
    #     if records is None:
    #         raise YomboWarning("Unable to unpickle records, input is None")
    #
    #     if len(pickled_columns) == 0 or len(records) == 0:
    #         return records
    #
    #     if isinstance(pickled_columns, list):
    #         temp_pickle = {}
    #         for key in pickled_columns:
    #             temp_pickle[key] = "msgpack_base85"
    #         pickled_columns = temp_pickle
    #
    #     def do_unpickle(columns):
    #         for column, encoding in pickled_columns.items():
    #             if column in columns and columns[column] is not None:
    #                 columns[column] = cls._Tools.data_unpickle(columns[column], encoding)
    #
    #     if isinstance(records, dict):
    #         do_unpickle(records)
    #     else:
    #         for record in records:
    #             do_unpickle(record)
    #     return records

    ########################
    # Basic SQL Operations #
    ########################
    def db_all(self, table, columns: Optional[str] = None):
        """
        Get all table items.

        :param table:
        :param columns: Which columns to select, default is '*'.
        :return:
        """
        results = yield self.db_select(table, columns=columns)
        yield results

    def db_delete(self, table: str, where: Optional[list] = None, row_id: Optional[str] = None):
        """
        Delete from the given table.

        :param table: Table to delete from.
        :param where: Conditional list.
        :param row_id: If provided, builds a where statement to include this id.
        :return: A Deferred.
        """
        raise NotImplemented("Delete function must be implemented by child class.")

    def db_delete_many(self, table: str, ids: list, id_column: Optional[str] = None):
        """
        Delete many values (id's) from table.

        :param table: Table to delete from.
        :param ids: Id's to delete
        :param id_column: Id column to use.
        :return: A Deferred.
        """
        raise NotImplemented("Delete many function must be implemented by child class.")

    def db_drop(self, table: str):
        """
        Drop a database table.

        :param table: Table to delete.
        :return: A Deferred.
        """
        raise NotImplemented("Drop many function must be implemented by child class.")

    def db_insert(self, table: str, values: dict, txn=None, prefix: Optional[str] = None):
        """
        Insert into table, the vals provided in vals.

        :param table: Table to insert a row into.
        :param vals: A dictionary or list of dictionaries of values to insert.
        :param txn: If txn is given it will be used for the query, otherwise a typical runQuery will be used
        :return: A Deferred that calls a callback with the id of new row.
        """
        raise NotImplemented("Insert function must be implemented by child class.")

    def db_select(self, table: str, columns: Optional[str] = None, where: Optional[Union[list, dict, str]] = None,
                  groupby: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None,
                  orderby: Optional[str] = None, row_id: Optional[str] = None):
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
        :param row_id: If provided, builds a where statement to include this id.

        :return: If limit is 1 or id is set, then one dictionary or None if not found is returned. Otherwiwse,
          a list of dictionaries are returned.
        """
        raise NotImplemented("Select function must be implemented by child class.")

    @classmethod
    def db_truncate(cls, table: str) -> None:
        """
        Truncate the given table.

        :param table: The database table to get rows from
        :return: A C{Deferred}.
        """
        raise NotImplemented("Truncate function must be implemented by child class.")

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
        raise NotImplemented("Update function must be implemented by child class.")

    def db_update_many(self, table: str, the_items: list, where_column: Optional[str] = None):
        """
        Update many rows into a given table.

        :param table: Table to update.
        :param the_items: The items to update.
        :param where_column: The column to use for update selection.
        :return: A Deferred
        """
        raise NotImplemented("Update many function must be implemented by child class.")

    #######
    # Various database interactions.
    #######
    @inlineCallbacks
    def run_interaction(self, interaction: Callable, *args, **kwargs):
        """
        Used to run an interaction against the database.

        :param interaction: The callable to use to run the interaction, for transactions.
        :param args: Arguments to send to interaction.
        :param kwargs: KWArgs to send to interaction.
        :return:
        """
        raise NotImplemented

    @inlineCallbacks
    def run_operation(self, query: str, *args, **kwargs):
        """
        Typically runs twisted.enterprise.dbapi.ConnectionPool.runOperation. However, can be used
        for any purpose needed.
        """
        raise NotImplemented

    @inlineCallbacks
    def execute_transaction(self, txn, query: str, *args, **kwargs):
        """
        Execute given query within the given transaction.

        :param txn: A transaction pointer
        :param query: Query string.
        :param args: Arguments to send to interaction.
        :param kwargs: KWArgs to send to interaction.
        """
        raise NotImplemented

    @staticmethod
    def get_last_insert_id(txn) -> int:
        """
        Using the given txn, get the id of the last inserted row.

        :return: The integer id of the last inserted row.
        """
        raise NotImplemented
