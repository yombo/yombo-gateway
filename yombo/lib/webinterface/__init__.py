# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * End user documentation: `Web Interface @ User Documentation <https://yombo.net/docs/gateway/web_interface>`_
  * For library documentation, see: `Web Interface @ Library Documentation <https://yombo.net/docs/libraries/web_interface>`_

Provides web interface to easily configure and manage the gateway devices and modules.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2018 by Yombo.
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
from OpenSSL import crypto
from operator import itemgetter
from os import path, listdir, mkdir
import shutil
from time import time
from urllib.parse import parse_qs, urlparse

# Import twisted libraries
from twisted.web.server import Site
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
from yombo.lib.webinterface.auth import require_auth_pin, require_auth, run_first

from yombo.lib.webinterface.routes.api_v1.automation import route_api_v1_automation
from yombo.lib.webinterface.routes.api_v1.command import route_api_v1_command
from yombo.lib.webinterface.routes.api_v1.device import route_api_v1_device
from yombo.lib.webinterface.routes.api_v1.device_command import route_api_v1_device_command
from yombo.lib.webinterface.routes.api_v1.events import route_api_v1_events
from yombo.lib.webinterface.routes.api_v1.gateway import route_api_v1_gateway
from yombo.lib.webinterface.routes.api_v1.module import route_api_v1_module
from yombo.lib.webinterface.routes.api_v1.notification import route_api_v1_notification
from yombo.lib.webinterface.routes.api_v1.scenes import route_api_v1_scene
from yombo.lib.webinterface.routes.api_v1.server import route_api_v1_server
from yombo.lib.webinterface.routes.api_v1.stream import broadcast as route_api_v1_stream_broadcast
from yombo.lib.webinterface.routes.api_v1.stream import route_api_v1_stream
from yombo.lib.webinterface.routes.api_v1.statistics import route_api_v1_statistics
from yombo.lib.webinterface.routes.api_v1.system import route_api_v1_system
from yombo.lib.webinterface.routes.api_v1.webinterface_logs import route_api_v1_webinterface_logs

from yombo.lib.webinterface.routes.devtools.config import route_devtools_config
from yombo.lib.webinterface.routes.devtools.config_commands import route_devtools_config_commands
from yombo.lib.webinterface.routes.devtools.config_device_types import route_devtools_config_device_types
from yombo.lib.webinterface.routes.devtools.config_device_type_commands import route_devtools_config_device_type_commmands
from yombo.lib.webinterface.routes.devtools.config_device_command_inputs import route_devtools_config_device_command_inputs
from yombo.lib.webinterface.routes.devtools.config_input_types import route_devtools_config_input_types
from yombo.lib.webinterface.routes.devtools.config_modules import route_devtools_config_modules
from yombo.lib.webinterface.routes.devtools.config_variables import route_devtools_config_variables

from yombo.lib.webinterface.routes.authkeys import route_authkeys
from yombo.lib.webinterface.routes.atoms import route_atoms
from yombo.lib.webinterface.routes.automation import route_automation
from yombo.lib.webinterface.routes.automation.device import route_automation_device
from yombo.lib.webinterface.routes.automation.pause import route_automation_pause
from yombo.lib.webinterface.routes.automation.scene import route_automation_scene
from yombo.lib.webinterface.routes.automation.state import route_automation_state
from yombo.lib.webinterface.routes.automation.template import route_automation_template
from yombo.lib.webinterface.routes.configs import route_configs
from yombo.lib.webinterface.routes.crontab import route_crontabs
from yombo.lib.webinterface.routes.debug import route_debug
from yombo.lib.webinterface.routes.devices import route_devices
from yombo.lib.webinterface.routes.discovery import route_discovery
from yombo.lib.webinterface.routes.events import route_events
from yombo.lib.webinterface.routes.locations import route_locations
from yombo.lib.webinterface.routes.gateways import route_gateways
from yombo.lib.webinterface.routes.home import route_home
from yombo.lib.webinterface.routes.intents import route_intents
from yombo.lib.webinterface.routes.misc import route_misc
from yombo.lib.webinterface.routes.modules import route_modules
from yombo.lib.webinterface.routes.notices import route_notices
from yombo.lib.webinterface.routes.panel import route_panel
from yombo.lib.webinterface.routes.roles import route_roles
from yombo.lib.webinterface.routes.scenes import route_scenes
from yombo.lib.webinterface.routes.scenes.device import route_scenes_device
from yombo.lib.webinterface.routes.scenes.pause import route_scenes_pause
from yombo.lib.webinterface.routes.scenes.scene import route_scenes_scene
from yombo.lib.webinterface.routes.scenes.state import route_scenes_state
from yombo.lib.webinterface.routes.scenes.template import route_scenes_template
from yombo.lib.webinterface.routes.statistics import route_statistics
from yombo.lib.webinterface.routes.states import route_states
from yombo.lib.webinterface.routes.system import route_system
from yombo.lib.webinterface.routes.users import route_users
from yombo.lib.webinterface.routes.webinterface_logs import route_webinterface_logs
from yombo.lib.webinterface.constants import NAV_SIDE_MENU, DEFAULT_NODE, NOTIFICATION_PRIORITY_MAP_CSS

