from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth, run_first

def route_devtools_debug(webapp):
    with webapp.subroute("/devtools/debug") as webapp:

        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/", "Home")
            webinterface.add_breadcrumb(request, "/devtools/debug", "Debug")

        @webapp.route('/')
        @require_auth()
        def page_devtools2(webinterface, request, session):
            return webinterface.redirect(request, '/devtools/debug/index')


        @webapp.route('/index')
        @require_auth()
        def page_devtools_debug(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/index.html')
            root_breadcrumb(webinterface, request)
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/commands')
        @require_auth()
        def page_devtools_debug_commands(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/commands/index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/debug/commands", "Commands")
            return page.render(alerts=webinterface.get_alerts(),
                               commands=webinterface._Commands.commands,
                               )

        @webapp.route('/commands/<string:command_id>/details')
        @require_auth()
        def page_devtools_debug_commands_details(webinterface, request, session, command_id):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/commands/details.html')
            command = webinterface._Commands.commands[command_id]
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/debug/commands", "Commands")
            webinterface.add_breadcrumb(request, "/devtools/debug/commands/%s/details" % command_id, command.label)
            return page.render(alerts=webinterface.get_alerts(),
                               command=command,
                               )

        @webapp.route('/device_types')
        @require_auth()
        def page_devtools_debug_device_type(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/device_types/index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/debug/device_types", "Device Types")
            return page.render(alerts=webinterface.get_alerts(),
                               device_types=webinterface._DeviceTypes.device_types,
                               )

        @webapp.route('/device_types/<string:device_type_id>/details')
        @require_auth()
        def page_devtools_debug_device_type_details(webinterface, request, session, device_type_id):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/device_types/details.html')
            device_type = webinterface._DeviceTypes.device_types[device_type_id]
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/debug/device_types", "Device Types")
            webinterface.add_breadcrumb(request, "/devtools/debug/device_types/%s/details" % device_type_id, device_type.label)
            return page.render(alerts=webinterface.get_alerts(),
                               device_type=device_type,
                               devices=webinterface._Devices,
                               )

        @webapp.route('/hooks_called_libraries')
        @require_auth()
        def page_devtools_debug_hooks_called_libraries(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/hooks_called_libraries.html')
            return page.render(alerts=webinterface.get_alerts(),
                               hooks_called=webinterface._Loader.hook_counts
                               )

        @webapp.route('/hooks_called_modules')
        @require_auth()
        def page_devtools_debug_hooks_called_modules(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/hooks_called_modules.html')
            return page.render(alerts=webinterface.get_alerts(),
                               hooks_called=webinterface._Modules.hook_counts
                               )

        @webapp.route('/nodes')
        @require_auth()
        def page_devtools_debug_nodes(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/nodes/index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/debug/nodes", "Nodes")
            return page.render(alerts=webinterface.get_alerts(),
                               nodes=webinterface._Nodes.nodes,
                               )

        @webapp.route('/nodes/<string:node_id>/details')
        @require_auth()
        def page_devtools_debug_nodes_details(webinterface, request, session, node_id):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/nodes/details.html')
            node = webinterface._Nodes.nodes[node_id]
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/debug/nodes", "Nodes")
            webinterface.add_breadcrumb(request, "/devtools/debug/nodes/%s/details" % node_id, node.label)
            return page.render(alerts=webinterface.get_alerts(),
                               node=node,
                               )

        @webapp.route('/modules')
        @require_auth()
        def page_devtools_debug_modules(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/modules/index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/debug/modules", "Modules")
            return page.render(alerts=webinterface.get_alerts(),
                               modules=webinterface._Modules.modules
                               )

        @webapp.route('/modules/<string:module_id>/details')
        @require_auth()
        def page_devtools_debug_modules_details(webinterface, request, session, module_id):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/modules/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/debug/modules", "Modules")
            webinterface.add_breadcrumb(request, "/devtools/debug/modules/%s/details" % webinterface._Modules.modules[module_id]._module_id, webinterface._Modules.modules[module_id]._label)
            return page.render(alerts=webinterface.get_alerts(),
                               module=webinterface._Modules.modules[module_id],
                               module_devices=webinterface._DeviceTypes.module_devices(module_id),
                               device_types=webinterface._DeviceTypes,
                               devices=webinterface._Devices,
                               )

        @webapp.route('/statistic_bucket_lifetimes')
        @require_auth()
        def page_devtools_debug_statistic_bucket_lifetimes(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/statistic_bucket_lifetimes.html')
            return page.render(alerts=webinterface.get_alerts(),
                               bucket_lifetimes=webinterface._Statistics.bucket_lifetimes
                               )

        @webapp.route('/sslcerts')
        @require_auth()
        def page_devtools_debug_sslcerts(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/sslcerts/index.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/debug/sslcerts", "SSL Certs")
            return page.render(alerts=webinterface.get_alerts(),
                               sslcerts=webinterface._SSLCerts.managed_certs,
                               )

        @webapp.route('/sslcerts/<string:cert_name>/details')
        @require_auth()
        def page_devtools_debug_sslcerts_details(webinterface, request, session, cert_name):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/debug/sslcerts/details.html')
            sslcert = webinterface._SSLCerts.managed_certs[cert_name]
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/devtools/debug/sslcerts", "SSL Certs")
            webinterface.add_breadcrumb(request, "/devtools/debug/sslcerts/%s/details" % sslcert.sslname, sslcert.sslname)
            return page.render(alerts=webinterface.get_alerts(),
                               sslcert=sslcert,
                               )