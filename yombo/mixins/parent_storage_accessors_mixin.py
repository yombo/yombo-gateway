# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Mixin class for libraries and modules that allows easy access to the core attribute. For example, if the library
or module has an attribute named 'widgets' that stores various Widget instances, this mixin allows for easily
accessing that attribute and makes it available internally and externally through standardized calls.

Additionally, this makes the parent class semi-dictionary like with basic features such as iter, get/set item,
contains, length, etc.

This mixin should only be used by libraries and modules that want to add to_dict, to_database, etc. The following
class attributes are required to integrate these features:

* _storage_attribute_name - Used by mixins to get the database table name AND the name of the class
  attribute where the primary items are stored. For example: "widgets"
* _storage_attribute_sort_key - When sorting the storage attribute, use this field within each instance to sort by.
* _storage_fields - A list of columns that should be exported from to_dict/to_database/to_external.

Optional:
* _storage_pickled_fields - A dictionary to determine if any fields should be pickled when exporting. Dictionaries,
  lists, tuples, etc, must be pickled before exporting. The format of this dictionary:
  {'field_name', 'content_type'} This example pickles the the 'roles' attribute to msgpack then base64 encodes it:
  {"roles": "msgpack_base64"}
  This example {"roles": "json"} just converts it to a simple json string.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/mixins/parent_storage_accessors_mixin.html>`_
"""
# Import python libraries
from typing import Any, Optional

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred

# Import Yombo libraries
from yombo.constants import __version__
from yombo.utils.decorators.deprecation import deprecated


class ParentStorageAccessorsMixin:
    @inlineCallbacks
    def _stop_(self, **kwargs):
        """ Called during the second to last phase of shutdown."""
        if hasattr(self, "_storage_attribute_name"):
            class_data_items = getattr(self, self._storage_attribute_name)
            for item_id, item in class_data_items.items():
                if hasattr(item, '_stop_') and callable(item._stop_):
                    yield maybeDeferred(item._stop_)

    @inlineCallbacks
    def _unload_(self, **kwargs):
        """Called during the last phase of shutdown. We'll save any pending changes."""
        if hasattr(self, "_storage_attribute_name"):
            class_data_items = getattr(self, self._storage_attribute_name)
            for item_id, item in class_data_items.items():
                if hasattr(item, '_unload_') and callable(item._unload_):
                    yield maybeDeferred(item._unload_)

    def __contains__(self, item_requested):
        """
        .. note::

           The item you are searching for must be enabled.

        Checks to if a provided id, label, or machine_label exists. This can be used on commands, devices, modules,
        and nearly any other item within the framework.

            >>> if "137ab129da9318" in self._Commands:
            >>> if "living room light" in self._Commands:
            >>> if "insteonapi" in self._Modules:
            >>> if "bedroom_light" in self._Devices:

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when the requested item is not found.
        :param item_requested: The id, label, or machine_label, or other attribute to search for.
        :type item_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(item_requested)
            return True
        except:
            return False

    def __getitem__(self, item_requested: str):
        """
        .. note::

           The item you are searching for must be enabled.

        Checks to if a provided id, label, or machine_label exists. This can be used on commands, devices, modules,
        and nearly any other item within the framework.

            >>> if "137ab129da9318" in self._Commands:
            >>> if "living room light" in self._Commands:
            >>> if "insteonapi" in self._Modules:
            >>> if "bedroom_light" in self._Devices:

        .. note::

           The __getitem__ function is a shortcut to the get() function for the library. You
           can use either one. Some libraries offer more search choices and options using the
           get() method.

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when the requested item is not found.
        :param item_requested: The id, label, or machine_label, or other attribute to search for.
        :type item_requested: string
        :return: Returns the instance requested.
        :rtype: bool
        """
        return self.get(item_requested)

    def __setitem__(self, key: str, value: Any):
        """
        Generally, libraries prohibit setting values this way. Check the specific library for details.

        :raises Exception: Always raised.
        """
        if hasattr(self, "set") and callable(self.set) is True:
            return self.set(key, value)
        raise Exception("Not allowed.")

    def __delitem__(self, item_requested: str):
        """
        Generally, libraries prohibit deleting values this way. Check the specific library for details.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ Return an __iter__() """
        return self._get_storage_data().__iter__()

    def __len__(self):
        """
        Returns an int of the number of items configured for the library.

        :return: The number of commands configured.
        :rtype: int
        """
        return len(self._get_storage_data())

    def keys(self):
        """
        Returns all the ID's for the library data.

        :return: A list of command IDs.
        :rtype: list
        """
        return self._get_storage_data().keys()

    def items(self):
        """
        Gets a list of tuples representing the commands configured.

        :return: A list of tuples.
        :rtype: list
        """
        return self._get_storage_data().items()

    def values(self):
        return self._get_storage_data().values()

    def sorted(self, key: Optional[str] = None):
        """
        Returns a sorted dictionary that is by "key". The key can be any attribute within the requested object, such as
        label, area_label, machine_label.

        :param key: Attribute contained in a device to sort by, default: area_label
        :return: All devices, sorted by key.
        """
        items_to_sort = self._get_storage_data()
        if key is None:
            key = self._storage_attribute_sort_key
        return dict(sorted(iter(items_to_sort.items()), key=lambda i: getattr(i[1], key)))

    def to_database_all(self) -> dict:
        """
        Returns all items as a dictionary, that can be used to re-create into a database.

        :return:
        """
        results = {}
        storage = self._get_storage_data()
        for item_id, item in storage.items():
            results[item_id] = item.to_database()
        return results

    def to_dict_all(self) -> dict:
        """
        Returns all items as a dictionary.

        :return:
        """
        results = {}
        storage = self._get_storage_data()
        for item_id, item in storage.items():
            results[item_id] = item.to_dict(include_meta=False)
        return results

    def get_all(self, filters: Optional[dict] = None, **kwargs):
        """
        Returns a list of all items, unless filters are provided.  Be careful, this is not a deepcopy!

        :param filters: A dictionary of key/values to filter results.
        :return:
        """
        # storage = self._get_storage_data()
        results = []

        def check_filter(input):
            for key, value in filters.items():
                if key in input:
                    if input[key] == value:
                        return True
            return False

        for item_id, item in self.sorted().items():
            if filters is not None:
                data = item.to_dict(include_meta=False)
                if check_filter(data) is False:
                    continue
            results.append(item)
        return results

    @deprecated(deprecated_in="0.24.0", removed_in="0.25.0",
                current_version=__version__,
                details="get_all() instead.")
    def to_external_all(self, filters: Optional[dict] = None, **kwargs) -> list:
        """
        Returns all items as a list. Typically used to output to API.

        :param filters: A dictionary of key/values to filter results.
        :return:
        """
        results = []
        storage = self._get_storage_data()

        def check_filter(input):
            print("check_filter....")
            for key, value in filters.items():
                if key in input:
                    if input[key] == value:
                        return True
            return False

        for item_id, item in storage.items():
            data = item.to_dict(include_meta=False)
            if filters is not None:
                if check_filter(data) is False:
                    continue
            results.append(data)
        return results

    def _get_storage_data(self):
        """ Helper to get the library storage attribute. """
        return getattr(self, self._storage_attribute_name)
