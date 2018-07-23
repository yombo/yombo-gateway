# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth

def route_statistics(webapp):
    with webapp.subroute("/statistics") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_statistics(webinterface, request, session):
            session.has_access('statistic:*', 'view', raise_error=True)
            return webinterface.redirect(request, '/statistics/index')

        @webapp.route('/index')
        @require_auth()
        @inlineCallbacks
        def page_statistics_index(webinterface, request, session):
            session.has_access('statistic:*', 'view', raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/statistics/index.html')
            system_stats = yield webinterface._Libraries['localdb'].get_distinct_stat_names(search_name_start='lib.')
            device_stats = yield webinterface._Libraries['localdb'].get_distinct_stat_names(search_name_start='devices.')
            energy_stats = yield webinterface._Libraries['localdb'].get_distinct_stat_names(search_name_start='energy.')

            return page.render(
                alerts=webinterface.get_alerts(),
                system_stats=system_stats,
                device_stats=device_stats,
                energy_stats=energy_stats,
            )
