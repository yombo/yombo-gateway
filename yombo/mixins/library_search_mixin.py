# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Library Search @ Module Development <https://yombo.net/docs/mixins/library_search_mixin>`_


Add get, get_advanced, search, and search_advanced functions to libraries.

.. warning::

   This helper module is intended for libraries, but can be adapted to modules as well.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/mixins/library_search_mixin.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.utils import do_search_instance


class LibrarySearchMixin:
    """
    Implements get and search functions.
    """
    _storage_attribute_sort_key: ClassVar[str] = "label"
    _storage_attribute_sort_key_order: ClassVar[str] = "asc"

    def get(self, item_requested):
        """
        Get an item by it's ID or machine_label. Unlike search(), this doesn't use any fuzzy logic to search
        for the requested item. This is a wrapper for get_advanced().

        :param item_requested: The item ID or machine label to get.
        :return:
        """
        items_to_search = getattr(self, self._storage_attribute_name)
        if self._storage_class_reference is not None and \
                isinstance(item_requested, self._storage_class_reference):
            return item_requested

        if isinstance(item_requested, str) is False:
            raise ValueError(f"item_requested must be a string, received: {item_requested}")

        if item_requested in items_to_search:
            return items_to_search[item_requested]

        if hasattr(self, "_storage_search_fields"):
            criteria = {}
            for key in self._storage_search_fields:
                criteria[key] = item_requested
        else:
            criteria = {
                    "machine_label": item_requested,
                }

        if "machine_label" in criteria:
            criteria["machine_label"] = criteria["machine_label"].lower()

        try:
            return self.get_advanced(criteria, multiple=False)
        except KeyError:
            raise KeyError(f"No matching {self._storage_attribute_name} found: {item_requested}")

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
        items_to_search = getattr(self, self._storage_attribute_name)
        if multiple is None:
            multiple = True
        results = {}
        for item_id, item in items_to_search.items():
            for key, value in criteria.items():
                if key not in self._storage_search_fields:
                    continue

                if value == getattr(item, key):
                    if multiple is False:
                        return item
                    results[item_id] = item
        if len(results) == 0:
            # for item_id, item in items_to_search.items():
            #     print(f"Searching: {item_id}: {item.__dict__}")
            raise KeyError(f"No matching {self._storage_attribute_name} found.")
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
        :param max_results: How many results to return, 0 = unlimited above cutoff.
        :type max_results: int
        :param status: Default: 1 - The status of the item to check for.
        :type status: int
        :return: Returns a list of items if 1 or more are found.
        :rtype: list
        """
        if isinstance(item_requested, str) is False:
            raise ValueError("item_requested must be a string.")
        if max_results is None:
            max_results = 0

        if hasattr(self, "_storage_search_fields"):
            search_attributes = []
            for key in self._storage_search_fields:
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
                raise ValueError("Status must be an int.")
            required_field = "status"
            required_value = status

        return self.search_advanced(search_attributes, limiter, max_results=max_results,
                                    required_field=required_field, required_value=required_value
                                    )["values"]

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
        :param max_results: How many results to return, defaults to 0 to find items above the limiter.
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
        items_to_search = getattr(self, self._storage_attribute_name)

        try:
            # logger.debug("item.search() is about to call do_search_instance...: %s" % item_requested)
            results = do_search_instance(search_attributes,
                                         items_to_search,
                                         allowed_keys=self._storage_search_fields,
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
            raise KeyError(f"Searched for {self._storage_attribute_name}, but had problems: {e}")
