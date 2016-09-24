from yombo.lib.webinterface.auth import require_auth_pin, require_auth

def route_voicecmds(webapp):
    with webapp.subroute("/voicecmds") as webapp:
        @webapp.route('/')
        @require_auth_pin()
        def page_voicecmds(webinterface, request):
            return webinterface.redirect(request, '/voicecmds/index')

        @webapp.route('/index')
        @require_auth()
        def page_voicecmds_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/voicecmds/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               voicecmds=webinterface._VoiceCmds.get_all(),
                               )

        @webapp.route('/details/<string:voicecmd_id>')
        @require_auth()
        def page_voicecmds_details(webinterface, request, session, voicecmd_id):
            page = webinterface.get_template(request, webinterface._dir + 'pages/voicecmds/details.html')
            return page.render(alerts=webinterface.get_alerts(),
                               commands=webinterface._Commands.get_public_commands(),
                               page_label='Public Commands',
                               page_description='Puiblicly available commands.'
                               )
