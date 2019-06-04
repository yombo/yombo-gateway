"""
This file handles the homepage, static files, and misc one-off urls.
"""
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
        @inlineCallbacks
        def home_index(webinterface, request, session):
            if webinterface.operating_mode == "config":
                return webinterface.redirect(request, "/misc/config")
            elif webinterface.operating_mode == "first_run":
                logger.info("Incoming request to /, but gateway needs setup. Redirecting to gateway_setup")
                return webinterface.redirect(request, "/misc/gateway_setup")
            if session is None or session.enabled is False or session.is_valid() is False or session.has_user is False:
                return webinterface.redirect(request, "/user/login")

            if "index" not in webinterface.file_cache:
                webinterface.file_cache["index"] = {}
                try:
                    webinterface.file_cache["index"]["data"] = yield read_file(f"{webinterface.working_dir}/frontend/index.html")
                    webinterface.file_cache["index"]["headers"] = {"Cache-Control": f"max-age=7200",
                                                           "Content-Type": "text/html"}
                except:
                    return "Unable to process request."

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
            return webinterface.nuxt_env_content(request)

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

        @webapp.route("/sw.js")
        @require_auth()
        @inlineCallbacks
        def home_service_worker(webinterface, request, session):
            """ Service worker file for authenticated users only. """
            print("got sw.js request...")
            if "sw.js" not in webinterface.file_cache:
                print("sw.js - loading cache...")
                webinterface.file_cache["sw.js"] = {}
                try:
                    webinterface.file_cache["sw.js"]["data"] = yield read_file(f"{webinterface.working_dir}/frontend/sw.js")
                    webinterface.file_cache["sw.js"]["headers"] = {"Cache-Control": f"max-age=60",
                                                           "Content-Type": "application/javascript"}
                except:
                    return "Unable to process request."

            file = webinterface.file_cache["sw.js"]
            # print(webinterface.file_cache)
            # print(file)
            print("sw.js - setting headers")
            if "headers" in file and len(file["headers"]) > 0:
                for header_name, header_content in file['headers'].items():
                    request.setHeader(header_name, header_content)
            print("sw.js - send response.")
            return file["data"]

        @webapp.route("/favicon.ico")
        def home_static(webinterface, request):
            request.responseHeaders.removeHeader("Expires")
            base_headers(request)
            request.setHeader("Cache-Control", f"max-age={random_int(604800, .2)}")
            return File(webinterface.working_dir + "/frontend/img/icons/favicon.ico")

        def base_headers(request):
            request.setHeader("server", "Apache/2.4.39 (Unix)")
            request.setHeader("X-Powered-By", "YGW")
