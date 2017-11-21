from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboAPIWarning

def route_devtools_config_device_types(webapp):
    with webapp.subroute("/devtools") as webapp:

        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/devtools/config/", "Config Tools")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types", True)

        @webapp.route('/config/device_types/index')
        @require_auth()
        def page_devtools_device_types_index_get(webinterface, request, session):
            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/index.html')
            root_breadcrumb(webinterface, request)
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/config/device_types/<string:device_type_id>/command/<string:command_id>/details',
                      methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_details_get(webinterface, request, session, device_type_id, command_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                device_command_input_results = yield webinterface._YomboAPI.request(
                    'GET',
                    '/v1/device_command_input?_filters[device_type_id]=%s&_filters[command_id]=%s' % (
                        device_type_id, command_id)
                )
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                command_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/command/%s' % command_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/command_details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
                    device_type_id, command_id),
                command_results['data']['label'])

            return page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    inputs=device_command_input_results['data'],
                                    command=command_results['data']
                                    )

        @webapp.route('/config/device_types/<string:device_type_id>/command/add_command', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_add_get(webinterface, request, session, device_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/command_add.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/add" % device_type_id,
                                        "Add Command")

            return page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    )

        @webapp.route('/config/device_types/<string:device_type_id>/command/<string:command_id>/add_command',
                      methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_add_do_get(webinterface, request, session, device_type_id, command_id):
            results = yield webinterface._DeviceTypes.dev_command_add(device_type_id, command_id)
            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/details' % device_type_id)

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

            try:
                device_type_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/add" % device_type_id,
                                        "Add Command")

            return page.render(alerts=webinterface.get_alerts(), msg=msg)

        @webapp.route('/config/device_types/<string:device_type_id>/command/<string:command_id>/remove_command',
                      methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_remove_command_get(webinterface, request, session, device_type_id, command_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                command_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/command/%s' % command_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/command_remove.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/remove" % device_type_id,
                                        "Remove Command")

            return page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    command=command_results['data'],
                                    )

        @webapp.route('/config/device_types/<string:device_type_id>/command/<string:command_id>/remove_command',
                      methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_remove_command_post(webinterface, request, session, device_type_id, command_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/details' % device_type_id)

            if confirm != "remove":
                webinterface.add_alert(
                    'Must enter "remove" in the confirmation box to remove the command from the device type.',
                    'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/device_type_id' % device_type_id)

            device_type_results = yield webinterface._DeviceTypes.dev_command_remove(device_type_id, command_id)
            if device_type_results['status'] == 'failed':
                webinterface.add_alert(device_type_results['apimsghtml'], 'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/details' % device_type_id)

            try:
                command_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/command/%s' % command_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

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

            try:
                device_type_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
                device_type_id, command_id), command_results['data']['label'])

            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/remove" % device_type_id,
                                        "Remove Command")

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/device_types/<string:device_type_id>/command/<string:command_id>/add_input',
                      methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_add_input_get(webinterface, request, session, device_type_id,
                                                             command_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/command_input_add.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/add" % device_type_id,
                                        "Add Command")

            return page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    command=command_results['data']
                                    )

        @webapp.route(
            '/config/device_types/<string:device_type_id>/command/<string:command_id>/input/<string:input_type_id>/add_input',
            methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_input_add_get(webinterface, request, session, device_type_id, command_id,
                                                             input_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
                    device_type_id, command_id),
                "Command")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/add_input" % (
                    device_type_id, command_id),
                "Associate input")

            try:
                command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')
            webinterface.add_breadcrumb(
                request, "/devtools/config/device_types/%s/command/%s/input/%s/add_input" % (
                    device_type_id, command_id, input_type_id),
                    input_type_results['data']['label']
            )

            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'live_update': webinterface.request_get_default(request, 'live_update', ""),
                'notes': webinterface.request_get_default(request, 'notes', ""),
                'value_required': webinterface.request_get_default(request, 'value_required', 0),
                'value_min': webinterface.request_get_default(request, 'value_min', ""),
                'value_max': webinterface.request_get_default(request, 'value_max', ""),
                'value_casing': webinterface.request_get_default(request, 'value_casing', "none"),
                'encryption': webinterface.request_get_default(request, 'encryption', "nosuggestion"),
            }
            return page_devtools_device_types_command_input_form(webinterface,
                                                                 request,
                                                                 session,
                                                                 'add',
                                                                 data,
                                                                 device_type_results['data'],
                                                                 command_results['data'],
                                                                 input_type_results['data'],
                                                                 "Associate input type to command")

        @webapp.route(
            '/config/device_types/<string:device_type_id>/command/<string:command_id>/input/<string:input_type_id>/add_input',
            methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_input_add_post(webinterface, request, session, device_type_id,
                                                              command_id, input_type_id):
            data = {
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'live_update': webinterface.request_get_default(request, 'live_update', ""),
                'notes': webinterface.request_get_default(request, 'notes', ""),
                'value_required': webinterface.request_get_default(request, 'value_required', 0),
                'value_min': webinterface.request_get_default(request, 'value_min', ""),
                'value_max': webinterface.request_get_default(request, 'value_max', ""),
                'value_casing': webinterface.request_get_default(request, 'value_casing', "none"),
                'encryption': webinterface.request_get_default(request, 'encryption', "nosuggestion"),
            }

            results = yield webinterface._DeviceTypes.dev_command_input_add(device_type_id, command_id, input_type_id,
                                                                             data)

            try:
                command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
            device_type_id, command_id),
                                        command_results['data']['label'])
            webinterface.add_breadcrumb(
                request,
                "/devtools/config/device_types/%s/command/%s/add_input" % (
                    device_type_id, command_id),
                "Associate input"
            )

            # print("results:status: %s" % results['status'])
            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                return page_devtools_device_types_command_input_form(
                    webinterface,
                    request,
                    session,
                    'add',
                    data, device_type_results['data'],
                    command_results['data'],
                    input_type_results['data'],
                    "Associate input type to command")

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
            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route(
            '/config/device_types/<string:device_type_id>/command/<string:command_id>/input/<string:input_type_id>/details',
            methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_input_details_get(webinterface, request, session, device_type_id,
                                                                 command_id, input_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                device_command_input_results = yield webinterface._YomboAPI.request(
                    'GET',
                    '/v1/device_command_input?_filters[device_type_id]=%s&_filters[command_id]=%s&_filters[input_type_id]=%s' % (
                        device_type_id,
                        command_id,
                        input_type_id))
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/command_input_details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
            device_type_id, command_id),
                                        "Command - %s" % command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/edit_input" % (
            device_type_id, command_id),
                                        "Input Command Details")
            return page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    command=command_results['data'],
                                    command_input=device_command_input_results['data'][0],
                                    input_type=input_type_results['data'],
                                    )

        @webapp.route(
            '/config/device_types/<string:device_type_id>/command/<string:command_id>/input/<string:input_type_id>/edit_input',
            methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_input_edit_get(webinterface, request, session, device_type_id,
                                                              command_id, input_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                device_command_input_results = yield webinterface._YomboAPI.request(
                    'GET',
                    '/v1/device_command_input?_filters[device_type_id]=%s&_filters[command_id]=%s&_filters[input_type_id]=%s' % (
                        device_type_id, command_id,
                        input_type_id))
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            # data = {
            #     'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
            #     'live_update': webinterface.request_get_default(request, 'live_update', ""),
            #     'notes': webinterface.request_get_default(request, 'notes', ""),
            #     'value_required': webinterface.request_get_default(request, 'value_required', ""),
            #     'value_min': webinterface.request_get_default(request, 'value_min', ""),
            #     'value_max': webinterface.request_get_default(request, 'value_max', ""),
            #     'value_casing': webinterface.request_get_default(request, 'value_casing', "none"),
            #     'encryption': webinterface.request_get_default(request, 'encryption', "nosuggestion"),
            # }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
            device_type_id, command_id),
                                        "Command - %s" % command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/edit_input" % (
            device_type_id, command_id),
                                        "Edit input")
            return page_devtools_device_types_command_input_form(webinterface, request, session, 'add',
                                                                      device_command_input_results['data'][0],
                                                                      device_type_results['data'],
                                                                      command_results['data'],
                                                                      input_type_results['data'],
                                                                      "Associate input type to command")

        @webapp.route(
            '/config/device_types/<string:device_type_id>/command/<string:command_id>/input/<string:input_type_id>/edit_input',
            methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_input_edit_post(webinterface, request, session, device_type_id,
                                                               command_id, input_type_id):
            data = {
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'live_update': webinterface.request_get_default(request, 'live_update', ""),
                'notes': webinterface.request_get_default(request, 'notes', ""),
                'value_required': webinterface.request_get_default(request, 'value_required', ""),
                'value_min': webinterface.request_get_default(request, 'value_min', ""),
                'value_max': webinterface.request_get_default(request, 'value_max', ""),
                'value_casing': webinterface.request_get_default(request, 'value_casing', "none"),
                'encryption': webinterface.request_get_default(request, 'encryption', "nosuggestion"),
            }

            results = yield webinterface._DeviceTypes.dev_command_input_edit(
                device_type_id, command_id, input_type_id,data
            )

            try:
                command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                return page_devtools_device_types_command_input_form(webinterface, request, session, 'add',
                                                                  data, device_type_results['data'][0],
                                                                  command_results['data'],
                                                                  input_type_results['data'],
                                                                  "Associate input type to command")

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
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/details" % (
            device_type_id, command_id),
                                        "Command - %s" % command_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/%s/edit_input" % (
            device_type_id, command_id),
                                        "Edit input")
            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

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
        @inlineCallbacks
        def page_devtools_device_types_command_delete_input_get(webinterface, request, session, device_type_id,
                                                                command_id, input_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type/%s' % input_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/command_input_remove.html')
            root_breadcrumb(webinterface, request)
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
            return page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    input_type=input_type_results['data'],
                                    command=command_results['data'],
                                    )

        @webapp.route(
            '/config/device_types/<string:device_type_id>/command/<string:command_id>/input/<string:input_type_id>/remove_input',
            methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_delete_input_post(webinterface, request, session, device_type_id,
                                                                 command_id, input_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/details' % device_type_id)

            if confirm != "remove":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the device type.',
                                       'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/command/%s/input/%s/remove_input' % (
                                             device_type_id, command_id, input_type_id))

            results = yield webinterface._DeviceTypes.dev_command_input_remove(device_type_id, command_id,
                                                                               input_type_id)
            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/details' % device_type_id)

            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                command_results = yield webinterface._YomboAPI.request('GET', '/v1/command/%s' % command_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

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
            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/device_types/<string:device_type_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_details_get(webinterface, request, session, device_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                category_results = yield webinterface._YomboAPI.request('GET',
                                                                        '/v1/category/%s' % device_type_results['data'][
                                                                            'category_id'])
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                device_type_commands_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/device_type_command/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/details.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])

            return page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    category=category_results['data'],
                                    device_type_commands=device_type_commands_results['data']
                                    )

        @webapp.route('/config/device_types/<string:device_type_id>/delete', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_delete_get(webinterface, request, session, device_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/delete.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/delete" % device_type_id, "Delete")
            return page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    )

        @webapp.route('/config/device_types/<string:device_type_id>/delete', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_delete_post(webinterface, request, session, device_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/details' % device_type_id)

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the device type.',
                                       'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/details' % device_type_id)

            results = yield webinterface._DeviceTypes.dev_device_type_delete(device_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/details' % device_type_id)

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

            try:
                device_type_results = yield webinterface._YomboAPI.request('GET',
                                                                           '/v1/device_types/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/delete" % device_type_id,
                                        "Delete")

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/device_types/<string:device_type_id>/disable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_disable_get(webinterface, request, session, device_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/disable.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/disable" % device_type_id, "Disable")

            return page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    )

        @webapp.route('/config/device_types/<string:device_type_id>/disable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_disable_post(webinterface, request, session, device_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/details' % device_type_id)

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the device type.',
                                       'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/device_type_id' % device_type_id)

            results = yield webinterface._DeviceTypes.dev_device_type_disable(device_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/details' % device_type_id)

            msg = {
                'header': 'Device Type Disabled',
                'label': 'Device Type disabled successfully',
                'description': '<p>The device type has been disabled.</p><p>Continue to <a href="/devtools/config/device_types/index">device types index</a> or <a href="/devtools/config/device_types/%s/details">view the device type</a>.</p>' % device_type_id,
            }

            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/disable" % device_type_id,
                                        "Disable")

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/device_types/<string:device_type_id>/enable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_enable_get(webinterface, request, session, device_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/enable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/disable" % device_type_id, "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    )

        @webapp.route('/config/device_types/<string:device_type_id>/enable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_enable_post(webinterface, request, session, device_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/details' % device_type_id)

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the device type.',
                                       'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/device_type_id' % device_type_id)

            results = yield webinterface._DeviceTypes.dev_device_type_enable(device_type_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/details' % device_type_id)

            msg = {
                'header': 'Device Type Enabled',
                'label': 'Device Type enabled successfully',
                'description': '<p>The device type has been enabled.</p><p>Continue to <a href="/devtools/config/device_types/index">device types index</a> or <a href="/devtools/config/device_types/%s/details">view the device type</a>.</p>' % device_type_id,
            }

            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/enable" % device_type_id,
                                        "Enable")
            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/device_types/add', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_add_get(webinterface, request, session):
            try:
                category_results = yield webinterface._YomboAPI.request('GET',
                                                                        '/v1/category?_filters[category_type]=device_type')
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

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
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/add", "Add")
            return page_devtools_devicestypes_form(webinterface,
                                                   request,
                                                   session,
                                                   'add',
                                                   data,
                                                   category_results['data'],
                                                   "Add Device Type")

        @webapp.route('/config/device_types/add', methods=['POST'])
        @require_auth()
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
                try:
                    category_results = yield webinterface._YomboAPI.request('GET',
                                                                            '/v1/category?_filters[category_type]=device_type')
                except YomboAPIWarning as e:
                    webinterface.add_alert(e.html_message, 'warning')
                    return webinterface.redirect(request, '/devtools/config/device_types/index')
                return page_devtools_devicestypes_form(webinterface,
                                                       request,
                                                       session,
                                                       'add',
                                                       data,
                                                       category_results['data'],
                                                       "Add Device Type")

            msg = {
                'header': 'Device Type Added',
                'label': 'Device typ added successfully',
                'description': '<p>The device type has been added. If you have requested this device type to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/config/device_types/index">device types index</a> or <a href="/devtools/config/device_types/%s/details">view the new device type</a>.</p>' %
                               device_type_results['device_type_id'],
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/add", "Add")
            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/device_types/<string:device_type_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_edit_get(webinterface, request, session, device_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                category_results = yield webinterface._YomboAPI.request('GET',
                                                                        '/v1/category?_filters[category_type]=device_type')
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/edit" % device_type_id, "Edit")

            return page_devtools_devicestypes_form(
                webinterface,
                request,
                session,
                'edit',
                device_type_results['data'],
                category_results['data'],
                "Edit Device Type: %s" % device_type_results['data']['label'])

        @webapp.route('/config/device_types/<string:device_type_id>/edit', methods=['POST'])
        @require_auth()
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
                try:
                    category_results = yield webinterface._YomboAPI.request('GET',
                                                                            '/v1/category?_filters[category_type]=device_type')
                except YomboAPIWarning as e:
                    webinterface.add_alert(e.html_message, 'warning')
                    return webinterface.redirect(request, '/devtools/config/device_types/index')

                webinterface.add_alert(device_type_results['apimsghtml'], 'warning')
                return page_devtools_devicestypes_form(webinterface, request, session, 'edit', data,
                                                            category_results['data'],
                                                            "Edit Device Type: %s" % data['label'])

                return webinterface.redirect(request, '/devtools/config/device_types/index')

            msg = {
                'header': 'Device Type Updated',
                'label': 'Device typ updated successfully',
                'description': '<p>The device type has been updated. If you have requested this device type to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/config/device_types/index">device types index</a> or <a href="/devtools/config/device_types/%s/details">view the new device type</a>.</p>' %
                               device_type_results['device_type_id'],
            }

            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/enable" % device_type_id,
                                        "Enable")

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

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
        @inlineCallbacks
        def page_devtools_device_types_variables_get(webinterface, request, session, device_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % device_type_id)
            except YomboAPIWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_types/variable_details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/variables" % device_type_id,
                                        "Variable Groups")
            return page.render(alerts=webinterface.get_alerts(),
                                    device_type=device_type_results['data'],
                                    )
