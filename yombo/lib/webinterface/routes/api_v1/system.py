# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found, return_error, return_unauthorized
from yombo.utils import epoch_to_string, bytes_to_unicode, random_string

def route_api_v1_system(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route('/tools/awake')
        def apiv1_system_tools_awake(webinterface, request):
            request.setHeader("Access-Control-Allow-Origin", '*');
            return 1

        @webapp.route('/tools/ping')
        @require_auth(api=True)
        def apiv1_system_tools_ping(webinterface, request):
            try:
                request_id = request.args.get('id')[0]
            except Exception as e:
                request_id = random_string(length=12)

            return return_good(request,
                               payload={'id': request_id,
                                        'time': float(time()),
                                        }
                               )

        @webapp.route('/tools/uptime')
        @require_auth(api=True)
        def apiv1_system_tools_uptime(webinterface, request, session):
            if webinterface.starting == True:
                return return_error(request, payload='Not ready yet.')
            try:
                request_id = str(request.args.get('timeonly')[0])
                if request_id == '1':
                    return str(webinterface._Atoms['running_since'])
            except Exception as e:
                pass

            try:
                request_id = request.args.get('id')[0]
            except Exception as e:
                request_id = random_string(length=12)

            return return_good(request,
                               payload={'id': request_id,
                                        'time': str(webinterface._Atoms['running_since']),
                                        }
                               )
