# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For library documentation, see: `Variables @ Library Documentation <https://yombo.net/docs/libraries/variable_data>`_


A library to get variables in various formats. Also used to send updates to Yombo API.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/variabledata.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import VariableDataSchema
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin

logger = get_logger("library.variable_data")


class VariableDataItem(Entity, LibraryDBChildMixin):
    """
    A class to manage a single variable data item.
    """
    _Entity_type: ClassVar[str] = "Variable data"
    _Entity_label_attribute: ClassVar[str] = "variable_data_id"

    @property
    def variable_fields(self):
        try:
            return self._VariableFields.get(self.variable_field_id)
        except KeyError:
            pass
        return None

    def __init__(self, parent, **kwargs) -> None:
        """
        Setup the variable data object using information passed in.

        :param incoming: A dict with all required items to create the class.
        :type incoming: dict
        """
        super().__init__(parent, **kwargs)

        # Values will be properly set in _init_ - might need to be decrypted.
        self.decrypted = self.data
        self.display = self.data

    def _init_(self) -> None:
        """
        Used to decrypt any variable data.  Called by library_db_parent_mixin.

        :return:
        """
        self.decrypted = None
        self.display = self.data
        if self.data_content_type != "string":
            try:
                print(f"varidata, requesting data unpick: {self.data}")
                self.decrypted = self._Tools.data_unpickle(self.data, self.data_content_type)
                self.display = "-----ENCRYPTED DATA-----"
            except ValueError as e:
                self.decrypted = self.data
            except YomboWarning as e:
                logger.warn("Error trying to decode variable data: {e}", e=e)


class VariableData(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages variable data items.
    """
    _storage_primary_field_name: ClassVar[str] = "variable_data_id"
    variable_data: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_attribute_name: ClassVar[str] ="variable_data"
    _storage_label_name: ClassVar[str] ="variable_data"
    _storage_class_reference: ClassVar = VariableDataItem
    _storage_schema: ClassVar = VariableDataSchema()
    _storage_search_fields: ClassVar[List[str]] = [
        "variable_data_id", "variable_field_id", "variable_relation_id", "variable_relation_type", "user_id"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "data_weight"
    _storage_attribute_sort_key_order: ClassVar[str] = "asc"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework and loads the variable data.
        """
        yield self.load_from_database()

    def data(self, relation_type: str, relation_id: str, field_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Gets available variable data for a given device_id or module_id.

        :param relation_type: Usually, either 'module' or 'device'.
        :param relation_id: The device id or module id.
        :param field_id: Optionally, only return the data items with the provided field.
        """
        data_items = {}
        # print(f"vdd: relation_type={relation_type}, relation_id={relation_id}, field_id={field_id}")
        for item_id, item in self.variable_data.items():
            if item["variable_relation_type"] == relation_type and item["variable_relation_id"] == relation_id:
                # print(f"vdd: {item_id} = {item.__dict__}")
                if field_id is not None and item["variable_field_id"] != field_id:
                    continue
                data_items[item_id] = item

        data_items = dict(sorted(iter(data_items.items()), key=lambda i: getattr(i[1], 'data_weight')))
        # print(f"vdd: data_items 2: {data_items}")

        results = {}
        for item_id, item in data_items.items():
            field = self._VariableFields.get(item["variable_field_id"])
            field_machine_label = field.field_machine_label
            if field_machine_label not in results:
                results[field.field_machine_label] = {"data": [], "decrypted": [], "display": [], "ref": []}
            results[field_machine_label]["data"].append(item.data)
            results[field_machine_label]["decrypted"].append(item.decrypted)
            results[field_machine_label]["display"].append(item.display)
            results[field_machine_label]["ref"].append(item)
        # print(f"vdd: results: {results}")
        return results

    def data_by_field_id(self, field_id: str) -> Dict[str, Any]:
        """
        Gets all available data items for the provided field.

        :param field_id:
        :return:
        """
        results = {}
        for item_id, item in self.variable_data.items():
            if item.variable_field_id == field_id:
                results[item_id] = item
        return results
