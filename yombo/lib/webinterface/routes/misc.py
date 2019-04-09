"""
Handles misc page requests
"""
# Import Yombo libraries
from yombo.lib.webinterface.auth import run_first


def route_misc(webapp):
    with webapp.subroute("/misc") as webapp:

        @webapp.route("/gateway_setup")
        @run_first()
        def misc_gateway_setup(webinterface, request, session):
            """
            Displayed when the gateway is new and needs to be installed. Presents the user with the option
            to run the setup wizard or restore from a backup.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            return webinterface.render(request, session, webinterface.wi_dir + "/pages/misc/gateway_setup.html")
