# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth

def route_states(webapp):
    with webapp.subroute("/states") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_states(webinterface, request, session):
            session.has_access('state:*', 'view', raise_error=True)
            return webinterface.redirect(request, '/states/index')

        @webapp.route('/index')
        @require_auth()
        def page_states_index(webinterface, request, session):
            session.has_access('state:*', 'view', raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/states/index.html')
            # i18n = webinterface.i18n(request)
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/info", "Info")
            webinterface.add_breadcrumb(request, "/states/index", "States")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/<string:gateway_id>/<string:state_name>/details')
        @require_auth()
        @inlineCallbacks
        def page_states_details(webinterface, request, session, gateway_id, state_name):
            session.has_access('state:%s' % state_name, 'view', raise_error=True)
            try:
                state = webinterface._States.get(state_name, full=True, gateway_id=gateway_id)
            except Exception as e:
                webinterface.add_alert('State Name was not found.  %s' % state_name, 'warning')
                webinterface.add_breadcrumb(request, "/info", "Info")
                redirect = webinterface.redirect(request, '/states/index')
                return redirect
            state_history = yield webinterface._States.get_history(state_name, 0, 400)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/states/details.html')
            if state_history is None:
                state_history = []
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/info", "Info")
            webinterface.add_breadcrumb(request, "/states/index", "States")
            webinterface.add_breadcrumb(request, "/states/%s/details" % state_name, state_name)
            page = page.render(alerts=webinterface.get_alerts(),
                               state=state,
                               state_history=state_history,
                               state_to_human=webinterface._States.convert_to_human,
                               )
            return page
