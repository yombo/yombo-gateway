from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth_pin, require_auth

def route_devtools(webapp):
    with webapp.subroute("/devtools") as webapp:
        @webapp.route('/')
        @require_auth_pin()
        def page_devtools(webinterface, request):
            return webinterface.redirect(request, '/devtools/index')

        @webapp.route('/index')
        @require_auth()
        def page_devtools_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/commands/public')
        @require_auth()
        def page_devtools_commands_public(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/commands_list.html')
            return page.render(alerts=webinterface.get_alerts(),
                               commands=webinterface._Commands.get_public_commands(),
                               page_label='Public Commands',
                               page_description='Publicly available commands.'
                               )

        @webapp.route('/commands/local')
        @require_auth()
        def page_devtools_commands_local(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/commands_list.html')
            return page.render(alerts=webinterface.get_alerts(),
                               commands=webinterface._Commands.get_local_commands(),
                               page_label='Local Commands',
                               page_description='Local commands, only available to the primary account holder.'
                               )

        @webapp.route('/commands/edit/<string:command_id>')
        @require_auth()
        def page_devtools_command_details(webinterface, request, session, command_id):
            try:
                command = webinterface._Commands[command_id]
            except:
                webinterface.add_alert('Command ID was not found.', 'warning')
                return webinterface.redirect(request, '/devtools/command/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/command_edit.html')
            return page.render(alerts=webinterface.get_alerts(),
                               command=command,
                               input_types=webinterface._InputTypes.get_all()
                               )

        @webapp.route('/debug')
        @require_auth()
        def page_devtools_debug(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )
        @webapp.route('/debug/hooks_called_libraries')
        @require_auth()
        def page_devtools_debug_hooks_called_libraries(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/hooks_called_libraries.html')
            return page.render(alerts=webinterface.get_alerts(),
                               hooks_called=webinterface._Loader.hook_counts
                               )

        @webapp.route('/debug/hooks_called_modules')
        @require_auth()
        def page_devtools_debug_hooks_called_modules(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/hooks_called_modules.html')
            return page.render(alerts=webinterface.get_alerts(),
                               hooks_called=webinterface._Modules.hook_counts
                               )

        @webapp.route('/debug/statistic_bucket_lifetimes')
        @require_auth()
        def page_devtools_debug_statistic_bucket_lifetimes(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/statistic_bucket_lifetimes.html')
            return page.render(alerts=webinterface.get_alerts(),
                               bucket_lifetimes=webinterface._Statistics.bucket_lifetimes
                               )

        @webapp.route('/devicetypes/public')
        @require_auth()
        def page_devtools_devicetypes_public(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/devicetypes_list.html')
            return page.render(alerts=webinterface.get_alerts(),
                               items=webinterface._DeviceTypes.get_public_devicetypes(),
                               page_label='Public Device Types',
                               page_description='Publicly available device types.'
                               )

        @webapp.route('/devicetypes/local')
        @require_auth()
        def page_devtools_devicetypes_local(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/devicetypes_list.html')
            return page.render(alerts=webinterface.get_alerts(),
                               items=webinterface._DeviceTypes.get_local_devicetypes(),
                               page_label='Local Device  Types',
                               page_description='Local device types, only available to the primary account holder.'
                               )

        @webapp.route('/devicetypes/details/<string:devicetype_id>')
        @require_auth()
        def page_devtools_devicetypes_details(webinterface, request, session, devicetype_id):
            try:
                devicetype = webinterface._DeviceTypes[devicetype_id]
            except YomboWarning:
                webinterface.add_alert('Device Type ID was not found: %s' % devicetype_id, 'warning')
                return webinterface.redirect(request, '/devtools/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/devicetype_details.html')
            return page.render(alerts=webinterface.get_alerts(),
                               devicetype=devicetype,
                               input_types=webinterface._InputTypes.get_all()
                               )

        @webapp.route('/devicetypes/edit/<string:device_id>')
        @require_auth()
        def page_devtools_devicetypes_edit(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices[device_id]
            except:
                webinterface.add_alert('Device Type ID was not found.', 'warning')
                return webinterface.redirect(request, '/devtools/devicetypes/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/devicetype_edit.html')
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               input_types=webinterface._InputTypes.get_all()
                               )

        @webapp.route('/modules/index')
        @require_auth()
        def page_devtools_modules_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/modules/add', methods=['GET'])
        @require_auth()
        def page_devtools_modules_add_get(webinterface, request, session):
            data = {
                'module_type': '',
                'label': '',
                'machine_label': '',
                'description': '',
                'short_description': '',
                'description_formatting': '',
                'repository_link': '',
                'issue_tracker_link': '',
                'doc_link': '',
                'git_link': '',
                'prod_branch': '',
                'dev_branch': '',
                #                'variable_data': json_output['vars'],
                'public': int(0),
                'status': int(1),
            }
            return page_devtools_modules_edit_form(webinterface, request, session, data, "Add New Module")

        # def page_devtools_modules_add_form(webinterface, request, session, module, var_data):
        #     page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/edit.html')
        #     returnValue(page.render(alerts=webinterface.get_alerts(),
        #                        module=module,
        #                        ))

        @webapp.route('/modules/add', methods=['POST'])
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
                #                'variable_data': json_output['vars'],
                'public': int(request.args.get('public')[0]),
                'status': int(request.args.get('status')[0]),
            }

            results = yield webinterface._Modules.dev_add_module(data)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(page_devtools_modules_edit_form(webinterface, request, session, data, None))

            msg = {
                'header': 'Module Added',
                'label': 'Module added successfully',
                'description': 'The module has been added. If you have requested this module to be made public, please allow a few days for Yombo to perform a code review of your repository.',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/modules/details/<string:module_id>', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_details_get(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if results['code'] != 200:
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))
            print "results: %s" % results['data']

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/details.html')
            returnValue( page.render(alerts=webinterface.get_alerts(),
                               module=results['data'],
                               )
                         )

            returnValue(page_devtools_modules_edit_form(webinterface, request, session, results['data'], "Edit Module: %s" % results['data']['label']))

        @webapp.route('/modules/edit/<string:module_id>', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_edit_get(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            print "111111"
            if results['code'] != 200:
                webinterface.add_alert(results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))
            returnValue(page_devtools_modules_edit_form(webinterface, request, session, results['data'], None))

        def page_devtools_modules_edit_form(webinterface, request, session, module, header_label):
            print "aaaaa"
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/edit.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               module=module,
                               )

        @webapp.route('/modules/edit/<string:module_id>', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_edit_post(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if results['code'] != 200:
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))

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

            results = yield webinterface._Modules.dev_edit_module(module_id, data)

            data['module_type'] = request.args.get('module_type')[0];
            data['machine_label'] = request.args.get('machine_label')[0];

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(page_devtools_modules_edit_form(webinterface, request, session, data, "Edit Module: %s" % data['label']))

            msg = {
                'header': 'Module Updated',
                'label': 'Module updated successfully',
                'description': 'The module has been updated. If you have requested this module to be made public, please allow a few days for Yombo to perform a code review of your repository.',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))