"""
Create sqlite tables, base starting point.

Date created: 20190812

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/lib/localdb/migrations/sql/sqlite/20190812.start.html>`_
"""
from yoyo import step

from yombo.core.log import get_logger
from yombo.lib.localdb.migrations.sql.sql_20200325_initialize import migration_lines
from yombo.lib.localdb.migrations.sql import sqlite_convert_step_line

logger = get_logger("library.localdb.migrations.sql.sqlite")

logger.info("Creating new database file. This will take a bit of time on Raspberry Pi like devices.")
migration_lines = sqlite_convert_step_line(migration_lines)

for migration_line in migration_lines:
    step(migration_line)
