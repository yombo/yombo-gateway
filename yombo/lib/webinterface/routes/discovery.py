# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/discovery" sub-route of the web interface.

Shows available discovered devices by the system. Allows the user to create a matching Yombo device so that it
can be managed.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/routes/discovery.py>`_
"""

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.discovery")


def route_discovery(webapp):
    with webapp.subroute("/discovery") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/discovery/index", "Discovery")

        @webapp.route('/')
        @require_auth()
        def page_discovery(webinterface, request, session):
            session.has_access('device', '*', 'view')
            return webinterface.redirect(request, '/discovery/index')

        @webapp.route('/index')
        @require_auth()
        def page_discovery_index(webinterface, request, session):
            session.has_access('device', '*', 'view')
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/discovery/index.html')
            root_breadcrumb(webinterface, request)
            return page.render(
                alerts=webinterface.get_alerts(),
                discovery=webinterface._Discovery.discovered,
            )

        @webapp.route('/<string:device_id>/details')
        @require_auth()
        def page_discovery_details(webinterface, request, session, device_id):
            session.has_access('device', device_id, 'view')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/discovery/details/%s" % device_id, "Device Details")
            discovered_device = webinterface._Discovery[device_id]
            yombo_device = discovered_device.yombo_device
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/discovery/details.html')
            return page.render(
                alerts=webinterface.get_alerts(),
                discovered_device=discovered_device,
                yombo_device=yombo_device,
            )
