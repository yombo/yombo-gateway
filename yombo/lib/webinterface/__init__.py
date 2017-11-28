# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Web Interface @ Module Development <https://docs.yombo.net/Libraries/Web_Interface>`_


Provides web interface for configuration of the Yombo system.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://docs.yombo.net/gateway/html/current/_modules/yombo/lib/webinterface.html>`_
"""
# Import python libraries
from OpenSSL import crypto
import shutil
from collections import OrderedDict
from os import path, listdir, mkdir
from time import time
from urllib.parse import parse_qs, urlparse
from operator import itemgetter
import jinja2
from klein import Klein
import markdown
from docutils.core import publish_parts
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from hashlib import sha256

# Import twisted libraries
from twisted.web.server import Site
from twisted.internet import reactor, ssl
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import 3rd party libraries
from yombo.ext.expiringdict import ExpiringDict

# Import Yombo libraries
from yombo.core.exceptions import YomboRestart, YomboCritical
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.ext.totp
import yombo.utils

from yombo.lib.webinterface.sessions import Sessions
from yombo.lib.webinterface.auth import require_auth_pin, require_auth, run_first

from yombo.lib.webinterface.routes.api_v1.automation import route_api_v1_automation
from yombo.lib.webinterface.routes.api_v1.command import route_api_v1_command
from yombo.lib.webinterface.routes.api_v1.device import route_api_v1_device
from yombo.lib.webinterface.routes.api_v1.gateway import route_api_v1_gateway
from yombo.lib.webinterface.routes.api_v1.module import route_api_v1_module
from yombo.lib.webinterface.routes.api_v1.notification import route_api_v1_notification
from yombo.lib.webinterface.routes.api_v1.server import route_api_v1_server
from yombo.lib.webinterface.routes.api_v1.statistics import route_api_v1_statistics
from yombo.lib.webinterface.routes.api_v1.system import route_api_v1_system

from yombo.lib.webinterface.routes.devtools.config import route_devtools_config
from yombo.lib.webinterface.routes.devtools.config_commands import route_devtools_config_commands
from yombo.lib.webinterface.routes.devtools.config_device_types import route_devtools_config_device_types
from yombo.lib.webinterface.routes.devtools.config_input_types import route_devtools_config_input_types
from yombo.lib.webinterface.routes.devtools.config_modules import route_devtools_config_modules
from yombo.lib.webinterface.routes.devtools.config_variables import route_devtools_config_variables
from yombo.lib.webinterface.routes.devtools.debug import route_devtools_debug

from yombo.lib.webinterface.routes.atoms import route_atoms
from yombo.lib.webinterface.routes.automation import route_automation
from yombo.lib.webinterface.routes.configs import route_configs
from yombo.lib.webinterface.routes.devices import route_devices
from yombo.lib.webinterface.routes.locations import route_locations
from yombo.lib.webinterface.routes.gateways import route_gateways
from yombo.lib.webinterface.routes.home import route_home
from yombo.lib.webinterface.routes.misc import route_misc
from yombo.lib.webinterface.routes.modules import route_modules
from yombo.lib.webinterface.routes.notices import route_notices
from yombo.lib.webinterface.routes.panel import route_panel
from yombo.lib.webinterface.routes.statistics import route_statistics
from yombo.lib.webinterface.routes.states import route_states
from yombo.lib.webinterface.routes.system import route_system
from yombo.lib.webinterface.routes.voicecmds import route_voicecmds
from yombo.lib.webinterface.routes.setup_wizard import route_setup_wizard
from yombo.lib.webinterface.constants import NAV_SIDE_MENU, DEFAULT_NODE, NOTIFICATION_PRIORITY_MAP_CSS

#from yombo.lib.webinterfaceyombosession import YomboSession

logger = get_logger("library.webinterface")


class NotFound(Exception):
    pass

class Yombo_Site(Site):

    def setup_log_queue(self, webinterface):
        self.save_log_queue_loop = LoopingCall(self.save_log_queue)
        self.save_log_queue_loop.start(8.7, False)

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
        ignored_extensions = ('.js', '.css', '.jpg', '.jpeg', '.gif', '.ico', '.woff2', '.map')
        url_path = request.path.decode().strip()

        if any(url_path.endswith(ext) for ext in ignored_extensions):
            return

        od = OrderedDict({
            'request_at': time(),
            'request_protocol': request.clientproto.decode().strip(),
            'referrer': self._escape(request.getHeader(b"referer") or b"-").strip(),
            'agent': self._escape(request.getHeader(b"user-agent") or b"-").strip(),
            'ip': request.getClientIP(),
            'hostname': request.getRequestHostname().decode().strip(),
            'method': request.method.decode().strip(),
            'path': url_path,
            'secure': request.isSecure(),
            'response_code': request.code,
            'response_size': request.sentLength,
            'uploadable': 1,
            'uploaded': 0,
        })

        self.log_queue.append(od)

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

    def _init_(self, **kwargs):
        self.enabled = self._Configs.get('webinterface', 'enabled', True)
        if not self.enabled:
            return

        self.gateway_id = self._Configs.get2('core', 'gwid', 'local', False)
        # self._LocalDB = self._Loader.loadedLibraries['localdb']
        self._current_dir = self._Atoms.get('yombo.path') + "/yombo"
        self._dir = '/lib/webinterface/'
        self._build_dist()  # Make all the JS and CSS files
        self.secret_pin_totp = self._Configs.get2('webinterface', 'auth_pin_totp',
                                     yombo.utils.random_string(length=16, letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'))
        self._VoiceCmds = self._Loader.loadedLibraries['voicecmds']
        self.misc_wi_data = {}
        self.sessions = Sessions(self._Loader)

        self.wi_port_nonsecure = self._Configs.get2('webinterface', 'nonsecure_port', 8080)
        self.wi_port_secure = self._Configs.get2('webinterface', 'secure_port', 8443)

        self.webapp.templates = jinja2.Environment(loader=jinja2.FileSystemLoader(self._current_dir))
        self.setup_basic_filters()

        # Load API routes
        route_api_v1_automation(self.webapp)
        route_api_v1_command(self.webapp)
        route_api_v1_device(self.webapp)
        route_api_v1_gateway(self.webapp)
        route_api_v1_module(self.webapp)
        route_api_v1_notification(self.webapp)
        route_api_v1_server(self.webapp)
        route_api_v1_statistics(self.webapp)
        route_api_v1_system(self.webapp)

        # Load devtool routes
        route_devtools_config(self.webapp)
        route_devtools_config_commands(self.webapp)
        route_devtools_config_device_types(self.webapp)
        route_devtools_config_input_types(self.webapp)
        route_devtools_config_modules(self.webapp)
        route_devtools_config_variables(self.webapp)
        route_devtools_debug(self.webapp)

        # Load web server routes
        route_atoms(self.webapp)
        route_automation(self.webapp)
        route_configs(self.webapp)
        route_devices(self.webapp)
        route_locations(self.webapp)
        route_devtools_config(self.webapp)
        route_gateways(self.webapp)
        route_home(self.webapp)
        route_misc(self.webapp)
        route_modules(self.webapp)
        route_notices(self.webapp)
        route_panel(self.webapp)
        route_setup_wizard(self.webapp)
        route_statistics(self.webapp)
        route_states(self.webapp)
        route_system(self.webapp)
        route_voicecmds(self.webapp)

        self.temp_data = ExpiringDict(max_age_seconds=1800)
        self.web_server_started = False
        self.web_server_ssl_started = False

        self.already_start_web_servers = False
        self.web_factory = None

        # just here to set a password if it doesn't exist.
        mqtt_password = self._Configs.get('mqtt_users', 'panel.webinterface', yombo.utils.random_string())

    # def _start_(self):
    #     self.webapp.templates.globals['_'] = _  # i18n

    @property
    def operating_mode(self):
        return self._Loader.operating_mode

    @inlineCallbacks
    def _load_(self, **kwargs):
        if hasattr(self, 'sessions'):
            yield self.sessions.init()

        if hasattr(self, 'sessions') is False:
            return
        if not self.enabled:
            return

        self.auth_pin = self._Configs.get2('webinterface', 'auth_pin',
              yombo.utils.random_string(length=4, letters=yombo.utils.human_alpabet()).lower())
        self.auth_pin_totp = self._Configs.get2('webinterface', 'auth_pin_totp', yombo.utils.random_string(length=16))
        self.auth_pin_type = self._Configs.get2('webinterface', 'auth_pin_type', 'pin')
        self.auth_pin_required = self._Configs.get2('webinterface', 'auth_pin_required', True)

        # self.web_factory = Yombo_Site(self.webapp.resource(), None, logPath='/dev/null')
        self.web_factory = Yombo_Site(self.webapp.resource(), None, logPath=None)
        self.web_factory.setup_log_queue(self)
        self.web_factory.noisy = False  # turn off Starting/stopping message
#        self.web_factory.sessionFactory = YomboSession
        self.displayTracebacks = False

        self._display_pin_console_at = 0

        self.misc_wi_data['gateway_configured'] = self._home_gateway_configured()
        self.misc_wi_data['gateway_label'] = self._Configs.get2('core', 'label', 'Yombo Gateway', False)
        self.misc_wi_data['operating_mode'] = self.operating_mode
        self.misc_wi_data['notifications'] = self._Notifications
        self.misc_wi_data['notification_priority_map_css'] = NOTIFICATION_PRIORITY_MAP_CSS
        self.misc_wi_data['breadcrumb'] = []

        # self.functions = {
        #     'yes_no': yombo.utils.is_yes_no,
        # }
        self.webapp.templates.globals['local_gateway'] = self._Gateways.get_local()
        self.webapp.templates.globals['commands'] = self._Commands
        self.webapp.templates.globals['devices'] = self._Devices
        self.webapp.templates.globals['gateways'] = self._Gateways
        self.webapp.templates.globals['misc_wi_data'] = self.misc_wi_data
        self.webapp.templates.globals['devices'] = self._Devices
        # self.webapp.templates.globals['func'] = self.functions

        self.starting = False
        self.start_web_servers()

    def _start_(self, **kwargs):
        self._Notifications.add({
            'title': 'System still starting',
            'message': 'Still starting up. Please wait.',
            'source': 'Web Interface Library',
            'persist': True,
            'priority': 'high',
            'always_show': True,
            'always_show_allow_clear': False,
            'id': 'webinterface:starting',
        })
        added_notification = True
        self._get_nav_side_items()

    def _started_(self, **kwargs):
        # if self.operating_mode != 'run':
        self._display_pin_console_at = int(time())
        self.display_pin_console()
        self._Notifications.delete('webinterface:starting')

    def check_have_required_nodes(self):
        try:
            node = yield self._Nodes.get('main_page', 'webinterface_page')
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
        if self.already_start_web_servers is True:
            return
        self.already_start_web_servers = True
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
                    self._Configs.set('webinterface', 'nonsecure_port', self.wi_port_nonsecure()+port_attempts)
                    logger.warn(
                        "Web interface is on a new port: {new_port}", new_port=self.wi_port_nonsecure()+port_attempts)

        if self.web_server_ssl_started is False:
            if self.wi_port_secure() == 0:
                logger.warn("Secure port has been disabled. With gateway stopped, edit yomobo.ini and change: webinterface->secure_port")
            else:
                self.web_server_ssl_started = True
                cert = self._SSLCerts.get('lib_webinterface')
                # print("wb init: cert: %s" % cert)

                privkeypyssl = crypto.load_privatekey(crypto.FILETYPE_PEM, cert['key'])
                certpyssl = crypto.load_certificate(crypto.FILETYPE_PEM, cert['cert'])
                if cert['chain'] is not None:
                    chainpyssl = [crypto.load_certificate(crypto.FILETYPE_PEM, cert['chain'])]
                    # chainpyssl = [crypto.load_certificate(crypto.FILETYPE_PEM, cert['chain'])]
                else:
                    chainpyssl = None
                # chainpyssl = None
                contextFactory = ssl.CertificateOptions(privateKey=privkeypyssl,
                                                        certificate=certpyssl,
                                                        extraCertChain=chainpyssl)

                port_attempts = 0
                while port_attempts < 100:
                    try:
                        self.web_interface_ssl_listener = reactor.listenSSL(self.wi_port_secure(), self.web_factory,
                                                                            contextFactory)
                        break
                    except Exception as e:
                        port_attempts += 1
                if port_attempts >= 100:
                    logger.warn("Unable to start secure web server, no available port could be found. Tried: {starting} - {ending}",
                                starting=self.wi_port_secure(), ending=self.wi_port_secure()+port_attempts)
                elif port_attempts > 0:
                    self._Configs.set('webinterface', 'secure_port', self.wi_port_secure()+port_attempts)
                    logger.warn(
                        "Secure (tls/ssl) web interface is on a new port: {new_port}", new_port=self.wi_port_secure()+port_attempts)

        logger.debug("done starting web servers")
        self.already_start_web_servers = False

    def _configuration_set_(self, **kwargs):
        """
        Receive configuruation updates and adjust as needed.

        :param kwargs: section, option(key), value
        :return:
        """
        section = kwargs['section']
        option = kwargs['option']
        value = kwargs['value']

        # if section == 'core':
        #     if option == 'label':
        #         self.misc_wi_data['gateway_label'] = value

        if self.starting is True:
            return

        if section == 'webinterface':
            if option == 'nonsecure_port':
                self.change_ports(port_nonsecure=value)
            elif option == 'secure_port':
                self.change_ports(port_secure=value)

    def _sslcerts_(self, **kwargs):
        """
        Called to collect to ssl cert requirements.

        :param kwargs:
        :return:
        """
        fqdn = self._Configs.get('dns', 'fqdn', None, False)
        if fqdn is None:
            logger.warn("Unable to create webinterface SSL cert: DNS not set properly.")
            return
        cert = {}
        cert['sslname'] = "lib_webinterface"
        cert['sans'] = ['localhost', 'l', 'local', 'i', 'e', 'internal', 'external', str(int(time()))]
        cert['cn'] = cert['sans'][0]
        cert['callback'] = self.new_ssl_cert
        return cert

    def new_ssl_cert(self, newcert, **kwargs):
        """
        Called when a requested certificate has been signed or updated. If needed, this funciton
        will function will restart the SSL service if the current certificate has expired or is
        a self-signed cert.

        :param kwargs:
        :return:
        """
        logger.warn("Got updated SSL Cert!  Thanks.")
        pass

    @inlineCallbacks
    def _unload_(self, **kwargs):
        if hasattr(self, 'web_factory'):
            if self.web_factory is not None:
                yield self.web_factory.save_log_queue()
        if hasattr(self, 'sessions'):
            if self.sessions is not None:
                yield self.sessions._unload_()

    # def WebInterface_configuration_details(self, **kwargs):
    #     return [{'webinterface': {
    #                 'enabled': {
    #                     'description': {
    #                         'en': 'Enables/disables the web interface.',
    #                     }
    #                 },
    #                 'port': {
    #                     'description': {
    #                         'en': 'Port number for the web interface to listen on.'
    #                     }
    #                 }
    #             },
    #     }]

    @webapp.route('/<path:catchall>')
    @require_auth()
    def page_404(self, request, session, catchall):
        request.setResponseCode(404)
        page = self.get_template(request, self._dir + 'pages/404.html')
        return page.render()

    @webapp.handle_errors(NotFound)
    @require_auth()
    def notfound(self, request, failure):
        request.setResponseCode(404)
        return 'Not found, I say'

    def display_pin_console(self):
        print("###########################################################")
        print("#                                                         #")
        if self.operating_mode != 'run':
            print("# The Yombo Gateway website is running in                 #")
            print("# configuration only mode.                                #")
            print("#                                                         #")

        dns_fqdn = self._Configs.get('dns', 'fqdn', None, False)
        if dns_fqdn is None:
            local_hostname = "127.0.0.1"
            internal_hostname = self._Configs.get('core', 'localipaddress_v4')
            external_hostname = self._Configs.get('core', 'externalipaddress_v4')
            local = "http://%s:%s" %(local_hostname, self.wi_port_nonsecure())
            internal = "http://%s:%s" %(internal_hostname, self.wi_port_nonsecure())
            external = "https://%s:%s" % (external_hostname, self.wi_port_secure())
            print("# The gateway can be accessed from the following urls:    #")
            print("#                                                         #")
            print("# On local machine:                                       #")
            print("#  %-54s #" % local)
            print("#                                                         #")
            print("# On local network:                                       #")
            print("#  %-54s #" % internal)
            print("#                                                         #")
            print("# From external network (check port forwarding):          #")
            print("#  %-54s #" % external)
        else:
            website_url = "http://%s" % dns_fqdn
            print("# The gateway can be accessed from the following url:     #")
            print("#                                                         #")
            print("# From anywhere:                                          #")
            print("#  %-54s #" % website_url)

        print("#                                                         #")
        print("#                                                         #")
        print("# Web Interface access pin code:                          #")
        print("#  %-25s                              #" % self.auth_pin())
        print("#                                                         #")
        print("###########################################################")

    def i18n(self, request):
        """
        Gets a translator based on the language the browser provides us.

        :param request: The browser request.
        :return:
        """
        return web_translator(self, request)

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
                   'nav_side': [
                       {
                       'label1': 'Tools',
                       'label2': 'MQTT',
                       'priority1': 3000,
                       'priority2': 10000,
                       'icon': 'fa fa-wrench fa-fw',
                       'url': '/tools/mqtt',
                       'tooltip': '',
                       'opmode': 'run',
                       },
                   ],
                   'routes': [
                       self.web_interface_routes,
                  ],
               }

        """
        # first, lets get the top levels already defined so children don't re-arrange ours.
        top_levels = {}
        temp_list = sorted(NAV_SIDE_MENU, key=itemgetter('priority1', 'priority2'))
        for item in temp_list:
            label1 = item['label1']
            if label1 not in temp_list:
                top_levels[label1] = item['priority1']

        nav_side_menu = NAV_SIDE_MENU.copy()

        add_on_menus = yield yombo.utils.global_invoke_all('_webinterface_add_routes_',
                                                           called_by=self,
                                                           )
        for component, options in add_on_menus.items():
            if 'nav_side' in options:
                for new_nav in options['nav_side']:
                    if isinstance(new_nav['priority1'], int) is False:
                        new_nav['priority1'] = top_levels[new_nav['label1']]
                    nav_side_menu.append(new_nav)
            if 'menu_priorities' in options:  # allow modules to change the ording of top level menus
                for label, priority in options['menu_priorities'].items():
                    top_levels[label] = priority
            if 'routes' in options:
                for new_route in options['routes']:
                    new_route(self.webapp)

        # build menu tree
        self.misc_wi_data['nav_side'] = OrderedDict()

        temp_list = sorted(nav_side_menu, key=itemgetter('priority1', 'priority2'))
        for item in temp_list:
            label1 = item['label1']
            if label1 not in self.misc_wi_data['nav_side']:
                self.misc_wi_data['nav_side'][label1] = []
            self.misc_wi_data['nav_side'][label1].append(item)
        self.starting = False

    def add_alert(self, message, level='info', dismissable=True, type='session', deletable=True):
        """
        Add an alert to the stack.
        :param level: info, warning, error
        :param message:
        :return:
        """
        rand = yombo.utils.random_string(length=12)
        self.alerts[rand] = {
            'type': type,
            'level': level,
            'message': message,
            'dismissable': dismissable,
            'deletable': deletable,
        }
        return rand

    def make_alert(self, message, level='info', type='session', dismissable=False):
        """
        Add an alert to the stack.
        :param level: info, warning, error
        :param message:
        :return:
        """
        return {
            'level': level,
            'message': message,
            'dismissable': dismissable,
        }

    def get_alerts(self, type=None, session=None):
        """
        Retrieve a list of alerts for display.
        """
        if type is None:
            type = 'session'

        show_alerts = OrderedDict()
        for keyid in list(self.alerts.keys()):
            if self.alerts[keyid]['type'] == type:
                show_alerts[keyid] = self.alerts[keyid]
                if type == 'session':
                    del self.alerts[keyid]
        return show_alerts

    def get_template(self, request, template_path):
        request.setHeader('server', 'Yombo/1.0')
        return self.webapp.templates.get_template(template_path)

    def redirect(self, request, redirect_path):
        request.setHeader('server', 'Yombo/1.0')
        request.redirect(redirect_path)

    def _tpl_home_gateway_configured(self):
        if not self._home_gateway_configured():
            return "This gateway is not properly configured. Click _here_ to run the configuration wizard."
        else:
            return ""

    def _home_gateway_configured(self):
        gwuuid = self._Configs.get("core", "gwuuid", None, False)
        gwhash = self._Configs.get("core", "gwhash", None, False)
        gpgkeyid = self._Configs.get('gpg', 'keyid', None, False)

        if gwuuid is None or gwhash is None or gpgkeyid is None:
            return False
        else:
            return True

    def _get_parms(self, request):
        return parse_qs(urlparse(request.uri).query)

    def format_markdown(self, input_text, formatting=None):
        if formatting == 'restructured' or formatting is None:
            return publish_parts(input_text, writer_name='html')['html_body']
        elif formatting == 'markdown':
            return markdown.markdown(input_text, extensions=['markdown.extensions.nl2br', 'markdown.extensions.codehilite'])
        return input_text

    def make_link(self, link, link_text, target = None):
        if link == '' or link is None or link.lower() == "None":
            return "None"
        if target is None:
            target = "_self"
        return '<a href="%s" target="%s">%s</a>' % (link, target, link_text)

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
        if hasattr(request, 'breadcrumb') is False:
            request.breadcrumb = []
            self.misc_wi_data['breadcrumb'] = request.breadcrumb

        if show is None:
            show = True

        if style is None:
            style = 'link'
        elif style == 'select_groups':
            items = {}
            for option_label, option_data in data.items():
                items[option_label] = []
                for select_text, select_url in option_data.items():
                    selected = ''
                    option_style = 'None'
                    if select_url.startswith("$"):
                        selected = 'selected'
                        select_url = select_url[1:]
                    elif select_url.startswith("#"):
                        option_style = 'divider'

                    items[option_label].append({
                        'option_style': option_style,
                        'text': select_text,
                        'url': select_url,
                        'selected': selected,
                    })
            data = items
        elif style == 'select':
            items = []
            for select_text, select_url in data.items():
                selected = ''
                option_style = 'None'
                if select_url.startswith("$"):
                    selected = 'selected'
                    select_url = select_url[1:]
                elif select_url.startswith("#"):
                    option_style = 'divider'

                items.append({
                    'option_style': option_style,
                    'text': select_text,
                    'url': select_url,
                    'selected': selected,
                })
            data = items

        hash = sha256(str(str(url) + str(text) + str(show) + str(style) + json.dumps(data)).encode()).hexdigest()
        breadcrumb = {
            'hash': hash,
            'url': url,
            'text': text,
            'show': show,
            'style': style,
            'data': data,
        }
        request.breadcrumb.append(breadcrumb)

    def setup_basic_filters(self):
        self.webapp.templates.filters['yes_no'] = yombo.utils.is_yes_no
        self.webapp.templates.filters['make_link'] = self.make_link
        self.webapp.templates.filters['status_to_string'] = yombo.utils.status_to_string
        self.webapp.templates.filters['public_to_string'] = yombo.utils.public_to_string
        self.webapp.templates.filters['epoch_to_human'] = yombo.utils.epoch_to_string
        self.webapp.templates.filters['epoch_to_pretty_date'] = self._Times.get_age # yesterday, 5 minutes ago, etc.
        self.webapp.templates.filters['format_markdown'] = self.format_markdown
        self.webapp.templates.filters['hide_none'] = self.dispay_hide_none
        self.webapp.templates.filters['display_encrypted'] = self._GPG.display_encrypted
        self.webapp.templates.filters['display_temperature'] = self._Localize.display_temperature

    def dispay_hide_none(self, input):
        if input is None:
            return ""
        if isinstance(input, str):
            if input.lower() == "none":
                return ""
        return input

    def restart(self, request, message=None, redirect=None):
        if message is None:
            message = "Web interface requested restart."
        if redirect is None:
            redirect = "/?"

        page = self.get_template(request, self._dir + 'pages/restart.html')
        reactor.callLater(0.3, self.do_restart)
        return page.render(message=message,
                           redirect=redirect,
                           uptime=str(self._Atoms['running_since'])
                           )

    def do_restart(self):
        try:
            raise YomboRestart("Web Interface setup wizard complete.")
        except:
            pass

    def shutdown(self, request):
        page = self.get_template(request, self._dir + 'pages/shutdown.html')
        # reactor.callLater(0.3, self.do_shutdown)
        return page.render()

    def do_shutdown(self):
        raise YomboCritical("Web Interface setup wizard complete.")

    # def WebInterface_configuration_set(self, **kwargs):
    #     """
    #     Hook from configuration library. Get any configuration changes.
    #
    #     :param kwargs: 'section', 'option', and 'value' are sent here.
    #     :return:
    #     """
    #     if kwargs['section'] == 'webinterface':
    #         option = kwargs['option']
    #         if option == 'auth_pin':
    #             self.auth_pin(set=kwargs['value'])
    #         elif option == 'auth_pin_totp':
    #             self.auth_pin_totp(set=kwargs['value'])
    #         elif option == 'auth_pin_type':
    #             self.auth_pin_type(set=kwargs['value'])
    #         elif option == 'auth_pin_required':
    #             self.auth_pin_required(set=kwargs['value'])

    def _build_dist(self):
        """
        This is blocking code. Doesn't really matter, it only does it on startup.

        Builds the 'dist' directory from the 'build' directory. Easy way to update the source css/js files and update
        the webinterface JS and CSS files.
        :return:
        """
        if not path.exists('yombo/lib/webinterface/static/dist'):
            mkdir('yombo/lib/webinterface/static/dist')
        if not path.exists('yombo/lib/webinterface/static/dist/css'):
            mkdir('yombo/lib/webinterface/static/dist/css')
        if not path.exists('yombo/lib/webinterface/static/dist/js'):
            mkdir('yombo/lib/webinterface/static/dist/js')
        if not path.exists('yombo/lib/webinterface/static/dist/fonts'):
            mkdir('yombo/lib/webinterface/static/dist/fonts')

        def do_cat(inputs, output):
            output = 'yombo/lib/webinterface/static/' + output
            with open(output, 'w') as outfile:
                for fname in inputs:
                    fname = 'yombo/lib/webinterface/static/' + fname
                    with open(fname) as infile:
                        outfile.write(infile.read())

        def copytree(src, dst, symlinks=False, ignore=None):
            src = 'yombo/lib/webinterface/static/' + src
            dst = 'yombo/lib/webinterface/static/' + dst
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
            'source/jquery/jquery-2.2.4.min.js',
            'source/sb-admin/js/js.cookie.min.js',
            'source/bootstrap/dist/js/bootstrap.min.js',
            'source/metisMenu/metisMenu.min.js',
        ]
        CAT_SCRIPTS_OUT = 'dist/js/jquery-cookie-bootstrap-metismenu.min.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/jquery/jquery.validate.min.js',
        ]
        CAT_SCRIPTS_OUT = 'dist/js/jquery.validate.min.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/bootstrap/dist/css/bootstrap.min.css',
            'source/metisMenu/metisMenu.min.css',
        ]
        CAT_SCRIPTS_OUT = 'dist/css/bootstrap-metisMenu.min.css'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/bootstrap/dist/css/bootstrap.min.css',
        ]
        CAT_SCRIPTS_OUT = 'dist/css/bootstrap.min.css'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/sb-admin/js/sb-admin-2.min.js',
            'source/sb-admin/js/yombo.js',
        ]
        CAT_SCRIPTS_OUT = 'dist/js/sb-admin2.min.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/sb-admin/css/sb-admin-2.css',
            'source/sb-admin/css/yombo.css',
            ]
        CAT_SCRIPTS_OUT = 'dist/css/admin2.min.css'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/font-awesome/css/font-awesome.min.css',
            ]
        CAT_SCRIPTS_OUT = 'dist/css/font_awesome.min.css'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/datatables-plugins/integration/bootstrap/3/dataTables.bootstrap.css',
            'source/datatables-responsive/css/responsive.dataTables.min.css',
            ]
        CAT_SCRIPTS_OUT = 'dist/css/datatables.min.css'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/datatables/js/jquery.dataTables.min.js',
            'source/datatables-plugins/integration/bootstrap/3/dataTables.bootstrap.min.js',
            'source/datatables-responsive/js/dataTables.responsive.min.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/datatables.min.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/jrcode/jquery-qrcode.min.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/jquery-qrcode.min.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/creative/js/jquery.easing.min.js',
            'source/creative/js/scrollreveal.min.js',
            'source/creative/js/creative.min.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/creative.min.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/creative/css/creative.css',
            ]
        CAT_SCRIPTS_OUT = 'dist/css/creative.css'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/echarts/echarts.min.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/echarts.min.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)


        CAT_SCRIPTS = [
            'source/sb-admin/js/mappicker.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/mappicker.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)
        CAT_SCRIPTS = [
            'source/sb-admin/css/mappicker.css',
            ]
        CAT_SCRIPTS_OUT = 'dist/css/mappicker.css'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/mqtt/mqttws31.min.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/mqttws31.min.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/sb-admin/js/jquery.serializejson.min.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/jquery.serializejson.min.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/sb-admin/js/sha256.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/sha256.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/yombo/jquery.are-you-sure.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/jquery.are-you-sure.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        # Just copy files
        copytree('source/font-awesome/fonts/', 'dist/fonts/')

        copytree('source/bootstrap/dist/fonts/', 'dist/fonts/')

class web_translator(object):
    def __init__(self, webinterface, request):
        self.webinterface = webinterface
        self.translator = webinterface._Localize.get_translator(webinterface._Localize.parse_accept_language(request.getHeader('accept-language')))

    def __call__(self, msgctxt, msgid1=None, msgid2=None, num=None, *args, **kwargs):
        return self.webinterface._Localize.handle_translate(msgctxt, msgid1=msgid1, msgid2=msgid2, num=num,
                                                     translator=self.translator)