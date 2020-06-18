from yombo.constants.permissions import AUTH_PLATFORM_NOTIFICATION
from yombo.lib.webinterface.auth import get_session
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found

def route_api_v1_notification(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/notification", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_notifications_get(webinterface, request, session):
            session.is_allowed(AUTH_PLATFORM_NOTIFICATION, "view")
            return return_good(request, "". webinterface.notifications.notifications)

        @webapp.route("/notification/<string:notification_id>/ack", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_notifications_ack_get(webinterface, request, session, notification_id):
            webinterface._Validate.id_string(notification_id)
            session.is_allowed(AUTH_PLATFORM_NOTIFICATION, "view", notification_id)
            try:
                webinterface._Notifications.ack(notification_id)
            except KeyError as e:
                return return_not_found(request)
            return return_good(request)
