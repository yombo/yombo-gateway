# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Mixin class for libraries that store database tables in memory.

This mixing should be loaded right after "Library" in the class parent order list. Other mixins to use:
* library_search_mixin - search through the library data
* sync_to_everywhere - sync the library data to DB, Config, and Yombo API

To use this class, the following attributes must be defined within the library as a global class attribute:
* _class_storage_attribute_name - The name both the variable inside the library where data is stored and the
  database table name.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
import sys
import traceback
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.accessors_mixin import AccessorsMixin
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("mixins.library_db_model_mixin")


class LibraryDBModelMixin(AccessorsMixin):
    @property
    def _class_storage_db_columns(self):
        """
        Gets a list of columns that should be synced....Everything but the ID.

        Override this function to create custom column list.

        This function gets it's values from the LocalDB library.

        :return:
        """
        columns = self._Parent._LocalDB.get_table_columns(self._class_storage_attribute_name)
        if "id" in columns:
            columns.remove("id")
        return columns

    def __init__(self, *args, **kwargs):
        if hasattr(self, "_can_have_fake_data") is False:
            self._can_have_fake_data = True
        super().__init__(*args, **kwargs)

    def class_storage_as_list(self):
        """
        Return a list of dictionaries representing all known items for the library. Typically used in the API or
        when a list of dictionaries as opposed to list of instances is needed.

        :return:
        """
        items = []
        for item_id, item in getattr(self, self._class_storage_attribute_name).items():
            items.append(item.asdict())
        return items

    def get_copy(self):
        """
        Get a shallow copy of the class data.

        :return:
        """
        return getattr(self, self._class_storage_attribute_name).copy()

    def _class_storage_preprocess_load(self, item, **kwargs):
        """
        Used to make any changes to the item (as a dict) before being loaded into memory.

        To skip loading this item, raise YomboWarning.

        :param item:
        """
        pass

    @inlineCallbacks
    def _class_storage_load_from_database(self, **kwargs):
        """
        Loads the library data items from the database into the library storage variable.
        """
        get_func_name = f"get_{self._Parent._class_storage_attribute_name}"
        if hasattr(self._Parent._LocalDB, get_func_name):
            # print(f"Getting db items: get_{self._class_storage_attribute_name}")
            db_getter = getattr(self._Parent._LocalDB, get_func_name, **kwargs)
            db_items = yield db_getter()
        else:
            db_items = yield self._Parent._LocalDB.generic_item_get(self._Parent._class_storage_attribute_name)

        # if self._Parent._LocalDB.generic_item_functions_available(self._Parent._class_storage_attribute_name):
        #     db_items = yield self._Parent._LocalDB.generic_item_get(self._Parent._class_storage_attribute_name)
        # else:
        #     print(f"Getting db items: get_{self._class_storage_attribute_name}")
        #     db_getter = getattr(self._Parent._LocalDB, f"get_{self._class_storage_attribute_name}", **kwargs)
        #     db_items = yield db_getter()

        # logger.info("db_items: {db_items}", db_items=db_items)
        for item in db_items:
            item = item.__dict__
            yield maybeDeferred(self._class_storage_preprocess_load, item)
            yield self._class_storage_load_db_items_to_memory(item, source="database", **kwargs)
            yield maybeDeferred(self._class_storage_postprocess_load, item)


    def _class_storage_postprocess_load(self, item, **kwargs):
        """
        Used to make any changes to the item instance after it has been loaded to memory. Any changes
        may be synced if sync_to_everywhere is enabled.

        This function is not expect to receive anything back.
        :param item:
        :return:
        """
        pass

    def _class_storage_get_instance_model(self, incoming):
        """ Get the class used to create the library model instance. Primarily used by input types."""
        return self._class_storage_load_db_class

    @inlineCallbacks
    def _class_storage_load_db_items_to_memory(self, incoming, source=None, **kwargs):
        """
        This method is here to be overridden incase any data manipulation needs to take place before
        doing the actual load into memory.

        This method simply just calls _generic_class_storage_load_to_memory using the library variables
        for references.

        :param incoming:
        :param source:
        :param kwargs:
        :return: The new instance.
        """
        # print(f"self._class_storage_get_instance_model(incoming): {self._class_storage_get_instance_model(incoming)}")

        instance = yield maybeDeferred(
            self._generic_class_storage_load_to_memory,
            getattr(self, self._class_storage_attribute_name),
            self._class_storage_get_instance_model(incoming),
            incoming,
            source,
            **kwargs)

        if hasattr(instance, 'start_data_sync'):
            start_data_sync = getattr(instance, "start_data_sync")
            if callable(start_data_sync):
                start_data_sync()
        return instance

    @inlineCallbacks
    def _generic_class_storage_load_to_memory(self, storage, klass, incoming, source, **kwargs):
        """
        Loads data into memory using basic hook calls.

        :param storage: Dictionary to store new data in.
        :param klass: The class to use to store the data
        :param incoming: Data to be saved
        :return:
        """

        run_phase_name, run_phase_int = self._Loader.run_phase
        if run_phase_int < 4000:  # just before 'libraries_started' is when we start processing automation triggers.
            call_hooks = False
        else:
            call_hooks = True

        # print(f"_generic_class_storage_load_to_memory: {self._FullName} - incoming: {incoming}")

        storage_id = incoming["id"]

        hook_prefix = self._Parent._class_storage_load_hook_prefix,

        if call_hooks:
            global_invoke_all(f"_{hook_prefix}_before_load_",
                              called_by=self,
                              id=storage_id,
                              data=incoming,
                              )
        try:
            storage[storage_id] = klass(self,
                                        incoming,
                                        source=source,
                                        **kwargs)
            yield maybeDeferred(storage[storage_id]._init_, **kwargs)

        except Exception as e:
            logger.error("Error while creating {label} instance: {e}",
                         label=self._Parent._class_storage_load_hook_prefix,
                         e=e)
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")
            raise YomboWarning(f"Unable to create DB model: {e}")

        if call_hooks:
            global_invoke_all(f"_{hook_prefix}_loaded_",
                              called_by=self,
                              id=storage_id,
                              data=storage[storage_id],
                              )
        return storage[storage_id]

    # def _set_fake_data(self, value):
    #     if isinstance(value, bool):
    #         self._fake_data = value
    #
    #     if hasattr(super(), '_set_fake_data'):
    #         super()._set_fake_data(value)

    # def update_attributes_preprocess(self, incoming):
    #     """
    #     Allows parents to perform pre-process functions before the attribute is comited.
    #
    #     If the attribute shouldn't be commited, simply raise YomboWarning
    #
    #     :param name:
    #     :param value:
    #     :return:
    #     """
    #     pass
    #
    # def update_attributes_postprocess(self, incoming):
    #     """
    #     Allows parents to perform post-process functions after all subbmited items have been processed, but
    #     before a possible sync event.
    #
    #     This sends the incoming data for reference/usage.
    #
    #     :param name:
    #     :param value:
    #     :return:
    #     """
    #     pass

    # def update_attributes(self, incoming, source=None, session=None, broadcast=None):
    #     """
    #     Use to set attributes for the instance. This can used to edit the attributes as well.
    #
    #     This is 100% anti-pythonic. Here's why:
    #     If attributes are set internally, it's assumed that these come internally and are 100% pythonic. This is fine.
    #     There are times when things don't need to be synced to other other places:
    #     * If from AQMP/YomboAPI, then we just need to update the memory and database.
    #     * If from database (loading), then we just need to update memory and not Yombo API.
    #
    #     :param incoming: a dictionary containing key/value pairs to update.
    #     :param source:
    #     :return:
    #     """
    #     if hasattr(self, "_can_have_fake_data") and "_fake_data" in incoming:
    #         self._set_fake_data(incoming['_fake_data'])
    #
    #     hook_prefix = self._Parent._class_storage_load_hook_prefix,
    #     storage_id = getattr(self, self._primary_column)
    #     storage = getattr(self, self._class_storage_attribute_name)
    #     if broadcast in (None, True):
    #         global_invoke_all(f"_{hook_prefix}_before_update_",
    #                           called_by=self,
    #                           id=storage_id,
    #                           data=storage[storage_id],
    #                           )
    #
    #     if hasattr(super(), 'update_attributes'):
    #         super().update_attributes(incoming, source=source, session=session, broadcast=broadcast)
    #
    #     if broadcast in (None, True):
    #         global_invoke_all(f"_{hook_prefix}_updated_",
    #                           called_by=self,
    #                           id=storage_id,
    #                           data=storage[storage_id],
    #                           )
    #
    #     if hasattr(super(), 'update_attributes'):
    #         return
    #
    #     try:
    #         self.update_attributes_preprocess(incoming)
    #     except YomboWarning as e:
    #         logger.info("Skipping update attributes for {item_type}",
    #                     item_type=self._Parent._class_storage_load_hook_prefix)
    #         return
    #
    #     for name, value in incoming.items():
    #         super(LibraryDBModelMixin, self).__setattr__(name, value)
    #
    #     self.update_attributes_postprocess()
