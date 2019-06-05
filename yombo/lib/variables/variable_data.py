# This file was created by Yombo for use with Yombo Python data automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For library documentation, see: `Variables @ Library Documentation <https://yombo.net/docs/libraries/variables>`_

The variable data class.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/data/html/current/_modules/yombo/lib/variables.html>`_
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.sync_to_everywhere import SyncToEverywhere

logger = get_logger("library.variables.data")


class VariableData(Entity, SyncToEverywhere):
    """
    A class to manage a single variable data item.
    """
    @property
    def variable_field(self):
        try:
            return self._Parent.field_by_id(self.variable_field_id)
        except KeyError:
            pass
        return None

    @property
    def decrypted(self):
        return self._decrypted

    @decrypted.setter
    def decrypted(self, val):
        raise AttributeError("Unable to set 'decrypted' to a value. Set 'data' instead.")

    @property
    def display(self):
        return self._display

    @display.setter
    def display(self, val):
        raise AttributeError("Unable to set 'display' to a value. Set 'data' instead.")

    def __init__(self, parent, data, source=None):
        """
        Setup the variable data object using information passed in.

        :param data: A dict with all required items to create the class.
        :type data: dict

        """
        self._internal_label = "variable_data"  # Used by mixins
        self._can_have_fake_data = True
        super().__init__(parent)

        self.variable_data_id = data["id"]

        # database columns
        self.user_id = None
        self.gateway_id = None
        self.variable_field_id = None
        self.variable_relation_id = None
        self.variable_relation_type = None
        self.data = None
        self.data_weight = None
        self.updated_at = None
        self.created_at = None

        # computed values
        self._decrypted = self.data
        self._display = self.data

        self.update_attributes(data, source=source)
        self.start_data_sync()

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

    def __str__(self):
        """
        Print a string when printing the class.  This will return the data id so that
        the data can be identified and referenced easily.
        """
        return self.variable_data_id

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

    def __repl__(self):
        """
        Export data variables as a dictionary.
        """
        return self.asdict()
