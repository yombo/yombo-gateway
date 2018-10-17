# Import python libraries
from collections import OrderedDict
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.log import get_logger
# Import 3rd-party libs
from yombo.ext.twistar.utils import dictToWhere
from yombo.lib.localdb import (VariableFields, VariableGroups, VariableFieldDataView, VariableGroupFieldView,
                               VariableGroupFieldDataView, )

logger = get_logger('library.localdb.variables')


class DB_Variables(object):

    @inlineCallbacks
    def get_variable_data(self, **kwargs):
        """
        Searches for variable data, using named agurments as where search fields, and'd together.

        :param group_id: Field group_id to search for.
        :type group_id: str
        :return: Available variable fields.
        :rtype: list
        """
        records = yield VariableFieldDataView.find(
            where=dictToWhere(kwargs),
            orderby='data_weight ASC')

        variables = OrderedDict()
        for record in records:
            # print("record: %s" % record)
            if record.field_machine_label not in variables:
                variables[record.field_machine_label] = {}
                variables[record.field_machine_label][record.data_id] = record.data
        return variables

    @inlineCallbacks
    def get_variable_fields(self, **kwargs):
        """
        Searches for variable fields, using named agurments as where search fields, and'd together.

        :param group_id: Field group_id to search for.
        :type group_id: str
        :return: Available variable fields.
        :rtype: list
        """
        records = yield VariableFields.find(
            where=dictToWhere(kwargs),
            orderby='field_weight ASC')

        return records

    @inlineCallbacks
    def get_variable_fields_encrypted(self):
        """
        Get all field id's that should be encrypted.

        :return: Field id's that have encryption set to suggested or always.
        :rtype: list
        """
        records = yield VariableFields.find(
            where=["encryption = 'always' or encryption = 'suggested'"]
        )
        items = []
        for record in records:
            items.append(record.id)
        return items

    @inlineCallbacks
    def get_variable_groups(self, **kwargs):
        """
        Searches for variable groups, using named agurments as where search fields, and'd together.

        :return: Available variable groups.
        :rtype: list
        """
        records = yield VariableGroups.find(
            where=dictToWhere(kwargs),
            orderby='group_weight ASC')

        return records

    @inlineCallbacks
    def get_variable_fields_data(self, data_relation_id=None, **kwargs):
        """
        Gets fields an associated data. Named arguments are used to crate the WHERE statement.

        :return: Available variable data nested inside the fields as 'data'.
        :rtype: list
        """
        records = yield VariableFieldDataView.find(
            where=dictToWhere(kwargs),
            orderby='field_weight ASC, data_weight ASC')
        variables = OrderedDict()
        for record in records:
            if data_relation_id is not None:
                if record.data_relation_id not in (None, data_relation_id):
                    continue

            if record.field_machine_label not in variables:
                variables[record.field_machine_label] = {
                    'id': record.field_id,
                    'field_machine_label': record.field_machine_label,
                    'field_label': record.field_label,
                    'field_description': record.field_description,
                    'field_help_text': record.field_help_text,
                    'field_weight': record.field_weight,
                    'value_min': record.value_min,
                    'value_max': record.value_max,
                    'value_casing': record.encryption,
                    'value_required': record.value_required,
                    'encryption': record.encryption,
                    'input_type_id': record.input_type_id,
                    'default_value': record.default_value,
                    'multiple': record.multiple,
                    'data_weight': record.data_weight,
                    'created_at': record.field_created_at,
                    'updated_at': record.field_updated_at,
                    'data': OrderedDict(),
                    'values': [],
                    'values_display': [],
                    'values_orig': [],
                }

            data = {
                'id': record.data_id,
                'weight': record.data_weight,
                'created_at': record.data_created_at,
                'updated_at': record.data_updated_at,
                'relation_id': record.data_relation_id,
                'relation_type': record.data_relation_type,
            }
            if record.data is not None:
                value = yield self._GPG.decrypt(record.data)
                try:  # lets be gentle for now.  Try to validate and corerce.
                    # validate the value is valid input
                    data['value'] = self._InputTypes.check(
                        variables[record.field_machine_label]['input_type_id'],
                        value,
                        casing=variables[record.field_machine_label]['value_casing'],
                        required=variables[record.field_machine_label]['value_required'],
                        min=variables[record.field_machine_label]['value_min'],
                        max=variables[record.field_machine_label]['value_max'],
                        default=variables[record.field_machine_label]['default_value'],
                    )
                except Exception as e:
                    logger.debug("Variable doesn't validate ({input_type_id}): {label}   Value:{value}    Reason: {e}",
                                label=variables[record.field_machine_label]['field_label'],
                                value=value,
                                input_type_id=variables[record.field_machine_label]['input_type_id'],
                                e=e)
                    data['value'] = value

                data['value_display'] = yield self._GPG.display_encrypted(record.data)
            else:
                data['value'] = None
                data['value_display'] = ""

            data['value_orig'] = record.data
            variables[record.field_machine_label]['data'][record.data_id] = data
            variables[record.field_machine_label]['values'].append(data['value'])
            variables[record.field_machine_label]['values_display'].append(data['value_display'])
            variables[record.field_machine_label]['values_orig'].append(data['value_orig'])
        return variables

    @inlineCallbacks
    def get_variable_groups_fields(self,  **kwargs):
        """
        Gets groups with nested fields, with nested data. Named arguments are used to crate the WHERE statement.

        :return: Available variable data nested inside the fields as 'data'.
        :rtype: list
        """
        # print("lbdb: %s" % dictToWhere(kwargs))
        records = yield VariableGroupFieldView.find(
            where=dictToWhere(kwargs),
            orderby='group_weight ASC, field_weight ASC')
        variables = OrderedDict()
        for record in records:
            if record.group_machine_label not in variables:
                variables[record.group_machine_label] = {
                    'id': record.group_id,
                    'group_relation_type': record.group_relation_type,
                    'group_id': record.group_id,
                    'group_machine_label': record.group_machine_label,
                    'group_label': record.group_label,
                    'group_description': record.group_description,
                    'group_weight': record.group_weight,
                    'group_status': record.group_status,
                    'fields': OrderedDict(),
                }
            if record.field_machine_label not in variables[record.group_machine_label]['fields']:
                variables[record.group_machine_label]['fields'][record.field_machine_label] = {
                    'id': record.field_id,
                    'field_machine_label': record.field_machine_label,
                    'field_label': record.field_label,
                    'field_description': record.field_description,
                    'field_help_text': record.field_help_text,
                    'field_weight': record.field_weight,
                    'value_min': record.value_min,
                    'value_max': record.value_max,
                    'value_casing': record.encryption,
                    'value_required': record.value_required,
                    'encryption': record.encryption,
                    'input_type_id': record.input_type_id,
                    'default_value': record.default_value,
                    'multiple': record.multiple,
                    'created_at': record.field_created_at,
                    'updated_at': record.field_updated_at,
                    'data': OrderedDict(),
                    'values': [],
                    'values_display': [],
                    'values_orig': [],
                }
        return variables

    @inlineCallbacks
    def get_variable_groups_fields_data(self, data_relation_id=None, **kwargs):
        """
        Gets groups with nested fields, with nested data. Named arguments are used to crate the WHERE statement.

        :return: Available variable data nested inside the fields as 'data'.
        :rtype: list
        """
        records = yield VariableGroupFieldDataView.find(
            where=dictToWhere(kwargs),
            orderby='group_weight ASC, field_weight ASC, data_weight ASC')
        variables = OrderedDict()
        for record in records:
            if data_relation_id is not None:
                if record.data_relation_id not in (None, data_relation_id):
                    continue

            if record.group_machine_label not in variables:
                variables[record.group_machine_label] = {
                    'id': record.group_id,
                    'group_relation_type': record.group_relation_type,
                    'group_id': record.group_id,
                    'group_machine_label': record.group_machine_label,
                    'group_label': record.group_label,
                    'group_description': record.group_description,
                    'group_weight': record.group_weight,
                    'group_status': record.group_status,
                    'fields': OrderedDict(),
                }
            if record.field_machine_label not in variables[record.group_machine_label]['fields']:
                variables[record.group_machine_label]['fields'][record.field_machine_label] = {
                    'id': record.field_id,
                    'field_machine_label': record.field_machine_label,
                    'field_label': record.field_label,
                    'field_description': record.field_description,
                    'field_help_text': record.field_help_text,
                    'field_weight': record.field_weight,
                    'value_min': record.value_min,
                    'value_max': record.value_max,
                    'value_casing': record.encryption,
                    'value_required': record.value_required,
                    'encryption': record.encryption,
                    'input_type_id': record.input_type_id,
                    'default_value': record.default_value,
                    'multiple': record.multiple,
                    'data_weight': record.data_weight,
                    'created_at': record.field_created_at,
                    'updated_at': record.field_updated_at,
                    'data': OrderedDict(),
                    'values': [],
                    'values_display': [],
                    'values_orig': [],
                }
            data = {
                'id': record.data_id,
                'weight': record.data_weight,
                'created_at': record.data_created_at,
                'updated_at': record.data_updated_at,
                'relation_id': record.data_relation_id,
                'relation_type': record.data_relation_type,
            }
            if record.data is not None:
                value = yield self._GPG.decrypt(record.data)
                try:  # lets be gentle for now.  Try to validate and corerce.
                    # validate the value is valid input
                    data['value'] = self._InputTypes.check(
                        variables[record.field_machine_label]['input_type_id'],
                        value,
                        casing=variables[record.field_machine_label]['value_casing'],
                        required=variables[record.field_machine_label]['value_required'],
                        min=variables[record.field_machine_label]['value_min'],
                        max=variables[record.field_machine_label]['value_max'],
                        default=variables[record.field_machine_label]['default_value'],
                    )
                except Exception as e:  # for now, just pass
                    logger.debug("Variable doesn't validate: {label}   Value:{value}.  Reason: {e}",
                                label=variables[record.field_machine_label]['field_label'],
                                value=value,
                                e=e)
                    data['value'] = value
                data['value_display'] = yield self._GPG.display_encrypted(record.data)
            else:
                data['value'] = None
                data['value_display'] = ""

            data['value_orig'] = record.data
            variables[record.group_machine_label]['fields'][record.field_machine_label]['data'][record.data_id] = data
            variables[record.group_machine_label]['fields'][record.field_machine_label]['values'].append(data['value'])
            variables[record.group_machine_label]['fields'][record.field_machine_label]['values_display'].append(data['value_display'])
            variables[record.group_machine_label]['fields'][record.field_machine_label]['values_orig'].append(data['value_orig'])
        return variables

    @inlineCallbacks
    def del_variables(self, data_relation_type, data_relation_id):
        """
        Deletes variables for a given relation type and relation id.

        :return:
        """
        results = yield self.dbconfig.delete('variable_data',
                                             where=['data_relation_type = ? and data_relation_id = ?',
                                                    data_relation_type,
                                                    data_relation_id]
                                             )
        return results

    @inlineCallbacks
    def add_variable_data(self, data, **kwargs):
        # print("add_variable_data: data: %s" % data)

        # add_variable_data: data: {'field_id': 'pVyrdoVdDglKbj', 'relation_id': 'j2z8gbJxkNl4qwM6',
        #                           'relation_type': 'device', 'data_weight': 0, 'data': '4075575332',
        #                           'updated_at': 1530552709, 'created_at': 1530552709, 'id': 'qZlMkAzWd8aW4pngyx'}

        args = {
            'id': data['id'],
            'field_id': data['field_id'],
            'data_relation_id': data['relation_id'],
            'data_relation_type': data['relation_type'],
            'data': data['data'],
            'data_weight': data['data_weight'],
            'updated_at': data['updated_at'],
            'created_at': data['created_at'],
        }
        results = yield self.dbconfig.insert('variable_data', args, None, 'OR IGNORE')
        return results

    @inlineCallbacks
    def edit_variable_data(self, data_id, value):
        yield self.dbconfig.update("variable_data",
                                   {'data': value, 'updated_at': time()},
                                   where=['id = ?', data_id])

    @inlineCallbacks
    def get_variable_groups(self, group_relation_type, group_relation_id):
        """
        Gets all variable groups for a given type and by id.

        :param group_relation_type:
        :param group_relation_id:
        :return:
        """
        records = yield VariableGroups.find(
            where=['group_relation_type = ? AND group_relation_id =?', group_relation_type, group_relation_id],
            orderby='group_weight ASC')
        return records

