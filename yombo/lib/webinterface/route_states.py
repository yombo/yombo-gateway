from yombo.lib.webinterface.auth import require_auth_pin, require_auth

def route_states(webapp):
    with webapp.subroute("/states") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_states(webinterface, request, session):
            return webinterface.redirect(request, '/configs/basic')

        @webapp.route('/index')
        @require_auth()
        def page_states_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/states/index.html')
            strings = webinterface._Localize.get_strings(request.getHeader('accept-language'), 'states')
            return page.render(alerts=webinterface.get_alerts(),
                               states=webinterface._Libraries['states'].get_states(),
                               states_i18n=strings,
                               )
