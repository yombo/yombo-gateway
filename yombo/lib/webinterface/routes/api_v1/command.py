# Import python libraries

from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good\


def route_api_v1_command(webapp):
    with webapp.subroute("/api/v1") as webapp:
        @webapp.route('/command', methods=['GET'])
        @require_auth(api=True)
        def apiv1_command_get(webinterface, request, session):
            return return_good(request, payload=webinterface._Commands.full_list_commands())
