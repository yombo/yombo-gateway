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
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/automation/index", "Automation")
            page = webinterface.get_template(request, webinterface._dir + 'pages/automation/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )

        
        @webapp.route('/<string:automation_id>/details')
        @require_auth()
        def page_automation_details(webinterface, request, session, automation_id):
            try:
                device = webinterface._Devices[automation_id]
            except:
                webinterface.add_alert('Device ID was not found.', 'warning')
                return webinterface.redirect(request, '/automation/index')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/automation/index", "Automation")
            webinterface.add_breadcrumb(request, "/automation/add_rul", "Rule details")
            page = webinterface.get_template(request, webinterface._dir + 'pages/automation/device.html')
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               )

        @webapp.route('/platforms')
        @require_auth()
        def page_automation_platforms(webinterface, request, session):
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/automation/index", "Automation")
            webinterface.add_breadcrumb(request, "/automation/platforms", "Platforms")
            page = webinterface.get_template(request, webinterface._dir + 'pages/automation/platforms.html')
            return page.render(alerts=webinterface.get_alerts(),
                               source_platforms=webinterface._Automation.sources,  # List of source processors,
                               filter_platforms=webinterface._Automation.filters,  # List of filter processors,
                               action_platforms=webinterface._Automation.actions,  # List of actionprocessors,
                               )

        @webapp.route('/add_rule')
        @require_auth()
        def page_automation_add_new(webinterface, request, session):
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/automation/index", "Automation")
            webinterface.add_breadcrumb(request, "/automation/add_rule", "Add rule")
            page = webinterface.get_template(request, webinterface._dir + 'pages/automation/add_rule.html')
            return page.render(alerts=webinterface.get_alerts(),
                               source_platforms=webinterface._Automation.sources,  # List of source processors,
                               filter_platforms=webinterface._Automation.filters,  # List of filter processors,
                               action_platforms=webinterface._Automation.actions,  # List of actionprocessors,
                               )