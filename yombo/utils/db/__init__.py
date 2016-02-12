"""
Misc items to help with DB Schema updates
"""
def create_index(table, field, **kwargs):
    unique = kwargs.get('unique', False)

    if unique:
        unique = "UNIQUE"
    else:
        unique = ""
    return "CREATE %s INDEX IF NOT EXISTS %s_%s_idx ON %s (%s);" % (unique, table, field, table, field)

