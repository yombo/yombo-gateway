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

####################################
# Command
####################################
        @webapp.route('/commands/index')
        @require_auth()
        def page_devtools_commands_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/commands/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/commands/<string:command_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_details_get(webinterface, request, session, command_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if results['code'] != 200:
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/commands/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/commands/details.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    command=results['data'],
                                    )
                        )

        @webapp.route('/commands/add', methods=['GET'])
        @require_auth()
        def page_devtools_commands_add_get(webinterface, request, session):
            data = {
                'voice_cmd': webinterface.reqest_get_default(request, 'voice_cmd', ""),
                'label': webinterface.reqest_get_default(request, 'label', ""),
                'machine_label': webinterface.reqest_get_default(request, 'machine_label', ""),
                'description': webinterface.reqest_get_default(request, 'description', ""),
                'status': int(webinterface.reqest_get_default(request, 'status', 1)),
                'public': int(webinterface.reqest_get_default(request, 'public', 0)),
            }
            return page_devtools_commands_form(webinterface, request, session, 'add', data,
                                                        "Add Command")

        @webapp.route('/commands/add', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_add_post(webinterface, request, session):
            data = {
                'voice_cmd': webinterface.reqest_get_default(request, 'voice_cmd', ""),
                'label': webinterface.reqest_get_default(request, 'label', ""),
                'machine_label': webinterface.reqest_get_default(request, 'machine_label', ""),
                'description': webinterface.reqest_get_default(request, 'description', ""),
                'status': int(webinterface.reqest_get_default(request, 'status', 1)),
                'public': int(webinterface.reqest_get_default(request, 'public', 0)),
            }

            command_results = yield webinterface._Commands.dev_add_command(data)

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                returnValue(
                    page_devtools_commands_form(webinterface, request, session, 'add', data, "Add Command"))

            msg = {
                'header': 'Command Added',
                'label': 'Command added successfully',
                'description': '<p>The command has been added. If you have requested this command to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/commands/index">command index</a></p>',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/commands/<string:command_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_edit_get(webinterface, request, session, command_id):
            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/commands/index'))

            returnValue(
                page_devtools_commands_form(webinterface, request, session, 'edit', command_results['data'],
                                                "Edit Command: %s" % command_results['data']['label']))

        @webapp.route('/commands/<string:command_id>/edit', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_edit_post(webinterface, request, session, command_id):
            data = {
                'voice_cmd': webinterface.reqest_get_default(request, 'voice_cmd', ""),
                'label': webinterface.reqest_get_default(request, 'label', ""),
                # 'machine_label': webinterface.reqest_get_default(request, 'machine_label', ""),
                'description': webinterface.reqest_get_default(request, 'description', ""),
                'status': int(webinterface.reqest_get_default(request, 'status', 1)),
                'public': int(webinterface.reqest_get_default(request, 'public', 0)),
            }

            command_results = yield webinterface._Commands.dev_edit_command(command_id, data)

            data['machine_label'] = request.args.get('machine_label_hidden')[0];

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                returnValue(page_devtools_commands_form(webinterface, request, session, 'edit', data,
                                                            "Edit Command: %s" % data['label']))

                returnValue(webinterface.redirect(request, '/devtools/commands/index'))

            msg = {
                'header': 'Command Updated',
                'label': 'Command updated successfully',
                'description': '<p>The command has been updated. If you have requested this command to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/commands/index">command index</a></p>',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        def page_devtools_commands_form(webinterface, request, session, action_type, command,
                                            header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/commands/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               command=command,
                               action_type=action_type,
                               )

        @webapp.route('/commands/<string:command_id>/variables', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_variables_get(webinterface, request, session, command_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if results['code'] != 200:
                webinterface.add_alert(results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/commands/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/modules/variable_details.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    module=results['data'],
                                    )
                        )

####################################
# Device Types
####################################
        @webapp.route('/device_types/index')
        @require_auth()
        def page_devtools_device_types_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/device_types/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/device_types/<string:device_type_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_details_get(webinterface, request, session, device_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

            category_results = yield webinterface._YomboAPI.request('GET', '/v1/category/%s' % device_type_results['data']['category_id'])
            if category_results['code'] != 200:
                webinterface.add_alert(category_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/device_types/details.html')
            returnValue( page.render(alerts=webinterface.get_alerts(),
                               device_type=device_type_results['data'],
                               category=category_results['data'],
                               )
                         )

        @webapp.route('/device_types/add', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_add_get(webinterface, request, session):
            category_results = yield webinterface._YomboAPI.request('GET', '/v1/category?category_type=device_type')
            if category_results['code'] != 200:
                webinterface.add_alert(category_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

            data = {
                'category_id': webinterface.reqest_get_default(request, 'category_id', ""),
                'label': webinterface.reqest_get_default(request, 'label', ""),
                'machine_label': webinterface.reqest_get_default(request, 'machine_label', ""),
                'description': webinterface.reqest_get_default(request, 'description', ""),
                'status': int(webinterface.reqest_get_default(request, 'status', 1)),
                'public': int(webinterface.reqest_get_default(request, 'public', 0)),
            }
            returnValue(page_devtools_devicestypes_form(webinterface, request, session, 'add', data, category_results['data'], "Add Device Type"))

        @webapp.route('/device_types/add', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_add_post(webinterface, request, session):
            data = {
                'category_id': webinterface.reqest_get_default(request, 'category_id', ""),
                'label': webinterface.reqest_get_default(request, 'label', ""),
                'machine_label': webinterface.reqest_get_default(request, 'machine_label', ""),
                'description': webinterface.reqest_get_default(request, 'description', ""),
                'status': int(webinterface.reqest_get_default(request, 'status', 1)),
                'public': int(webinterface.reqest_get_default(request, 'public', 0)),
            }

            device_type_results = yield webinterface._DeviceTypes.dev_add_device_type(data)

            if device_type_results['status'] == 'failed':
                webinterface.add_alert(device_type_results['apimsghtml'], 'warning')
                category_results = yield webinterface._YomboAPI.request('GET', '/v1/category?category_type=device_type')
                if category_results['code'] != 200:
                    webinterface.add_alert(category_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/device_types/index'))
                returnValue(
                    page_devtools_devicestypes_form(webinterface, request, session,  'add', data, category_results['data'],
                                                    "Add Device Type"))

            msg = {
                'header': 'Device Type Added',
                'label': 'Device typ added successfully',
                'description': '<p>The device type has been added. If you have requested this device type to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/device_types/index">device types index</a></p>',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/device_types/<string:device_type_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_edit_get(webinterface, request, session, device_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))
            category_results = yield webinterface._YomboAPI.request('GET', '/v1/category?category_type=device_type')
            if category_results['code'] != 200:
                webinterface.add_alert(category_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

            returnValue(page_devtools_devicestypes_form(webinterface, request, session,  'edit', device_type_results['data'], category_results['data'], "Edit Device Type: %s" % device_type_results['data']['label']))

        @webapp.route('/device_types/<string:device_type_id>/edit', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_edit_post(webinterface, request, session, device_type_id):
            data = {
                'category_id': webinterface.reqest_get_default(request, 'category_id', ""),
                'label': webinterface.reqest_get_default(request, 'label', ""),
#                'machine_label': webinterface.reqest_get_default(request, 'machine_label', ""),
                'description': webinterface.reqest_get_default(request, 'description', ""),
                'status': int(webinterface.reqest_get_default(request, 'status', 1)),
                'public': int(webinterface.reqest_get_default(request, 'public', 0)),
            }

            device_type_results = yield webinterface._DeviceTypes.dev_edit_device_type(device_type_id, data)

            data['machine_label'] = request.args.get('machine_label_hidden')[0];

            if device_type_results['status'] == 'failed':
                category_results = yield webinterface._YomboAPI.request('GET', '/v1/category?category_type=device_type')
                if category_results['code'] != 200:
                    webinterface.add_alert(category_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

                webinterface.add_alert(device_type_results['apimsghtml'], 'warning')
                returnValue(page_devtools_devicestypes_form(webinterface, request, session, 'edit', data,
                                                            category_results['data'],
                                                            "Edit Device Type: %s" % data['label']))

                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

            msg = {
                'header': 'Device Type Updated',
                'label': 'Device typ updated successfully',
                'description': '<p>The device type has been updated. If you have requested this device type to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/device_types/index">device types index</a></p>',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        def page_devtools_devicestypes_form(webinterface, request, session, action_type, device_type, categories, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/device_types/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               device_type=device_type,
                               categories=categories,
                               action_type=action_type,
                               )

        @webapp.route('/device_types/<string:device_type_id>/variables', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_variables_get(webinterface, request, session, device_type_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if results['code'] != 200:
                webinterface.add_alert(results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/variable_details.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                               module=results['data'],
                               )
                        )

####################################
# Modules
####################################
        @webapp.route('/modules/index')
        @require_auth()
        def page_devtools_modules_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/modules/<string:module_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_details_get(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if results['code'] != 200:
                webinterface.add_alert(results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/details.html')
            returnValue( page.render(alerts=webinterface.get_alerts(),
                               module=results['data'],
                               )
                         )

        @webapp.route('/modules/<string:module_id>/disable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_disable_get(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if results['code'] != 200:
                webinterface.add_alert(results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/disable.html')
            returnValue( page.render(alerts=webinterface.get_alerts(),
                               module=results['data'],
                               )
                         )

        @webapp.route('/modules/<string:module_id>/disable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_disable_post(webinterface, request, session, module_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/modules/%s/module_id' % module_id))

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the module.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/%s/module_id' % module_id))

            results = yield webinterface._Modules.dev_disable_module(module_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/%s/details' % module_id))

            msg = {
                'header': 'Module Disabled',
                'label': 'Module disabled successfully',
                'description': '<p>The module has been disabled.</p><p>Continue to <a href="/devtools/modules/index">modules index</a> or <a href="/devtools/modules/%s/details" % module_id>view the module</a>.</p>',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

            # ---

        @webapp.route('/modules/<string:module_id>/enable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_enable_get(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if results['code'] != 200:
                webinterface.add_alert(results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/enable.html')
            returnValue( page.render(alerts=webinterface.get_alerts(),
                               module=results['data'],
                               )
                         )

        @webapp.route('/modules/<string:module_id>/enable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_enable_post(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules[module_id]
            except Exception, e:
                print "Module find errr: %s" % e
                webinterface.add_alert('Module ID was not found.', 'warning')
                returnValue(webinterface.redirect(request, '/modules/index'))

            confirm = request.args.get('confirm')[0]
            if confirm != "enable":
                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/enable.html')
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the module.', 'warning')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        ))

            results = yield webinterface._Modules.dev_enable_module(module._Details.module_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')

                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/enable.html')
                returnValue(page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        ))

            msg = {
                'header': 'Module enabled',
                'label': 'Module configuration updated successfully',
                'description': '',
            }

            webinterface._Notifications.add({'title': 'Restart Required',
                                             'message': 'Module enabled. A system <strong><a  class="confirm-restart" href="#" title="Restart Yombo Gateway">restart is required</a></strong> to take affect.',
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


        @webapp.route('/modules/add', methods=['GET'])
        @require_auth()
        def page_devtools_modules_add_get(webinterface, request, session):
            data = {
                'module_type': webinterface.reqest_get_default(request, 'module_type', ""),
                'label': webinterface.reqest_get_default(request, 'label', ""),
                'machine_label': webinterface.reqest_get_default(request, 'machine_label', ""),
                'description': webinterface.reqest_get_default(request, 'description', ""),
                'short_description': webinterface.reqest_get_default(request, 'short_description', ""),
                'description_formatting': webinterface.reqest_get_default(request, 'description_formatting', ""),
                'repository_link': webinterface.reqest_get_default(request, 'repository_link', ""),
                'issue_tracker_link': webinterface.reqest_get_default(request, 'issue_tracker_link', ""),
                'doc_link': webinterface.reqest_get_default(request, 'doc_link', ""),
                'git_link': webinterface.reqest_get_default(request, 'git_link', ""),
                'prod_branch': webinterface.reqest_get_default(request, 'prod_branch', ""),
                'dev_branch': webinterface.reqest_get_default(request, 'dev_branch', ""),
                'status': int(webinterface.reqest_get_default(request, 'status', 1)),
                'public': int(webinterface.reqest_get_default(request, 'public', 0)),
            }
            return page_devtools_modules_form(webinterface, request, session, data, "Add Module")

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
                'public': int(request.args.get('public')[0]),
                'status': int(request.args.get('status')[0]),
            }

            results = yield webinterface._Modules.dev_add_module(data)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(page_devtools_modules_form(webinterface, request, session, data, None))

            msg = {
                'header': 'Module Added',
                'label': 'Module added successfully',
                'description': '<p>The module has been added. If you have requested this module to be made public, please allow a few days for Yombo to perform a code review of your repository.</p><p>Continue to <a href="/devtools/modules/index">modules index</a></p>',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/modules/<string:module_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_edit_get(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if results['code'] != 200:
                webinterface.add_alert(results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))
            returnValue(page_devtools_modules_form(webinterface, request, session, results['data'], "Edit Module: %s" % results['data']['label']))

        @webapp.route('/modules/<string:module_id>/edit', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_edit_post(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if results['code'] != 200:
                webinterface.add_alert(results['content']['html_message'], 'warning')
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
                returnValue(page_devtools_modules_form(webinterface, request, session, data, "Edit Module: %s" % data['label']))

            msg = {
                'header': 'Module Updated',
                'label': 'Module updated successfully',
                'description': '<p>The module has been updated. If you have requested this module to be made public, please allow a few days for Yombo to perform a code review of your repository.</p><p>Continue to <a href="/devtools/modules/index">modules index</a></p>',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        def page_devtools_modules_form(webinterface, request, session, module, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               module=module,
                               )

        @webapp.route('/modules/<string:module_id>/variables', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_variables_get(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if results['code'] != 200:
                webinterface.add_alert(results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/variable_details.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                               module=results['data'],
                               )
                        )

####################################
# Variables
####################################
        @webapp.route('/variables/group/<string:group_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_details_get(webinterface, request, session, group_id):
            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/index'))

            field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/by_group/%s' % group_id)
            if field_results['code'] != 200:
                webinterface.add_alert(field_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/index'))
                # returnValue(webinterface.redirect(request, '/modules/%s/variables' % module_id))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/variables/group_details.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                               var_group=group_results['data'],
                               var_fields=field_results['data']
                               )
                        )

        @webapp.route('/variables/group/<string:group_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_edit_get(webinterface, request, session, group_id):
            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/index'))

            if group_results['data']['relation_type'] == "module":
                parent_type = 'module'
                parent_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % group_results['data']['relation_id'])
                if parent_results['code'] != 200:
                    webinterface.add_alert(parent_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/index'))
            elif group_results['data']['relation_type'] == "device_type":
                parent_type = 'device_type'
                parent_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % group_results['data']['relation_id'])
                if parent_results['code'] != 200:
                    webinterface.add_alert(parent_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/index'))

            returnValue(page_devtools_variables_group_form(webinterface, request, session, parent_type, parent_results['data'], group_results['data'], "Edit Group Variable: %s" % group_results['data']['group_label']))

        @webapp.route('/variables/group/add/<string:parent_id>/<string:parent_type>', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_add_get(webinterface, request, session, parent_id, parent_type):
            data = {
                'relation_id': parent_id,
                'relation_type': parent_type,
                'group_machine_label': webinterface.reqest_get_default(request, 'group_machine_label', ""),
                'group_label': webinterface.reqest_get_default(request, 'group_label', ""),
                'group_description': webinterface.reqest_get_default(request, 'group_description', ""),
                'group_weight': webinterface.reqest_get_default(request, 'group_weight', 0),
                'status': int(webinterface.reqest_get_default(request, 'status', 1)),
            }

            if parent_type == "module":
                parent_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % parent_id)
                if parent_results['code'] != 200:
                    webinterface.add_alert(parent_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/index'))
            elif parent_type == "device_type":
                parent_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % parent_id)
                if parent_results['code'] != 200:
                    webinterface.add_alert(parent_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/index'))

            returnValue(page_devtools_variables_group_form(webinterface, request, session, parent_type, parent_results['data'], data, "Add Group Variable to: %s" % parent_results['data']['label']))

        @webapp.route('/variables/group/add/<string:parent_id>/<string:parent_type>', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_add_post(webinterface, request, session, parent_id, parent_type):
            data = {
                'relation_id': parent_id,
                'relation_type': parent_type,
                'group_machine_label': request.args.get('group_machine_label')[0],
                'group_label': request.args.get('group_label')[0],
                'group_description': request.args.get('group_description')[0],
                'group_weight': request.args.get('group_weight')[0],
                'status': int(request.args.get('status')[0]),
            }

            if parent_type == "module":
                parent_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % parent_id)
                if parent_results['code'] != 200:
                    webinterface.add_alert(parent_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/index'))
            elif parent_type == "device_type":
                parent_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % parent_id)
                if parent_results['code'] != 200:
                    webinterface.add_alert( ['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/index'))

            returnValue(page_devtools_variables_group_form(webinterface, request, session, parent_type, parent_results['data'], data, "Add Group Variable to: %s" % parent_results['data']['label']))



        @webapp.route('/variables/group/add/<string:parent_id>/<string:parent_type>', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_add_post(webinterface, request, session, parent_id, parent_type):
            data = {
                'relation_id': parent_id,
                'relation_type': parent_type,
                'group_machine_label': request.args.get('group_machine_label')[0],
                'group_label': request.args.get('group_label')[0],
                'group_description': request.args.get('group_description')[0],
                'group_weight': request.args.get('group_weight')[0],
                'status': int(request.args.get('status')[0]),
            }

            if parent_type == "module":
                parent_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % parent_id)
                if parent_results['code'] != 200:
                    webinterface.add_alert(parent_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/index'))
            elif parent_type == "device_type":
                parent_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % parent_id)
                if parent_results['code'] != 200:
                    webinterface.add_alert( ['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/index'))

            results = yield webinterface._Variables.dev_add_group(data)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(page_devtools_variables_group_form(webinterface, request, session, parent_type, parent_results['data'], data, "Add Group Variable to: %s" % parent_results['data']['label']))

            msg = {
                'header': 'Variable Group Added',
                'label': 'Variable group added successfully',
                'description': 'The variable group has beed added.',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        def page_devtools_variables_group_form(webinterface, request, session, parent_type, parent, group, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/variables/group_form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               parent_type=parent_type,
                               parent=parent,
                               group=group,
                               )

        @webapp.route('/variables/group/<string:group_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_edit_get(webinterface, request, session, group_id):
            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/variables/group_form.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                               var_group=group_results['data'],
                               )
                        )

        @webapp.route('/variables/field/<string:field_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_field_details_get(webinterface, request, session, field_id):
            field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/%s' % field_id)
            if field_results['code'] != 200:
                webinterface.add_alert(field_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/modules/%s/variables' % module_id))

            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % field_results['data']['group_id'])
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/modules/%s/variables' % module_id))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/variables/field_details.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                               var_group=group_results['data'],
                               var_field=field_results['data']
                               )
                        )
