# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
A complementary class to the LibraryDBModelMixin class. This should be used in all child classes for libraries that
use the LibraryDBModelMixin.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
from time import time

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred, Deferred

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("mixins.library_db_child_mixin")

CLASS_DEFAULTS = {
    "_fake_data": False,
    "_sync_init_complete": True,
}


class LibraryDBChildMixin:

    def __init__(self, *args, **kwargs):
        # print(self.__dict__)
        for key, value in CLASS_DEFAULTS.items():
            if hasattr(self, key) is False:
                self.__dict__[key] = value
        self._setup_class_columns()  # From LibraryDBChildMixin
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        """ Allows this class to be accessed list a dictionary. """
        return getattr(self, key)

    def __repr__(self):
        """
        Returns some info about the current child object.

        :return: Returns some info about the current child object.
        :rtype: string
        """
        return f"<{self._Entity_type}: {getattr(self, self._Entity_label_attribute)}>"

    def _init_(self, **kwargs):
        """ Called so the class can run deferreds (yield) or complete any setups items. """
        if hasattr(super(), '_init_'):
            super()._init_(**kwargs)

    def _set_fake_data(self, value):
        if isinstance(value, bool):
            self._fake_data = value

        if hasattr(super(), '_set_fake_data'):
            super()._set_fake_data(value)

    @inlineCallbacks
    def _unload_(self, **kwargs):
        """Called during the last phase of shutdown. We'll save any pending changes."""
        if hasattr(self, "_class_storage_attribute_name"):
            class_data_items = getattr(self, self._class_storage_attribute_name)
            for item_id, item in class_data_items.items():
                # print(f"item.... checking unload")
                if hasattr(item, '_unload_'):
                    # print("item.... has unload")
                    unload = getattr(item, "_unload_")
                    if callable(unload):
                        # print("item.... calling unload")
                        yield maybeDeferred(unload)

    def _setup_class_columns(self):
        """ Creates class instance variables to match the DB columns. """
        self.__dict__[str(self._primary_column)] = None
        for field in self._Parent._class_storage_db_columns:
            self.__dict__[field] = None

    def _setup_class_model(self, incoming, source):
        # print(f"_setup_class_model: incoming: {incoming}")
        setattr(self, str(self._primary_column), incoming["id"])
        self.update_attributes(incoming, source=source)  # From SyncToEverywhereMixin

        if hasattr(self, "start_data_sync"):
            self.start_data_sync()
        # print(f"_setup_class_model: incoming: ..................... Done")

    @property
    def _class_storage_db_columns(self):
        """
        Gets a list of fields that should be synced....Everything but the ID.

        Override this function to create custom field list.

        This function gets it's values from the LocalDB library.

        :return:
        """
        fields = self._Parent._LocalDB.get_table_columns(self._class_storage_attribute_name)
        if "id" in fields:
            fields.remove("id")
        return fields

    def asdict(self):
        """ Returns the current object as a dictionary. """
        results = {"id": getattr(self, self._primary_column)}
        for field in self._Parent._class_storage_db_columns:
            results[field] = getattr(self, field)
        return results

    def as_reference_postprocess(self, incoming):
        """ Allow reference dictionary to modified before being returned. """
        pass

    def as_reference(self):
        """ Returns a dictionary used that can be used to send externally. """
        data = {"id": getattr(self, self._primary_column)}
        for field in self._Parent._class_storage_db_columns:
            data[field] = getattr(self, field)
        self.as_reference_postprocess(data)

        return {
            "meta": {
                "source": self._FullName,
                "gateway_id": self.gateway_id,
                "primary_field": self._primary_column,
            },
            "data": data
        }

    def update_attributes_preprocess(self, incoming):
        """
        Allows parents to perform pre-process functions before the attribute is comited.

        If the attribute shouldn't be commited, simply raise YomboWarning

        :param name:
        :param value:
        :return:
        """
        pass

    def update_attributes_postprocess(self, incoming):
        """
        Allows parents to perform post-process functions after all subbmited items have been processed, but
        before a possible sync event.

        This sends the incoming data for reference/usage.

        :param name:
        :param value:
        :return:
        """
        pass

    def update_attributes(self, incoming, source=None, session=None, broadcast=None):
        """
        Use to set attributes for the instance. This can used to edit the attributes as well.

        This is 100% anti-pythonic. Here's why:
        If attributes are set internally, it's assumed that these come internally and are 100% pythonic. This is fine.
        There are times when things don't need to be synced to other other places:
        * If from AQMP/YomboAPI, then we just need to update the memory and database.
        * If from database (loading), then we just need to update memory and not Yombo API.

        :param incoming: a dictionary containing key/value pairs to update.
        :param source:
        :return:
        """
        if hasattr(self, "_sync_init_complete") is False:
            for name, value in incoming.items():
                self.__dict__[name] = value
            return
        # print(f"library db child: {self._Entity_type}, update attrs start")

        if hasattr(self, "_can_have_fake_data") and "_fake_data" in incoming:
            self._set_fake_data(incoming['_fake_data'])

        # print(f"LibraryDBChildMixin update_attributes __dict__ : {self.__dict__}")
        # print(f"LibraryDBChildMixin update_attributes __dict__ : {LibraryDBChildMixin.__dict__}")

        hook_prefix = self._Parent._class_storage_load_hook_prefix
        storage_id = getattr(self, self._primary_column)

        try:
            self.update_attributes_preprocess(incoming)
        except YomboWarning as e:
            logger.info("Skipping update attributes for {item_type}",
                        item_type=self._Parent._class_storage_load_hook_prefix)
            return

        if broadcast in (None, True) and self._Loader.run_phase[1] >= 6500:
            # print(f"calling hook: {hook_prefix}")
            global_invoke_all(f"_{hook_prefix}_before_update2_",
                              called_by=self,
                              id=storage_id,
                              data=self,
                              )

        if hasattr(super(), 'update_attributes'):
            super().update_attributes(incoming, source=source, session=session)
        else:
            for name, value in incoming.items():
                self.__dict__[name] = value

        if broadcast in (None, True) and self._Loader.run_phase[1] >= 6500:
            global_invoke_all(f"_{hook_prefix}_updated2_",
                              called_by=self,
                              id=storage_id,
                              data=self,
                              )

        try:
            self.update_attributes_preprocess(incoming)
        except YomboWarning as e:
            logger.info("Skipping update attributes for {item_type}",
                        item_type=self._Parent._class_storage_load_hook_prefix)
            return
