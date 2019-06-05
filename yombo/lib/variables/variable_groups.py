# This file was created by Yombo for use with Yombo Python data automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For library documentation, see: `Variables @ Library Documentation <https://yombo.net/docs/libraries/variables>`_

The variable group class.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/data/html/current/_modules/yombo/lib/variables.html>`_
"""
# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.log import get_logger
from yombo.mixins.sync_to_everywhere import SyncToEverywhere

logger = get_logger("library.variables.groups")


class VariableGroup(Entity, SyncToEverywhere):
    """
    A class to manage a single variable group item.
    """

    def __init__(self, parent, data, source=None):
        """
        Setup the variable group object using information passed in.

        :param data: A dict with all required items to create the class.
        :type data: dict

        """
        self._internal_label = "variable_fields"  # Used by mixins
        super().__init__(parent)

        self.variable_group_id = data["id"]

        # database columns
        self.user_id = None
        self.group_relation_id = None
        self.group_relation_type = None
        self.group_machine_label = None
        self.group_label = None
        self.group_description = None
        self.group_weight = None
        self.status = None
        self.updated_at = None
        self.created_at = None

        self.update_attributes(data, source=source)
        self.start_data_sync()

    def __str__(self):
        """
        Print a string when printing the class.  This will return the data id so that
        the data can be identified and referenced easily.
        """
        return self.variable_group_id

    def asdict(self):
        """
        Export data variables as a dictionary.
        """
        return {
            "variable_group_id": str(self.variable_group_id),
            "group_relation_id": str(self.group_relation_id),
            "group_relation_type": str(self.group_relation_type),
            "group_machine_label": str(self.group_machine_label),
            "group_label": str(self.group_label),
            "group_description": str(self.group_description),
            "group_weight": str(self.group_weight),
            "status": str(self.status),
            "created_at": int(self.created_at),
            "updated_at": int(self.updated_at),
        }

    def __repl__(self):
        """
        Export data variables as a dictionary.
        """
        return self.asdict()
