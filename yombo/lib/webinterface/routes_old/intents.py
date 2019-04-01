# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth

def route_intents(webapp):
    with webapp.subroute("/intents") as webapp:
        @webapp.route("/")
        @require_auth()
        def page_intents(webinterface, request, session):
            session.has_access("intent", "*", "view", raise_error=True)
            return webinterface.redirect(request, "/intents/index")

        @webapp.route("/index")
        @require_auth()
        def page_intents_index(webinterface, request, session):
            session.has_access("intent", "*", "view", raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/intents/index.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/info", "Info")
            webinterface.add_breadcrumb(request, "/intents/index", "Intents")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route("/<string:intent_id>/details")
        @require_auth()
        def page_intents_details(webinterface, request, session, intent_id):
            try:
                intent = webinterface._Intents.get(intent_id)
            except KeyError as e:
                session.has_access("intent", "*", "view", raise_error=True)
                webinterface.add_alert(f"Intent ID was not found.  {intent_id}", "warning")
                webinterface.add_breadcrumb(request, "/info", "Info")
                redirect = webinterface.redirect(request, "/intents/index")
                return redirect
            session.has_access("intent", intent_id, "view", raise_error=True)

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/intents/details.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/info", "Info")
            webinterface.add_breadcrumb(request, "/intents/index", "Intents")
            webinterface.add_breadcrumb(request, f"/intents/{intent_id}/details", intent_id)
            page = page.render(alerts=webinterface.get_alerts(),
                               intent=intent,
                               )
            return page
