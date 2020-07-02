"""
Various helpers used by various database systems. Used to hold tools used during migration.
"""
import re


def sql_create_index(table: str, field: str, **kwargs) -> str:
    """
    Create indexes for sql based migrations.

    :param table:
    :param field:
    :param kwargs:
    :return:
    """
    unique = kwargs.get("unique", False)

    if unique:
        unique = "UNIQUE"
    else:
        unique = ""
    return f"CREATE {unique} INDEX IF NOT EXISTS {table}_{field}_idx ON {table} (`{field}`);"


def sqlite_convert_step_line(lines: list) -> list:
    """
    Simply remove/change all the MariaDB/MySQL items that don't work on SQLite, then add it

    Note: The step() function must be performed within the migration file and not here!

    :param lines: A list of lines to transfer from MySQL to SQLite.
    """
    varbinary = re.compile("VARBINARY\(([0-9]*)\)")
    collate = re.compile(r"COLLATE [A-Za-z_0-9]+")
    comment = re.compile(r"""COMMENT ([`"'])(?:(?=(\\?))\2.)*?\1+""")
    results = []
    for line in lines:
        line = varbinary.sub('BLOB', line)
        line = collate.sub('', line)
        line = comment.sub('', line)
        line = line.replace("INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTOINCREMENT",
                            "INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT")
        results.append(line)
    return results
