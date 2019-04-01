from yombo.core.exceptions import YomboNoAccess
from yombo.lib.webinterface.auth import require_auth

def route_atoms(webapp):
    with webapp.subroute("/atoms") as webapp:
        @webapp.route("/")
        @require_auth()
        def page_atoms(webinterface, request, session):
            return webinterface.redirect(request, "/atoms/index")

        @webapp.route("/index")
        @require_auth()
        def page_lib_atoms_index(webinterface, request, session):
            session.has_access("atom", "*", "view")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/atoms/index.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/info", "Info")
            webinterface.add_breadcrumb(request, "/atoms/index", "Atoms")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route("/<string:gateway_id>/<string:atom_name>/details")
        @require_auth()
        def page_lib_atoms_details(webinterface, request, session, gateway_id, atom_name):
            session.has_access("atom", atom_name, "view")
            try:
                atom = webinterface._Atoms.get(atom_name, full=True, gateway_id=gateway_id)
            except Exception as e:
                webinterface.add_alert(f"Atom Name was not found.  {atom_name}", "warning")
                redirect = webinterface.redirect(request, "/atoms/index")
                return redirect
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/atoms/details.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/info", "Info")
            webinterface.add_breadcrumb(request, "/atoms/index", "Atoms")
            webinterface.add_breadcrumb(request, f"/atoms/{gateway_id}/{atom_name}/details", atom_name)
            page = page.render(alerts=webinterface.get_alerts(),
                               atom=atom,
                               atom_to_human=webinterface._Atoms.convert_to_human,
                               )
            return page
