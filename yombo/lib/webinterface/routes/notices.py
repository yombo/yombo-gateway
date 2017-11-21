from yombo.lib.webinterface.auth import require_auth

def route_notices(webapp):
    with webapp.subroute("/notifications") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_modules(webinterface, request, session):
            return webinterface.redirect(request, '/notifications/index')

        @webapp.route('/index')
        @require_auth()
        def page_notifications_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/notifications/index.html')
            return page.render(alerts=webinterface.get_alerts())

        @webapp.route('/<string:notification_id>/details')
        @require_auth()
        def page_notifications_details(webinterface, request, session, notification_id):
            page = webinterface.get_template(request, webinterface._dir + 'pages/notifications/details.html')
            try:
                webinterface._Notifications.ack(notification_id)
                notice = webinterface._Notifications[notification_id]
            except:
                webinterface.add_alert('Notification ID was not found.', 'warning')
                return webinterface.redirect(request, '/notifications/index')
            return page.render(alerts=webinterface.get_alerts(),
                               notice=notice,
                               )

        @webapp.route('/<string:notification_id>/delete')
        @require_auth()
        def page_notifications_edit(webinterface, request, session, module_id):
            page = webinterface.get_template(request, webinterface._dir + 'pages/notifications/delete.html')
            return page.render(alerts=webinterface.get_alerts(),
                               notice=webinterface._Notifications[notification_id],
                               )
