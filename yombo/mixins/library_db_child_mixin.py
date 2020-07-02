"""
A complementary class to the LibraryDBParentMixin class. This should be used in all child classes for libraries that
use the LibraryDBParentMixin. This also ensures items are sync'd to the database, and optionally, to the Yombo
API.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/mixins/library_db_child_mixin.html>`_
"""
from marshmallow.exceptions import ValidationError
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboInvalidValidation
from yombo.core.log import get_logger
from yombo.mixins.child_storage_accessors_mixin import ChildStorageAccessorsMixin
from yombo.utils.hookinvoke import global_invoke_all
from yombo.utils import is_true_false

logger = get_logger("mixins.library_db_child_mixin")

CLASS_DEFAULTS = {
    "_sync_enabled": False,
    "_sync_to_api": False,  # If true, sync to yombo API - Needs to explicitly be set by the library to enable this.
    "_sync_to_db": True,  # If true, sync to db
    "_sync_data_delay": 5,  # If greater than 0, allow sync to API and DB to be delayed.
    "_sync_init_complete": False,  # Once the object has been completely setup, this turns to True.
    "_fake_data": False,
}

SYNC_TO_DB = 1  # Bit operator to check if syncing to db
SYNC_TO_API = 2  # Bit operator to check if syncing to api
SYNC_NOW = 4  # Bit operator to check if item should be immediately synced.


