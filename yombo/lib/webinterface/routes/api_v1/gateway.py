# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found, return_error, return_unauthorized
from yombo.utils.converters import epoch_to_string

def route_api_v1_gateway(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route('/gateway', methods=['GET'])
        @require_auth(api=True)
        def apiv1_gateway_get(webinterface, request, session):
            session.has_access('gateway', '*', 'view', raise_error=True)
            return return_good(request, payload=webinterface._Gateways.full_list_gateways())

        @webapp.route('/gateway/<string:gateway_id>', methods=['GET'])
        @require_auth(api=True)
        def apiv1_gateway_details_get(webinterface, request, session, gateway_id):
            session.has_access('gateway', gateway_id, 'view', raise_error=True)
            if len(gateway_id) > 50 or isinstance(gateway_id, str) is False:
                return return_error(request, 'invalid gateway_id format', 400)

            if gateway_id in webinterface._Gateways:
                gateway = webinterface._Gateways[gateway_id]
            return return_good(request, payload=gateway.asdict())
