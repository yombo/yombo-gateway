from yombo.lib.webinterface.auth import require_auth

def route_system(webapp):
    with webapp.subroute("/system") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_modules(webinterface, request, session):
            return webinterface.redirect(request, '/system/index')

        @webapp.route('/index')
        @require_auth()
        def page_system_index(webinterface, request, session):
            gwid = webinterface.gateway_id()
            page = webinterface.get_template(request, webinterface._dir + 'pages/system/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               gwid=gwid(),
                              )

        @webapp.route('/control')
        @require_auth()
        def page_system_control(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/system/control.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/control/restart')
        @require_auth()
        def page_system_control_restart(webinterface, request, session):
            return webinterface.restart(request)

        @webapp.route('/control/shutdown')
        @require_auth()
        def page_system_control_shutdown(webinterface, request, session):
            return webinterface.shutdown(request)

