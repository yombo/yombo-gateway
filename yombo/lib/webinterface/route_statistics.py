from yombo.lib.webinterface.auth import require_auth_pin, require_auth

def route_statistics(webapp):
    with webapp.subroute("/statistics") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_statistics(webinterface, request, session):
            return webinterface.redirect(request, '/statistics/index')

        @webapp.route('/index')
        @require_auth()
        def page_statistics_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/statistics/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               devices=webinterface._Libraries['devices']._devicesByUUID,
                               )

        
        @webapp.route('/<string:device_id>/details')
        @require_auth()
        def page_statistics_details(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices[device_id]
            except Exception, e:
                webinterface.add_alert('Device ID was not found.  %s' % e, 'warning')
                return webinterface.redirect(request, '/devices/index')
            device_commands = device.available_commands()
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/device.html')
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               device_commands=device_commands,
                               commands=webinterface._Commands,
                               )
    
        @webapp.route('/<string:device_id>/edit')
        @require_auth()
        def page_statistics_edit(webinterface, request, session, device_id):
            try:
                device = webinterface._Devices.get(device_id)
            except Exception, e:
                # print "device find errr: %s" % e
                webinterface.add_alert('Device ID was not found.', 'warning')
                return webinterface.redirect(request, '/devices/index')
            page = webinterface.get_template(request, webinterface._dir + 'pages/devices/device.html')
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               commands=webinterface._Commands,
                               )