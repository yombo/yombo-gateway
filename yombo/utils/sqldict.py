# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Acts like a persistent dictionary between gateway stop/starts.
Acts exactly like a dictionary {}, however when the dictionary
is updated, the correlating database record for the dictionary
gets updated.

*Usage**:

.. code-block:: python

   from yombo.core.sqldict import SQLDict  #load at the top of the file.

   resources  = SQLDict(self, "someVars") # 'self' is required for data isolation
    
   resources['apple'] = 'ripe'
   resources['fruits'] = ['grape', 'orange', 'plum']
   resources['family'] = {'brother' : 'Jeff', 'mom' : 'Sara', 'dad' : 'Sam'}

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2015 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import cPickle
from itertools import izip
from sqlite3 import Binary as sqlite3Binary

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.loader import getLoader
from yombo.core.log import getLogger

logger = getLogger('core.sqldict')


class SQLDict(dict):
    """
    A persistent database backed dictionary

    This dictionary extends the base dictionary class, allowing it to be
    manipulated like any other dictionary item. However, when the dictionary
    is updated, the database is updated.

    Only use this dictionary to store persistent values. Update 
    iterations/calculations are expensive due to the SQL updates.

    If the dictionary for the given "dictname" exists, it will be populated
    from the database, otherwise it will be created.
    """
    def __init__(self, moduleObj, dict_name):
        """
        On init, construct a new dictionary. If there is an existing 'dict_name' for
        the given 'moduleObj', then it will be loaded.

        Update SQL on any updates/deletes.
        :param moduleObj: The module object that is using this data.
        :type moduleObj: Module Object
        :param dict_name: Name of the dictionary to store in the database.
        :type dict_name: string
        """
        super(SQLDict, self).__init__()
        self.__init = True  # only true when loaded, don't save what was just loaded.
        self.__module_name = moduleObj._FullName.lower()
        self.__dict_name = dict_name
        self.__loader = getLoader()

        self.__init = False        

    @inlineCallbacks
    def load(self):
        data = yield self.__loader.loadedLibraries['localdb'].get_sql_dict(self.__module_name, self.__dict_name)
        mydata = cPickle.loads(str(data.dict_data))
        logger.debug("key === {key}  data = {mydata}", key=data.data_key, data=mydata)
        self[data.dict_key] = mydata

    def __setitem__(self, key, value):
        """
        After calling the dictionary __setitem__, update the database.
        """
        super(SQLDict, self).__setitem__(key, value)
        self._updateSQL(key, value)

    def _updateSQL(self, key, value):
        """
        Update the database with new data. Use the loader library to handle this.
        """
        if self.__init is True:
            return True
        pdata = sqlite3Binary(cPickle.dumps(value, cPickle.HIGHEST_PROTOCOL))

        self.__loader.saveSQLDict(self.__module_name, self.__dict_name, key, pdata)

    def setdefault(self, key, value=None):
        if key not in self:
            self[key] = value
        return self[key]

    def update(self, *args, **kwargs):
        """
        Update the dictionary variable as well as the database.
        """
        if args:
            if len(args) > 1:
                raise TypeError("update expected at most 1 arguments, got %d" % len(args))
            other = dict(args[0])
            for key in other:
                self[key] = other[key]
                self._updateSQL(self[key], other[key])

        for key in kwargs:
            self[key] = kwargs[key]
            self._updateSQL(self[key], kwargs[key])
