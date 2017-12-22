from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning

def route_devtools_config_variables(webapp):
    with webapp.subroute("/devtools") as webapp:

        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/devtools/config/", "Config Tools")
            webinterface.add_breadcrumb(request, "/devtools/config/modules/index", "Modules", True)

        @inlineCallbacks
        def variable_group_breadcrumbs(webinterface, request, parent_id, parent_type):
            if parent_type in ('module', 'all_devices', 'all_modules'):
                try:
                    module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % parent_id)
                except YomboWarning as e:
                    webinterface.add_alert(e.html_message, 'warning')
                    return webinterface.redirect(request, '/devtools/config/modules/index')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/details" % parent_id,
                                            module_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/modules/%s/variables" % parent_id,
                                            "Variable Groups", True)

                return module_results
            elif parent_type == 'device_type':
                try:
                    device_type_results = yield webinterface._YomboAPI.request('GET', '/v1/device_type/%s' % parent_id)
                except YomboWarning as e:
                    webinterface.add_alert(e.html_message, 'warning')
                    return webinterface.redirect(request, '/devtools/config/modules/index')
                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/details" % parent_id,
                                            device_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/device_types/%s/variables" % parent_id,
                                            "Variable Groups", True)
                return device_type_results

        @webapp.route('/config/variables/group/<string:group_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_details_get(webinterface, request, session, group_id):
            try:
                group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            try:
                field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/by_group/%s' % group_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      group_results['data']['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            if parent['code'] > 299:
                webinterface.add_alert(['content']['html_message'], 'warning')
                return webinterface.redirect(request, '/devtools/config/index')

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/group_details.html')
            # root_breadcrumb(webinterface, request)
            if group_results['data']['relation_type'] == "module":
                group_results['data']['relation_type_label'] = "Local Module"
            elif group_results['data']['relation_type'] == "device_type":
                group_results['data']['relation_type_label'] = "Device Type"
            elif group_results['data']['relation_type'] == "all_devices":
                group_results['data']['relation_type_label'] = "All Devices"
            elif group_results['data']['relation_type'] == "all_modules":
                group_results['data']['relation_type_label'] = "All Modules"
            return page.render(alerts=webinterface.get_alerts(),
                                    parent=parent['data'],
                                    group=group_results['data'],
                                    fields=field_results['data']
                                    )

        @webapp.route('/config/variables/group/add/<string:parent_id>/<string:parent_type>', methods=['GET'])
        @require_auth()
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
            if parent['code'] > 299:
                webinterface.add_alert(['content']['html_message'], 'warning')
                return webinterface.redirect(request, '/devtools/config/index')

            return page_devtools_variables_group_form(webinterface, request, session, parent_type, parent['data'], data,
                                                   "Add Group Variable to: %s" % parent['data']['label'])

        @webapp.route('/config/variables/group/add/<string:parent_id>/<string:parent_type>', methods=['POST'])
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
            if parent['code'] > 299:
                webinterface.add_alert(['content']['html_message'], 'warning')
                return webinterface.redirect(request, '/devtools/config/index')

            dev_group_results = yield webinterface._Variables.dev_group_add(data)
            if dev_group_results['status'] == 'failed':
                webinterface.add_alert(dev_group_results['apimsghtml'], 'warning')
                return page_devtools_variables_group_form(webinterface, request, session, parent_type, parent['data'],
                                                       data, "Add Group Variable to: %s" % parent['data']['label'])

            msg = {
                'header': 'Variable Group Added',
                'label': 'Variable group added successfully',
                'description': ''
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            if parent_type in ('module', 'all_devices', 'all_modules'):
                msg[
                    'description'] = '<p>Variable group has beed added.</p><p>Continue to:<ul><li><a href="/devtools/config/modules/index">modules index</a></li><li><a href="/devtools/config/modules/%s/details">view the module</a></li><li><a href="/devtools/config/modules/%s/variables"> view module variables</a></li></ul></p>' % (
                parent_id, parent_id)
            elif parent_type == 'device_type':
                msg[
                    'description'] = '<p>Variable group has beed added.</p><p>Continue to:<ul><li><a href="/devtools/config/device_types/index">device types index</a></li><li><a href="/devtools/config/device_types/%s/details">view the device type: %s</a></li><li><a href="/devtools/config/device_types/%s/variables"> view device type variables</a></li></ul></p>' % (
                parent_id, parent['data']['label'], parent_id)

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/variables/group/<string:group_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_edit_get(webinterface, request, session, group_id):
            try:
                group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            parent_type = group_results['data']['relation_type']
            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      parent_type)
            webinterface.add_breadcrumb(request, "/", "Edit Variable")
            if parent['code'] > 299:
                webinterface.add_alert(['content']['html_message'], 'warning')
                return webinterface.redirect(request, '/devtools/config/index')

            return page_devtools_variables_group_form(webinterface, request, session, parent_type, parent['data'],
                                                           group_results['data'],
                                                           "Edit Group Variable: %s" % group_results['data'][
                                                               'group_label'])

        @webapp.route('/config/variables/group/<string:group_id>/edit', methods=['POST'])
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

            try:
                group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            parent_type = group_results['data']['relation_type']
            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      parent_type)
            webinterface.add_breadcrumb(request, "/", "Edit Variable")
            if parent['code'] > 299:
                webinterface.add_alert(['content']['html_message'], 'warning')
                return webinterface.redirect(request, '/devtools/config/index')

            dev_group_results = yield webinterface._Variables.dev_group_edit(group_id, data)
            if dev_group_results['status'] == 'failed':
                webinterface.add_alert(dev_group_results['apimsghtml'], 'warning')
                return page_devtools_variables_group_form(webinterface, request, session, parent_type, parent['data'],
                                                       data, "Add Group Variable to: %s" % parent['data']['label'])

            msg = {
                'header': 'Variable Group Edited',
                'label': 'Variable group edited successfully',
                'description': ''
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            if parent_type in ('module', 'all_devices', 'all_modules'):
                msg[
                    'description'] = '<p>Variable group has beed edited.</p><p>Continue to:<ul><li><a href="/devtools/config/modules/index">modules index</a></li><li><a href="/devtools/config/modules/%s/details">view the module</a></li><li><a href="/devtools/config/modules/%s/variables"> view module variables</a></li></ul></p>' % (
                parent['data']['id'], parent['data']['id'])
            elif parent_type == 'device_type':
                msg[
                    'description'] = '<p>Variable group has beed edited.</p><p>Continue to:<ul><li><a href="/devtools/config/device_types/index">device types index</a></li><li><a href="/devtools/config/device_types/%s/details">view the device type: %s</a></li><li><a href="/devtools/config/device_types/%s/variables"> view device type variables</a></li></ul></p>' % (
                parent['data']['id'], parent['data']['label'], parent['data']['id'])

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

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
        @inlineCallbacks
        def page_devtools_variables_group_enable_get(webinterface, request, session, group_id):
            try:
                group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            data = group_results['data']
            parent = yield variable_group_breadcrumbs(webinterface, request, data['relation_id'], data['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Enable")

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/group_enable.html')
            return page.render(alerts=webinterface.get_alerts(),
                                    var_group=data,
                                    parent=parent,
                                    )

        @webapp.route('/config/variables/group/<string:group_id>/enable', methods=['post'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_enable_post(webinterface, request, session, group_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request, '/devtools/config/index')

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the variable group.',
                                       'warning')
                return webinterface.redirect(request, '/devtools/config/variables/group/%s/enable' % group_id)

            dev_group_results = yield webinterface._Variables.dev_group_enable(group_id)
            if dev_group_results['status'] == 'failed':
                webinterface.add_alert(dev_group_results['apimsghtml'], 'warning')
                return webinterface.redirect(request, '/devtools/config/variables/group/%s/enable' % group_id)

            try:
                group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

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

            if data['relation_type'] in ('module', 'all_devices', 'all_modules'):
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

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/variables/group/<string:group_id>/disable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_disable_get(webinterface, request, session, group_id):
            try:
                group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            data = group_results['data']
            parent = yield variable_group_breadcrumbs(webinterface, request, data['relation_id'], data['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Disable")

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/group_disable.html')
            return page.render(alerts=webinterface.get_alerts(),
                                    var_group=data,
                                    parent=parent,
                                    )

        @webapp.route('/config/variables/group/<string:group_id>/disable', methods=['post'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_disable_post(webinterface, request, session, group_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request, '/devtools/config/index')

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the variable group.',
                                       'warning')
                return webinterface.redirect(request, '/devtools/config/variables/group/%s/disable' % group_id)

            dev_group_results = yield webinterface._Variables.dev_group_disable(group_id)
            if dev_group_results['status'] == 'failed':
                webinterface.add_alert(dev_group_results['apimsghtml'], 'warning')
                return webinterface.redirect(request, '/devtools/config/variables/group/%s/disable' % group_id)

            try:
                group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

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

            if data['relation_type'] in ('module', 'all_devices', 'all_modules'):
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

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/variables/group/<string:group_id>/delete', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_delete_get(webinterface, request, session, group_id):
            try:
                group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            data = group_results['data']
            parent = yield variable_group_breadcrumbs(webinterface, request, data['relation_id'], data['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Delete")

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/group_delete.html')
            return page.render(alerts=webinterface.get_alerts(),
                                    var_group=data,
                                    parent=parent,
                                    )

        @webapp.route('/config/variables/group/<string:group_id>/delete', methods=['post'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_group_delete_post(webinterface, request, session, group_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request, '/devtools/config/index')

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the variable group.',
                                       'warning')
                return webinterface.redirect(request, '/devtools/config/variables/group/%s/delete' % group_id)

            dev_group_results = yield webinterface._Variables.dev_group_delete(group_id)
            if dev_group_results['status'] == 'failed':
                webinterface.add_alert(dev_group_results['apimsghtml'], 'warning')
                return webinterface.redirect(request, '/devtools/config/variables/group/%s/details' % group_id)

            try:
                group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

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

            if data['relation_type'] in ('module', 'all_devices', 'all_modules'):
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

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/variables/group/<string:group_id>/new_field', methods=['GET'])
        @require_auth()
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

            try:
                group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            parent_type = group_results['data']['relation_type']
            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      parent_type)
            if parent['code'] > 299:
                webinterface.add_alert(['content']['html_message'], 'warning')
                return webinterface.redirect(request, '/devtools/config/index')

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type?status=1')
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Add Field")
            return page_devtools_variables_field_form(webinterface, request, session, parent, group_results['data'], data,
                                                   input_type_results['data'],
                                                   "Add Field Variable to: %s" % group_results['data']['group_label'])

        @webapp.route('/config/variables/group/<string:group_id>/new_field', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_field_add_post(webinterface, request, session, group_id):
            try:
                group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

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
            for data_key in list(data.keys()):
                # print "key:data %s:%s" % (data_key, data[data_key])
                if isinstance(data[data_key], str) and len(data[data_key]) == 0:
                    del data[data_key]

            try:
                group_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/group/%s' % group_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      group_results['data']['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "New Field")
            if parent['code'] > 299:
                webinterface.add_alert(parent['content']['html_message'], 'warning')
                return webinterface.redirect(request, '/devtools/config/index')

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type?status=1')
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            dev_field_results = yield webinterface._Variables.dev_field_add(data)
            if dev_field_results['status'] == 'failed':
                webinterface.add_alert(dev_field_results['apimsghtml'], 'warning')
                return page_devtools_variables_field_form(webinterface, request, session,
                                                               group_results['data']['relation_type'],
                                                               parent['data'], data, input_type_results['data'],
                                                               "Add Group Variable to: %s" % parent['data']['label'])

            msg = {
                'header': 'Variable Field Added',
                'label': 'Variable field added to group successfully',
                'description': ''
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            if group_results['data']['relation_type'] in ('module', 'all_devices', 'all_modules'):
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

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/variables/field/<string:field_id>/delete', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_field_delete_get(webinterface, request, session, field_id):
            try:
                field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/%s' % field_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            try:
                group_results = yield webinterface._YomboAPI.request('GET',
                                                                     '/v1/variable/group/%s' % field_results['data'][
                                                                         'group_id'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            parent = yield variable_group_breadcrumbs(webinterface, request,
                                                      group_results['data']['relation_id'],
                                                      group_results['data']['relation_type'])

            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Delete Field")

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/field_delete.html')
            return page.render(alerts=webinterface.get_alerts(),
                                    var_field=field_results['data'],
                                    parent=parent,
                                    )

        @webapp.route('/config/variables/field/<string:field_id>/delete', methods=['post'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_field_delete_post(webinterface, request, session, field_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request, '/devtools/config/index')

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the variable group.',
                                       'warning')
                return webinterface.redirect(request, '/devtools/config/variables/feild/%s/delete' % field_id)

            try:
                field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/%s' % field_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            try:
                group_results = yield webinterface._YomboAPI.request('GET',
                                                                     '/v1/variable/group/%s' % field_results['data'][
                                                                         'group_id'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            dev_group_results = yield webinterface._Variables.dev_field_delete(field_id)
            if dev_group_results['status'] == 'failed':
                webinterface.add_alert(dev_group_results['apimsghtml'], 'warning')
                return webinterface.redirect(request, '/devtools/config/variables/field/%s/details' % field_id)

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

            if group_results['data']['relation_type'] in ('module', 'all_devices', 'all_modules'):
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

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/variables/field/<string:field_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_field_details_get(webinterface, request, session, field_id):
            field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/%s' % field_id)
            if field_results['code'] > 299:
                webinterface.add_alert(field_results['content']['html_message'], 'warning')
                return webinterface.redirect(request, '/modules/%s/variables' % field_id)

            try:
                group_results = yield webinterface._YomboAPI.request('GET',
                                                                     '/v1/variable/group/%s' % field_results['data'][
                                                                         'group_id'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET',
                                                                          '/v1/input_type/%s' % field_results['data'][
                                                                              'input_type_id'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      group_results['data']['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Details")

            page = webinterface.get_template(request,
                                             webinterface._dir + 'pages/devtools/config/variables/field_details.html')
            return page.render(alerts=webinterface.get_alerts(),
                                    var_group=group_results['data'],
                                    var_field=field_results['data'],
                                    input_type=input_type_results['data']
                                    )

        @webapp.route('/config/variables/field/<string:field_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_field_edit_get(webinterface, request, session, field_id):
            try:
                field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/%s' % field_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            try:
                group_results = yield webinterface._YomboAPI.request('GET',
                                                                     '/v1/variable/group/%s' % field_results['data'][
                                                                         'group_id'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      group_results['data']['relation_type'])
            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Edit Field")
            if parent['code'] > 299:
                webinterface.add_alert(parent['content']['html_message'], 'warning')
                return webinterface.redirect(request, '/devtools/config/index')

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type?status=1')
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            return page_devtools_variables_field_form(webinterface,
                                                           request,
                                                           session,
                                                           group_results['data']['relation_type'],
                                                           parent['data'], field_results['data'],
                                                           input_type_results['data'],
                                                           "Edit Field Variable: %s" %
                                                           field_results['data']['field_label'])

        @webapp.route('/config/variables/field/<string:field_id>/edit', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_variables_field_edit_post(webinterface, request, session, field_id):
            try:
                field_results = yield webinterface._YomboAPI.request('GET', '/v1/variable/field/%s' % field_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

            try:
                group_results = yield webinterface._YomboAPI.request('GET',
                                                                     '/v1/variable/group/%s' % field_results['data'][
                                                                         'group_id'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/modules/index')

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

            for key in list(data.keys()):
                if data[key] == "":
                    del data[key]
                elif key in ['value_min', 'value_max']:
                    if data[key] is None or data[key].lower() == "none":
                        del data[key]
                    else:
                        data[key] = int(data[key])

            parent = yield variable_group_breadcrumbs(webinterface, request, group_results['data']['relation_id'],
                                                      group_results['data']['relation_type'])
            if parent['code'] > 299:
                webinterface.add_alert(parent['content']['html_message'], 'warning')
                return webinterface.redirect(request, '/devtools/config/index')

            webinterface.add_breadcrumb(request,
                                        "/devtools/config/variables/group/%s/details" % group_results['data']['id'],
                                        group_results['data']['group_label'])
            webinterface.add_breadcrumb(request, "/", "Edit Field")

            results = yield webinterface._Variables.dev_field_edit(field_id, data)
            if results['status'] == 'failed':
                try:
                    input_type_results = yield webinterface._YomboAPI.request('GET', '/v1/input_type?status=1')
                except YomboWarning as e:
                    webinterface.add_alert(e.html_message, 'warning')
                    return webinterface.redirect(request, '/devtools/config/modules/index')

                webinterface.add_alert(results['apimsghtml'], 'warning')
                return page_devtools_variables_field_form(webinterface,
                                                               request,
                                                               session,
                                                               parent['data'],
                                                               group_results['data']['relation_type'],
                                                               field_results['data'],
                                                               input_type_results['data'],
                                                               "Edit Field Variable: %s" % field_results['data'][
                                                                   'field_label'])

            msg = {
                'header': 'Variable Field Edited',
                'label': 'Variable field edited successfully',
                'description': ''
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/display_notice.html')
            if group_results['data']['relation_type'] in ('module', 'all_devices', 'all_modules'):
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

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

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
