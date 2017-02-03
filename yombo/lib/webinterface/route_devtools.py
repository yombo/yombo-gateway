from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth_pin, require_auth

def route_devtools(webapp):
    with webapp.subroute("/devtools") as webapp:

        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/", "Home")
            webinterface.add_breadcrumb(request, "/devtools/", "Developer Tools")

        @webapp.route('/')
        @require_auth_pin()
        def page_devtools(webinterface, request):
            return webinterface.redirect(request, '/devtools/index')

        @webapp.route('/index')
        @require_auth()
        def page_devtools_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/index.html')
            root_breadcrumb(webinterface, request)
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
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/commands/<string:command_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_details_get(webinterface, request, session, command_id):
            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/commands/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/commands/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/commands/%s/details" % command_results['data']['id'], command_results['data']['label'])
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    command=command_results['data'],
                                    )
                        )

        @webapp.route('/commands/<string:command_id>/delete', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_delete_get(webinterface, request, session, command_id):
            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/commands/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/commands/delete.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/commands/%s/details" % command_id, command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/commands/%s/delete" % command_id, "Delete")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    command=command_results['data'],
                                    )
                        )

        @webapp.route('/commands/<string:command_id>/delete', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_delete_post(webinterface, request, session, command_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/commands/%s/details' % command_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the command.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/commands/%s/details' % command_id))

            command_results = yield webinterface._Commands.dev_delete_command(command_id)

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/commands/%s/details' % command_id))

            msg = {
                'header': 'Command Deleted',
                'label': 'Command deleted successfully',
                'description': '<p>The command has been deleted.</p><p>Continue to <a href="/devtools/commands/index">commands index</a> or <a href="/devtools/commands/%s/details">view the command</a>.</p>' % command_id,
            }

            command_api_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if command_api_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands")
                webinterface.add_breadcrumb(request, "/devtools/commands/%s/details" % command_id,
                                            command_api_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/commands/%s/delete" % command_id, "Delete")
            else:
                webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/commands/<string:command_id>/disable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_disable_get(webinterface, request, session, command_id):
            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/commands/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/commands/disable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/commands/%s/details" % command_id, command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/commands/%s/delete" % command_id, "Disable")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    command=command_results['data'],
                                    )
                        )

        @webapp.route('/commands/<string:command_id>/disable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_disable_post(webinterface, request, session, command_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/commands/%s/details' % command_id))

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the command.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/commands/%s/details' % command_id))

            command_results = yield webinterface._Commands.dev_disable_command(command_id)

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/commands/%s/details' % command_id))

            msg = {
                'header': 'Command Disabled',
                'label': 'Command disabled successfully',
                'description': '<p>The command has been disabled.</p><p>Continue to <a href="/devtools/commands/index">commands index</a> or <a href="/devtools/commands/%s/details">view the command</a>.</p>' % command_id,
            }

            command_api_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if command_api_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands")
                webinterface.add_breadcrumb(request, "/devtools/commands/%s/details" % command_id,
                                            command_api_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/commands/%s/delete" % command_id, "Disable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands", True)
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/commands/<string:command_id>/enable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_enable_get(webinterface, request, session, command_id):
            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/commands/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/commands/enable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/commands/%s/details" % command_id, command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/commands/%s/enable", "Enable")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    command=command_results['data'],
                                    )
                        )

        @webapp.route('/commands/<string:command_id>/enable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_enable_post(webinterface, request, session, command_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/commands/%s/details' % command_id))

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the command.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/commands/%s/details' % command_id))

            command_results = yield webinterface._Commands.dev_enable_command(command_id)

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/commands/%s/details' % command_id))

            msg = {
                'header': 'Command Enabled',
                'label': 'Command enabled successfully',
                'description': '<p>The command has been enabled.</p><p>Continue to <a href="/devtools/commands/index">commands index</a> or <a href="/devtools/commands/%s/details">view the command</a>.</p>' % command_id,
            }

            command_api_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if command_api_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands")
                webinterface.add_breadcrumb(request, "/devtools/commands/%s/details" % command_id,
                                            command_api_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/commands/%s/enable", "Enable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

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
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/commands/add", "Add")
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
                'description': '<p>The command has been added. If you have requested this command to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/commands/index">command index</a> or <a href="/devtools/commands/%s/details">view the command</a>.</p>' % command_results['command_id'],
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/commands/add", "Add")
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

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/commands/%s/details" % command_results['data']['id'], command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/commands/%s/edit", "Edit")

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

            data['machine_label'] = request.args.get('machine_label_hidden')[0]

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                returnValue(page_devtools_commands_form(webinterface, request, session, 'edit', data,
                                                            "Edit Command: %s" % data['label']))

                returnValue(webinterface.redirect(request, '/devtools/commands/index'))

            msg = {
                'header': 'Command Updated',
                'label': 'Command updated successfully',
                'description': '<p>The command has been updated. If you have requested this command to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/commands/index">command index</a> or <a href="/devtools/commands/%s/details">view the command</a>.</p>' % command_id,
            }

            command_api_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/commands/index", "Commands")
            if command_api_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/commands/%s/details" % command_id,
                                            command_api_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/commands/%s/edit", "Edit")

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


