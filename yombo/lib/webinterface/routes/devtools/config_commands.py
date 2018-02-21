from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning

def route_devtools_config_commands(webapp):
    with webapp.subroute("/devtools") as webapp:

        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/devtools/config/", "Config Tools")
            webinterface.add_breadcrumb(request, "/devtools/config/commands/index", "Commands", True)

        @webapp.route('/config/commands/index')
        @require_auth()
        def page_devtools_commands_index(webinterface, request, session):
            page = webinterface.get_template(
                request,
                webinterface._dir + 'pages/devtools/config/commands/index.html')
            root_breadcrumb(webinterface, request)
            return page.render(alerts=webinterface.get_alerts())

        @webapp.route('/config/commands/<string:command_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_details_get(webinterface, request, session, command_id):
            try:
                command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id,
                                                                       session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/commands/index')

            page = webinterface.get_template(
                request,
                webinterface._dir + 'pages/devtools/config/commands/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(
                request,
                "/devtools/config/commands/%s/details" % command_results['data']['id'],
                command_results['data']['label']
            )
            return page.render(alerts=webinterface.get_alerts(),
                               command=command_results['data'],
                               )

        @webapp.route('/config/commands/<string:command_id>/delete', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_delete_get(webinterface, request, session, command_id):
            try:
                command_results = yield webinterface._YomboAPI.request(
                    'GET',
                    '/v1/command/%s' % command_id,
                    session=session['yomboapi_session']
                )
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/commands/index')
            page = webinterface.get_template(
                request,
                webinterface._dir + 'pages/devtools/config/commands/delete.html'
            )
            root_breadcrumb(webinterface, request)

            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                        command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/delete" % command_id, "Delete")
            return page.render(alerts=webinterface.get_alerts(),
                               command=command_results['data'],
                               )

        @webapp.route('/config/commands/<string:command_id>/delete', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_delete_post(webinterface, request, session, command_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request,
                                             '/devtools/config/commands/%s/details' % command_id)

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the command.', 'warning')
                return webinterface.redirect(request,
                                                  '/devtools/config/commands/%s/details' % command_id)

            command_results = yield webinterface._Commands.dev_command_delete(command_id,
                                                                              session=session['yomboapi_session'])

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                return webinterface.redirect(request,
                                                  '/devtools/config/commands/%s/details' % command_id)

            msg = {
                'header': 'Command Deleted',
                'label': 'Command deleted successfully',
                'description': '<p>The command has been deleted.</p><p>Continue to <a href="/devtools/config/commands/index">commands index</a> or <a href="/devtools/config/commands/%s/details">view the command</a>.</p>' % command_id,
            }

            try:
                command_api_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id,
                                                                           session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/commands/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                        command_api_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/delete" % command_id, "Delete")

            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        @webapp.route('/config/commands/<string:command_id>/disable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_disable_get(webinterface, request, session, command_id):
            try:
                command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id,
                                                                       session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/commands/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/commands/disable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                        command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/delete" % command_id, "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                               command=command_results['data'],
                               )

        @webapp.route('/config/commands/<string:command_id>/disable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_disable_post(webinterface, request, session, command_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request,
                                             '/devtools/config/commands/%s/details' % command_id)

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the command.',
                                       'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/commands/%s/details' % command_id)

            command_results = yield webinterface._Commands.dev_command_disable(command_id,
                                                                               session=session['yomboapi_session'])

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/commands/%s/details' % command_id)

            msg = {
                'header': 'Command Disabled',
                'label': 'Command disabled successfully',
                'description': '<p>The command has been disabled.</p><p>Continue to <a href="/devtools/config/commands/index">commands index</a> or <a href="/devtools/config/commands/%s/details">view the command</a>.</p>' % command_id,
            }

            try:
                command_api_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id,
                                                                           session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/commands/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                        command_api_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/delete" % command_id, "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        @webapp.route('/config/commands/<string:command_id>/enable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_enable_get(webinterface, request, session, command_id):
            try:
                command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id,
                                                                       session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/commands/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/config/commands/enable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                        command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/enable", "Enable")
            return page.render(alerts=webinterface.get_alerts(),
                                    command=command_results['data'],
                                    )

        @webapp.route('/config/commands/<string:command_id>/enable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_enable_post(webinterface, request, session, command_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request,
                                             '/devtools/config/commands/%s/details' % command_id)

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the command.', 'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/commands/%s/details' % command_id)

            command_results = yield webinterface._Commands.dev_command_enable(command_id,
                                                                              session=session['yomboapi_session'])

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/commands/%s/details' % command_id)

            msg = {
                'header': 'Command Enabled',
                'label': 'Command enabled successfully',
                'description': '<p>The command has been enabled.</p><p>Continue to <a href="/devtools/config/commands/index">commands index</a> or <a href="/devtools/config/commands/%s/details">view the command</a>.</p>' % command_id,
            }

            try:
                command_api_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id,
                                                                           session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/commands/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                        command_api_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/enable", "Enable")

            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        @webapp.route('/config/commands/add', methods=['GET'])
        @require_auth()
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
            webinterface.add_breadcrumb(request, "/devtools/config/commands/add", "Add")
            return page_devtools_commands_form(webinterface, request, session, 'add', data,
                                               "Add Command")

        @webapp.route('/config/commands/add', methods=['POST'])
        @require_auth()
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

            command_results = yield webinterface._Commands.dev_command_add(data,
                                                                           session=session['yomboapi_session'])

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                return page_devtools_commands_form(webinterface,
                                                   request,
                                                   session,
                                                   'add',
                                                   data,
                                                   "Add Command",
                                                   )

            msg = {
                'header': 'Command Added',
                'label': 'Command added successfully',
                'description': '<p>The command has been added. If you have requested this command to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/config/commands/index">command index</a> or <a href="/devtools/config/commands/%s/details">view the command</a>.</p>' %
                               command_results['data']['id'],
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/commands/add", "Add")
            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        @webapp.route('/config/commands/<string:command_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_commands_edit_get(webinterface, request, session, command_id):
            try:
                command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id,
                                                                       session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/commands/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(
                request,
                "/devtools/config/commands/%s/details" % command_results['data']['id'],
                command_results['data']['label'])
            webinterface.add_breadcrumb(
                request,
                "/devtools/config/commands/%s/edit",
                "Edit")

            return page_devtools_commands_form(webinterface,
                                               request,
                                               session,
                                               'edit',
                                               command_results['data'],
                                               "Edit Command: %s" % command_results['data']['label'])

        @webapp.route('/config/commands/<string:command_id>/edit', methods=['POST'])
        @require_auth()
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

            command_results = yield webinterface._Commands.dev_command_edit(command_id,
                                                                            data,
                                                                            session=session['yomboapi_session'])

            data['machine_label'] = request.args.get('machine_label_hidden')[0]

            if command_results['status'] == 'failed':
                webinterface.add_alert(command_results['apimsghtml'], 'warning')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/details" % command_id,
                                            data['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/edit", "Edit")

                return page_devtools_commands_form(webinterface, request, session, 'edit', data,
                                                        "Edit Command: %s" % data['label'])

                return webinterface.redirect(request, '/devtools/config/commands/index')

            msg = {
                'header': 'Command Updated',
                'label': 'Command updated successfully',
                'description': '<p>The command has been updated. If you have requested this command to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/config/commands/index">command index</a> or <a href="/devtools/config/commands/%s/details">view the command</a>.</p>' % command_id,
            }

            try:
                command_api_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/command/%s' % command_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(
                    request,'/devtools/config/commands/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(
                request,
                "/devtools/config/commands/%s/details" % command_id,
                command_api_results['data']['label']
            )
            webinterface.add_breadcrumb(request, "/devtools/config/commands/%s/edit", "Edit")

            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        def page_devtools_commands_form(webinterface, request, session, action_type, command,
                                        header_label):
            page = webinterface.get_template(
                request,
                webinterface._dir + 'pages/devtools/config/commands/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               command=command,
                               action_type=action_type,
                               )
