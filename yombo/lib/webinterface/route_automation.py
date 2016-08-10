
def route_automation(webapp):
    with webapp.subroute("/automation") as webapp:
        @webapp.route('/')
        def page_automation(webinterface, request):
            return webinterface.redirect(request, '/automation/index')

        @webapp.route('/index')
        def page_automation_index(webinterface, request):
            page = webinterface.get_template(request, webinterface._dir + 'pages/automation/index.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               data=webinterface.data,
                               alerts=webinterface.get_alerts(),
                               rules=webinterface.loader.loadedLibraries['automation'].rules,
                               )

        
        @webapp.route('/details/<string:automation_id>')
        def page_automation_details(webinterface, request, automation_id):

            try:
                device = webinterface._DevicesLibrary[devicautomation_ide_id]
            except:
                webinterface.add_alert('Device ID was not found.', 'warning')
                return webinterface.redirect(request, '/automation/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/automation/device.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               data=webinterface.data,
                               alerts=webinterface.get_alerts(),
                               device=device,
                               commands=webinterface._Commands,
                               )
    
        @webapp.route('/edit/<string:device_id>')
        def page_devices_edit(webinterface, request, device_id):

            try:
                device = webinterface._DevicesLibrary[device_id]
            except:
                webinterface.add_alert('Device ID was not found.', 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/device.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               data=webinterface.data,
                               alerts=webinterface.get_alerts(),
                               device=device,
                               commands=webinterface._Commands,
                               )