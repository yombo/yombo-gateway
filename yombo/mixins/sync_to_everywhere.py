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

logger = get_logger("mixins.sync_to_everywhere")

SYNC_TO_DB = 1
SYNC_TO_YOMBO = 2
SYNC_TO_CONFIG = 4


class SyncToEverywhere(object):
    @property
    def _sync_fields(self):
        """
        Gets a list of fields that should be synced....Everything but the ID.

        Override this function to create custom field list.

        This function gets it's values from the LocalDB library.

        :return:
        """
        fields = self._Parent._LocalDB.get_table_fields(self._internal_label)
        if "id" in fields:
            fields.remove("id")
        return fields

    def __init__(self, *args, **kwargs):
        # if self._internal_label == "devices": print("sync everywhere init..... 1")
        self._sync_enabled = False
        # if self._internal_label == "devices": print(f"sync everywhere init.....enabled: {self._sync_enabled}")
        self._sync_delay = 5
        self._sync_enabled = True
        self._sync_enabled = False
        self._sync_max_delay = 30
        self._sync_calllater_db_time = None
        self._sync_calllater_db = None
        self._sync_calllater_yombo_time = None
        self._sync_calllater_yombo = None
        self._sync_calllater_config_time = None
        self._sync_calllater_config = None

        if not hasattr(self, "_syncs_to_db"):
            self._syncs_to_db = True     # If true, sync to db
        if not hasattr(self, "_syncs_to_yombo"):
            self._syncs_to_yombo = True  # If true, sync to yombo API.
        if not hasattr(self, "_syncs_to_config"):
            self._syncs_to_config = False  # If true, sync to yombo API.
        self._sync_mode = 0

        if self._syncs_to_db:
            self._sync_mode |= SYNC_TO_DB
        if self._syncs_to_yombo:
            self._sync_mode |= SYNC_TO_YOMBO
        if self._syncs_to_config:
            self._sync_mode |= SYNC_TO_CONFIG

        # print(f"sync mode for: {self._internal_label} = {self._sync_mode}")
        # print(f"sync fields:{self._sync_fields}")

        if hasattr(self, "_can_have_fake_data") and self._can_have_fake_data is True:
            self._fake_data = False
        super().__init__()

    def __setattr__(self, name, value):
        if hasattr(self, '_internal_label'):
            # if self._internal_label == "devices": print(f"Sync start: name2: {name}")
            # logger.debug("Sync start: '{internal}', name: {name}",
            #              internal='ll', name=name)
            if hasattr(self, '_sync_enabled'):
                # if self._internal_label == "devices": print(f"Sync start: name2.1:  enabled: {self._sync_enabled} , {name} = {value}")
                if self._sync_enabled is True and name in self._sync_fields:
                    # if self._internal_label == "devices": print(f"Sync start: name3: {name}")
                    if not hasattr(self, name) or getattr(self, name) != value:
                        # if self._internal_label == "devices": print(f"Sync start: name5: {name}")
                        # logger.debug("Sync sending: '{internal}', name: {name} label: {label}",
                        #              internal=self._internal_label, name=name, label=self.__str__())
                        self.sync_item_data(self._sync_mode)
        super(SyncToEverywhere, self).__setattr__(name, value)

    def set(self, name, value, source=None, session=None):
        self.update_attributes(name, value, source, session)

    def update_attribute(self, name, value, source=None, session=None):
        """
        Use to set a single for the instance.

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
        sync_mode = 0
        if source is None or source.lower() == "internal":
            if self._syncs_to_db:
                sync_mode |= SYNC_TO_DB
            if self._syncs_to_yombo:
                sync_mode |= SYNC_TO_YOMBO
            if self._syncs_to_config:
                sync_mode |= SYNC_TO_CONFIG
            sync_mode = SYNC_TO_DB + SYNC_TO_YOMBO
        elif source == "amqp":
            if self._syncs_to_db:
                sync_mode |= SYNC_TO_DB
            if self._syncs_to_config:
                sync_mode |= SYNC_TO_CONFIG
        elif source == "database":
            sync_mode = 0
        else:
            raise YomboWarning("source attribute must be one of: database, amqp, internal, or none.")

        has_changes = False
        if (not hasattr(self, name) or getattr(self, name) != value) and name in self._sync_fields:
            has_changes = True

        super(SyncToEverywhere, self).__setattr__(name, value)

        if has_changes is True and sync_mode > 0:
            self.sync_item_data(sync_mode, session)

    def update_attributes(self, incoming, source=None, session=None):
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
        sync_mode = 0
        if source is None or source.lower() == "internal":
            if self._syncs_to_db:
                sync_mode |= SYNC_TO_DB
            if self._syncs_to_yombo:
                sync_mode |= SYNC_TO_YOMBO
            if self._syncs_to_config:
                sync_mode |= SYNC_TO_CONFIG
            sync_mode = SYNC_TO_DB + SYNC_TO_YOMBO
        elif source == "amqp":
            if self._syncs_to_db:
                sync_mode |= SYNC_TO_DB
            if self._syncs_to_config:
                sync_mode |= SYNC_TO_CONFIG
        elif source == "database":
            sync_mode = 0
        else:
            raise YomboWarning("source attribute must be one of: database, amqp, internal, or none.")

        if hasattr(self, "_can_have_fake_data") and self._fake_data is True and \
                "_fake_data" in incoming:
            self._set_fake_data(incoming['_fake_data'])
            self._fake_data = False

        has_changes = False
        for name, value in incoming.items():
            if (not hasattr(self, name) or getattr(self, name) != value) and name in self._sync_fields:
                has_changes = True
            super(SyncToEverywhere, self).__setattr__(name, value)

        if has_changes is True and sync_mode > 0:
            self.sync_item_data(sync_mode, session)

    def _set_fake_data(self, value):
        if isinstance(value, bool):
            if value is True:
                self.stop_data_sync()
            else:
                self.start_data_sync()
            self._fake_data = value

    def start_data_sync(self):
        """ Allow sync to happen. """
        if hasattr(self, "_fake_data") and self._fake_data is True:
            self._sync_enabled = False
        self._sync_enabled = True
        # if self._internal_label == "devices": print(f"start_data_sync: {self._sync_enabled}, label: {self.label}")

    def stop_data_sync(self):
        """ Disable syncing. """
        self.flush_sync()
        self._sync_enabled = False

    def sync_allowed(self):
        """ A method that be overridden to determine if sync should take place."""
        return True

    def sync_item_data(self, sync_mode, session=None):
        """
        Sets up a call later to sync to the local database and/or Yombo API.

        :return:
        """
        logger.info("sync_to_database starting. Mode: {mode}", mode=sync_mode)
        if self.sync_allowed() is False or (hasattr(self, "_fake_data") and self._fake_data is True):
            return

        if sync_mode & SYNC_TO_DB:
            if self._sync_calllater_db is not None and self._sync_calllater_db.active():
                # print("%s: on_change called.. still active.")
                self._sync_calllater_db.cancel()
                if self._sync_calllater_db_time is not None and self._sync_calllater_db_time < time() - self._sync_max_delay:
                    # print("forcing save now..!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    object.__setattr__(self, "_sync_calllater_db", None)
                    object.__setattr__(self, "_sync_calllater_db_time", None)
                    reactor.callLater(0.01, self._do_sync_db)
                else:
                    # print("saving node later..")
                    object.__setattr__(self, "_sync_calllater_db", reactor.callLater(self._sync_delay, self._do_sync_db))
            else:
                object.__setattr__(self, "_sync_calllater_db", reactor.callLater(self._sync_delay, self._do_sync_db))
                object.__setattr__(self, "_sync_calllater_db_time", time())

        if sync_mode & SYNC_TO_YOMBO:
            if self._sync_calllater_yombo is not None and self._sync_calllater_yombo.active():
                # print("%s: on_change called.. still active.")
                self._sync_calllater_yombo.cancel()
                if self._sync_calllater_yombo_time is not None and self._sync_calllater_yombo_time < time() - self._sync_max_delay:
                    # print("forcing save now..!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    object.__setattr__(self, "_sync_calllater_yombo", None)
                    object.__setattr__(self, "_sync_calllater_yombo_time", None)
                    reactor.callLater(0.01, self._do_sync_yombo, session)
                else:
                    # print("saving node later..")
                    object.__setattr__(self, "_sync_calllater_yombo", reactor.callLater(self._sync_delay, self._do_sync_yombo, session))
            else:
                object.__setattr__(self, "_sync_calllater_yombo", reactor.callLater(self._sync_delay, self._do_sync_yombo, session))
                object.__setattr__(self, "_sync_calllater_yombo_time", time())

        if sync_mode & SYNC_TO_CONFIG:
            if self._sync_calllater_config is not None and self._sync_calllater_config.active():
                # print("%s: on_change called.. still active.")
                self._sync_calllater_config.cancel()
                if self._sync_calllater_config_time is not None and self._sync_calllater_config_time < time() - self._sync_max_delay:
                    # print("forcing save now..!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    object.__setattr__(self, "_sync_calllater_config", None)
                    object.__setattr__(self, "_sync_calllater_config_time", None)
                    reactor.callLater(0.01, self._do_sync_yombo, session)
                else:
                    # print("saving node later..")
                    object.__setattr__(self, "_sync_calllater_config", reactor.callLater(self._sync_delay, self._do_sync_yombo))
            else:
                object.__setattr__(self, "_sync_calllater_config", reactor.callLater(self._sync_delay, self._do_sync_yombo))
                object.__setattr__(self, "_sync_calllater_config_time", time())

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
            object.__setattr__(self, "_sync_calllater_db", None)
            object.__setattr__(self, "_sync_calllater_db_time", None)

        logger.info("_do_sync_db")
        dbsave = getattr(self._Parent._LocalDB, f"save_{self._internal_label}")
        yield dbsave(self)

    def _do_sync_config(self):
        """
        This function must be set within the class being used in. This is bascially a callback to the save
        function so the item can save itself.
        :return:
        """
        if self._sync_calllater_yombo is not None and self._sync_calllater_yombo.active():
            self._sync_calllater_yombo.cancel()
            object.__setattr__(self, "_sync_calllater_yombo", None)
            object.__setattr__(self, "_sync_calllater_yombo_time", None)

        logger.info("_do_sync_config")

    # @inlineCallbacks
    def _do_sync_yombo(self, session):
        """
        Does the actual sync to Yombo API.

        :return:
        """
        if self._sync_calllater_yombo is not None and self._sync_calllater_yombo.active():
            self._sync_calllater_yombo.cancel()
            object.__setattr__(self, "_sync_calllater_yombo", None)
            object.__setattr__(self, "_sync_calllater_yombo_time", None)

        logger.info("_do_sync_yombo")
