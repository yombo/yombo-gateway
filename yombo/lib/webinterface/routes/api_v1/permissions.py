# Import python libraries
# from twisted.internet.defer import inlineCallbacks
from yombo.classes.jsonapi import JSONApi
from yombo.lib.webinterface.auth import get_session
from yombo.lib.webinterface.routes.api_v1.__init__ import return_not_found

from yombo.constants.permissions import AUTH_PLATFORM_PERMISSION


def route_api_v1_permissions(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/permissions", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_permissions_get(webinterface, request, session):
            session.is_allowed(AUTH_PLATFORM_PERMISSION, "view")
            return webinterface.render_api(request,
                                           data=JSONApi(webinterface._Permissions.get_all()),
                                           data_type="permissions",
                                           )

        @webapp.route("/permissions/<string:permission_id>", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_permissions_details_get(webinterface, request, session, permission_id):
            webinterface._Validate.id_string(permission_id)
            session.is_allowed(AUTH_PLATFORM_PERMISSION, "view", permission_id)
            if permission_id in webinterface._Permissions:
                permission = webinterface._Permissions[permission_id]
            else:
                return return_not_found(request, "Role not found")

            return webinterface.render_api(request,
                                           data=JSONApi(permission),
                                           data_type="permissions",
                                           )
