# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For library documentation, see: `Variables @ Library Documentation <https://yombo.net/docs/libraries/variable_data>`_


A library to get variables in various formats. Also used to send updates to Yombo API.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/variable_data.html>`_
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_db_model_mixin import LibraryDBModelMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.sync_to_everywhere_mixin import SyncToEverywhereMixin

logger = get_logger("library.variable_data")


class VariableDataItem(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
    """
    A class to manage a single variable data item.
    """
    _primary_column = "variable_data_id"  # Used by mixins

    @property
    def variable_fields(self):
        try:
            return self._VariableFields.get(self.variable_field_id)
        except KeyError:
            pass
        return None

    def __init__(self, parent, incoming, source=None):
        """
        Setup the variable data object using information passed in.

        :param incoming: A dict with all required items to create the class.
        :type incoming: dict
        """
        self._Entity_type = "Variable data"
        self._Entity_label_attribute = "variable_data_id"
        super().__init__(parent)
        self._setup_class_model(incoming, source=source)

        # computed values
        self.decrypted = self.data
        self.display = self.data

    @inlineCallbacks
    def _init_(self):
        """
        Used to decrypt any data.  This is called by the variables class during setup.

        :return:
        """
        try:
            self._decrypted = yield self._Parent._GPG.decrypt(self.data)
        except YomboWarning:
            self._decrypted = None
        self._display = self._Parent._GPG.display_encrypted(self.data)

    def asdict(self):
        """
        Export data variables as a dictionary.
        """
        return {
            "variable_data_id": str(self.variable_data_id),
            "user_id": str(self.user_id),
            "gateway_id": str(self.gateway_id),
            "variable_field_id": str(self.variable_field_id),
            "variable_relation_id": str(self.variable_relation_id),
            "variable_relation_type": str(self.variable_relation_type),
            "data": str(self.data),
            "display": str(self.display),
            "data_weight": str(self.data_weight),
            "created_at": int(self.created_at),
            "updated_at": int(self.updated_at),
        }



class VariableData(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Manages variable data items.
    """
    variable_data = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "variable_data"
    _class_storage_load_db_class = VariableDataItem
    _class_storage_attribute_name = "variable_data"
    _class_storage_search_fields = [
        "variable_data_id", "variable_field_id", "variable_relation_id", "variable_relation_type", "user_id"
    ]
    _class_storage_sort_key = "data_weight"

    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        yield self._class_storage_load_from_database()

    def data(self, variable_relation_type=None, variable_relation_id=None):
        """
        Gets available variable data for a given device_id or module_id.

        :param variable_relation_type: Either "module" or "device".
        :type variable_relation_type: str
        :param variable_relation_id: The id of the module or device to find.
        :type variable_relation_id: str
        :return: Available variable data.
        :rtype: dict
        """
        results = {}
        for item_id, item in self.variable_data.items():
            if (variable_relation_type is None or item.variable_relation_type == variable_relation_type) and \
                    (variable_relation_id is None or item.variable_relation_id == variable_relation_id):
                results[item_id] = item
        return results

    def data_by_field_id(self, field_id):
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
