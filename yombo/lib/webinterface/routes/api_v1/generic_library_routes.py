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
from yombo.lib.webinterface.routes.api_v1 import request_args
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
            data = request_args(request)
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
            klass = getattr(webinterface, route_data["resource_name"])

            data_type = route_data["resource_label"]
            if data_type == "modules":
                data_type = "gateway_modules"

            new_kwargs = {}
            arguments = signature(klass.get)
            if "instance" in arguments.parameters:
                new_kwargs["instance"] = True
            return webinterface.render_api(request,
                                           data=JSONApi(klass.get(item_id, **new_kwargs), data_type=data_type),
                                           data_type=data_type,
                                           )

        def generic_arguments(request, session) -> dict:
            """
            Returns a dictionary of arguments to pass on the library reference.

            :param request:
            :param session:
            :return:
            """
            data = request_args(request)
            arguments = {
                "authentication": session,
                "load_source": "library",
                "request_context": f"web:{request.request_id},{request.getClientIP()}",
            }
            return data, arguments

        def _parseHeader(line):
            # cgi.parse_header requires a str
            key, pdict = cgi.parse_header(line.decode('charmap'))

            # We want the key as bytes, and cgi.parse_multipart (which consumes
            # pdict) expects a dict of str keys but bytes values
            key = key.encode('charmap')
            pdict = {x: y.encode('charmap') for x, y in pdict.items()}
            return (key, pdict)

        def parse_qs(qs, keep_blank_values=0, strict_parsing=0):
            """
            Like C{cgi.parse_qs}, but with support for parsing byte strings on Python 3.
            @type qs: C{bytes}
            """
            d = {}
            items = [s2 for s1 in qs.split(b"&") for s2 in s1.split(b";")]
            for item in items:
                try:
                    k, v = item.split(b"=", 1)
                except ValueError:
                    if strict_parsing:
                        raise
                    continue
                if v or keep_blank_values:
                    k = unquote(k.replace(b"+", b" "))
                    v = unquote(v.replace(b"+", b" "))
                    if k in d:
                        d[k].append(v)
                    else:
                        d[k] = [v]
            return d

        def patch_put_hotfix(request):
            """
            Twisted doesn't get arguments for PATCH/PUT. Ticket submitted:
            https://twistedmatrix.com/trac/ticket/9759#ticket

            This method attempts to get the arguments for PATCH and PUT.
            :param request:
            :return:
            """

            ctype = request.requestHeaders.getRawHeaders(b'content-type')[0]
            content = request.content.read()
            clength = len(content)
            request.args = {}

            # print(f"request.method: {request.method}")
            # print(f"ctype: {ctype}")
            # print(f"clength: {clength}")
            # print(f"content: {content}")
            if request.method in (b"POST", b"PATCH", b"PUT") and ctype and clength:
                mfd = b'multipart/form-data'
                key, pdict = _parseHeader(ctype)
                # This weird CONTENT-LENGTH param is required by
                # cgi.parse_multipart() in some versions of Python 3.7+, see
                # bpo-29979. It looks like this will be relaxed and backported, see
                # https://github.com/python/cpython/pull/8530.
                pdict["CONTENT-LENGTH"] = clength
                if key == b'application/x-www-form-urlencoded':
                    # print("parsing url encoded")
                    # print(parse_qs(content, 1))
                    request.args.update(parse_qs(content, 1))
                elif key == mfd:  # This isnt' working. :(
                    try:
                        # print(f"FD 1: pdict: {pdict}")
                        boundary = pdict["boundary"].decode("charmap").replace("-", "")
                        pdict["boundary"] = boundary.encode("charmap")
                        # print(f"FD 2: pdict: {pdict}")
                        cgiArgs = cgi.parse_multipart(
                            request.content, pdict, encoding='utf8',
                            errors="surrogateescape")

                        # print(f"FD: cgiArgs: {cgiArgs}")
                        # The parse_multipart function on Python 3.7+
                        # decodes the header bytes as iso-8859-1 and
                        # decodes the body bytes as utf8 with
                        # surrogateescape -- we want bytes
                        request.args.update({
                            x.encode('iso-8859-1'): \
                                [z.encode('utf8', "surrogateescape")
                                 if isinstance(z, str) else z for z in y]
                            for x, y in cgiArgs.items()})
                    except Exception as e:
                        print(f"error parsing form data: {e}")
                        pass
            request.args = bytes_to_unicode(request.args)

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

            results = yield maybeDeferred(library_reference.delete, item_id)
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
            updated.

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

            patch_put_hotfix(request)
            data, arguments = generic_arguments(request, session)

            results = yield maybeDeferred(library_reference.update, item_id, data, **arguments)
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

            data, arguments = generic_arguments(request, session)
            data.update(arguments)
            results = yield maybeDeferred(library_reference.new, **data)
            return webinterface.render_api(request,
                                           data=JSONApi(results),
                                           data_type=route_data["resource_label"],
                                           )
