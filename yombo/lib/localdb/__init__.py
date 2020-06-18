# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Add database support to the Yombo gateway.
A database API to SQLite3.

.. warning::

   These functions, variables, and classes **should not** be accessed directly
   by modules. These are documented here for completeness. Use (or create) a
   :ref:`utils <utils>` function to get what is needed.

.. note::

  * For library documentation, see: `LocalDB @ Library Documentation <https://yombo.net/docs/libraries/localdb>`_

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/localdb/__init__.html>`_
"""
# Import python libraries
from time import time
from typing import Any, ClassVar, Dict, Optional, Type

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.mixins.database_mixin import DatabaseMixin
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.lib.localdb.library_support import LibrarySupport
from yombo.utils.hookinvoke import global_invoke_libraries

logger = get_logger("library.localdb")


class LocalDB(YomboLibrary, DatabaseMixin, LibrarySupport):
    """
    Manages all database interactions.
    """
    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Check to make sure the database exists. Will create if missing, will also update schema if any
        changes are required.
        """
        # These tables are represent the data retrieved from Yombo API tables. This list of tables
        # is used by the system data handler to sync from Yombo API to these tables.
        self.yombo_api_tables = ['categories', 'commands', 'devices', 'device_command_inputs',
                                 'device_commands', 'device_types', 'device_type_commands', 'gateways', 'input_types',
                                 'locations', 'modules', 'module_commits', 'module_device_types', 'nodes', 'users',
                                 'variable_groups', 'variable_fields', 'variable_data']

        # For sqlite, set type to sqlite and set the path to the database file.
        self.database_type = self._Configs.get("database.type", "sqlite")

        self.database_path = self._Configs.get("database.path", f"{self._working_dir}/etc/yombo.sqlite3")
        self.database_migration_path = f"{self._app_dir}/yombo/lib/localdb/migrations/sql/{self.database_type}"
        yield self.setup_database_connection()

        # used to cache data tables lookups for the webinterface viewers
        self.event_counts = self._Cache.ttl(ttl=15, tags="events")
        self.storage_counts = self._Cache.ttl(ttl=15, tags="storage")
        self.webinterface_counts = self._Cache.ttl(ttl=15, tags="web_logs")

        yield global_invoke_libraries("_storage_setup_db_columns_", called_by=self)

        # Perform DB cleanup activites based on local section.
        if self._Configs.get("database.purge_sqlidicts", False) is True:
            self.truncate("sqldicts")
            self._Configs.set("database.purge_sqlidicts", False)

        if self._Configs.get("database.purge_device_states", False) is True:
            self.truncate("device_states")
            self._Configs.set("database.purge_device_states", False)

    @inlineCallbacks
    def get_ids_for_yombo_api_tables(self):
        """
        Gets all the IDS for all tables that are remotely managed.

        :return:
        """
        ids = {}
        current_time = int(time())
        for table in self.yombo_api_tables:
            ids[table] = {}
            columns = "id"
            # print(f"db_model: {self.db_model[table]}")
            if "updated_at" in self.db_model[table]:
                columns += ", updated_at"
            table_ids = yield self.database.db_select(table, columns=columns)
            for item in table_ids:
                if "updated_at" in self.db_model[table]:
                    ids[table][item['id']] = item['updated_at']
                else:
                    ids[table][item['id']] = current_time
        return ids
