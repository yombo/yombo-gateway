# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found, return_error, return_unauthorized
from yombo.utils import epoch_to_string, bytes_to_unicode

def route_api_v1_notification(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route('/notification', methods=['GET'])
        @require_auth()
        def apiv1_notifications_get(webinterface, request, session):
            return return_good(request, ''. webinterface.notifications.notifications)

        @webapp.route('/notification/<string:notification_id>/ack', methods=['GET'])
        @require_auth()
        def apiv1_notifications_ack_get(webinterface, request, session, notification_id):
            try:
                webinterface._Notifications.ack(notification_id)
            except KeyError as e:
                return return_not_found(request)
            return return_good(request)

        # @webapp.route('/web_notif', methods=['GET'])
        # @require_auth()
        # def api_v1_web_notif_get(webinterface, request, session):
        #     action = request.args.get('action')[0]
        #     results = {}
        #     if action == "closed":
        #         id = request.args.get('id')[0]
        #         # print "alert - id: %s" % id
        #         if id in webinterface.alerts:
        #             del webinterface.alerts[id]
        #             results = {"status": 200}
        #     request.setHeader('Content-Type', 'application/json')
        #     return json.dumps(results)