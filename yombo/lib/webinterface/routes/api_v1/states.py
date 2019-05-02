"""
Handles calls to view the system states.
"""
# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth


def route_api_v1_states(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/states", methods=["GET"])
        @require_auth(api=True)
        def apiv1_states_get(webinterface, request, session):
            """ Gets the system states. """
            return webinterface.render_api(request, None,
                                           data_type="atoms",
                                           attributes=webinterface._States.get_list()
                                           )

        @webapp.route("/states/<string:state>", methods=["GET"])
        @require_auth(api=True)
        def apiv1_states_details_get(webinterface, request, session, state):
            """ Gets a single system state. """
            return webinterface.render_api(request, None,
                                           data_type="states",
                                           attributes=webinterface._States.get(state)
                                           )

        # @webapp.route("/states/<string:state>", methods=["POST"])
        # @require_auth(api=True)
        # def apiv1_states_details_get(webinterface, request, session, state):
        #     """ Sets  a system state. """
        #     return webinterface.render_api(request, None,
        #                                    data_type="states",
        #                                    attributes=webinterface._States.get(state)
        #                                    )
