# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/events" sub-route of the web interface.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.22.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/route_devices.py>`_
"""
# from collections import OrderedDict
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.route_devices")

def route_events(webapp):
    with webapp.subroute("/events") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_events(webinterface, request, session):
            session.has_access('events', '*', 'view', raise_error=True)
            return webinterface.redirect(request, '/events/index')

        @webapp.route('/index')
        @require_auth()
        def page_events_index(webinterface, request, session):
            session.has_access('events', '*', 'view', raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/events/index.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/events/index", "Events")
            return page.render(
                alerts=webinterface.get_alerts(),
                event_types=webinterface._Events.event_types,
                )

        # see webinterface/routes/api_v1/events.py for API portion.
        @webapp.route('/index_bottom/<string:event_type>/<string:event_subtype>')
        @require_auth()
        def page_events_index_bottom(webinterface, request, session, event_type, event_subtype):
            session.has_access('events', '*', 'view', raise_error=True)
            event_types = webinterface._Events.event_types
            if (event_type in event_types and event_subtype in event_types[event_type]) is False:
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/events/index_bottom_invalid.html')
                return page.render(message="Invalid event type and subtype selected.")

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/events/index_bottom.html')
            return page.render(
                alerts=webinterface.get_alerts(),
                event_types=webinterface._Events.event_types,
                event_type=event_type,
                event_subtype=event_subtype,
                description=event_types[event_type][event_subtype]['description'],
                attributes=event_types[event_type][event_subtype]['attributes'],
                )