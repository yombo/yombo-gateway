# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning

REQUEST_TYPES = {
    "commands": {
        "endpoint": "/v1/commands",
        "title": "command",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "devices": {
        "endpoint": "/v1/devices",
        "title": "device",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "device_types": {
        "endpoint": "/v1/device_types",
        "title": "device types",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "device_type_commands": {
        "endpoint": "/v1/device_type_commands",
        "title": "device type commands",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "device_command_inputs": {
        "endpoint": "/v1/device_command_inputs",
        "title": "device command inputs",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "gateways": {
        "endpoint": "/v1/gateways",
        "title": "gateway",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "gateway_modules": {
        "endpoint": "/v1/gateways/{}/modules",
        "title": "gateway module",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "gateways_users": {
        "endpoint": "/v1/gateways/{}/users",
        "title": "gateway user",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "input_types": {
        "endpoint": "/v1/input_types",
        "title": "input types",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "locations": {
        "endpoint": "/v1/locations",
        "title": "location",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "modules": {
        "endpoint": "/v1/modules",
        "title": "module",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "module_device_types": {
        "endpoint": "/v1/module_device_types",
        "title": "module device types",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "nodes": {
        "endpoint": "/v1/nodes",
        "title": "nodes",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "variables_data": {
        "endpoint": "/v1/variables",
        "title": "variable data",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "variables_fields": {
        "endpoint": "/v1/variable_fields",
        "title": "variable fields",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    "variables_groups": {
        "endpoint": "/v1/variable_groups",
        "title": "variable groups",
        "methods": ["POST", "PATCH", "DELETE"]
        },
    }

SYNC_MIXIN_MAP = {

}


class YA_Commands(object):
    """
    This class extends the Yombo API library to generic functions for making requests to the Yombo API - this is
    used only to send data such as adding new items, updating items, or deleting itmes. This doesn't fetch items.
    """
    def request_data(self, request_type):
        """
        Gets the request_data for the given request type. If the request isn't immediately found, it will try to
        find it using the _internal_name for the sync to everywhere mixin.

        :param request_type:
        :return:
        """
        if request_type in REQUEST_TYPES:
            return REQUEST_TYPES[request_type]

        if request_type in SYNC_MIXIN_MAP:
            return REQUEST_TYPES[SYNC_MIXIN_MAP[request_type]]

        raise YomboWarning(
            {
                "title": "Unknown request type",
                "detail": f"The request_type of '{request_type}' was not found.",
            },
            component="YomboAPI",
            name="request_data")

    def _generate_uri(self, request_data, data_id=None, index=None):
        """ Internal: Used to generate URI ."""
        if index is None:
            base = request_data["endpoint"]
        else:
            base = request_data["endpoint"].format(index)

        if data_id is None:
            return base
        else:
            return f"base/{data_id}"

    @inlineCallbacks
    def add(self, request_type, data, session=None, data_id=None, index=None):
        """
        Used to (POST) items to the Yombo Gateway. This can be used to create new commands, devices, etc.

        Some requests, such as the gateway modules, require the ID of the gateway to modify. This is specified
        in the index parameter.

        :param request_type: Request type such as "commands", "variables_data", or "modules".
        :type request_type: str
        :param data: Fields to send to the Yombo API.
        :type data: dict
        :param session: A session to associate the change. Should be provided if the change is a the result of a web request.
        :type session: websession instance
        :param index: Some requests, such as gateway modules, require an additional ID to work.
        :type index: str
        :return: Returns a dictionary containing various attributes on success. Raises YomboWarning on failure.
        :rtype: dict
        """
        request_data = self.request_data(request_type)
        if "POST" not in request_data["methods"]:
            raise YomboWarning(f"'{request_type} cannot perform 'POST' request.")

        try:
            api_reqults = yield self._YomboAPI.request("POST",
                                                       self._generate_uri(request_data, data_id=data_id, index=index),
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            raise YomboWarning(
                {
                    "title": f"{request_data['title_failed']}",
                    "detail": e.message,
                },
                component="YomboAPI",
                name="add")

        return {
            "status": "success",
            "msg": "Item added.",
            "data": api_reqults["data"],
        }

    @inlineCallbacks
    def patch(self, request_type, data, session=None, data_id=None, index=None):
        """
        Used to update (PATCH) items to the Yombo Gateway. This can be used to edit commands, devices, etc.

        Some requests, such as the gateway modules, require the ID of the gateway to modify. This is specified
        in the index parameter.

        :param request_type: Request type such as "commands", "variables_data", or "modules".
        :type request_type: str
        :param data: Fields to send to the Yombo API.
        :type data: dict
        :param session: A session to associate the change. Should be provided if the change is a the result of a web request.
        :type session: websession instance
        :param index: Some requests, such as gateway modules, require an additional ID to work.
        :type index: str
        :return: Returns a dictionary containing various attributes on success. Raises YomboWarning on failure.
        :rtype: dict
        """
        request_data = REQUEST_TYPES[request_type]
        if "PATCH" not in request_data["methods"]:
            raise YomboWarning(f"'{request_type} cannot perform 'PATCH' request.")

        try:
            api_reqults = yield self._YomboAPI.request("PATCH",
                                                       self._generate_uri(request_data, data_id=data_id, index=index),
                                                       data,
                                                       session=session)
        except YomboWarning as e:
            raise YomboWarning(
                {
                    "title": request_data["title_failed"],
                    "detail": e.message,
                },
                component="YomboAPI",
                name="add")

        return {
            "status": "success",
            "msg": "Item updated.",
            "data": api_reqults["data"],
        }

    @inlineCallbacks
    def enable(self, request_type, session=None, data_id=None, index=None):
        """
        Used to update (PATCH) items to the Yombo Gateway. This can be used to edit commands, devices, etc.
        This basically just sends a single field of 'status' to 1, and uses the patch() method.

        Some requests, such as the gateway modules, require the ID of the gateway to modify. This is specified
        in the index parameter.

        :param request_type: Request type such as "commands", "variables_data", or "modules".
        :type request_type: str
        :param session: A session to associate the change. Should be provided if the change is a the result of a web request.
        :type session: websession instance
        :param index: Some requests, such as gateway modules, require an additional ID to work.
        :type index: str
        :return: Returns a dictionary containing various attributes on success. Raises YomboWarning on failure.
        :rtype: dict
        """
        results = yield self.patch(request_type, {"status": 1}, session=session, index=index)
        return results

    @inlineCallbacks
    def disable(self, request_type, session=None, data_id=None, index=None):
        """
        Used to update (PATCH) items to the Yombo Gateway. This can be used to edit commands, devices, etc.
        This basically just sends a single field of 'status' to 1, and uses the patch() method.

        Some requests, such as the gateway modules, require the ID of the gateway to modify. This is specified
        in the index parameter.

        :param request_type: Request type such as "commands", "variables_data", or "modules".
        :type request_type: str
        :param session: A session to associate the change. Should be provided if the change is a the result of a web request.
        :type session: websession instance
        :param index: Some requests, such as gateway modules, require an additional ID to work.
        :type index: str
        :return: Returns a dictionary containing various attributes on success. Raises YomboWarning on failure.
        :rtype: dict
        """
        results = yield self.patch(request_type, {"status": 0}, session=session, index=index)
        return results

    @inlineCallbacks
    def delete(self, request_type, data_id, purge=None, session=None, index=None):
        """
        Used to delete (delete) items to the Yombo Gateway. This can be used to delete commands, devices, etc.

        Optionally, we can ask the YomboAPI to purge the data. Typically, data is marked for deletion in 30 days.
        This allows some items to be recovered. A purge request will ask the Yombo API to just delete it now without
        tossing it into the trash.

        There is no guarantee that items can be recovered - many items are deleted immediately.

        Some requests, such as the gateway modules, require the ID of the gateway to modify. This is specified
        in the index parameter.

        :param request_type: Request type such as "commands", "variables_data", or "modules".
        :type request_type: str
        :param data_id: The item id to delete. Such as variable_data_id.
        :type data_id: str
        :param purge: Set to True if the data should be deleted instead of the trash bin.
        :type purge: bool
        :param session: A session to associate the change. Should be provided if the change is a the result of a web request.
        :type session: websession instance
        :param index: Some requests, such as gateway modules, require an additional ID to work.
        :type index: str
        :return: Returns a dictionary containing various attributes on success. Raises YomboWarning on failure.
        :rtype: dict
        """
        request_data = REQUEST_TYPES[request_type]
        if "DELETE" not in request_data["methods"]:
            raise YomboWarning(f"'{request_type} cannot perform 'DELETE' request.")

        try:
            api_reqults = yield self._YomboAPI.request("DELETE",
                                                       self._generate_uri(request_data, data_id=data_id, index=index),
                                                       session=session)
        except YomboWarning as e:
            raise YomboWarning(
                {
                    "title": request_data["title_failed"],
                    "detail": e.message,
                },
                component="YomboAPI",
                name="delete")

        return {
            "status": "success",
            "msg": "Item updated.",
            "data": api_reqults["data"],
        }
