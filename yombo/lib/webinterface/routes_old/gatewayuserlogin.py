# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/auth/gateway_user_token" sub-route of the web interface.

More or less a knock off of oauth2.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.25.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.route_calllater")

def route_gatewayuserlogin(webapp):
    with webapp.subroute("/auth") as webapp:
        @webapp.route("/gateway_user_token")
        @require_auth()
        @inlineCallbacks
        def page_gatewayuserlogin_gateway_user_token(webinterface, request, session):
            if "token" in request.args:
                json_output = request.args.get("json_output", [{}])[0]

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/calllater/index.html")
            webinterface._Events.save_event_queue_loop.reset()
            yield webinterface._Events.save_event_queue()
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/calllater/index", "Tasks")
            return page.render(
                alerts=webinterface.get_alerts(),
                event_types=webinterface._Events.event_types,
                )