####################################
# Device Types
####################################
        @webapp.route('/device_types/index')
        @require_auth()
        def page_devtools_device_types_index_get(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/device_types/index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/device_types/<string:device_type_id>/add_command', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_add_command_get(webinterface, request, session, device_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/device_types/add_command.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id, device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/add_command" % device_type_id, "Add Command")

            returnValue(page.render(alerts=webinterface.get_alerts(),
                               device_type=device_type_results['data'],
                               ))

        @webapp.route('/device_types/<string:device_type_id>/add_command/<string:command_id>', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_add_command_do_get(webinterface, request, session, device_type_id, command_id):
            print "111"
            results = yield webinterface._DeviceTypes.dev_add_command(device_type_id, command_id)
            print "222"
            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/%s/details' % device_type_id))

            msg = {
                'header': 'Command Associated',
                'label': 'Command has been associated successfully',
                'description': '<p>The command has been associated to the device type.</p><p>Continue to <a href="/devtools/device_types/index">device types index</a> or <a href="/devtools/device_types/%s/details">view the device type</a>.</p>' % device_type_id,
            }

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if device_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id,
                                            device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/device_types/%s/add_command" % device_type_id,
                                            "Add Command")
            else:
                webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))


        @webapp.route('/device_types/<string:device_type_id>/remove_command/<string:command_id>', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_remove_command_get(webinterface, request, session, device_type_id, command_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))
            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/device_types/remove_command.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id, device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/remove_command" % device_type_id, "Remove Command")

            returnValue( page.render(alerts=webinterface.get_alerts(),
                               device_type=device_type_results['data'],
                               command=command_results['data'],
                               )
                         )

        @webapp.route('/device_types/<string:device_type_id>/remove_command/<string:command_id>', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_remove_command_post(webinterface, request, session, device_type_id, command_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/device_types/%s/details' % device_type_id))

            if confirm != "remove":
                webinterface.add_alert('Must enter "remove" in the confirmation box to remove the command from the device type.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/%s/device_type_id' % device_type_id))

            device_type_results = yield webinterface._DeviceTypes.dev_remove_command(device_type_id, command_id)
            if device_type_results['status'] == 'failed':
                webinterface.add_alert(device_type_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/%s/details' % device_type_id))

            msg = {
                'header': 'Command Removed',
                'label': 'Command has been removed successfully',
                'description': '<p>The command has been remove from the device type.</p><p>Continue to <a href="/devtools/device_types/index">device types index</a> or <a href="/devtools/device_types/%s/details">view the device type</a>.</p>' % device_type_id,
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            root_breadcrumb(webinterface, request)

            if device_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))
            else:
                webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types", True)

            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id, device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/remove_command" % device_type_id, "Remove Command")

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

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

            device_type_commands_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type_command/%s' % device_type_id)
            if device_type_commands_results['code'] != 200:
                webinterface.add_alert(device_type_commands_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/device_types/details.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id, device_type_results['data']['label'])

            returnValue( page.render(alerts=webinterface.get_alerts(),
                               device_type=device_type_results['data'],
                               category=category_results['data'],
                               device_type_commands=device_type_commands_results['data']
                               )
                         )

        @webapp.route('/device_types/<string:device_type_id>/delete', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_delete_get(webinterface, request, session, device_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/device_types/delete.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id, device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/delete" % device_type_id, "Delete")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    )
                        )

        @webapp.route('/device_types/<string:device_type_id>/delete', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_delete_post(webinterface, request, session, device_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/device_types/%s/details' % device_type_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the device type.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/%s/details' % device_type_id))

            results = yield webinterface._DeviceTypes.dev_delete_device_type(device_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/%s/details' % device_type_id))

            msg = {
                'header': 'Device Type Deleted',
                'label': 'Device Type deleted successfully',
                'description': '<p>The device type has been deleted.</p><p>Continue to <a href="/devtools/device_types/index">device type index</a> or <a href="/devtools/device_types/%s/details">view the device type</a>.</p>' % device_type_id,
            }

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_types/%s' % device_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if device_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id,
                                            device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/device_types/%s/delete" % device_type_id, "Delete")
            else:
                webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/device_types/<string:device_type_id>/disable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_disable_get(webinterface, request, session, device_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/device_types/disable.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id, device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/disable" % device_type_id, "Disable")

            returnValue( page.render(alerts=webinterface.get_alerts(),
                               device_type=device_type_results['data'],
                               )
                         )

        @webapp.route('/device_types/<string:device_type_id>/disable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_disable_post(webinterface, request, session, device_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/device_types/%s/details' % device_type_id))

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the device type.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/%s/device_type_id' % device_type_id))

            results = yield webinterface._DeviceTypes.dev_disable_device_type(device_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/%s/details' % device_type_id))

            msg = {
                'header': 'Device Type Disabled',
                'label': 'Device Type disabled successfully',
                'description': '<p>The device type has been disabled.</p><p>Continue to <a href="/devtools/device_types/index">device types index</a> or <a href="/devtools/device_types/%s/details">view the device type</a>.</p>' % device_type_id,
            }

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            if device_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id, device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/device_types/%s/disable" % device_type_id, "Disable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/device_types/<string:device_type_id>/enable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_enable_get(webinterface, request, session, device_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/device_types/enable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id, device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/disable" % device_type_id, "Disable")
            returnValue( page.render(alerts=webinterface.get_alerts(),
                               device_type=device_type_results['data'],
                               )
                         )

        @webapp.route('/device_types/<string:device_type_id>/enable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_enable_post(webinterface, request, session, device_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/device_types/%s/details' % device_type_id))

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the device type.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/%s/device_type_id' % device_type_id))

            results = yield webinterface._DeviceTypes.dev_enable_device_type(device_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/%s/details' % device_type_id))

            msg = {
                'header': 'Device Type Enabled',
                'label': 'Device Type enabled successfully',
                'description': '<p>The device type has been enabled.</p><p>Continue to <a href="/devtools/device_types/index">device types index</a> or <a href="/devtools/device_types/%s/details">view the device type</a>.</p>' % device_type_id,
            }

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            if device_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id, device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/device_types/%s/enable" % device_type_id, "Enable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

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
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/device_types/add", "Add")
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
                'description': '<p>The device type has been added. If you have requested this device type to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/device_types/index">device types index</a> or <a href="/devtools/device_types/%s/details">view the new device type</a>.</p>' %
                               device_type_results['device_type_id'],
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/device_types/add", "Add")
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

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id, device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/edit" % device_type_id, "Edit")

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

            data['machine_label'] = request.args.get('machine_label_hidden')[0]

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
                'description': '<p>The device type has been updated. If you have requested this device type to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/device_types/index">device types index</a> or <a href="/devtools/device_types/%s/details">view the new device type</a>.</p>' %
                               device_type_results['device_type_id'],
            }

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            if device_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id, device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/device_types/%s/enable" % device_type_id, "Enable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types", True)

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
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/device_types/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/device_types/variable_details.html')
            webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % device_type_id, device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/device_types/%s/variables" % device_type_id, "Variables")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                               device_type=device_type_results['data'],
                               )
                        )

####################################
# Modules
####################################
        @webapp.route('/modules/index')
        @require_auth()
        def page_devtools_modules_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/modules/index", "Modules")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/modules/<string:module_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_details_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/modules/%s/details" % module_id, module_results['data']['label'])
            returnValue( page.render(alerts=webinterface.get_alerts(),
                               module=module_results['data'],
                               )
                         )

        @webapp.route('/modules/<string:module_id>/delete', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_delete_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/delete.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/modules/%s/details" % module_id, module_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/modules/%s/delete" % module_id, "Delete")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    module=module_results['data'],
                                    )
                        )

        @webapp.route('/modules/<string:module_id>/delete', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_delete_post(webinterface, request, session, module_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/modules/%s/details' % module_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the module.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/%s/details' % module_id))

            module_results = yield webinterface._Modules.dev_delete_module(module_id)

            if module_results['status'] == 'failed':
                webinterface.add_alert(module_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/%s/details' % module_id))

            msg = {
                'header': 'Module Deleted',
                'label': 'Module deleted successfully',
                'description': '<p>The module has been deleted.</p><p>Continue to <a href="/devtools/modules/index">modules index</a> or <a href="/devtools/modules/%s/details">view the module</a>.</p>' % module_id,
            }

            module_api_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if module_api_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/modules/index", "Modules")
                webinterface.add_breadcrumb(request, "/devtools/modules/%s/details" % module_id,
                                            module_api_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/modules/%s/delete" % module_id, "Delete")
            else:
                webinterface.add_breadcrumb(request, "/devtools/modules/index", "Modules", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/modules/<string:module_id>/disable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_disable_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/disable.html')
            returnValue( page.render(alerts=webinterface.get_alerts(),
                               module=module_results['data'],
                               )
                         )

        @webapp.route('/modules/<string:module_id>/disable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_disable_post(webinterface, request, session, module_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/modules/%s/details' % module_id))

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the module.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/%s/details' % module_id))

            results = yield webinterface._Modules.dev_disable_module(module_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/%s/details' % module_id))

            msg = {
                'header': 'Module Disabled',
                'label': 'Module disabled successfully',
                'description': '<p>The module has been disabled.</p><p>Continue to <a href="/devtools/modules/index">modules index</a> or <a href="/devtools/modules/%s/details">view the module</a>.</p>' % module_id,
            }

            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            if module_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/modules/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/modules/%s/details" % module_id, module_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/modules/%s/disable" % module_id, "Disable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/modules/index", "Modules", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/modules/<string:module_id>/enable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_enable_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/enable.html')
            returnValue( page.render(alerts=webinterface.get_alerts(),
                               module=module_results['data'],
                               )
                         )

        @webapp.route('/modules/<string:module_id>/enable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_enable_post(webinterface, request, session, module_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/modules/%s/details' % module_id))

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the module.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/%s/details' % module_id))

            results = yield webinterface._Modules.dev_enable_module(module_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/%s/details' % module_id))

            msg = {
                'header': 'Module Enabled',
                'label': 'Module enabled successfully',
                'description': '<p>The module has been enabled.</p><p>Continue to <a href="/devtools/modules/index">modules index</a> or <a href="/devtools/modules/%s/details">view the module</a>.</p>' % module_id,
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
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
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/modules/add", "Add Module")
            return page_devtools_modules_form(webinterface, request, session, data, "add", "Add Module")

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
                returnValue(page_devtools_modules_form(webinterface, request, session, data, "add", "Add Module"))

            msg = {
                'header': 'Module Added',
                'label': 'Module added successfully',
                'description': '<p>The module has been added. If you have requested this module to be made public, please allow a few days for Yombo to perform a code review of your repository.</p><p>Continue to <a href="/devtools/modules/index">modules index</a></p>',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/modules/add", "Add Module")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/modules/<string:module_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_edit_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/modules/%s/details" % module_id, module_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/modules/%s/edit" % module_id, "Edit")

            returnValue(page_devtools_modules_form(webinterface, request, session, module_results['data'], "edit", "Edit Module: %s" % module_results['data']['label']))

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

            data['module_type'] = request.args.get('module_type')[0]
            data['machine_label'] = request.args.get('machine_label')[0]

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(page_devtools_modules_form(webinterface, request, session, data, "edit", "Edit Module: %s" % data['label']))

            msg = {
                'header': 'Module Updated',
                'label': 'Module updated successfully',
                'description': '<p>The module has been updated. If you have requested this module to be made public, please allow a few days for Yombo to perform a code review of your repository.</p><p>Continue to <a href="/devtools/modules/index">modules index</a></p>',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        def page_devtools_modules_form(webinterface, request, session, module, display_type, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               module=module,
                               display_type=display_type
                               )

        @webapp.route('/modules/<string:module_id>/variables', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_modules_variables_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/modules/variable_details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/modules/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/modules/%s/details" % module_id, module_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/modules/%s/variables" % module_id, "Variables")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                               module=module_results['data'],
                               )
                        )

####################################
# Variables
####################################
        @inlineCallbacks
        def variable_group_breadcrumbs(webinterface, request, parent_id, parent_type):
            if parent_type == 'module':
                module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % parent_id)
                root_breadcrumb(webinterface, request)

                if module_results['code'] == 200:
                    webinterface.add_breadcrumb(request, "/devtools/modules/index", "Modules")
                    webinterface.add_breadcrumb(request, "/devtools/modules/%s/details" % parent_id,
                                                module_results['data']['label'])
                    webinterface.add_breadcrumb(request, "/devtools/modules/%s/variables" % parent_id, "Group Variables", True)
                else:
                    webinterface.add_breadcrumb(request, "/devtools/modules/index", "Modules", True)

                returnValue(module_results)
            elif parent_type == 'device_type':
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % parent_id)
                root_breadcrumb(webinterface, request)

                if device_type_results['code'] == 200:
                    webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Device Types")
                    webinterface.add_breadcrumb(request, "/devtools/device_types/%s/details" % parent_id,
                                                device_type_results['data']['label'])
                    webinterface.add_breadcrumb(request, "/devtools/device_types/%s/variables" % parent_id, "Group Variables", True)
                else:
                    webinterface.add_breadcrumb(request, "/devtools/device_types/index", "Modules", True)
                returnValue(device_type_results)

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

            parent = yield variable_group_breadcrumbs(webinterface, request, parent_id, parent_type)
            webinterface.add_breadcrumb(request, "/", "Add Variable")
            if parent['code'] != 200:
                webinterface.add_alert(['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/index'))

            returnValue(page_devtools_variables_group_form(webinterface, request, session, parent_type, parent['data'], data, "Add Group Variable to: %s" % parent['data']['label']))

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

            parent = yield variable_group_breadcrumbs(webinterface, request, parent_id, parent_type)
            webinterface.add_breadcrumb(request, "/", "Add Variable")
            if parent['code'] != 200:
                webinterface.add_alert(['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/index'))

            results = yield webinterface._Variables.dev_add_group(data)
            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(page_devtools_variables_group_form(webinterface, request, session, parent_type, parent['data'], data, "Add Group Variable to: %s" % parent['data']['label']))

            msg = {
                'header': 'Variable Group Added',
                'label': 'Variable group added successfully',
                'description': ''
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            if parent_type == 'module':
                msg['description'] = '<p>Variable group has beed added.</p><p>Continue to:<ul><li><a href="/devtools/modules/index">modules index</a></li><li><a href="/devtools/modules/%s/details">view the module</a></li><li><a href="/devtools/modules/%s/variables"> view module variables</a></li></ul></p>' % (parent_id, parent_id)
            elif parent_type == 'device_type':
                msg['description'] = '<p>Variable group has beed added.</p><p>Continue to:<ul><li><a href="/devtools/device_types/index">device types index</a></li><li><a href="/devtools/device_types/%s/details">view the device type: %s</a></li><li><a href="/devtools/device_types/%s/variables"> view device type variables</a></li></ul></p>' % (parent_id, parent['data']['label'], parent_id)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/variables/group/<string:group_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_edit_get(webinterface, request, session, group_id):
            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/index'))

            parent_type = group_results['data']['relation_type']
            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'], parent_type)
            webinterface.add_breadcrumb(request, "/", "Edit Variable")
            if parent['code'] != 200:
                webinterface.add_alert(['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/index'))

            returnValue(page_devtools_variables_group_form(webinterface, request, session, parent_type, parent['data'], group_results['data'], "Edit Group Variable: %s" % group_results['data']['group_label']))

        def page_devtools_variables_group_form(webinterface, request, session, parent_type, parent, group, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/variables/group_form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               parent_type=parent_type,
                               parent=parent,
                               group=group,
                               )

        @webapp.route('/variables/group/<string:group_id>/edit', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_edit_post(webinterface, request, session, group_id):
            data = {
                'group_machine_label': request.args.get('group_machine_label')[0],
                'group_label': request.args.get('group_label')[0],
                'group_description': request.args.get('group_description')[0],
                'group_weight': request.args.get('group_weight')[0],
                'status': int(request.args.get('status')[0]),
            }

            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/index'))

            parent_type = group_results['data']['relation_type']
            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'], parent_type)
            webinterface.add_breadcrumb(request, "/", "Edit Variable")
            if parent['code'] != 200:
                webinterface.add_alert(['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/index'))

            results = yield webinterface._Variables.dev_edit_group(group_id, data)
            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(page_devtools_variables_group_form(webinterface, request, session, parent_type, parent['data'], data, "Add Group Variable to: %s" % parent['data']['label']))

            msg = {
                'header': 'Variable Group Edited',
                'label': 'Variable group edited successfully',
                'description': ''
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            if parent_type == 'module':
                msg['description'] = '<p>Variable group has beed edited.</p><p>Continue to:<ul><li><a href="/devtools/modules/index">modules index</a></li><li><a href="/devtools/modules/%s/details">view the module</a></li><li><a href="/devtools/modules/%s/variables"> view module variables</a></li></ul></p>' % (parent['data']['id'], parent['data']['id'])
            elif parent_type == 'device_type':
                msg['description'] = '<p>Variable group has beed edited.</p><p>Continue to:<ul><li><a href="/devtools/device_types/index">device types index</a></li><li><a href="/devtools/device_types/%s/details">view the device type: %s</a></li><li><a href="/devtools/device_types/%s/variables"> view device type variables</a></li></ul></p>' % (parent['data']['id'], parent['data']['label'], parent['data']['id'])

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/variables/group/<string:group_id>/delete', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_delete_get(webinterface, request, session, group_id):
            var_group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if var_group_results['code'] != 200:
                webinterface.add_alert(var_group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/index'))

            data = var_group_results['data']
            parent = yield variable_group_breadcrumbs(webinterface, request, data['relation_id'], data['relation_type'])
            webinterface.add_breadcrumb(request, "/", "Delete Variable")

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/variables/group_delete.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    var_group=data,
                                    parent=parent,
                                    )
                        )

        @webapp.route('/variables/group/<string:group_id>/delete', methods=['post'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_delete_post(webinterface, request, session, group_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/index'))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the variable group.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/variables/group/%s/delete' % group_id))

            var_group_results = yield webinterface._Variables.dev_delete_group(group_id)

            if var_group_results['status'] == 'failed':
                webinterface.add_alert(var_group_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/variables/group/%s/delete' % group_id))

            var_group_api_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if var_group_api_results['code'] != 200:
                webinterface.add_alert(var_group_api_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/index'))

            data = var_group_api_results['data']
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            parent = yield variable_group_breadcrumbs(webinterface, request, data['relation_id'], data['relation_type'])
            webinterface.add_breadcrumb(request, "/", "Delete Variable")

            msg = {
                'header': 'Variable Group Deleted',
                'label': 'Variable Group deleted successfully',
                'description': '',
            }

            if data['relation_type'] == 'module':
                msg['description'] = '<p>Variable group has beed deleted.</p><p>Continue to:<ul><li><a href="/devtools/modules/index">modules index</a></li><li><a href="/devtools/modules/%s/details">view the module</a></li><li><a href="/devtools/modules/%s/variables"> view module variables</a></li></ul></p>' % (data['relation_id'], data['relation_id'])
            elif data['relation_type'] == 'device_type':
                msg['description'] = '<p>Variable group has beed deleted.</p><p>Continue to:<ul><li><a href="/devtools/device_types/index">device types index</a></li><li><a href="/devtools/device_types/%s/details">view the device type: %s</a></li><li><a href="/devtools/device_types/%s/variables"> view device type variables</a></li></ul></p>' % (data['relation_id'], parent['data']['label'], data['relation_id'])

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/variables/field/<string:field_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_field_details_get(webinterface, request, session, field_id):
            field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/%s' % field_id)
            if field_results['code'] != 200:
                webinterface.add_alert(field_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/modules/%s/variables' % field_id))

            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % field_results['data']['group_id'])
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/modules/%s/variables' % field_id))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/variables/field_details.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                               var_group=group_results['data'],
                               var_field=field_results['data']
                               )
                        )
