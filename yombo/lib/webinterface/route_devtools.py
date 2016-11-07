from yombo.lib.webinterface.auth import require_auth_pin, require_auth

def route_devtools(webapp):
    with webapp.subroute("/devtools") as webapp:
        @webapp.route('/')
        @require_auth_pin()
        def page_devtools(webinterface, request):
            return webinterface.redirect(request, '/devtools/index')

        @webapp.route('/index')
        @require_auth()
        def page_devtools_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/commands/public')
        @require_auth()
        def page_devtools_commands_public(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/commands_list.html')
            return page.render(alerts=webinterface.get_alerts(),
                               commands=webinterface._Commands.get_public_commands(),
                               page_label='Public Commands',
                               page_description='Puiblicly available commands.'
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

        @webapp.route('/command/edit/<string:device_id>')
        @require_auth()
        def page_devices_command_edit(webinterface, request, session, device_id):

            try:
                device = webinterface._DevicesLibrary[device_id]
            except:
                webinterface.add_alert('Device ID was not found.', 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/devtools/device.html')
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               commands=webinterface._Commands,
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
