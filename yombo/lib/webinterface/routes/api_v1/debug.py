# Import python libraries

from yombo.lib.webinterface.auth import require_auth

DEBUG_TYPES = {
    "atoms": {
        "class": "_Atoms"
    },
    "automation_rules": {
        "class": "_Automation"
    },
    "cache": {
        "class": "_Cache"
    },
    "commands": {
        "class": "_Commands"
    },
    "crontab": {
        "class": "_CronTab"
    },
    "devices": {
        "class": "_Devices"
    },
    "device_command_inputs": {
        "class": "_DeviceCommandInputs"
    },
    "device_command_types": {
        "class": "_DeviceTypeCommands"
    },
    "device_types": {
        "class": "_DeviceTypes"
    },
    "gateways": {
        "class": "_Gateways"
    },
    "input_types": {
        "class": "_InputTypes"
    },
    "locations": {
        "class": "_Locations"
    },
    "modules": {
        "class": "_Modules"
    },
    "moduledevicetypes": {
        "class": "_ModuleDeviceTypes"
    },
    "notifications": {
        "class": "_Notifications"
    },
    "scenes": {
        "class": "_Scenes"
    },
    "sqldict": {
        "class": "_SQLDict"
    },
    "sslcerts": {
        "class": "_SSLCerts"
    },
    "states": {
        "class": "_States"
    },
    "storage": {
        "class": "_Storage"
    },
    "users": {
        "class": "_Users"
    },
    "variables_data": {
        "class": "_VariableData"
    },
    "variables_fields": {
        "class": "_VariableFields"
    },
    "variables_groups": {
        "class": "_VariableGroups"
    },
}


def route_api_v1_debug(webapp):
    with webapp.subroute("/api/v1") as webapp:
        @webapp.route("/debug", methods=["GET"])
        @require_auth(api=True)
        def apiv1_debug_get(webinterface, request, session):

            try:
                debug_type = request.args.get("debug_type")[0]
            except Exception as e:
                debug_type = None

            if debug_type is None or debug_type not in DEBUG_TYPES:
                return webinterface.render_api_error(request, None,
                                                     code="invalid_debug_type",
                                                     title="Invalid debug type",
                                                     detail="Debug type supplied is invalid.",
                                                     response_code=500)

            debug = DEBUG_TYPES[debug_type]

            klass = getattr(webinterface, debug["class"])
            print(klass.class_storage_as_list())
            return webinterface.render_api(request, None,
                                           data_type=debug_type,
                                           attributes=klass.class_storage_as_list()
                                           )
