# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For library documentation, see: `Variables @ Library Documentation <https://yombo.net/docs/libraries/variables>`_


A library to get variables in various formats. Also used to send updates to Yombo API.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2017-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/variables.html>`_
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_db_model_mixin import LibraryDBModelMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.sync_to_everywhere_mixin import SyncToEverywhereMixin

logger = get_logger("library.variable_groups")


class VariableGroup(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
    """
    A class to manage a single variable group item.
    """
    _primary_column = "variable_group_id"  # Used by mixins

    def __init__(self, parent, incoming, source=None):
        """
        Setup the variable group object using information passed in.

        :param data: A dict with all required items to create the class.
        :type data: dict
        """
        self._Entity_type = "Variable group"
        self._Entity_label_attribute = "group_machine_label"
        super().__init__(parent)
        self._setup_class_model(incoming, source=source)


class VariableGroups(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Various variable tools.
    """
    variable_groups = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "variable_group"
    _class_storage_load_db_class = VariableGroup
    _class_storage_attribute_name = "variable_groups"
    _class_storage_search_fields = [
        "variable_group_id", "group_relation_id", "group_relation_type", "group_machine_label", "group_label"
    ]
    _class_storage_sort_key = "variable_group_id"

    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        yield self._class_storage_load_from_database()

    def groups(self, group_relation_type=None, group_relation_id=None):
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

    def fields(self, group_relation_type=None, group_relation_id=None):
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

    def data(self, group_relation_type=None, group_relation_id=None):
        """
        Used to get all available fields and any related data for a module or device.

        :param group_relation_type:
        :param group_relation_id:
        :return:
        """
        groups = self.groups(group_relation_type, group_relation_id)

        fields = {}
        for group_id, group in groups.items():
            fields.update(self._VariableFields.fields(group_id))

        # Have to re-sort the fields due to being all mixed up from the group selection above.
        fields = dict(sorted(iter(fields.items()), key=lambda i: getattr(i[1], 'field_weight')))

        results = {}
        for field_id, field in fields.items():
            # print(f"VG: data(): field: {field.__dict__}")
            field_machine_label = field.field_machine_label
            results[field_machine_label] = {"data": [], "decrypted": [], "display": [], "ref": []}

            # print(f"Field: {field.__dict__}")
            data_items = self._VariableData.data_by_field_id(field.variable_field_id)
            data_items = dict(sorted(iter(data_items.items()), key=lambda i: getattr(i[1], 'data_weight')))
            for data_id, item in data_items.items():
                results[field_machine_label]["data"].append(item.data)
                results[field_machine_label]["decrypted"].append(item.decrypted)
                results[field_machine_label]["display"].append(item.display)
                results[field_machine_label]["ref"].append(item)
        return results
