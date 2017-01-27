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

        @webapp.route('/add/<string:module_id>', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_modules_add(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/add.html')
            data = {
                'module_id': results['data']['id'],
                'install_branch': results['data']['prod_branch'],
                'variable_data': {},
            }
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    server_module=results['data'],
                                    module_data={},
                                    ))

        @webapp.route('/add/<string:module_id>', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_modules_add_post(webinterface, request, session, module_id):
            json_output = json.loads(request.args.get('json_output')[0])

            data = {
                'module_id': json_output['module_id'],
                'install_branch': json_output['install_branch'],
            }
            if 'vars' in json_output:
                json_output['variable_data'] = json_output['vars']

            results = yield webinterface._Modules.add_module(data)
            if results['status'] == 'failed':
                print "failed to submit new module: %s" % results
                webinterface.add_alert(results['apimsghtml'], 'warning')

                results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/add.html')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                        server_module=results['data'],
                                        module_data=data,
                                        ))

            msg = {
                'header': 'Module Added',
                'label': 'Module configuration updated successfully',
                'description': '',
            }

            webinterface._Notifications.add({'title': 'Restart Required',
                                             'message': 'Module added. A system <strong><a  class="confirm-restart" href="#" title="Restart Yombo Gateway">restart is required</a></strong> to take affect.',
                                             'source': 'Web Interface',
                                             'persist': False,
                                             'priority': 'high',
                                             'always_show': True,
                                             'always_show_allow_clear': False,
                                             'id': 'reboot_required',
                                             })

            page = webinterface.get_template(request, webinterface._dir + 'pages/reboot_needed.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

            webinterface.add_alert("Module configuratiuon updated. A restart is required to take affect.", 'warning')
            returnValue(webinterface.redirect(request, '/modules/index'))

        @webapp.route('/disable/<string:module_id>', methods=['GET'])
        @require_auth()
        def page_modules_disable_get(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules.get(module_id)
                # module = webinterface._Modules[module_id]
            except Exception, e:
                print "Module find errr: %s" % e
                webinterface.add_alert('Module ID was not found.', 'warning')
                return webinterface.redirect(request, '/modules/index')

            # print "module: %s " % module._ModuleVariables
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/disable.html')
            return page.render(alerts=webinterface.get_alerts(),
                                    module=module,
                                    )

        @webapp.route('/disable/<string:module_id>', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_modules_disable_post(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules[module_id]
            except Exception, e:
                print "Module find errr: %s" % e
                webinterface.add_alert('Module ID was not found.', 'warning')
                returnValue(webinterface.redirect(request, '/modules/index'))

            confirm = request.args.get('confirm')[0]
            if confirm != "disable":
                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/disable.html')
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the module.', 'warning')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        ))

            results = yield webinterface._Modules.disable_module(module._Details.module_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')

                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/disable.html')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        ))

            msg = {
                'header': 'Module Disabled',
                'label': 'Module configuration updated successfully',
                'description': '',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/reboot_needed.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/enable/<string:module_id>', methods=['GET'])
        @require_auth()
        def page_modules_enable_get(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules.get(module_id)
                # module = webinterface._Modules[module_id]
            except Exception, e:
                print "Module find errr: %s" % e
                webinterface.add_alert('Module ID was not found.', 'warning')
                return webinterface.redirect(request, '/modules/index')

            # print "module: %s " % module._ModuleVariables
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/enable.html')
            return page.render(alerts=webinterface.get_alerts(),
                               module=module,
                               )

        @webapp.route('/enable/<string:module_id>', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_modules_enable_post(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules[module_id]
            except Exception, e:
                print "Module find errr: %s" % e
                webinterface.add_alert('Module ID was not found.', 'warning')
                returnValue(webinterface.redirect(request, '/modules/index'))

            confirm = request.args.get('confirm')[0]
            if confirm != "enable":
                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/enable.html')
                webinterface.add_alert('Must enter "disable" in the confirmation box to enable the module.', 'warning')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        ))

            results = yield webinterface._Modules.enable_module(module._Details.module_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')

                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/enable.html')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        ))

            msg = {
                'header': 'Module Enabled',
                'label': 'Module configuration updated successfully',
                'description': '',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/reboot_needed.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/remove/<string:module_id>', methods=['GET'])
        @require_auth()
        def page_modules_remove_get(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules.get(module_id)
                # module = webinterface._Modules[module_id]
            except Exception, e:
                print "Module find errr: %s" % e
                webinterface.add_alert('Module ID was not found.', 'warning')
                return webinterface.redirect(request, '/modules/index')

            # print "module: %s " % module._ModuleVariables
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/remove.html')
            return page.render(alerts=webinterface.get_alerts(),
                               module=module,
                               )


        @webapp.route('/remove/<string:module_id>', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_modules_remove_post(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules[module_id]
            except Exception, e:
                print "Module find errr: %s" % e
                webinterface.add_alert('Module ID was not found.', 'warning')
                returnValue(webinterface.redirect(request, '/modules/index'))

            confirm = request.args.get('confirm')[0]
            if confirm != "remove":
                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/remove.html')
                webinterface.add_alert('Must enter "disable" in the confirmation box to remove the module.', 'warning')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        ))

            results = yield webinterface._Modules.remove_module(module._Details.module_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')

                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/remove.html')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        ))

            msg = {
                'header': 'Module Enabled',
                'label': 'Module configuration updated successfully',
                'description': '',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/reboot_needed.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
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

            results = yield module._Details.edit_module(module_id, data)
            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')

                results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/edit.html')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                        server_module=results['data'],
                                        module=module,
                                        ))

            msg = {
                'header': 'Module Updated',
                'label': 'Module configuration updated successfully',
                'description': '',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/reboot_needed.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

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
