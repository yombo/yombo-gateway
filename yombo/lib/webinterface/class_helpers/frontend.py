"""
Extends the web_interface library class to add support for frontend items.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/webinterface/class_helpers/builddist.html>`_
"""
# Import python libraries
import json
from os import environ, path, makedirs, listdir, walk as oswalk, unlink, stat as osstat, kill
from PIL import Image
import shutil
from time import time
from copy import deepcopy

# Import twisted libraries
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, DeferredList
from twisted.internet.utils import getProcessOutput

# Import Yombo libraries
from yombo.utils import read_file, download_file
from yombo.utils.networking import ip_addres_in_local_network
from yombo.core.log import get_logger
from yombo.utils.filewriter import FileWriter
from yombo.utils.hookinvoke import global_invoke_all

from yombo.lib.webinterface.constants import FRONTEND_DASHBOARD_NAV

logger = get_logger("library.webinterface.class_helpers.builddist")


class Frontend:
    """
    """
    # @inlineCallbacks
    def dashboard_sidebar_navigation(self, **kwargs):
        """
        Generates items for the frontend dashboard navigation. This starts with a pre-defined set of items
        and then allows other modules to add additional items.

        **Usage**:

        .. code-block:: python

           def _frontend_dashboard_sidebar_(self, **kwargs):
               return {
                   "nav_side": [
                       {
                       "label1": "Tools",
                       "label2": "MQTT",
                       "priority1": 3000,
                       "priority2": 10000,
                       "icon": "fa fa-wrench fa-fw",
                       "url": "/tools/mqtt",
                       "tooltip": "",
                       "opmode": "run",
                       "cluster": "any",
                       },
                   ],
                   "routes": [
                       self.web_interface_routes,
                   ],
                   "configs" {
                        "settings_link": "/modules/tester/index",
                   },
               }

        """
        # sort the nav items
        # build a dict with inner/outter
        # build a list with that.

        # add_on_menus = yield global_invoke_all("_frontend_dashboard_sidebar_",
        #                                        called_by=self,
        #                                        )
        # logger.debug("_webinterface_add_routes_ results: {add_on_menus}", add_on_menus=add_on_menus)
        nav_side_menu = sorted(FRONTEND_DASHBOARD_NAV, key=lambda k: k['priority'])

        intermediate = {}

        for item in nav_side_menu:
            if item["parent"] is None:
                intermediate[item["label"]] = {"out": item, "in": []}

        for item in nav_side_menu:
            if item["parent"] is not None:
                if item["parent"] not in intermediate:
                    logger.warn("Frontend dashbard nav item being discarded, no parent: {item}", item=item)
                    continue
                intermediate[item["parent"]]["in"].append(item)

        results = []
        for label, data in intermediate.items():
            results.append(data)

        return results

        #
        # temp_list = sorted(NAV_SIDE_MENU, key=itemgetter("priority1", "label1", "priority2"))
        # for item in temp_list:
        #     label1 = item["label1"]
        #     if label1 not in temp_list:
        #         top_levels[label1] = item["priority1"]
        #
        # for component, options in add_on_menus.items():
        #     logger.debug("component: {component}, options: {options}", component=component, options=options)
        #     if "menu_priorities" in options:  # allow modules to change the ordering of top level menus
        #         for label, priority in options["menu_priorities"].items():
        #             top_levels[label] = priority
        #     if "routes" in options:
        #         for new_route in options["routes"]:
        #             new_route(self.webapp)
        #     if "configs" in options:
        #         if "settings_link" in options["configs"]:
        #             self.module_config_links[component._module_id] = options["configs"]["settings_link"]
        #
        # # build menu tree
        # self.misc_wi_data["nav_side"] = {}
        #
        # is_master = self.is_master
        # # temp_list = sorted(nav_side_menu, key=itemgetter("priority1", "priority2", "label1"))
        # temp_list = sorted(nav_side_menu, key=itemgetter("priority1", "label1", "priority2", "label2"))
        # for item in temp_list:
        #     if "cluster" not in item:
        #         item["cluster"] = "any"
        #     if item["cluster"] == "master" and is_master is not True:
        #         continue
        #     if item["cluster"] == "member" and is_master is True:
        #         continue
        #     item["label1_text"] = deepcopy(item["label1"])
        #     item["label2_text"] = deepcopy(item["label2"])
        #     label1 = "ui::navigation::" + yombo.utils.snake_case(item["label1"])
        #     item["label1"] = "ui::navigation::" + yombo.utils.snake_case(item["label1"])
        #     item["label2"] = "ui::navigation::" + yombo.utils.snake_case(item["label2"])
        #     if label1 not in self.misc_wi_data["nav_side"]:
        #         self.misc_wi_data["nav_side"][label1] = []
        #     self.misc_wi_data["nav_side"][label1].append(item)
        #
