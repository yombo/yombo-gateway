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
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

from .variable_data import  VariableData
from .variable_fields import VariableField
from .variable_groups import VariableGroup

logger = get_logger("library.devices")


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

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.variable_data = {}
        self.variable_fields = {}
        self.variable_groups = {}
        self._started = False

        yield self._load_variable_data_from_database()
        yield self._load_variable_fields_from_database()
        yield self._load_variable_groups_from_database()

        self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.

    def _start_(self, **kwargs):
        self._started = True

    @inlineCallbacks
    def _load_variable_data_from_database(self):
        """
        Loads variable data from database and sends them to
        :py:meth:`_load_variable_data_into_memory <Variables._load_variable_data_into_memory>`

        This can be triggered either on system startup or when new/updated variables have been saved to the
        database and we need to refresh existing variables.
        """
        data = yield self._LocalDB.get_variable_data()
        for item in data:
            yield self._load_variable_data_into_memory(item.__dict__, source="database")

    @inlineCallbacks
    def _load_variable_data_into_memory(self, data, source=None):
        """
        Add a new variable data to memory or update an existing variable data.

        :param data: A dictionary of items required to either setup a new variable data or update an existing one.
        :type data: dict
        :param source: Where the data is coming from.
        :type source: string
        :returns: Pointer to new / update variable data
        """
        var_data = self._generic_load_into_memory(self.variable_data, 'variable_data', VariableData, data, source)
        yield var_data._init_()
        return var_data

    @inlineCallbacks
    def _load_variable_fields_from_database(self):
        """
        Loads variable data from database and sends them to
        :py:meth:`_load_variable_fields_into_memory <Variables._load_variable_fields_into_memory>`

        This can be triggered either on system startup or when new/updated variables have been saved to the
        database and we need to refresh existing variables.
        """
        data = yield self._LocalDB.get_variable_fields()
        for item in data:
            self._load_variable_fields_into_memory(item.__dict__, source="database")

    def _load_variable_fields_into_memory(self, data, source=None):
        """
        Add a new variable field to memory or update an existing variable field.

        :param data: A dictionary of items required to either setup a new variable field or update an existing one.
        :type data: dict
        :param source: Where the field is coming from.
        :type source: string
        :returns: Pointer to new / update variable field
        """
        return self._generic_load_into_memory(self.variable_fields, 'variable_field', VariableField, data, source)

    @inlineCallbacks
    def _load_variable_groups_from_database(self):
        """
        Loads variable data from database and sends them to
        :py:meth:`_load_variable_groups_into_memory <Variables._load_variable_groups_into_memory>`

        This can be triggered either on system startup or when new/updated variables have been saved to the
        database and we need to refresh existing variables.
        """
        data = yield self._LocalDB.get_variable_groups()
        for item in data:
            # print(f"load var: group: {item.__dict__}")
            self._load_variable_groups_into_memory(item.__dict__, source="database")

    def _load_variable_groups_into_memory(self, data, source=None):
        """
        Add a new variable group to memory or update an existing variable group.

        :param data: A dictionary of items required to either setup a new variable group or update an existing one.
        :type data: dict
        :param source: Where the field is coming from.
        :type source: string
        :returns: Pointer to new / update variable group
        """
        return self._generic_load_into_memory(self.variable_groups, 'variable_group', VariableGroup, data, source)

    def data_by_id(self, variable_data_id):
        """
        Gets variable data by it's id.

        :param variable_data_id:
        :return:
        """
        if variable_data_id in self.variable_data:
            return self.variable_data[variable_data_id]
        raise KeyError(f"Variable data id not found: {variable_data_id}")

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

    def field_by_id(self, variable_field_id):
        """
        Gets variable field by it's id.

        :param variable_field_id:
        :return:
        """
        if variable_field_id in self.variable_fields:
            return self.variable_fields[variable_field_id]
        raise KeyError(f"Variable field id not found: {variable_field_id}")

    def field(self, group_id=None):
        """
        Gets available variable data for a given group_id.

        :param group_id: Field group_id to search for.
        :type group_id: str
        :return: Available variable fields.
        :rtype: dict
        """
        results = {}
        for item_id, item in self.variable_fields.items():
            if (group_id is None or item.group_id == group_id):
                results[item_id] = item
        return results

    def group_by_id(self, variable_group_id):
        """
        Gets variable group by it's id.

        :param variable_field_id:
        :return:
        """
        if variable_group_id in self.variable_groups:
            return self.variable_groups[variable_group_id]
        raise KeyError(f"Variable group id not found: {variable_group_id}")

    @inlineCallbacks
    def group(self, group_relation_type=None, group_relation_id=None):
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
        for item_id, item in self.variable_data.items():
            if (group_relation_type is None or item.group_relation_type == group_relation_type) and \
                    (group_relation_id is None or item.group_relation_id == group_relation_id):
                results[item_id] = item
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
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't add variable group: User session missing.",
                    "apimsg": "Couldn't add variable group: User session missing.",
                    "apimsghtml": "Couldn't add variable group: User session missing.",
                }

            var_results = yield self._YomboAPI.request("POST", "/v1/variable/group",
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't add variable group: {e.message}",
                "apimsg": f"Couldn't add variable group: {e.message}",
                "apimsghtml": f"Couldn't add variable group: {e.html_message}",
            }
        # print("group edit results: %s" % group_results)
        # print("var_results: %s" % var_results)

        return {
            "status": "success",
            "msg": "Variable group added.",
            "group_id": var_results["data"]["id"],
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
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't edit variable group: User session missing.",
                    "apimsg": "Couldn't edit variable group: User session missing.",
                    "apimsghtml": "Couldn't edit variable group: User session missing.",
                }
            yield self._YomboAPI.request("PATCH", f"/v1/variable/group/{group_id}",
                                         data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't edit variable group: {e.message}",
                "apimsg": f"Couldn't edit variable group: {e.message}",
                "apimsghtml": f"Couldn't edit variable group: {e.html_message}",
            }

        # print("group edit results: %s" % group_results)

        return {
            "status": "success",
            "msg": "Variable group edited.",
            "group_id": group_id,
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
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't delete variable group: User session missing.",
                    "apimsg": "Couldn't delete variable group: User session missing.",
                    "apimsghtml": "Couldn't delete variable group: User session missing.",
                }

            yield self._YomboAPI.request("DELETE", f"/v1/variable/group/{group_id}",
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't delete variable group: {e.message}",
                "apimsg": f"Couldn't delete variable group: {e.message}",
                "apimsghtml": f"Couldn't delete variable group: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Variable group deleted.",
            "group_id": group_id,
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
            "status": 1,
        }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't enable variable group: User session missing.",
                    "apimsg": "Couldn't enable variable group: User session missing.",
                    "apimsghtml": "Couldn't enable variable group: User session missing.",
                }

            yield self._YomboAPI.request("PATCH", f"/v1/variable/group/{group_id}",
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't enable variable group: {e.message}",
                "apimsg": f"Couldn't enable variable group: {e.message}",
                "apimsghtml": f"Couldn't enable variable group: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Variable group enabled.",
            "group_id": group_id,
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
            "status": 0,
        }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't disable variable group: User session missing.",
                    "apimsg": "Couldn't disable variable group: User session missing.",
                    "apimsghtml": "Couldn't disable variable group: User session missing.",
                }

            yield self._YomboAPI.request("PATCH", f'/v1/variable/group/{group_id}',
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't disable variable group: {e.message}",
                "apimsg": f"Couldn't disable variable group: {e.message}",
                "apimsghtml": f"Couldn't disable variable group: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Variable group disabled.",
            "group_id": group_id,
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
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't add variable field: User session missing.",
                    "apimsg": "Couldn't add variable field: User session missing.",
                    "apimsghtml": "Couldn't add variable field: User session missing.",
                }

            var_results = yield self._YomboAPI.request("POST", "/v1/variable/field",
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't add variable field: {e.message}",
                "apimsg": f"Couldn't add variable field: {e.message}",
                "apimsghtml": f"Couldn't add variable field: {e.html_message}",
            }
        # print("field edit results: %s" % field_results)
        # print("var_results: %s" % var_results)

        return {
            "status": "success",
            "msg": "Variable field added.",
            "field_id": var_results["data"]["id"],
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
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't edit variable field: User session missing.",
                    "apimsg": "Couldn't edit variable field: User session missing.",
                    "apimsghtml": "Couldn't edit variable field: User session missing.",
                }

            yield self._YomboAPI.request("PATCH", f"/v1/variable/field/{field_id}",
                                         data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't edit variable field: {e.message}",
                "apimsg": f"Couldn't edit variable field: {e.message}",
                "apimsghtml": f"Couldn't edit variable field: {e.html_message}",
            }

        # print("field edit results: %s" % field_results)

        return {
            "status": "success",
            "msg": "Variable field edited.",
            "field_id": field_id,
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
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't delete variable field: User session missing.",
                    "apimsg": "Couldn't delete variable field: User session missing.",
                    "apimsghtml": "Couldn't delete variable field: User session missing.",
                }

            yield self._YomboAPI.request("DELETE", f"/v1/variable/field/{field_id}",
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't delete variable field: {e.message}",
                "apimsg": f"Couldn't delete variable field: {e.message}",
                "apimsghtml": f"Couldn't delete variable field: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Variable field deleted.",
            "field_id": field_id,
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
            "status": 1,
        }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't enable variable field: User session missing.",
                    "apimsg": "Couldn't enable variable field: User session missing.",
                    "apimsghtml": "Couldn't enable variable field: User session missing.",
                }

            yield self._YomboAPI.request("PATCH", f"/v1/variable/field/{field_id}",
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't enable variable field: {e.message}",
                "apimsg": f"Couldn't enable variable field: {e.message}",
                "apimsghtml": f"Couldn't enable variable field: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Variable field enabled.",
            "field_id": field_id,
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
            "status": 0,
        }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't disable variable field: User session missing.",
                    "apimsg": "Couldn't disable variable field: User session missing.",
                    "apimsghtml": "Couldn't disable variable field: User session missing.",
                }

            yield self._YomboAPI.request("PATCH", f"/v1/variable/field/{field_id}",
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't disable variable field: {e.message}",
                "apimsg": f"Couldn't disable variable field: {e.message}",
                "apimsghtml": f"Couldn't disable variable field: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Variable field disabled.",
            "field_id": field_id,
        }
