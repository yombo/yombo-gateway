# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

A library to get variables in various formats. Also used to send updates to Yombo API.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from __future__ import print_function
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue

# Import Yombo libraries

from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
logger = get_logger('library.devices')


class Variables(YomboLibrary):
    """
    Various variable tools.
    """
    def _init_(self):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.

        self.gwid = self._Configs.get("core", "gwid")

    @inlineCallbacks
    def get_variable_data(self, relation_type=None, relation_id=None, **kwargs):
        """
        Gets available variable data for a given device_id or module_id. Any additional named arguments
        will be used as key/value pairs in the where statement.

        :param relation_type: Either 'module' or 'device'.
        :type relation_type: str
        :param relation_id: The id of the module or device to find.
        :type relation_id: str
        :return: Available variable data.
        :rtype: list
        """
        if relation_type is not None:
            kwargs['relation_type'] = relation_type
        if relation_id is not None:
            kwargs['relation_id'] = relation_id

        print("variables.get_variable_data.kwargs = %s" % kwargs)
        results = yield self._LocalDB.get_variable_data(**kwargs)
        print("variables.get_variable_data.results = %s" % results)
        returnValue(results)

    @inlineCallbacks
    def get_variable_fields(self, group_id=None, **kwargs):
        """
        Gets available variable fields for a given group_id. Any additional named arguments
        will be used as key/value pairs in the where statement.

        :param group_id: Field group_id to search for.
        :type group_id: str
        :return: Available variable fields.
        :rtype: list
        """
        if group_id is not None:
            kwargs['group_id'] = group_id
        results = yield self._LocalDB.get_variable_fields(**kwargs)
        returnValue(results)

    @inlineCallbacks
    def get_variable_groups(self, relation_type=None, relation_id=None, **kwargs):
        """
        Gets available variable groups for a given module_id or device_type_id. Any additional named arguments
        will be used as key/value pairs in the where statement.

        :param relation_type: Either 'module' or 'device'.
        :type relation_type: str
        :param relation_id: The id of the module or device to find.
        :type relation_id: str
        :return: Available variable groups.
        :rtype: list
        """
        if relation_type is not None:
            kwargs['relation_type'] = relation_type
        if relation_id is not None:
            kwargs['relation_id'] = relation_id

        results = yield self._LocalDB.get_variable_groups(**kwargs)
        returnValue(results)

    @inlineCallbacks
    def get_variable_fields_data(self, **kwargs):
        groups = yield self._LocalDB.get_variable_fields_data(**kwargs)
        # print("variables library: get_groups_fields: groups: %s" % groups)
        returnValue(groups)

    @inlineCallbacks
    def get_groups_fields(self, relation_type=None, relation_id=None, variable_data=None):

        groups = yield self._LocalDB.get_variable_groups_fields(group_relation_type=relation_type, group_relation_id=relation_id)
        if variable_data is not None:
            for group in groups:
                fields = group['fields']
                for field in fields:
                    if group['id'] in variable_data:
                        if field['id'] in variable_data[group['id']]:
                            groups[group['id']][field['id']] = variable_data[group['id']][field['id']]
        # print("variables library: get_groups_fields: groups: %s" % groups)
        returnValue(groups)

    @inlineCallbacks
    def get_variable_groups_fields_data(self, **kwargs):
        # print("variables library: get_variable_groups_fields_data: kwargs: %s" % kwargs)
        groups = yield self._LocalDB.get_variable_groups_fields_data(**kwargs)
        # print("variables library: get_variable_groups_fields_data: groups: %s" % groups)
        returnValue(groups)

    @inlineCallbacks
    def dev_group_add(self, data, **kwargs):
        """
        Add a new variable group.

        :param data:
        :param kwargs:
        :return:
        """

        var_results = yield self._YomboAPI.request('POST', '/v1/variable/group', data)
        # print("group edit results: %s" % group_results)
        # print("var_results: %s" % var_results)
        if var_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't add variable group",
                'apimsg': var_results['content']['message'],
                'apimsghtml': var_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable group added.",
            'group_id': var_results['data']['id'],
        }
        returnValue(results)

    @inlineCallbacks
    def dev_group_edit(self, group_id, data, **kwargs):
        """
        Edit a group at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        group_results = yield self._YomboAPI.request('PATCH', '/v1/variable/group/%s' % (group_id), data)
        # print("group edit results: %s" % group_results)

        if group_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit variable group",
                'apimsg': group_results['content']['message'],
                'apimsghtml': group_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable group edited.",
            'group_id': group_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_group_delete(self, group_id, **kwargs):
        """
        Delete a variable group at the Yombo server level, not at the local gateway level.

        :param group_id:
        :param kwargs:
        :return:
        """
        group_results = yield self._YomboAPI.request('DELETE', '/v1/variable/group/%s' % group_id)

        if group_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete variable group",
                'apimsg': group_results['content']['message'],
                'apimsghtml': group_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable group deleted.",
            'group_id': group_id,
        }
        returnValue(results)


    @inlineCallbacks
    def dev_group_enable(self, group_id, **kwargs):
        """
        Enable a group at the Yombo server level, not at the local gateway level.

        :param group_id: The group ID to enable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 1,
        }

        group_results = yield self._YomboAPI.request('PATCH', '/v1/variable/group/%s' % group_id, api_data)

        if group_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't enable variable group",
                'apimsg': group_results['content']['message'],
                'apimsghtml': group_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable group enabled.",
            'group_id': group_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_group_disable(self, group_id, **kwargs):
        """
        Enable a group at the Yombo server level, not at the local gateway level.

        :param group_id: The group ID to disable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 0,
        }

        group_results = yield self._YomboAPI.request('PATCH', '/v1/variable/group/%s' % group_id, api_data)

        if group_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable variable group",
                'apimsg': group_results['content']['message'],
                'apimsghtml': group_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable group disabled.",
            'group_id': group_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_field_add(self, data, **kwargs):
        """
        Add a new variable field.

        :param data:
        :param kwargs:
        :return:
        """

        var_results = yield self._YomboAPI.request('POST', '/v1/variable/field', data)
        # print("field edit results: %s" % field_results)
        # print("var_results: %s" % var_results)
        if var_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't add variable field",
                'apimsg': var_results['content']['message'],
                'apimsghtml': var_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable field added.",
            'field_id': var_results['data']['id'],
        }
        returnValue(results)

    @inlineCallbacks
    def dev_field_edit(self, field_id, data, **kwargs):
        """
        Edit a field at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        field_results = yield self._YomboAPI.request('PATCH', '/v1/variable/field/%s' % (field_id), data)
        # print("field edit results: %s" % field_results)

        if field_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit variable field",
                'apimsg': field_results['content']['message'],
                'apimsghtml': field_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable field edited.",
            'field_id': field_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_field_delete(self, field_id, **kwargs):
        """
        Delete a variable field at the Yombo server level, not at the local gateway level.

        :param field_id:
        :param kwargs:
        :return:
        """
        field_results = yield self._YomboAPI.request('DELETE', '/v1/variable/field/%s' % field_id)

        if field_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete variable field",
                'apimsg': field_results['content']['message'],
                'apimsghtml': field_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable field deleted.",
            'field_id': field_id,
        }
        returnValue(results)


    @inlineCallbacks
    def dev_field_enable(self, field_id, **kwargs):
        """
        Enable a field at the Yombo server level, not at the local gateway level.

        :param field_id: The field ID to enable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 1,
        }

        field_results = yield self._YomboAPI.request('PATCH', '/v1/variable/field/%s' % field_id, api_data)

        if field_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't enable variable field",
                'apimsg': field_results['content']['message'],
                'apimsghtml': field_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable field enabled.",
            'field_id': field_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_field_disable(self, field_id, **kwargs):
        """
        Enable a field at the Yombo server level, not at the local gateway level.

        :param field_id: The field ID to disable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 0,
        }

        field_results = yield self._YomboAPI.request('PATCH', '/v1/variable/field/%s' % field_id, api_data)

        if field_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable variable field",
                'apimsg': field_results['content']['message'],
                'apimsghtml': field_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Variable field disabled.",
            'field_id': field_id,
        }
        returnValue(results)