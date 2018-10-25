# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/webinterface_logs" sub-route of the web interface.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.22.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/route_devices.py>`_
"""
# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.route_devices")

def route_webinterface_logs(webapp):
    with webapp.subroute("/webinterface_logs") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_webinterface_logs(webinterface, request, session):
            session.has_access('weblogs', '*', 'view', raise_error=True)
            return webinterface.redirect(request, '/webinterface_logs/index')

        @webapp.route('/index')
        @require_auth()
        def page_webinterface_logs_index(webinterface, request, session):
            session.has_access('weblogs', '*', 'view', raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/webinterface_logs/index.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/webinterface_logs/index", "Webinterface Logs")
            return page.render(
                alerts=webinterface.get_alerts(),
                )
