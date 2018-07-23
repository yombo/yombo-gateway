# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/panel" sub-route of the web interface.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2017 by Yombo.
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

def route_panel(webapp):
    with webapp.subroute("/panel") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_panel(webinterface, request, session):
            session.has_access('panel:*', 'view', raise_error=True)
            return webinterface.redirect(request, '/panel/index')

        @webapp.route('/index')
        @require_auth()
        def page_panel_index(webinterface, request, session):
            session.has_access('panel:*', 'view', raise_error=True)
            master_gateway_id = webinterface._Configs.get('core', 'master_gateway', None, False)
            if master_gateway_id is None:
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/panel/no_master_gateway.html')
                master_gateway = None
            else:
                master_gateway = webinterface._Gateways[master_gateway_id]
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/panel/index.html')

            return page.render(
                alerts=webinterface.get_alerts(),
                session=session,
                master_gateway=master_gateway,
                )
