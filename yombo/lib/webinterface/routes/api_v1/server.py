"""
Handles items for the basic/static webinterface, NOT for the frontend.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018-2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/cache.html>`_
"""

# Import python libraries
import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_error
from yombo.constants import CONTENT_TYPE_JSON

def route_api_v1_server(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/server/dns/check_available/<string:dnsname>", methods=["GET"])
        @require_auth(api=True)
        @inlineCallbacks
        def apiv1_server_dns_check_available(webinterface, request, session, dnsname):
            url = f"/v1/dns_domains/check_available/{dnsname}"
            auth_header = yield session.authorization_header()
            try:
                response = yield webinterface._YomboAPI.request("GET", url, authorization_header=auth_header)
            except YomboWarning as e:
                return return_error(request, e.message, e.errorno)

            return webinterface.render_api_raw(request, session,
                                           data=response.content["data"]
                                           )
