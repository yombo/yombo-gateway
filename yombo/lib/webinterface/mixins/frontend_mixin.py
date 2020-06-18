"""
Manages the various Frontend Vue application. This builds the Frontend Vue application and provides a couple
of routes that the Frontend application uses when loading. This extends the :ref:`WebInterface <webinterface>`
library.

Handles items related to the frontend:
  * Build the frontend using yarn.
  * Create the frontend navigation sidebar.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/webinterface/mixins/frontend.html>`_
"""
# Import python libraries
from copy import deepcopy
import json
from os import environ, path, makedirs, listdir, walk as oswalk, unlink, stat as osstat, kill
from PIL import Image
import random
import shutil
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union


# Import twisted libraries
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks
from twisted.internet.utils import getProcessOutput

# Import Yombo libraries
from yombo.constants.frontend import DASHBOARD_NAV, GLOBAL_ITEMS_NAV
from yombo.core.log import get_logger
from yombo.utils.hookinvoke import global_invoke_all
from yombo.utils.networking import ip_address_in_local_network

logger = get_logger("library.webinterface.mixins.frontend")


class FrontendMixin:
    """
    Builds the frontend and create the navbar side menu items for the dashboard.
    """
    @inlineCallbacks
    def dashboard_sidebar_navigation(self, **kwargs):
        """
        Generates items for the frontend dashboard navigation. This starts with a pre-defined set of items
        and then allows other modules to add additional items.

        Modules can add links to the dashboard by returning a dictionary to the '_frontend_dashboard_sidebar_' hook.
        For module settings, the preferred method is to provide 'config' key with dictionary with 1 key:
        * label - a label for the link. This label will be run thru the translator for localization.

        The settings will automatically generate a link to the module's machine_label. The module should supply
        a matching page in the 'frontend' folder within the module.

        Additionally, the module can return a 'dashboard_link' key in the dictionary with a list of navigation
        items to create.

        **Usage**:

        The code below provides both a link and a module configuration settings. Typically, the module would return
        one or the other.

        .. code-block:: python

           def _frontend_dashboard_sidebar_(self, **kwargs):
               return {
                   "dashboard_link": [
                        {
                            "parent": "ui.navigation.module_configs",
                            "label": "ui.label.amazonalexa",
                            "path": {"name": "dashboard-module_configs-amazonalexa", "params": {}},
                            "priority": 1000,
                        },
                   ],
               }

        """
        dashbard_items = deepcopy(DASHBOARD_NAV)

        add_on_menus = yield global_invoke_all("_dashboard_sidebar_navigation_", called_by=self)

        for component, options in add_on_menus.items():
            if "dashboard_link" in options:
                dashbard_items = dashbard_items + options["dashboard_link"]

        frontend_config_files = yield self._Modules.search_modules_for_files("/frontend_configs/index.vue")
        if len(frontend_config_files) > 0:
            dashbard_items.append({
                "parent": None,
                "icon": "fas fa-puzzle-piece",
                "label": f"ui.navigation.module_configs",
                "path": {"name": f"dashboard-module_settings", "params": {}},
                "priority": 3000,
            })
            for fullpath, file in frontend_config_files.items():
                dashbard_items.append({
                    "parent": "ui.navigation.module_configs",
                    "label": f"module.{file['module_name']}.ui.label_config",
                    "label_alt": file["module_name"],
                    "path": {"name": f"dashboard-module_configs-{file['module_name']}", "params": {}},
                    "priority": 10000,
                })

        dashbard_items = sorted(dashbard_items, key=lambda k: (k["priority"], k["label"]))

        intermediate = {}

        for item in dashbard_items:
            if item["parent"] is None:
                intermediate[item["label"]] = {"out": item, "in": []}

        for item in dashbard_items:
            if item["parent"] is not None:
                if item["parent"] not in intermediate:
                    logger.warn("Frontend dashbard nav item being discarded, no parent: {item}", item=item)
                    continue
                intermediate[item["parent"]]["in"].append(item)

        results = []
        for label, data in intermediate.items():
            results.append(data)

        return results

    def global_items_sidebar_navigation(self, **kwargs):
        """
        Generates items for the frontend global items navigation.
        """
        global_items = sorted(GLOBAL_ITEMS_NAV, key=lambda k: (k["priority"], k["label"]))

        intermediate = {}

        for item in global_items:
            if item["parent"] is None:
                intermediate[item["label"]] = {"out": item, "in": []}

        for item in global_items:
            if item["parent"] is not None:
                if item["parent"] not in intermediate:
                    logger.warn("Frontend global item nav item being discarded, no parent: {item}", item=item)
                    continue
                intermediate[item["parent"]]["in"].append(item)

        results = []
        for label, data in intermediate.items():
            results.append(data)

        return results

    @inlineCallbacks
    def build_dist(self, verbose: Optional[bool] = None) -> None:
        """
        This builds the ~/.yombo/frontend folder.

        1) Copies the basic webinterface items to ~/.yombo/frontend for us when the user
           isn't logged in, or when the gateawy needs to be setup

        2) Generates the frontend single page application, and copies to ~/.yombo/frontend
           This step uses NPM to build the application and take a few minutes on low end
           devices such as Raspberry PI.

        3) Checks if there's any nice background images, if not, it downloads some free ones
           and renders various sizes to be displayed as needed.

        :param verbose: If True, displays more debug lines.
        :return:
        """
        content = self.nuxt_env_content()
        yield self._Files.save(filename=f"{self._app_dir}/yombo/frontend/static/nuxt.env",
                               content=content,
                               mode="w")  # open in append mode.

        if verbose is True:
            logger.info("Copying web static content.")
        yield self.copy_static_web_items()
        if not path.exists(self._working_dir + "/frontend/img/bg/5.jpg"):
            if verbose is True:
                logger.info("Downloading pretty background images.")
            self.download_background_images()
        if not path.exists(f"{self._working_dir}/frontend/_nuxt"):
            if verbose is True:
                logger.info("Copying basic web items for setup wizard.")
            yield self.copy_frontend()  # We copy the previously built frontend in case it's new install..
        yield self.build_frontend()

    @inlineCallbacks
    def frontend_npm_run(self, arguments: Optional[list] = None) -> None:
        """
        Does the actual execution of the npm run.

        :param arguments: A list of arguments to pass to NPM.
        :return:
        """
        if arguments is None:
            arguments = ["npm", "run", "prod", "--", self._working_dir]

        results = yield getProcessOutput(
            "nice",
            arguments,
            path=f"{self._app_dir}/yombo/frontend",
            env=environ.copy(),
            errortoo=True,
        )
        self.npm_build_results = results

    @inlineCallbacks
    def build_frontend(self) -> None:
        """
        This execute the NPM build process for the frontend.

        :return:
        """
        if self.frontend_building is True:
            return

        if self.frontend_building is True:
            logger.warn("Cannot build frontend : already building...")
            return
        start_time = time()

        npm_running = yield self.check_npm_running()
        if npm_running:
            logger.info("Frontend builder appears to already be running. Won't build now.")
            return

        logger.info("Web Frontend: Starting build. This may take a while to complete. Will notify when done.")
        self.frontend_building = True
        yield self.frontend_npm_run()  # THe build script copies to the final destination.
        logger.info("Web Frontend: Finished building in {seconds} seconds. Ready to use.",
                    seconds=round(time() - start_time))
        self.display_how_to_access()
        self.frontend_building = False

    @inlineCallbacks
    def check_npm_running(self) -> bool:
        """
        Checks if the builder process is running. First, it checks if the PID file is found. It then
        inspects that file and checks to make sure the actual process is running. If the process is running,
        return True. If not, remove file the PID file and return False.
        """
        # Check if builder is already running:
        if path.isfile(f"{self._app_dir}/yombo/frontend/util/builder.pid") is False:
            return False

        pid = yield self._Files.read(f"{self._app_dir}/yombo/frontend/util/builder.pid")
        try:
            kill(int(pid), 0)
            return True
        except OSError:
            unlink(f"{self._app_dir}/yombo/frontend/util/builder.pid")
            return False

    @inlineCallbacks
    def copy_frontend(self) -> None:
        """
        Copy the frontend contents to the static folder.
        :return:
        """
        yield threads.deferToThread(self.empty_directory, f"{self._working_dir}/frontend/_nuxt")
        if path.exists(f"{self._app_dir }/yombo/frontend/dist/_nuxt/"):
            yield self.copytree("yombo/frontend/dist/_nuxt/", "frontend/_nuxt/")
        if path.exists(f"{self._app_dir }/yombo/frontend/dist/index.html"):
            yield threads.deferToThread(shutil.copy2, self._app_dir + "/yombo/frontend/dist/index.html", self._working_dir + "/frontend/")
        if path.exists(f"{self._app_dir }/yombo/frontend/dist/sw.js"):
            yield threads.deferToThread(shutil.copy2, self._app_dir + "/yombo/frontend/dist/sw.js", self._working_dir + "/frontend/")

    @inlineCallbacks
    def download_background_images(self) -> None:
        """
        Downloads background images for various web pages. This downloads free images,
        and prepares various sizes.
        """

        background_images = [  # these images are free.  See unplash.com
            "https://images.unsplash.com/photo-1557648490-3d27c35dca2b",  # @strathacona
            "https://images.unsplash.com/photo-1578134260566-d4083893996a",  # @atulvi
            "https://images.unsplash.com/photo-1577353716826-9151912dcdd1",  # @blaichch
            "https://images.unsplash.com/photo-1572295727871-7638149ea3d7",  # Willian Justen de Vasconcellos
            "https://images.unsplash.com/photo-1542644250-543d4ac76b70",  # Erica Tessmann
            "https://images.unsplash.com/photo-1563210080-dfe35c83e2eb",  # Peter Lloyd
            "https://images.unsplash.com/photo-1414490929659-9a12b7e31907",  # Joschko Hammermann
            "https://images.unsplash.com/photo-1571217668979-f46db8864f75",  # Cristina Gottardi
            "https://images.unsplash.com/photo-1571366343168-631c5bcca7a4",  # Rizknas
            "https://images.unsplash.com/photo-1499881473615-cce30babfcad",  # Michal Pechardo
            "https://images.unsplash.com/reserve/unsplash_524010c76b52a_1.JPG",
            "https://images.unsplash.com/reserve/z7R1rjT6RhmZdqWbM5hg_R0001139.jpg",
            "https://images.unsplash.com/reserve/J3URHssSQyqifuJVcgKu_Wald.jpg",
            "https://images.unsplash.com/uploads/14114036359651bd991f1/b3ed8fdf",
            "https://images.unsplash.com/reserve/vof4H8A1S02iWcK6mSAd_sarahmachtsachen.com_TheBeach.jpg",
            ]  # If added/updated, update WI/route/user.py - page_usr_login_user_get

        if not path.exists(f"{self._working_dir}/frontend/img/bg"):
            makedirs(f"{self._working_dir}/frontend/img/bg")

        random_images = random.sample(background_images, 6)
        for idx, image in enumerate(random_images):
            logger.debug(f"WebInterface background image: {image}")
            try:
                yield self._Requests.download_file(image, f"{self._working_dir}/frontend/img/bg/{idx}.jpg")
            except:
                continue
            logger.debug(f"WebInterface background image, done: {image}")
            full = Image.open(f"{self._working_dir}/frontend/img/bg/{idx}.jpg")
            sizes = {
                2048: 67,
                1364: 67,
                600: 65,
            }
            for size, quality in sizes.items():
                out = yield threads.deferToThread(full.resize, (size, size), Image.BICUBIC)
                yield threads.deferToThread(out.save,
                                            f"{self._working_dir}/frontend/img/bg/{idx}_{size}.jpg",
                                            format="JPEG",
                                            subsampling=0,
                                            quality=quality)

    def nuxt_env_content(self, request=None):
        internal_http_port = self._Gateways.local.internal_http_port
        internal_http_secure_port = self._Gateways.local.internal_http_secure_port
        external_http_port = self._Gateways.local.external_http_port
        external_http_secure_port = self._Gateways.local.external_http_secure_port
        internal_http_port = internal_http_port if internal_http_port is not None else \
            self._Configs.get("self.nonsecure_port", None, False)
        internal_http_secure_port = internal_http_secure_port if internal_http_secure_port is not None else \
            self._Configs.get("self.secure_port", None, False)
        external_http_port = external_http_port if external_http_port is not None else \
            self._Configs.get("self.nonsecure_port", None, False)
        external_http_secure_port = external_http_secure_port if external_http_secure_port is not None else \
            self._Configs.get("self.secure_port", None, False)

        client_location = "local"
        if request is not None and ip_address_in_local_network(request.getClientIP()):
            client_location = "remote"

        return json.dumps({
            "gateway_id": self._gateway_id,
            "working_dir": self._working_dir,
            "internal_http_port": internal_http_port,
            "internal_http_secure_port": internal_http_secure_port,
            "external_http_port": external_http_port,
            "external_http_secure_port": external_http_secure_port,
            "api_key": self.api_key,
            "mqtt_port": self._Mosquitto.listen_port,
            "mqtt_port_ssl": self._Mosquitto.listen_port_ss_ssl,
            "mqtt_port_websockets": self._Mosquitto.listen_port_websockets,
            "mqtt_port_websockets_ssl": self._Mosquitto.listen_port_websockets_ss_ssl,
            "client_location": client_location,
            "static_data": False,
            "generated_at": int(time()),

        }, indent='\t', separators=(',', ': '))

    @inlineCallbacks
    def copy_static_web_items(self):
        """
        Copies base webpages, not relating to the frontend application.

        :return:
        """
        def do_cat(inputs, output):
            output = f"{self._working_dir}/frontend/{output}"
            makedirs(path.dirname(output), exist_ok=True)
            with open(output, "w") as outfile:
                for fname in inputs:
                    fname = "yombo/lib/webinterface/static/" + fname
                    with open(fname) as infile:
                        outfile.write(infile.read())

        CAT_SCRIPTS = [
            "source/bootstrap4/css/bootstrap.min.css",
            "source/bootstrap-select/css/bootstrap-select.min.css",
            "source/bootstrap4-toggle/bootstrap4-toggle.min.css",
            "source/yombo/yombo.css",
            "source/yombo/mappicker.css",
        ]
        CAT_SCRIPTS_OUT = "css/basic_app.min.css"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/yombo/mappicker.js",
            ]
        CAT_SCRIPTS_OUT = "js/mappicker.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/jquery/jquery.validate.min.js",
        ]
        CAT_SCRIPTS_OUT = "js/jquery.validate.min.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/jquery/jquery-3.3.1.min.js",
            "source/jquery/jquery.validate.min.js",
            "source/js-cookie/js.cookie.min.js",
            "source/bootstrap4/js/bootstrap.bundle.min.js",
            "source/bootstrap-select/js/bootstrap-select.min.js",
            "source/bootstrap4-toggle/bootstrap4-toggle.min.js",
            "source/yombo/jquery.are-you-sure.js",
            "source/yombo/yombo.js",
        ]
        CAT_SCRIPTS_OUT = "js/basic_app.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        filename = f"{self._working_dir}/frontend/nuxt.env"
        content = self.nuxt_env_content()
        yield self._Files.save(filename=filename, content=content, mode="w")  # open in append mode.

        yield self.copytree("yombo/lib/webinterface/static/source/img/", "frontend/img/")

    @inlineCallbacks
    def copytree(self, src, dst, symlinks=False, ignore=None):
        if src.startswith("/") is False:
            src = self._app_dir + "/" + src
        if dst.startswith("/") is False:
            dst = self._working_dir + "/" + dst

        if not path.exists(dst):
            makedirs(dst)
        for item in listdir(src):
            s = path.join(src, item)
            d = path.join(dst, item)
            if path.isdir(s):
                self.copytree(s, d, symlinks, ignore)
            else:
                if not path.exists(d) or osstat(s).st_mtime - osstat(d).st_mtime > 1:
                    yield threads.deferToThread(shutil.copy2, s, d)

    def empty_directory(self, delpath):
        for root, dirs, files in oswalk(delpath):
            for f in files:
                unlink(path.join(root, f))
            for d in dirs:
                shutil.rmtree(path.join(root, d))
