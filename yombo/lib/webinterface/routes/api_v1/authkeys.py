"""
Add rotate endpoint to authkeys.
"""
from yombo.classes.jsonapi import JSONApi
from yombo.constants.permissions import AUTH_PLATFORM_AUTHKEY
from yombo.lib.webinterface.auth import get_session
from yombo.lib.webinterface.routes.api_v1.__init__ import return_error


def route_api_v1_authkeys(webapp):
    with webapp.subroute("/api/v1/lib/auth_keys") as webapp:

        @webapp.route("/<string:auth_id>/rotate", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_authkeys_rotate_get(webinterface, request, session, auth_id):
            webinterface._Validate.id_string(auth_id)
            session.is_allowed(AUTH_PLATFORM_AUTHKEY, "edit", auth_id)
            if len(auth_id) > 100 or isinstance(auth_id, str) is False:
                return return_error(request, "invalid auth_id format", 400)

            authkey = webinterface._AuthKeys[auth_id]
            auth_key_id_full = authkey.rotate()
            results = authkey.to_external()
            results["auth_key_id_full"] = auth_key_id_full

            return webinterface.render_api(request,
                                           data=JSONApi(authkey),
                                           data_type="auth_keys",
                                           )
