# Import twisted libraries

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth

def route_gateways(webapp):
    with webapp.subroute("/gateways") as webapp:
        @webapp.route("/")
        @require_auth()
        def page_gateways(webinterface, request, session):
            return webinterface.redirect(request, "/gateways/index")

        @webapp.route("/index")
        @require_auth()
        def page_lib_gateways_index(webinterface, request, session):
            session.has_access("gateway", "*", "view")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/gateways/index.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/gateways/index", "Gateways")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route("/<string:gateway_id>/details")
        @require_auth()
        def page_lib_gateways_details(webinterface, request, session, gateway_id):
            session.has_access("gateway", gateway_id, "view")
            try:
                gateway = webinterface._Gateways.get(gateway_id)
            except Exception as e:
                webinterface.add_alert(f"Gateway was not found.  {gateway_id}", "warning")
                return webinterface.redirect(request, "/gateways/index")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/gateways/details.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/gateways/index", "Gateways")
            webinterface.add_breadcrumb(request, f"/gateways/{gateway_id}/details", gateway.label)
            return page.render(alerts=webinterface.get_alerts(),
                               gateway=gateway,
                               )
