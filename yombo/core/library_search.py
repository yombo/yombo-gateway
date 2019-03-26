# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Library Search @ Module Development <https://yombo.net/docs/core/library_search>`_


Add get, get_advanced, search, and search_advanced functions to libraries.

.. warning::

   This helper module is intended for libraries, but can be adapted to modules as well.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/library_search.html>`_
"""
from collections import OrderedDict

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.utils import do_search_instance


class LibrarySearch(object):
    """
    Implements get and search functions.
    """
    def get_all(self):
        """
        Returns a copy of the items list.  Be careful, this is not a deepcopy!
        :return:
        """
        return getattr(self, self.item_search_attribute).copy()

    def sorted(self, key=None):
        """
        Returns an OrderedDict, sorted by "key". The key can be any attribute within the device object, such as
        label, area_label, etc.

        :param key: Attribute contained in a device to sort by, default: area_label
        :type key: str
        :return: All devices, sorted by key.
        :rtype: OrderedDict
        """
        items_to_sort = getattr(self, self.item_search_attribute)
        if key is None:
            key = self.item_sort_key
        return OrderedDict(sorted(iter(items_to_sort.items()), key=lambda i: getattr(i[1], key)))

    def get(self, item_requested):
        """
        Get an item by it's ID or machine_label. Unlike search(), this doesn't use any fuzzy logic to search
        for the requested item. This is a wrapper for get_advanced().

        :param item_requested: The item ID or machine label to get.
        :param multiple: If multiple items should be returned, default is False.
        :return:
        """
        items_to_search = getattr(self, self.item_search_attribute)
        # print(f"library search: get: item_search_attribute {items_to_search}")

        if isinstance(item_requested, str) is False:
            raise YomboWarning("item_requested must be a string.")

        if item_requested in items_to_search:
            return items_to_search[item_requested]

        if hasattr(self, "item_criteria_keys"):
            criteria = {}
            for key in self.item_criteria_keys:
                criteria[key] = item_requested
        else:
            criteria = {
                    "machine_label": item_requested,
                }
        # print(f"library search: get: criteria {criteria}")
        return self.get_advanced(criteria, multiple=False)

    def get_advanced(self, criteria, multiple=None):
        """
        Searching through the items looking for exact matches using various criteria.

        If multiple is True, returns a dictionary of items; otherwise returns the single item.

        self._Nodes.get_advanced({"item_type": "scene"})
        self._Commands.get_advanced({"machine_label": "on"})

        :param criteria: A dictionary of elements and values to search for.
        :param multiple: If multiple items should be returned, default is False.
        :return:
        """
        items_to_search = getattr(self, self.item_search_attribute)
        if multiple is None:
            multiple = True
        results = {}
        for item_id, item in items_to_search.items():
            for key, value in criteria.items():
                if key not in self.item_searchable_attributes:
                    continue

                # print("searching: %s" % item._instance)
                # if value == item._instance[key]:
                if value == getattr(item, key):
                    if multiple is False:
                        return item
                    results[item_id] = item
        if len(results) == 0:
            raise KeyError(f"No matching {self.item_search_attribute} found.")
        return results

    def search(self, item_requested, limiter=None, max_results=None, status=None):
        """
        Search VS Get: Get doesn't use fuzzy logic, search does.

        A simple wrapper around do_search to add searching for item_id, machine_label, and label. Use
        search_advanced directly for more advanced searching.

        This performs a fuzzy search and can be adjust using the limiter argument. By default, the
        searched items must be at least 90% (.90) match.

        .. note::

            The the built in methods below can also be used to search.

                >>> self._Nodes["13ase45"]

            or:

                >>> self._Nodes["numeric"]

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param item_requested: A string to search for. Will look at the id's, machine_label, label, item_type, destination
        :type item_requested: string
        :param limiter: Default: .90 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter: float
        :param max_results: How many results to return.
        :type max_results: int
        :param status: Default: 1 - The status of the item to check for.
        :type status: int
        :return: Returns a list of items if 1 or more are found.
        :rtype: list
        """
        if isinstance(item_requested, str) is False:
            raise YomboWarning("item_requested must be a string.")
        if max_results is None:
            max_results = 1

        if hasattr(self, "item_criteria_keys"):
            search_attributes = {}
            for key in self.item_criteria_keys:
                search_attributes.append({
                    "field": key,
                    "value": item_requested,
                    "limiter": limiter,
                    },
                )
        else:
            search_attributes = [
                {
                    "field": "item_id",
                    "value": item_requested,
                    "limiter": limiter,
                },
                {
                    "field": "machine_label",
                    "value": item_requested,
                    "limiter": limiter,
                },
                {
                    "field": "label",
                    "value": item_requested,
                    "limiter": limiter,
                }
            ]
        if status is None:
            required_field = None
            required_value = None
        else:
            if isinstance(status, int) is False:
                raise YomboWarning("Status must be an int.")
            required_field = "status"
            required_value = status

        return self.search_advanced(search_attributes, limiter, max_results=max_results,
                                    required_field=required_field, required_value=required_value
                                    )["items"]

    def search_advanced(self, search_attributes, limiter=None, max_results=None,
                        required_field=None, required_value=None,
                        ignore_field=None, ignore_value=None):
        """
        An advanced search that accepts an array if items to search for. Allows searching multiple
        attributes and different attributes. It's suggested to use search() for basic searching.

        This performs a fuzzy search and can be adjust using the limiter argument. By default, the
        searched items must be at least 90% (.90) match.

        .. note::

            Can use the built in methods below or use search/get to include "item_type" limiter:

                >>> self._Nodes["13ase45"]

            or:

                >>> self._Nodes["numeric"]

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param search_attributes: A string to search for. Will look at the id's, machine_label, label, item_type, destination
        :type search_attributes: list, dict
        :param limiter: Default: .90 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter: float
        :param max_results: How many results to return, defaults to found items above the limiter.
        :type max_results: int
        :param required_field: If set, this field will be required to match. Typically used for status.
        :type required_field: str
        :param required_value: Any value to require
        :type required_value: mixed
        :param ignore_field: If set, and this field matches the result, the result will be dropped.
        :type ignore_field: str
        :param ignore_value: Any value to force a result to be dropped.
        :type ignore_value: mixed
        :return: Pointer to requested item.
        :rtype: dict
        """
        items_to_search = getattr(self, self.item_search_attribute)

        try:
            # logger.debug("item.search() is about to call do_search_instance...: %s" % item_requested)
            results = do_search_instance(search_attributes,
                                         items_to_search,
                                         allowed_keys=self.item_searchable_attributes,
                                         limiter=limiter,
                                         max_results=max_results,
                                         required_field=required_field,
                                         required_value=required_value,
                                         ignore_field=ignore_field,
                                         ignore_value=ignore_value,
                                         )
            # logger.debug("found item by search: others: {others}", others=others)
            if results["was_found"]:
                return results

            raise KeyError(f"item not found.")
        except YomboWarning as e:
            raise KeyError(f"Searched for {self.item_search_attribute}, but had problems: {e}")
