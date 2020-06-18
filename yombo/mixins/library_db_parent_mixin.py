# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Mixin class for libraries that store database tables in memory.

This mixin should be loaded right after "Library" in the class parent order list. Other mixins to use:

* library_search_mixin - search through the library data
* sync_to_everywhere - sync the library data to DB, Config, and Yombo API

To use this class, the following attributes must be defined within the library as a global class attribute:

* _storage_attribute_name - The name both the variable inside the library where data is stored and the database
  table name.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/mixins/library_db_parent_mixin.html>`_
"""
from marshmallow.exceptions import ValidationError
import sys
import traceback
from typing import Any, ClassVar, Dict, List, Optional, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred

# Import Yombo libraries
from yombo.constants import LOCAL_SOURCES
from yombo.core.exceptions import YomboWarning, YomboMarshmallowValidationError
from yombo.core.log import get_logger
from yombo.mixins.parent_storage_accessors_mixin import ParentStorageAccessorsMixin
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("mixins.library_db_parent_mixin")


class LibraryDBParentMixin(ParentStorageAccessorsMixin):
    _storage_schema: ClassVar = None
    _new_items_require_authentication: ClassVar[bool] = False
    _storage_pickled_fields: ClassVar[Dict[str, str]] = {}
    _storage_fields: ClassVar[list] = None

    @inlineCallbacks
    def _stop_(self, **kwargs):
        """ Called during the second to last phase of shutdown. """
        if hasattr(self, "_storage_attribute_name"):
            class_data_items = getattr(self, self._storage_attribute_name)
            for item_id, item in class_data_items.items():
                if hasattr(item, '_stop_'):
                    stop_ = getattr(item, "_stop_")
                    if callable(stop_):
                        yield maybeDeferred(stop_)

    @inlineCallbacks
    def _unload_(self, **kwargs):
        """ Called during the last phase of shutdown. We'll save any pending changes. """
        if hasattr(self, "_storage_attribute_name"):
            class_data_items = getattr(self, self._storage_attribute_name)
            for item_id, item in class_data_items.items():
                if hasattr(item, '_unload_'):
                    unload = getattr(item, "_unload_")
                    if callable(unload):
                        yield maybeDeferred(unload)

    def copy(self) -> dict:
        """
        Get a shallow copy of the class data.

        :return:
        """
        return getattr(self, self._storage_attribute_name).copy()

    def _storage_setup_db_columns_(self, **kwargs):
        """ Setup the _storage_fields. """
        if self._storage_fields is None:
            self._storage_fields = self._LocalDB.db_get_table_columns(self._storage_attribute_name)

    def pickle_data_records(self, incoming, pickled_columns: Optional[dict] = None):
        """
        Pickles various records as needed.

        :param incoming:
        :return:
        """
        if pickled_columns is None:
            if hasattr(self, "_storage_pickled_fields"):
                pickled_columns = self._storage_pickled_fields
            else:
                return incoming

        return self._Tools.pickle_records(incoming, pickled_columns)

    def unpickle_data_records(self, incoming, pickled_columns: Optional[dict] = None):
        """
        After the item is loaded from the database, this function will be called to
        unpickle the data.

        :param incoming:
        :param pickled_columns:
        :return:
        """
        if "pickled_columns" is None:
            if hasattr(self, "_storage_pickled_fields"):
                pickled_columns = self._storage_pickled_fields
            else:
                return incoming

        return self._Tools.unpickle_records(incoming, pickled_columns)

    def _storage_class_reference_getter(self, incoming):
        """
        Get the class used to create the library model instance. Primarily used by input types and nodes.

        Incoming is not used here, but may be used in child classes.
        """
        return self._storage_class_reference

    @inlineCallbacks
    def load_from_database(self, return_data=None, db_args=None):
        """
        Loads the library data items from the database into the library storage variable.

        load_from_database steps:
        Load all items from the DB, then send to load_db_items_to_memory.

        :param return_data: If True, will return the data instead of loading it into memory.
        :param db_args: A dictionary or arguments to pass to the db loader.
        """
        if db_args is None:
            db_args = {}

        # Check if there's a specific getter for the given table.
        get_func_name = f"get_{self._Parent._storage_attribute_name}"
        if hasattr(self._Parent._LocalDB, get_func_name):
            db_getter = getattr(self._Parent._LocalDB.database, get_func_name)
            db_items = yield db_getter(db_args=db_args)
        else:
            db_items = yield self._Parent._LocalDB.database.db_generic_item_get(self, db_args=db_args)
            pickled_columns = {}
            if "pickled_columns" in db_args:
                pickled_columns = db_args["pickled_columns"]
            elif hasattr(self, "_storage_pickled_fields"):
                pickled_columns = self._storage_pickled_fields

            db_items = self.unpickle_data_records(db_items, pickled_columns)

        if return_data is True:
            return db_items
        results = yield self.load_db_items_to_memory(db_items, load_source="database")
        return results

    @inlineCallbacks
    def load_db_items_to_memory(self, items, load_source=None, save_into_storage: Optional[bool] = None, **kwargs):
        """
        This loads multiple items into memory, a list of pointers to the new items will be returned.

        :param items:
        :param load_source:
        :param save_into_storage: If false, won't save into the library storage
        :param kwargs:
        :return: The new instance.
        """
        if items is None or len(items) == 0:
            logger.debug("load_db_items_to_memory received no items as an input for: {db_item_name}",
                         db_item_name=self._storage_label_name)
            return
        if isinstance(items, list) is False:
            items = [items]

        results = {}
        for item in items:
            # print(f"parent, about to call load_an_item_to_memory: {item}")
            try:
                instance = yield self.load_an_item_to_memory(item,
                                                             load_source=load_source,
                                                             save_into_storage=save_into_storage,
                                                             **kwargs)
            except YomboWarning as e:
                logger.warn(str(e))
                continue
            if instance is None:
                continue
            # print(f"load_db_items_to_memory, instance: {instance.__dict__}")
            results[instance._primary_field_id] = instance
        return results

    def load_an_item_to_memory_pre_check(self, incoming, load_source):
        """
        A quick pre-check to see if the item should be loaded into memory. Simply return False or raise
        YomboWarning.

        :param incoming:
        :return:
        """
        return

    def load_an_item_to_memory_pre_process(self, incoming: dict, **kwargs) -> None:
        """
        Called just before an instance is loaded into memory.

        Raise YomboWarning to stop loading into memory.

        :param incoming:
        :return: The new instance.
        """
        pass

    @inlineCallbacks
    def load_an_item_to_memory(self, incoming: dict,
                               authentication: Optional = None,
                               load_source: Optional[str] = None,
                               generated_source: Optional[str] = None,
                               save_into_storage: Optional[bool] = None,
                               **kwargs,
                               ):
        """
        This method is here to be overridden incase any data manipulation needs to take place before
        doing the actual load into memory.

        This method simply just calls do_class_storage_load_an_item_to_memory using the library variables
        for references.

        :param incoming:
        :param authentication: An authentication (AuthMixin source) to set request_by and request_type
        :param load_source: Where the data originated from. One of: local, database, yombo, system
        :param generated_source: Last resource string to use as a source.
        :param save_into_storage: If false, won't save into the library storage
        :param kwargs:
        :return: The new instance.
        """
        try:
            yield maybeDeferred(self.load_an_item_to_memory_pre_check, incoming, load_source)
        except YomboWarning as e:
            logger.info("Not loading '{class_storage_attribute_name}' into memory: {e}",
                        class_storage_attribute_name=self._storage_attribute_name, e=e.message)
            return

        if self._new_items_require_authentication:
            request_by = None
            request_by_type = None
            request_context = None
            if "request_by" in incoming:
                request_by = incoming["request_by"]
            if "request_by_type" in incoming:
                request_by_type = incoming["request_by_type"]
            if "request_context" in incoming:
                request_context = incoming["request_context"]
            try:
                incoming["request_by"], incoming["request_by_type"] = self._Permissions.request_by_info(
                    authentication, request_by, request_by_type)
            except YomboWarning:
                raise YomboWarning(f"New {self._storage_label_name} must have a valid authentication or request_by and"
                                   f" request_by_type.")

            if request_context is None:
                incoming["request_context"] = generated_source  # get the module/class/function name of caller
            # request.request_context = incoming["request_context"]
            # incoming["request_context"] = request.request_id

        if load_source is None:
            load_source = "local"  # get the module/class/function name of caller
        if load_source not in LOCAL_SOURCES:
            raise YomboWarning(f"Load an item into memory request load_source got '{load_source}',"
                               f" needs to be: {', '.join(LOCAL_SOURCES)}")

        storage = getattr(self, self._storage_attribute_name)
        storage_id = None
        if self._storage_primary_field_name in incoming:
            incoming["id"] = incoming[self._storage_primary_field_name]
            del incoming[self._storage_primary_field_name]
        if "id" in incoming:
            if incoming["id"] is None:
                del incoming["id"]
            else:
                storage_id = incoming["id"]

        run_phase_name, run_phase_int = self._Loader.run_phase
        if run_phase_int < 4000:  # just before 'libraries_started' is when we start processing automation triggers.
            call_hooks = False
        else:
            call_hooks = True

        if storage_id is not None and storage_id in storage:
            raise YomboWarning(f"Cannot add {self._storage_label_name} item to memory, already exists: {storage_id}")

        try:
            yield maybeDeferred(self.load_an_item_to_memory_pre_process, incoming)
        except YomboWarning as e:
            logger.info("Not loading '{class_storage_attribute_name}' into memory: {e}",
                        class_storage_attribute_name=self._storage_attribute_name, e=e)
            return

        if call_hooks:
            yield global_invoke_all(f"_{self._Parent._storage_label_name}_before_load_",
                                    called_by=self,
                                    arguments={
                                        "id": storage_id,
                                        "data": incoming,
                                        },
                                    )
        try:
            instance = self.do_load_an_item_to_memory(
                            storage,
                            self._storage_class_reference_getter(incoming),
                            incoming,
                            load_source=load_source,
                            **kwargs)
        except ValidationError as e:
            raise YomboWarning(f"Unable to load item '{self._Parent._storage_label_name}' into memory: {e}."
                               f" Incoming: {incoming}")

        storage_id = instance._primary_field_id

        if hasattr(instance, "_init_") and callable(instance._init_):
            try:
                yield maybeDeferred(instance._init_, **kwargs)
            except Exception as e:
                logger.error("Error while running _init_ for: {label} Additional details: {e}",
                             label=self._Parent._storage_label_name,
                             e=e)
                logger.error("--------------------------------------------------------")
                logger.error("{error}", error=sys.exc_info())
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
                logger.error("--------------------------------------------------------")
                raise YomboWarning(f"Error while running _init_ for: {self._Parent._storage_label_name} "
                                   f"Additional details: {e}")

        if call_hooks:
            yield global_invoke_all(f"_{self._Parent._storage_label_name}_loaded_",
                                    called_by=self,
                                    arguments={
                                        "id": storage_id,
                                        "data": incoming,
                                        },
                                    )

        # print(f"checking start_data_sync... {instance._Entity_type} - {instance._primary_field_id}")

        if hasattr(instance, 'start_data_sync'):
            # print(f"checking start_data_sync... has it")
            start_data_sync = getattr(instance, "start_data_sync")
            if callable(start_data_sync):
                # print(f"checking start_data_sync... is callable.")
                start_data_sync()

        try:
            yield maybeDeferred(self.load_an_item_to_memory_post_process, instance)
        except YomboWarning as e:
            logger.info("Error with load into memory post process for '{class_storage_attribute_name}' into memory: {e}",
                        class_storage_attribute_name=self._storage_attribute_name, e=e)
        return instance

    def load_an_item_to_memory_post_process(self, instance):
        """
        Called after an instance is loaded into memory.

        :param instance:
        :return: The new instance.
        """
        pass

    def do_load_an_item_to_memory(self, storage: dict, klass, incoming: dict, load_source: str,
                                  save_into_storage: Optional[bool] = None, **kwargs):
        """
        Loads data into memory using basic hook calls.

        :param storage: Dictionary to store new data in.
        :param klass: The class to use to store the data
        :param incoming: Data to be saved
        :param load_source: Where the data originated from: database, amqp, system, module
        :param save_into_storage: If false, won't save into the library storage
        :return:
        """
        if self._storage_primary_field_name in incoming:
            incoming["id"] = incoming[self._storage_primary_field_name]
            del incoming[self._storage_primary_field_name]
        if "id" in incoming and incoming["id"] is None:
            del incoming["id"]

        try:
            # print(f"do_load_an_item_to_memory: {incoming}")
            instance = klass(self,
                             incoming=incoming,
                             load_source=load_source,
                             **kwargs)
            # Used by system data mixin to save atoms/states manually.
            if hasattr(self, "save_an_item_to_memory") and callable(self.save_an_item_to_memory):
                self.save_an_item_to_memory(storage, instance, instance._primary_field_id)
            elif save_into_storage is not False:
                storage[instance._primary_field_id] = instance
        except ValidationError as e:
            raise e
        except Exception as e:
            logger.error("Error while creating {label} instance: {e}",
                         label=self._Parent._storage_label_name,
                         e=e)
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")
            raise YomboWarning(f"Error while creating {self._Parent._storage_label_name} instance: {e}")

        return instance

    @inlineCallbacks
    def db_select(self, *args, **kwargs):

        """
        Finds items based on either the row_id or using the where list/dict.  Like using self._LocalDB.select(),
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
        results = yield self._LocalDB.db_select(self._storage_attribute_name, *args, **kwargs)
        if results is None:
            return None
        if hasattr(self, "_storage_pickled_fields"):
            return self._Tools.unpickle_records(results, self._storage_pickled_fields)
        return results

    @inlineCallbacks
    def db_delete(self, *args, **kwargs):

        """
        Delete an item by the ID field.

        Examples:
        self.db_delete(row_id="ud92jh3")
        self.db_delete(where=["machine_label = ?", "some_label")

        :param row_id:
        :param where:
        :param group:
        :param limit:
        :param orderby:
        :return:
        """
        results = yield self._LocalDB.db_delete(self._storage_attribute_name, *args, **kwargs)
        return results

    ########################################################
    # Generic handlers for creating/update/deleting items. #
    ########################################################
    def update(self, item_id: str, incoming: dict, **kwargs) -> None:
        """
        Updates an item. First, it finds the item by it's ID (or machine_label), then calls it's update() method
        with the incoming dictionary.

        In short, this is a simple wrapper to calling the item's update() method directly, same results.

        :param item_id: The item's id (or machine_label) to update.
        :param incoming: A dictionary of key/values to update.
        """
        if incoming is None or isinstance(incoming, dict) is False:
            raise YomboWarning("update() - 'incoming' must be a dictionary.")

        # print(f"item, update: {item_id}, {incoming}")
        if self._Parent._storage_schema is not None:
            # print(f"library db PARENT: checking schema: {self._Parent._storage_label_name}: {incoming}")
            # print(f"about to check data with schema: {self._Parent._storage_schema}")
            try:
                data = incoming.copy()
                data = dict(self._Parent._storage_schema.load(data, partial=True))
                incoming = {key: data[key] for key in incoming.keys() if key in data}
            except ValidationError as e:
                logger.warn("Validation error loading '{item_name}', reason: {e}",
                            item_name=self._Parent._storage_label_name, e=e)
                raise YomboMarshmallowValidationError(e)
        # return
        # the_item = self.get(item_id)
        # the_item.update(incoming)
        # return the_item

    @inlineCallbacks
    def delete(self, item_id: str) -> None:
        """
        Finds the item, and then calls the item's delete method.

        :param item_id: The item's id (or machine_label) to update.
        :param incoming: A dictionary of key/values to update.
        """
        the_item = self.get(item_id)
        yield maybeDeferred(self.delete_pre_process)
        yield maybeDeferred(the_item.delete)
        yield maybeDeferred(self.delete_post_process)

    def delete_pre_process(self, the_item):
        """
        Runs any pre-process tasks before an item is deleted.

        :param the_item:
        :return:
        """
        pass

    def delete_post_process(self, the_item):
        """
        Runs any post-process tasks after an item is deleted.

        :param the_item:
        :return:
        """
        pass
