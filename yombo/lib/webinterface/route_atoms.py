from yombo.lib.webinterface.auth import require_auth

def route_atoms(webapp):
    with webapp.subroute("/atoms") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_atoms(webinterface, request, session):
            return webinterface.redirect(request, '/atoms/index')

        @webapp.route('/index')
        @require_auth()
        def page_lib_atoms_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/atoms/index.html')
            # i18n = webinterface.i18n(request)
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/atoms/index", "Atoms")
            return page.render(alerts=webinterface.get_alerts(),
                               atoms=webinterface._Libraries['atoms'].get_atoms(),
                               # _=i18n,
                               )

        @webapp.route('/<string:atom_name>/details')
        @require_auth()
        def page_lib_atoms_details(webinterface, request, session, atom_name):
            try:
                atom = webinterface._Atoms.get(atom_name, full=True)
            except Exception as e:
                webinterface.add_alert('Atom Name was not found.  %s' % atom_name, 'warning')
                redirect = webinterface.redirect(request, '/atoms/index')
                return redirect
            page = webinterface.get_template(request, webinterface._dir + 'pages/atoms/details.html')
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/atoms/index", "Atoms")
            webinterface.add_breadcrumb(request, "/atoms/%s/details" % atom_name, atom_name)
            page = page.render(alerts=webinterface.get_alerts(),
                               atom=atom,
                               atom_to_human=webinterface._Atoms.convert_to_human,
                               )
            return page