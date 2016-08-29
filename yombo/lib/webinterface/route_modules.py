from yombo.lib.webinterface.auth import require_auth_pin, require_auth

def route_modules(webapp):
    with webapp.subroute("/modules") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_modules(webinterface, request, session):
            return webinterface.redirect(request, '/modules/index')

        @webapp.route('/index')
        @require_auth()
        def page_modules_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               modules=webinterface._Libraries['modules']._modulesByUUID,
                               )
