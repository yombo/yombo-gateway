from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.lib.webinterface.auth import require_auth, run_first

def route_devtools_config(webapp):
    with webapp.subroute("/devtools") as webapp:

        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/devtools/config/", "Config Tools")

        @webapp.route('/config/')
        @require_auth()
        @run_first()
        def page_devtools(webinterface, request, session):
            return webinterface.redirect(request, '/devtools/config/index')

        @webapp.route('/config/index')
        @require_auth()
        @run_first()
        def page_devtools_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/index.html')
            root_breadcrumb(webinterface, request)
            return page.render(alerts=webinterface.get_alerts(),
                               )

        ####################################
        # Command
        ####################################
        @webapp.route('/config/commands/index')
        @require_auth()
        @run_first()
        def page_devtools_commands_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/commands/index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/config/commands/<string:command_id>/details', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_commands_details_get(webinterface, request, session, command_id):
            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/commands/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/commands/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_results['data']['id'],
                                        command_results['data']['label'])
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    command=command_results['data'],
                                    )
                        )

        @webapp.route('/config/commands/<string:command_id>/delete', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_commands_delete_get(webinterface, request, session, command_id):
            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/commands/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/commands/delete.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                        command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/delete" % command_id, "Delete")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    command=command_results['data'],
                                    )
                        )

        @webapp.route('/config/commands/<string:command_id>/delete', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_commands_delete_post(webinterface, request, session, command_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/commands/%s/details' % command_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the command.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/commands/%s/details' % command_id))

            command_results = yield webinterface._Commands.dev_command_delete(command_id)

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/commands/%s/details' % command_id))

            msg = {
                'header': 'Command Deleted',
                'label': 'Command deleted successfully',
                'description': '<p>The command has been deleted.</p><p>Continue to <a href="/devtools/config/commands/index">commands index</a> or <a href="/devtools/config/commands/%s/details">view the command</a>.</p>' % command_id,
            }

            command_api_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if command_api_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands")
                webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                            command_api_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/delete" % command_id, "Delete")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/commands/<string:command_id>/disable', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_commands_disable_get(webinterface, request, session, command_id):
            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/commands/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/commands/disable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                        command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/delete" % command_id, "Disable")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    command=command_results['data'],
                                    )
                        )

        @webapp.route('/config/commands/<string:command_id>/disable', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_commands_disable_post(webinterface, request, session, command_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/commands/%s/details' % command_id))

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the command.',
                                       'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/commands/%s/details' % command_id))

            command_results = yield webinterface._Commands.dev_command_disable(command_id)

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/commands/%s/details' % command_id))

            msg = {
                'header': 'Command Disabled',
                'label': 'Command disabled successfully',
                'description': '<p>The command has been disabled.</p><p>Continue to <a href="/devtools/config/commands/index">commands index</a> or <a href="/devtools/config/commands/%s/details">view the command</a>.</p>' % command_id,
            }

            command_api_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if command_api_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands")
                webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                            command_api_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/delete" % command_id, "Disable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands", True)
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/commands/<string:command_id>/enable', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_commands_enable_get(webinterface, request, session, command_id):
            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/commands/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/commands/enable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                        command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/enable", "Enable")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    command=command_results['data'],
                                    )
                        )

        @webapp.route('/config/commands/<string:command_id>/enable', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_commands_enable_post(webinterface, request, session, command_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/commands/%s/details' % command_id))

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the command.', 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/commands/%s/details' % command_id))

            command_results = yield webinterface._Commands.dev_command_enable(command_id)

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/commands/%s/details' % command_id))

            msg = {
                'header': 'Command Enabled',
                'label': 'Command enabled successfully',
                'description': '<p>The command has been enabled.</p><p>Continue to <a href="/devtools/config/commands/index">commands index</a> or <a href="/devtools/config/commands/%s/details">view the command</a>.</p>' % command_id,
            }

            command_api_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if command_api_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands")
                webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                            command_api_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/enable", "Enable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/commands/add', methods=['GET'])
        @require_auth()
        @run_first()
        def page_devtools_commands_add_get(webinterface, request, session):
            data = {
                'voice_cmd': webinterface.request_get_default(request, 'voice_cmd', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'public': int(webinterface.request_get_default(request, 'public', 0)),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/config/commands/add", "Add")
            return page_devtools_commands_form(webinterface, request, session, 'add', data,
                                               "Add Command")

        @webapp.route('/config/commands/add', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_commands_add_post(webinterface, request, session):
            data = {
                'voice_cmd': webinterface.request_get_default(request, 'voice_cmd', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'public': int(webinterface.request_get_default(request, 'public', 0)),
            }

            command_results = yield webinterface._Commands.dev_command_add(data)

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                returnValue(
                    page_devtools_commands_form(webinterface, request, session, 'add', data, "Add Command"))

            msg = {
                'header': 'Command Added',
                'label': 'Command added successfully',
                'description': '<p>The command has been added. If you have requested this command to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/config/commands/index">command index</a> or <a href="/devtools/config/commands/%s/details">view the command</a>.</p>' %
                               command_results['command_id'],
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/config/commands/add", "Add")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/commands/<string:command_id>/edit', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_commands_edit_get(webinterface, request, session, command_id):
            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/commands/index'))

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_results['data']['id'],
                                        command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/edit", "Edit")

            returnValue(
                page_devtools_commands_form(webinterface, request, session, 'edit', command_results['data'],
                                            "Edit Command: %s" % command_results['data']['label']))

        @webapp.route('/config/commands/<string:command_id>/edit', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_commands_edit_post(webinterface, request, session, command_id):
            data = {
                'voice_cmd': webinterface.request_get_default(request, 'voice_cmd', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                # 'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'public': int(webinterface.request_get_default(request, 'public', 0)),
                'id': command_id,
            }

            command_results = yield webinterface._Commands.dev_command_edit(command_id, data)

            data['machine_label'] = request.args.get('machine_label_hidden')[0]

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands")
                webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                            data['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/edit", "Edit")

                returnValue(page_devtools_commands_form(webinterface, request, session, 'edit', data,
                                                        "Edit Command: %s" % data['label']))

                returnValue(webinterface.redirect(request, '/devtools/config/commands/index'))

            msg = {
                'header': 'Command Updated',
                'label': 'Command updated successfully',
                'description': '<p>The command has been updated. If you have requested this command to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/config/commands/index">command index</a> or <a href="/devtools/config/commands/%s/details">view the command</a>.</p>' % command_id,
            }

            command_api_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands")
            if command_api_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                            command_api_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/edit", "Edit")

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        def page_devtools_commands_form(webinterface, request, session, action_type, command,
                                        header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/commands/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               command=command,
                               action_type=action_type,
                               )

        ####################################
        # Device Types
        ####################################
        @webapp.route('/config/device_types/index')
        @require_auth()
        @run_first()
        def page_devtools_device_types_index_get(webinterface, request, session):
            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/config/device_types/<string:device_type_id>/command/<string:command_id>/details',
                      methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_command_details_get(webinterface, request, session, device_type_id, command_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            device_command_input_results = yield webinterface._YomboAPI.request('GET',
                                                                                '/v1/device_command_input?device_type_id=%s&command_id=%s' % (
                                                                                device_type_id, command_id))
            if device_command_input_results['code'] != 200:
                webinterface.add_alert(device_command_input_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/command_details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
            device_type_id, command_id),
                                        command_results['data']['label'])

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    inputs=device_command_input_results['data'],
                                    command=command_results['data']
                                    ))

        @webapp.route('/config/device_types/<string:device_type_id>/command/add_command', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_command_add_get(webinterface, request, session, device_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/command_add.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/add" % device_type_id,
                                        "Add Command")

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    ))

        @webapp.route('/config/device_types/<string:device_type_id>/command/<string:command_id>/add_command',
                      methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_command_add_do_get(webinterface, request, session, device_type_id, command_id):
            results = yield webinterface._DeviceTypes.dev_command_add(device_type_id, command_id)
            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            msg = {
                'header': 'Command Associated',
                'label': 'Command has been associated successfully',
                'description': '<p>The command has been associated to the device type.</p>'
                               '<p>Continue to:'
                               '<ul>'
                               '<li><a href="/devtools/config/device_types/index">Device types index</a></li>'
                               '<li><a href="/devtools/config/device_types/%s/details">View the device type</a></li>'
                               '<li><strong>Don\'t forget to add input types for the command: <a href="/devtools/config/device_types/%s/command/%s/details">View device type command</a></strong></li>'
                               '</ul>'
                               '</p>' % (device_type_id, device_type_id, command_id)
            }

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if device_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                            device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/add" % device_type_id,
                                            "Add Command")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/device_types/<string:device_type_id>/command/<string:command_id>/remove_command',
                      methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_remove_command_get(webinterface, request, session, device_type_id, command_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))
            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/command_remove.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/remove" % device_type_id,
                                        "Remove Command")

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    command=command_results['data'],
                                    )
                        )

        @webapp.route('/config/device_types/<string:device_type_id>/command/<string:command_id>/remove_command',
                      methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_remove_command_post(webinterface, request, session, device_type_id, command_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            if confirm != "remove":
                webinterface.add_alert(
                    'Must enter "remove" in the confirmation box to remove the command from the device type.',
                    'warning')
                returnValue(
                    webinterface.redirect(request, '/devtools/config/device_types/%s/device_type_id' % device_type_id))

            device_type_results = yield webinterface._DeviceTypes.dev_command_remove(device_type_id, command_id)
            if device_type_results['status'] == 'failed':
                webinterface.add_alert(device_type_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            msg = {
                'header': 'Command Removed',
                'label': 'Command has been removed successfully',
                'description': '<p>The command has been removed from the device type.</p>'
                               '<p>Continue to:'
                               '<ul>'
                               '<li><a href="/devtools/config/device_types/index">Device types index</a></li>'
                               '<li><strong><a href="/devtools/config/device_types/%s/details">View the device type</a></strong></li>'
                               '</ul>'
                               '</p>' % device_type_id
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            root_breadcrumb(webinterface, request)

            if device_type_results['code'] == 200:
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                            device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
                    device_type_id, command_id), command_results['data']['label'])
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types", True)

            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/remove" % device_type_id,
                                        "Remove Command")

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/device_types/<string:device_type_id>/command/<string:command_id>/add_input',
                      methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_command_add_input_get(webinterface, request, session, device_type_id,
                                                             command_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/command_input_add.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/add" % device_type_id,
                                        "Add Command")

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    command=command_results['data']
                                    ))

        @webapp.route(
            '/config/device_types/<string:device_type_id>/command/<string:command_id>/input/<string:input_type_id>/add_input',
            methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_command_input_add_get(webinterface, request, session, device_type_id, command_id,
                                                             input_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            root_breadcrumb(webinterface, request)
            if device_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                            device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
                device_type_id, command_id),
                                            "Command")
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/add_input" % (
                device_type_id, command_id),
                                            "Associate input")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types", True)

            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            data = {
                'live_update': webinterface.request_get_default(request, 'live_update', ""),
                'notes': webinterface.request_get_default(request, 'notes', ""),
                'value_required': webinterface.request_get_default(request, 'value_required', ""),
                'value_min': webinterface.request_get_default(request, 'value_min', ""),
                'value_max': webinterface.request_get_default(request, 'value_max', ""),
                'value_casing': webinterface.request_get_default(request, 'value_casing', "none"),
                'encryption': webinterface.request_get_default(request, 'encryption', "nosuggestion"),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/add", "Add")
            returnValue(page_devtools_device_types_command_input_form(webinterface, request, session, 'add', data,
                                                                      device_type_results['data'],
                                                                      command_results['data'],
                                                                      input_type_results['data'],
                                                                      "Associate input type to command"))

        @webapp.route(
            '/config/device_types/<string:device_type_id>/command/<string:command_id>/input/<string:input_type_id>/add_input',
            methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_command_input_add_post(webinterface, request, session, device_type_id,
                                                              command_id, input_type_id):
            data = {
                'live_update': webinterface.request_get_default(request, 'live_update', ""),
                'notes': webinterface.request_get_default(request, 'notes', ""),
                'value_required': webinterface.request_get_default(request, 'value_required', ""),
                'value_min': webinterface.request_get_default(request, 'value_min', ""),
                'value_max': webinterface.request_get_default(request, 'value_max', ""),
                'value_casing': webinterface.request_get_default(request, 'value_casing', "none"),
                'encryption': webinterface.request_get_default(request, 'encryption', "nosuggestion"),
            }

            results = yield webinterface._DeviceTypes.dev_command_input_edit(device_type_id, command_id, input_type_id,
                                                                             data)

            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            root_breadcrumb(webinterface, request)
            if device_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                            device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
                device_type_id, command_id),
                                            command_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/add_input" % (
                device_type_id, command_id),
                                            "Associate input")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types", True)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(
                    page_devtools_device_types_command_input_form(webinterface, request, session, 'add',
                                                                  data, device_type_results['data'],
                                                                  command_results['data'],
                                                                  input_type_results['data'],
                                                                  "Associate input type to command"))

            msg = {
                'header': 'Input Associated',
                'label': 'Input has been associated to the command successfully',
                'description': '<p>The input has been associated to the device type command.</p>'
                               '<p>Continue to <ul>'
                               '<li><a href="/devtools/config/device_types/index">Device types index</a></li>'
                               '<li><a href="/devtools/config/device_types/%s/details">View the device type</a></li>'
                               '<li><strong><a href="/devtools/config/device_types/%s/command/%s/details">View device type command</a></strong></li>'
                               '</p>' % (device_type_id, device_type_id, command_id)
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route(
            '/config/device_types/<string:device_type_id>/command/<string:command_id>/input/<string:input_type_id>/details',
            methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_command_input_details_get(webinterface, request, session, device_type_id,
                                                                 command_id, input_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            device_command_input_results = yield webinterface._YomboAPI.request('GET',
                                                                                '/v1/device_command_input?device_type_id=%s&command_id=%s&input_type_id=%s' % (
                                                                                device_type_id, command_id,
                                                                                input_type_id))
            if device_command_input_results['code'] != 200:
                webinterface.add_alert(device_command_input_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/command_input_details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
            device_type_id, command_id),
                                        "Command - %s" % command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/edit_input" % (
            device_type_id, command_id),
                                        "Input Command Details")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    command=command_results['data'],
                                    command_input=device_command_input_results['data'][0],
                                    input_type=input_type_results['data'],
                                    ))

        @webapp.route(
            '/config/device_types/<string:device_type_id>/command/<string:command_id>/input/<string:input_type_id>/edit_input',
            methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_command_input_edit_get(webinterface, request, session, device_type_id,
                                                              command_id, input_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            device_command_input_results = yield webinterface._YomboAPI.request('GET',
                                                                                '/v1/device_command_input?device_type_id=%s&command_id=%s&input_type_id=%s' % (
                                                                                device_type_id, command_id,
                                                                                input_type_id))
            if device_command_input_results['code'] != 200:
                webinterface.add_alert(device_command_input_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            data = {
                'live_update': webinterface.request_get_default(request, 'live_update', ""),
                'notes': webinterface.request_get_default(request, 'notes', ""),
                'value_required': webinterface.request_get_default(request, 'value_required', ""),
                'value_min': webinterface.request_get_default(request, 'value_min', ""),
                'value_max': webinterface.request_get_default(request, 'value_max', ""),
                'value_casing': webinterface.request_get_default(request, 'value_casing', "none"),
                'encryption': webinterface.request_get_default(request, 'encryption', "nosuggestion"),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
            device_type_id, command_id),
                                        "Command - %s" % command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/edit_input" % (
            device_type_id, command_id),
                                        "Edit input")
            returnValue(page_devtools_device_types_command_input_form(webinterface, request, session, 'add',
                                                                      device_command_input_results['data'][0],
                                                                      device_type_results['data'],
                                                                      command_results['data'],
                                                                      input_type_results['data'],
                                                                      "Associate input type to command"))

        @webapp.route(
            '/config/device_types/<string:device_type_id>/command/<string:command_id>/input/<string:input_type_id>/edit_input',
            methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_command_input_edit_post(webinterface, request, session, device_type_id,
                                                               command_id, input_type_id):
            data = {
                'live_update': webinterface.request_get_default(request, 'live_update', ""),
                'notes': webinterface.request_get_default(request, 'notes', ""),
                'value_required': webinterface.request_get_default(request, 'value_required', ""),
                'value_min': webinterface.request_get_default(request, 'value_min', ""),
                'value_max': webinterface.request_get_default(request, 'value_max', ""),
                'value_casing': webinterface.request_get_default(request, 'value_casing', "none"),
                'encryption': webinterface.request_get_default(request, 'encryption', "nosuggestion"),
            }

            results = yield webinterface._DeviceTypes.dev_command_input_edit(device_type_id, command_id, input_type_id,
                                                                             data)

            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(
                    page_devtools_device_types_command_input_form(webinterface, request, session, 'add',
                                                                  data, device_type_results['data'][0],
                                                                  command_results['data'],
                                                                  input_type_results['data'],
                                                                  "Associate input type to command"))

            msg = {
                'header': 'Input Associated',
                'label': 'Input has been associated to the command successfully',
                'description': '<p>The input has been associated to the device type command.</p>'
                               '<p>Continue to <ul>'
                               '<li><a href="/devtools/config/device_types/index">Device types index</a></li>'
                               '<li><a href="/devtools/config/device_types/%s/details">View the device type</a></li>'
                               '<li><strong><a href="/devtools/config/device_types/%s/command/%s/details">View device type command</a></strong></li>'
                               '</p>' % (device_type_id, device_type_id, command_id)
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
            device_type_id, command_id),
                                        "Command - %s" % command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/edit_input" % (
            device_type_id, command_id),
                                        "Edit input")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        def page_devtools_device_types_command_input_form(webinterface, request, session, action_type, command_input,
                                                          device_type, command, input_type, header_label):
            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/command_input_form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               device_type=device_type,
                               command=command,
                               command_input=command_input,
                               input_type=input_type,
                               action_type=action_type,
                               )

        @webapp.route(
            '/config/device_types/<string:device_type_id>/command/<string:command_id>/input/<string:input_type_id>/remove_input',
            methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_command_delete_input_get(webinterface, request, session, device_type_id,
                                                                command_id, input_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/command_input_remove.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/device_types/%s/command/%s/details" % (
                                        device_type_id, command_id),
                                        command_results['data']['label'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/device_types/%s/command/%s/input/" % (
                                        device_type_id, command_id),
                                        "Remove Input")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    input_type=input_type_results['data'],
                                    command=command_results['data'],

                                    )
                        )

        @webapp.route(
            '/config/device_types/<string:device_type_id>/command/<string:command_id>/input/<string:input_type_id>/remove_input',
            methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_command_delete_input_post(webinterface, request, session, device_type_id,
                                                                 command_id, input_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            if confirm != "remove":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the device type.',
                                       'warning')
                returnValue(webinterface.redirect(request,
                                                  '/devtools/config/device_types/%s/command/%s/input/%s/remove_input' % (
                                                  device_type_id, command_id, input_type_id)))

            results = yield webinterface._DeviceTypes.dev_command_input_remove(device_type_id, command_id,
                                                                               input_type_id)
            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            if command_results['code'] != 200:
                webinterface.add_alert(command_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            msg = {
                'header': 'Device Type Deleted',
                'label': 'Device Type deleted successfully',
                'description': '<p>The device type has been deleted.</p>'
                               '<p>Continue to:'
                               '<ul>'
                               '<li><a href="/devtools/config/device_types/index">Device type index</a></li>'
                               '<li><a href="/devtools/config/device_types/%s/details">View device type</a></li>'
                               '<li><strong><a href="/devtools/config/device_types/%s/command/%s/details">View the device type command</a></strong></li>'
                               '</ul></p>' % (device_type_id, device_type_id, command_id)
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/device_types/%s/command/%s/details" % (
                                        device_type_id, command_id),
                                        command_results['data']['label'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/device_types/%s/command/%s/input/" % (
                                        device_type_id, command_id),
                                        "Remove Input")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/device_types/<string:device_type_id>/details', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_details_get(webinterface, request, session, device_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            category_results = yield webinterface._YomboAPI.request('GET',
                                                                    '/v1/category/%s' % device_type_results['data'][
                                                                        'category_id'])
            if category_results['code'] != 200:
                webinterface.add_alert(category_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            device_type_commands_results = yield webinterface._YomboAPI.request('GET',
                                                                                '/v1/device_type_command/%s' % device_type_id)
            if device_type_commands_results['code'] != 200:
                webinterface.add_alert(device_type_commands_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/details.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    category=category_results['data'],
                                    device_type_commands=device_type_commands_results['data']
                                    )
                        )

        @webapp.route('/config/device_types/<string:device_type_id>/delete', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_delete_get(webinterface, request, session, device_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/delete.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/delete" % device_type_id, "Delete")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    )
                        )

        @webapp.route('/config/device_types/<string:device_type_id>/delete', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_delete_post(webinterface, request, session, device_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the device type.',
                                       'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            results = yield webinterface._DeviceTypes.dev_device_type_delete(device_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            msg = {
                'header': 'Device Type Deleted',
                'label': 'Device Type deleted successfully',
                'description': '<p>The device type has been deleted.</p>'
                               '<p>Continue to:'
                               '<ul>'
                               '<li><a href="/devtools/config/device_types/index">Device type index</a></li>'
                               '<li><stron><a href="/devtools/config/device_types/%s/details">Ciew the device type</a></strong></li>'
                               '</ul></p>' % device_type_id,
            }

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_types/%s' % device_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if device_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                            device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/delete" % device_type_id,
                                            "Delete")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/device_types/<string:device_type_id>/disable', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_disable_get(webinterface, request, session, device_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/disable.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/disable" % device_type_id, "Disable")

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    )
                        )

        @webapp.route('/config/device_types/<string:device_type_id>/disable', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_disable_post(webinterface, request, session, device_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the device type.',
                                       'warning')
                returnValue(
                    webinterface.redirect(request, '/devtools/config/device_types/%s/device_type_id' % device_type_id))

            results = yield webinterface._DeviceTypes.dev_device_type_disable(device_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            msg = {
                'header': 'Device Type Disabled',
                'label': 'Device Type disabled successfully',
                'description': '<p>The device type has been disabled.</p><p>Continue to <a href="/devtools/config/device_types/index">device types index</a> or <a href="/devtools/config/device_types/%s/details">view the device type</a>.</p>' % device_type_id,
            }

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            if device_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                            device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/disable" % device_type_id,
                                            "Disable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/device_types/<string:device_type_id>/enable', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_enable_get(webinterface, request, session, device_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/enable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/disable" % device_type_id, "Disable")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    )
                        )

        @webapp.route('/config/device_types/<string:device_type_id>/enable', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_enable_post(webinterface, request, session, device_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the device type.',
                                       'warning')
                returnValue(
                    webinterface.redirect(request, '/devtools/config/device_types/%s/device_type_id' % device_type_id))

            results = yield webinterface._DeviceTypes.dev_device_type_enable(device_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/%s/details' % device_type_id))

            msg = {
                'header': 'Device Type Enabled',
                'label': 'Device Type enabled successfully',
                'description': '<p>The device type has been enabled.</p><p>Continue to <a href="/devtools/config/device_types/index">device types index</a> or <a href="/devtools/config/device_types/%s/details">view the device type</a>.</p>' % device_type_id,
            }

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            if device_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                            device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/enable" % device_type_id,
                                            "Enable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/device_types/add', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_add_get(webinterface, request, session):
            category_results = yield webinterface._YomboAPI.request('GET', '/v1/category?category_type=device_type')
            if category_results['code'] != 200:
                webinterface.add_alert(category_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            data = {
                'category_id': webinterface.request_get_default(request, 'category_id', ""),
                'platform': webinterface.request_get_default(request, 'platform', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'public': int(webinterface.request_get_default(request, 'public', 0)),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/add", "Add")
            returnValue(
                page_devtools_devicestypes_form(webinterface, request, session, 'add', data, category_results['data'],
                                                "Add Device Type"))

        @webapp.route('/config/device_types/add', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_add_post(webinterface, request, session):
            data = {
                'category_id': webinterface.request_get_default(request, 'category_id', ""),
                'platform': webinterface.request_get_default(request, 'platform', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'public': int(webinterface.request_get_default(request, 'public', 0)),
            }

            device_type_results = yield webinterface._DeviceTypes.dev_device_type_add(data)

            if device_type_results['status'] == 'failed':
                webinterface.add_alert(device_type_results['apimsghtml'], 'warning')
                category_results = yield webinterface._YomboAPI.request('GET', '/v1/category?category_type=device_type')
                if category_results['code'] != 200:
                    webinterface.add_alert(category_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))
                returnValue(
                    page_devtools_devicestypes_form(webinterface, request, session, 'add', data,
                                                    category_results['data'],
                                                    "Add Device Type"))

            msg = {
                'header': 'Device Type Added',
                'label': 'Device typ added successfully',
                'description': '<p>The device type has been added. If you have requested this device type to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/config/device_types/index">device types index</a> or <a href="/devtools/config/device_types/%s/details">view the new device type</a>.</p>' %
                               device_type_results['device_type_id'],
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/add", "Add")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/device_types/<string:device_type_id>/edit', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_edit_get(webinterface, request, session, device_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))
            category_results = yield webinterface._YomboAPI.request('GET', '/v1/category?category_type=device_type')
            if category_results['code'] != 200:
                webinterface.add_alert(category_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/edit" % device_type_id, "Edit")

            returnValue(
                page_devtools_devicestypes_form(webinterface, request, session, 'edit', device_type_results['data'],
                                                category_results['data'],
                                                "Edit Device Type: %s" % device_type_results['data']['label']))

        @webapp.route('/config/device_types/<string:device_type_id>/edit', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_edit_post(webinterface, request, session, device_type_id):
            data = {
                'category_id': webinterface.request_get_default(request, 'category_id', ""),
                'platform': webinterface.request_get_default(request, 'platform', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                #                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'public': int(webinterface.request_get_default(request, 'public', 0)),
            }

            device_type_results = yield webinterface._DeviceTypes.dev_device_type_edit(device_type_id, data)

            data['machine_label'] = request.args.get('machine_label_hidden')[0]

            if device_type_results['status'] == 'failed':
                category_results = yield webinterface._YomboAPI.request('GET', '/v1/category?category_type=device_type')
                if category_results['code'] != 200:
                    webinterface.add_alert(category_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

                webinterface.add_alert(device_type_results['apimsghtml'], 'warning')
                returnValue(page_devtools_devicestypes_form(webinterface, request, session, 'edit', data,
                                                            category_results['data'],
                                                            "Edit Device Type: %s" % data['label']))

                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            msg = {
                'header': 'Device Type Updated',
                'label': 'Device typ updated successfully',
                'description': '<p>The device type has been updated. If you have requested this device type to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/config/device_types/index">device types index</a> or <a href="/devtools/config/device_types/%s/details">view the new device type</a>.</p>' %
                               device_type_results['device_type_id'],
            }

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            if device_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                            device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/enable" % device_type_id,
                                            "Enable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        def page_devtools_devicestypes_form(webinterface, request, session, action_type, device_type, categories,
                                            header_label):
            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               device_type=device_type,
                               categories=categories,
                               action_type=action_type,
                               )

        @webapp.route('/config/device_types/<string:device_type_id>/variables', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_device_types_variables_get(webinterface, request, session, device_type_id):
            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
                webinterface.add_alert(device_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/device_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/variable_details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/variables" % device_type_id,
                                        "Variable Groups")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    )
                        )

        ####################################
        # Input Types
        ####################################
        @webapp.route('/config/input_types/index')
        @require_auth()
        @run_first()
        def page_devtools_input_types_index_get(webinterface, request, session):
            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/input_types/index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/config/input_types/<string:input_type_id>/details', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_input_types_details_get(webinterface, request, session, input_type_id):
            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

            category_results = yield webinterface._YomboAPI.request('GET',
                                                                    '/v1/category/%s' % input_type_results['data'][
                                                                        'category_id'])
            if category_results['code'] != 200:
                webinterface.add_alert(category_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/input_types/details.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                        input_type_results['data']['label'])

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    input_type=input_type_results['data'],
                                    category=category_results['data'],
                                    )
                        )

        @webapp.route('/config/input_types/<string:input_type_id>/delete', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_input_types_delete_get(webinterface, request, session, input_type_id):
            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/input_types/delete.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                        input_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/delete" % input_type_id, "Delete")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    input_type=input_type_results['data'],
                                    )
                        )

        @webapp.route('/config/input_types/<string:input_type_id>/delete', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_input_types_delete_post(webinterface, request, session, input_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the input type.',
                                       'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id))

            results = yield webinterface._InputTypes.dev_input_type_delete(input_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id))

            msg = {
                'header': 'Input Type Deleted',
                'label': 'Input Type deleted successfully',
                'description': '<p>The input type has been deleted.</p><p>Continue to <a href="/devtools/config/input_types/index">input type index</a> or <a href="/devtools/config/input_types/%s/details">view the input type</a>.</p>' % input_type_id,
            }

            input_type_results = yield webinterface._YomboAPI.request('GET',
                                                                      '/v1/input_types/%s' % input_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            if input_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                            input_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/delete" % input_type_id, "Delete")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/input_types/<string:input_type_id>/disable', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_input_types_disable_get(webinterface, request, session, input_type_id):
            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/input_types/disable.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                        input_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/disable" % input_type_id, "Disable")

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    input_type=input_type_results['data'],
                                    )
                        )

        @webapp.route('/config/input_types/<string:input_type_id>/disable', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_input_types_disable_post(webinterface, request, session, input_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id))

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the input type.',
                                       'warning')
                returnValue(
                    webinterface.redirect(request, '/devtools/config/input_types/%s/input_type_id' % input_type_id))

            results = yield webinterface._InputTypes.dev_input_type_disable(input_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id))

            msg = {
                'header': 'Input Type Disabled',
                'label': 'Input Type disabled successfully',
                'description': '<p>The input type has been disabled.</p><p>Continue to <a href="/devtools/config/input_types/index">input types index</a> or <a href="/devtools/config/input_types/%s/details">view the input type</a>.</p>' % input_type_id,
            }

            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            if input_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                            input_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/disable" % input_type_id,
                                            "Disable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/input_types/<string:input_type_id>/enable', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_input_types_enable_get(webinterface, request, session, input_type_id):
            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/input_types/enable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                        input_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/disable" % input_type_id, "Disable")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    input_type=input_type_results['data'],
                                    )
                        )

        @webapp.route('/config/input_types/<string:input_type_id>/enable', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_input_types_enable_post(webinterface, request, session, input_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id))

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the input type.',
                                       'warning')
                returnValue(
                    webinterface.redirect(request, '/devtools/config/input_types/%s/input_type_id' % input_type_id))

            results = yield webinterface._InputTypes.dev_input_type_enable(input_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id))

            msg = {
                'header': 'Input Type Enabled',
                'label': 'Input Type enabled successfully',
                'description': '<p>The input type has been enabled.</p><p>Continue to <a href="/devtools/config/input_types/index">input types index</a> or <a href="/devtools/config/input_types/%s/details">view the input type</a>.</p>' % input_type_id,
            }

            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            if input_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                            input_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/enable" % input_type_id, "Enable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/input_types/add', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_input_types_add_get(webinterface, request, session):
            category_results = yield webinterface._YomboAPI.request('GET', '/v1/category?category_type=input_type')
            if category_results['code'] != 200:
                webinterface.add_alert(category_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

            data = {
                'category_id': webinterface.request_get_default(request, 'category_id', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'input_regex': webinterface.request_get_default(request, 'input_regex', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'public': int(webinterface.request_get_default(request, 'public', 0)),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/add", "Add")
            returnValue(page_devtools_input_types_form(webinterface, request, session, 'add', data,
                                                       category_results['data'], "Add Input Type"))

        @webapp.route('/config/input_types/add', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_input_types_add_post(webinterface, request, session):
            data = {
                'category_id': webinterface.request_get_default(request, 'category_id', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'input_regex': webinterface.request_get_default(request, 'input_regex', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'public': int(webinterface.request_get_default(request, 'public', 0)),
            }

            input_type_results = yield webinterface._InputTypes.dev_input_type_add(data)

            if input_type_results['status'] == 'failed':
                webinterface.add_alert(input_type_results['apimsghtml'], 'warning')
                category_results = yield webinterface._YomboAPI.request('GET',
                                                                        '/v1/category?category_type=input_type')
                if category_results['code'] != 200:
                    webinterface.add_alert(category_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))
                returnValue(
                    page_devtools_input_types_form(webinterface, request, session, 'add', data,
                                                   category_results['data'],
                                                   "Add Input Type"))

            msg = {
                'header': 'Input Type Added',
                'label': 'Input typ added successfully',
                'description': '<p>The input type has been added. If you have requested this input type to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/config/input_types/index">input types index</a> or <a href="/devtools/config/input_types/%s/details">view the new input type</a>.</p>' %
                               input_type_results['input_type_id'],
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/add", "Add")
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/input_types/<string:input_type_id>/edit', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_input_types_edit_get(webinterface, request, session, input_type_id):
            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

            category_results = yield webinterface._YomboAPI.request('GET', '/v1/category?category_type=input_type')
            if category_results['code'] != 200:
                webinterface.add_alert(category_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                        input_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/edit" % input_type_id, "Edit")

            returnValue(
                page_devtools_input_types_form(webinterface, request, session, 'edit', input_type_results['data'],
                                               category_results['data'],
                                               "Edit Input Type: %s" % input_type_results['data']['label']))

        @webapp.route('/config/input_types/<string:input_type_id>/edit', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_input_types_edit_post(webinterface, request, session, input_type_id):
            data = {
                'id': input_type_id,
                'category_id': webinterface.request_get_default(request, 'category_id', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'input_regex': webinterface.request_get_default(request, 'input_regex', 1),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'public': int(webinterface.request_get_default(request, 'public', 0)),
            }

            dev_input_type_results = yield webinterface._InputTypes.dev_input_type_edit(input_type_id, data)

            data['machine_label'] = request.args.get('machine_label_hidden')[0]

            if dev_input_type_results['status'] == 'failed':
                input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
                if input_type_results['code'] != 200:
                    webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

                category_results = yield webinterface._YomboAPI.request('GET',
                                                                        '/v1/category?category_type=input_type')
                if category_results['code'] != 200:
                    webinterface.add_alert(category_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                            input_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/edit" % input_type_id, "Edit")

                webinterface.add_alert(dev_input_type_results['apimsghtml'], 'warning')
                returnValue(page_devtools_input_types_form(webinterface, request, session, 'edit', data,
                                                           category_results['data'],
                                                           "Edit Input Type: %s" % data['label']))

                returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

            msg = {
                'header': 'Input Type Updated',
                'label': 'Input typ updated successfully',
                'description': '<p>The input type has been updated. If you have requested this input type to be made public, please allow a few days for Yombo review.</p>'
                               '<p>Continue to <a href="/devtools/config/input_types/index">input types index</a> or <a href="/devtools/config/input_types/%s/details">view the updated input type</a>.</p>' %
                               input_type_id,
            }

            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            if input_type_results['code'] == 200:
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                            input_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/enable" % input_type_id, "Enable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types", True)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        def page_devtools_input_types_form(webinterface, request, session, action_type, input_type, categories,
                                           header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/input_types/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               input_type=input_type,
                               categories=categories,
                               action_type=action_type,
                               display_type=action_type
                               )

        ####################################
        # Modules
        ####################################
        @webapp.route('/config/modules/index')
        @require_auth()
        @run_first()
        def page_devtools_modules_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/modules/index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/config/modules/<string:module_id>/details', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_modules_details_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET',
                                                                  '/v1/module/%s?_expand=device_types' % module_id)
            if module_results['code'] != 200:
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
        @run_first()
        @inlineCallbacks
        def page_devtools_modules_delete_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
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
        @run_first()
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
            if module_api_results['code'] == 200:
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
        @run_first()
        @inlineCallbacks
        def page_devtools_modules_disable_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/modules/disable.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    module=module_results['data'],
                                    )
                        )

        @webapp.route('/config/modules/<string:module_id>/disable', methods=['POST'])
        @require_auth()
        @run_first()
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

            if module_results['code'] == 200:
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
        @run_first()
        @inlineCallbacks
        def page_devtools_modules_enable_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/modules/enable.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    module=module_results['data'],
                                    )
                        )

        @webapp.route('/config/modules/<string:module_id>/enable', methods=['POST'])
        @require_auth()
        @run_first()
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
        @run_first()
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
        @run_first()
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
        @run_first()
        @inlineCallbacks
        def page_devtools_modules_edit_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
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
        @run_first()
        @inlineCallbacks
        def page_devtools_modules_edit_post(webinterface, request, session, module_id):
            results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if results['code'] != 200:
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
        @run_first()
        @inlineCallbacks
        def page_devtools_modules_device_types_index_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
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
        @run_first()
        @inlineCallbacks
        def page_devtools_modules_device_types_add_get(webinterface, request, session, module_id, device_type_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
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
        @run_first()
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
        @run_first()
        @inlineCallbacks
        def page_devtools_modules_device_types_remove_get(webinterface, request, session, module_id, device_type_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
                webinterface.add_alert(module_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/modules/index'))

            device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            if device_type_results['code'] != 200:
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
        @run_first()
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
        @run_first()
        @inlineCallbacks
        def page_devtools_modules_variables_get(webinterface, request, session, module_id):
            module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            if module_results['code'] != 200:
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

        ####################################
        # Variables
        ####################################
        @inlineCallbacks
        def variable_group_breadcrumbs(webinterface, request, parent_id, parent_type):
            if parent_type == 'module':
                module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % parent_id)
                root_breadcrumb(webinterface, request)

                if module_results['code'] == 200:
                    webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules")
                    webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % parent_id,
                                                module_results['data']['label'])
                    webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/variables" % parent_id,
                                                "Variable Groups", True)
                else:
                    webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules", True)

                returnValue(module_results)
            elif parent_type == 'device_type':
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % parent_id)
                root_breadcrumb(webinterface, request)

                if device_type_results['code'] == 200:
                    webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
                    webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % parent_id,
                                                device_type_results['data']['label'])
                    webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/variables" % parent_id,
                                                "Variable Groups", True)
                else:
                    webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Modules", True)
                returnValue(device_type_results)

        @webapp.route('/config/variables/group/<string:group_id>/details', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_group_details_get(webinterface, request, session, group_id):
            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/by_group/%s' % group_id)
            if field_results['code'] != 200:
                webinterface.add_alert(field_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))
                # returnValue(webinterface.redirect(request, '/modules/%s/variables' % module_id))

            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      group_results['data']['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            if parent['code'] != 200:
                webinterface.add_alert(['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/group_details.html')
            # root_breadcrumb(webinterface, request)
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    parent=parent['data'],
                                    group=group_results['data'],
                                    fields=field_results['data']
                                    )
                        )

        @webapp.route('/config/variables/group/add/<string:parent_id>/<string:parent_type>', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_group_add_get(webinterface, request, session, parent_id, parent_type):
            data = {
                'relation_id': parent_id,
                'relation_type': parent_type,
                'group_machine_label': webinterface.request_get_default(request, 'group_machine_label', ""),
                'group_label': webinterface.request_get_default(request, 'group_label', ""),
                'group_description': webinterface.request_get_default(request, 'group_description', ""),
                'group_weight': webinterface.request_get_default(request, 'group_weight', 0),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
            }

            parent = yield variable_group_breadcrumbs(webinterface, request, parent_id, parent_type)
            webinterface.add_breadcrumb(request, "/", "Add Variable")
            if parent['code'] != 200:
                webinterface.add_alert(['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            returnValue(
                page_devtools_variables_group_form(webinterface, request, session, parent_type, parent['data'], data,
                                                   "Add Group Variable to: %s" % parent['data']['label']))

        @webapp.route('/config/variables/group/add/<string:parent_id>/<string:parent_type>', methods=['POST'])
        @require_auth()
        @run_first()
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
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            dev_group_results = yield webinterface._Variables.dev_group_add(data)
            if dev_group_results['status'] == 'failed':
                webinterface.add_alert(dev_group_results['apimsghtml'], 'warning')
                returnValue(
                    page_devtools_variables_group_form(webinterface, request, session, parent_type, parent['data'],
                                                       data, "Add Group Variable to: %s" % parent['data']['label']))

            msg = {
                'header': 'Variable Group Added',
                'label': 'Variable group added successfully',
                'description': ''
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            if parent_type == 'module':
                msg[
                    'description'] = '<p>Variable group has beed added.</p><p>Continue to:<ul><li><a href="/devtools/config/modules/index">modules index</a></li><li><a href="/devtools/config/modules/%s/details">view the module</a></li><li><a href="/devtools/config/modules/%s/variables"> view module variables</a></li></ul></p>' % (
                parent_id, parent_id)
            elif parent_type == 'device_type':
                msg[
                    'description'] = '<p>Variable group has beed added.</p><p>Continue to:<ul><li><a href="/devtools/config/device_types/index">device types index</a></li><li><a href="/devtools/config/device_types/%s/details">view the device type: %s</a></li><li><a href="/devtools/config/device_types/%s/variables"> view device type variables</a></li></ul></p>' % (
                parent_id, parent['data']['label'], parent_id)

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/variables/group/<string:group_id>/edit', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_group_edit_get(webinterface, request, session, group_id):
            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            parent_type = group_results['data']['relation_type']
            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      parent_type)
            webinterface.add_breadcrumb(request, "/", "Edit Variable")
            if parent['code'] != 200:
                webinterface.add_alert(['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            returnValue(page_devtools_variables_group_form(webinterface, request, session, parent_type, parent['data'],
                                                           group_results['data'],
                                                           "Edit Group Variable: %s" % group_results['data'][
                                                               'group_label']))

        @webapp.route('/config/variables/group/<string:group_id>/edit', methods=['POST'])
        @require_auth()
        @run_first()
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
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            parent_type = group_results['data']['relation_type']
            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      parent_type)
            webinterface.add_breadcrumb(request, "/", "Edit Variable")
            if parent['code'] != 200:
                webinterface.add_alert(['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            dev_group_results = yield webinterface._Variables.dev_group_edit(group_id, data)
            if dev_group_results['status'] == 'failed':
                webinterface.add_alert(dev_group_results['apimsghtml'], 'warning')
                returnValue(
                    page_devtools_variables_group_form(webinterface, request, session, parent_type, parent['data'],
                                                       data, "Add Group Variable to: %s" % parent['data']['label']))

            msg = {
                'header': 'Variable Group Edited',
                'label': 'Variable group edited successfully',
                'description': ''
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            if parent_type == 'module':
                msg[
                    'description'] = '<p>Variable group has beed edited.</p><p>Continue to:<ul><li><a href="/devtools/config/modules/index">modules index</a></li><li><a href="/devtools/config/modules/%s/details">view the module</a></li><li><a href="/devtools/config/modules/%s/variables"> view module variables</a></li></ul></p>' % (
                parent['data']['id'], parent['data']['id'])
            elif parent_type == 'device_type':
                msg[
                    'description'] = '<p>Variable group has beed edited.</p><p>Continue to:<ul><li><a href="/devtools/config/device_types/index">device types index</a></li><li><a href="/devtools/config/device_types/%s/details">view the device type: %s</a></li><li><a href="/devtools/config/device_types/%s/variables"> view device type variables</a></li></ul></p>' % (
                parent['data']['id'], parent['data']['label'], parent['data']['id'])

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        def page_devtools_variables_group_form(webinterface, request, session, parent_type, parent, group,
                                               header_label):
            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/group_form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               parent_type=parent_type,
                               parent=parent,
                               group=group,
                               )

        @webapp.route('/config/variables/group/<string:group_id>/enable', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_group_enable_get(webinterface, request, session, group_id):
            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            data = group_results['data']
            parent = yield variable_group_breadcrumbs(webinterface, request, data['relation_id'], data['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Enable")

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/group_enable.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    var_group=data,
                                    parent=parent,
                                    )
                        )

        @webapp.route('/config/variables/group/<string:group_id>/enable', methods=['post'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_group_enable_post(webinterface, request, session, group_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the variable group.',
                                       'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/variables/group/%s/enable' % group_id))

            dev_group_results = yield webinterface._Variables.dev_group_enable(group_id)
            if dev_group_results['status'] == 'failed':
                webinterface.add_alert(dev_group_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/variables/group/%s/enable' % group_id))

            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            data = group_results['data']
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            parent = yield variable_group_breadcrumbs(webinterface, request, data['relation_id'], data['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Enable")

            msg = {
                'header': 'Variable Group Enabled',
                'label': 'Variable Group enabled successfully',
                'description': '',
            }

            if data['relation_type'] == 'module':
                msg['description'] = '<p>Variable group has beed enabled.</p>' \
                                     '<p>Continue to:' \
                                     '<ul>' \
                                     '<li><a href="/devtools/config/modules/index">Modules index</a></li>' \
                                     '<li><a href="/devtools/config/modules/%s/details">View the module</a></li>' \
                                     '<li><strong><a href="/devtools/config/modules/%s/variables">View module variables</a></strong></li>' \
                                     '</ul>' \
                                     '</p>' % (data['relation_id'], data['relation_id'])
            elif data['relation_type'] == 'device_type':
                msg['description'] = '<p>Variable group has beed enabled.</p>' \
                                     '<p>Continue to:<ul>' \
                                     '<li><a href="/devtools/config/device_types/index">Device types index</a></li>' \
                                     '<li><a href="/devtools/config/device_types/%s/details">View the device type: %s</a></li>' \
                                     '<li><strong><a href="/devtools/config/device_types/%s/variables">View device type variables</a></strong></li>' \
                                     '</ul>' \
                                     '</p>' % (data['relation_id'], parent['data']['label'], data['relation_id'])

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/variables/group/<string:group_id>/disable', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_group_disable_get(webinterface, request, session, group_id):
            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            data = group_results['data']
            parent = yield variable_group_breadcrumbs(webinterface, request, data['relation_id'], data['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Disable")

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/group_disable.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    var_group=data,
                                    parent=parent,
                                    )
                        )

        @webapp.route('/config/variables/group/<string:group_id>/disable', methods=['post'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_group_disable_post(webinterface, request, session, group_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the variable group.',
                                       'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/variables/group/%s/disable' % group_id))

            dev_group_results = yield webinterface._Variables.dev_group_disable(group_id)
            if dev_group_results['status'] == 'failed':
                webinterface.add_alert(dev_group_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/variables/group/%s/disable' % group_id))

            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            data = group_results['data']
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            parent = yield variable_group_breadcrumbs(webinterface, request, data['relation_id'], data['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Disable")

            msg = {
                'header': 'Variable Group Disabled',
                'label': 'Variable Group deleted successfully',
                'description': 'disable'
            }

            if data['relation_type'] == 'module':
                msg['description'] = '<p>Variable group has beed disabled.</p>' \
                                     '<p>Continue to:' \
                                     '<ul>' \
                                     '<li><a href="/devtools/config/modules/index">Modules index</a></li>' \
                                     '<li><a href="/devtools/config/modules/%s/details">View the module</a></li>' \
                                     '<li><strong><a href="/devtools/config/modules/%s/variables">View module variables</a></strong></li>' \
                                     '</ul>' \
                                     '</p>' % (data['relation_id'], data['relation_id'])
            elif data['relation_type'] == 'device_type':
                msg['description'] = '<p>Variable group has beed disabled.</p>' \
                                     '<p>Continue to:<ul>' \
                                     '<li><a href="/devtools/config/device_types/index">Device types index</a></li>' \
                                     '<li><a href="/devtools/config/device_types/%s/details">View the device type: %s</a></li>' \
                                     '<li><strong><a href="/devtools/config/device_types/%s/variables">View device type variables</a></strong></li>' \
                                     '</ul>' \
                                     '</p>' % (data['relation_id'], parent['data']['label'], data['relation_id'])

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/variables/group/<string:group_id>/delete', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_group_delete_get(webinterface, request, session, group_id):
            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            data = group_results['data']
            parent = yield variable_group_breadcrumbs(webinterface, request, data['relation_id'], data['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Delete")

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/group_delete.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    var_group=data,
                                    parent=parent,
                                    )
                        )

        @webapp.route('/config/variables/group/<string:group_id>/delete', methods=['post'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_group_delete_post(webinterface, request, session, group_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the variable group.',
                                       'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/variables/group/%s/delete' % group_id))

            dev_group_results = yield webinterface._Variables.dev_group_delete(group_id)
            if dev_group_results['status'] == 'failed':
                webinterface.add_alert(dev_group_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/variables/group/%s/details' % group_id))

            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            data = group_results['data']
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            parent = yield variable_group_breadcrumbs(webinterface, request, data['relation_id'], data['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'], False)
            webinterface.add_breadcrumb(request, "/", "Deleted")

            msg = {
                'header': 'Variable Group Deleted',
                'label': 'Variable Group deleted successfully',
                'description': '',
            }

            if data['relation_type'] == 'module':
                msg['description'] = '<p>Variable group has beed deleted.</p>' \
                                     '<p>Continue to:' \
                                     '<ul>' \
                                     '<li><a href="/devtools/config/modules/index">Modules index</a></li>' \
                                     '<li><a href="/devtools/config/modules/%s/details">View the module</a></li>' \
                                     '<li><strong><a href="/devtools/config/modules/%s/variables">View module variables</a></strong></li>' \
                                     '</ul>' \
                                     '</p>' % (data['relation_id'], data['relation_id'])
            elif data['relation_type'] == 'device_type':
                msg['description'] = '<p>Variable group has beed disabled.</p>' \
                                     '<p>Continue to:<ul>' \
                                     '<li><a href="/devtools/config/device_types/index">Device types index</a></li>' \
                                     '<li><a href="/devtools/config/device_types/%s/details">View the device type: %s</a></li>' \
                                     '<li><strong><a href="/devtools/config/device_types/%s/variables">View device type variables</a></strong></li>' \
                                     '</ul>' \
                                     '</p>' % (data['relation_id'], parent['data']['label'], data['relation_id'])

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/variables/group/<string:group_id>/new_field', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_field_add_get(webinterface, request, session, group_id):
            data = {
                'group_id': group_id,
                'field_machine_label': webinterface.request_get_default(request, 'field_machine_label', ""),
                'field_label': webinterface.request_get_default(request, 'field_label', ""),
                'field_description': webinterface.request_get_default(request, 'field_description', ""),
                'field_weight': int(webinterface.request_get_default(request, 'field_weight', 0)),
                'value_min': webinterface.request_get_default(request, 'value_min', ""),
                'value_max': webinterface.request_get_default(request, 'value_max', ""),
                'value_casing': webinterface.request_get_default(request, 'value_casing', ""),
                'value_required': webinterface.request_get_default(request, 'value_required', ""),
                'encryption': webinterface.request_get_default(request, 'encryption', ""),
                'input_type_id': webinterface.request_get_default(request, 'input_type_id', ""),
                'default_value': webinterface.request_get_default(request, 'default_value', ""),
                'field_help_text': webinterface.request_get_default(request, 'field_help_text', ""),
                'multiple': int(webinterface.request_get_default(request, 'multiple', 0)),
            }

            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            parent_type = group_results['data']['relation_type']
            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      parent_type)
            if parent['code'] != 200:
                webinterface.add_alert(['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type?status=1')
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Add Field")
            returnValue(
                page_devtools_variables_field_form(webinterface, request, session, parent, group_results['data'], data,
                                                   input_type_results['data'],
                                                   "Add Field Variable to: %s" % group_results['data']['group_label']))

        @webapp.route('/config/variables/group/<string:group_id>/new_field', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_field_add_post(webinterface, request, session, group_id):
            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            data = {
                'group_id': group_id,
                'field_machine_label': webinterface.request_get_default(request, 'field_machine_label', ""),
                'field_label': webinterface.request_get_default(request, 'field_label', ""),
                'field_description': webinterface.request_get_default(request, 'field_description', ""),
                'field_weight': int(webinterface.request_get_default(request, 'field_weight', 0)),
                'value_min': webinterface.request_get_default(request, 'value_min', ""),
                'value_max': webinterface.request_get_default(request, 'value_max', ""),
                'value_casing': webinterface.request_get_default(request, 'value_casing', ""),
                'value_required': webinterface.request_get_default(request, 'value_required', ""),
                'encryption': webinterface.request_get_default(request, 'encryption', ""),
                'input_type_id': webinterface.request_get_default(request, 'input_type_id', ""),
                'default_value': webinterface.request_get_default(request, 'default_value', ""),
                'field_help_text': webinterface.request_get_default(request, 'field_help_text', ""),
                'multiple': int(webinterface.request_get_default(request, 'multiple', 0)),
            }

            # print data
            for data_key in data.keys():
                # print "key:data %s:%s" % (data_key, data[data_key])
                if isinstance(data[data_key], str) and len(data[data_key]) == 0:
                    del data[data_key]

            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      group_results['data']['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "New Field")
            if parent['code'] != 200:
                webinterface.add_alert(parent['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type?status=1')
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

            dev_field_results = yield webinterface._Variables.dev_field_add(data)
            if dev_field_results['status'] == 'failed':
                webinterface.add_alert(dev_field_results['apimsghtml'], 'warning')
                returnValue(page_devtools_variables_field_form(webinterface, request, session,
                                                               group_results['data']['relation_type'],
                                                               parent['data'], data, input_type_results['data'],
                                                               "Add Group Variable to: %s" % parent['data']['label']))

            msg = {
                'header': 'Variable Field Added',
                'label': 'Variable field added to group successfully',
                'description': ''
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            if group_results['data']['relation_type'] == 'module':
                msg['description'] = '<p>Variable group has beed added.</p>' \
                                     '<p>Continue to:' \
                                     '<ul>' \
                                     '<li><a href="/devtools/config/modules/index">Modules index</a></li>' \
                                     '<li><a href="/devtools/config/modules/%s/details">View the module</a></li>' \
                                     '<li><strong><a href="/devtools/config/modules/%s/variables">View module variables</a></strong></li>' \
                                     '</ul></p>' % (
                                     group_results['data']['relation_id'], group_results['data']['relation_id'])

            elif group_results['data']['relation_type'] == 'device_type':
                msg['description'] = '<p>Variable group has beed added.</p>' \
                                     '<p>Continue to:' \
                                     '<ul>' \
                                     '<li><a href="/devtools/config/device_types/index">Device types index</a></li>' \
                                     '<li><a href="/devtools/config/device_types/%s/details">View the device type: %s</a></li>' \
                                     '<li><strong><a href="/devtools/config/device_types/%s/variables">View device type variables</a></strong></li><' \
                                     '/ul></p>' % (group_results['data']['relation_id'], parent['data']['label'],
                                                   group_results['data']['relation_id'])

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/variables/field/<string:field_id>/delete', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_field_delete_get(webinterface, request, session, field_id):
            field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/%s' % field_id)
            if field_results['code'] != 200:
                webinterface.add_alert(field_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % field_results['data'][
                'group_id'])
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            parent = yield variable_group_breadcrumbs(webinterface, request,
                                                      group_results['data']['relation_id'],
                                                      group_results['data']['relation_type'])

            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Delete Field")

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/field_delete.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    var_field=field_results['data'],
                                    parent=parent,
                                    )
                        )

        @webapp.route('/config/variables/field/<string:field_id>/delete', methods=['post'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_field_delete_post(webinterface, request, session, field_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the variable group.',
                                       'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/variables/feild/%s/delete' % field_id))

            field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/%s' % field_id)
            if field_results['code'] != 200:
                webinterface.add_alert(field_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % field_results['data'][
                'group_id'])
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            dev_group_results = yield webinterface._Variables.dev_field_delete(field_id)
            if dev_group_results['status'] == 'failed':
                webinterface.add_alert(dev_group_results['apimsghtml'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/variables/field/%s/details' % field_id))

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      group_results['data']['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Delete Field")

            msg = {
                'header': 'Variable Field Deleted',
                'label': 'Variable Field deleted successfully',
                'description': '',
            }

            if group_results['data']['relation_type'] == 'module':
                msg['description'] = '<p>Variable field has beed deleted.</p><p>Continue to:' \
                                     '<ul>' \
                                     '<li><a href="/devtools/config/modules/index">Modules index</a></li>' \
                                     '<li><a href="/devtools/config/modules/%s/details">Ciew the module</a></li>' \
                                     '<li><strong><a href="/devtools/config/modules/%s/variables">View module variables</a></strong></li>' \
                                     '</ul>' \
                                     '</p>' % (
                                     group_results['data']['relation_id'], group_results['data']['relation_id'])
            elif group_results['data']['relation_type'] == 'device_type':
                msg['description'] = '<p>Variable field has beed deleted.</p>' \
                                     '<p>Continue to:' \
                                     '<ul>' \
                                     '<li><a href="/devtools/config/device_types/index">Device types index</a></li>' \
                                     '<li><a href="/devtools/config/device_types/%s/details">view the device type: %s</a></li>' \
                                     '<li><strong><a href="/devtools/config/device_types/%s/variables">View device type variables</a></strong></li>' \
                                     '</ul><' \
                                     '/p>' % (group_results['data']['relation_id'], parent['data']['label'],
                                              group_results['data']['relation_id'])

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        @webapp.route('/config/variables/field/<string:field_id>/details', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_field_details_get(webinterface, request, session, field_id):
            field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/%s' % field_id)
            if field_results['code'] != 200:
                webinterface.add_alert(field_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/modules/%s/variables' % field_id))

            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % field_results['data'][
                'group_id'])
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/modules/%s/variables' % field_id))

            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      group_results['data']['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Details")

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/field_details.html')
            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    var_group=group_results['data'],
                                    var_field=field_results['data']
                                    )
                        )

        @webapp.route('/config/variables/field/<string:field_id>/edit', methods=['GET'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_field_edit_get(webinterface, request, session, field_id):
            field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/%s' % field_id)
            if field_results['code'] != 200:
                webinterface.add_alert(field_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % field_results['data'][
                'group_id'])
            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      group_results['data']['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Edit Field")
            if parent['code'] != 200:
                webinterface.add_alert(parent['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type?status=1')
            if input_type_results['code'] != 200:
                webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

            returnValue(page_devtools_variables_field_form(webinterface,
                                                           request,
                                                           session,
                                                           group_results['data']['relation_type'],
                                                           parent['data'], field_results['data'],
                                                           input_type_results['data'],
                                                           "Edit Field Variable: %s" %
                                                           field_results['data']['field_label']))

        @webapp.route('/config/variables/field/<string:field_id>/edit', methods=['POST'])
        @require_auth()
        @run_first()
        @inlineCallbacks
        def page_devtools_variables_field_edit_post(webinterface, request, session, field_id):
            field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/%s' % field_id)
            if field_results['code'] != 200:
                webinterface.add_alert(field_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            group_results = yield webinterface._YomboAPI.request('GET',
                                                                 '/v1/variable/group/%s' % field_results['data'][
                                                                     'group_id'])

            if group_results['code'] != 200:
                webinterface.add_alert(group_results['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            data = {
                'field_machine_label': webinterface.request_get_default(request, 'field_machine_label', ""),
                'field_label': webinterface.request_get_default(request, 'field_label', ""),
                'field_description': webinterface.request_get_default(request, 'field_description', ""),
                'field_weight': int(webinterface.request_get_default(request, 'field_weight', 0)),
                'value_min': webinterface.request_get_default(request, 'value_min', ""),
                'value_max': webinterface.request_get_default(request, 'value_max', ""),
                'value_casing': webinterface.request_get_default(request, 'value_casing', ""),
                'value_required': webinterface.request_get_default(request, 'value_required', ""),
                'encryption': webinterface.request_get_default(request, 'encryption', ""),
                'input_type_id': webinterface.request_get_default(request, 'input_type_id', ""),
                'default_value': webinterface.request_get_default(request, 'default_value', ""),
                'field_help_text': webinterface.request_get_default(request, 'field_help_text', ""),
                'multiple': int(webinterface.request_get_default(request, 'multiple', 0)),
            }

            for key in data.keys():
                if data[key] == "":
                    del data[key]
                elif key in ['value_min', 'value_max']:
                    if data[key] is None or data[key].lower() == "none":
                        del data[key]
                    else:
                        data[key] = int(data[key])

            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      group_results['data']['relation_type'])
            if parent['code'] != 200:
                webinterface.add_alert(parent['content']['html_message'], 'warning')
                returnValue(webinterface.redirect(request, '/devtools/config/index'))

            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Edit Field")

            results = yield webinterface._Variables.dev_field_edit(field_id, data)
            if results['status'] == 'failed':
                input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type?status=1')
                if input_type_results['code'] != 200:
                    webinterface.add_alert(input_type_results['content']['html_message'], 'warning')
                    returnValue(webinterface.redirect(request, '/devtools/config/input_types/index'))

                webinterface.add_alert(results['apimsghtml'], 'warning')
                returnValue(page_devtools_variables_field_form(webinterface,
                                                               request,
                                                               session,
                                                               parent['data'],
                                                               group_results['data']['relation_type'],
                                                               field_results['data'],
                                                               input_type_results['data'],
                                                               "Edit Field Variable: %s" % field_results['data'][
                                                                   'field_label']))

            msg = {
                'header': 'Variable Field Edited',
                'label': 'Variable field edited successfully',
                'description': ''
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            if group_results['data']['relation_type'] == 'module':
                msg['description'] = '<p>Variable group has beed edited.</p>' \
                                     '<p>Continue to:' \
                                     '<ul>' \
                                     '<li><a href="/devtools/config/modules/index">Back to modules index</a></li>' \
                                     '<li><a href="/devtools/config/modules/%s/details">view the module</a></li>' \
                                     '<li><strong><a href="/devtools/config/modules/%s/variables">view module variables</a></strong></li>' \
                                     '</ul></p>' % (
                                         group_results['data']['relation_id'], group_results['data']['relation_id'])

            elif group_results['data']['relation_type'] == 'device_type':
                msg['description'] = '<p>Variable group has beed edited.</p>' \
                                     '<p>Continue to:' \
                                     '<ul>' \
                                     '<li><a href="/devtools/config/device_types/index">device types index</a></li>' \
                                     '<li><a href="/devtools/config/device_types/%s/details">view the device type: %s</a></li>' \
                                     '<li><strong><a href="/devtools/config/device_types/%s/variables">view device type variables</a></strong></li><' \
                                     '/ul></p>' % (group_results['data']['relation_id'], parent['data']['label'],
                                                   group_results['data']['relation_id'])

            returnValue(page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    ))

        def page_devtools_variables_field_form(webinterface, request, session, parent, group, field, input_types,
                                               header_label):
            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/field_form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               parent=parent,
                               group=group,
                               field=field,
                               input_types=input_types,
                               )
