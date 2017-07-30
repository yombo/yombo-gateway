from yombo.ext.twistar.registry import Registry
from yombo.ext.twistar.dbconfig.base import InteractionBase


class SQLiteDBConfig(InteractionBase):
    def whereToString(self, where):
        assert(isinstance(where, list))
        query = where[0]
        args = where[1:]
        return (query, args)


    def updateArgsToString(self, args):
        colnames = self.escapeColNames(list(args.keys()))
        setstring = ",".join([key + " = ?" for key in colnames])
        return (setstring, list(args.values()))


    def insertArgsToString(self, vals):
        return "(" + ",".join(["?" for _ in list(vals.items())]) + ")"


    # def insertMany(self, tablename, vals):
    #     def _insertMany(txn):
    #         for val in vals:
    #             self.insert(tablename, val, txn)
    #     return Registry.DBPOOL.runInteraction(_insertMany)

    def pragma(self, pragma_string):
        """
        Truncate the given tablename.

        @return: A C{Deferred}.
        """
        q = "PRAGMA %s" % pragma_string
        return self.runInteraction(self._doselect, q, [], 'PRAGMA_table_info')

    def truncate(self, tablename):
        """
        Truncate the given tablename.

        @return: A C{Deferred}.
        """
        q = "DELETE FROM %s" % tablename
        return self.executeOperation(q, [])