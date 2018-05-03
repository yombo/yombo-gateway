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

# from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
# from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth
from yombo.core.log import get_logger
# from yombo.utils import random_string

logger = get_logger("library.webinterface.route_devices")

def route_panel(webapp):
    with webapp.subroute("/panel") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_panel(webinterface, request, session):
            return webinterface.redirect(request, '/panel/index')

        @webapp.route('/index')
        @require_auth()
        def page_panel_index(webinterface, request, session):
            print(request.requestHeaders)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/panel/index.html')
            return page.render(
                alerts=webinterface.get_alerts(),
                )
