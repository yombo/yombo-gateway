"""
Loads the various routes into the :ref:`WebInterface <webinterface>` library.

Assets:
/css/, /img/,

Core Routes:
/frontend/ - Items needed for the frontend applications.
/lib/ - library data - Mostly handled by generic routes.
/mod/ - module data - Mostly handled by generic routes and extended by the module.
/sys/ - system data - Handled by the route->system file.
/user/ - Current user items - Handled by the route->system file.
/yombo/ - Lookup items from yombo api.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/webinterface/mixins/loadroutes.html>`_
"""
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants.permissions import AUTH_PLATFORMS
from yombo.core.log import get_logger

# Import webinterface routes
from yombo.lib.webinterface.routes.home import route_home
from yombo.lib.webinterface.routes.system import route_system
from yombo.lib.webinterface.routes.system_sso import route_system_sso
from yombo.lib.webinterface.routes.user import route_user

# Import routes.
from yombo.lib.webinterface.routes.api_v1.authkeys import route_api_v1_authkeys
from yombo.lib.webinterface.routes.api_v1.devices import route_api_v1_devices
from yombo.lib.webinterface.routes.api_v1.frontend import route_api_v1_frontend
from yombo.lib.webinterface.routes.api_v1.mosquitto_auth import route_api_v1_mosquitto_auth
from yombo.lib.webinterface.routes.api_v1.system import route_api_v1_system
from yombo.lib.webinterface.routes.api_v1.current_user import route_api_v1_current_user
from yombo.lib.webinterface.routes.api_v1.web_stream import route_api_v1_web_stream
from yombo.lib.webinterface.routes.api_v1.yombo_resources import route_api_v1_yombo_resources
# from yombo.lib.webinterface.routes.api_v1.server import route_api_v1_server

# Generic API routes.
from yombo.lib.webinterface.routes.api_v1.debug import route_api_v1_debug
from yombo.lib.webinterface.routes.api_v1.generic_library_routes import route_api_v1_generic_library_routes

from yombo.utils.hookinvoke import global_invoke_all


# # from yombo.lib.webinterface.routes.api_v1.camera import route_api_v1_camera
# # from yombo.lib.webinterface.routes.api_v1.events import route_api_v1_events
# # from yombo.lib.webinterface.routes.api_v1.gateway import route_api_v1_gateway
# # from yombo.lib.webinterface.routes.api_v1.module import route_api_v1_module
# # from yombo.lib.webinterface.routes.api_v1.notification import route_api_v1_notification
# from yombo.lib.webinterface.routes.api_v1.scenes import route_api_v1_scenes
# from yombo.lib.webinterface.routes.api_v1.server import route_api_v1_server
# # from yombo.lib.webinterface.routes.api_v1.statistics import route_api_v1_statistics
# # from yombo.lib.webinterface.routes.api_v1.storage import route_api_v1_storage
# # from yombo.lib.webinterface.routes.api_v1.web_logs import route_api_v1_web_logs


logger = get_logger("library.webinterface.mixins.load_routes")


class LoadRoutesMixin:
    """
    Loads all the various routes into the Klein webapp.
    """
    def add_routes(self, reference):
        """
        Add additional routes. See any of the routes file to examples.

        :param reference:
        :return:
        """
        reference(self.webapp)

    @inlineCallbacks
    def webinterface_load_routes(self):
        for path, data in AUTH_PLATFORMS.items():
            if data["resource_type"] is None:
                continue

            results = {
                "auth_platform": path,
                "actions": data["actions"]["possible"],
                "resource_name": f"_{data['resource_name']}",
                "resource_label": data["resource_label"],
            }
            if data["resource_type"].startswith("library"):
                self.generic_router_list["libraries"][data["resource_label"]] = results
            if data["resource_type"].startswith("module"):
                self.generic_router_list["modules"][data["resource_label"]] = results

        # Load API routes
        route_api_v1_authkeys(self.webapp)
        route_api_v1_devices(self.webapp)
        route_api_v1_frontend(self.webapp)
        if self._Mosquitto.enabled is True:
            route_api_v1_mosquitto_auth(self.webapp)
        route_api_v1_system(self.webapp)
        route_api_v1_current_user(self.webapp)
        route_api_v1_web_stream(self.webapp, self)
        route_api_v1_yombo_resources(self.webapp)
        # To delete/fix.
        # route_api_v1_scenes(self.webapp)
        # route_api_v1_camera(self.webapp)
        # route_api_v1_events(self.webapp)
        # route_api_v1_statistics(self.webapp)
        # route_api_v1_web_logs(self.webapp)
        # The generic api routes are added last so as not to supersede of any specifically defined routes.

        # Generic API routes.
        route_api_v1_debug(self.webapp)
        route_api_v1_generic_library_routes(self.webapp)

        # Load web server routes
        route_home(self.webapp)
        route_system(self.webapp)
        route_system_sso(self.webapp)
        route_user(self.webapp)
        if self._Loader.operating_mode != "run":
            from yombo.lib.webinterface.routes.restore import route_restore
            from yombo.lib.webinterface.routes.setup_wizard import route_setup_wizard
            route_setup_wizard(self.webapp)
            route_restore(self.webapp)

        # Load additional module routes.
        add_on_menus = yield global_invoke_all("_webinterface_add_routes_", called_by=self)

        for component, options in add_on_menus.items():
            if "routes" in options:
                if isinstance(options["routes"], str):
                    options["routes"] = [options["routes"]]
                for route in options["routes"]:
                    # print(f"load_routes, route: {route}")
                    route(self.webapp)
