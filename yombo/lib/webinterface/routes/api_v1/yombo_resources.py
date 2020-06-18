"""
Handles items for the basic/static webinterface, NOT for the frontend.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/cache.html>`_
"""

# Import python libraries
import json

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import get_session
from yombo.lib.webinterface.routes.api_v1.__init__ import return_error
from yombo.constants import CONTENT_TYPE_JSON


def route_api_v1_yombo_resources(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/yombo/dns/check_available/<string:dnsname>", methods=["GET"])
        @get_session(auth_required=True, api=True)
        @inlineCallbacks
        def apiv1_yombo_resources_dns_check_available(webinterface, request, session, dnsname):
            webinterface._Validate.id_string(dnsname)
            auth_header = yield session.authorization_header(request)
            try:
                response = yield webinterface._YomboAPI.request("GET",
                                                                f"/v1/dns_domains/check_available/{dnsname}",
                                                                authorization_header=auth_header)
            except YomboWarning as e:
                print(f"aaaaaaaaaa = meta = {e.meta}")
                print(f"aaaaaaaaaa = content = {e.meta.content}")
                print(f"aaaaaaaaaa = response_code = {e.meta.response_code}")
                if hasattr(e, "meta") and "errors" in e.meta.content:
                    return return_error(request, e.meta.content["errors"], e.meta.response_code)
                return return_error(request, e.message, e.error_code)

            return webinterface.render_api_raw(request,
                                               data=response.content["data"],
                                               data_type="dns_available",

                                               )
