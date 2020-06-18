# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `SQLDict @ Library Documentation <https://yombo.net/docs/libraries/sqldicts>`_


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

   resources  = yield self._SQLDicts.get(self, "someVars") # "self" is required for data isolation

   # Data needs to be unserialized when loading and serialized before saving, they are set
   # when calling get:
   # resources  = yield self._SQLDicts.get(self, "someVars", serself.serialize_data) # Set a serializer on init.
   # set a serializer and unserializer:
   # resources  = yield self._SQLDicts.get(self,
                                           "someVars",
                                           serializer=self.serialize_data,  # This must be a callable
                                           unserializer=self.unserialize_data  # This must be a callable
                                           )

   resources["apple"] = "ripe"
   resources["fruits"] = ["grape", "orange", "plum"]
   resources["family"] = {"brother" : "Jeff", "mom" : "Sara", "dad" : "Sam"}

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/sqldicts.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred

# Import Yombo libraries
from yombo.classes.maxdict import MaxDict
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import SQLDictSchema
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin

logger = get_logger("core.sqldicts")


class SQLDict(Entity, LibraryDBChildMixin):
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
    _Entity_type: ClassVar[str] = "SQLDict"
    _Entity_label_attribute: ClassVar[str] = "dict_name"

    serializer = None
    unserializer = None

    @property
    def _entity_label(self):
        return f"{self.component}:{self.dict_name}"

    def __str__(self):
        return self.dict_data.__str__()

    def __contains__(self, key):
        return self.dict_data.__contains__(key)

    def __delitem__(self, key):
        """
        After calling the dictionary __delitem__, update the database.
        """
        self.sync_item_data()
        return self.dict_data.__delitem__(key)

    def __len__(self, key):
        return self.dict_data.__len__()

    def __iter__(self, key):
        return self.dict_data.__iter__()

    def __missing__(self, key, value):
        return self.dict_data.__missing__(key)

    def __setitem__(self, key, value):
        """
        After calling the dictionary __setitem__, update the database.
        """
        self.dict_data[key] = value
        self.sync_item_data()

    def __getitem__(self, item):
        return self.dict_data.__getitem__(item)

    def keys(self):
        return self.dict_data.keys()

    def values(self):
        return self.dict_data.values()

    def items(self):
        return self.dict_data.items()

    def load_attribute_values_pre_process(self, incoming: dict) -> None:
        """
        After a sqldicts is loaded, it needs to be unserialized.

        :return:
        """
        if "unserializer" in incoming and incoming["unserializer"] is not None:
            incoming["unserializer"](incoming["dict_data"])
            del incoming["unserializer"]
        if "max_length" in incoming:
            incoming["dict_data"] = MaxDict(incoming["max_length"], incoming["dict_data"])

    # def to_database_postprocess(self, incoming):
    #     if self.serializer is not None:
    #         incoming["data_dict"] = self.serializer(self.dict_data)


class SQLDicts(YomboLibrary, LibraryDBParentMixin):
    """
    Provide a database backed persistent dictionary.
    """
    sqldicts: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "sqldict_id"
    _storage_attribute_name: ClassVar[str] = "sqldicts"
    _storage_label_name: ClassVar[str] = "sqldict"
    _storage_class_reference: ClassVar = SQLDict
    _storage_schema: ClassVar = SQLDictSchema()
    _storage_pickled_fields: ClassVar[Dict[str, str]] = {"dict_data": "json"}
    _storage_search_fields: ClassVar[str] = [
        "sqldict_id",
    ]
    _storage_attribute_sort_key: ClassVar[str] = "machine_label"

    def _init_(self, **kwargs):
        """
        Setup the is enabled attribute.

        :param kwargs:
        :return:
        """
        self.enabled = self._Configs.get("events.enabled", True)

    @inlineCallbacks
    def get(self, owner_object, dict_name, max_length=None, serializer=None, unserializer=None):
        """
        Used to get or create a new SQL backed dictionary. You method must be decorated with @inlineCallbacks and then
        yield the results of this call.
        """
        if self.enabled is False:
            return {}

        if isinstance(owner_object, str):
            component = owner_object.lower()
        else:
            component = str(owner_object._FullName.lower())
        dict_name = str(dict_name)
        sqldict_id = self._Hash.sha224_compact(f"{component}:{dict_name}")
        if sqldict_id in self.sqldicts:
            return self.sqldicts[sqldict_id]

        results = yield self.db_select(row_id=sqldict_id)
        if results:
            instance = yield self.load_an_item_to_memory(results, load_source="database")
            if instance is None:
                raise YomboWarning
            self.sqldicts[sqldict_id] = instance
            return instance

        instance = yield self.load_an_item_to_memory(
            {
                "id": sqldict_id,
                "component": component,
                "dict_name": dict_name,
                "dict_data": {},
                "serializer": serializer,
                "unserializer": unserializer,
                "max_length": max_length,
            },
            load_source="local")
        self.sqldicts[sqldict_id] = instance
        return instance
