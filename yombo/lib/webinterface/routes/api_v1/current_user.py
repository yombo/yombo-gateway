"""
Handles calls for the current user data. Gets the user's session based on the user's cookie
and returns the access_token which can be used to access the Yombo API. THis primarily used
by the frontend application to make requests.

"""
# Import Yombo libraries
from yombo.classes.jsonapi import JSONApi
from yombo.constants import AUTH_TYPE_WEBSESSION
from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import get_session


def route_api_v1_current_user(webapp):
    with webapp.subroute("/api/v1/current_user") as webapp:

        @webapp.route("/access_token", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_current_user_access_token(webinterface, request, session):
            """
            This gets the current logged in user's access token. This is typically called by the frontend
            application so that I can make calls to Yombo API.
            """
            if session.auth_type != AUTH_TYPE_WEBSESSION:
                raise YomboWarning(f"Must authenticate with a websession (cookie), not {session.auth_type}",
                                   title="Invalid session type")
            access_token = session.get_access_token(request)
            return webinterface.render_api(request,
                                           data=JSONApi(data={
                                               "type": "user_session_token",
                                               "id": request.auth.auth_id,
                                               "attributes": {
                                                   "id": request.auth.auth_id,
                                                   "access_token": access_token[0],
                                                   "access_token_expires": access_token[1],
                                                   "session": request.session_long_id,
                                                   }
                                               }),
                                           data_type="user_session_token",
                                           )

