from yombo.lib.webinterface.auth import require_auth_pin, require_auth

def route_devices(webapp):
    with webapp.subroute("/devices") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_devices(webinterface, request, session):
            return webinterface.redirect(request, '/devices/index')

        @webapp.route('/index')
        @require_auth()
        def page_devices_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/index.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               data=webinterface.data,
                               alerts=webinterface.get_alerts(),
                               devices=webinterface._Libraries['devices']._devicesByUUID,
                               )

        @webapp.route('/delayed_commands')
        @require_auth()
        def page_devices_delayed_commands(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/delayed_commands.html')
            print "delayed queue active: %s" % webinterface._Devices.delay_queue_active
            return page.render(alerts=webinterface.get_alerts(),
                               delayed_commands=webinterface._Devices.delay_queue_active,
                               )

        @webapp.route('/details/<string:device_id>')
        @require_auth()
        def page_devices_details(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices[device_id]
            except Exception, e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/details.html')
            print device.available_commands()
            print device.device_variables
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               devicetypes=webinterface._DeviceTypes,
                               commands=webinterface._Commands,
                               )
    
        @webapp.route('/edit/<string:device_id>')
        @require_auth()
        def page_devices_edit(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices.get(device_id)
            except Exception, e:
                print "device find errr: %s" % e
                webinterface.add_alert('Device ID was not found.', 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/edit.html')
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               commands=webinterface._Commands,
                               )