# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found, return_error, return_unauthorized
from yombo.utils import epoch_to_string, bytes_to_unicode

def route_api_v1_automation(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route('/automation/list/items', methods=['GET'])
        @require_auth()
        def apiv1_automation_list_items_get(webinterface, request, session):
            try:
                platform = request.args.get('platform')[0]
            except:
                return return_error(request, 'platform must be specified.')
            # try:
            #     type = request.args.get('type')[0]
            # except:
            #     return return_error('type must be specified.')
            webinterface._Automation.get_available_items(platform=platform)

            a = return_good(request, 'The list')
            request.setHeader('Content-Type', 'application/json')
            return json.dumps(a)
