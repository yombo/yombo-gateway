"""
This generic router can handle the majority of the common API interactions. Complex interactions will have their
own independant file and routes.
"""
# Import python libraries
from inspect import signature
import sys
import traceback
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from twisted.internet.defer import inlineCallbacks, maybeDeferred

from yombo.classes.jsonapi import JSONApi
from yombo.core.exceptions import YomboWebinterfaceError
from yombo.core.log import get_logger
from yombo.lib.webinterface.auth import get_session
from yombo.lib.webinterface.routes.api_v1 import request_args, request_data
from yombo.utils import bytes_to_unicode

# Monkey patches until: https://twistedmatrix.com/trac/ticket/9759#ticket
import cgi
from urllib.parse import (ParseResultBytes, urlparse as _urlparse, unquote_to_bytes as unquote)

logger = get_logger("lib.webinterface.routes.api_v1.generic_library_routes")


def get_route_data(generic_router_list: dict, route_type: str, resource_name: str, action: str) -> dict:
    """
    Get the generic router data. If it's not found, raises YomboWebinterfaceError.

    :param generic_router_list:
    :param route_type:
    :param resource_name:
    :param action:
    :param item_id:
    """
    if resource_name not in generic_router_list[route_type]:
        raise YomboWebinterfaceError(response_code=404, error_code="api-resource-not-found-404")

    route_data = generic_router_list[route_type][resource_name]
    if action not in route_data["actions"]:
        raise YomboWebinterfaceError(response_code=405)

    return route_data


def route_api_v1_generic_library_routes(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/lib/<string:resource_name>", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_generic_route_library_get(webinterface, request, session, resource_name):
            """
            Handles the majority of the api resource view requests.

            :param webinterface:
            :param request:
            :param session:
            :param resource_name:
            :return:
            """
            data = request_args(webinterface, request)
            filters = None
            if "filter" in data:
                filters = data["filter"]

            if resource_name == "gateway_modules":
                resource_name = "modules"

            route_data = get_route_data(webinterface.generic_router_list, "libraries", resource_name, "view")
            session.is_allowed(route_data["auth_platform"], "view")
            klass = getattr(webinterface, route_data["resource_name"])
            data_type = route_data["resource_label"]
            if data_type == "modules":
                data_type = "gateway_modules"
            try:
                # print(f"generic get: {klass.get_all(filters=filters, gateway_id=webinterface._gateway_id)}")
                return webinterface.render_api(request,
                                               data=JSONApi(klass.get_all(filters=filters, gateway_id=webinterface._gateway_id),
                                                            data_type=data_type),
                                               data_type=data_type,
                                               )
            except Exception as e:
                logger.error("--------==(Error: {e})==--------", e=e)
                logger.error("--------------------------------------------------------")
                logger.error("{error}", error=sys.exc_info())
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
                logger.error("--------------------------------------------------------")

        @webapp.route("/lib/<string:resource_name>/<string:item_id>", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_generic_route_library_details_get(webinterface, request, session, resource_name, item_id):
            """
            Handles the majority of the api resource view requests.

            :param webinterface:
            :param request:
            :param session:
            :param resource_name:
            :return:
            """
            route_data = get_route_data(webinterface.generic_router_list, "libraries", resource_name, "view")
            session.is_allowed(route_data["auth_platform"], "view", item_id=item_id)
            library_reference = getattr(webinterface, route_data["resource_name"])

            data_type = route_data["resource_label"]
            if data_type == "modules":
                data_type = "gateway_modules"

            new_kwargs = {}
            arguments = signature(library_reference.get)
            if "instance" in arguments.parameters:
                new_kwargs["instance"] = True
            return webinterface.render_api(request,
                                           data=JSONApi(library_reference.get(item_id, **new_kwargs), data_type=data_type),
                                           data_type=data_type,
                                           )

        def generic_arguments(webinterface, request, session, prefix: Optional[str] = None) -> dict:
            """
            Returns a dictionary of arguments to pass on the library reference.

            :param request:
            :param session:
            :param prefix:
            :return:
            """
            incoming = request_data(webinterface, request)
            if prefix is None:
                prefix = ""
            arguments = {
                f"{prefix}load_source": "library",
                f"{prefix}request": request,
                f"{prefix}request_context": f"web:{request.request_id},{request.getClientIP()}",
                f"{prefix}authentication": session,
            }
            return incoming, arguments

        @webapp.route("/lib/<string:resource_name>/<string:item_id>", methods=["DELETE"])
        @get_session(auth_required=True, api=True)
        @inlineCallbacks
        def apiv1_generic_route_library_delete(webinterface, request, session, resource_name, item_id):
            """
            Deletes a resource record. The required attributes varies depending on what is being deleted.

            :param webinterface:
            :param request:
            :param session:
            :param resource_name:
            :param item_id:
            :return:
            """
            route_data = get_route_data(webinterface.generic_router_list, "libraries", resource_name, "remove")
            session.is_allowed(route_data["auth_platform"], "remove")
            library_reference = getattr(webinterface, route_data["resource_name"])
            incoming, arguments = generic_arguments(webinterface, request, session)

            results = yield library_reference.api_update(item_id, **arguments)
            return webinterface.render_api(request,
                                           data=JSONApi(results),
                                           data_type=route_data["resource_label"],
                                           )

        @webapp.route("/lib/<string:resource_name>/<string:item_id>", methods=["PATCH", "PUT"])
        @get_session(auth_required=True, api=True)
        @inlineCallbacks
        def apiv1_generic_route_library_patch(webinterface, request, session, resource_name, item_id):
            """
            Updates (patches/puts) a resource record. The required attributes varies depending on what is being
            updated. Typically is the same as API.Yombo.Net items. See: https://yombo.net/API:Overview

            :param webinterface:
            :param request:
            :param session:
            :param resource_name:
            :param item_id:
            :return:
            """
            route_data = get_route_data(webinterface.generic_router_list, "libraries", resource_name, "modify")
            session.is_allowed(route_data["auth_platform"], "modify")
            library_reference = getattr(webinterface, route_data["resource_name"])
            incoming, arguments = generic_arguments(webinterface, request, session)

            results = yield library_reference.api_update(item_id, incoming, **arguments)
            return webinterface.render_api(request,
                                           data=JSONApi(results),
                                           data_type=route_data["resource_label"],
                                           )

        @webapp.route("/lib/<string:resource_name>", methods=["POST"])
        @get_session(auth_required=True, api=True)
        @inlineCallbacks
        def apiv1_generic_route_library_post(webinterface, request, session, resource_name):
            """
            Create a new resource record. The required attributes varies depending on what is being created.

            :param webinterface:
            :param request:
            :param session:
            :param resource_name:
            :return:
            """
            route_data = get_route_data(webinterface.generic_router_list, "libraries", resource_name, "create")
            session.is_allowed(route_data["auth_platform"], "create")
            library_reference = getattr(webinterface, route_data["resource_name"])
            incoming, arguments = generic_arguments(webinterface, request, session, prefix="_")
            incoming.update(arguments)

            results = yield library_reference.new(**incoming)
            return webinterface.render_api(request,
                                           data=JSONApi(results),
                                           data_type=route_data["resource_label"],
                                           )
