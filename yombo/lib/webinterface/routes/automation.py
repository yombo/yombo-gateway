from yombo.lib.webinterface.auth import require_auth

def route_automation(webapp):
    with webapp.subroute("/automation") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_automation(webinterface, request, session):
            return webinterface.redirect(request, '/automation/index')

        @webapp.route('/index')
        @require_auth()
        def page_automation_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/automation/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               rules=webinterface._Loader.loadedLibraries['automation'].rules,
                               )

        
        @webapp.route('/<string:automation_id>/details')
        @require_auth()
        def page_automation_details(webinterface, request, session, automation_id):
            try:
                device = webinterface._DevicesLibrary[automation_id]
            except:
                webinterface.add_alert('Device ID was not found.', 'warning')
                return webinterface.redirect(request, '/automation/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/automation/device.html')
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               commands=webinterface._Commands,
                               )

        @webapp.route('/platforms')
        @require_auth()
        def page_automation_platforms(webinterface, request, session):

            page = webinterface.get_template(request, webinterface._dir + 'pages/automation/platforms.html')
            sources = webinterface._Loader.loadedLibraries['automation'].sources  # List of source processors
            filters = webinterface._Loader.loadedLibraries['automation'].filters # List of filter processors
            actions = webinterface._Loader.loadedLibraries['automation'].actions  # List of actionprocessors

            return page.render(alerts=webinterface.get_alerts(),
                               source_platforms=sources,
                               filter_platforms=filters,
                               action_platforms=actions,
                               )

        @webapp.route('/add_rule')
        @require_auth()
        def page_automation_add_new(webinterface, request, session):

            page = webinterface.get_template(request, webinterface._dir + 'pages/automation/add_rule.html')
            sources = webinterface._Loader.loadedLibraries['automation'].sources  # List of source processors
            filters = webinterface._Loader.loadedLibraries['automation'].filters # List of filter processors
            actions = webinterface._Loader.loadedLibraries['automation'].actions  # List of actionprocessors

            return page.render(alerts=webinterface.get_alerts(),
                               source_platforms=sources,
                               filter_platforms=filters,
                               action_platforms=actions,
                               )