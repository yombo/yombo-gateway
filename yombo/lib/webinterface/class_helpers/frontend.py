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
    This webinterface helper class provides features to support the frontend application. Notably, it
    generates the dashboard sidebar.
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
                            "parent": "ui.navigation.module_configurations",
                            "label": "ui.label.amazon_alexa",
                            "path": {"name": "dashboard-module_configs-amazon_alexa", "params": {}},
                            "priority": 1000,
                        },
                   ],
                   "config": {
                        "label": "ui.label.amazon_alexa",
                   },
               }

        """
        dashbard_items = deepcopy(FRONTEND_DASHBOARD_NAV)
        config_links = []

        add_on_menus = yield global_invoke_all("_dashboard_sidebar_navigation_",
                                               called_by=self,
                                               )

        for component, options in add_on_menus.items():
            if "dashboard_link" in options:
                dashbard_items = dashbard_items + options["dashboard_link"]

            if "config" in options:
                config_links.append({
                    "parent": "ui.navigation.module_configurations",
                    "label": options['config']['label'],
                    "path": {"name": f"dashboard-module_configs-{component._machine_label.lower()}", "params": {}},
                    "priority": 1,
                })
        if len(config_links) > 0:
            config_links.append({
                "parent": None,
                "icon": "fas fa-puzzle-piece",
                "label": f"ui.navigation.module_configurations",
                "path": {"name": f"dashboard-module_settings", "params": {}},
                "priority": 1,
            })
            config_links = sorted(config_links, key=lambda k: k['label'])

        for index, config_link in enumerate(config_links):
            config_link["priority"] = index

        dashbard_items = sorted(dashbard_items + config_links, key=lambda k: k['priority'])

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

