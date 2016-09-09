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
from sqlite3 import Binary as sqlite3Binary

from yombo.ext.six import string_types

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue, Deferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('core.sqldict')


class SQLDict(YomboLibrary):
    """
    Provide a database backed persistent dictionary.
    """
    def _init_(self,):
        self._dictionaries = {}
        self.unload_defer = None
        self._saveSQLDictLoop = None

    def _load_(self):
        self._saveSQLDictLoop = LoopingCall(self.save_sql_dict)
        self._saveSQLDictLoop.start(60)

    def _start_(self):
        self.save_sql_dict()

    def _stop_(self):
        if self._saveSQLDictLoop is not None:
            self._saveSQLDictLoop.stop()

    def _unload_(self):
        self.save_sql_dict(True)
        self.unload_defer = Deferred()
        return self.unload_defer

    @inlineCallbacks
    def get(self, owner_object, dict_name):
        if isinstance(owner_object, string_types):
            component_name = owner_object.lower()
        else:
            component_name = str(owner_object._FullName.lower())
        dict_name = str(dict_name)
        if component_name+":"+dict_name in self._dictionaries:
            returnValue(self._dictionaries[component_name+":"+dict_name]['dict'])

        dict = SQLDictionary(self, component_name, dict_name)
#        print "SQLDict: about to load: %s" % dict_name
        yield dict.load()

        self._dictionaries[component_name+":"+dict_name] = {
            'component_name': component_name,
            'dict_name': dict_name,
            'dict': dict,
            'dirty': False  # True if data needs to be saved.
            }
        returnValue(dict)

    @inlineCallbacks
    def save_sql_dict(self, save_all=False):
        """
        Called by SQLDictionary to save a dictionary to the SQL database.

        This allows multiple updates to happen to a dictionary without the overhead of constantly updating the
        matching SQL record. This can lead to some data loss.

        :param save_all: If true, save all the SQL Dictionaries
        :return:
        """
        for name, di in self._dictionaries.iteritems():
#            logger.warn("save_sql_dict 1")
            if di['dirty'] or save_all:
#                logger.warn("save_sql_dict 3 {di}", di=di)
                safe_data = {}  # Sometimes wierd datatype's happen...  Not good.
                for key, item in di['dict'].iteritems():
                    safe_data[key] = item
 #               logger.warn("save_sql_dict 4 {di}", di=safe_data)
                save_data = sqlite3Binary(cPickle.dumps(safe_data, cPickle.HIGHEST_PROTOCOL))
                yield self._Libraries['localdb'].set_sql_dict(di['component_name'],
                        di['dict_name'], save_data)
#                print "in save_sql_dict - returned from saving data into sql"
                self._dictionaries[name]['dirty'] = False
        if self.unload_defer is not None:
            self.unload_defer.callback(10)


    # def _saveSQLDictDB(self):
    #     if len(self._SQLDictUpdates):
    #         logger.debug("Doing _saveSQLDictDB")
    #         for module in self._SQLDictUpdates.keys():
    #             for dictname in self._SQLDictUpdates[module]:
    #                 for key1 in self._SQLDictUpdates[module][dictname]:
    #                     yield self._Libraries['localdb'].set_sql_dict(module,
    #                             dictname, key1, self._SQLDictUpdates[module][dictname][key1])
    #             del self._SQLDictUpdates[module]


class SQLDictionary(dict):
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
    def __init__(self, parent, component_name, dict_name):
        """
        On init, construct a new dictionary. If there is an existing 'dict_name' for
        the given 'moduleObj', then it will be loaded.

        Update SQL on any updates/deletes.
        :param owner_object: The module object that is using this data.
        :type owner_object: Module Object
        :param dict_name: Name of the dictionary to store in the database.
        :type dict_name: string
        """
        super(SQLDictionary, self).__init__()
        self._SQLDict = parent

        self.__init = True  # only true when loaded, don't save what was just loaded.
        self.__component_name = component_name
        self.__dict_name = dict_name
        self.__init = False

    @inlineCallbacks
    def load(self):
        self.__load = True  # only true when loaded, don't save what was just loaded.
        results = yield self._SQLDict._Libraries['localdb'].get_sql_dict(self.__component_name, self.__dict_name)
        if len(results) != 1:
            returnValue(None)

        result_data = str(results[0]['dict_data'])
        items = cPickle.loads(result_data)

        for key, value in items.iteritems():
            self[key] = value
        self.__load = False  # only true when loaded, don't save what was just loaded.

    def __setitem__(self, key, value):
        """
        After calling the dictionary __setitem__, update the database.
        """
#        print "sqldictioary:__setitem__: %s:%s" % (key, value)
        super(SQLDictionary, self).__setitem__(key, value)
        self._update_sql(key, value)

    def touch(self):
        if not self.__load:
            self._SQLDict._dictionaries[self.__component_name+":"+self.__dict_name]['dirty'] = True

    def _update_sql(self, key, value):
        """
        Update the database with new data. Use the loader library to handle this.
        """
        if self.__init is True:
            return True

        self.touch()
#        self.__loader.save_sql_dict(self.__component_name, self.__dict_name, key, pdata)

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
                self._update_sql(self[key], other[key])

        for key in kwargs:
            self[key] = kwargs[key]
            self._update_sql(self[key], kwargs[key])
