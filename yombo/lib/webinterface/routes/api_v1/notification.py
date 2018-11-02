from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found

def route_api_v1_notification(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/notification", methods=["GET"])
        @require_auth(api=True)
        def apiv1_notifications_get(webinterface, request, session):
            session.has_access("notification", "*", "view", raise_error=True)
            return return_good(request, "". webinterface.notifications.notifications)

        @webapp.route("/notification/<string:notification_id>/ack", methods=["GET"])
        @require_auth(api=True)
        def apiv1_notifications_ack_get(webinterface, request, session, notification_id):
            session.has_access("notification", "*", "view", raise_error=True)
            try:
                webinterface._Notifications.ack(notification_id)
            except KeyError as e:
                return return_not_found(request)
            return return_good(request)
