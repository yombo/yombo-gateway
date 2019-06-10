# Import python libraries

from yombo.lib.webinterface.auth import require_auth


def route_api_v1_command(webapp):
    with webapp.subroute("/api/v1") as webapp:
        @webapp.route("/commands", methods=["GET"])
        @require_auth(api=True)
        def apiv1_command_get(webinterface, request, session):
            return webinterface.render_api(request, None,
                                           data_type="command",
                                           attributes=webinterface._Commands.class_storage_as_list()
                                           )
