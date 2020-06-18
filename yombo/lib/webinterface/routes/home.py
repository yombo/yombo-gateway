"""
This file handles the homepage, static files, and misc one-off urls.

Adds the following routes:
/robots.txt - Disallow all
<404> and catchall - Two functions to catch everything that is missed.
"""
from mimetypes import guess_type
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.web.static import File

# Import Yombo libraries
from yombo.constants import CONTENT_TYPE_JSON
from yombo.core.log import get_logger
from yombo.lib.webinterface.auth import get_session
from yombo.lib.webinterface.response_tools import common_headers
from yombo.utils import random_int

logger = get_logger("library.webinterface.routes.home")


class NotFound(Exception):
    pass


def route_home(webapp):
    with webapp.subroute("") as webapp:

        @webapp.handle_errors(NotFound)
        @get_session(auth_required=True)
        @inlineCallbacks
        def home_not_found(webinterface, request, session, *args, **kwargs):
            """ This shouldn't ever be used....failsafe."""
            if session.is_valid():
                content = yield home_return_cached_file(webinterface, request, session, "index.html")
                return content
            else:
                return webinterface.render_error(request,
                                                 response_code=404,
                                                 )

        @webapp.route("/robots.txt")
        def home_robots_txt(webinterface, request):
            return "User-agent: *\nDisallow: /\n"

        @webapp.route("/<path:catchall>", branch=True)
        @get_session(auth_required=True)
        @inlineCallbacks
        def home_static_frontend_catchall(webinterface, request, session, catchall):
            """ For frontend that doesn't match anything. """
            uri = request.uri.decode()[1:]
            if session.is_valid():
                content = yield home_return_cached_file(webinterface, request, session, "index.html")
                return content
            else:
                return webinterface.render_error(request,
                                                 response_code=404,
                                                 )

        @webapp.route("/")
        @get_session()
        @inlineCallbacks
        def home_index(webinterface, request, session):
            if webinterface._Loader.operating_mode == "config":
                return webinterface.redirect(request, "/misc/config")
            elif webinterface._Loader.operating_mode == "first_run":
                logger.info("Incoming request to /, but gateway needs setup. Redirecting to gateway_setup")
                return webinterface.redirect(request, "/setup_wizard/start")
            if session is None or session.is_valid() is False:
                return webinterface.redirect(request, "/user/login")

            content = yield home_return_cached_file(webinterface, request, session, "index.html")
            return content

        @inlineCallbacks
        def home_return_cached_file(webinterface, request, session, filename, cache_ttl=None):
            allowed_files = [
                "index.html", "sw.js",
            ]
            common_headers(request)
            if filename not in allowed_files:
                return webinterface.render_error(request,
                                                 title="Invalid file request.",
                                                 response_code=400,
                                                 )

            if cache_ttl is None:
                cache_ttl = 7200

            if filename in webinterface.file_cache:
                if "data" not in webinterface.file_cache or "data" not in webinterface.file_cache:
                    del webinterface.file_cache[filename]

            if filename not in webinterface.file_cache:
                webinterface.file_cache[filename] = {}
                try:
                    webinterface.file_cache[filename]["data"] = yield webinterface._Files.read(
                        f"{webinterface._working_dir}/frontend/{filename}")
                    webinterface.file_cache[filename]["headers"] = {
                        "Cache-Control": f"max-age={cache_ttl}",
                        "Content-Type": guess_type(filename)[0]
                    }
                except Exception as e:
                    logger.info("Error with returning home cached file: {e}", e=e)
                    del webinterface.file_cache[filename]
                    return webinterface.still_building_frontend(request)

            file = webinterface.file_cache[filename]
            if "headers" in file and len(file["headers"]) > 0:
                for header_name, header_content in file['headers'].items():
                    request.setHeader(header_name, header_content)
            return file["data"]

        @webapp.route("/nuxt.env")
        @get_session(auth_required=True)
        def home_nuxt_env(webinterface, request, session):
            request.responseHeaders.removeHeader("Expires")
            request.setHeader("Content-Type", CONTENT_TYPE_JSON)
            request.setHeader("Cache-Control", f"max-age=30")
            return webinterface.nuxt_env_content(request)

        @webapp.route("/css/", branch=True)
        def home_static_frontend_css(request):
            """ For frontend css stylesheets. """
            webinterface = webapp.webinterface
            request.responseHeaders.removeHeader("Expires")
            base_headers(request)
            request.setHeader("Cache-Control", f"max-age={random_int(21600, .2)}")
            return File(webinterface._working_dir + "/frontend/css")

        @webapp.route("/img/", branch=True)
        def home_static_frontend_img(request):
            """ For frontend images. """
            webinterface = webapp.webinterface
            request.responseHeaders.removeHeader("Expires")
            base_headers(request)
            request.setHeader("Cache-Control", f"max-age={random_int(604800, .2)}")
            return File(webinterface._working_dir + "/frontend/img")

        @webapp.route("/js/", branch=True)
        def home_static_frontend_js(request):
            """ For frontend javascript files. """
            webinterface = webapp.webinterface
            # uri = request.uri.decode('utf-8')
            # print(f"static_frontend_js {uri}")
            # if uri.endswith('basic_app.js'):
            base_headers(request)
            request.setHeader("Cache-Control", f"max-age={random_int(21600, .2)}")
            request.responseHeaders.removeHeader("Expires")
            return File(webinterface._working_dir + "/frontend/js")

        @webapp.route("/_nuxt/", branch=True)
        def home_static_frontend_nuxt(request):
            """ For frontend javascript files. """
            webinterface = webapp.webinterface
            # uri = request.uri.decode('utf-8')
            # print(f"static_frontend_js {uri}")
            # if uri.endswith('basic_app.js'):
            base_headers(request)
            request.setHeader("Cache-Control", f"max-age={random_int(21600, .2)}")
            request.responseHeaders.removeHeader("Expires")
            return File(webinterface._working_dir + "/frontend/_nuxt")

        @webapp.route("/sw.js")
        @get_session(auth_required=True)
        @inlineCallbacks
        def home_service_worker(webinterface, request, session):
            """ Service worker file for authenticated users only. """
            content = yield home_return_cached_file(webinterface, request, session, "sw.js", 60)
            return content

        @webapp.route("/favicon.ico")
        def home_static(request):
            webinterface = webapp.webinterface
            request.responseHeaders.removeHeader("Expires")
            base_headers(request)
            request.setHeader("Cache-Control", f"max-age={random_int(604800, .2)}")
            return File(webinterface._working_dir + "/frontend/img/icons/favicon.ico")

        def base_headers(request):
            request.setHeader("server", "Apache/2.4.41 (Unix)")
