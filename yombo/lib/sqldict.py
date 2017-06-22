# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Acts like a persistent dictionary between gateway stop/starts.
Acts exactly like a dictionary {}, however when the dictionary
is updated, the correlating database record for the dictionary
gets updated.

For performance reasons, data is only saved to disk periodically or when
the gateway exits.

The SQLDict can also use a serializer when saving data to disk. Just include
a callback to a serializer when requesting a SQLDict with the get() function,
or set a serializer later, see example below.

An unserialize function can be called to restore the data as well. This
requires the serializer and unserializer to be set inside the get() request.

*Usage**:

.. code-block:: python

   resources  = yield self._SQLDict.get(self, "someVars") # 'self' is required for data isolation
   # set a serializer when requesting a SQLDict:
   # resources  = yield self._SQLDict.get(self, "someVars", self.serialize_data) # Set a serializer on init.
   # set a serializer and unserializer:
   # resources  = yield self._SQLDict.get(self, "someVars", self.serialize_data, self.unserialize_data) # Set a serializer on init.

   resources['apple'] = 'ripe'
   resources['fruits'] = ['grape', 'orange', 'plum']
   resources['family'] = {'brother' : 'Jeff', 'mom' : 'Sara', 'dad' : 'Sam'}

   # optional, set a serializer after init. Unserializer must be set within the get() function above.
   resources.set_serializer(self.serialize_data)

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import msgpack

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('core.sqldict')


class SQLDict(YomboLibrary):
    """
    Provide a database backed persistent dictionary.
    """
    def _init_(self,):
        """
        Sets up a few variables. Doesn't do much.
        :return:
        """
        self._dictionaries = {}
        self.unload_defer = None
        self._saveSQLDictLoop = None

    def _load_(self, **kwargs):
        """
        Starts the loop to save data to SQL every so often.
        :return:
        """
        self._saveSQLDictLoop = LoopingCall(self.save_sql_dict)
        self._saveSQLDictLoop.start(self._Configs.get('sqldict', 'save_interval', 60, False))

    def _stop_(self, **kwargs):
        """
        When gateway stops, we stop the save interval timer. Will be saved in _unload_.
        :return:
        """
        if self._saveSQLDictLoop is not None and self._saveSQLDictLoop.running:
            self._saveSQLDictLoop.stop()

    @inlineCallbacks
    def _unload_(self, **kwargs):
        """
        Save any data to disk (sql).
        """
        yield self.save_sql_dict(True)

    @inlineCallbacks
    def get(self, owner_object, dict_name, serializer=None, unserializer=None, max_length=None):
        """
        Used to get or create a new SQL backed dictionary. You method must be decorated with @inlineCallbacks and then
        yield the results of this call.
        """
        if isinstance(owner_object, str):
            component_name = owner_object.lower()
        else:
            component_name = str(owner_object._FullName.lower())
        dict_name = str(dict_name)
        if component_name+":"+dict_name in self._dictionaries:
            return self._dictionaries[component_name+":"+dict_name]['dict']

        dict = SQLDictionary(self, component_name, dict_name, serializer, unserializer, max_length)
#        print "SQLDict: about to load: %s" % dict_name
        yield dict.load()

        self._dictionaries[component_name+":"+dict_name] = {
            'component_name': component_name,
            'dict_name': dict_name,
            'dict': dict,
            'dirty': False  # True if data needs to be saved.
            }
        return dict

    @inlineCallbacks
    def save_sql_dict(self, save_all=False):
        """
        Called periodically and on exit to save a dictionary to the SQL database.

        This allows multiple updates to happen to a dictionary without the overhead of constantly updating the
        matching SQL record. This can lead to some data loss if data is constantly updating and the system crashes.

        :param save_all: If true, save all the SQL Dictionaries
        :return:
        """
        for name, di in self._dictionaries.items():
            if di['dirty'] or save_all:
                # logger.info("save_sql_dict {name} ", name=name)
                # logger.info("save_sql_dict {ser} ", ser=di['dict']._SQLDictionary__serializer)
#                logger.warn("save_sql_dict 3 {di}", di=di)
                safe_data = {}  # Sometimes wierd datatype's happen...  Not good.
                for key, item in di['dict'].items():

                    if di['dict']._SQLDictionary__serializer is not None:
                        try:
                            safe_data[key] = di['dict']._SQLDictionary__serializer(item)
                        except YomboWarning:
                            continue

                    else:
                        safe_data[key] = item

                # logger.info("save_sql_dict 4 {di}", di=safe_data)

                # logger.info("save_sql_dict {safe_data} ", safe_data=safe_data)
                save_data = msgpack.packb(safe_data, use_bin_type=True)
                yield self._Libraries['localdb'].set_sql_dict(di['component_name'],
                        di['dict_name'], save_data)
#                print "in save_sql_dict - returned from saving data into sql"
                di['dirty'] = False


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
    def __init__(self, parent, component_name, dict_name, serializer=None, unserializer=None, max_length=None):
        """
        On init, construct a new dictionary. If there is an existing 'dict_name' for
        the given 'moduleObj', then it will be loaded.

        Update SQL on any updates/deletes.

        :param parent: The SQLDict library.
        :param component_name: The name of the component requesting storage.
        :param dict_name: Name of the dictionary to store in the database.
        :param serializer: A callable function to use to serialize data when saving.
        :param unserializer: A callable function to use to unserialize data when restoring
        :param max_length: If set, the dictionary can only grow to this size.

        :type dict_name: string
        """
        super(SQLDictionary, self).__init__()

        self._Parent = parent
        self.__component_name = component_name
        self.__dict_name = dict_name
        self.__load = False
        self.__serializer = serializer
        self.__unserializer = unserializer
        self.__max_length = max_length

        if max_length is not None and isinstance(max_length, int) is False:
            raise YomboWarning("SQLDict accepts either None or int for max_length. Recieved: %s" % max_length)

        if max_length is not None:
            while len(self) > max_length:
               self.popitem()

    @inlineCallbacks
    def load(self):
        self.__load = True  # only true when loaded, don't save what was just loaded.
        results = yield self._Parent._Libraries['localdb'].get_sql_dict(self.__component_name, self.__dict_name)
        if len(results) != 1:
            return None

        items = msgpack.unpackb(results[0]['dict_data'], encoding='utf-8')
        # print("sqldict results: %s" % items)

        for key, value in items.items():
            if self.__unserializer is not None:
                try:
                    value = self.__unserializer(value)
                    self[key] = value
                except YomboWarning:
                    continue
            else:
                self[key] = value

        self.__load = False  # only true when loaded, don't save what was just loaded.

    def set_serializer(self, serializer):
        """
        Set a serializer. This will be called on the data portion of a dictionary before saving.

        The serializer can raise "YomboWarning" to skipping saving this data.

        :param serializer: a pointer to a callable function
        :return:
        """
        self.__serializer = serializer

    def __setitem__(self, key, value):
        """
        After calling the dictionary __setitem__, update the database.
        """
#        print "sqldictioary:__setitem__: %s:%s" % (key, value)
        super(SQLDictionary, self).__setitem__(key, value)
        if key not in self and len(self) >= self.__max_length:
            self.popitem()
        self._update_sql(key, value)

    def touch(self):
        if not self.__load:
            self._Parent._dictionaries[self.__component_name+":"+self.__dict_name]['dirty'] = True

    def _update_sql(self, key, value):
        """
        Update the database with new data. Use the loader library to handle this.
        """
        if self.__load is False:
            self.touch()

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
