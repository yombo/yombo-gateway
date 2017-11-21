from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.lib.webinterface.auth import require_auth

def route_devtools_config_modules(webapp):
    with webapp.subroute("/devtools") as webapp:

        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/devtools/config/", "Config Tools")

        @webapp.route('/config/modules/index')
        @require_auth()
        def page_devtools_modules_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/modules/index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/config/modules/<string:module_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_details_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET',
                                                                  '/v1/module/%s?_expand=device_types' % module_id)
            if module_results['code'] > 299:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/modules/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % module_id,
                                        module_results['data']['label'])
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    module=module_results['data'],
                                    )
                        )

        @webapp.route('/config/modules/<string:module_id>/delete', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_delete_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] > 299:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/modules/delete.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % module_id,
                                        module_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/delete" % module_id, "Delete")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    module=module_results['data'],
                                    )
                        )

        @webapp.route('/config/modules/<string:module_id>/delete', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_delete_post(webinterface, request, session, module_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the module.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            module_results = yield webinterface._Modules.dev_module_delete(module_id)

            if module_results['status'] == 'failed':
                webinterface.add_alert(module_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            msg = {
                'header': 'Module Deleted',
                'label': 'Module deleted successfully',
                'description': '<p>The module has been deleted.</p><p>Continue to <a href="/devtools/config/modules/index">modules index</a> or <a href="/devtools/config/modules/%s/details">view the module</a>.</p>' % module_id,
            }

            module_api_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if module_api_results['code'] <= 299:
                webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules")
                webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % module_id,
                                            module_api_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/delete" % module_id, "Delete")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/modules/<string:module_id>/disable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_disable_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] > 299:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/modules/disable.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    module=module_results['data'],
                                    )
                        )

        @webapp.route('/config/modules/<string:module_id>/disable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_disable_post(webinterface, request, session, module_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the module.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            results = yield webinterface._Modules.dev_module_disable(module_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            msg = {
                'header': 'Module Disabled',
                'label': 'Module disabled successfully',
                'description': '<p>The module has been disabled.</p><p>Continue to <a href="/devtools/config/modules/index">modules index</a> or <a href="/devtools/config/modules/%s/details">view the module</a>.</p>' % module_id,
            }

            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            if module_results['code'] <= 299:
                webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % module_id,
                                            module_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/disable" % module_id, "Disable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/modules/<string:module_id>/enable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_enable_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] > 299:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/modules/enable.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    module=module_results['data'],
                                    )
                        )

        @webapp.route('/config/modules/<string:module_id>/enable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_enable_post(webinterface, request, session, module_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the module.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            results = yield webinterface._Modules.dev_module_enable(module_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            msg = {
                'header': 'Module Enabled',
                'label': 'Module enabled successfully',
                'description': '<p>The module has been enabled.</p><p>Continue to <a href="/devtools/config/modules/index">modules index</a> or <a href="/devtools/config/modules/%s/details">view the module</a>.</p>' % module_id,
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/modules/add', methods=['GET'])
        @require_auth()
        def page_devtools_modules_add_get(webinterface, request, session):
            data = {
                'module_type': webinterface.request_get_default(request, 'module_type', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'short_description': webinterface.request_get_default(request, 'short_description', ""),
                'description_formatting': webinterface.request_get_default(request, 'description_formatting', ""),
                'repository_link': webinterface.request_get_default(request, 'repository_link', ""),
                'issue_tracker_link': webinterface.request_get_default(request, 'issue_tracker_link', ""),
                'doc_link': webinterface.request_get_default(request, 'doc_link', ""),
                'git_link': webinterface.request_get_default(request, 'git_link', ""),
                'prod_branch': webinterface.request_get_default(request, 'prod_branch', ""),
                'dev_branch': webinterface.request_get_default(request, 'dev_branch', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'public': int(webinterface.request_get_default(request, 'public', 0)),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/config/modules/add", "Add Module")
            return page_devtools_modules_form(webinterface, request, session, data, "add", "Add Module")

        @webapp.route('/config/modules/add', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_add_post(webinterface, request, session):
            data = {
                'module_type': request.args.get('module_type')[0],
                'label': request.args.get('label')[0],
                'machine_label': request.args.get('machine_label')[0],
                'description': request.args.get('description')[0],
                'short_description': request.args.get('short_description')[0],
                'description_formatting': request.args.get('description_formatting')[0],
                'repository_link': request.args.get('repository_link')[0],
                'issue_tracker_link': request.args.get('issue_tracker_link')[0],
                'doc_link': request.args.get('doc_link')[0],
                'git_link': request.args.get('git_link')[0],
                'prod_branch': request.args.get('prod_branch')[0],
                'dev_branch': request.args.get('dev_branch')[0],
                'public': int(request.args.get('public')[0]),
                'status': int(request.args.get('status')[0]),
            }

            results = yield webinterface._Modules.dev_module_add(data)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(page_devtools_modules_form(webinterface, request, session, data, "add", "Add Module"))

            msg = {
                'header': 'Module Added',
                'label': 'Module added successfully',
                'description': '<p>The module has been added. If you have requested this module to be made public, please allow a few days for Yombo to perform a code review of your repository.</p><p>Continue to <a href="/devtools/config/modules/index">modules index</a></p>',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/config/modules/add", "Add Module")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/modules/<string:module_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_edit_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] > 299:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % module_id,
                                        module_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/edit" % module_id, "Edit")

            returnValue(page_devtools_modules_form(webinterface, request, session, module_results['data'], "edit",
                                                   "Edit Module: %s" % module_results['data']['label']))

        @webapp.route('/config/modules/<string:module_id>/edit', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_edit_post(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if results['code'] > 299:
                webinterface.add_alert(results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))

            data = {
                # 'module_type': request.args.get('module_type')[0],
                'label': request.args.get('label')[0],
                # 'machine_label': request.args.get('machine_label')[0],
                'description': request.args.get('description')[0],
                'short_description': request.args.get('short_description')[0],
                'description_formatting': request.args.get('description_formatting')[0],
                'repository_link': request.args.get('repository_link')[0],
                'issue_tracker_link': request.args.get('issue_tracker_link')[0],
                'doc_link': request.args.get('doc_link')[0],
                'git_link': request.args.get('git_link')[0],
                'prod_branch': request.args.get('prod_branch')[0],
                'dev_branch': request.args.get('dev_branch')[0],
                #                'variable_data': json_output['vars'],
                'public': int(request.args.get('public')[0]),
                'status': int(request.args.get('status')[0]),
            }

            results = yield webinterface._Modules.dev_module_edit(module_id, data)

            data['module_type'] = request.args.get('module_type')[0]
            data['machine_label'] = request.args.get('machine_label')[0]

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(page_devtools_modules_form(webinterface, request, session, data, "edit",
                                                       "Edit Module: %s" % data['label']))

            msg = {
                'header': 'Module Updated',
                'label': 'Module updated successfully',
                'description': '<p>The module has been updated. If you have requested this module to be made public, please allow a few days for Yombo to perform a code review of your repository.</p><p>Continue to <a href="/devtools/config/modules/index">modules index</a></p>',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        def page_devtools_modules_form(webinterface, request, session, module, display_type, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/modules/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               module=module,
                               display_type=display_type
                               )

        @webapp.route('/config/modules/<string:module_id>/device_types/index', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_device_types_index_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] > 299:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/modules/devicetype_index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % module_id,
                                        module_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % module_id,
                                        "Associate Device Type")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    module=module_results['content']['response']['module'],
                                    )
                        )

        @webapp.route('/config/modules/<string:module_id>/device_types/<string:device_type_id>/add', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_device_types_add_get(webinterface, request, session, module_id, device_type_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] > 299:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] > 299:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/modules/devicetype_add.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % module_id,
                                        module_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % module_id,
                                        "Associate Device Type")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    module=module_results['data'],
                                    device_type=device_type_results['data'],
                                    )
                        )

        @webapp.route('/config/modules/<string:module_id>/device_types/<string:device_type_id>/add', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_device_types_add_post(webinterface, request, session, module_id, device_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/device_types/%s/add' % (
                    module_id, device_type_id)))

            if confirm != "add":
                webinterface.add_alert('Must enter "add" in the confirmation box to add device type to module.',
                                       'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            results = yield webinterface._Modules.dev_module_device_type_add(module_id, device_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            webinterface.add_alert("Device Type added to module.", 'warning')
            returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

        @webapp.route('/config/modules/<string:module_id>/device_types/<string:device_type_id>/remove', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_device_types_remove_get(webinterface, request, session, module_id, device_type_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] > 299:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] > 299:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/modules/devicetype_remove.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % module_id,
                                        module_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % module_id,
                                        "Remove Device Type")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    module=module_results['data'],
                                    device_type=device_type_results['data'],
                                    )
                        )

        @webapp.route('/config/modules/<string:module_id>/device_types/<string:device_type_id>/remove',
                      methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_device_types_remove_post(webinterface, request, session, module_id, device_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/device_types/%s/add' % (
                    module_id, device_type_id)))

            if confirm != "remove":
                webinterface.add_alert('Must enter "remove" in the confirmation box to remove device type from module.',
                                       'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            results = yield webinterface._Modules.dev_module_device_type_remove(module_id, device_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

            webinterface.add_alert("Device Type removed from module.", 'warning')
            returnValue(webinterface.redirect(request, '/devtools/config/modules/%s/details' % module_id))

        @webapp.route('/config/modules/<string:module_id>/variables', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_variables_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] > 299:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/modules/variable_details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % module_id,
                                        module_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/variables" % module_id, "Variables")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    module=module_results['data'],
                                    )
                        )
