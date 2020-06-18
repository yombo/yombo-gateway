# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Child of the ParentStorageAccessorsMixin. This allows children to properly display details about itself. The primary
class (parent) should have the matching ParentStorageAccessorsMixin.


 Additionally, the child must have the following
class variables defined:

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/mixins/child_storage_accessors_mixin.html>`_
"""
from copy import deepcopy
import json
import msgpack
from typing import Any, ClassVar, Dict, List, Optional, Union

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("mixins.library_db_parent_processors_mixin")


class ChildStorageAccessorsMixin:
    _additional_to_dict_fields: ClassVar[list] = []

    def _get_attribute(self, name: str, value: Optional[Any] = None):
        """
        Un-pythonic way of getting an attribute, primarily used for to_dict. This allows classes to modify
        the data before it's sent.

        :param name:
        :param value:
        :return:
        """
        get_attribute_name = f"_get_{name}_attribute"
        # if name == "energy_map":
        #     print(f"_get_attribute: {name}")
        #     print(type(getattr(self, name)))
        #     print(getattr(self, name))

        if hasattr(self, get_attribute_name):
            attribute_getter_name_callable = getattr(self, get_attribute_name)
            return attribute_getter_name_callable(value=value)
        else:
            if value is not None:
                return value
            else:
                return getattr(self, name)

    def _set_attribute(self, name: str, value: Optional[Any] = None, return_value: Optional[bool] = None):
        """
        Un-pythonic way of setting an attribute. This allows classes to modify the data before it's saved.

        :param name:
        :param value:
        :param return_value:
        :return:
        """
        set_attribute_name = f"_set_{name}_attribute"
        if hasattr(self, set_attribute_name):
            named_callable = getattr(self, set_attribute_name)
            return named_callable(value=value, return_value=return_value)
        else:
            if return_value is True:
                return value
            else:
                return setattr(self, name, value)

    def to_dict(self, to_database: Optional[bool] = None, to_external: Optional[bool] = None,
                include_meta: Optional[bool] = None, incoming_data: Optional[dict] = None,
                filters: Optional[dict] = None):
        """
        Represents the current child class as a dictionary. Depending on the final destination, the output can be
        altered as needed.

        Do not set to_database and to_event to true at same time.

        :param to_database: If true, only the database fields will be returned.
        :param to_external: If true, the dict will be formated for JSONAPI format.
        :param include_meta: If true, will include additional details, typically used internally.
        :param incoming_data: Use this data instead of the class data. Used for testing and Yombo API sync.
        :return:
        """
        if to_database is None:
            to_database = False
        if to_external is None:
            to_external = False
        if include_meta is None:
            include_meta = False

        if to_database is True and to_external is True:
            raise YomboWarning("to_dict() cannot have both to_database and to_external as true.")

        data = {}
        if include_meta is True and hasattr(self, "_meta"):
            meta = self._meta
        else:
            meta = {}

        def add_field(new_field):
            """ Add a field to the results. """
            if field == "id":
                data["id"] = self._primary_field_id
            else:
                if incoming_data is not None:
                    data[new_field] = self._get_attribute(new_field, value=incoming_data[new_field])
                else:
                    data[new_field] = self._get_attribute(new_field)

        try:
            for field in self._Parent._storage_fields:
                if incoming_data is None:
                    add_field(field)
                else:
                    if field in incoming_data:
                        add_field(field)
            if to_database is False and to_external is False:
                for field in self._additional_to_dict_fields:
                    add_field(field)
        except Exception as e:
            logger.warn("Error generating to_dict() data: {e}", e=e)
        if (incoming_data is None and "id" not in data) or (incoming_data is not None and "id" in incoming_data):
            data["id"] = getattr(self, self._Parent._storage_primary_field_name)

        if hasattr(self, "to_dict_postprocess"):  # allow children to have final say in content.
            try:
                self.to_dict_postprocess(data, meta=meta, to_external=to_external, to_database=to_database,
                                         include_meta=include_meta)
            except Exception as e:
                logger.warn("(2) Error generating to_dict postprocess: {e}", e=e)
        if include_meta is False:
            return deepcopy(data)
        else:
            return {"data": deepcopy(data), "meta": deepcopy(meta)}

    def to_database(self, incoming_data: Optional[dict] = None) -> Dict[str, Any]:
        """ Nearly the same as to_dict(to_database=True), but pickles the columns before returning results. """
        # print(f"to_database: {self.to_dict(to_database=True, include_meta=False)}")
        # print(f"pickle_data_records(to_database): {self.pickle_data_records(self.to_dict(to_database=True, include_meta=False))}")
        return self._Parent.pickle_data_records(self.to_dict(to_database=True,
                                                             include_meta=False,
                                                             incoming_data=incoming_data))

    def to_external(self) -> Dict[str, Any]:
        """ The same as to_dict(to_external=True, ), but pickles the columns before returning results. """
        return self.to_dict(to_external=True, include_meta=False)

    def to_json(self, **kwargs):
        """
        Creates a json representation of this item. Basically, takes to_dict, and converts to json.
        :return:
        """
        return json.dumps(self.to_dict(**kwargs))

    def to_msgpack(self, **kwargs):
        """
        Creates a msgpack representation of this item. Basically, takes to_dict, and converts to json.
        :return:
        """
        return msgpack.packb(self.to_dict(**kwargs))
