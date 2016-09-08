# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue

# Import Yombo libraries
from yombo.lib.webinterface.auth import  require_auth

def route_states(webapp):
    with webapp.subroute("/states") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_states(webinterface, request, session):
            return webinterface.redirect(request, '/states/index')

        @webapp.route('/index')
        @require_auth()
        def page_states_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/states/index.html')
            strings = webinterface._Localize.get_strings(request.getHeader('accept-language'), 'states')
            return page.render(alerts=webinterface.get_alerts(),
                               states=webinterface._Libraries['states'].get_states(),
                               states_i18n=strings,
                               )

        @webapp.route('/details/<string:state_name>')
        @require_auth()
        @inlineCallbacks
        def page_states_details(webinterface, request, session, state_name):
            try:
                state = webinterface._States.get(state_name, full=True)
            except Exception, e:
                webinterface.add_alert('State Name was not found.  %s' % state_name, 'warning')
                redirect = webinterface.redirect(request, '/states/index')
                returnValue(redirect)
            state_history = yield webinterface._States.get_history(state_name, 0, 400)
            page = webinterface.get_template(request, webinterface._dir + 'pages/states/details.html')
            if state_history is None:
                state_history = []
            page = page.render(alerts=webinterface.get_alerts(),
                               state=state,
                               state_history=state_history,
                               state_to_human=webinterface._States.convert_to_human,
                               )
            returnValue(page)
