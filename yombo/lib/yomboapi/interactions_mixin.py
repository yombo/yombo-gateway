"""
The YomboAPI library has been split up to keep it organized. This just extends the YomboAPI to handle
requests.
"""
# Import python libraries
from typing import Any, Optional, Union
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("lib.yomboapi.generic")

REQUEST_TYPES = {
    "commands": {
        "endpoints": "/v1/commands",
        "endpoint": "/v1/commands/{id}",
        "title": "command",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "devices": {
        "endpoints": "/v1/devices",
        "endpoint": "/v1/devices/{id}",
        "title": "device",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "device_types": {
        "endpoints": "/v1/device_types",
        "endpoint": "/v1/device_types/{id}",
        "title": "device types",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "device_type_commands": {
        "endpoints": "/v1/device_type_commands",
        "endpoint": "/v1/device_type_commands/{id}",
        "title": "device type commands",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "device_command_inputs": {
        "endpoints": "/v1/device_command_inputs",
        "endpoint": "/v1/device_command_inputs/{id}",
        "title": "device command inputs",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "gateways": {
        "endpoints": "/v1/gateways",
        "endpoint": "/v1/gateways/{id}",
        "title": "gateway",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "gateway_modules": {
        "endpoints": "/v1/gateways/{gw_id}/modules",
        "endpoint": "/v1/gateways/{gw_id}/modules{id}",
        "title": "gateway module",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "gateways_users": {
        "endpoints": "/v1/gateways/{gw_id}/users",
        "endpoint": "/v1/gateways/{gw_id}/users/{id}",
        "title": "gateway user",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "input_types": {
        "endpoints": "/v1/input_types",
        "endpoint": "/v1/input_types/{id}",
        "title": "input types",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "locations": {
        "endpoints": "/v1/locations",
        "endpoint": "/v1/locations/{id}",
        "title": "location",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "modules": {
        "endpoints": "/v1/modules",
        "endpoint": "/v1/modules/{id}",
        "title": "module",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "module_device_types": {
        "endpoints": "/v1/module_device_types",
        "endpoint": "/v1/module_device_types/{id}",
        "title": "module device types",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "nodes": {
        "endpoints": "/v1/nodes",
        "endpoint": "/v1/nodes/{id}",
        "title": "nodes",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "variable_data": {
        "endpoints": "/v1/variables",
        "endpoint": "/v1/variables/{id}",
        "title": "variable data",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "variables_fields": {
        "endpoints": "/v1/variable_fields",
        "endpoint": "/v1/variable_fields/{id}",
        "title": "variable fields",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    "variables_groups": {
        "endpoints": "/v1/variable_groups",
        "endpoint": "/v1/variable_groups/{id}",
        "title": "variable groups",
        "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"]
        },
    }


class InteractionsMixin:
    """
    This class extends the Yombo API library to add generic functions for making requests to the Yombo API - this is
    used only to send data such as adding new items, updating items, or deleting items.
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

        raise YomboWarning(
            {
                "title": "Unknown request type",
                "detail": f"The request_type of '{request_type}' was not found.",
            },
            component_name="YomboAPI::InteractionsMixin::request_data",
            component_type="library")

    @inlineCallbacks
    def new(self, request_type: str, data: dict, url_format: Optional[dict] = None) -> dict:
        """
        Uses (POST) to add items to the Yombo Gateway. This can be used to create new commands, devices, etc.

        Some requests, such as the gateway modules, require the ID of the gateway to modify. This is specified
        in the index parameter.

        :param request_type: Request type such as "commands", "variables_data", or "modules".
        :param data: Fields to send to the Yombo API.
        :param url_format: A dictionary to send the format() function for the url.
        :return: Returns a dictionary containing various attributes on success. Raises YomboWarning on failure.
        """
        logger.debug("api::new, data: ({data_type}) - {data}", data_type=type(data), data=data)
        request_details = self.request_data(request_type)
        if "POST" not in request_details["methods"]:
            raise YomboWarning(f"'{request_type} cannot perform 'POST' request.")

        if isinstance(url_format, dict) is False:
            url_format = {}

        if "gw_id" in request_details["endpoints"] and "gw_id" not in url_format:
            url_format["gw_id"] = self._gateway_id

        try:
            response = yield self._YomboAPI.request("POST",
                                                    request_details["endpoints"].format(**url_format),
                                                    body=data)
        except YomboWarning as e:
            logger.warn("YomboAPI::InteractionsMixin::New - error: {e}", e=e)
            raise YomboWarning(
                {
                    "title": "Error with API request.",
                    "detail": "Unknown error.",
                },
                component_name="YomboAPI::InteractionsMixin::new",
                component_type="library")

        if response.response_code != 201:
            raise YomboWarning(response.content["errors"])

        return {
            "status": "ok",
            "content": response.content,
            "response": response
        }

    @inlineCallbacks
    def update(self, request_type: str, url_format: dict, data: dict) -> dict:
        """
        Used to update (PATCH) items to the Yombo Gateway. This can be used to edit commands, devices, etc.

        Some requests, such as the gateway modules, require the ID of the gateway to modify. This is specified
        in the index parameter.

        :param request_type: Request type such as "commands", "variables_data", or "modules".
        :param url_format: A dictionary to send the format() function for the url.
        :param data: Fields to send to the Yombo API.
        :return: Returns a dictionary containing various attributes on success. Raises YomboWarning on failure.
        """
        try:
            request_details = self.request_data(request_type)
        except YomboWarning as e:
            logger.info("Unable to update item to api: {e}", e=e)
            return {
                "status": "fail",
            }
        if "PATCH" not in request_details["methods"]:
            raise YomboWarning(f"'{request_type} cannot perform 'PATCH' request to Yombo API.")

        if isinstance(url_format, dict) is False:
            url_format = {}

        if "gw_id" in request_details["endpoints"] and "gw_id" not in url_format:
            url_format["gw_id"] = self._gateway_id

        try:
            response = yield self._YomboAPI.request("PATCH",
                                                    request_details["endpoint"].format(**url_format),
                                                    body=data)
        except YomboWarning as e:
            logger.error("Error doing api update: {e}", e=e)
            raise YomboWarning(
                {
                    "title": request_details["title_failed"],
                    "detail": e.message,
                },
                component_name="YomboAPI::InteractionsMixin::update",
                component_type="library")

        return {
            "status": "ok",
            "content": response.content,
            "response": response
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
        request_details = REQUEST_TYPES[request_type]
        if "DELETE" not in request_details["methods"]:
            raise YomboWarning(f"'{request_type} cannot perform 'DELETE' request.")

        try:
            response = yield self._YomboAPI.request("DELETE",
                                                    self._generate_uri(
                                                        request_details,
                                                        data_id=data_id,
                                                        index=index),
                                                    session=session)
        except YomboWarning as e:
            raise YomboWarning(
                {
                    "title": request_details["title_failed"],
                    "detail": e.message,
                },
                component_name="YomboAPI::InteractionsMixin::delete",
                component_type="library")

        return {
            "status": "ok",
            "content": response.content,
            "response": response
        }
