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
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/variablegroups.html>`_
"""
from typing import Any, ClassVar, Dict, List, Optional

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import VariableGroupSchema
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin

logger = get_logger("library.variable_groups")


class VariableGroup(Entity, LibraryDBChildMixin):
    """
    A class to manage a single variable group item.
    """
    _Entity_type: ClassVar[str] = "Variable group"
    _Entity_label_attribute: ClassVar[str] = "group_machine_label"


class VariableGroups(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Various variable tools.
    """
    variable_groups: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "variable_group_id"
    _storage_attribute_name: ClassVar[str] ="variable_groups"
    _storage_label_name: ClassVar[str] ="variable_group"
    _storage_class_reference: ClassVar = VariableGroup
    _storage_schema: ClassVar = VariableGroupSchema()
    _storage_search_fields: ClassVar[List[str]] = [
        "variable_group_id", "group_relation_id", "group_relation_type", "group_machine_label", "group_label"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "group_weight"
    _storage_attribute_sort_key_order: ClassVar[str] = "asc"

    @inlineCallbacks
    def _init_(self, **kwargs) -> None:
        """
        Load variable groups into memory.
        """
        yield self.load_from_database()

    def groups(self,
               group_relation_type: Optional[str] = None,
               group_relation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Gets available variable data for a given group_relation_type or relation_id.

        :param group_relation_type: Either "module" or "device".
        :type group_relation_type: str
        :param group_relation_id: The id of the module or device to find.
        :type group_relation_id: str
        :return: Available variable groups.
        :rtype: list
        """
        results = {}
        for item_id, item in self.variable_groups.items():
            if (group_relation_type is None or item.group_relation_type == group_relation_type) and \
                    (group_relation_id is None or item.group_relation_id == group_relation_id):
                results[item_id] = item
        return results

    def fields(self,
               group_relation_type: Optional[str] = None,
               group_relation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all the available fields for a given type and id.

        :param group_relation_type:
        :param group_relation_id:
        :return:
        """
        groups = self.groups(group_relation_type, group_relation_id)
        fields = {}
        for group_id, group in groups.items():
            fields.update(self._VariableFields.fields(group_id))

        # Have to re-sort the fields due to being all mixed up from the group selection above.
        return dict(sorted(iter(fields.items()), key=lambda i: getattr(i[1], 'field_weight')))

    # def data(self,
    #          relation_type: Optional[str] = None,
    #          relation_id: Optional[str] = None) -> Dict[str, Any]:
    #     """
    #     Used to get all available fields and any related data for a module or device.
    #
    #     :param relation_type:
    #     :param relation_id:
    #     :return:
    #     """
    #     groups = self.groups(relation_type, relation_id)
    #     print(f":variable grounds, data: groups: {groups}")
    #
    #     fields = {}
    #     for group_id, group in groups.items():
    #         print(f":variable grounds, data: fields: {self._VariableFields.fields(group_id)}")
    #         fields.update(self._VariableFields.data(relation_type, relation_id))
    #
    #     # Have to re-sort the fields due to being all mixed up from the group selection above.
    #     fields = dict(sorted(iter(fields.items()), key=lambda i: getattr(i[1], 'field_weight')))
    #
    #     results = {}
    #     for field_id, field in fields.items():
    #         field_machine_label = field.field_machine_label
    #         results[field_machine_label] = {"data": [], "decrypted": [], "display": [], "ref": []}
    #
    #         data_items = self._VariableData.data_by_field_id(field.variable_field_id)
    #         data_items = dict(sorted(iter(data_items.items()), key=lambda i: getattr(i[1], 'data_weight')))
    #         for data_id, item in data_items.items():
    #             results[field_machine_label]["data"].append(item.data)
    #             results[field_machine_label]["decrypted"].append(item.decrypted)
    #             results[field_machine_label]["display"].append(item.display)
    #             results[field_machine_label]["ref"].append(item)
    #     return results
