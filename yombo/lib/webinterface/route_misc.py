# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth

def route_misc(webapp):
    with webapp.subroute("/") as webapp:
        @webapp.route('/info')
        @require_auth()
        def page_lib_webinterface_misc_info_get(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/misc/info.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/info", "Information")
            return page.render(alerts=webinterface.get_alerts(),
                               states=webinterface._States.get_states(),
                               )
