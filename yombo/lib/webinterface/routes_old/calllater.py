# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/calllater" sub-route of the web interface.

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

def route_calllater(webapp):
    with webapp.subroute("/calllater") as webapp:
        @webapp.route("/")
        @require_auth()
        def page_calllater(webinterface, request, session):
            session.has_access("calllater", "*", "view", raise_error=True)
            return webinterface.redirect(request, "/calllater/index")

        @webapp.route("/index")
        @require_auth()
        @inlineCallbacks
        def page_calllater_index(webinterface, request, session):
            session.has_access("calllater", "*", "view", raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/calllater/index.html")
            webinterface._Events.save_event_queue_loop.reset()
            yield webinterface._Events.save_event_queue()
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/calllater/index", "Tasks")
            return page.render(
                alerts=webinterface.get_alerts(),
                event_types=webinterface._Events.event_types,
                )
