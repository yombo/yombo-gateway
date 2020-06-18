"""
Adds support for MySQL and MariaDB.

Currently, this database connection type is unsupported and untested.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/localdb/connections/mysql.html>`_
"""
# import pymysql
import sys
from typing import Any, ClassVar, Dict, List, Type, Optional, Union

from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks

# Yombo
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.database_mixin.connections.sqlbase import SQLBase

logger = get_logger("mixins.database_mixin.connections.sqlite")

class ReconnectingMySQLConnectionPool(adbapi.ConnectionPool):
    """
    This connection pool will reconnect if the server goes away.  This idea is from:
    http://www.gelens.org/2009/09/13/twisted-connectionpool-revisited/
    """
    def _runInteraction(self, interaction, *args, **kw):
        conn = self.connectionFactory(self)
        trans = self.transactionFactory(self, conn)
        try:
            result = interaction(trans, *args, **kw)
            trans.close()
            conn.commit()
            return result
        except Exception as e:
            conn = self.connections.get(self.threadID())
            self.disconnect(conn)
            conn = self.connectionFactory(self)
            trans = self.transactionFactory(self, conn)
            try:
                result = interaction(trans, *args, **kw)
                trans.close()
                conn.commit()
                return result
            except Exception as e:
                # print(f"Run interaction Exception: {e}")
                # excType, excValue, excTraceback = sys.exc_info()
                try:
                    conn.rollback()
                except Exception as e2:
                    # print("Run interaction Exception during rollback: %s" % e2)
                    logger.err(None, "Rollback failed")
                raise e
                # compat.reraise(excValue, excTraceback)


class MySQL(SQLBase):
    includeBlankInInsert = False

    def db_connect_to_pool(self) -> None:
        """
        Connects to the SQLite database and sets the self.db_pool to the adbapi connection pool.
        :return:
        """
        try:
            logger.debug("mysql::db_connect_to_pool:: {database_host}", database_host=self._Parent.database_host)
            self.db_pool = ReconnectingMySQLConnectionPool("MySQLdb",
                                                           user=self._Parent.database_user,
                                                           passwd=self._Parent.database_password,
                                                           db=self._Parent.database_db,
                                                           host=self._Parent.database_host,
                                                           # cp_reconnect=True,
                                                           cp_noisy=False,
                                                           )
        except Exception as e:
            raise YomboWarning(f"Error connecting to mysql/mariadb database: {e}")

    @inlineCallbacks
    def db_list_tables(self) -> List[str]:
        """
        Gets a list of all tables within the database.
        :return:
        """
        tables = yield self.run_query("show tables;")
        return [e[0] for e in tables]

    @inlineCallbacks
    def db_list_table_columns(self, table_name: str) -> List[str]:
        """
        Gets a list of all tables within the database.

        :param table_name: The database table to get rows from
        :return:
        """
        columns = yield self.run_query(f"describe {table_name}")
        results = []
        for column in columns:
            if column[0].lower() == "no":
                notnull = 0
            else:
                notnull = 1

            results.append({
                "name": column[0],
                "type": column[1],
                "notnull": notnull,
            })
        return results


class ReconnectingMySQLConnectionPool(adbapi.ConnectionPool):
    """
    This connection pool will reconnect if the server goes away.  This idea was taken from:
    http://www.gelens.org/2009/09/13/twisted-connectionpool-revisited/
    """
    def _runInteraction(self, interaction, *args, **kw):
        conn = self.connectionFactory(self)
        trans = self.transactionFactory(self, conn)
        try:
            result = interaction(trans, *args, **kw)
            trans.close()
            conn.commit()
            return result
        except Exception as e:
            conn = self.connections.get(self.threadID())
            self.disconnect(conn)
            conn = self.connectionFactory(self)
            trans = self.transactionFactory(self, conn)
            try:
                result = interaction(trans, *args, **kw)
                trans.close()
                conn.commit()
                return result
            except Exception as e:
                # print("Run interaction Exception: %s" % e)
                excType, excValue, excTraceback = sys.exc_info()
                try:
                    conn.rollback()
                except Exception as e2:
                    # print("Run interaction Exception during rollback: %s" % e2)
                    logger.error(None, "Rollback failed")
                raise e
                # compat.reraise(excValue, excTraceback)


