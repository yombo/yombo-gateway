"""
Generic debug handler for /api/v1/debug route.
"""
from yombo.classes.jsonapi import JSONApi
from yombo.constants.library_references import LIBRARY_REFERENCES
from yombo.constants.permissions import AUTH_PLATFORM_SYSTEM_OPTION
from yombo.core.exceptions import YomboWebinterfaceError
from yombo.lib.webinterface.auth import get_session

DEBUG_TYPES = [
    "atoms",
    "automation_rules",
    "cache",
    "commands",
    "crontab",
    "devices",
    "device_command_inputs",
    "device_command_types",
    "device_types",
    "gateways",
    "input_types",
    "locations",
    "modules",
    "moduledevicetypes",
    "notifications",
    "scenes",
    "sqldicts",
    "sslcerts",
    "states",
    "storage",
    "users",
    "variable_data",
    "variable_fields",
    "variable_groups",
]


def route_api_v1_debug(webapp):
    with webapp.subroute("/api/v1") as webapp:
        @webapp.route("/debug", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_debug_get(webinterface, request, session):
            session.is_allowed(AUTH_PLATFORM_SYSTEM_OPTION, "debug")

            try:
                debug_type = request.args.get("debug_type")[0]
            except Exception as e:
                debug_type = None

            if debug_type is None or debug_type not in DEBUG_TYPES:
                raise YomboWebinterfaceError(errors="Debug type supplied is invalid",
                                             error_code="invalid_debug_type",
                                             title="Invalid debug type",
                                             response_code=400)

            if debug_type not in LIBRARY_REFERENCES:
                raise YomboWebinterfaceError(errors="Debug type is not supported.",
                                             error_code="unsupported_debug_type",
                                             title="Unsupported debug type",
                                             response_code=400)

            klass = getattr(webinterface, LIBRARY_REFERENCES[debug_type]["class"])
            # print(klass.to_list())
            return webinterface.render_api(request,
                                           data=JSONApi(klass.get_all()),
                                           data_type=debug_type,
                                           )
