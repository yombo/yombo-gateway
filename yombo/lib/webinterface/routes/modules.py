# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/modules" sub-route of the web interface.

Responsible for adding, removing, and updating modules that are used by the gateway.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/route_modules.py>`_
"""

try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning

def route_modules(webapp):
    """
    Extends routes of the webapp (web interface).

    :param webapp: the Klein web server instance
    :return:
    """
    with webapp.subroute("/modules") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_modules(webinterface, request, session):
            return webinterface.redirect(request, '/modules/index')

        @webapp.route('/index')
        @require_auth()
        def page_modules_index(webinterface, request, session):
            """
            Show an index of modules configured on the Gateway.
            :param webinterface: pointer to the web interface library
            :param request: a Twisted request
            :param session: User's session information.
            :return:
            """
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/index.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/modules/index", "Modules")
            return page.render(alerts=webinterface.get_alerts(),
                               modules=webinterface._Libraries['modules'].modules,
                               )

        @webapp.route('/server_index')
        @require_auth()
        def page_modules_server_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/server_index.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/modules/index", "Server Modules")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/<string:module_id>/server_details')
        @require_auth()
        @inlineCallbacks
        def page_modules_details_from_server(webinterface, request, session, module_id):
            try:
                module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/modules/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/details_server.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/modules/server_index", "Server Modules")
            webinterface.add_breadcrumb(request, "/modules/%s/server_details" % module_results['data']['id'], module_results['data']['label'])
            return page.render(alerts=webinterface.get_alerts(),
                                    server_module=module_results['data'],
                                    modules=webinterface._Modules.modules,
                                    )

        @webapp.route('/<string:module_id>/add', methods=['POST', 'GET'])
        @require_auth()
        @inlineCallbacks
        def page_modules_add(webinterface, request, session, module_id):
            try:
                module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/modules/index')

            ok_to_save = True

            if 'json_output' in request.args:
                json_output = request.args.get('json_output', [{}])[0]
                json_output = json.loads(json_output)
                data = {
                    'status': json_output['status'],
                    'module_id': json_output['module_id'],
                    'install_branch': json_output['install_branch'],
                }
                if 'first_time' in json_output:
                    ok_to_save = False
            else:
                data = {
                    'status': 1,
                    'module_id': module_results['data']['id'],
                    'install_branch': module_results['data']['prod_branch'],
                    'variable_data': {},
                }
                json_output = {}
                ok_to_save = False

            variable_data = yield webinterface._Variables.extract_variables_from_web_data(json_output.get('vars', {}))

            if ok_to_save:
                if 'vars' in json_output:
                    variable_data = yield webinterface._Variables.extract_variables_from_web_data(
                        json_output.get('vars', {}))
                    data['variable_data'] = variable_data

                results = yield webinterface._Modules.add_module(data)
                if results['status'] == 'success':

                    webinterface._Notifications.add({'title': 'Restart Required',
                                                     'message': 'Module added. A system <strong><a  class="confirm-restart" href="#" title="Restart Yombo Gateway">restart is required</a></strong> to take affect.',
                                                     'source': 'Web Interface',
                                                     'persist': False,
                                                     'priority': 'high',
                                                     'always_show': True,
                                                     'always_show_allow_clear': False,
                                                     'id': 'reboot_required',
                                                     'local': True,
                                                     })

                    page = webinterface.get_template(request, webinterface._dir + 'pages/reboot_needed.html')
                    msg={
                        'header': 'Module Added',
                        'label': 'Module added successfully',
                        'description': '',
                        'content': 'The module was added and will be installed on next reboot. You can also '\
                        '<a href="/modules/server_index"><label>add another module</label></a>.'
                    }
                    return page.render(alerts=webinterface.get_alerts(), msg=msg)
                else:
                    webinterface.add_alert(results['apimsghtml'], 'warning')
                    variable_groups = yield webinterface._Variables.get_variable_groups_fields(
                        group_relation_type='device_type',
                        group_relation_id='device_type_id',
                    )
            else:
                variable_groups = {}
                for group in module_results['data']['variable_groups']:
                    variable_groups[group['id']] = group
                for field in module_results['data']['variable_fields']:
                    if 'fields' not in variable_groups[field['group_id']]:
                        variable_groups[field['group_id']]['fields'] = {}
                    variable_groups[field['group_id']]['fields'][field['id']] = field

            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/add.html')


            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/modules/index", "Add Module")
            return page.render(alerts=webinterface.get_alerts(),
                                    server_module=module_results['data'],
                                    variable_groups=variable_groups,
                                    input_types=webinterface._InputTypes.input_types,
                                    module_data=data,
                                    )

        # @webapp.route('/<string:module_id>/add', methods=['POST'])
        # @require_auth()
        # @inlineCallbacks
        # def page_modules_add_post(webinterface, request, session, module_id):
        #     json_output = json.loads(request.args.get('json_output')[0])
        #
        #     data = {
        #         'status': json_output['status'],
        #         'module_id': json_output['module_id'],
        #         'install_branch': json_output['install_branch'],
        #     }
        #     # print "jsonoutput = %s" % json_output
        #     if 'vars' in json_output:
        #         variable_data = yield webinterface._Variables.extract_variables_from_web_data(json_output.get('vars', {}))
        #         data['variable_data'] = variable_data
        #
        #     results = yield webinterface._Modules.add_module(data)
        #     if results['status'] == 'failed':
        #         module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
        #         if module_results['code'] != 200:
        #             webinterface.add_alert(module_results['content']['html_message'], 'warning')
        #             returnValue(webinterface.redirect(request, '/modules/index'))
        #
        #         # print "failed to submit new module: %s" % results
        #         webinterface.add_alert(results['apimsghtml'], 'warning')
        #         module_variables = yield webinterface._Variables.get_variable_groups_fields(
        #             group_relation_type='device_type',
        #             group_relation_id='device_type_id',
        #         )
        #
        #         if device['variable_data'] is not None:
        #             device_variables = yield webinterface._Variables.merge_variable_groups_fields_data_data(
        #                 device_variables,
        #                 json_output.get('vars', {})
        #             )
        #
        #         results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
        #         page = webinterface.get_template(request, webinterface._dir + 'pages/modules/add.html')
        #         returnValue(page.render(alerts=webinterface.get_alerts(),
        #                                 server_module=results['data'],
        #                                 input_types=webinterface._InputTypes.input_types,
        #                                 module_data=data,
        #                                 ))
        #
        #     msg = {
        #         'header': 'Module Added',
        #         'label': 'Module configuration updated successfully',
        #         'description': '',
        #     }
        #
        #     webinterface._Notifications.add({'title': 'Restart Required',
        #                                      'message': 'Module added. A system <strong><a  class="confirm-restart" href="#" title="Restart Yombo Gateway">restart is required</a></strong> to take affect.',
        #                                      'source': 'Web Interface',
        #                                      'persist': False,
        #                                      'priority': 'high',
        #                                      'always_show': True,
        #                                      'always_show_allow_clear': False,
        #                                      'id': 'reboot_required',
        #                                      'local': True,
        #                                      })
        #
        #     page = webinterface.get_template(request, webinterface._dir + 'pages/reboot_needed.html')
        #     returnValue(page.render(alerts=webinterface.get_alerts(),
        #                             msg=msg,
        #                             ))
        #
        #     webinterface.add_alert("Module configuratiuon updated. A restart is required to take affect.", 'warning')
        #     returnValue(webinterface.redirect(request, '/modules/index'))

        @webapp.route('/<string:module_id>/details')
        @require_auth()
        @inlineCallbacks
        def page_modules_details(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules[module_id]
            except Exception as e:
                webinterface.add_alert('Module ID was not found.', 'warning')
                return webinterface.redirect(request, '/modules/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/details.html')
            device_types = yield webinterface._LocalDB.get_module_device_types(module_id)
            module_variables = yield module._module_variables()
            # print("module_variables: %s" % module_variables)
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/modules/%s/details" % module._module_id, module._label)
            return page.render(alerts=webinterface.get_alerts(),
                               module=module,
                               module_variables=module_variables,
                               device_types=device_types,
                               )

        @webapp.route('/<string:module_id>/disable', methods=['GET'])
        @require_auth()
        def page_modules_disable_get(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules[module_id]
            except Exception as e:
                webinterface.add_alert('Module ID was not found.', 'warning')
                return webinterface.redirect(request, '/modules/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/disable.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/modules/%s/details" % module._module_id, module._label)
            webinterface.add_breadcrumb(request, "/modules/%s/disable" % module._module_id, "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                                    module=module,
                                    )

        @webapp.route('/<string:module_id>/disable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_modules_disable_post(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules[module_id]
            except Exception as e:
                webinterface.add_alert('Module ID was not found.', 'warning')
                return webinterface.redirect(request, '/modules/index')

            confirm = request.args.get('confirm')[0]
            if confirm != "disable":
                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/disable.html')
                webinterface.add_alert('Must enter "disable" in the confirmation box to disable the module.', 'warning')
                return page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        )

            results = yield webinterface._Modules.disable_module(module._module_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')

                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/disable.html')
                return page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        )

            msg = {
                'header': 'Module Disabled',
                'label': 'Module configuration updated successfully',
                'description': '',
            }

            webinterface._Notifications.add({'title': 'Restart Required',
                                             'message': 'Module disabled. A system <strong><a  class="confirm-restart" href="#" title="Restart Yombo Gateway">restart is required</a></strong> to take affect.',
                                             'source': 'Web Interface',
                                             'persist': False,
                                             'priority': 'high',
                                             'always_show': True,
                                             'always_show_allow_clear': False,
                                             'id': 'reboot_required',
                                             'local': True,
                                             })

            page = webinterface.get_template(request, webinterface._dir + 'pages/reboot_needed.html')
            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/<string:module_id>/edit', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_modules_edit_get(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules.get(module_id)
            except Exception as e:
                webinterface.add_alert('Module ID was not found.', 'warning')
                return webinterface.redirect(request, '/modules/index')

            try:
                module_results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, '/modules/index')

            module_variables = yield module._module_variables()
            device_types = yield webinterface._LocalDB.get_module_device_types(module_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/edit.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/modules/%s/details" % module._module_id, module._label)
            webinterface.add_breadcrumb(request, "/modules/%s/edit" % module._module_id, "Edit")
            return page.render(alerts=webinterface.get_alerts(),
                                    server_module=module_results['data'],
                                    module=module,
                                    module_variables=module_variables,
                                    device_types=device_types,
                                    )

        @webapp.route('/<string:module_id>/edit', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_modules_edit_post(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules[module_id]
            except Exception as e:
                webinterface.add_alert('Module ID was not found.', 'warning')
                return webinterface.redirect(request, '/modules/index')

            json_output = json.loads(request.args.get('json_output')[0])

            data = {
                'status': json_output['status'],
                'module_id': json_output['module_id'],
                'install_branch': json_output['install_branch'],
                'variable_data': json_output['vars'],
            }

            results = yield webinterface._Modules.edit_module(module_id, data)
            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')

                try:
                    results = yield webinterface._YomboAPI.request('GET', '/v1/module/%s' % module_id)
                except YomboWarning as e:
                    webinterface.add_alert(e.html_message, 'warning')
                    return webinterface.redirect(request, '/modules/index')
                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/edit.html')
                return page.render(alerts=webinterface.get_alerts(),
                                        server_module=results['data'],
                                        module=module,
                                        )

            msg = {
                'header': 'Module Updated',
                'label': 'Module configuration updated successfully',
                'description': '',
            }

            webinterface._Notifications.add({'title': 'Restart Required',
                                             'message': 'Module edited. A system <strong><a  class="confirm-restart" href="#" title="Restart Yombo Gateway">restart is required</a></strong> to take affect.',
                                             'source': 'Web Interface',
                                             'persist': False,
                                             'priority': 'high',
                                             'always_show': True,
                                             'always_show_allow_clear': False,
                                             'id': 'reboot_required',
                                             'local': True,
                                             })

            page = webinterface.get_template(request, webinterface._dir + 'pages/reboot_needed.html')
            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @inlineCallbacks
        def page_modules_edit_form(webinterface, request, session, device, variable_data=None):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/edit.html')
            device_variables = yield webinterface._Variables.get_variable_groups_fields_data(
                group_relation_type='device_type',
                group_relation_id=device['device_type_id'],
                data_relation_type='device',
                data_relation_id=device['device_id'],
            )

            if variable_data is not None:
                device_variables = yield webinterface._Variables.merge_variable_groups_fields_data_data(
                    device_variables,
                    variable_data
                )
            return page.render(alerts=webinterface.get_alerts(),
                                    device=device,
                                    device_variables=device_variables,
                                    commands=webinterface._Commands,
                                    )


        @webapp.route('/<string:module_id>/enable', methods=['GET'])
        @require_auth()
        def page_modules_enable_get(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules[module_id]
            except Exception as e:
                webinterface.add_alert('Module ID was not found.', 'warning')
                return webinterface.redirect(request, '/modules/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/enable.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/modules/%s/details" % module._module_id, module._label)
            webinterface.add_breadcrumb(request, "/modules/%s/enable" % module._module_id, "Enable")
            return page.render(alerts=webinterface.get_alerts(),
                               module=module,
                               )

        @webapp.route('/<string:module_id>/enable', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_modules_enable_post(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules[module_id]
            except Exception as e:
                webinterface.add_alert('Module ID was not found.', 'warning')
                return webinterface.redirect(request, '/modules/index')

            confirm = request.args.get('confirm')[0]
            if confirm != "enable":
                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/enable.html')
                webinterface.add_alert('Must enter "disable" in the confirmation box to enable the module.', 'warning')
                return page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        )

            results = yield webinterface._Modules.enable_module(module._module_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')

                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/enable.html')
                return page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        )

            webinterface._Notifications.add({'title': 'Restart Required',
                                             'message': 'Module enabled. A system <strong><a  class="confirm-restart" href="#" title="Restart Yombo Gateway">restart is required</a></strong> to take affect.',
                                             'source': 'Web Interface',
                                             'persist': False,
                                             'priority': 'high',
                                             'always_show': True,
                                             'always_show_allow_clear': False,
                                             'id': 'reboot_required',
                                             'local': True,
                                             })

            msg = {
                'header': 'Module Enabled',
                'label': 'Module configuration updated successfully',
                'description': '',
            }

            page = webinterface.get_template(request, webinterface._dir + 'pages/reboot_needed.html')
            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )

        @webapp.route('/<string:module_id>/remove', methods=['GET'])
        @require_auth()
        def page_modules_remove_get(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules[module_id]
            except Exception as e:
                webinterface.add_alert('Module ID was not found.', 'warning')
                return webinterface.redirect(request, '/modules/index')

            page = webinterface.get_template(request, webinterface._dir + 'pages/modules/remove.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/modules/index", "Modules")
            webinterface.add_breadcrumb(request, "/modules/%s/details" % module._module_id, module._label)
            webinterface.add_breadcrumb(request, "/modules/%s/remove" % module._module_id, "Remove")
            return page.render(alerts=webinterface.get_alerts(),
                               module=module,
                               )


        @webapp.route('/<string:module_id>/remove', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_modules_remove_post(webinterface, request, session, module_id):
            try:
                module = webinterface._Modules[module_id]
            except Exception as e:
                webinterface.add_alert('Module ID was not found.', 'warning')
                return webinterface.redirect(request, '/modules/index')

            confirm = request.args.get('confirm')[0]
            if confirm != "remove":
                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/remove.html')
                webinterface.add_alert('Must enter "disable" in the confirmation box to remove the module.', 'warning')
                return page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        )

            results = yield webinterface._Modules.remove_module(module._module_id)

            if results['status'] == 'failed':
                webinterface.add_alert(results['apimsghtml'], 'warning')

                page = webinterface.get_template(request, webinterface._dir + 'pages/modules/remove.html')
                return page.render(alerts=webinterface.get_alerts(),
                                        module=module,
                                        )

            msg = {
                'header': 'Module Removed',
                'label': 'Module configuration updated successfully',
                'description': '',
            }

            webinterface._Notifications.add({'title': 'Restart Required',
                                             'message': 'Module removed. A system <strong><a  class="confirm-restart" href="#" title="Restart Yombo Gateway">restart is required</a></strong> to take affect.',
                                             'source': 'Web Interface',
                                             'persist': False,
                                             'priority': 'high',
                                             'always_show': True,
                                             'always_show_allow_clear': False,
                                             'id': 'reboot_required',
                                             'local': True,
                                             })

            page = webinterface.get_template(request, webinterface._dir + 'pages/reboot_needed.html')
            return page.render(alerts=webinterface.get_alerts(),
                                    msg=msg,
                                    )
