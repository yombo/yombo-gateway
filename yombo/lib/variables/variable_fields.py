# This file was created by Yombo for use with Yombo Python data automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For library documentation, see: `Variables @ Library Documentation <https://yombo.net/docs/libraries/variables>`_

The variable field class.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/data/html/current/_modules/yombo/lib/variables.html>`_
"""
# Import Yombo libraries
from yombo.core.log import get_logger
from yombo.core.entity import Entity
from yombo.mixins.sync_to_everywhere import SyncToEverywhere

logger = get_logger("library.variables.groups")


class VariableField(Entity, SyncToEverywhere):
    """
    A class to manage a single variable field item.
    """
    @property
    def variable_group(self):
        try:
            return self._Parent.group_by_id(self.variable_group_id)
        except KeyError:
            pass
        return None

    def __init__(self, parent, data, source=None):
        """
        Setup the variable field object using information passed in.

        :param data: A dict with all required items to create the class.
        :type data: dict

        """
        self._internal_label = "variable_fields"  # Used by mixins
        self._can_have_fake_data = True
        super().__init__(parent)

        self.variable_field_id = data["id"]

        # database columns
        self.user_id = None
        self.variable_group_id = None
        self.field_machine_label = None
        self.field_label = None
        self.field_description = None
        self.field_weight = None
        self.value_required = None
        self.value_max = None
        self.value_min = None
        self.value_casing = None
        self.encryption = None
        self.input_type_id = None
        self.default_value = None
        self.field_help_text = None
        self.multiple = None
        self.updated_at = None
        self.created_at = None

        self.update_attributes(data, source=source)
        self.start_data_sync()

    def __str__(self):
        """
        Print a string when printing the class.  This will return the data id so that
        the data can be identified and referenced easily.
        """
        return self.variable_field_id

    def asdict(self):
        """
        Export data variables as a dictionary.
        """
        return {
            "variable_field_id": str(self.variable_field_id),
            "user_id": str(self.user_id),
            "variable_group_id": str(self.variable_group_id),
            "field_machine_label": str(self.field_machine_label),
            "field_label": str(self.field_label),
            "field_description": str(self.field_description),
            "field_weight": str(self.field_weight),
            "value_required": str(self.value_required),
            "value_max": str(self.value_max),
            "value_min": str(self.value_min),
            "value_casing": str(self.value_casing),
            "encryption": str(self.encryption),
            "input_type_id": str(self.input_type_id),
            "default_value": str(self.default_value),
            "field_help_text": str(self.field_help_text),
            "multiple": str(self.multiple),
            "created_at": int(self.created_at),
            "updated_at": int(self.updated_at),
        }

    def __repl__(self):
        """
        Export data variables as a dictionary.
        """
        return self.asdict()
