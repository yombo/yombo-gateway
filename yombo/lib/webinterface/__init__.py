# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * End user documentation: `Web Interface @ User Documentation <https://yombo.net/docs/gateway/web_interface>`_
  * For library documentation, see: `Web Interface @ Library Documentation <https://yombo.net/docs/libraries/web_interface>`_

Provides web interface to easily configure and manage the gateway devices and modules.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/webinterface.html>`_
"""
# Import python libraries
from collections import OrderedDict
from copy import deepcopy
from hashlib import sha256
import jinja2
import json
from klein import Klein
from operator import itemgetter
from random import randint
from time import time
from urllib.parse import parse_qs, urlparse, urlunparse

# Import twisted libraries
from twisted.internet import reactor, ssl
from twisted.internet.defer import inlineCallbacks, maybeDeferred, Deferred
from twisted.internet.task import LoopingCall

# Import 3rd party libraries
from yombo.ext.expiringdict import ExpiringDict

# Import Yombo libraries
from yombo.core.exceptions import YomboRestart, YomboCritical
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.ext.totp
import yombo.utils
import yombo.utils.converters as converters
import yombo.utils.datetime as dt_util
from yombo.lib.webinterface.auth import require_auth

from yombo.lib.webinterface.class_helpers.builddist import BuildDistribution
from yombo.lib.webinterface.class_helpers.errorhandler import ErrorHandler
from yombo.lib.webinterface.class_helpers.yombo_site import Yombo_Site
from yombo.lib.webinterface.class_helpers.webserver import WebServer

from yombo.lib.webinterface.routes.api_v1.automation import route_api_v1_automation
from yombo.lib.webinterface.routes.api_v1.camera import route_api_v1_camera
from yombo.lib.webinterface.routes.api_v1.command import route_api_v1_command
from yombo.lib.webinterface.routes.api_v1.device import route_api_v1_device
from yombo.lib.webinterface.routes.api_v1.device_command import route_api_v1_device_command
from yombo.lib.webinterface.routes.api_v1.events import route_api_v1_events
from yombo.lib.webinterface.routes.api_v1.gateway import route_api_v1_gateway
from yombo.lib.webinterface.routes.api_v1.module import route_api_v1_module
from yombo.lib.webinterface.routes.api_v1.mqtt import route_api_v1_mqtt
from yombo.lib.webinterface.routes.api_v1.notification import route_api_v1_notification
from yombo.lib.webinterface.routes.api_v1.scenes import route_api_v1_scene
from yombo.lib.webinterface.routes.api_v1.server import route_api_v1_server
from yombo.lib.webinterface.routes.api_v1.stream import broadcast as route_api_v1_stream_broadcast
from yombo.lib.webinterface.routes.api_v1.stream import route_api_v1_stream
from yombo.lib.webinterface.routes.api_v1.statistics import route_api_v1_statistics
from yombo.lib.webinterface.routes.api_v1.storage import route_api_v1_storage
from yombo.lib.webinterface.routes.api_v1.system import route_api_v1_system
from yombo.lib.webinterface.routes.api_v1.webinterface_logs import route_api_v1_webinterface_logs

from yombo.lib.webinterface.routes.home import route_home
from yombo.lib.webinterface.routes.misc import route_misc
from yombo.lib.webinterface.routes.user import route_user
from yombo.lib.webinterface.constants import NAV_SIDE_MENU, DEFAULT_NODE, NOTIFICATION_PRIORITY_MAP_CSS

logger = get_logger("library.webinterface")


class WebInterface(BuildDistribution, ErrorHandler, YomboLibrary, WebServer):
    """
    Web interface framework.
    """
    webapp = Klein()  # Like Flask, but for twisted

    visits = 0
    alerts = OrderedDict()
    starting = True
    already_starting_web_servers = False
    hook_listeners = {}  # special way to toss hook calls to routes.

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo web interface library"

    @inlineCallbacks
    def _init_(self, **kwargs):
        self.frontend_building = False
        self.web_interface_fully_started = False
        self.enabled = self._Configs.get("webinterface", "enabled", True)

        self.fqdn = self._Configs.get2("dns", "fqdn", None, False)

        self.gateway_id = self._Configs.gateway_id
        self.is_master = self._Configs.is_master
        self.master_gateway_id = self._Configs.master_gateway_id
        self.enabled = self._Configs.get("core", "enabled", True)
        if not self.enabled:
            return

        self.translators = {}
        self.idempotence = yield self._SQLDict.get("yombo.lib.webinterface", "idempotence")  # tracks if a request was already made

        self.working_dir = self._Atoms.get("working_dir")
        self.app_dir = self._Atoms.get("app_dir")
        self.wi_dir = "/lib/webinterface"

        self.build_dist()  # Make all the JS and CSS files
        self.misc_wi_data = {}

        self.wi_port_nonsecure = self._Configs.get2("webinterface", "nonsecure_port", 8080)
        self.wi_port_secure = self._Configs.get2("webinterface", "secure_port", 8443)

        self.webapp.templates = jinja2.Environment(loader=jinja2.FileSystemLoader(f"{self.app_dir}/yombo"),
                                                   extensions=["jinja2.ext.loopcontrols"])
        self.setup_basic_filters()

        self.web_interface_listener = None
        self.web_interface_ssl_listener = None

        self.api_stream_spectators = {}

        # Load API routes
        route_api_v1_automation(self.webapp)
        route_api_v1_camera(self.webapp)
        route_api_v1_command(self.webapp)
        route_api_v1_device(self.webapp)
        route_api_v1_device_command(self.webapp)
        route_api_v1_events(self.webapp)
        route_api_v1_gateway(self.webapp)
        route_api_v1_module(self.webapp)
        route_api_v1_mqtt(self.webapp)
        route_api_v1_notification(self.webapp)
        route_api_v1_server(self.webapp)
        route_api_v1_statistics(self.webapp)
        route_api_v1_stream(self.webapp, self)
        route_api_v1_system(self.webapp)
        route_api_v1_scene(self.webapp)
        route_api_v1_storage(self.webapp)
        route_api_v1_webinterface_logs(self.webapp)

        # Load web server routes
        route_home(self.webapp)
        route_misc(self.webapp)
        route_user(self.webapp)
        if self.operating_mode != "run":
            from yombo.lib.webinterface.routes.restore import route_restore
            from yombo.lib.webinterface.routes.setup_wizard import route_setup_wizard
            route_setup_wizard(self.webapp)
            route_restore(self.webapp)

        self.temp_data = ExpiringDict(max_age_seconds=1800)
        self.web_server_started = False
        self.web_server_ssl_started = False

        self.web_factory = None
        self.user_login_tokens = self._Cache.ttl(name="lib.users.cache", ttl=300)

    @property
    def operating_mode(self):
        return self._Loader.operating_mode

    def _load_(self, **kwargs):
        if not self.enabled:
            return

        self.module_config_links = {}

        # self.web_factory = Yombo_Site(self.webapp.resource(), None, logPath="/dev/null")
        self.web_factory = Yombo_Site(self.webapp.resource(), None, logPath=None)
        self.web_factory.setup_log_queue(self)
        self.web_factory.noisy = False  # turn off Starting/stopping message
        self.displayTracebacks = False

        self._display_how_to_access_at = 0  # When the display notice for how to access the web was shown.

        self.misc_wi_data["gateway_label"] = self._Configs.get2("core", "label", "Yombo Gateway", False)
        self.misc_wi_data["operating_mode"] = self.operating_mode
        self.misc_wi_data["notifications"] = self._Notifications
        self.misc_wi_data["notification_priority_map_css"] = NOTIFICATION_PRIORITY_MAP_CSS
        self.misc_wi_data["breadcrumb"] = []

        self.webapp.templates.globals["yombo"] = self
        self.webapp.templates.globals["_local_gateway"] = self._Gateways.local
        self.webapp.templates.globals["_amqp"] = self._AMQP
        self.webapp.templates.globals["_amqpyombo"] = self._AMQPYombo
        self.webapp.templates.globals["_authkeys"] = self._AuthKeys
        self.webapp.templates.globals["_atoms"] = self._Atoms
        self.webapp.templates.globals["_automation"] = self._Automation
        self.webapp.templates.globals["_cache"] = self._Cache
        self.webapp.templates.globals["_calllater"] = self._Calllater
        self.webapp.templates.globals["_commands"] = self._Commands
        self.webapp.templates.globals["_configs"] = self._Configs
        self.webapp.templates.globals["_crontab"] = self._CronTab
        self.webapp.templates.globals["_events"] = self._Events
        self.webapp.templates.globals["_devices"] = self._Devices
        self.webapp.templates.globals["_devicetypes"] = self._DeviceTypes
        self.webapp.templates.globals["_downloadmodules"] = self._DownloadModules
        self.webapp.templates.globals["_gatewaycoms"] = self._GatewayComs
        self.webapp.templates.globals["_gateways"] = self._Gateways
        self.webapp.templates.globals["_gpg"] = self._GPG
        self.webapp.templates.globals["_inputtypes"] = self._InputTypes
        self.webapp.templates.globals["_intents"] = self._Intents
        self.webapp.templates.globals["_libraries"] = self._Libraries
        self.webapp.templates.globals["_localize"] = self._Localize
        self.webapp.templates.globals["_locations"] = self._Locations
        self.webapp.templates.globals["_locations"] = self._Locations
        self.webapp.templates.globals["_modules"] = self._Modules
        self.webapp.templates.globals["_mqtt"] = self._MQTT
        self.webapp.templates.globals["_nodes"] = self._Nodes
        self.webapp.templates.globals["_notifiticaions"] = self._Notifications
        self.webapp.templates.globals["_users"] = self._Users
        self.webapp.templates.globals["_queue"] = self._Queue
        self.webapp.templates.globals["_scenes"] = self._Scenes
        self.webapp.templates.globals["_requests"] = self._Requests
        self.webapp.templates.globals["_sqldict"] = self._SQLDict
        self.webapp.templates.globals["_sslcerts"] = self._SSLCerts
        self.webapp.templates.globals["_states"] = self._States
        self.webapp.templates.globals["_statistics"] = self._Statistics
        self.webapp.templates.globals["_storage"] = self._Storage
        self.webapp.templates.globals["_tasks"] = self._Tasks
        self.webapp.templates.globals["_times"] = self._Times
        self.webapp.templates.globals["_variables"] = self._Variables
        self.webapp.templates.globals["_validate"] = self._Validate
        self.webapp.templates.globals["_webinterface"] = self
        self.webapp.templates.globals["py_randint"] = randint
        self.webapp.templates.globals["py_time_time"] = time
        self.webapp.templates.globals["py_urllib_urlparse"] = urlparse
        self.webapp.templates.globals["py_urllib_urlunparse"] = urlunparse
        self.webapp.templates.globals["yombo_utils"] = yombo.utils
        self.webapp.templates.globals["misc_wi_data"] = self.misc_wi_data
        self.webapp.templates.globals["misc_wi_data"] = self.misc_wi_data
        self.webapp.templates.globals["webinterface"] = self
        self.webapp.templates.globals["_location_id"] = None
        self.webapp.templates.globals["_area_id"] = None
        self.webapp.templates.globals["_location"] = None
        self.webapp.templates.globals["_area"] = None
        self.webapp.templates.globals["bg_image_id"] = lambda: int(time()/300) % 6

        self._refresh_jinja2_globals_()
        self.starting = False
        self.start_web_servers()
        self.clean_idempotence_ids_loop = LoopingCall(self.clean_idempotence_ids)
        self.clean_idempotence_ids_loop.start(1806, False)

    def _refresh_jinja2_globals_(self, **kwargs):
        """
        Update various globals for the Jinja2 template.

        :return:
        """
        if self.operating_mode != "run":
            return
        self.webapp.templates.globals["_location_id"] = self._Locations.location_id
        self.webapp.templates.globals["_area_id"] = self._Locations.area_id
        self.webapp.templates.globals["_location"] = self._Locations.location
        self.webapp.templates.globals["_area"] = self._Locations.area

    def _start_(self, **kwargs):
        self._Notifications.add({
            "title": "System still starting",
            "message": "Still starting up. Please wait.",
            "source": "Web Interface Library",
            "persist": True,
            "priority": "high",
            "always_show": True,
            "always_show_allow_clear": False,
            "id": "webinterface:starting",
        })
        self._get_nav_side_items()
        self.webapp.templates.globals["_"] = _  # i18n

    def _started_(self, **kwargs):
        # if self.operating_mode != "run":
        self._display_how_to_access_at = int(time())
        self.display_how_to_access()
        self._Notifications.delete("webinterface:starting")
        self.web_interface_fully_started = True

        self.send_hook_listeners_ping_loop = LoopingCall(self.send_hook_listeners_ping_loop)
        self.send_hook_listeners_ping_loop.start(55, True)

    def clean_idempotence_ids(self):
        """
        Removes older idempotence keys.

        :return:
        """
        delete_time = int(time()) - 1800
        for key in self.idempotence.keys():
            if self.idempotence[key] < delete_time:
                del self.idempotence[key]

    def send_hook_listeners_ping_loop(self):
        route_api_v1_stream_broadcast(self, "ping", int(time()))

    def register_hook(self, name, thecallback):
        if name not in self.hook_listeners:
            self.hook_listeners[name] = []
        self.hook_listeners[name].append(thecallback)

    @inlineCallbacks
    def _yombo_universal_hook_(self, hook_name=None, **kwargs):
        """
        Implements the universal hook.

        :param kwargs:
        :return:
        """
        if hook_name in self.hook_listeners:
            for a_callback in self.hook_listeners[hook_name]:
                d = Deferred()
                d.addCallback(lambda ignored: maybeDeferred(a_callback, self, hook_name=hook_name, **kwargs))
                d.addErrback(self.yombo_universal_hook_failure, hook_name, a_callback)
                d.callback(1)
                yield d

    def yombo_universal_hook_failure(self, failure, hook_name, acallback):
        logger.warn("---==(failure WI:universal hook for hook ({hook_name})==----",
                    hook_name=hook_name)
        logger.warn("--------------------------------------------------------")
        logger.warn("{acallback}", acallback=acallback)
        logger.warn("{failure}", failure=failure)
        logger.warn("--------------------------------------------------------")
        raise RuntimeError(f"failure during module invoke for hook: {failure}")

    def check_have_required_nodes(self):
        try:
            node = yield self._Nodes.get("main_page", "webinterface_page")
        except KeyError as e:
            pass
            # add base node...

    def _configuration_set_(self, **kwargs):
        """
        Need to monitor if the web interface port has changed. This will restart the webinterface
        server if needed.

        :param kwargs: section, option(key), value
        :return:
        """
        section = kwargs["section"]
        option = kwargs["option"]
        value = kwargs["value"]

        if self.starting is True:
            return

        if section == "webinterface":
            if option == "nonsecure_port":
                self.change_ports(port_nonsecure=value)
            elif option == "secure_port":
                self.change_ports(port_secure=value)

    @inlineCallbacks
    def _unload_(self, **kwargs):
        if hasattr(self, "web_factory"):
            if self.web_factory is not None:
                yield self.web_factory.save_log_queue()

    @property
    def internal_url(self):
        """
        Returns the starting portion of the URL to this host.
        https://i.exmaple.yombo.net

        :return:
        """
        fqdn = self.fqdn()
        if fqdn is None:
            internal_hostname = self._Configs.get("core", "localipaddress_v4")
            return f"http://{internal_hostname}:{self.wi_port_nonsecure()}"
        else:
            return f"https://i.{fqdn}:{self.wi_port_secure()}"

    @property
    def external_url(self):
        """
        Returns the starting portion of the URL to this host.
        https://e.exmaple.yombo.net

        :return:
        """
        fqdn = self.fqdn()
        if fqdn is None:
            external_hostname = self._Configs.get("core", "externalipaddress_v4")
            return f"https://{external_hostname}:{self.wi_port_secure()}"
        else:
            return f"https://e.{fqdn}:{self.wi_port_secure()}"

    def i18n(self, request):
        """
        Gets a translator based on the language the browser provides us.

        :param request: The browser request.
        :return:
        """
        locales = self._Localize.parse_accept_language(request.getHeader("accept-language"))
        locales_hash = yombo.utils.sha256_compact("".join(str(e) for e in locales))
        if locales_hash in self.translators:
            return self.translators[locales_hash]
        else:
            self.translators[locales_hash] = web_translator(self, locales)
        return self.translators[locales_hash]

    @inlineCallbacks
    def _get_nav_side_items(self, **kwargs):
        """
        Called before modules have their _prestart_ function called (after _load_).

        This implements the hook "webinterface_add_routes" and calls all libraries and modules. It allows libs and
        modules to add menus to the web interface and provide additional funcationality.

        **Usage**:

        .. code-block:: python

           def ModuleName_webinterface_add_routes(self, **kwargs):
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
        # first, lets get the top levels already defined so children don"t re-arrange ours.
        top_levels = {}
        add_on_menus = yield yombo.utils.global_invoke_all("_webinterface_add_routes_",
                                                           called_by=self,
                                                           )
        logger.debug("_webinterface_add_routes_ results: {add_on_menus}", add_on_menus=add_on_menus)
        nav_side_menu = deepcopy(NAV_SIDE_MENU)
        for component, options in add_on_menus.items():
            if "nav_side" in options:
                for new_menu in options["nav_side"]:
                    if new_menu["label1"] in nav_side_menu:
                        the_index = nav_side_menu[new_menu["label1"]].index("bar")
                        new_menu["priority1"] = nav_side_menu[the_index]["priority1"]
                    if "priority1" not in new_menu or isinstance(new_menu["priority1"], int) is False:
                        new_menu["priority1"] = 1000
                    if "priority2" not in new_menu or isinstance(new_menu["priority2"], int) is False:
                        new_menu["priority2"] = 100
                nav_side_menu = nav_side_menu + options["nav_side"]

        temp_list = sorted(NAV_SIDE_MENU, key=itemgetter("priority1", "label1", "priority2"))
        for item in temp_list:
            label1 = item["label1"]
            if label1 not in temp_list:
                top_levels[label1] = item["priority1"]

        for component, options in add_on_menus.items():
            logger.debug("component: {component}, options: {options}", component=component, options=options)
            if "menu_priorities" in options:  # allow modules to change the ordering of top level menus
                for label, priority in options["menu_priorities"].items():
                    top_levels[label] = priority
            if "routes" in options:
                for new_route in options["routes"]:
                    new_route(self.webapp)
            if "configs" in options:
                if "settings_link" in options["configs"]:
                    self.module_config_links[component._module_id] = options["configs"]["settings_link"]

        # build menu tree
        self.misc_wi_data["nav_side"] = OrderedDict()

        is_master = self.is_master()
        # temp_list = sorted(nav_side_menu, key=itemgetter("priority1", "priority2", "label1"))
        temp_list = sorted(nav_side_menu, key=itemgetter("priority1", "label1", "priority2", "label2"))
        for item in temp_list:
            if "cluster" not in item:
                item["cluster"] = "any"
            if item["cluster"] == "master" and is_master is not True:
                continue
            if item["cluster"] == "member" and is_master is True:
                continue
            item["label1_text"] = deepcopy(item["label1"])
            item["label2_text"] = deepcopy(item["label2"])
            label1 = "ui::navigation::" + yombo.utils.snake_case(item["label1"])
            item["label1"] = "ui::navigation::" + yombo.utils.snake_case(item["label1"])
            item["label2"] = "ui::navigation::" + yombo.utils.snake_case(item["label2"])
            if label1 not in self.misc_wi_data["nav_side"]:
                self.misc_wi_data["nav_side"][label1] = []
            self.misc_wi_data["nav_side"][label1].append(item)

        self.starting = False

    def add_alert(self, message, level="info", dismissible=True, type="session", deletable=True):
        """
        Add an alert to the stack.
        :param level: info, warning, error
        :param message:
        :return:
        """
        rand = yombo.utils.random_string(length=12)
        self.alerts[rand] = {
            "type": type,
            "level": level,
            "message": message,
            "dismissible": dismissible,
            "deletable": deletable,
        }
        return rand

    def get_alerts(self, type=None, session=None):
        """
        Retrieve a list of alerts for display.
        """
        if type is None:
            type = "session"

        show_alerts = OrderedDict()
        for keyid in list(self.alerts.keys()):
            if self.alerts[keyid]["type"] == type:
                show_alerts[keyid] = self.alerts[keyid]
                if type == "session":
                    del self.alerts[keyid]
        return show_alerts

    def get_template(self, request, template_path):
        request.webinterface.webapp.templates.globals["_"] = request.webinterface.i18n(request)  # set in auth.update_request.
        return self.webapp.templates.get_template(template_path)

    def redirect(self, request, redirect_path):
        request.redirect(redirect_path)

    def _get_parms(self, request):
        return parse_qs(urlparse(request.uri).query)

    def request_get_default(self, request, name, default, offset=None):
        if offset == None:
            offset = 0
        try:
            return request.args.get(name)[offset]
        except:
            return default

    def home_breadcrumb(self, request):
        self.add_breadcrumb(request, "/?", "Home")

    def add_breadcrumb(self, request, url=None, text=None, show=None, style=None, data=None):
        if hasattr(request, "breadcrumb") is False:
            request.breadcrumb = []
            self.misc_wi_data["breadcrumb"] = request.breadcrumb

        if show is None:
            show = True

        if style is None:
            style = "link"
        elif style == "select_groups":
            items = {}
            for option_label, option_data in data.items():
                items[option_label] = []
                for select_text, select_url in option_data.items():
                    selected = ""
                    option_style = "None"
                    if select_url.startswith("$"):
                        selected = "selected"
                        select_url = select_url[1:]
                    elif select_url.startswith("#"):
                        option_style = "divider"

                    items[option_label].append({
                        "option_style": option_style,
                        "text": select_text,
                        "url": select_url,
                        "selected": selected,
                    })
            data = items
        elif style == "select":
            items = []
            for select_text, select_url in data.items():
                selected = ""
                option_style = "None"
                if select_url.startswith("$"):
                    selected = "selected"
                    select_url = select_url[1:]
                elif select_url.startswith("#"):
                    option_style = "divider"

                items.append({
                    "option_style": option_style,
                    "text": select_text,
                    "url": select_url,
                    "selected": selected,
                })
            data = items

        hash = sha256(str(str(url) + str(text) + str(show) + str(style) + json.dumps(data)).encode()).hexdigest()
        breadcrumb = {
            "hash": hash,
            "url": url,
            "text": text,
            "show": show,
            "style": style,
            "data": data,
        }
        request.breadcrumb.append(breadcrumb)

    def setup_basic_filters(self):
        self.webapp.templates.filters["yes_no"] = yombo.utils.is_yes_no
        self.webapp.templates.filters["true_false"] = yombo.utils.is_true_false
        self.webapp.templates.filters["excerpt"] = yombo.utils.excerpt
        self.webapp.templates.filters["make_link"] = yombo.utils.make_link
        self.webapp.templates.filters["status_to_string"] = converters.status_to_string
        self.webapp.templates.filters["public_to_string"] = converters.public_to_string
        self.webapp.templates.filters["epoch_to_string"] = converters.epoch_to_string
        self.webapp.templates.filters["epoch_get_age"] = dt_util.get_age  # yesterday, 5 minutes ago, etc.
        self.webapp.templates.filters["epoch_get_age_exact"] = dt_util.get_age_exact  # yesterday, 5 minutes ago, etc.
        self.webapp.templates.filters["format_markdown"] = yombo.utils.format_markdown
        self.webapp.templates.filters["hide_none"] = yombo.utils.display_hide_none
        self.webapp.templates.filters["display_encrypted"] = self._GPG.display_encrypted
        self.webapp.templates.filters["display_temperature"] = self._Localize.display_temperature
        self.webapp.templates.filters["json_human"] = yombo.utils.json_human
        self.webapp.templates.filters["yombo"] = self

    def restart(self, request, message=None, redirect=None):
        if message is None:
            message = ""
        if redirect is None:
            redirect = "/?"

        page = self.get_template(request, self.wi_dir + "/pages/restart.html")
        reactor.callLater(0.3, self.do_restart)
        return page.render(message=message,
                           redirect=redirect,
                           uptime=str(self._Atoms["running_since"])
                           )

    def do_restart(self):
        try:
            raise YomboRestart("Web Interface setup wizard complete.")
        except:
            pass

    def shutdown(self, request):
        page = self.get_template(request, self.wi_dir + "/pages/shutdown.html")
        # reactor.callLater(0.3, self.do_shutdown)
        return page.render()

    def do_shutdown(self):
        raise YomboCritical("Web Interface setup wizard complete.")


class web_translator(object):
    def __init__(self, webinterface, locales):
        self.webinterface = webinterface
        self.translator = webinterface._Localize.get_translator(locales)

    def __call__(self, msgid, default_text=None, **kwargs):
        kwargs["translator"] = self.translator
        return self.webinterface._Localize.handle_translate(msgid, default_text, **kwargs)
