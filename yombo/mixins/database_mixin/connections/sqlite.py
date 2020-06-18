"""
Adds support for the SQLite database type.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/localdb/connections/sqlite.html>`_
"""
from os.path import isfile, join
from time import time
from typing import Any, Callable, ClassVar, Dict, List, Type, Optional, Union

from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks
from twisted.internet.utils import getProcessOutput

from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.database_mixin.connections.sqlbase import SQLBase

logger = get_logger("mixins.database_mixin.connections.sqlite")


class SQLiteDB(SQLBase):
    """
    Modifications from SQLBase for SQLite specific items.
    """
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.variable_placeholder: ClassVar[str] = "?"

    @inlineCallbacks
    def db_migrate_pre(self):
        """Do actions before migration."""
        yield self.run_operation("PRAGMA synchronous=0;")

    @inlineCallbacks
    def db_migrate_post(self) -> None:
        """Do actions before migration. Setup sync to 2, and chmod to databse to 600 for security."""
        yield self.run_operation("PRAGMA synchronous=2;")
        yield self._Files.chmod(self._Parent.database_path, 0o600)

    def db_cleanup_post_process(self, **kwargs):
        """ Do any activities to cleanup the database. """
        return self.run_operation("VACUUM")

    @property
    def connection_string(self) -> str:
        """ Connection string to pass to twisted adbapi. """
        return f"sqlite:///{self._Parent.database_path}"

    @inlineCallbacks
    def db_connect_to_pool(self) -> None:
        """
        Connects to the SQLite database and sets the self.db_pool to the adbapi connection pool.
        :return:
        """
        try:
            logger.debug("sqlite::db_connect_to_pool:: {path}", path=self._Parent.database_path)
            self.db_pool = adbapi.ConnectionPool("sqlite3",
                                                 self._Parent.database_path,
                                                 check_same_thread=False,
                                                 cp_min=1,
                                                 cp_max=1
                                                 )
        except Exception as e:
            raise YomboWarning(f"Error connecting to sqlite database: {e}")

        yield self.run_operation("PRAGMA synchronous=2;")

    def db_optimize(self) -> None:
        """
        Rebuild the sqlite database file. For details: http://www.sqlitetutorial.net/sqlite-vacuum/
        :return:
        """
        return self.run_operation("VACUUM")

    @inlineCallbacks
    def db_list_tables(self) -> List[str]:
        """
        Gets a list of all tables within the database.
        :return:
        """
        tables = yield self.db_select("sqlite_master", columns="tbl_name", where=["type = ?", "table"])
        return [e["tbl_name"] for e in tables]

    def db_list_table_columns(self, table_name: str) -> List[str]:
        """
        Gets a list of all tables within the database.

        :param table_name: The database table to get rows from
        :return:
        """
        return self.db_select(f"PRAGMA_TABLE_INFO('{table_name}')", columns="name, type, `notnull`")

    @inlineCallbacks
    def make_backup(self):
        """
        Makes a backup of the database file. This only keeps 20 backups and typically only happens once a day.

        :return:
        """
        start_time = time()
        db_file = self._Atoms.get("working_dir") + "/etc/yombo.sqlite3"
        db_backup_path = self._Atoms.get("working_dir") + "/bak/db/"
        directory_files = yield self._Files.listdir(db_backup_path)
        if directory_files is not None:
            db_backup_files = [f for f in directory_files if isfile(join(db_backup_path, f))]
            start_time = time()
            for i in range(20, -1, -1):  # reversed range
                current_backup_file_name = f"yombo.sqlite3.{i}"
                if current_backup_file_name in db_backup_files:
                    if i == 20:
                        yield self._Files.delete_file(db_backup_path + current_backup_file_name)
                    else:
                        next_backup_file_name = f"yombo.sqlite3.{str(i + 1)}"
                        yield self._Files.move_file(db_backup_path + current_backup_file_name, db_backup_path + next_backup_file_name)

        yield getProcessOutput("sqlite3", [db_file, f".backup {db_backup_path}yombo.sqlite3.1"])
        self._Events.new(event_type="localdb",
                         event_subtype="dbbackup",
                         attributes=time() - start_time,
                         request_by="localdb",
                         request_by_type="library")
