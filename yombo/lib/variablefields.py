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

logger = get_logger("library.variable_fields")


class VariableField(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
    """
    A class to manage a single variable field item.
    """
    _primary_column = "variable_field_id"  # Used by mixins

    @property
    def variable_group(self):
        try:
            return self._VariableGroups.group_by_id(self.variable_group_id)
        except KeyError:
            pass
        return None

    def __init__(self, parent, incoming, source=None):
        """
        Setup the variable field object using information passed in.

        :param incoming: A dict with all required items to create the class.
        :type incoming: dict

        """
        self._Entity_type = "Variable field"
        self._Entity_label_attribute = "field_machine_label"

        super().__init__(parent)
        self._setup_class_model(incoming, source=source)


class VariableFields(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Various variable tools.
    """
    variable_fields = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "variable_field"
    _class_storage_load_db_class = VariableField
    _class_storage_attribute_name = "variable_fields"
    _class_storage_search_fields = [
        "variable_field_id", "variable_group_id", "field_machine_label", "field_label", "field_description", "user_id"
    ]
    _class_storage_sort_key = "data_weight"

    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        yield self._class_storage_load_from_database()


    def fields(self, variable_group_id=None):
        """
        Gets available variable fields for a given variable_group_id.

        :param group_id: Field group_id to search for.
        :type group_id: str
        :return: Available variable fields.
        :rtype: dict
        """
        results = {}
        for field_id, field in self.variable_fields.items():
            if (variable_group_id is field or field.variable_group_id == variable_group_id):
                results[field_id] = field
        return results
