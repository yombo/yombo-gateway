# Import python libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found


def route_api_v1_device_command(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/device_command", methods=["GET"])
        @require_auth(api=True)
        def apiv1_device_command_getall_get(webinterface, request, session):
            session.has_access("device_command", "*", "view", raise_error=True)
            return webinterface.render_api(request, None,
                                           data_type="device_commands",
                                           attributes=webinterface._DeviceCommands.get_device_commands_list()
                                           )

        @webapp.route("/device_command/<string:device_command_id>", methods=["GET"])
        @require_auth(api=True)
        def apiv1_device_command_getone_get(webinterface, request, session, device_command_id):
            session.has_access("device_command", device_command_id, "view", raise_error=True)
            if device_command_id in webinterface._DeviceCommands.device_commands:
                device_command = webinterface._DeviceCommands.device_commands[device_command_id]
                return webinterface.render_api(request, None,
                                               data_type="device_commands",
                                               attributes=device_command(device_command.asdict())
                                               )

                return return_good(
                    request,
                    payload=device_command.asdict()
                )

            return return_not_found(request, f"Error with device command id: {device_command_id}")
