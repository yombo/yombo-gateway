def route_devices(webapp):
    with webapp.subroute("/devices") as webapp:
        @webapp.route('/')
        def page_devices(webinterface, request):
            return webinterface.redirect(request, '/devices/index')

        @webapp.route('/index')
        def page_devices_index(webinterface, request):
            auth = webinterface.require_auth(request)
            if auth is not None:
                return auth
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/index.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               data=webinterface.data,
                               alerts=webinterface.get_alerts(),
                               devices=webinterface._Libraries['devices']._devicesByUUID,
                               )

        
        @webapp.route('/details/<string:device_id>')
        def page_devices_details(webinterface, request, device_id):
            auth = webinterface.require_auth(request)
            if auth is not None:
                return auth

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
    
        @webapp.route('/edit/<string:device_id>')
        def page_devices_edit(webinterface, request, device_id):
            auth = webinterface.require_auth(request)
            if auth is not None:
                return auth

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