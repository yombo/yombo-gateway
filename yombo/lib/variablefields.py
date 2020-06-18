# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For library documentation, see: `Variables @ Library Documentation <https://yombo.net/docs/libraries/variables>`_


A library to get variables in various formats. Also used to send updates to Yombo API.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2017-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/variablefields.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import VariableFieldSchema
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin

logger = get_logger("library.variable_fields")


class VariableField(Entity, LibraryDBChildMixin):
    """
    A class to manage a single variable field item.
    """
    _Entity_type: ClassVar[str] = "Variable field"
    _Entity_label_attribute: ClassVar[str] = "field_machine_label"

    @property
    def variable_group(self):
        try:
            return self._VariableGroups.group_by_id(self.variable_group_id)
        except KeyError:
            pass
        return None

    # def __init__(self, parent, **kwargs) -> None:
    #     """
    #     Setup a new user instance.
    #
    #     :param parent: A reference to the users library.
    #     """
    #     print(f"variable field init, kwargs: {kwargs}")
    #     super().__init__(parent, **kwargs)
    #     print(f"variable field init, dict: {self.__dict__}")


class VariableFields(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Various variable tools.
    """
    variable_fields: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "variable_field_id"
    _storage_attribute_name: ClassVar[str] ="variable_fields"
    _storage_label_name: ClassVar[str] ="variable_field"
    _storage_class_reference: ClassVar = VariableField
    _storage_schema: ClassVar = VariableFieldSchema()
    _storage_search_fields: ClassVar[List[str]] = [
        "variable_field_id", "variable_group_id", "field_machine_label", "field_label", "field_description", "user_id"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "field_weight"
    _storage_attribute_sort_key_order: ClassVar[str] = "asc"

    @inlineCallbacks
    def _init_(self, **kwargs) -> None:
        """
        Loads the variable fields into memory.
        """
        yield self.load_from_database()

    def fields(self, variable_group_id: str) -> Dict[str, Any]:
        """
        Gets available variable fields for a given variable_group_id.

        :param variable_group_id: Group id to search for.
        :type group_id: str
        :return: Available variable fields.
        :rtype: dict
        """
        results = {}
        for field_id, field in self.variable_fields.items():
            if variable_group_id is field or field.variable_group_id == variable_group_id:
                results[field_id] = field
        return results

    def data(self, relation_type: str, relation_id: str, field_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Gets data for the provided relation type and id, optionally filtered by field_id.

        :param relation_type: Usually, either 'module' or 'device'.
        :param relation_id: The device id or module id.
        :param field_id: Optionally, only return the data items with the provided field.
        """
        results = {}
        for field_id, field in fields.items():
            field_machine_label = field.field_machine_label
            results[field_machine_label] = {"data": [], "decrypted": [], "display": [], "ref": []}

            data_items = self._VariableData.data_by_field_id(field.variable_field_id)
            data_items = dict(sorted(iter(data_items.items()), key=lambda i: getattr(i[1], 'data_weight')))
            for data_id, item in data_items.items():
                results[field_machine_label]["data"].append(item.data)
                results[field_machine_label]["decrypted"].append(item.decrypted)
                results[field_machine_label]["display"].append(item.display)
                results[field_machine_label]["ref"].append(item)
        return results

        results = {}
        for item_field_id, item_field in self.variable_fields.items():
            if field_id is None or item_field_id == field_id:
                if item_field["variable_relation_type"] == relation_type and\
                        item_field["variable_relation_id"] == relation_id:
                    results[item_field_id] = item_field
        return results