class LibraryDBChildMixin(ChildStorageAccessorsMixin):
    """
    This class handles items at the local instance level. This handles the initial loading of the data and
    data updates.

    When attributes are updated, this library will automatically calls before and after the attribute is updated.
    To prevent a flood of hook calls, use the 'update_attributes' method to bulk update attributes.
    """
    @property
    def _primary_field_id(self):
        """ Get the ID for the object. """
        return self.__dict__[self._Parent._storage_primary_field_name]

    @_primary_field_id.setter
    def _primary_field_id(self, val):
        """ Set the ID for the object. """
        self.__dict__[self._Parent._storage_primary_field_name] = val

    @property
    def _entity_label(self):
        """ Get the label for the current object. """
        return getattr(self, self._Entity_label_attribute)

    def __setattr__(self, name: str, value: Any):
        """
        Monitor set attributes and possibly sync changes.

        This is only allowed during the class setup and if not syncing to the API. Otherwise, call
       update() with a dictionary of key:value pairs to update.

        :param name: Name of attribute to update.
        :param value: Value to set attribute.
        """
        if hasattr(self, "_Parent") is False:
            self.__dict__[name] = value
            return
        if name.startswith("_") or \
                name.startswith("__") or \
                hasattr(self, "_sync_to_api") is False or \
                hasattr(self, "_sync_to_db") is False or \
                hasattr(self, "_Parent") is False or \
                hasattr(self._Parent, "_storage_fields") is False or \
                hasattr(self, "_sync_init_complete") is False or \
                self._Parent._storage_fields is None or \
                name not in self._Parent._storage_fields or \
                self._sync_init_complete is False or \
                self._fake_data is True or \
                (self._sync_to_api is False and self._sync_to_db is False):
            self.__dict__[name] = value
        elif self._sync_data_delay > 0:
            self.__dict__[name] = value
            reactor.callLater(0.0001, self.sync_item_data)
        else:
            raise YomboWarning('Cannot set attribute directly, use "object.update({dict})" instead.')

    ########################
    ##   Startup Items    ##
    ########################
    def __init__(self, *args, **kwargs):
        """
        Setup the object, including it's meta data. And it's.
        :param args:
        :param kwargs:
        """
        for key, value in CLASS_DEFAULTS.items():
            if hasattr(self, key) is False:
                self.__dict__[key] = value

        if hasattr(self, "_meta") is False:
            self.__dict__["_meta"] = {}
        self.__dict__["_meta"]["load_source"] = kwargs.get("load_source", None)
        self.__dict__["_meta"]["source"] = self._FullName
        self.__dict__["_meta"]["gateway_id"] = self._gateway_id
        self.__dict__["_meta"]["type"] = self._Parent._storage_attribute_name
        self.__dict__["_meta"]["item_type"] = self._Parent._storage_label_name

        self._sync_data_callLater = None
        self._deleted = False
        self._in_database = False
        if self._meta["load_source"] == "database":
            self._in_database = True

        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            pass

        self.init_attributes()  # Setup columns based on the database table columns.

        self.load_attribute_values(**kwargs)
        self.__dict__["_sync_init_complete"] = True

    def __getitem__(self, key):
        """ Allows this class to be accessed like a dictionary. """
        return getattr(self, key)

    def __repr__(self):
        """
        Returns some info about the current child object.

        :return: Returns some info about the current child object.
        :rtype: string
        """
        return f"<{self._Entity_type}: {self._entity_label}>"

    def init_attributes(self, columns: Optional[List[str]] = None) -> None:
        """
        Called during setup, this should set all the core attributes to None and prepared to be loaded later.

        Accepts a list of names (columns) that should be added as attributes to the current instance.

        If columns is not provided, will use the parent's _storage_primary_field_name. Since
        _storage_primary_field_name is populated by the database fields, it will also check for
        _storage_primary_field_name_extra to see if any other fields should be populated by default.
        """
        self.__dict__[self._Parent._storage_primary_field_name] = None
        if columns is None:
            columns = self._Parent._storage_fields
        for col in columns:
            if col == "id":
                continue
            self.__dict__[col] = None

        if hasattr(self._Parent, "_storage_primary_field_name_extra"):
            for col in self._Parent._storage_primary_field_name_extra:
                self.__dict__[col] = None

    def load_attribute_values_pre_process(self, incoming: Dict[str, Any]) -> None:
        """
        Allows children to perform pre-process functions before the attribute is committed.

        If the attribute shouldn't be committed, simply raise YomboWarning

        :param incoming: Incoming values. Simply alter these values directly.
        :return:
        """
        pass

    def load_attribute_values_post_process(self, incoming: Dict[str, Any]) -> None:
        """
        Allows children to perform post-process functions after the attribute is committed.

        :param incoming: Incoming values. Simply alter these values directly.
        :return:
        """
        pass

    def load_attribute_values(self, incoming: Dict[str, Any], load_source: Optional[str] = None,
                              request_context: Optional[str] = None,
                              authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None,
                              **kwargs) -> None:
        """
        This loads all the data from 'incoming' (a dictionary) and loads them into the instance attributes.

        This first setups the 'id' column value (based on _storage_primary_field_name). Then it calls update() to
        perform the actual update.

        :param incoming: Typically a dictionary conntaing the items attributes.
        :param load_source: Where the data originated from. One of: local, database, yombo, system
        :param request_context: Context about the request. Such as an IP address of the source.
        :param authentication: An auth item such as a websession or authkey.

        :return:
        """
        if load_source is not None:
            incoming["load_source"] = load_source
        if request_context is not None:
            incoming["request_context"] = request_context
        if authentication is not None:
            incoming["request_by"], incoming["request_by_type"] = self._Users.request_by_info(authentication)
        if self._Parent._storage_schema is not None:
            try:
                incoming = dict(self._Parent._storage_schema.load(incoming))
            except ValidationError as e:
                logger.warn("Error loading '{item_name}', reason: {e}",
                            item_name=self._Parent._storage_label_name, e=e)
                raise e
        if "id" not in incoming:
            raise AttributeError(f"Incoming dictionary is missing id key")

        incoming[self._Parent._storage_primary_field_name] = incoming["id"]
        del incoming["id"]
        self.load_attribute_values_pre_process(incoming)
        if "machine_label" in incoming:
            try:
                incoming["machine_label"] = self._Validate.slugify(incoming["machine_label"])
            except YomboInvalidValidation as e:
                logger.warn("Unable to verify machine_label: {incoming}", incoming=incoming)
                raise

        for name, value in incoming.items():
            if name in self.__dict__:
                set_attribute_name = f"_set_{name}_attribute"
                if hasattr(self, set_attribute_name):
                    attribute_setter_callable = getattr(self, set_attribute_name)
                    attribute_setter_callable(value)
                    continue  # Only update the value if it's not None...that's the default anyways.
                if isinstance(self.__dict__[name], dict):  # So we can preserve a maxdict instance.
                    if isinstance(self.__dict__[name], dict) is False:
                        self.__dict__[name] = {}
                    self.__dict__[name].clear()
                    self.__dict__[name].update(value)
                else:
                    the_property = getattr(type(self), name, None)
                    if isinstance(the_property, property):
                        logger.debug(f"{name} - setting via property", name=name)
                        the_property.__set__(self, value)
                    else:
                        logger.debug(f"{name} - setting via local dictionary", name=name)
                        self.__dict__[name] = value
        self.load_attribute_values_post_process(incoming)

    def from_database(self, incoming):
        if hasattr(self, "_storage_pickled_fields"):
            return self._Tools.unpickle_records(incoming, self._storage_pickled_fields)
        return incoming

    def set_fake_data(self, value):
        if hasattr(super(), "set_fake_data"):
            super().set_fake_data(value)
        elif isinstance(value, bool):
            self.__dict__["_fake_data"] = value

    def update_attributes_pre_process(self, incoming: Dict[str, Any]):
        """
        Allows children to perform pre-process functions before the attribute is committed.

        If the attribute shouldn't be commited, simply raise YomboWarning

        :param incoming: a dictionary containing key/value pairs to update.
        :return:
        """
        pass

    @inlineCallbacks
    def api_update(self, incoming, load_source: Optional[str] = None, request_context: Optional[str] = None,
                   authentication: Optional[Any] = None, **kwargs):
        """
        Alternative to update() found below. This first tries to update the data at API.Yombo.net before
        updating locally.  After API.Yombo is updated, this method will call update() to complete locally.

        Reasoning: The update() method is not deferred friendly. Update() will eventaully complete the same tasks,
        but provides no status back on completed failed.

        :param incoming: The dictionary to send Yombo API
        :param load_source: Where the data originated from. One of: local, database, yombo, system
        :param request_context: Context about the request. Such as an IP address of the source.
        :param authentication: An auth item such as a websession or authkey.
        :return:
        """
        print("api_update child: a")
        logger.info("api_update: saving data to api: {incoming}", incoming=incoming)
        print("api_update child: b")
        if self._sync_init_complete is True and \
                self.sync_allowed() is True and \
                self._fake_data is False and \
                self._sync_enabled is True and \
                self._sync_to_api is True:
            response = yield self._sync_do_sync_to_api(incoming=incoming)
            print("api_update child: c")
            data = response.content["data"]["attributes"]
        print("api_update child: d")
        logger.info("about to save the data locally.")
        print("api_update child: e")
        if load_source == "library":  # Disable sending to API again.
            load_source = "yombo"
        self.update(incoming, load_source=load_source, request_context=request_context, authentication=authentication)

    def update(self, incoming_items: dict, load_source: Optional[str] = None, request_context: Optional[str] = None,
               authentication: Optional[Any] = None, broadcast: Optional[bool] = None,
               save_delay: Optional[Union[int, float]] = None):
        """
        Bulk update the attributes for the instance. Using this method prevents a flood of hook calls when
        updating multiple attributes at once. If the attributes were updated directly, which is fine for updating
        one attribute, at least 2 hooks will be made each time an attribute is updated.

        This is 100% anti-pythonic. Here's why:
        If attributes are set internally, it's assumed that these come internally and are 100% pythonic. This is fine.
        There are times when things don't need to be synced to other other places:
        * If from AQMP/YomboAPI, then we just need to update the memory and database.
        * If from database (loading), then we just need to update memory and not Yombo API.

        :param incoming_items: A dictionary of items to update.
        :param load_source: Where the data originated from. One of: local, database, yombo, system
        :param request_context: Context about the request. Such as an IP address of the source.
        :param authentication: An auth item such as a websession or authkey.
        :param broadcast: If false, won't broadcast using the hook system.
        :param save_delay: Override the default save delay, in seconds.
        """
        if isinstance(incoming_items, dict) is False:
            raise YomboWarning(f"update attributes expects a dictionary, got: {type(incoming_items)}")

        if "_fake_data" in incoming_items:
            self.set_fake_data(incoming_items['_fake_data'])
            del incoming_items['_fake_data']

        hook_prefix = self._Parent._storage_label_name
        try:
            self.update_attributes_pre_process(incoming_items)
        except YomboWarning as e:
            logger.info("Skipping update attributes for {item_type}, reason: {e}",
                        item_type=hook_prefix,
                        e=e)
            return

        save_data_keys = []
        for name, value in incoming_items.items():
            if name == "id":  # No changing the ID for an item. Bad.
                continue
                # self._primary_field_id = value
            elif hasattr(self, name) and getattr(self, name) == value and \
                    isinstance(value, int) is True and isinstance(value, str) is True and \
                    isinstance(value, float) is True and isinstance(value, bytes) is True and \
                    isinstance(value, bool) is True:
                continue
            elif name.startswith("_") or name.startswith("__") or name not in self._Parent._storage_fields:
                self.__dict__[name] = value
            else:
                self.__dict__[name] = value
                save_data_keys.append([name])

        # If still loading the item, just load it and skip syncing.
        if len(save_data_keys) == 0:
            logger.debug("Update: Nothing new to save, skipping.")
            return

        # If still loading the item, just load it and skip syncing.
        if hasattr(self, "_sync_init_complete") is False or self._sync_init_complete is False:
            logger.debug("Update: sync_init_complete isn't done, skipping.")
            return

        if hasattr(self, "updated_at") and "updated_at" not in save_data_keys:
            if isinstance(self.updated_at, int):
                self.__dict__["updated_at"] = int(time())
            elif isinstance(self.updated_at, float):
                self.__dict__["updated_at"] = round(time(), 4)

        storage_id = self._primary_field_id

        if broadcast in (None, True) and self._Loader.run_phase[1] >= 6500:
            global_invoke_all(f"_{hook_prefix}_before_update_",
                              called_by=self,
                              arguments={
                                  "id": storage_id,
                                  "data": self,
                                  }
                              )

        sync_mode = self._sync_compute_sync_mode(load_source)
        if sync_mode > 0:

            self.sync_item_data(sync_mode=sync_mode, save_delay=save_delay)

        if broadcast in (None, True) and self._Loader.run_phase[1] >= 6500:
            global_invoke_all(f"_{hook_prefix}_updated_",
                              called_by=self,
                              arguments={
                                  "id": storage_id,
                                  "data": self,
                                  }
                              )

        try:
            self.update_attributes_post_process(incoming_items)
        except YomboWarning as e:
            logger.info("Update attributes post process errors: {e}",
                        item_type=self._Parent._storage_label_name,
                        e=e)
            return

    def update_attributes_post_process(self, incoming: Dict[str, Any]):
        """
        Allows parents to perform post-process functions after all submitted items have been processed, but
        before a possible sync event.

        This sends the incoming data for reference/usage.

        :param incoming:
        :return:
        """
        pass

    ########################
    ##     Sync Items     ##
    ########################
    def _sync_compute_sync_mode(self, load_source=None):
        """
        Returns a sync value based on the incoming load_source and the current settings for API/DB sync.

        load_source should be one of:

          * local - Locally generated content - needs to be synced everywhere.
          * database - Loaded from the database, no need to be synced anywhere.
          * yombo - Only synced to the database. This is either from the API or AMQP (same data source).
          * system - Data that is not synced anywhere.

        :param load_source: One of: local, database, yombo
        :return:
        """
        if load_source is None:
            load_source = "local"
        sync_mode = 0
        if load_source is None or load_source.lower() == "local":
            if self._sync_to_db:
                sync_mode |= SYNC_TO_DB
            if self._sync_to_api:
                sync_mode |= SYNC_TO_API
        elif load_source == "yombo":
            if self._sync_to_db:
                sync_mode |= SYNC_TO_DB
            sync_mode |= SYNC_NOW
        elif load_source in ("database", "system"):
            sync_mode = 0
        else:
            raise YomboWarning("load_source attribute must be one of: local, database, yombo, or NoneType.")
        return sync_mode

    def start_data_sync(self):
        """ Allow sync to happen. """
        if self._fake_data is True:
            self.__dict__["_sync_enabled"] = False
            return False
        self.__dict__["_sync_enabled"] = True
        if self._meta["load_source"] not in ("database", "system"):
            self.sync_item_data(load_source=self._meta["load_source"])
        return True

    def stop_data_sync(self):
        """ Disable syncing. """
        self.sync_item_data()
        self.__dict__["_sync_enabled"] = False
        return True

    def set_fake_data(self, value):
        """ If data is fake, we won't sync to anywhere. """
        if isinstance(is_true_false(value), bool):
            self.__dict__["_fake_data"] = value
            if value is True:
                self.stop_data_sync()
            else:
                self.start_data_sync()
            return True

    def sync_allowed(self):
        """ A method that be overridden to determine if sync should take place."""
        # if self._meta["load_source"] == "system":
        #     print(f"sync_allowed: {self._meta}")
        #     return False
        return True

    def sync_item_data(self, sync_mode: Optional[int] = None, load_source: Optional[str] = None,
                       save_delay: Optional[Union[int, float]] = None):
        """
        Syncs items to the database and/or to the Yombo api.

        :param save_delay: Override the default save delay, in seconds.

        :return:
        """
        if self._sync_init_complete is not True or \
                self.sync_allowed() is False or \
                self._fake_data is True or \
                self._sync_enabled is not True or \
                (self._sync_to_api is False and self._sync_to_db is False):
            # print("sync_item_data skipped in first check.")
            # print(f"self._sync_init_complete: {self._sync_init_complete} - is not True - {self._sync_init_complete is not True}")
            # print(f"self.sync_allowed: {self.sync_allowed()} - is False - {self.sync_allowed() is False}")
            # print(f"self._fake_data: {self._fake_data} - is True- {self._fake_data is True}")
            # print(f"self._sync_enabled: {self._sync_enabled} - is not True - {self._sync_enabled is not True}")
            # print(f"self._sync_to_api: {self._sync_to_api} - is False - {self._sync_to_api is False and self._sync_to_db is False}")
            # print(f"self._sync_to_db: {self._sync_to_db} - is False - {self._sync_to_api is False and self._sync_to_db is False}")
            return

        if sync_mode is None:
            sync_mode = self._sync_compute_sync_mode(load_source)

        if self._sync_data_callLater is not None and self._sync_data_callLater.active():
            self._sync_data_callLater.cancel()
        if isinstance(save_delay, int) or isinstance(save_delay, float):
            sync_delay = save_delay
        else:
            sync_delay = self._sync_data_delay
        if sync_delay in (0, None):
            sync_delay = 0.001
        self._sync_data_callLater = reactor.callLater(sync_delay, self._do_sync_item_data, sync_mode)

    @inlineCallbacks
    def _do_sync_item_data(self, sync_mode: Optional[int] = None):
        if sync_mode & SYNC_TO_API:
            try:
                if self._Entity_type == "Device":
                    logger.warn("Device - about to send to api")
                logger.warn("about to send to api: {the_item}", the_item=self)
                results = yield self._sync_do_sync_to_api()
                if results["status"] == "ok":
                    for name, value in \
                            self._Parent.unpickle_data_records(results["content"]["data"]["attributes"]).items():
                        self.__dict__[name] = value

                if self._Entity_type == "Device":
                    logger.warn("Device - about to send to api, done")
            except YomboWarning as e:
                logger.warn("Cannot set attributes for ({entity_type}) {label} - {e}",
                            entity_type=self._Entity_type,
                            label=self._entity_label,
                            e=e)
                return
        if sync_mode & SYNC_TO_DB:
            yield self.db_save(sync_mode & SYNC_NOW)

    @inlineCallbacks
    def _sync_do_sync_to_api(self, data: Optional[Any] = None):
        """
        Does the actual sync to Yombo API.

        :param data: Data to send to the API, otherwise, uses data from memory.
        :return:
        """
        if self._sync_to_api is False:
            return None

        results = yield self._YomboAPI.update(request_type=self._Parent._storage_attribute_name,
                                              data=data if data is not None else self.to_database(),
                                              url_format={"id": self._primary_field_id},
                                              )
        return results

    ########################
    ##   Database Items   ##
    ########################
    @inlineCallbacks
    def db_select(self, *args, **kwargs):

        """
        Finds items based on either the row_id or using the where list/dict.  Like using self._LocalDB.db_select(),
        but add the table name and un-pickles the columns automatically.

        Examples:
        self.db_select(row_id="ud92jh3")
        self.db_select(where=["machine_label = ?", "some_label")

        :param row_id:
        :param where:
        :param group:
        :param limit:
        :param orderby:
        :return:
        """
        results = yield self._LocalDB.database.db_select(self._Parent._storage_attribute_name, *args, **kwargs)
        pickled_columns = None
        if "pickled_columns" in kwargs:
            pickled_columns = kwargs["pickled_columns"]
        return self._Parent.unpickle_data_records(results, pickled_columns=pickled_columns)
        # if isinstance(results, list):
        #     for record in results:
        #         return self._Parent.unpickle_data_records(record, pickled_columns=pickled_columns)
        # else:
        #     return self._Parent.unpickle_data_records(results, pickled_columns=pickled_columns)

    def db_save_allow(self) -> bool:
        """
        If save (either update or insert) should be allowed.

        :return:
        """
        return True

    @inlineCallbacks
    def db_save(self, save_now: Optional[bool] = None):
        """
        Save this object to the database.
        :return:
        """
        if self._deleted:
            raise YomboWarning("Cannot save a previously deleted object.")

        if self.db_save_allow() is False:
            return

        if self._in_database is False:
            yield self.db_insert(save_now)
        else:
            yield self.db_update(save_now)

    def db_before_create(self):
        """ Perform these actions to the object before creating new database row. """
        pass

    def db_before_insert(self):
        """ Perform these actions to the object before update database row. """
        pass

    def db_before_save(self):
        """ Perform these actions to the object before saving. """
        pass

    def db_before_update(self):
        """ Perform these actions to the object before updating database row. """
        pass

    @inlineCallbacks
    def db_insert(self, save_now: Optional[bool] = None):
        """ Create a new row in the database for this object. """
        yield maybeDeferred(self.db_before_create)
        yield maybeDeferred(self.db_before_save)
        yield maybeDeferred(self._db_insert, save_now)
        self._in_database = True

    @inlineCallbacks
    def _db_insert(self, save_now: Optional[bool] = None):
        """
        Insert this current object into database, a new record.

        :return: A C{Deferred} that sends a callback the inserted object.
        """
        if save_now is None:
            save_now = False

        if len(self._Parent._storage_fields) == 0:
            raise YomboWarning(f"Table {self._storage_attribute_name} has no columns, cannot insert into database.")

        data = self.to_database()
        print(f"_db_insert: data: {data}")
        if "gateway_id" in data and data["gateway_id"] == "local":
            return

        if self._Parent._storage_attribute_name in ("events") or save_now is True:
            yield self._Parent._LocalDB.database.db_insert(self._Parent._storage_attribute_name,
                                                           data)
        else:
            self._Parent._LocalDB.add_bulk_queue(self._Parent._storage_attribute_name,
                                                 "insert",
                                                 data)
        self._in_database = True

    @inlineCallbacks
    def db_update(self, save_now: Optional[bool] = None):
        """ Update database record. """
        yield maybeDeferred(self.db_before_update)
        yield maybeDeferred(self.db_before_save)
        yield maybeDeferred(self._db_update, save_now)
        self._in_database = True

    @inlineCallbacks
    def _db_update(self, save_now: Optional[bool] = None):
        """
        Update this current object into database, an updated record.

        :return: A C{Deferred} that sends a callback the inserted object.
        """
        if save_now is None:
            save_now = False

        if len(self._Parent._storage_fields) == 0:
            raise YomboWarning(f"Table {self._storage_attribute_name} has no columns, cannot insert into database.")

        data = self.to_database()
        if "gateway_id" in data and data["gateway_id"] == "local":
            return
        if self._Parent._storage_attribute_name in ("events") or save_now is True:
            yield self._Parent._LocalDB.database.db_update(self._Parent._storage_attribute_name,
                                                           data,
                                                           where=["id = ?", self._primary_field_id])
        else:
            self._Parent._LocalDB.add_bulk_queue(self._Parent._storage_attribute_name,
                                                 "update",
                                                 data)
