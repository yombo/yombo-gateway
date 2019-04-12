"""
This file handles the homepage, static files, and misc one-off urls.
"""
import json
import re

# Import twisted libraries
from twisted.web.static import File

# Import Yombo libraries
from yombo.constants import CONTENT_TYPE_JSON
from yombo.lib.webinterface.auth import require_auth, run_first
from yombo.utils import random_int
from yombo.utils.networking import ip_addres_in_local_network
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.home")


class NotFound(Exception):
    pass


def route_home(webapp):
    with webapp.subroute("") as webapp:

        @webapp.handle_errors(NotFound)
        @require_auth()
        def notfound(self, request, failure):
            """ This shouldn't ever be used....failsafe."""
            request.setResponseCode(404)
            return "Not found, I say!"

        @webapp.route("/robots.txt")
        def robots_txt(webinterface, request):
            return "User-agent: *\nDisallow: /\n"

        @webapp.route("/<path:catchall>", branch=True)
        @require_auth()
        def home_static_frontend_catchall(webinterface, request, session, catchall):
            """ For frontend that doesn't match anything. """
            base_headers(request)
            uri = request.uri.decode()[1:]
            logger.info("Catchall for: {uri}", uri=uri)

            if uri not in webinterface.file_cache:
                if webinterface.operating_mode != "run":
                    webinterface.redirect(request, "/")
                uri = "index"
            if uri in webinterface.file_cache:
                file = webinterface.file_cache[uri]
                if "headers" in file and len(file["headers"]) > 0:
                    for header_name, header_content in file['headers'].items():
                        request.setHeader(header_name, header_content)
                return file["data"]

        @webapp.route("/")
        @run_first()
        def home_index(webinterface, request, session):
            # print(f"zzzz webinterface.operating_mode: {webinterface.operating_mode}")
            if webinterface.operating_mode == "config":
                return webinterface.redirect(request, "/misc/config")
            elif webinterface.operating_mode == "first_run":
                logger.info("Incoming request to /, but gateway needs setup. Redirecting to gateway_setup")
                return webinterface.redirect(request, "/misc/gateway_setup")
            print(f"zzzz2 webinterface.operating_mode: {webinterface.operating_mode}")
            if session is None or session.enabled is False or session.is_valid() is False or session.has_user is False:
                return webinterface.redirect(request, "/user/login")
            # print(f"page from home: {webinterface.working_dir}/frontend/index.html")

            file = webinterface.file_cache["index"]
            if "headers" in file and len(file["headers"]) > 0:
                for header_name, header_content in file['headers'].items():
                    request.setHeader(header_name, header_content)
            return file["data"]

        @webapp.route("/nuxt.env")
        @require_auth()
        def home_nuxt_env(webinterface, request, session):
            request.responseHeaders.removeHeader("Expires")
            request.setHeader("Content-Type", CONTENT_TYPE_JSON)

            request.setHeader("Cache-Control", f"max-age=5")
            internal_http_port = webinterface._Gateways.local.internal_http_port
            internal_http_secure_port = webinterface._Gateways.local.internal_http_secure_port
            external_http_port = webinterface._Gateways.local.external_http_port
            external_http_secure_port = webinterface._Gateways.local.external_http_secure_port

            internal_http_port = internal_http_port if internal_http_port is not None else \
                webinterface._Configs.get("webinterface", "nonsecure_port", None, False)
            internal_http_secure_port = internal_http_secure_port if internal_http_secure_port is not None else \
                webinterface._Configs.get("webinterface", "secure_port", None, False)
            external_http_port = external_http_port if external_http_port is not None else \
                webinterface._Configs.get("webinterface", "nonsecure_port", None, False)
            external_http_secure_port = external_http_secure_port if external_http_secure_port is not None else \
                webinterface._Configs.get("webinterface", "secure_port", None, False)

            return json.dumps({
                "gateway_id": webinterface.gateway_id(),
                "working_dir": webinterface.working_dir,
                "internal_http_port": internal_http_port,
                "internal_http_secure_port": internal_http_secure_port,
                "external_http_port": external_http_port,
                "external_http_secure_port": external_http_secure_port,
                "api_key": webinterface._Configs.get("frontend", "api_key", "4Pz5CwKQCsexQaeUvhJnWAFO6TRa9SafnpAQfAApqy9fsdHTLXZ762yCZOct", False),
                "mqtt_port": webinterface._MQTT.server_listen_port,
                "mqtt_port_ssl": webinterface._MQTT.server_listen_port_ss_ssl,
                "mqtt_port_websockets": webinterface._MQTT.server_listen_port,
                "mqtt_port_websockets_ssl": webinterface._MQTT.server_listen_port,
                "mqtt_port": webinterface._MQTT.server_listen_port,
                "client_location":
                    "remote" if ip_addres_in_local_network(request.getClientIP()) else "local",
            })

        # @webapp.route("/<path:catchall>", branch=True, strict_slashes=False)
        # @require_auth()
        # def home_static_frontend_catchall(webinterface, request, session, catchall):
        #     """ For frontend that doesn't match anything. """
        #     print(f"catchall: {catchall}")
        #     print(f"page 404: {webinterface.working_dir}/frontend - {request.uri}")
        #     # return File(webinterface.working_dir + "/frontend/css/")
        #
        #     uri = request.uri.decode('utf-8')
        #     return File(webinterface.working_dir + "/frontend" + uri)
        #
        #     if re.match('^[a-zA-Z0-9?/.]*$', uri) is None:  # we have bad characters
        #         return "Please stop that."
        #
        #     max_age = 60
        #     if uri.endswith('.js') or uri.endswith('.css') or uri.startswith('/img/'):
        #         max_age = random_int(604800, .2)
        #
        #     mime = guess_extension(uri)[0]
        #     if mime is not None:
        #         request.setHeader("Content-Type", mime)
        #     request.responseHeaders.removeHeader("Expires")
        #     request.setHeader("Cache-Control", f"max-age={max_age}")
        #     # return "asdf"
        #     return File(webinterface.working_dir + "/frontend")

        @webapp.route("/css/", branch=True)
        def home_static_frontend_css(webinterface, request):
            """ For frontend css stylesheets. """
            request.responseHeaders.removeHeader("Expires")
            base_headers(request)
            request.setHeader("Cache-Control", f"max-age={random_int(604800, .2)}")
            return File(webinterface.working_dir + "/frontend/css")

        @webapp.route("/img/", branch=True)
        def home_static_frontend_img(webinterface, request):
            """ For frontend images. """
            request.responseHeaders.removeHeader("Expires")
            base_headers(request)
            request.setHeader("Cache-Control", f"max-age={random_int(604800, .2)}")
            return File(webinterface.working_dir + "/frontend/img")

        @webapp.route("/js/", branch=True)
        def home_static_frontend_js(webinterface, request):
            """ For frontend javascript files. """
            # uri = request.uri.decode('utf-8')
            # print(f"static_frontend_js {uri}")
            # if uri.endswith('basic_app.js'):
            base_headers(request)
            request.setHeader("Cache-Control", f"max-age={random_int(604800, .2)}")
            request.responseHeaders.removeHeader("Expires")
            return File(webinterface.working_dir + "/frontend/js")

        @webapp.route("/_nuxt/", branch=True)
        def home_static_frontend_nuxt(webinterface, request):
            """ For frontend javascript files. """
            # uri = request.uri.decode('utf-8')
            # print(f"static_frontend_js {uri}")
            # if uri.endswith('basic_app.js'):
            base_headers(request)
            request.setHeader("Cache-Control", f"max-age={random_int(604800, .2)}")
            request.responseHeaders.removeHeader("Expires")
            return File(webinterface.working_dir + "/frontend/_nuxt")

        @webapp.route("/favicon.ico")
        def home_static(webinterface, request):
            request.responseHeaders.removeHeader("Expires")
            base_headers(request)
            request.setHeader("Cache-Control", f"max-age={random_int(604800, .2)}")
            return File(webinterface.working_dir + "/frontend/img/icons/favicon.ico")

        def base_headers(request):
            request.setHeader("server", "Apache/2.4.38 (Unix)")
            request.setHeader("X-Powered-By", "YGW")
