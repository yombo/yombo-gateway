"""
Misc items to help with DB Schema migrations
"""

def create_index(table, field, **kwargs):
    unique = kwargs.get("unique", False)

    if unique:
        unique = "UNIQUE"
    else:
        unique = ""
    return f"CREATE {unique} INDEX IF NOT EXISTS {table}_{field}_idx ON {table} (`{field}`);"
