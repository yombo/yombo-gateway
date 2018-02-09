# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Variables @ Module Development <https://yombo.net/docs/libraries/variables>`_


A library to get variables in various formats. Also used to send updates to Yombo API.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/variables.html>`_
"""
# Import python libraries

try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from functools import partial
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('library.devices')


class Variables(YomboLibrary):
    """
    Various variable tools.
    """

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo variables library"

    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.

        self.gateway_id = self._Configs.get('core', 'gwid', 'local', False)

    # @memoize_ttl(15)
    @inlineCallbacks
    def get_variable_data(self, data_relation_type=None, data_relation_id=None, **kwargs):
        """
        Gets available variable data for a given device_id or module_id. Any additional named arguments
        will be used as key/value pairs in the where statement.

        :param data_relation_type: Either 'module' or 'device'.
        :type data_relation_type: str
        :param data_relation_id: The id of the module or device to find.
        :type data_relation_id: str
        :return: Available variable data.
        :rtype: list
        """
        if data_relation_type is not None:
            kwargs['data_relation_type'] = data_relation_type
        if data_relation_id is not None:
            kwargs['data_relation_id'] = data_relation_id

        results = yield self._LocalDB.get_variable_data(**kwargs)
        return results

    # @memoize_ttl(60)
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
        return results

    # @memoize_ttl(60)
    @inlineCallbacks
    def get_variable_fields_encrypted(self):
        """
        Get all field id's that should be encrypted.

        :return: Field id's that have encryption set to suggested or always.
        :rtype: list
        """
        results = yield self._LocalDB.get_variable_fields_encrypted()
        return results

    # @memoize_ttl(60)
    @inlineCallbacks
    def get_variable_groups(self, group_relation_type=None, group_relation_id=None, **kwargs):
        """
        Gets available variable groups for a given module_id or device_type_id. Any additional named arguments
        will be used as key/value pairs in the where statement.

        :param group_relation_type: Either 'module' or 'device'.
        :type group_relation_type: str
        :param relation_id: The id of the module or device to find.
        :type relation_id: str
        :return: Available variable groups.
        :rtype: list
        """
        if group_relation_type is not None:
            kwargs['group_relation_type'] = group_relation_type
        if group_relation_id is not None:
            kwargs['group_relation_id'] = group_relation_id

        results = yield self._LocalDB.get_variable_groups(**kwargs)
        return results

    # @memoize_ttl(30)
    @inlineCallbacks
    def get_variable_fields_data(self, **kwargs):
        """
        Used to get the fields and data. Named arguments needs to be data_relation_id and data_relation_type.
        
        This method returns a deferred.
        
        :param kwargs: 
        :return: 
        """
        groups = yield self._LocalDB.get_variable_fields_data(**kwargs)
        # print("variables library: get_groups_fields: groups: %s" % groups)
        return groups

    def get_variable_fields_data_callable(self, **kwargs):
        """
        Like get_variable_fields_data, but returns a callable. This callable can be used to get the latest
        information. The callable is called, it will return a deferred.
        
        :param kwargs: 
        :return: 
        """
        return partial(self.get_variable_fields_data, **kwargs)

    # @memoize_ttl(10)
    @inlineCallbacks
    def get_variable_groups_fields(self, group_relation_type=None, group_relation_id=None, variable_data=None):
        """
        Returns groups and fields for a given group_relation_id and group_relation_type.
        
        This method returns a deferred.
        
        :param group_relation_type: 
        :param group_relation_id: 
        :param variable_data: 
        :return: 
        """

        # print("get group fields: %s %s" % (group_relation_type, group_relation_id))
        groups = yield self._LocalDB.get_variable_groups_fields(group_relation_type=group_relation_type,
                                                                group_relation_id=group_relation_id)
        if variable_data is not None:
            for group in groups:
                fields = group['fields']
                for field in fields:
                    if group['id'] in variable_data:
                        if field['id'] in variable_data[group['id']]:
                            groups[group['id']][field['id']] = variable_data[group['id']][field['id']]
        return groups

    # @memoize_ttl(10)
    @inlineCallbacks
    def get_variable_groups_fields_data(self, **kwargs):
        """
        Returns groups, fields, and data. Usually data_relation_id and data_relation_type is submitted.
        
        This returns a deferred.

        :param kwargs: 
        :return: 
        """
        # print("variables library: get_variable_groups_fields_data: kwargs: %s" % kwargs)
        groups = yield self._LocalDB.get_variable_groups_fields_data(**kwargs)
        # print("variables library: get_variable_groups_fields_data: groups: %s" % groups)
        return groups

    # @memoize_ttl(10)
    def merge_variable_fields_data_data(self, fields, new_data_items):
        """
        Merge the results from get_variable_fields_data and a dictiionary of data times, usually
        the response from a web post.
        :param groups: 
        :param data: 
        :return: 
        """
        for field_name, field in fields:
            if field_name in new_data_items:
                new_data = new_data_items['field_name']
                # print("new_data: %s" % new_data)
                if field['id'] in new_data:
                    field['id']['value'] = new_data[field['id']]
                else:
                    field[field['id']] = {
                        'id': field['id'],
                        'value': new_data[field['id']],
                    }

                # for data in field['data']:
                #     if data['name']

            field['values'] = []
            for data_id, data in field['data'].items():
                field['values'].append(data['value'])

    # @memoize_ttl(10)
    @inlineCallbacks
    def merge_variable_groups_fields_data_data(self, groups, new_data_items, relation_type = None):
        """
        Merge the results from get_variable_groups_fields_data and a dictiionary of data times, usually
        the response from a web post or get_variable_data.
        :param groups: 
        :param data: 
        :return: 
        """
        # print("merge_variable_data. Groups: %s" % groups)
        # print("merge_variable_data. new_data_items: %s" % new_data_items)
        for group_name, group in groups.items():
            for field_name, field in group['fields'].items():
                # print("111 field %s" % field )
                # print("111 field_name %s" % field )
                found_field_id = None
                found_field_key = None
                if field_name in new_data_items:
                    found_field_id = field['id']
                    found_field_key = field_name
                elif field['id'] in new_data_items:
                    found_field_id = field['id']
                    found_field_key = field['id']
                if found_field_id is not None:
                    new_data_item = new_data_items[found_field_key]
                    # print("222 new_data: %s" % new_data_item)
                    # print("222 field['id']: %s" % field['id'])
                    for data_id, data in new_data_item.items():
                        data_items = {
                            'id': data_id,
                            'relation_id': None,
                            'relation_type': relation_type,
                            'weight': 0,
                            'created_at': time(),
                            'updated_at': time(),
                        }
                        # print("zzzzz")
                        if data is not None:
                            data_items['value'] = yield self._GPG.decrypt(data)
                            data_items['value_display'] = yield self._GPG.display_encrypted(data)
                        else:
                            data_items['value'] = None
                            data_items['value_display'] = ""

                        data_items['value_orig'] = data
                        # print("zzzzz 10")
                        groups[group_name]['fields'][field_name]['data'][data_id] = data_items
                        # print("zzzzz 11")
                        groups[group_name]['fields'][field_name]['values'].append(data_items['value'])
                        # print("zzzzz 12")
                        groups[group_name]['fields'][field_name]['values_display'].append(data_items['value_display'])
                        # print("zzzzz 13")
                        groups[group_name]['fields'][field_name]['values_orig'].append(data_items['value_orig'])

                        # print("newdata: %s" % data_items)

        # print("merge_variable_data. groups_done: %s" % groups)
        return groups

    @inlineCallbacks
    def extract_variables_from_web_data(self, new_data_items, encrypt=None):
        """
        Extract values posted from webinterface pages into something that can be submitted to either
        modules or devices to the Yombo API.
        :param new_data_items: 
        :return: 
        """
        if encrypt is None:
            encrypt = True

        if encrypt is True:
            encrypt_fields = yield self.get_variable_fields_encrypted()
        else:
            encrypt_fields = []

        # print("extract_variables_from_web_data: %s" % encrypt_fields)
        results = new_data_items.copy()
        # print("extract_variables_from_web_data1: %s" % new_data_items)

        for field_id, data in results.items():
            for data_id, value in data.items():
                final_value = ""
                if isinstance(value, dict):
                    # print("processing from dict..")
                    if value['input'] == '-----ENCRYPTED DATA-----':
                        # print("encry: %s" % value['orig'].startswith('-----BEGIN PGP MESSAGE-----'))
                        # print("encry: %s" % value['orig'])
                        if value['orig'].startswith('-----BEGIN PGP MESSAGE-----') is False:
                            raise YomboWarning("Invalid variable data.")
                        else:
                            # print("final_value: value['orig']")
                            final_value = value['orig']
                    else:
                        # print("final_value: value['input']")
                        final_value = value['input']
                else:
                    # print("processing else")
                    final_value = value
                # print("final_value: %s" % final_value)
                if field_id in encrypt_fields:
                    final_value = yield self._GPG.encrypt(final_value)
                results[field_id][data_id] = final_value
        # print("extract_variables_from_web_data: %s" % results)
        return results

    @inlineCallbacks
    def dev_group_add(self, data, **kwargs):
        """
        Add a new variable group.

        :param data:
        :param kwargs:
        :return:
        """
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't add variable group: User session missing.",
                    'apimsg': "Couldn't add variable group: User session missing.",
                    'apimsghtml': "Couldn't add variable group: User session missing.",
                }

            var_results = yield self._YomboAPI.request('POST', '/v1/variable/group',
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't add variable group: %s" % e.message,
                'apimsg': "Couldn't add variable group: %s" % e.message,
                'apimsghtml': "Couldn't add variable group: %s" % e.html_message,
            }
        # print("group edit results: %s" % group_results)
        # print("var_results: %s" % var_results)

        return {
            'status': 'success',
            'msg': "Variable group added.",
            'group_id': var_results['data']['id'],
        }

    @inlineCallbacks
    def dev_group_edit(self, group_id, data, **kwargs):
        """
        Edit a group at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't edit variable group: User session missing.",
                    'apimsg': "Couldn't edit variable group: User session missing.",
                    'apimsghtml': "Couldn't edit variable group: User session missing.",
                }
            yield self._YomboAPI.request('PATCH', '/v1/variable/group/%s' % (group_id),
                                         data,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't edit variable group: %s" % e.message,
                'apimsg': "Couldn't edit variable group: %s" % e.message,
                'apimsghtml': "Couldn't edit variable group: %s" % e.html_message,
            }

        # print("group edit results: %s" % group_results)

        return {
            'status': 'success',
            'msg': "Variable group edited.",
            'group_id': group_id,
        }

    @inlineCallbacks
    def dev_group_delete(self, group_id, **kwargs):
        """
        Delete a variable group at the Yombo server level, not at the local gateway level.

        :param group_id:
        :param kwargs:
        :return:
        """
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't delete variable group: User session missing.",
                    'apimsg': "Couldn't delete variable group: User session missing.",
                    'apimsghtml': "Couldn't delete variable group: User session missing.",
                }

            yield self._YomboAPI.request('DELETE', '/v1/variable/group/%s' % group_id,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't delete variable group: %s" % e.message,
                'apimsg': "Couldn't delete variable group: %s" % e.message,
                'apimsghtml': "Couldn't delete variable group: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Variable group deleted.",
            'group_id': group_id,
        }


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

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't enable variable group: User session missing.",
                    'apimsg': "Couldn't enable variable group: User session missing.",
                    'apimsghtml': "Couldn't enable variable group: User session missing.",
                }

            yield self._YomboAPI.request('PATCH', '/v1/variable/group/%s' % group_id,
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't enable variable group: %s" % e.message,
                'apimsg': "Couldn't enable variable group: %s" % e.message,
                'apimsghtml': "Couldn't enable variable group: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Variable group enabled.",
            'group_id': group_id,
        }

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

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't disable variable group: User session missing.",
                    'apimsg': "Couldn't disable variable group: User session missing.",
                    'apimsghtml': "Couldn't disable variable group: User session missing.",
                }

            yield self._YomboAPI.request('PATCH', '/v1/variable/group/%s' % group_id,
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't disable variable group: %s" % e.message,
                'apimsg': "Couldn't disable variable group: %s" % e.message,
                'apimsghtml': "Couldn't disable variable group: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Variable group disabled.",
            'group_id': group_id,
        }

    @inlineCallbacks
    def dev_field_add(self, data, **kwargs):
        """
        Add a new variable field.

        :param data:
        :param kwargs:
        :return:
        """
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't add variable field: User session missing.",
                    'apimsg': "Couldn't add variable field: User session missing.",
                    'apimsghtml': "Couldn't add variable field: User session missing.",
                }

            var_results = yield self._YomboAPI.request('POST', '/v1/variable/field',
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't add variable field: %s" % e.message,
                'apimsg': "Couldn't add variable field: %s" % e.message,
                'apimsghtml': "Couldn't add variable field: %s" % e.html_message,
            }
        # print("field edit results: %s" % field_results)
        # print("var_results: %s" % var_results)

        return {
            'status': 'success',
            'msg': "Variable field added.",
            'field_id': var_results['data']['id'],
        }

    @inlineCallbacks
    def dev_field_edit(self, field_id, data, **kwargs):
        """
        Edit a field at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't edit variable field: User session missing.",
                    'apimsg': "Couldn't edit variable field: User session missing.",
                    'apimsghtml': "Couldn't edit variable field: User session missing.",
                }

            yield self._YomboAPI.request('PATCH', '/v1/variable/field/%s' % (field_id),
                                         data,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't edit variable field: %s" % e.message,
                'apimsg': "Couldn't edit variable field: %s" % e.message,
                'apimsghtml': "Couldn't edit variable field: %s" % e.html_message,
            }

        # print("field edit results: %s" % field_results)

        return {
            'status': 'success',
            'msg': "Variable field edited.",
            'field_id': field_id,
        }

    @inlineCallbacks
    def dev_field_delete(self, field_id, **kwargs):
        """
        Delete a variable field at the Yombo server level, not at the local gateway level.

        :param field_id:
        :param kwargs:
        :return:
        """
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't delete variable field: User session missing.",
                    'apimsg': "Couldn't delete variable field: User session missing.",
                    'apimsghtml': "Couldn't delete variable field: User session missing.",
                }

            yield self._YomboAPI.request('DELETE', '/v1/variable/field/%s' % field_id,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't delete variable field: %s" % e.message,
                'apimsg': "Couldn't delete variable field: %s" % e.message,
                'apimsghtml': "Couldn't delete variable field: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Variable field deleted.",
            'field_id': field_id,
        }


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

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't enable variable field: User session missing.",
                    'apimsg': "Couldn't enable variable field: User session missing.",
                    'apimsghtml': "Couldn't enable variable field: User session missing.",
                }

            yield self._YomboAPI.request('PATCH', '/v1/variable/field/%s' % field_id,
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't enable variable field: %s" % e.message,
                'apimsg': "Couldn't enable variable field: %s" % e.message,
                'apimsghtml': "Couldn't enable variable field: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Variable field enabled.",
            'field_id': field_id,
        }

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

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't disable variable field: User session missing.",
                    'apimsg': "Couldn't disable variable field: User session missing.",
                    'apimsghtml': "Couldn't disable variable field: User session missing.",
                }

            yield self._YomboAPI.request('PATCH', '/v1/variable/field/%s' % field_id,
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't disable variable field: %s" % e.message,
                'apimsg': "Couldn't disable variable field: %s" % e.message,
                'apimsghtml': "Couldn't disable variable field: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Variable field disabled.",
            'field_id': field_id,
        }
