# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found, return_error, return_unauthorized
from yombo.utils import epoch_to_string, bytes_to_unicode

def route_api_v1_system(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route('/ping')
        def apiv1_system_ping(webinterface, request):
            if webinterface.starting == True:
                return;
            request.setHeader("Access-Control-Allow-Origin", '*');
            return "y-pong-01"

        @webapp.route('/uptime')
        @require_auth(api=True)
        def apiv1_system_uptime(webinterface, request, session):
            if webinterface.starting == True:
                return;
            return str(webinterface._Atoms['running_since'])
