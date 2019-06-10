# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Mixin class for that uses '_class_storage_attribute_name' to make the module or library act like
a dictionary.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred


class AccessorsMixin(object):
    @inlineCallbacks
    def _stop_(self, **kwargs):
        """ Called during the second to last phase of shutdown."""
        if hasattr(self, "_class_storage_attribute_name"):
            class_data_items = getattr(self, self._class_storage_attribute_name)
            for item_id, item in class_data_items.items():
                if hasattr(item, '_stop_'):
                    stop_ = getattr(item, "_stop_")
                    if callable(stop_):
                        yield maybeDeferred(stop_)

    @inlineCallbacks
    def _unload_(self, **kwargs):
        """Called during the last phase of shutdown. We'll save any pending changes."""
        if hasattr(self, "_class_storage_attribute_name"):
            class_data_items = getattr(self, self._class_storage_attribute_name)
            for item_id, item in class_data_items.items():
                if hasattr(item, '_unload_'):
                    unload = getattr(item, "_unload_")
                    if callable(unload):
                        yield maybeDeferred(unload)

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

    def __getitem__(self, item_requested):
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

    def __setitem__(self, item_requested, value):
        """
        Generally, libraries prohibit setting values this way. Check the specific library for details.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, item_requested):
        """
        Generally, libraries prohibit deleting values this way. Check the specific library for details.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ Return an __iter__() """
        return getattr(self, self._class_storage_attribute_name).__iter__()

    def __len__(self):
        """
        Returns an int of the number of items configured for the library.

        :return: The number of commands configured.
        :rtype: int
        """
        return len(getattr(self, self._class_storage_attribute_name))

    def keys(self):
        """
        Returns all the ID's for the library data.

        :return: A list of command IDs.
        :rtype: list
        """
        return list(getattr(self, self._class_storage_attribute_name).keys())

    def items(self):
        """
        Gets a list of tuples representing the commands configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(getattr(self, self._class_storage_attribute_name).items())

    def values(self):
        return list(getattr(self, self._class_storage_attribute_name).values())

    def get_all(self):
        """
        Returns a copy of the items list.  Be careful, this is not a deepcopy!
        :return:
        """
        return getattr(self, self._class_storage_attribute_name).copy()

    def sorted(self, key=None):
        """
        Returns a sorted dictionary that is by "key". The key can be any attribute within the device object, such as
        label, area_label, etc.

        :param key: Attribute contained in a device to sort by, default: area_label
        :type key: str
        :return: All devices, sorted by key.
        :rtype: dict
        """
        items_to_sort = getattr(self, self._class_storage_attribute_name)
        if key is None:
            key = self._class_storage_sort_key
        return dict(sorted(iter(items_to_sort.items()), key=lambda i: getattr(i[1], key)))
