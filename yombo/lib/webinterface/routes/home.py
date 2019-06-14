"""
This file handles the homepage, static files, and misc one-off urls.
"""
from mimetypes import guess_type
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.web.static import File

# Import Yombo libraries
from yombo.constants import CONTENT_TYPE_JSON
from yombo.core.log import get_logger
from yombo.lib.webinterface.auth import require_auth, run_first
from yombo.utils import random_int, read_file
from yombo.ext.expiringdict import ExpiringDict

logger = get_logger("library.webinterface.routes.home")


class NotFound(Exception):
    pass


def route_home(webapp):
    with webapp.subroute("") as webapp:

        @webapp.handle_errors(NotFound)
        @require_auth()
        def home_not_found(self, request, failure):
            """ This shouldn't ever be used....failsafe."""
            request.setResponseCode(404)
            return "Not found, I say!"

        @webapp.route("/robots.txt")
        def home_robots_txt(webinterface, request):
            return "User-agent: *\nDisallow: /\n"

        @webapp.route("/<path:catchall>", branch=True)
        @require_auth()
        @inlineCallbacks
        def home_static_frontend_catchall(webinterface, request, session, catchall):
            """ For frontend that doesn't match anything. """
            base_headers(request)
            uri = request.uri.decode()[1:]
            logger.info("Catchall for: {uri}", uri=uri)
            content = yield home_return_cached_file(webinterface, request, session, "index.html")
            return content

        @webapp.route("/")
        @run_first()
        @inlineCallbacks
        def home_index(webinterface, request, session):
            if webinterface.operating_mode == "config":
                return webinterface.redirect(request, "/misc/config")
            elif webinterface.operating_mode == "first_run":
                logger.info("Incoming request to /, but gateway needs setup. Redirecting to gateway_setup")
                return webinterface.redirect(request, "/misc/gateway_setup")
            if session is None or session.enabled is False or session.is_valid() is False or session.has_user is False:
                return webinterface.redirect(request, "/user/login")

            content = yield home_return_cached_file(webinterface, request, session, "index.html")
            return content

        @inlineCallbacks
        def home_return_cached_file(webinterface, request, session, filename, cache_ttl=None):
            if cache_ttl is None:
                cache_ttl = 7200
            if filename not in webinterface.file_cache or "data" in webinterface.file_cache[filename]:
                webinterface.file_cache[filename] = {}
                try:
                    webinterface.file_cache[filename]["data"] = yield read_file(f"{webinterface.working_dir}/frontend/{filename}")
                    webinterface.file_cache[filename]["headers"] = {"Cache-Control": f"max-age={cache_ttl}",
                                                           "Content-Type": guess_type(filename)[0]}
                except:
                    return "Unable to process request. Couldn't read source file."

            file = webinterface.file_cache[filename]
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
            return webinterface.nuxt_env_content(request)

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

        @webapp.route("/sw.js")
        @require_auth()
        @inlineCallbacks
        def home_service_worker(webinterface, request, session):
            """ Service worker file for authenticated users only. """
            content = yield home_return_cached_file(webinterface, request, session, "sw.js", 60)
            return content

        @webapp.route("/favicon.ico")
        def home_static(webinterface, request):
            request.responseHeaders.removeHeader("Expires")
            base_headers(request)
            request.setHeader("Cache-Control", f"max-age={random_int(604800, .2)}")
            return File(webinterface.working_dir + "/frontend/img/icons/favicon.ico")

        def base_headers(request):
            request.setHeader("server", "Apache/2.4.39 (Unix)")
            request.setHeader("X-Powered-By", "YGW")
