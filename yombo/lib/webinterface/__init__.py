# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
The core of the webserver. Responsible for:

* Handling all browser interactions;
* Running the setup wizard on install;
* Handles API calls;
* Builds the frontend Vue application.

.. note::

  * End user documentation: `Web Interface @ User Documentation <https://yombo.net/docs/gateway/web_interface>`_
  * For library documentation, see: `Web Interface @ Library Documentation <https://yombo.net/docs/libraries/web_interface>`_

The webinterface module is broken up into the following components:

* Mixins
* Routes
* Pages

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/webinterface/__init__.html>`_
"""
# Import python libraries
from hashlib import sha256
import jinja2
import json
from klein import Klein
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union
from urllib.parse import parse_qs, urlparse

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred, Deferred
from twisted.internet.task import LoopingCall

# Import 3rd party libraries
from yombo.ext.expiringdict import ExpiringDict

# Import Yombo libraries
from yombo.constants.webinterface import NOTIFICATION_PRIORITY_MAP_CSS
from yombo.core.exceptions import YomboRestart, YomboQuit
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.utils
import yombo.utils.converters as converters
import yombo.utils.datetime as dt_util

from yombo.lib.webinterface.auth import get_session, setup_webinterface_reference
from yombo.lib.webinterface.yombo_site import YomboSite
from yombo.lib.webinterface.routes.api_v1.web_stream import web_broadcast

from yombo.lib.webinterface.mixins.frontend_mixin import FrontendMixin
from yombo.lib.webinterface.mixins.load_routes_mixin import LoadRoutesMixin
from yombo.lib.webinterface.mixins.render_mixin import RenderMixin
from yombo.lib.webinterface.yombo_site import YomboSite
from yombo.lib.webinterface.mixins.webserver_mixin import WebServerMixin
from yombo.utils import random_string

logger = get_logger("library.webinterface")


class WebInterface(YomboLibrary, FrontendMixin, LoadRoutesMixin, RenderMixin, WebServerMixin):
    """
    Web interface framework.
    """
    starting: ClassVar[bool] = True
    already_starting_web_servers: ClassVar[bool] = False
    hook_listeners: ClassVar[dict] = {}  # special way to toss hook calls to routes.
    generic_router_list: ClassVar[dict] = {"libraries": {}, "modules": {}}

    @inlineCallbacks
    def _init_(self, **kwargs):
        setup_webinterface_reference(self)  # Sets a reference to this library in auth.py
        self.webapp = Klein()
        self.webapp.webinterface = self

        self.api_key = self._Configs.get("frontend.api_key", random_string(length=75))
        self.frontend_building: bool = False
        self.web_interface_fully_started: bool = False
        self.enabled = self._Configs.get("webinterface.enabled", True)

        self.fqdn = self._Configs.get("dns.fqdn", None, False, instance=True)

        self.enabled = self._Configs.get("core.enabled", True)
        if not self.enabled:
            return

        self.file_cache = ExpiringDict(max_len=100, max_age_seconds=120) # used to load a few static files into memory that are commonly used.
        self.translators = {}
        self.idempotence = self._Cache.ttl(name="lib.webinterface.idempotence", ttl=300)

        self.wi_dir = "/lib/webinterface"

        self.misc_wi_data = {}

        self.wi_port_nonsecure = self._Configs.get("webinterface.nonsecure_port", 8080, instance=True)
        self.wi_port_secure = self._Configs.get("webinterface.secure_port", 8443, instance=True)

        self.webapp.templates = jinja2.Environment(loader=jinja2.FileSystemLoader(f"{self._app_dir}/yombo"),
                                                   extensions=["jinja2.ext.loopcontrols"])
        self.setup_basic_filters()

        self.web_interface_listener = None
        self.web_interface_ssl_listener = None

        self.api_stream_spectators = {}  # Tracks all the spectators connected. An alternative to MQTT listening.

        if self._Configs.get("webinterface.enable_default_routes", default=True, create=False):
            yield self.webinterface_load_routes()  # Loads all the routes.

        self.npm_build_results = None

        self.temp_data = ExpiringDict(max_age_seconds=1800)
        self.web_server_started = False
        self.web_server_ssl_started = False

        self.setup_wizard_map_js = None
        self.web_factory = None
        self.user_login_tokens = self._Cache.ttl(name="lib.users.cache", ttl=300)

    @property
    def operating_mode(self):
        return self._Loader.operating_mode

    @inlineCallbacks
    def _load_(self, **kwargs):
        if not self.enabled:
            return

        yield self._Notifications.new(notice_id="webinterface:starting",
                                      title="System still starting",
                                      message="Still starting up. Please wait.",
                                      priority="high",
                                      always_show=True,
                                      always_show_allow_clear=False,
                                      _request_context=self._FullName,
                                      _authentication=self.AUTH_USER
                                      )

        if self._Configs.get("webinterface.enable_frontend", True, False):
            self.build_dist()  # Makes the Vue application frontend.

        self.module_config_links = {}

        # self.web_factory = YomboSite(self.webapp.resource(), None, logPath="/dev/null")
        self.web_factory = YomboSite(self, self.webapp.resource(), None, logPath=None)
        self.web_factory.noisy = False  # turn off Starting/stopping message
        self.displayTracebacks = False

        self._display_how_to_access_at = 0  # When the display notice for how to access the web was shown.

        self.misc_wi_data["gateway_label"] = self._Configs.get("core.label", "Yombo Gateway", False, instance=True)
        self.misc_wi_data["operating_mode"] = self._Loader.operating_mode
        self.misc_wi_data["notifications"] = self._Notifications
        self.misc_wi_data["notification_priority_map_css"] = NOTIFICATION_PRIORITY_MAP_CSS
        self.misc_wi_data["breadcrumb"] = []

        self.webapp.templates.globals["yombo"] = self
        self.webapp.templates.globals["_local_gateway"] = self._Gateways.local
        self.webapp.templates.globals["py_time"] = time
        self.webapp.templates.globals["misc_wi_data"] = self.misc_wi_data
        self.webapp.templates.globals["webinterface"] = self
        self.webapp.templates.globals["bg_image_id"] = lambda: int(time()/300) % 6  # Used to select a background.
        # self.webapp.templates.globals["get_alerts"] = self.get_alerts

        self._refresh_jinja2_globals_()
        self.starting = False
        yield self.start_web_servers()
        self.clean_idempotence_ids_loop = LoopingCall(self.clean_idempotence_ids)
        self.clean_idempotence_ids_loop.start(1806, False)

    def _refresh_jinja2_globals_(self, **kwargs):
        """
        Update various globals for the Jinja2 template.

        :return:
        """
        if self._Loader.operating_mode != "run":
            return
        self.webapp.templates.globals["_location_id"] = self._Locations.location_id
        self.webapp.templates.globals["_area_id"] = self._Locations.area_id
        self.webapp.templates.globals["_location"] = self._Locations.location
        self.webapp.templates.globals["_area"] = self._Locations.area

    @inlineCallbacks
    def _start_(self, **kwargs):
        self.webapp.templates.globals["_"] = _  # i18n
        if self._gateway_id == "local":
            results = yield self._Requests.request("get", "https://yg2.in/9id39")
            self.setup_wizard_map_js = results.content.strip()

    def _started_(self, **kwargs):
        """ Perform a couple of small tasks after everything has started. """
        self.web_interface_fully_started = True
        self.display_how_to_access()
        self._Notifications.delete("webinterface:starting")

        self.send_hook_listeners_ping_loop = LoopingCall(self.send_hook_listeners_ping_loop)
        self.send_hook_listeners_ping_loop.start(55, True)

    @inlineCallbacks
    def _unload_(self, **kwargs):
        if hasattr(self, "web_factory"):
            if self.web_factory is not None:
                yield self.web_factory.save_log_queue()

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
        web_broadcast(self, "ping", int(time()))

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

    def _configs_set_(self, arguments, **kwargs):
        """
        Need to monitor if the web interface port has changed. This will restart the webinterface
        server if needed.

        :param arguments: section, option(key), value
        :return:
        """
        section = arguments["section"]
        option = arguments["option"]
        value = arguments["value"]

        if self.starting is True:
            return

        if section == "webinterface":
            if option == "nonsecure_port":
                self.change_ports(port_nonsecure=value)
            elif option == "secure_port":
                self.change_ports(port_secure=value)

    @property
    def internal_url(self):
        """
        Returns the starting portion of the URL to this host.
        https://i.exmaple.yombo.net

        :return:
        """
        if self.fqdn.value is None:
            internal_hostname = self._Configs.get("networking.localipaddress.v4")
            return f"http://{internal_hostname}:{self.wi_port_nonsecure.value}"
        else:
            return f"https://i.{self.fqdn.value}:{self.wi_port_secure.value}"

    @property
    def external_url(self):
        """
        Returns the starting portion of the URL to this host.
        https://e.exmaple.yombo.net

        :return:
        """
        if self.fqdn.value is None:
            external_hostname = self._Configs.get("networking.externalipaddress.v4")
            return f"https://{external_hostname}:{self.wi_port_secure.value}"
        else:
            return f"https://e.{self.fqdn.value}:{self.wi_port_secure.value}"

    def add_alert(self, session, message, level="info", display_once=True, deletable=True, id=None):
        """
        Add an alert to the stack.
        :param level: info, warning, error
        :param message:
        :return:
        """
        id = session.add_alert(message, level, display_once, deletable, id)
        return id

    def get_alerts(self, session, autodelete=None):
        """
        Retrieve a list of alerts for display.
        """
        if session is None:
            return {}
        return session.get_alerts(autodelete)

    def redirect(self, request, redirect_path):
        return request.redirect(redirect_path)

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
        self.add_breadcrumb(request, "/", "Home")

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
        self.webapp.templates.filters["display_temperature"] = self._Localize.display_temperature
        self.webapp.templates.filters["yombo"] = self

    def restart(self, request, message=None, redirect=None):
        """
        Restart the gateway. Called by various routes that need to restart the gateway. This will return
        the restarting html with message and redirect to injected into it.

        :param request:
        :param message:
        :param redirect:
        :return:
        """
        if message is None:
            message = ""
        if redirect is None:
            redirect = "/"

        def do_restart():
            try:
                raise YomboRestart("Web Interface setup wizard complete.")
            except:
                pass

        reactor.callLater(0.3, do_restart)
        return self.render_template(request,
                                    self.wi_dir + "/pages/misc/restarting.html",
                                    message=message,
                                    redirect=redirect,
                                    )

    def shutdown(self, request, message=None, redirect=None):
        """
        Shutdown the gateway. Called by various routes that need to shutdownthe gateway. This will return
        the shutting down html with the optional message injected into it.

        :param request:
        :param message:
        :param redirect:
        :return:
        """
        def do_shutdown():
            raise YomboQuit("Requested gateway shutdown from webinterface.")

        reactor.callLater(0.3, do_shutdown)
        return self.render_template(request,
                                    self.wi_dir + "/pages/misc/shutting_down.html")


class web_translator(object):
    def __init__(self, webinterface, locales):
        self.webinterface = webinterface
        self.translator = webinterface._Localize.get_translator(locales)

    def __call__(self, msgid, default_text=None, **kwargs):
        kwargs["translator"] = self.translator
        return self.webinterface._Localize.handle_translate(msgid, default_text, **kwargs)
