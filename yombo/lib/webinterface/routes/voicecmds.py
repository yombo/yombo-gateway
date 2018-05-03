from yombo.lib.webinterface.auth import require_auth

def route_voicecmds(webapp):
    with webapp.subroute("/voicecmds") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_voicecmds(webinterface, request, session):
            return webinterface.redirect(request, '/voicecmds/index')

        @webapp.route('/index')
        @require_auth()
        def page_voicecmds_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/voicecmds/index.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/voicecmds", "Voice Commands")
            return page.render(alerts=webinterface.get_alerts(),
                               voicecmds=webinterface._VoiceCmds.get_all(),
                               )

        @webapp.route('/<string:voicecmd_id>/details')
        @require_auth()
        def page_voicecmds_details(webinterface, request, session, voicecmd_id):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/voicecmds/details.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/voicecmds", "Voice Commands")
            webinterface.add_breadcrumb(request, "/voicecmds/%s/details" % voicecmd_id, "Details")
            return page.render(alerts=webinterface.get_alerts(),
                               # commands=webinterface._Commands.get_public_commands(),
                               page_label='Public Commands',
                               page_description='Puiblicly available commands.'
                               )
