# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Mixin class to sync changes to Yombo Cloud and local database, maybe other places too in the future.

This mixin must be the last in the chain.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
from time import time

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import sleep

logger = get_logger("mixins.sync_to_everywhere")

SYNC_TO_DB = 1
SYNC_TO_YOMBO = 2
SYNC_TO_CONFIG = 4

CLASS_DEFAULTS = {
    "_sync_enabled": False,
    "_sync_delay": 5,
    "_sync_max_delay": 30,
    "_syncs_to_db": True,  # If true, sync to db
    "_syncs_to_yombo": True,  # If true, sync to yombo API.
    "_syncs_to_config": False,  # If true, sync to yombo API.
    "_sync_init_complete": True,
}


class SyncToEverywhereMixin(object):
    def __setattr__(self, name, value):
        """ Monitor set attributes and possibly sync changes. """
        if hasattr(self, "_sync_init_complete") is False:
            self.__dict__[name] = value
            return
        self.update_attributes({name: value})

    def __init__(self, *args, **kwargs):
        for key, value in CLASS_DEFAULTS.items():
            if hasattr(self, key) is False:
                self.__dict__[key] = value

        # print(f"SyncToEverywhereMixin update_attributes __dict__ : {self.__dict__}")
        # print(f"SyncToEverywhereMixin update_attributes __dict__ : {SyncToEverywhereMixin.__dict__}")

        self._sync_calllater_db_time = None
        self._sync_calllater_db = None
        self._sync_calllater_yombo_time = None
        self._sync_calllater_yombo = None
        self._sync_calllater_config_time = None
        self._sync_calllater_config = None

        self._sync_mode = self._sync_compute_sync_mode()
        super().__init__(*args, **kwargs)

    @inlineCallbacks
    def _unload_(self):
        # print(f"end item unloaded: {self._Parent._class_storage_load_hook_prefix}")
        yield self.flush_sync()
        yield sleep(.1)

    def set(self, name, value, source=None, session=None):
        self.update_attributes(name, value, source, session)

    def _sync_compute_sync_mode(self, source=None):
        sync_mode = 0
        if source is None or source.lower() == "internal":
            if self._syncs_to_db:
                sync_mode |= SYNC_TO_DB
            if self._syncs_to_yombo:
                sync_mode |= SYNC_TO_YOMBO
            if self._syncs_to_config:
                sync_mode |= SYNC_TO_CONFIG
            # sync_mode = SYNC_TO_DB + SYNC_TO_YOMBO
        elif source == "amqp":
            if self._syncs_to_db:
                sync_mode |= SYNC_TO_DB
            if self._syncs_to_config:
                sync_mode |= SYNC_TO_CONFIG
        elif source == "database":
            sync_mode = 0
        else:
            raise YomboWarning("source attribute must be one of: database, amqp, internal, or none.")
        return sync_mode

    def update_attributes(self, incoming, source=None, session=None, broadcast=None):
        """
        Use to set attributes for the instance.

        This is 100% anti-pythonic. Here's why:
        If attributes are set internally, it's assumed that these come internally and are 100% pythonic. This is fine.
        There are times when things don't need to be synced to other other places:
        * If from AQMP/YomboAPI, then we just need to update the memory and database.
        * If from database (loading), then we just need to update memory and not Yombo API.

        :param name:
        :param value:
        :param source:
        :return:
        """
        if hasattr(self, "_sync_init_complete") is False:
            for name, value in incoming.items():
                self.__dict__[name] = value
            return
        # print(f"sync everywhere: {self._Entity_type}, update attrs start")

        sync_mode = self._sync_compute_sync_mode(source)
        if hasattr(self._Parent, "_class_storage_db_columns"):
            db_columns = self._Parent._class_storage_db_columns
        else:
            db_columns = None

        has_changes = False
        for name, value in incoming.items():
            if db_columns is not None:
                if (not hasattr(self, name) or getattr(self, name) != value) and \
                        name in db_columns:
                    has_changes = True
            self.__dict__[name] = value

        if has_changes is True and sync_mode > 0:
            self.sync_item_data(sync_mode, session)

    def _set_fake_data(self, value):
        if isinstance(value, bool):
            self._fake_data = value

            if value is True:
                self.stop_data_sync()
            else:
                self.start_data_sync()

    def start_data_sync(self):
        """ Allow sync to happen. """
        # print(f"Field: {self.__dict__}")

        if self._fake_data is True:
            self._sync_enabled = False
            return
        self._sync_enabled = True

    def stop_data_sync(self):
        """ Disable syncing. """
        self.flush_sync()
        self._sync_enabled = False

    def sync_allowed(self):
        """ A method that be overridden to determine if sync should take place."""
        return True

    def sync_item_data(self, sync_mode=None, session=None):
        """
        Sets up a call later to sync to the local database and/or Yombo API.

        :return:
        """
        if sync_mode is None:
            sync_mode = self._sync_compute_sync_mode()
        # logger.debug("sync_to_database starting. Mode: {mode}", mode=sync_mode)
        if self.sync_allowed() is False or self._fake_data is True or self._sync_enabled is not True:
            return

        if sync_mode & SYNC_TO_DB:
            if self._sync_calllater_db is not None and self._sync_calllater_db.active():
                # print("%s: on_change called.. still active.")
                self._sync_calllater_db.cancel()
                if self._sync_calllater_db_time is not None and self._sync_calllater_db_time < time() - self._sync_max_delay:
                    # print("forcing save now..!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    self.__dict__["_sync_calllater_db"] = None
                    self.__dict__["_sync_calllater_db_time"] = None
                    # object.__setattr__(self, "_sync_calllater_db", None)
                    # object.__setattr__(self, "_sync_calllater_db_time", None)
                    reactor.callLater(0.01, self._do_sync_db)
                else:
                    # print("saving node later..")
                    self.__dict__["_sync_calllater_db"] = reactor.callLater(self._sync_delay, self._do_sync_db)
                    # object.__setattr__(self, "_sync_calllater_db", reactor.callLater(self._sync_delay, self._do_sync_db))
            else:
                self.__dict__["_sync_calllater_db"] = reactor.callLater(self._sync_delay, self._do_sync_db)
                self.__dict__["_sync_calllater_db_time"] = time()
                # object.__setattr__(self, "_sync_calllater_db", reactor.callLater(self._sync_delay, self._do_sync_db))
                # object.__setattr__(self, "_sync_calllater_db_time", time())

        if sync_mode & SYNC_TO_YOMBO:
            if self._sync_calllater_yombo is not None and self._sync_calllater_yombo.active():
                # print("%s: on_change called.. still active.")
                self._sync_calllater_yombo.cancel()
                if self._sync_calllater_yombo_time is not None and self._sync_calllater_yombo_time < time() - self._sync_max_delay:
                    # print("forcing save now..!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    self.__dict__["_sync_calllater_yombo"] = None
                    self.__dict__["_sync_calllater_yombo_time"] = None
                    # object.__setattr__(self, "_sync_calllater_yombo", None)
                    # object.__setattr__(self, "_sync_calllater_yombo_time", None)
                    reactor.callLater(0.01, self._do_sync_yombo, session)
                else:
                    # print("saving node later..")
                    self.__dict__["_sync_calllater_yombo"] = reactor.callLater(self._sync_delay, self._do_sync_yombo, session)
                    # object.__setattr__(self, "_sync_calllater_yombo", reactor.callLater(self._sync_delay, self._do_sync_yombo, session))
            else:
                self.__dict__["_sync_calllater_yombo"] = reactor.callLater(self._sync_delay, self._do_sync_yombo, session)
                self.__dict__["_sync_calllater_yombo_time"] = time()
                # object.__setattr__(self, "_sync_calllater_yombo", reactor.callLater(self._sync_delay, self._do_sync_yombo, session))
                # object.__setattr__(self, "_sync_calllater_yombo_time", time())

        if sync_mode & SYNC_TO_CONFIG:
            if self._sync_calllater_config is not None and self._sync_calllater_config.active():
                # print("%s: on_change called.. still active.")
                self._sync_calllater_config.cancel()
                if self._sync_calllater_config_time is not None and self._sync_calllater_config_time < time() - self._sync_max_delay:
                    # print("forcing save now..!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    self.__dict__["_sync_calllater_config"] = None
                    self.__dict__["_sync_calllater_config_time"] = None
                    # object.__setattr__(self, "_sync_calllater_config", None)
                    # object.__setattr__(self, "_sync_calllater_config_time", None)
                    reactor.callLater(0.01, self._do_sync_yombo, session)
                else:
                    # print("saving node later..")
                    self.__dict__["_sync_calllater_config"] = reactor.callLater(self._sync_delay, self._do_sync_yombo)
                    # object.__setattr__(self, "_sync_calllater_config", reactor.callLater(self._sync_delay, self._do_sync_yombo))
            else:
                self.__dict__["_sync_calllater_config"] = reactor.callLater(self._sync_delay, self._do_sync_yombo)
                self.__dict__["_sync_calllater_config_time"] = time()
                # object.__setattr__(self, "_sync_calllater_config", reactor.callLater(self._sync_delay, self._do_sync_yombo))
                # object.__setattr__(self, "_sync_calllater_config_time", time())

    @inlineCallbacks
    def flush_sync(self):
        """
        Checks if there's a pending sync. If so, then do it now.

        :return:
        """
        if self._sync_calllater_db is not None and self._sync_calllater_db.active():
            self._sync_calllater_db.cancel()
            yield self._do_sync_db()

        # if self._sync_calllater_yombo is not None and self._sync_calllater_yombo.active():
        #     self._sync_calllater_yombo.cancel()
        #     yield self._do_sync_yombo()

    @inlineCallbacks
    def _do_sync_db(self):
        """
        Does the actual sync to database. This clears any pending callLater as well.

        :return:
        """
        if self._sync_calllater_db is not None and self._sync_calllater_db.active():
            self._sync_calllater_db.cancel()
            self.__dict__["_sync_calllater_db"] = None
            self.__dict__["_sync_calllater_db_time"] = None
            # object.__setattr__(self, "_sync_calllater_db", None)
            # object.__setattr__(self, "_sync_calllater_db_time", None)

        logger.info("_do_sync_db")
        save_func_name = f"save_{self._Parent._class_storage_attribute_name}"
        if hasattr(self._Parent._LocalDB, save_func_name):
            dbsave = getattr(self._Parent._LocalDB, save_func_name)
            yield dbsave(self)
        else:
            yield self._Parent._LocalDB.generic_item_save(self._Parent._class_storage_attribute_name, self)

        # if self._Parent._LocalDB.generic_item_functions_available(self._Parent._class_storage_attribute_name):
        #     yield self._Parent._LocalDB.generic_item_save(self._Parent._class_storage_attribute_name, self)
        # else:
        #     dbsave = getattr(self._Parent._LocalDB, f"save_{self._Parent._class_storage_attribute_name}")
        #     yield dbsave(self)

    def _do_sync_config(self):
        """
        This function must be set within the class being used in. This is bascially a callback to the save
        function so the item can save itself.
        :return:
        """
        if self._sync_calllater_yombo is not None and self._sync_calllater_yombo.active():
            self._sync_calllater_yombo.cancel()
            self.__dict__["_sync_calllater_config"] = None
            self.__dict__["_sync_calllater_config_time"] = None
            # object.__setattr__(self, "_sync_calllater_config", None)
            # object.__setattr__(self, "_sync_calllater_config_time", None)

        logger.info("_do_sync_config")

    # @inlineCallbacks
    def _do_sync_yombo(self, session):
        """
        Does the actual sync to Yombo API.

        :return:
        """
        if self._sync_calllater_yombo is not None and self._sync_calllater_yombo.active():
            self._sync_calllater_yombo.cancel()
            self.__dict__["_sync_calllater_yombo"] = None
            self.__dict__["_sync_calllater_yombo_time"] = None
            # object.__setattr__(self, "_sync_calllater_yombo", None)
            # object.__setattr__(self, "_sync_calllater_yombo_time", None)

        logger.info("_do_sync_yombo")
