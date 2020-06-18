#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
"""

.. note::

  * For library documentation, see: `Storage @ Library Documentation <https://yombo.net/docs/libraries/storage>`_


.. code-block:: python

   def _storage_backends_(self, **kwargs):
       return {
           "save_file_callback": self.save_file,
           "save_data_callback": self.save_data,
           "delete": self.delete,  # called with a dictionary reference of the file data
       }


Allows the system to store and retrieve files across difference platforms. This library only enables the core
features to peform these tasks, however, modules are required to store and retrieve items from different
platforms. This incldues S3, Dropbox, etc.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.25.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/storage.html>`_

"""
# Import python libraries
import datetime
# from mimetypes import MimeTypes
import ntpath
from os import path
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Union
from urllib.parse import urlparse

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin

from yombo.utils import random_string, sleep
from yombo.utils.dictionaries import clean_dict
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.storage")


class StorageItem(Entity, LibraryDBChildMixin):
    _Entity_type: ClassVar[str] = "Storage item"
    _Entity_label_attribute: ClassVar[str] = "storage_id"


class Storage(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Handles file storage.
    """
    storage: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "storage_id"
    _storage_attribute_name: ClassVar[str] = "storage"
    _storage_label_name: ClassVar[str] = "storage"
    _storage_class_reference: ClassVar = StorageItem
    _storage_pickled_fields: ClassVar[Dict[str, str]] = {"variables": "msgpack"}
    _storage_search_fields: ClassVar[str] = [
        "scheme", "netloc", "path"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "storage_id"

    storage = {}

    def _init_(self, **kwargs):
        # self.mime = MimeTypes()
        self.purge_expired_running = False

    @inlineCallbacks
    def _load_(self, **kwargs):
        data = yield global_invoke_all("_storage_backends_", called_by=self)

        for component, backends in data.items():
            if isinstance(backends, dict) is False:
                logger.warn("'_storage_backends_' must return a dictionary of storage backend types.")
                continue
            for scheme, attrs in backends.items():
                if scheme in self.storage:
                    logger.warn(f"Storage backends already has scheme type '{scheme}', skipping.")
                    continue
                self.storage[scheme] = attrs

        yield self.purge_expired()
        self._CronTab.new(self.purge_expired, mins=0, hours=4, label="Delete expired storage files.",
                          load_source="system")

    @inlineCallbacks
    def get(self, storage_id):
        """
        Retrieve a storage db object based on the file_id

        :param storage_id:
        :return:
        """
        data = yield self.db_select(row_id=storage_id)
        return data

    @inlineCallbacks
    def save_file(self, source_file, destination, delete_source=None, expires=None, public=None, mangle_name=None,
                  content_type=None, charset=None, extra=None):
        """
        Saves a file. Usually used when a file is on disk and needs to be uploaded.

        This should not be confused with:
         from yombo.utils.file import save_file
        Which saves the file locally, outside of the Yombo storage system.

        Destinations:
        file://path/file.
        s3://bucketname/path/file
        dropbox://path/file

        :param source_file:
        :param destination:
        :return:
        """
        if path.isfile(source_file) is False:
            raise YomboWarning(f"File doesn't exist: {source_file}")

        if delete_source is None:
            delete_source = True
        if expires is None:
            expires = 30
        if public is None:
            public = True
        if mangle_name is None:
            mangle_name = 1

        file_id = random_string(length=15)
        dest_parts, dest_parts_thumb, mangle_id = self.check_destination(destination, file_id, mangle_name)
        size = yield self._Files.size(source_file)
        results = yield maybeDeferred(self.storage[dest_parts.scheme]["save_file_callback"],
                                      source_file, dest_parts, dest_parts_thumb,
                                      delete_source, file_id, mangle_id, expires, public,
                                      extra)
        """
        new_path = "file://somehost/somepath/somefile_{index-id}.jpg
        """

        if content_type is None or charset is None:
            content_info = yield self._Files.mime_type_from_file(source_file)
            if content_type in (None, ""):
                content_type = content_info["content_type"]
            if charset in (None, ""):
                charset = content_info["charset"]

        new = StorageDB()
        new.id = file_id
        new.scheme = dest_parts.scheme
        new.username = dest_parts.username
        new.password = dest_parts.password
        new.netloc = dest_parts.netloc
        new.port = dest_parts.port
        new.path = dest_parts.path
        new.params = dest_parts.params
        new.query = dest_parts.query
        new.fragment = dest_parts.fragment
        new.mangle_id = mangle_id
        if expires > 0:
            new.expires = time() + (expires*86400)
        else:
            new.expires = 0
        new.public = public
        new.internal_url = results["internal_url"]
        new.external_url = results["external_url"]
        new.internal_thumb_url = results.get("internal_thumb_url", None)
        new.external_thumb_url = results.get("external_thumb_url", None)
        new.content_type = content_type
        new.charset = charset
        new.size = size
        new.created_at = round(time(), 3)
        new.file_path = results.get("file_path", None)
        new.file_path_thumb = results.get("file_path_thumb", None)
        new.variables = self._Tools.data_pickle(results.get("variables", {}))  # used by the various storage backends for their own use.
        yield new.save()

    @inlineCallbacks
    def save_data(self, source_data, destination, expires=None, public=None, mangle_name=None, content_type=None,
                  charset=None, extra=None):
        """
        Uploads data
        :param source_data:
        :param destination:
        :return:
        """
        if expires is None:
            expires = 30
        if public is None:
            public = True
        if mangle_name is None:
            mangle_name = 1

        file_id = random_string(length=15)

        dest_parts, dest_parts_thumb, mangle_id = self.check_destination(destination, file_id, mangle_name)
        results = yield maybeDeferred(self.storage[dest_parts.scheme]["save_data_callback"],
                                      source_data, dest_parts, dest_parts_thumb,
                                      file_id, mangle_id, expires, public, extra)

        # print(f" save data results: {results}")

        if content_type is None or charset is None:
            content_info = yield self._Files.mime_type_from_buffer(source_data)
            if content_type in (None, ""):
                content_type = content_info["content_type"]
            if charset in (None, ""):
                charset = content_info["charset"]

        new = StorageDB()
        new.id = file_id
        new.scheme = dest_parts.scheme
        new.username = dest_parts.username
        new.password = dest_parts.password
        new.netloc = dest_parts.netloc
        new.port = dest_parts.port
        new.path = dest_parts.path
        new.params = dest_parts.params
        new.query = dest_parts.query
        new.fragment = dest_parts.fragment
        new.mangle_id = mangle_id
        if expires > 0:
            new.expires = time() + (expires*86400)
        else:
            new.expires = 0
        new.public = public
        new.internal_url = results["internal_url"]
        new.external_url = results["external_url"]
        new.internal_thumb_url = results.get("internal_thumb_url", None)
        new.external_thumb_url = results.get("external_thumb_url", None)
        new.content_type = content_type
        new.charset = charset
        new.size = len(source_data)
        new.created_at = round(time(), 3)
        new.file_path = results.get("file_path", None)
        new.file_path_thumb = results.get("file_path_thumb", None)
        new.variables = self._Tools.data_pickle(results.get("variables", {}))  # used by the various storage backends for their own use.
        # print(f"new: {new} :: {new.__dict__}")
        yield new.save()

    @inlineCallbacks
    def delete(self, file_id):
        """
        Delete a file by it's id.

        :param file_id:
        :return:
        """
        print(f"Storage delete: {file_id}")
        file = yield self.get(file_id)
        print(f"Storage delete: 1a: {self.storage}")
        print(f"Storage delete: 1b: {file.scheme}")
        results = yield maybeDeferred(self.storage[file.scheme]["delete"], clean_dict(file.__dict__))
        print(f"Storage delete: 2")
        print(f"Results of deleting file '{file.id} {results}")
        print(f"Storage delete: 3")
        yield file.delete()
        return True

    @inlineCallbacks
    def purge_expired(self):
        """
        Iterate through all files and purge any expired ones. This call can take a while to complete.

        :return:
        """
        # print("purge expired: starting")
        if self.purge_expired_running:
            logger.info("purge_expired already running, skipping.")
            return
        self.purge_expired_running = True

        while True:
            records = yield self.db_select(where=["expires > 0 and expires < ?", int(time())], limit=50)
            # print(f"records: {records}")
            if len(records) == 0:
                self.purge_expired_running = False
                return

            for record in records:
                if record.scheme not in self.storage:
                    logger.warn("Unknown storage scheme type: {scheme}", scheme=record.scheme)
                else:
                    # print(f"purge expired: calling remote function")
                    results = yield maybeDeferred(self.storage[record.scheme]["delete"], clean_dict(record.__dict__))
                    # print(f"purge expired: done with remote, about to delete record from db")

                yield record.delete()
                # print(f"purge expired: done with db delete")
                yield sleep(0.02)

        self.purge_expired_running = False

    def check_destination(self, destination, file_id, mangle_name):
        """
        Checks the destinations and returns three items within a list:
        1) urlparsed results from the destination
        2) urlparse results from destination meant for thumbnails.
        3) an extra random id that is used to further hide the URL of the resource.

        :param destination:
        :param file_id:
        :param mangle_name:
        :return:
        """
        # print(f"storage: save file dest: {destination}")
        # print(f"storage: manglename: {mangle_name}")
        mangle_id = self._Hash.sha224_compact(random_string(length=100))[0:20]
        if mangle_name > 0:
            folder, filename = ntpath.split(destination)
            file, extension = path.splitext(filename)
            if mangle_name == 1:
                destination = f"{folder}/{file}_{file_id}_{mangle_id}{extension}"
                destination_thumb = f"{folder}/{file}_{file_id}_{mangle_id}_thumb{extension}"
            if mangle_name == 2:
                destination = f"{folder}/{file_id}_{mangle_id}{extension}"
                destination_thumb = f"{folder}/{file_id}_{mangle_id}_thumb{extension}"
            if mangle_name == 3:
                destination = f"{folder}/{file_id}_{mangle_id}"
                destination_thumb = f"{folder}/{file_id}_{mangle_id}_thumb"
            if mangle_name == 4:
                new_filename = self._Hash.sha256_compact(random_string(length=200))
                destination = f"{folder}/{new_filename}{extension}"
                destination_thumb = f"{folder}/{new_filename}{extension}_thumb"
            if mangle_name >= 5:
                new_filename = self._Hash.sha256_compact(random_string(length=200))
                destination = f"{folder}/{new_filename}"
                destination_thumb = f"{folder}/{new_filename}_thumb"

            # print(f"storage: save file new dest: {destination}")
        dest_parts = urlparse(destination)
        scheme = dest_parts.scheme
        if scheme not in self.storage:
            raise KeyError(f"Unknown file storage location type: {scheme}")
        dest_parts_thumb = urlparse(destination_thumb)
        return dest_parts, dest_parts_thumb, mangle_id

    def expand(self, daily_items=500):
        """
        Used to generate an extended path based on how many items per day will be generated. This
        helps to prevent a single directory containing to many files.

            >>> full_path = f"file://kitchen_webcam_motion/{self._Storage.expand(500)}/{int(round(time(), 3)*1000)}.jpg"

        :param daily_items: How many items are expected to be generated per day.
        :return:
        """
        if isinstance(daily_items, int) is False:
            raise YomboWarning("daily_items must be an int.")

        now = datetime.datetime.now()
        if daily_items <= 250:  # one folder per month. With thumbs: 7500 files per folder.
            return now.strftime("%Y/%m")  # returns the year/month: 2018/12 (december)
        if daily_items <= 500:  # one folder per week. With thumbs: 7000 files per folder.
            return now.strftime("%Y/%U")  # returns the year/week #: 2018/48)
        elif daily_items <= 3500:  # one folder per day. About 7000 files per folder.
            return now.strftime("%Y/%m_%d")  # returns the year/month_day: 2018/12_01 (december 1st)
        elif daily_items <= 84000:  # one folder per hour. About 7000 files per folder.
            # returns the year_week: 2018/12_01/12 (december 1st, 12th hour)
            return now.strftime("%Y/%m_%d/%H")
        elif daily_items <= 5040000:  # one folder per minute. About 7000 files per folder.
            # returns the year_week: 2018/12_01/12_30 (december 1st, 12:30)
            return now.strftime("%Y/%m_%d/%H_%M")
        else:  # That's a lot of files!!!
            # returns the year_week: 2018/12_01/12_30/20 (december 1st, 12:30:20)
            return now.strftime("%Y/%m_%d/%H_%M/%S")
