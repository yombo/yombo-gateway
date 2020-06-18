# Import python libraries
import json

from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import get_session
from yombo.constants import CONTENT_TYPE_JSON


def route_api_v1_frontend(webapp):
    with webapp.subroute("/api/v1/frontend") as webapp:

        @webapp.route("/dashboard_navbar_items", methods=["GET"])
        @get_session(auth_required=True, api=True)
        @inlineCallbacks
        def apiv1_frontend_dashboard_navbar_items_get(webinterface, request, session):
            results = yield webinterface.dashboard_sidebar_navigation()
            return webinterface.render_api_raw(request,
                                               data=results,
                                               data_type="dashboard_navbar_items",
                                               )

        @webapp.route("/globalitems_navbar_items", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_frontend_globalitems_navbar_items_get(webinterface, request, session):
            return webinterface.render_api_raw(request,
                                               data=webinterface.global_items_sidebar_navigation(),
                                               data_type="globalitems_navbar_items",
                                               )
