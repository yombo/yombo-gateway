# Import python libraries
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from time import time

from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found, return_error, return_unauthorized
from yombo.utils import epoch_to_string, bytes_to_unicode

def route_api_v1_module(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route('/module', methods=['GET'])
        @require_auth(api=True)
        @inlineCallbacks
        def apiv1_module_get(webinterface, request, session):
            session.has_access('module:*', 'view', raise_error=True)
            modules = yield webinterface._Modules.full_list_modules()
            return return_good(request, payload=modules)
