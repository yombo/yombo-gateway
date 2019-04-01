import json

from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth


def route_debug(webapp):
    with webapp.subroute("/debug") as webapp:

        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/", "Home")
            webinterface.add_breadcrumb(request, "/debug", "Debug")

        @webapp.route("/")
        @require_auth()
        def page_devtools2(webinterface, request, session):
            return webinterface.redirect(request, "/debug/index")

        @webapp.route("/index")
        @require_auth()
        def page_devtools_debug(webinterface, request, session):
            session.has_access("debug", "*", "view")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/index.html")
            root_breadcrumb(webinterface, request)
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route("/auth_platforms")
        @require_auth()
        def page_devtools_debug_auth_platforms(webinterface, request, session):
            session.has_access("debug", "*", "cache")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/user/auth_platforms.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/auth_platforms", "Auth Platforms")
            return page.render(
                alerts=webinterface.get_alerts(),
                auth_platforms=json.dumps(
                        webinterface._Users.auth_platforms, sort_keys=True, indent=4, separators=(",", ": ")
                    ),
                )

        @webapp.route("/cache")
        @require_auth()
        def page_devtools_debug_cache(webinterface, request, session):
            session.has_access("debug", "*", "cache")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/cache/index.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/cache", "Cache")
            return page.render(alerts=webinterface.get_alerts(),
                               caches=webinterface._Cache.caches,
                               )

        @webapp.route("/commands")
        @require_auth()
        def page_devtools_debug_commands(webinterface, request, session):
            session.has_access("debug", "*", "commands")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/commands/index.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/commands", "Commands")
            return page.render(alerts=webinterface.get_alerts(),
                               commands=webinterface._Commands.commands,
                               )

        @webapp.route("/commands/<string:command_id>/details")
        @require_auth()
        def page_devtools_debug_commands_details(webinterface, request, session, command_id):
            command_id = webinterface._Validate.id_string(command_id)
            session.has_access("debug", command_id, "commands")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/commands/details.html")
            command = webinterface._Commands.commands[command_id]
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/commands", "Commands")
            webinterface.add_breadcrumb(request, f"/debug/commands/{command_id}/details", command.label)
            return page.render(alerts=webinterface.get_alerts(),
                               command=command,
                               )

        @webapp.route("/crontab")
        @require_auth()
        def page_devtools_debug_commands(webinterface, request, session):
            session.has_access("debug", "*", "crontab")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/crontab/index.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/crontab", "Crontab")
            return page.render(alerts=webinterface.get_alerts(),
                               crontabs=webinterface._CronTab.cron_tasks,
                               )

        @webapp.route("/device_types")
        @require_auth()
        def page_devtools_debug_device_type(webinterface, request, session):
            session.has_access("debug", "*", "device_types")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/device_types/index.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/device_types", "Device Types")
            return page.render(alerts=webinterface.get_alerts(),
                               device_types=webinterface._DeviceTypes.device_types,
                               )

        @webapp.route("/device_types/<string:device_type_id>/details")
        @require_auth()
        def page_devtools_debug_device_type_details(webinterface, request, session, device_type_id):
            device_type_id = webinterface._Validate.id_string(device_type_id)
            session.has_access("debug", device_type_id, "device_types")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/device_types/details.html")
            device_type = webinterface._DeviceTypes.device_types[device_type_id]
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/device_types", "Device Types")
            webinterface.add_breadcrumb(request, f"/debug/device_types/{device_type_id}/details", device_type.label)
            return page.render(alerts=webinterface.get_alerts(),
                               device_type=device_type,
                               devices=webinterface._Devices,
                               )

        @webapp.route("/events/event_types")
        @require_auth()
        def page_devtools_debug_event_types(webinterface, request, session):
            session.has_access("debug", "*", "event_types")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/events/eventtypes.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/events/event_types", "Event Types")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route("/hooks_called_libraries")
        @require_auth()
        def page_devtools_debug_hooks_called_libraries(webinterface, request, session):
            session.has_access("debug", "*", "libraries")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/hooks_called_libraries.html")
            return page.render(alerts=webinterface.get_alerts(),
                               hooks_called=webinterface._Loader.hook_counts
                               )

        @webapp.route("/hooks_called_modules")
        @require_auth()
        def page_devtools_debug_hooks_called_modules(webinterface, request, session):
            session.has_access("debug", "*", "modules")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/hooks_called_modules.html")
            return page.render(alerts=webinterface.get_alerts(),
                               hooks_called=webinterface._Modules.hook_counts
                               )

        @webapp.route("/locales/files")
        @require_auth()
        def page_devtools_debug_locales_files_index(webinterface, request, session):
            session.has_access("debug", "*", "locales", raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/locales/files.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/locales", "Locales - Files")
            return page.render(
                alerts=webinterface.get_alerts(),
                files=webinterface._Localize.files,
                )

        @webapp.route("/locales/translations")
        @require_auth()
        def page_devtools_debug_translations_index(webinterface, request, session):
            session.has_access("debug", "*", "locales", raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/locales/translations.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/locales", "Locales - Translations")
            return page.render(
                alerts=webinterface.get_alerts(),
                files=webinterface._Localize.files,
                )

        @webapp.route("/locales/translations_bottom/<string:locale>")
        @require_auth()
        @inlineCallbacks
        def page_devtools_debug_translations_bottom(webinterface, request, session, locale):
            session.has_access("debug", "*", "locales", raise_error=True)
            files = webinterface._Localize.files
            if locale not in files:
                page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/locales/translations_bottom_invalid.html")
                return page.render(message="Invalid locale provided.")

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/locales/translations_bottom.html")
            locale = yield webinterface._Localize.locale_to_dict(locale)
            return page.render(
                alerts=webinterface.get_alerts(),
                locale=locale,
            )

        @webapp.route("/modules")
        @require_auth()
        def page_devtools_debug_modules(webinterface, request, session):
            session.has_access("debug", "*", "modules")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/modules/index.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/modules", "Modules")
            return page.render(alerts=webinterface.get_alerts(),
                               modules=webinterface._Modules.modules
                               )

        @webapp.route("/modules/<string:module_id>/details")
        @require_auth()
        def page_devtools_debug_modules_details(webinterface, request, session, module_id):
            module_id = webinterface._Validate.id_string(module_id)
            session.has_access("debug", module_id, "nodes")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/modules/details.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/modules", "Modules")
            webinterface.add_breadcrumb(request,
                                        f"/debug/modules/{webinterface._Modules.modules[module_id]._module_id}/details", webinterface._Modules.modules[module_id]._label)
            return page.render(alerts=webinterface.get_alerts(),
                               module=webinterface._Modules.modules[module_id],
                               module_devices=webinterface._DeviceTypes.module_devices(module_id),
                               device_types=webinterface._DeviceTypes,
                               devices=webinterface._Devices,
                               )

        @webapp.route("/nodes")
        @require_auth()
        def page_devtools_debug_nodes(webinterface, request, session):
            session.has_access("debug", "*", "nodes")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/nodes/index.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/nodes", "Nodes")
            return page.render(alerts=webinterface.get_alerts(),
                               nodes=webinterface._Nodes.nodes,
                               )

        @webapp.route("/nodes/<string:node_id>/details")
        @require_auth()
        def page_devtools_debug_nodes_details(webinterface, request, session, node_id):
            node_id = webinterface._Validate.id_string(node_id)
            session.has_access("debug", node_id, "nodes")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/nodes/details.html")
            node = webinterface._Nodes.nodes[node_id]
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/nodes", "Nodes")
            webinterface.add_breadcrumb(request, f"/debug/nodes/{node_id}/details", node.label)
            return page.render(alerts=webinterface.get_alerts(),
                               node=node,
                               )

        @webapp.route("/sslcerts")
        @require_auth()
        def page_devtools_debug_sslcerts(webinterface, request, session):
            session.has_access("debug", "*", "sslcerts")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/sslcerts/index.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/sslcerts", "SSL Certs")
            return page.render(alerts=webinterface.get_alerts(),
                               sslcerts=webinterface._SSLCerts.managed_certs,
                               )

        @webapp.route("/sslcerts/<string:cert_name>/details")
        @require_auth()
        def page_devtools_debug_sslcerts_details(webinterface, request, session, cert_name):
            cert_name = webinterface._Validate.id_string(cert_name)
            session.has_access("debug", cert_name, "sslcerts")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/sslcerts/details.html")
            sslcert = webinterface._SSLCerts.managed_certs[cert_name]
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/sslcerts", "SSL Certs")
            webinterface.add_breadcrumb(request, f"/debug/sslcerts/{sslcert.sslname}/details", sslcert.sslname)
            return page.render(alerts=webinterface.get_alerts(),
                               sslcert=sslcert,
                               )

        @webapp.route("/statistic_bucket_lifetimes")
        @require_auth()
        def page_devtools_debug_statistic_bucket_lifetimes(webinterface, request, session):
            session.has_access("debug", "*", "statistics")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/statistic_bucket_lifetimes.html")
            return page.render(alerts=webinterface.get_alerts(),
                               bucket_lifetimes=webinterface._Statistics.bucket_lifetimes
                               )

        @webapp.route("/requirements")
        @require_auth()
        def page_devtools_debug_requirements(webinterface, request, session):
            session.has_access("debug", "*", "requirements")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/debug/requirements/index.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/debug/requirements", "Requirements")
            return page.render(alerts=webinterface.get_alerts(),
                               requirements=webinterface._Loader.requirements
                               )

