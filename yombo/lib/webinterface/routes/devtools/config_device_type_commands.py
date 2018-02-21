from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning


def route_devtools_config_device_type_commmands(webapp):
    with webapp.subroute("/devtools") as webapp:

        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/devtools/config/", "Config Tools")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types", True)

        @webapp.route('/config/device_type_commands/<string:device_type_command_id>/details',
                      methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_type_commands_details_get(webinterface, request, session, device_type_command_id):
            try:
                device_type_command_results = yield webinterface._YomboAPI.request(
                    'GET',
                    '/v1/device_type_command/%s' % device_type_command_id,
                    session=session['yomboapi_session']
                )
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            device_type_id = device_type_command_results['data']['device_type_id']
            command_id = device_type_command_results['data']['command_id']

            try:
                command_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/command/%s' % command_id,
                    session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            try:
                device_command_input_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/device_command_input?_filters[device_type_id]=%s&_filters[command_id]=%s' %
                           (device_type_id, command_id),
                    session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')
            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_type_commands/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_command_results['data']['device_type_label'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/device_type_commands/%s/details" % device_type_command_id,
                                        command_results['data']['label'])

            return page.render(alerts=webinterface.get_alerts(),
                               device_type_command=device_type_command_results['data'],
                               device_command_input=device_command_input_results['data'],
                               device_type_command_id=device_type_command_id,
                               command=command_results['data']
                               )

        @webapp.route('/config/device_type_commands/<string:device_type_id>/add', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_type_commands_add_get(webinterface, request, session, device_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/device_type/%s' % device_type_id,
                    session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_type_commands/add.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/add" % device_type_id,
                                        "Add Command")

            return page.render(alerts=webinterface.get_alerts(),
                               device_type=device_type_results['data'],
                               )

        @webapp.route('/config/device_type_commands/add/<string:device_type_id>/<string:command_id>',
                      methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_add_do_get(webinterface, request, session, device_type_id, command_id):
            results = yield webinterface._DeviceTypes.dev_command_add(device_type_id,
                                                                      command_id,
                                                                      session=session['yomboapi_session'])
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
                               '<li><strong>Don\'t forget to add input types for the command:'
                               ' <a href="/devtools/config/device_type_commands/%s/details">View device type command</a></strong></li>'
                               '</ul>'
                               '</p>' % (device_type_id, results['data']['id'])
            }

            try:
                device_type_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/device_type/%s' % device_type_id,
                    session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/command/add" % device_type_id,
                                        "Add Command")

            return page.render(alerts=webinterface.get_alerts(), msg=msg)

        @webapp.route('/config/device_type_commands/<string:device_type_command_id>/remove',
                      methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_type_commands_remove_get(webinterface, request, session, device_type_command_id):
            try:
                device_type_command_results = yield webinterface._YomboAPI.request(
                    'GET',
                    '/v1/device_type_command/%s' % device_type_command_id,
                    session=session['yomboapi_session']
                )
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            device_type_id = device_type_command_results['data']['device_type_id']
            command_id = device_type_command_results['data']['command_id']

            try:
                command_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/command/%s' % command_id,
                    session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            # try:
            #     device_command_input_results = yield webinterface._YomboAPI.request(
            #         'GET', '/v1/device_command_input?_filters[device_type_id]=%s&_filters[command_id]=%s' %
            #                (device_type_id, command_id),
            #         session=session['yomboapi_session'])
            # except YomboWarning as e:
            #     webinterface.add_alert(e.html_message, 'warning')
            #     return webinterface.redirect(request, '/devtools/config/device_types/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/device_type_commands/remove.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/device_types/%s/details" % device_type_id,
                                        device_type_command_results['data']['device_type_label'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/device_type_commands/%s/details" % device_type_command_id,
                                        command_results['data']['label'])
            webinterface.add_breadcrumb(request,
                                        "/",
                                        "Remove command")

            return page.render(alerts=webinterface.get_alerts(),
                               device_type_command=device_type_command_results['data'],
                               # device_command_input=device_command_input_results['data'],
                               device_type_command_id=device_type_command_id,
                               command=command_results['data'],
                               )

        @webapp.route('/config/device_type_commands/<string:device_type_command_id>/remove',
                      methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_type_commands_remove_post(webinterface, request, session, device_type_command_id):
            try:
                device_type_command_results = yield webinterface._YomboAPI.request(
                    'GET',
                    '/v1/device_type_command/%s' % device_type_command_id,
                    session=session['yomboapi_session']
                )
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/device_types/index')

            device_type_id = device_type_command_results['data']['device_type_id']
            command_id = device_type_command_results['data']['command_id']

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

            device_type_results = yield webinterface._DeviceTypes.dev_command_remove(device_type_command_id,
                                                                                     session=session['yomboapi_session'])
            if device_type_results['status'] == 'failed':
                webinterface.add_alert(device_type_results['apimsghtml'], 'warning')
                return webinterface.redirect(request,
                                             '/devtools/config/device_types/%s/details' % device_type_id)

            try:
                command_results = yield webinterface._YomboAPI.request(
                    'GET', '/v1/command/%s' % command_id,
                    session=session['yomboapi_session'])
            except YomboWarning as e:
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
                    'GET', '/v1/device_type/%s' % device_type_id,
                    session=session['yomboapi_session'])
            except YomboWarning as e:
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
