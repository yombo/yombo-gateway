from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning

def route_devtools_config_input_types(webapp):
    with webapp.subroute("/devtools") as webapp:

        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/devtools/config/", "Config Tools")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types", True)

        @webapp.route('/config/input_types/index')
        @require_auth()
        def page_devtools_input_types_index_get(webinterface, request, session):
            page = webinterface.get_template(request,
                                             webinterface.wi_dir + '/pages/devtools/config/input_types/index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            return page.render(alerts=webinterface.get_alerts())

        @webapp.route('/config/input_types/<string:input_type_id>/details', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_input_types_details_get(webinterface, request, session, input_type_id):
            try:
                input_type_results = yield webinterface._YomboAPI.request('GET',
                                                                          '/v1/input_type/%s' % input_type_id,
                                                                          session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/index')

            try:
                category_results = yield webinterface._YomboAPI.request('GET',
                                                                        '/v1/category/%s' % input_type_results['data'][
                                                                            'category_id'],
                                                                        session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/index')

            page = webinterface.get_template(request,
                                             webinterface.wi_dir + '/pages/devtools/config/input_types/details.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                        input_type_results['data']['label'])

            return page.render(alerts=webinterface.get_alerts(),
                                    input_type=input_type_results['data'],
                                    category=category_results['data'],
                                    )

        @webapp.route('/config/input_types/<string:input_type_id>/delete', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_input_types_delete_get(webinterface, request, session, input_type_id):
            try:
                input_type_results = yield webinterface._YomboAPI.request('GET',
                                                                          '/v1/input_type/%s' % input_type_id,
                                                                          session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/index')

            page = webinterface.get_template(request,
                                             webinterface.wi_dir + '/pages/devtools/config/input_types/delete.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                        input_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/delete" % input_type_id, "Delete")
            return page.render(alerts=webinterface.get_alerts(),
                                    input_type=input_type_results['data'],
                                    )

        @webapp.route('/config/input_types/<string:input_type_id>/delete', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_input_types_delete_post(webinterface, request, session, input_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id)

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to delete the input type.',
                                       'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id)

            results = yield webinterface._InputTypes.dev_input_type_delete(input_type_id,
                                                                           session=session['yomboapi_session'])

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id)

            msg = {
                'header': 'Input Type Deleted',
                'label': 'Input Type deleted successfully',
                'description': '<p>The input type has been deleted.</p><p>Continue to <a href="/devtools/config/input_types/index">input type index</a> or <a href="/devtools/config/input_types/%s/details">view the input type</a>.</p>' % input_type_id,
            }

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET',
                                                                          '/v1/input_types/%s' % input_type_id,
                                                                          session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/index')

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                        input_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/delete" % input_type_id, "Delete")

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/input_types/<string:input_type_id>/disable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_input_types_disable_get(webinterface, request, session, input_type_id):
            try:
                input_type_results = yield webinterface._YomboAPI.request('GET',
                                                                          '/v1/input_type/%s' % input_type_id,
                                                                          session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/index')

            page = webinterface.get_template(request,
                                             webinterface.wi_dir + '/pages/devtools/config/input_types/disable.html')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                        input_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/disable" % input_type_id, "Disable")

            return page.render(alerts=webinterface.get_alerts(),
                                    input_type=input_type_results['data'],
                                    )

        @webapp.route('/config/input_types/<string:input_type_id>/disable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_input_types_disable_post(webinterface, request, session, input_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id)

            if confirm != "disable":
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the input type.',
                                       'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/%s/input_type_id' % input_type_id)

            results = yield webinterface._InputTypes.dev_input_type_disable(input_type_id,
                                                                            session=session['yomboapi_session'])

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id)

            msg = {
                'header': 'Input Type Disabled',
                'label': 'Input Type disabled successfully',
                'description': '<p>The input type has been disabled.</p><p>Continue to <a href="/devtools/config/input_types/index">input types index</a> or <a href="/devtools/config/input_types/%s/details">view the input type</a>.</p>' % input_type_id,
            }

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET',
                                                                          '/v1/input_type/%s' % input_type_id,
                                                                          session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/index')
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                        input_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/disable" % input_type_id,
                                        "Disable")

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/input_types/<string:input_type_id>/enable', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_input_types_enable_get(webinterface, request, session, input_type_id):
            try:
                input_type_results = yield webinterface._YomboAPI.request('GET',
                                                                          '/v1/input_type/%s' % input_type_id,
                                                                          session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/index')

            page = webinterface.get_template(request,
                                             webinterface.wi_dir + '/pages/devtools/config/input_types/enable.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                        input_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/disable" % input_type_id, "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                                    input_type=input_type_results['data'],
                                    )

        @webapp.route('/config/input_types/<string:input_type_id>/enable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_input_types_enable_post(webinterface, request, session, input_type_id):
            try:
                confirm = request.args.get('confirm')[0]
            except:
                return webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id)

            if confirm != "enable":
                webinterface.add_alert('Must enter "enable" in the confirmation box to enable the input type.',
                                       'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/%s/input_type_id' % input_type_id)

            results = yield webinterface._InputTypes.dev_input_type_enable(input_type_id,
                                                                           session=session['yomboapi_session'])

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/%s/details' % input_type_id)

            msg = {
                'header': 'Input Type Enabled',
                'label': 'Input Type enabled successfully',
                'description': '<p>The input type has been enabled.</p><p>Continue to <a href="/devtools/config/input_types/index">input types index</a> or <a href="/devtools/config/input_types/%s/details">view the input type</a>.</p>' % input_type_id,
            }

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET',
                                                                          '/v1/input_type/%s' % input_type_id,
                                                                          session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/index')
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                        input_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/enable" % input_type_id, "Enable")

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/input_types/add', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_input_types_add_get(webinterface, request, session):
            try:
                category_results = yield webinterface._YomboAPI.request('GET',
                                                                        '/v1/category?_filters[category_type]=input_type',
                                                                        session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/index')

            data = {
                'category_id': webinterface.request_get_default(request, 'category_id', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'platform': webinterface.request_get_default(request, 'platform', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'public': int(webinterface.request_get_default(request, 'public', 0)),
            }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/add", "Add")
            return page_devtools_input_types_form(webinterface, request, session, 'add', data,
                                                       category_results['data'], "Add Input Type")

        @webapp.route('/config/input_types/add', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_input_types_add_post(webinterface, request, session):
            data = {
                'category_id': webinterface.request_get_default(request, 'category_id', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'platform': webinterface.request_get_default(request, 'platform', ""),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'public': int(webinterface.request_get_default(request, 'public', 0)),
            }

            input_type_results = yield webinterface._InputTypes.dev_input_type_add(data,
                                                                                   session=session['yomboapi_session']
                                                                                   )

            if input_type_results['status'] == 'failed':
                webinterface.add_alert(input_type_results['apimsghtml'], 'warning')
                category_results = yield webinterface._YomboAPI.request('GET',
                                                                        '/v1/category?_filters[category_type]=input_type',
                                                                        session=session['yomboapi_session'])
                if category_results['code'] > 299:
                    webinterface.add_alert(category_results['content']['html_message'], 'warning')
                    return webinterface.redirect(request, '/devtools/config/input_types/index')
                return page_devtools_input_types_form(webinterface, request, session, 'add', data,
                                                   category_results['data'],
                                                   "Add Input Type")

            msg = {
                'header': 'Input Type Added',
                'label': 'Input typ added successfully',
                'description': '<p>The input type has been added. If you have requested this input type to be made public, please allow a few days for Yombo review.</p><p>Continue to <a href="/devtools/config/input_types/index">input types index</a> or <a href="/devtools/config/input_types/%s/details">view the new input type</a>.</p>' %
                               input_type_results['input_type_id'],
            }

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/display_notice.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/add", "Add")
            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/config/input_types/<string:input_type_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_input_types_edit_get(webinterface, request, session, input_type_id):
            try:
                input_type_results = yield webinterface._YomboAPI.request('GET',
                                                                          '/v1/input_type/%s' % input_type_id,
                                                                          session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/index')

            try:
                category_results = yield webinterface._YomboAPI.request('GET',
                                                                        '/v1/category?_filters[category_type]=input_type',
                                                                        session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                        input_type_results['data']['label'])
            webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/edit" % input_type_id, "Edit")

            return page_devtools_input_types_form(webinterface, request, session, 'edit', input_type_results['data'],
                                               category_results['data'],
                                               "Edit Input Type: %s" % input_type_results['data']['label'])

        @webapp.route('/config/input_types/<string:input_type_id>/edit', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_devtools_input_types_edit_post(webinterface, request, session, input_type_id):
            data = {
                'id': input_type_id,
                'category_id': webinterface.request_get_default(request, 'category_id', ""),
                'label': webinterface.request_get_default(request, 'label', ""),
                'description': webinterface.request_get_default(request, 'description', ""),
                'platform': webinterface.request_get_default(request, 'platform', 1),
                'status': int(webinterface.request_get_default(request, 'status', 1)),
                'public': int(webinterface.request_get_default(request, 'public', 0)),
            }

            dev_input_type_results = yield webinterface._InputTypes.dev_input_type_edit(input_type_id,
                                                                                        data,
                                                                                        session=session[
                                                                                            'yomboapi_session'])

            data['machine_label'] = request.args.get('machine_label_hidden')[0]

            if dev_input_type_results['status'] == 'failed':
                try:
                    input_type_results = yield webinterface._YomboAPI.request('GET',
                                                                              '/v1/input_type/%s' % input_type_id,
                                                                              session=session['yomboapi_session'])
                except YomboWarning as e:
                    webinterface.add_alert(e.html_message, 'warning')
                    return webinterface.redirect(request, '/devtools/config/input_types/index')

                try:
                    category_results = yield webinterface._YomboAPI.request('GET',
                                                                            '/v1/category?_filters[category_type]=input_type',
                                                                            session=session['yomboapi_session'])
                except YomboWarning as e:
                    webinterface.add_alert(e.html_message, 'warning')
                    return webinterface.redirect(request, '/devtools/config/input_types/index')

                root_breadcrumb(webinterface, request)
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                            input_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/edit" % input_type_id, "Edit")

                webinterface.add_alert(dev_input_type_results['apimsghtml'], 'warning')
                return page_devtools_input_types_form(webinterface, request, session, 'edit', data,
                                                           category_results['data'],
                                                           "Edit Input Type: %s" % data['label'])

                return webinterface.redirect(request, '/devtools/config/input_types/index')

            msg = {
                'header': 'Input Type Updated',
                'label': 'Input typ updated successfully',
                'description': '<p>The input type has been updated. If you have requested this input type to be made public, please allow a few days for Yombo review.</p>'
                               '<p>Continue to <a href="/devtools/config/input_types/index">input types index</a> or <a href="/devtools/config/input_types/%s/details">view the updated input type</a>.</p>' %
                               input_type_id,
            }

            try:
                input_type_results = yield webinterface._YomboAPI.request('GET',
                                                                          '/v1/input_type/%s' % input_type_id,
                                                                          session=session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/devtools/config/input_types/index')
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/display_notice.html')
            root_breadcrumb(webinterface, request)

            if input_type_results['code'] <= 299:
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types")
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/details" % input_type_id,
                                            input_type_results['data']['label'])
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/%s/enable" % input_type_id, "Enable")
            else:
                webinterface.add_breadcrumb(request, "/devtools/config/input_types/index", "Input Types", True)

            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        def page_devtools_input_types_form(webinterface, request, session, action_type, input_type, categories,
                                           header_label):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/devtools/config/input_types/form.html')
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               input_type=input_type,
                               categories=categories,
                               action_type=action_type,
                               display_type=action_type
                               )