logger = get_logger("library.webinterface")


class NotFound(Exception):
    pass


class Yombo_Site(Site):

    def setup_log_queue(self, webinterface):
        self.save_log_queue_loop = LoopingCall(self.save_log_queue)
        self.save_log_queue_loop.start(31.7, False)

        self.log_queue = []

        self.webinterface = webinterface
        self.db_save_log = self.webinterface._LocalDB.webinterface_save_logs

    def _escape(self, s):
        """
        Return a string like python repr, but always escaped as if surrounding
        quotes were double quotes.
        @param s: The string to escape.
        @type s: L{bytes} or L{unicode}
        @return: An escaped string.
        @rtype: L{unicode}
        """
        if not isinstance(s, bytes):
            s = s.encode("ascii")

        r = repr(s)
        if not isinstance(r, str):
            r = r.decode("ascii")
        if r.startswith(u"b"):
            r = r[1:]
        if r.startswith(u"'"):
            return r[1:-1].replace(u'"', u'\\"').replace(u"\\'", u"'")
        return r[1:-1]

    def log(self, request):
        """
        This is magically called by the Twisted framework unicorn: twisted.web.http:Request.finish()

        :param request:
        :return:
        """
        ignored_extensions = (".js", ".css", ".jpg", ".jpeg", ".gif", ".ico", ".woff2", ".map")
        url_path = request.path.decode().strip()

        if any(url_path.endswith(ext) for ext in ignored_extensions):
            return

        if request.getClientIP() == "127.0.0.1" and url_path.startswith("/api/v1/mqtt/auth/"):
            return

        if hasattr(request, "auth"):
            if request.auth is None:
                user_id = None
            else:
                user_id = request.auth.safe_display
        else:
            print(f"request has no auth! : {request}")
            user_id = None

        self.log_queue.append(OrderedDict({
            "request_at": time(),
            "request_protocol": request.clientproto.decode().strip(),
            "referrer": self._escape(request.getHeader(b"referer") or b"-").strip(),
            "agent": self._escape(request.getHeader(b"user-agent") or b"-").strip(),
            "ip": request.getClientIP(),
            "hostname": request.getRequestHostname().decode().strip(),
            "method": request.method.decode().strip(),
            "path": url_path,
            "secure": request.isSecure(),
            "auth_id": user_id,
            "response_code": request.code,
            "response_size": request.sentLength,
            "uploadable": 1,
            "uploaded": 0,
            })
        )

    def save_log_queue(self):
        if len(self.log_queue) > 0:
            queue = self.log_queue
            self.log_queue = []
            self.db_save_log(queue)


