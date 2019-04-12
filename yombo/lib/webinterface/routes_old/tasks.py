# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/tasks" sub-route of the web interface.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.25.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.route_tasks")

def route_tasks(webapp):
    with webapp.subroute("/tasks") as webapp:
        @webapp.route("/")
        @require_auth()
        def page_tasks(webinterface, request, session):
            session.has_access("tasks", "*", "view", raise_error=True)
            return webinterface.redirect(request, "/tasks/index")

        @webapp.route("/index")
        @require_auth()
        @inlineCallbacks
        def page_tasks_index(webinterface, request, session):
            session.has_access("tasks", "*", "view", raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/tasks/index.html")
            webinterface._Events.save_event_queue_loop.reset()
            yield webinterface._Events.save_event_queue()
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/tasks/index", "Tasks")
            return page.render(
                alerts=webinterface.get_alerts(),
                event_types=webinterface._Events.event_types,
                )
