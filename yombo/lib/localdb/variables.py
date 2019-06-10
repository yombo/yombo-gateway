# Import python libraries
from collections import OrderedDict
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.log import get_logger
# Import 3rd-party libs
from yombo.ext.twistar.utils import dictToWhere
from yombo.lib.localdb import (VariableData, VariableFields, VariableGroups, VariableFieldDataView, VariableGroupFieldView,
                               VariableGroupFieldDataView, )

logger = get_logger("library.localdb.variables")


class DB_Variables(object):

    @inlineCallbacks
    def get_variable_data(self):
        """
        Gets all variable data, but ordered in data weight.
        """
        records = yield VariableData.find(orderby="data_weight ASC")
        return self.process_get_results(records)

    @inlineCallbacks
    def get_variable_fields(self):
        """
        Gets all variable data, but ordered in data weight.
        """
        records = yield VariableFields.find(orderby="field_weight ASC")
        return self.process_get_results(records)

    @inlineCallbacks
    def get_variable_groups(self):
        """
        Gets all variable data, but ordered in data weight.
        """
        records = yield VariableGroups.find(orderby="group_weight ASC")
        return self.process_get_results(records)

    @inlineCallbacks
    def save_variable_data(self, data):
        """
        Attempts to find the provided variable data in the database. If it's found, it's updated. Otherwise, a new
        one is created.

        :param data: A variable data instance.
        :return:
        """
        variable = yield VariableData.find(data.variable_data_id)
        if variable is None:  # If none is found, create a new one.
            variable = VariableData()
            variable.id = data.variable_data_id

        for field in self.db_fields("variable_data"):
            setattr(variable, field, getattr(data, field))

        yield variable.save()

    @inlineCallbacks
    def save_variable_fields(self, data):
        """
        Attempts to find the provided variable field in the database. If it's found, it's updated. Otherwise, a new
        one is created.

        :param data: A variable field instance.
        :return:
        """
        variable = yield VariableFields.find(data.variable_field_id)
        if variable is None:  # If none is found, create a new one.
            variable = VariableFields()
            variable.id = data.variable_field_id

        for field in self.db_fields("variable_data"):
            setattr(variable, field, getattr(data, field))

        yield variable.save()

    @inlineCallbacks
    def save_variable_groups(self, data):
        """
        Attempts to find the provided variable groups in the database. If it's found, it's updated. Otherwise, a new
        one is created.

        :param data: A variable groups instance.
        :return:
        """
        variable = yield VariableGroups.find(data.variable_group_id)
        if variable is None:  # If none is found, create a new one.
            variable = VariableGroups()
            variable.id = data.variable_group_id

        for field in self.db_fields("variable_data"):
            setattr(variable, field, getattr(data, field))

        yield variable.save()
