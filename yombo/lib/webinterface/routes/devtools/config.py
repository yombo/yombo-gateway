from yombo.lib.webinterface.auth import require_auth

def route_devtools_config(webapp):
    with webapp.subroute("/devtools") as webapp:

        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/devtools/config/", "Config Tools")

        @webapp.route('/config/')
        @require_auth()
        def page_devtools(webinterface, request, session):
            return webinterface.redirect(request, '/devtools/config/index')

        @webapp.route('/config/index')
        @require_auth()
        def page_devtools_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devtools/config/index.html')
            root_breadcrumb(webinterface, request)
            return page.render(alerts=webinterface.get_alerts(),
                               )
