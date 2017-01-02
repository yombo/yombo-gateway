from yombo.lib.webinterface.auth import require_auth_pin, require_auth
from twisted.internet.defer import inlineCallbacks, returnValue

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

        @webapp.route('/add_index')
        @require_auth()
        def page_modules_add_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/add.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )
        @webapp.route('/server_details/<string:module_id>')
        @require_auth()
        @inlineCallbacks
        def page_modules_details_from_server(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/details_server.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                               module=results['data']))

        @webapp.route('/details/<string:module_id>')
        @require_auth()
        def page_modules_details(webinterface, request, session, module_id):
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/details.html')
            return page.render(alerts=webinterface.get_alerts(),
                               module=webinterface._Modules[module_id]._Class,
                               variables=webinterface._Modules[module_id]._ModuleVariables,
                               )

        @webapp.route('/edit/<string:module_id>')
        @require_auth()
        def page_modules_edit(webinterface, request, session, module_id):
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/edit.html')
            return page.render(alerts=webinterface.get_alerts(),
                               module=webinterface._Modules[module_id]._Class,
                               variables=webinterface._Modules[module_id]._ModuleVariables,
                               )