class WebInterface(YomboLibrary):
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
        self.web_interface_fully_started = False
        self.enabled = self._Configs.get("webinterface", "enabled", True)

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

        self._build_dist()  # Make all the JS and CSS files
        self.secret_pin_totp = self._Configs.get2("webinterface", "auth_pin_totp",
                                     yombo.utils.random_string(length=16, letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"))
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
        route_api_v1_command(self.webapp)
        route_api_v1_device(self.webapp)
        route_api_v1_device_command(self.webapp)
        route_api_v1_gateway(self.webapp)
        route_api_v1_module(self.webapp)
        route_api_v1_notification(self.webapp)
        route_api_v1_server(self.webapp)
        route_api_v1_statistics(self.webapp)
        route_api_v1_stream(self.webapp, self)
        route_api_v1_system(self.webapp)
        route_api_v1_scene(self.webapp)
        route_api_v1_events(self.webapp)
        route_api_v1_webinterface_logs(self.webapp)

        # Load devtool routes
        route_devtools_config(self.webapp)
        route_devtools_config_commands(self.webapp)
        route_devtools_config_device_types(self.webapp)
        route_devtools_config_device_type_commmands(self.webapp)
        route_devtools_config_device_command_inputs(self.webapp)
        route_devtools_config_input_types(self.webapp)
        route_devtools_config_modules(self.webapp)
        route_devtools_config_variables(self.webapp)

        # Load web server routes
        route_authkeys(self.webapp)
        route_atoms(self.webapp)
        route_automation(self.webapp)
        route_automation_device(self.webapp)
        route_automation_pause(self.webapp)
        route_automation_scene(self.webapp)
        route_automation_state(self.webapp)
        route_automation_template(self.webapp)
        route_configs(self.webapp)
        route_crontabs(self.webapp)
        route_debug(self.webapp)
        route_devices(self.webapp)
        route_discovery(self.webapp)
        route_events(self.webapp)
        route_locations(self.webapp)
        route_devtools_config(self.webapp)
        route_gateways(self.webapp)
        route_home(self.webapp)
        route_intents(self.webapp)
        route_misc(self.webapp)
        route_modules(self.webapp)
        route_notices(self.webapp)
        route_roles(self.webapp)
        route_scenes(self.webapp)
        route_scenes_device(self.webapp)
        route_scenes_pause(self.webapp)
        route_scenes_scene(self.webapp)
        route_scenes_state(self.webapp)
        route_scenes_template(self.webapp)
        if self.operating_mode != "run":
            from yombo.lib.webinterface.routes.setup_wizard import route_setup_wizard
            route_setup_wizard(self.webapp)
        route_statistics(self.webapp)
        route_states(self.webapp)
        route_system(self.webapp)
        route_users(self.webapp)
        route_webinterface_logs(self.webapp)
        if self.is_master():
            route_panel(self.webapp)

        self.temp_data = ExpiringDict(max_age_seconds=1800)
        self.web_server_started = False
        self.web_server_ssl_started = False

        self.web_factory = None

    @property
    def operating_mode(self):
        return self._Loader.operating_mode

    def _load_(self, **kwargs):
        if not self.enabled:
            return

        self.module_config_links = {}

        self.auth_pin = self._Configs.get2("webinterface", "auth_pin",
              yombo.utils.random_string(length=4, letters=yombo.utils.human_alphabet()).lower())
        self.auth_pin_totp = self._Configs.get2("webinterface", "auth_pin_totp", yombo.utils.random_string(length=16))
        self.auth_pin_type = self._Configs.get2("webinterface", "auth_pin_type", "pin")
        self.auth_pin_required = self._Configs.get2("webinterface", "auth_pin_required", True)

        # self.web_factory = Yombo_Site(self.webapp.resource(), None, logPath="/dev/null")
        self.web_factory = Yombo_Site(self.webapp.resource(), None, logPath=None)
        self.web_factory.setup_log_queue(self)
        self.web_factory.noisy = False  # turn off Starting/stopping message
        self.displayTracebacks = False

        self._display_pin_console_at = 0

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
        self.webapp.templates.globals["_commands"] = self._Commands
        self.webapp.templates.globals["_configs"] = self._Configs
        self.webapp.templates.globals["_crontab"] = self._CronTab
        self.webapp.templates.globals["_events"] = self._Events
        self.webapp.templates.globals["_devices"] = self._Devices
        self.webapp.templates.globals["_devicetypes"] = self._DeviceTypes
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
        self.webapp.templates.globals["_sqldict"] = self._SQLDict
        self.webapp.templates.globals["_sslcerts"] = self._SSLCerts
        self.webapp.templates.globals["_states"] = self._States
        self.webapp.templates.globals["_statistics"] = self._Statistics
        self.webapp.templates.globals["_tasks"] = self._Tasks
        self.webapp.templates.globals["_times"] = self._Times
        self.webapp.templates.globals["_variables"] = self._Variables
        self.webapp.templates.globals["_validate"] = self._Validate
        self.webapp.templates.globals["misc_wi_data"] = self.misc_wi_data
        self.webapp.templates.globals["webinterface"] = self

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
        self._display_pin_console_at = int(time())
        self.display_pin_console()
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

    @inlineCallbacks
    def change_ports(self, port_nonsecure=None, port_secure=None):
        if port_nonsecure is None and port_secure is None:
            logger.info("Asked to change ports, but nothing has changed.")
            return

        if port_nonsecure is not None:
            if port_nonsecure != self.wi_port_nonsecure():
                self.wi_port_nonsecure(set=port_nonsecure)
                logger.info("Changing port for the non-secure web interface: {port}", port=port_nonsecure)
                if self.web_server_started:
                    yield self.web_interface_listener.stopListening()
                    self.web_server_started = False

        if port_secure is not None:
            if port_secure != self.wi_port_secure():
                self.wi_port_secure(set=port_secure)
                logger.info("Changing port for the secure web interface: {port}", port=port_secure)
                if self.web_server_ssl_started:
                    yield self.web_interface_ssl_listener.stopListening()
                    self.web_server_ssl_started = False

        self.start_web_servers()

    # @inlineCallbacks
    def start_web_servers(self):
        if self.already_starting_web_servers is True:
            return
        self.already_starting_web_servers = True
        logger.debug("starting web servers")
        if self.web_server_started is False:
            if self.wi_port_nonsecure() == 0:
                logger.warn("Non secure port has been disabled. With gateway stopped, edit yomobo.ini and change: webinterface->nonsecure_port")
            else:
                self.web_server_started = True
                port_attempts = 0
                while port_attempts < 100:
                    try:
                        self.web_interface_listener = reactor.listenTCP(self.wi_port_nonsecure()+port_attempts, self.web_factory)
                        break
                    except Exception as e:
                        port_attempts += 1
                if port_attempts >= 100:
                    logger.warn("Unable to start web server, no available port could be found. Tried: {starting} - {ending}",
                                starting=self.wi_port_secure(), ending=self.wi_port_secure()+port_attempts)
                elif port_attempts > 0:
                    self._Configs.set("webinterface", "nonsecure_port", self.wi_port_nonsecure()+port_attempts)
                    logger.warn(
                        "Web interface is on a new port: {new_port}", new_port=self.wi_port_nonsecure()+port_attempts)

        if self.web_server_ssl_started is False:
            if self.wi_port_secure() == 0:
                logger.warn("Secure port has been disabled. With gateway stopped, edit yomobo.ini and change: webinterface->secure_port")
            else:
                self.web_server_ssl_started = True
                cert = self._SSLCerts.get("lib_webinterface")

                if cert["key_crypt"] is None or cert["cert_crypt"] is None:
                    logger.warn("Unable to start secure web interface, cert is not valid.")
                else:
                    contextFactory = ssl.CertificateOptions(privateKey=cert["key_crypt"],
                                                            certificate=cert["cert_crypt"],
                                                            extraCertChain=cert["chain_crypt"])
                    port_attempts = 0
                    # print("########### WEBINTER: about to start SSL port listener")

                    while port_attempts < 100:
                        try:
                            # print("about to start ssl listener on port: %s" % self.wi_port_secure())
                            self.web_interface_ssl_listener = reactor.listenSSL(self.wi_port_secure(), self.web_factory,
                                                                                contextFactory)
                            break
                        except Exception as e:
                            print(f"Unable to start secure web server: {e}")
                            port_attempts += 1
                    if port_attempts >= 100:
                        logger.warn("Unable to start secure web server, no available port could be found. Tried: {starting} - {ending}",
                                    starting=self.wi_port_secure(), ending=self.wi_port_secure()+port_attempts)
                    elif port_attempts > 0:
                        self._Configs.set("webinterface", "secure_port", self.wi_port_secure()+port_attempts)
                        logger.warn(
                            "Secure (tls/ssl) web interface is on a new port: {new_port}", new_port=self.wi_port_secure()+port_attempts)

        logger.debug("done starting web servers")
        self.already_starting_web_servers = False

    def _configuration_set_(self, **kwargs):
        """
        Receive configuruation updates and adjust as needed.

        :param kwargs: section, option(key), value
        :return:
        """
        section = kwargs["section"]
        option = kwargs["option"]
        value = kwargs["value"]

        # if section == "core":
        #     if option == "label":
        #         self.misc_wi_data["gateway_label"] = value

        if self.starting is True:
            return

        if section == "webinterface":
            if option == "nonsecure_port":
                self.change_ports(port_nonsecure=value)
            elif option == "secure_port":
                self.change_ports(port_secure=value)

    def _sslcerts_(self, **kwargs):
        """
        Called to collect to ssl cert requirements.

        :param kwargs:
        :return:
        """
        fqdn = self._Configs.get("dns", "fqdn", None, False)
        if fqdn is None:
            logger.warn("Unable to create webinterface SSL cert: DNS not set properly.")
            return
        cert = {}
        cert["sslname"] = "lib_webinterface"
        cert["sans"] = ["localhost", "l", "local", "i", "e", "internal", "external", str(int(time()))]
        cert["cn"] = cert["sans"][0]
        cert["update_callback"] = self.new_ssl_cert
        return cert

    @inlineCallbacks
    def new_ssl_cert(self, newcert, **kwargs):
        """
        Called when a requested certificate has been signed or updated. If needed, this function
        will function will restart the SSL service if the current certificate has expired or is
        a self-signed cert.

        :param kwargs:
        :return:
        """
        logger.info("Got a new cert! About to install it.")
        if self.web_server_ssl_started is not None:
            yield self.web_interface_ssl_listener.stopListening()
            self.web_server_ssl_started = False
        self.start_web_servers()

    @inlineCallbacks
    def _unload_(self, **kwargs):
        if hasattr(self, "web_factory"):
            if self.web_factory is not None:
                yield self.web_factory.save_log_queue()

    # def WebInterface_configuration_details(self, **kwargs):
    #     return [{"webinterface": {
    #                 "enabled": {
    #                     "description": {
    #                         "en": "Enables/disables the web interface.",
    #                     }
    #                 },
    #                 "port": {
    #                     "description": {
    #                         "en": "Port number for the web interface to listen on."
    #                     }
    #                 }
    #             },
    #     }]

    @webapp.route("/<path:catchall>")
    @require_auth()
    def page_404(self, request, session, catchall):
        request.setResponseCode(404)
        page = self.get_template(request, self.wi_dir + "/pages/errors/404.html")
        return page.render()

    @webapp.handle_errors(NotFound)
    @require_auth()
    def notfound(self, request, failure):
        request.setResponseCode(404)
        return "Not found, I say"

    def display_pin_console(self):
        print("###########################################################")
        print("#                                                         #")
        if self.operating_mode != "run":
            print("# The Yombo Gateway website is running in                 #")
            print("# configuration only mode.                                #")
            print("#                                                         #")

        dns_fqdn = self._Configs.get("dns", "fqdn", None, False)
        if dns_fqdn is None:
            local_hostname = "127.0.0.1"
            internal_hostname = self._Configs.get("core", "localipaddress_v4")
            external_hostname = self._Configs.get("core", "externalipaddress_v4")
            local = f"http://{local_hostname}:{self.wi_port_nonsecure()}"
            internal = f"http://{internal_hostname}:{self.wi_port_nonsecure()}"
            external = f"https://{external_hostname}:{self.wi_port_secure()}"
            print("# The gateway can be accessed from the following urls:    #")
            print("#                                                         #")
            print("# On local machine:                                       #")
            print(f"#  {local:<54} #")
            print("#                                                         #")
            print("# On local network:                                       #")
            print(f"#  {internal:<54} #")
            print("#                                                         #")
            print("# From external network (check port forwarding):          #")
            print(f"#  {external:<54} #")
        else:
            website_url = f"http://{dns_fqdn}"
            print("# The gateway can be accessed from the following url:     #")
            print("#                                                         #")
            print("# From anywhere:                                          #")
            print(f"#  {website_url:<54} #")

        print("#                                                         #")
        print("#                                                         #")
        print("# Web Interface access pin code:                          #")
        print(f"#  {self.auth_pin():<25}                              #")
        print("#                                                         #")
        print("###########################################################")

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

    def add_alert(self, message, level="info", dismissable=True, type="session", deletable=True):
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
            "dismissable": dismissable,
            "deletable": deletable,
        }
        return rand

    def make_alert(self, message, level="info", type="session", dismissable=False):
        """
        Add an alert to the stack.
        :param level: info, warning, error
        :param message:
        :return:
        """
        return {
            "level": level,
            "message": message,
            "dismissable": dismissable,
        }

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
        request.setHeader("server", "Apache/2.4.33 (Ubuntu)")
        request.webinterface.webapp.templates.globals["_"] = request.webinterface.i18n(request)  # set in auth.update_request.
        return self.webapp.templates.get_template(template_path)

    def redirect(self, request, redirect_path):
        request.setHeader("server", "Apache/2.4.33 (Ubuntu)")
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

    # def WebInterface_configuration_set(self, **kwargs):
    #     """
    #     Hook from configuration library. Get any configuration changes.
    #
    #     :param kwargs: "section", "option", and "value" are sent here.
    #     :return:
    #     """
    #     if kwargs["section"] == "webinterface":
    #         option = kwargs["option"]
    #         if option == "auth_pin":
    #             self.auth_pin(set=kwargs["value"])
    #         elif option == "auth_pin_totp":
    #             self.auth_pin_totp(set=kwargs["value"])
    #         elif option == "auth_pin_type":
    #             self.auth_pin_type(set=kwargs["value"])
    #         elif option == "auth_pin_required":
    #             self.auth_pin_required(set=kwargs["value"])

    def _build_dist(self):
        """
        This is blocking code. Doesn"t really matter, it only does it on startup.

        Builds the "dist" directory from the "build" directory. Easy way to update the source css/js files and update
        the webinterface JS and CSS files.
        :return:
        """
        if not path.exists("yombo/lib/webinterface/static/dist"):
            mkdir("yombo/lib/webinterface/static/dist")
        if not path.exists("yombo/lib/webinterface/static/dist/css"):
            mkdir("yombo/lib/webinterface/static/dist/css")
        if not path.exists("yombo/lib/webinterface/static/dist/js"):
            mkdir("yombo/lib/webinterface/static/dist/js")
        if not path.exists("yombo/lib/webinterface/static/dist/fonts"):
            mkdir("yombo/lib/webinterface/static/dist/fonts")

        def do_cat(inputs, output):
            output = "yombo/lib/webinterface/static/" + output
            with open(output, "w") as outfile:
                for fname in inputs:
                    fname = "yombo/lib/webinterface/static/" + fname
                    with open(fname) as infile:
                        outfile.write(infile.read())

        def copytree(src, dst, symlinks=False, ignore=None):
            src = "yombo/lib/webinterface/static/" + src
            dst = "yombo/lib/webinterface/static/" + dst
            if path.exists(dst):
                shutil.rmtree(dst)
            if path.isdir(src):
                if not path.exists(dst):
                    mkdir(dst)
            for item in listdir(src):
                s = path.join(src, item)
                d = path.join(dst, item)
                if path.isdir(s):
                    shutil.copytree(s, d, symlinks, ignore)
                else:
                    shutil.copy2(s, d)

        CAT_SCRIPTS = [
            "source/bootstrap/dist/css/bootstrap.min.css",
        ]
        CAT_SCRIPTS_OUT = "dist/css/bootstrap.min.css"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)
        CAT_SCRIPTS = [
            "source/bootstrap/dist/css/bootstrap.min.css.map",
        ]
        CAT_SCRIPTS_OUT = "dist/css/bootstrap.min.css.map"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/bootstrap/dist/css/bootstrap-theme.min.css",
        ]
        CAT_SCRIPTS_OUT = "dist/css/bootstrap-theme.min.css"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)
        CAT_SCRIPTS = [
            "source/bootstrap/dist/css/bootstrap-theme.min.css.map",
        ]
        CAT_SCRIPTS_OUT = "dist/css/bootstrap-theme.min.css.map"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/creative/css/creative.css",
            ]
        CAT_SCRIPTS_OUT = "dist/css/creative.css"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/metisMenu/metisMenu.min.css",
            "source/sb-admin/css/sb-admin-2.css",
            "source/sb-admin/css/yombo.css",
            ]
        CAT_SCRIPTS_OUT = "dist/css/admin2-metisMenu.min.css"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)
        CAT_SCRIPTS = [
            "source/metisMenu/metisMenu.min.css.map",
        ]
        CAT_SCRIPTS_OUT = "dist/css/metisMenu.min.css.map"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/datatables_1.10.18/dataTables.bootstrap.min.css",
            "source/datatables_1.10.18/responsive.bootstrap.css",
            ]
        CAT_SCRIPTS_OUT = "dist/css/datatables.min.css"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/datatables_1.10.18/jquery.dataTables.min.js",
            "source/datatables_1.10.18/dataTables.bootstrap.min.js",
            "source/datatables_1.10.18/dataTables.responsive.min.js",
            "source/datatables_1.10.18/responsive.bootstrap.js",
            ]
        CAT_SCRIPTS_OUT = "dist/js/datatables.min.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)
        copytree("source/datatables_1.10.18/images/", "dist/images/")

        CAT_SCRIPTS = [
            "source/jquery/jquery-2.2.4.min.js",
            "source/sb-admin/js/js.cookie.min.js",
            "source/bootstrap/dist/js/bootstrap.min.js",
            "source/metisMenu/metisMenu.min.js",
        ]
        CAT_SCRIPTS_OUT = "dist/js/jquery-cookie-bootstrap-metismenu.min.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)
        CAT_SCRIPTS = [
            "source/metisMenu/metisMenu.min.js.map",
        ]
        CAT_SCRIPTS_OUT = "dist/js/metisMenu.min.js.map"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/jquery/jquery.validate.min.js",
        ]
        CAT_SCRIPTS_OUT = "dist/js/jquery.validate.min.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/sb-admin/js/sb-admin-2.min.js",
            "source/sb-admin/js/yombo.js",
        ]
        CAT_SCRIPTS_OUT = "dist/js/sb-admin2.min.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/font-awesome5/js/fontawesome-all.min.js",
            ]
        CAT_SCRIPTS_OUT = "dist/js/fontawesome-all.min.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/jrcode/jquery-qrcode.min.js",
            ]
        CAT_SCRIPTS_OUT = "dist/js/jquery-qrcode.min.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/creative/js/jquery.easing.min.js",
            "source/creative/js/scrollreveal.min.js",
            "source/creative/js/creative.min.js",
            ]
        CAT_SCRIPTS_OUT = "dist/js/creative.min.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/echarts/echarts.min.js",
            ]
        CAT_SCRIPTS_OUT = "dist/js/echarts.min.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)


        CAT_SCRIPTS = [
            "source/sb-admin/js/mappicker.js",
            ]
        CAT_SCRIPTS_OUT = "dist/js/mappicker.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)
        CAT_SCRIPTS = [
            "source/sb-admin/css/mappicker.css",
            ]
        CAT_SCRIPTS_OUT = "dist/css/mappicker.css"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/mqtt/mqttws31.min.js",
            ]
        CAT_SCRIPTS_OUT = "dist/js/mqttws31.min.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/sb-admin/js/jquery.serializejson.min.js",
            ]
        CAT_SCRIPTS_OUT = "dist/js/jquery.serializejson.min.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/sb-admin/js/sha256.js",
            ]
        CAT_SCRIPTS_OUT = "dist/js/sha256.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/yombo/jquery.are-you-sure.js",
            ]
        CAT_SCRIPTS_OUT = "dist/js/jquery.are-you-sure.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        # Just copy files
        copytree("source/bootstrap/dist/fonts/", "dist/fonts/")
        copytree("source/bootstrap-select/", "dist/bootstrap-select/")
        copytree("source/img/", "dist/img/")

class web_translator(object):
    def __init__(self, webinterface, locales):
        self.webinterface = webinterface
        self.translator = webinterface._Localize.get_translator(locales)

    def __call__(self, msgid, default_text=None, **kwargs):
        kwargs["translator"] = self.translator
        return self.webinterface._Localize.handle_translate(msgid, default_text, **kwargs)
