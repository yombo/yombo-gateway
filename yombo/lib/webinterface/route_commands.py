from yombo.lib.webinterface.auth import require_auth_pin, require_auth

def route_commands(webapp):
    with webapp.subroute("/commands") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_commands(webinterface, request, session):
            return webinterface.redirect(request, '/commands/index')

        @webapp.route('/index')
        @require_auth()
        def page_commands_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/commands/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )
