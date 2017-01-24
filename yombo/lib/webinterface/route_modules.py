try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json


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

        @webapp.route('/server_index')
        @require_auth()
        def page_modules_server_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/server_index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )
        @webapp.route('/server_details/<string:module_id>')
        @require_auth()
        @inlineCallbacks
        def page_modules_details_from_server(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/details_server.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    server_module=results['data'],
                                    modules=webinterface._Modules._modulesByUUID,
                                    ))

        @webapp.route('/add/<string:module_id>')
        @require_auth()
        @inlineCallbacks
        def page_modules_add(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/add.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    server_module=results['data'],
                                    modules=webinterface._Modules,
                                    ))

        @webapp.route('/edit/<string:module_id>', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_modules_edit_get(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules.get(module_id)
                # module = webinterface._Modules[module_id]
            except Exception, e:
                print "Module find errr: %s" % e
                webinterface.add_alert('Module ID was not found.', 'warning')
                returnValue(webinterface.redirect(request, '/modules/index'))

            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            # print "results: %s " % results
            print "module: %s " % module._ModuleVariables
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/edit.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    server_module=results['data'],
                                    module=module,
                                    ))

        @webapp.route('/edit/<string:module_id>', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_modules_edit_post(webinterface, request, session, module_id):
            module = webinterface._Modules.get(module_id)
            try:
                module = webinterface._Modules[module_id]
            except Exception, e:
                print "Module find errr: %s" % e
                webinterface.add_alert('Module ID was not found.', 'warning')
                returnValue(webinterface.redirect(request, '/modules/index'))

            json_output = json.loads(request.args.get('json_output')[0])

            data = {
                'module_id': json_output['module_id'],
                'install_branch': json_output['install_branch'],
                'variable_data': json_output['vars'],
            }

            results = yield module._Details.edit_module(data)
            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')

                results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/edit.html')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                        server_module=results['data'],
                                        module=module,
                                        ))

            webinterface.add_alert("Module configuratiuon updated. A restart is required to take affect.", 'warning')
            returnValue(webinterface.redirect(request, '/modules/index'))

        @webapp.route('/details/<string:module_id>')
        @require_auth()
        def page_modules_details(webinterface, request, session, module_id):
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/details.html')
            return page.render(alerts=webinterface.get_alerts(),
                               module=webinterface._Modules[module_id],
                               variables=webinterface._Modules[module_id]._ModuleVariables,
                               )

        @webapp.route('/edit/<string:module_id>')
        @require_auth()
        def page_modules_edit(webinterface, request, session, module_id):
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/edit.html')
            return page.render(alerts=webinterface.get_alerts(),
                               module=webinterface._Modules[module_id],
                               variables=webinterface._Modules[module_id]._ModuleVariables,
                               )
