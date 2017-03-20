# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Provides web interface for configuration of the Yombo system.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import shutil
from collections import OrderedDict
from os import path, listdir, mkdir
from os.path import dirname, abspath
from time import strftime, localtime, time
from urlparse import parse_qs, urlparse
from operator import itemgetter
import jinja2
from klein import Klein
import markdown
from docutils.core import publish_parts
from random import randint

try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

# Import twisted libraries
from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue

# Import 3rd party libraries
from yombo.ext.expiringdict import ExpiringDict

# Import Yombo libraries
from yombo.core.exceptions import YomboRestart, YomboCritical, YomboWarning

from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.utils

from yombo.lib.webinterface.sessions import Sessions
from yombo.lib.webinterface.auth import require_auth_pin, require_auth, run_first

from yombo.lib.webinterface.route_atoms import route_atoms
from yombo.lib.webinterface.route_automation import route_automation
from yombo.lib.webinterface.route_api_v1 import route_api_v1
from yombo.lib.webinterface.route_configs import route_configs
from yombo.lib.webinterface.route_devices import route_devices
from yombo.lib.webinterface.route_devtools_debug import route_devtools_debug
from yombo.lib.webinterface.route_devtools_config import route_devtools_config
from yombo.lib.webinterface.route_modules import route_modules
from yombo.lib.webinterface.route_notices import route_notices
from yombo.lib.webinterface.route_statistics import route_statistics
from yombo.lib.webinterface.route_states import route_states
from yombo.lib.webinterface.route_system import route_system
from yombo.lib.webinterface.route_voicecmds import route_voicecmds

from yombo.lib.webinterface.route_setup_wizard import route_setup_wizard

#from yombo.lib.webinterfaceyombosession import YomboSession

logger = get_logger("library.webconfig")

simulate_gw = {
              'new':{
                  'label': '',
                  'description': '',
                  'variables': {
                      'elevation': '75',
                      'latitude': '37.758',
                      'longitude': '-122.438'
                      }
                  },
              'xyz1':{
                  'label': 'Home',
                  'description': 'Main house gateway',
                  'variables': {
                      'latitude': 38.576,
                      'longitude': -121.276,
                      'elevation': 100,
                      }
                  },
              'abc2':{
                  'label': 'Garage',
                  'description': 'The garage',
                  'variables': {
                      'latitude': 37.791,
                      'longitude': -121.858,
                      'elevation': 50,
                      }
                  },
              'mno3':{
                  'label': 'Shed',
                  'description': 'In the shed!',
                  'variables': {
                      'latitude': 37.259,
                      'longitude': -122.177,
                      'elevation': 25,
                      }
                  },
              }

nav_side_menu = [
    {
        'label1': 'Settings',
        'label2': 'Devices',
        'priority1': 500,
        'priority2': 500,
        'icon': 'fa fa-cogs fa-fw',
        'url': '/devices/index',
        'tooltip': 'Show Devices',
        'opmode': 'run',
    },
    {
        'label1': 'Settings',
        'label2': 'Modules',
        'priority1': 500,
        'priority2': 1500,
        'icon': 'fa fa-cogs fa-fw',
        'url': '/modules/index',
        'tooltip': '',
        'opmode': 'run',
    },
    {
        'label1': 'Settings',
        'label2': 'Basic Settings',
        'priority1': 500,
        'priority2': 2000,
        'icon': 'fa fa-cogs fa-fw',
        'url': '/configs/basic',
        'tooltip': '',
        'opmode': 'run',
    },
    {
        'label1': 'Settings',
        'label2': 'DNS',
        'priority1': 500,
        'priority2': 2250,
        'icon': 'fa fa-cogs fa-fw',
        'url': '/configs/dns',
        'tooltip': '',
        'opmode': 'run',
    },
    {
        'label1': 'Settings',
        'label2': 'Encryption Keys',
        'priority1': 500,
        'priority2': 2500,
        'icon': 'fa fa-wrench fa-fw',
        'url': '/configs/gpg/index',
        'tooltip': '',
        'opmode': 'run',
    },
    {
        'label1': 'Settings',
        'label2': 'Yombo.Ini',
        'priority1': 500,
        'priority2': 3000,
        'icon': 'fa fa-wrench fa-fw',
        'url': '/configs/yombo_ini',
        'tooltip': '',
        'opmode': 'run',
    },

    {
        'label1': 'Info',
        'label2': 'Atoms',
        'priority1': 1000,
        'priority2': 2000,
        'icon': 'fa fa-info fa-fw',
        'url': '/atoms/index',
        'tooltip': '',
        'opmode': 'run',
    },
    {
        'label1': 'Info',
        'label2': 'Delayed Commands',
        'priority1': 1000,
        'priority2': 2500,
        'icon': 'fa fa-info fa-fw',
        'url': '/devices/delayed_commands',
        'tooltip': '',
        'opmode': 'run',
    },
    {
        'label1': 'Info',
        'label2': 'States',
        'priority1': 1000,
        'priority2': 3000,
        'icon': 'fa fa-info fa-fw',
        'url': '/states/index',
        'tooltip': '',
        'opmode': 'run',
    },
    {
        'label1': 'Info',
        'label2': 'Voice Commands',
        'priority1': 1000,
        'priority2': 4000,
        'icon': 'fa fa-info fa-fw',
        'url': '/voicecmds/index',
        'tooltip': '',
        'opmode': 'run',
    },

    {
        'label1': 'Automation',
        'label2': 'Rules',
        'priority1': 1500,
        'priority2': 500,
        'icon': 'fa fa-random fa-fw',
        'url': '/automation/index',
        'tooltip': 'Show Rules',
        'opmode': 'run',
    },
    {
        'label1': 'Automation',
        'label2': 'Platforms',
        'priority1': 1500,
        'priority2': 1500,
        'icon': 'fa fa-random fa-fw',
        'url': '/automation/platforms',
        'tooltip': 'Automation Platforms',
        'opmode': 'run',
    },
    {
        'label1': 'Automation',
        'label2': 'Add Rule',
        'priority1': 1500,
        'priority2': 1000,
        'icon': 'fa fa-random fa-fw',
        'url': '/automation/add_rule',
        'tooltip': 'Automation Platforms',
        'opmode': 'run',
    },
    {
        'label1': 'Statistics',
        'label2': 'General',
        'priority1': 2000,
        'priority2': 500,
        'icon': 'fa fa-dashboard fa-fw',
        'url': '/statistics/index',
        'tooltip': '',
        'opmode': 'run',
    },
    {
        'label1': 'Tools',
        'label2': 'General',
        'priority1': 3000,
        'priority2': 500,
        'icon': 'fa fa-wrench fa-fw',
        'url': '/tools/index',
        'tooltip': '',
        'opmode': 'run',
    },



    {
        'label1': 'Developer Tools',
        'label2': 'Config Tools',
        'priority1': 5000,
        'priority2': 500,
        'icon': 'fa fa-code fa-fw',
        'url': '/devtools/config/index',
        'tooltip': '',
        'opmode': 'run',
    },
    {
        'label1': 'Developer Tools',
        'label2': 'Debug',
        'priority1': 5000,
        'priority2': 1000,
        'icon': 'fa fa-code fa-fw',
        'url': '/devtools/debug/index',
        'tooltip': '',
        'opmode': 'run',
    },
    {
        'label1': 'System',
        'label2': 'Status',
        'priority1': 6000,
        'priority2': 500,
        'icon': 'fa fa-hdd-o fa-fw',
        'url': '/system/index',
        'tooltip': '',
        'opmode': 'run',
    },
    {
        'label1': 'System',
        'label2': 'Control',
        'priority1': 6000,
        'priority2': 1000,
        'icon': 'fa fa-hdd-o fa-fw',
        'url': '/system/control',
        'tooltip': '',
        'opmode': 'run',
    },
]

notification_priority_map_css = {
    'low': 'info',
    'normal': 'info',
    'high': 'warning',
    'urent': 'danger'
}

class NotFound(Exception):
    pass

class WebInterface(YomboLibrary):
    """
    Web interface framework.
    """
    webapp = Klein()  # Like Flask, but for twisted

    visits = 0
    alerts = OrderedDict()

    def _init_(self):
        self.starting = True
        self.enabled = self._Configs.get('webinterface', 'enabled', True)
        if not self.enabled:
            return

        self.gwid = self._Configs.get("core", "gwid")
        self._LocalDb = self._Loader.loadedLibraries['localdb']
        self._current_dir = self._Atoms.get('yombo.path') + "/yombo"
        # print "web interface direct1: %s" % self._current_dir
        self._dir = '/lib/webinterface/'
        self._build_dist()  # Make all the JS and CSS files

        self.api = self._Loader.loadedLibraries['yomboapi']
        self._VoiceCmds = self._Loader.loadedLibraries['voicecmds']
        self.misc_wi_data = {}
        self.sessions = Sessions(self._Loader)

        self.wi_port_nonsecure = self._Configs.get('webinterface', 'nonsecure_port', 8080)
        self.wi_port_secure = self._Configs.get('webinterface', 'secure_port', 8443)

        self.webapp.templates = jinja2.Environment(loader=jinja2.FileSystemLoader(self._current_dir))
        self.setup_basic_filters()

        route_atoms(self.webapp)
        route_automation(self.webapp)
        route_api_v1(self.webapp)
        route_configs(self.webapp)
        route_devices(self.webapp)
        route_devtools_debug(self.webapp)
        route_devtools_config(self.webapp)
        route_modules(self.webapp)
        route_notices(self.webapp)
        route_setup_wizard(self.webapp)
        route_statistics(self.webapp)
        route_states(self.webapp)
        route_system(self.webapp)
        route_voicecmds(self.webapp)

        self.temp_data = ExpiringDict(max_age_seconds=1800)

    # def _start_(self):
    #     self.webapp.templates.globals['_'] = _  # i18n

    @webapp.handle_errors(NotFound)
    @require_auth()
    def notfound(self, request, failure):
        request.setResponseCode(404)
        return 'Not found, I say'

    @webapp.route('/<path:catchall>')
    @require_auth()
    @run_first()
    def page_404(self, request, session, catchall):
        request.setResponseCode(404)
        page = self.get_template(request, self._dir + 'pages/404.html')
        return page.render()

    @inlineCallbacks
    def _load_(self):
        if hasattr(self, 'sessions'):
            yield self.sessions.init()

    def _start_(self):
        if hasattr(self, 'sessions') is False:
            return
        if not self.enabled:
            return
        self._op_mode = self._Atoms['loader.operation_mode']

        self.auth_pin = self._Configs.get('webinterface', 'auth_pin',
              yombo.utils.random_string(length=4, letters=yombo.utils.human_alpabet()).lower())
        self.auth_pin_totp = self._Configs.get('webinterface', 'auth_pin_totp', yombo.utils.random_string(length=16))
        self.auth_pin_type = self._Configs.get('webinterface', 'auth_pin_type', 'pin')
        self.auth_pin_required = self._Configs.get('webinterface', 'auth_pin_required', True)

        self.web_factory = Site(self.webapp.resource(), None, logPath='/dev/null')
        self.web_factory.noisy = False  # turn off Starting/stopping message
#        self.web_factory.sessionFactory = YomboSession
        self.displayTracebacks = False

        self.web_interface_listener = reactor.listenTCP(self.wi_port_nonsecure, self.web_factory)
        self._display_pin_console_time = 0

        self.misc_wi_data['gateway_configured'] = self._home_gateway_configured()
        self.misc_wi_data['gateway_label'] = self._Configs.get('core', 'label', 'Yombo Gateway', False)
        self.misc_wi_data['operation_mode'] = self._op_mode
        self.misc_wi_data['notifications'] = self._Notifications
        self.misc_wi_data['notification_priority_map_css'] = notification_priority_map_css
        self.misc_wi_data['breadcrumb'] = []

        # self.functions = {
        #     'yes_no': yombo.utils.is_yes_no,
        # }

        self.webapp.templates.globals['misc_wi_data'] = self.misc_wi_data
        # self.webapp.templates.globals['func'] = self.functions

    def _module_started_(self, **kwargs):
        """
        to be deprecated. use i18n below.
        :param kwargs:
        :return:
        """
        # self.webapp.templates.globals['_'] = _  # i18n
        pass

    def _started_(self):
        # if self._op_mode != 'run':
        self._display_pin_console_time = int(time())
        self.display_pin_console()

    def _unload_(self):
        return self.sessions._unload_()

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

    def _configuration_set_(self, **kwargs):
        """
        Receive configuruation updates and adjust as needed.

        :param kwargs: section, option(key), value
        :return:
        """
        section = kwargs['section']
        option = kwargs['option']
        value = kwargs['value']

        if section == 'core':
            if option == 'label':
                self.misc_wi_data['gateway_label'] = value

    def i18n(self, request):
        """
        Gets a translator based on the language the browser provides us.

        :param request: The browser request.
        :return:
        """
        return web_translator(self, request)

    def _module_prestart_(self, **kwargs):
        """
        Called before modules have their _prestart_ function called.

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
        temp_dict = {}
        newlist = sorted(nav_side_menu, key=itemgetter('priority1', 'priority2'))
        for item in newlist:
            level1 = item['label1']
            if level1 not in newlist:
                temp_dict[level1] = item['priority1']

        temp_strings = yombo.utils.global_invoke_all('_webinterface_add_routes_')
        # print "new routes: %s" % temp_strings
        for component, options in temp_strings.iteritems():
            # print "1111"
            if 'nav_side' in options:
                # print "1111 2"
                for new_nav in options['nav_side']:
                    # print "1111 3"
                    if new_nav['label1'] in temp_dict:
                        # print "1111 4"
                        new_nav['priority1'] =  temp_dict[new_nav['label1']]
                    nav_side_menu.append(new_nav)
            if 'routes' in options:
                for new_route in options['routes']:
                    new_route(self.webapp)

        self.misc_wi_data['nav_side'] = OrderedDict()
        newlist = sorted(nav_side_menu, key=itemgetter('priority1', 'priority2'))
        for item in newlist:
            level1 = item['label1']
            if level1 not in self.misc_wi_data['nav_side']:
                self.misc_wi_data['nav_side'][level1] = []
            self.misc_wi_data['nav_side'][level1].append(item)
        # print self.misc_wi_data['nav_side']
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
        for keyid in self.alerts.keys():
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

    def check_op_mode(self, request, router, **kwargs):
#        print "op mode: %s" % self._op_mode
        if self._op_mode == 'config':
            # print "showing config home"
            method = getattr(self, 'config_'+ router)
            return method(request, **kwargs)
        elif self._op_mode == 'firstrun':
            method = getattr(self, 'firstrun_'+ router)
            return method(request, **kwargs)
        method = getattr(self, 'run_'+ router)
        return method(request, **kwargs)

    @webapp.route('/')
    @run_first()
    def home(self, request):
        return self.check_op_mode(request, 'home')

    @require_auth()
    @run_first()
    def run_home(self, request, session):
        page = self.webapp.templates.get_template(self._dir + 'pages/index.html')

        return page.render(alerts=self.get_alerts(),
                           delay_commands = self._Devices.delay_queue_active,
                           automation_rules = len(self._Loader.loadedLibraries['automation'].rules),
                           devices=self._Libraries['devices']._devicesByUUID,
                           modules=self._Libraries['modules']._modulesByUUID,
                           states=self._Libraries['states'].get_states(),
                           )

    @require_auth()
    @run_first()
    def config_home(self, request, session):
        # auth = self.require_auth(request)
        # if auth is not None:
        #     return auth

        page = self.get_template(request, self._dir + 'config_pages/index.html')
        return page.render(alerts=self.get_alerts(),
                           )
    def firstrun_home(self, request):
        return self.redirect(request, '/setup_wizard/1')

    @webapp.route('/logout', methods=['GET'])
    @run_first()
    def page_logout_get(self, request):
        # print "logout"
        self.sessions.close_session(request)
        request.received_cookies[self.sessions.config.cookie_session] = 'LOGOFF'
        return self.home(request)

    @webapp.route('/login/user', methods=['GET'])
    @require_auth_pin()
    @run_first()
    def page_login_user_get(self, request):
        return self.redirect(request, '/')

    @webapp.route('/login/user', methods=['POST'])
    @require_auth_pin()
    @run_first()
    @inlineCallbacks
    def page_login_user_post(self, request):
        submitted_g_recaptcha_response = request.args.get('g-recaptcha-response')[0]
        submitted_email = request.args.get('email')[0]
        submitted_password = request.args.get('password')[0]
        # if submitted_pin.isalnum() is False:
        #     alerts = { '1234': self.make_alert('Invalid authentication.', 'warning')}
        #     return self.require_auth(request, alerts)

        if self._op_mode != 'firstrun':
            results = yield self._LocalDb.get_gateway_user_by_email(self.gwid, submitted_email)
            if len(results) != 1:
                self.add_alert('Email address not allowed to access gateway.', 'warning')
                #            self.sessions.load(request)
                page = self.get_template(request, self._dir + 'pages/login_user.html')
                returnValue(page.render(alerts=self.get_alerts(),
                                        )
                            )

        results = yield self.api.user_login_with_credentials(submitted_email, submitted_password, submitted_g_recaptcha_response)
        # print "results:::::::::::::::::  %s" % results
        if (results['code'] == 200):
            login = results['content']['response']['login']

#        if submitted_email == 'one' and submitted_password == '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b':
            session = self.sessions.load(request)
            if session is False:
                session = self.sessions.create(request)

            session['auth'] = True
            session['auth_id'] = submitted_email
            session['auth_time'] = time()
            session['yomboapi_session'] = login['session']
            session['yomboapi_login_key'] = login['login_key']
            request.received_cookies[self.sessions.config.cookie_session] = session.session_id

            if self._op_mode == 'firstrun':
                # print "###############33  saving system session stufff...."
                self.api.save_system_login_key(login['login_key'])
                # print "###############33  saving system session stufff....done"
                self.api.save_system_session(login['session'])
        else:

            self.add_alert(results['content']['message'], 'warning')
#            self.sessions.load(request)
            page = self.get_template(request, self._dir + 'pages/login_user.html')
            returnValue(page.render(alerts=self.get_alerts(),
                               )
                       )

        login_redirect = "/"
        if 'login_redirect' in session:
            login_redirect = session['login_redirect']
            # print "$$$$$$$$$$$$$$$$$$ login redirect is set..."
            session.delete('login_redirect')

        # print "111 login_rdirect: %s" % login_redirect

#        print "delete login redirect... %s" % self.sessions.delete(request, 'login_redirect')
#        print "login/user:login_redirect: %s" % login_redirect
#        print "after delete rediret...session: %s" % session
        returnValue(self.redirect(request, login_redirect))

    @webapp.route('/login/pin', methods=['POST'])
    @run_first()
    def page_login_pin_post(self, request):
        submitted_pin = request.args.get('authpin')[0]
        valid_pin = False
        # print "pin submit: %s" % submitted_pin
        if submitted_pin.isalnum() is False:
            # print "pin submit2: %s" % submitted_pin
            self.add_alert('Invalid authentication.', 'warning')
            return self.redirect(request, '/login/pin')

        # print "pin submit2: %s" % submitted_pin
        if self.auth_pin_type == 'pin':
            if submitted_pin == self.auth_pin:
                # print "pin post444"
                expires = 10 * 365 * 24 * 60 * 60  # 10 years from now.
                request.addCookie(self.sessions.config.cookie_pin, time(), domain=None, path='/',
                          secure=self.sessions.config.secure, httpOnly=self.sessions.config.httponly,
                          max_age=expires)
                request.received_cookies[self.sessions.config.cookie_pin] = '1'
                session = self.sessions.create(request)
                session['auth'] = False
                session['auth_id'] = ''
                session['auth_time'] = 0
                session['yomboapi_session'] = ''
                session['yomboapi_login_key'] = ''
                request.received_cookies[self.sessions.config.cookie_session] = session.session_id

               # print "session: %s" % session
            else:
                return self.redirect(request, '/login/pin')
        return self.home(request)

    @webapp.route('/login/pin', methods=['GET'])
    @require_auth()
    @run_first()
    def page_login_pin_get(self, request):
        return self.redirect(request, '/')

    def restart(self, request, message=None, redirect=None):
        if message is None:
            message = "Web interface requested restart."
        if redirect is None:
            redirect = "/"

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
        try:
            raise YomboCritical("Web Interface setup wizard complete.")
        except:
            pass

    @webapp.route('/static/', branch=True)
    @run_first()
    def static(self, request):
        request.setHeader('Cache-Control', 'max-age=%s' % randint(300, 420))
        return File(self._current_dir + "/lib/webinterface/static/dist")

    def display_pin_console(self):
        dns_fqdn = self._Configs.get('dns', 'fqdn', None, False)
        if dns_fqdn is None:
            local_hostname = "127.0.0.1"
            internal_hostname = self._Configs.get('core', 'localipaddress_v4')
            external_hostname = self._Configs.get('core', 'externalipaddress_v4')
        else:
            local_hostname = "local.%s" % dns_fqdn
            internal_hostname = "i.%s" % dns_fqdn
            external_hostname = "e.%s" % dns_fqdn

        local = "http://%s:%s" %(local_hostname, self.wi_port_nonsecure)
        internal = "http://%s:%s" %(internal_hostname, self.wi_port_nonsecure)
        external = "http://%s:%s" % (external_hostname, self.wi_port_nonsecure)
        print "###########################################################"
        print "#                                                         #"
        if self._op_mode != 'run':
            print "# The Yombo Gateway website is running in                 #"
            print "# configuration only mode.                                #"
            print "#                                                         #"
        print "# The website can be accessed from the following urls:    #"
        print "#                                                         #"
        print "# On local machine:                                       #"
        print "#  %-54s #" % local
        print "#                                                         #"
        print "# On local network:                                       #"
        print "#  %-54s #" % internal
        print "#                                                         #"
        print "# From external network (check port forwarding):          #"
        print "#  %-54s #" % external
        print "#                                                         #"
        print "#                                                         #"
        print "# Web Interface access pin code:                          #"
        print "#  %-25s                              #" % self.auth_pin
        print "#                                                         #"
        print "###########################################################"

    @inlineCallbacks
    def get_api(webinterface, request, method, path, data=None):
        results = yield webinterface._YomboAPI.request(method, path, data)
        if results['code'] != 200:
            request.setResponseCode(results['code'])
            error = {
                'message': results['content']['message'],
                'html_message': results['content']['html_message'],
            }
            raise YomboWarning(json.dumps(error))
        returnValue(results)

    def _tpl_home_gateway_configured(self):
        if not self._home_gateway_configured():
            return "This gateway is not properly configured. Click _here_ to run the configuration wizard."
        else:
            return ""

    def _home_gateway_configured(self):
        gwuuid = self._Configs.get("core", "gwuuid", None)
        gwhash = self._Configs.get("core", "gwhash", None)
        gpgkeyid = self._Configs.get('gpg', 'keyid', None)

        if gwuuid is None or gwhash is None or gpgkeyid is None:
            return False
        else:
            return True

    def _get_parms(self, request):
        return parse_qs(urlparse(request.uri).query)

    def epoch_to_human(self, the_time, format=None):
        if format is None:
            format = '%b %d %Y %H:%M:%S %Z'
        return strftime(format, localtime(the_time))

    def format_markdown(webinterface, description, description_formatting):
        if description_formatting == 'restructured':
            return publish_parts(description, writer_name='html')['html_body']
        elif description_formatting == 'markdown':
            return markdown.markdown(description, extensions=['markdown.extensions.nl2br', 'markdown.extensions.codehilite'])
        return description

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
        self.add_breadcrumb(request, "/", "Home")

    def add_breadcrumb(self, request, url, text, show = True):
        if hasattr(request, 'breadcrumb') is False:
            request.breadcrumb = []
            self.misc_wi_data['breadcrumb'] = request.breadcrumb
        request.breadcrumb.append({'url': url, 'text': text, 'show': show})


    def setup_basic_filters(self):
        self.webapp.templates.filters['yes_no'] = yombo.utils.is_yes_no
        self.webapp.templates.filters['make_link'] = self.make_link
        self.webapp.templates.filters['status_to_string'] = yombo.utils.status_to_string
        self.webapp.templates.filters['public_to_string'] = yombo.utils.public_to_string
        self.webapp.templates.filters['epoch_to_human'] = yombo.utils.epoch_to_string
        self.webapp.templates.filters['epoch_to_pretty_date'] = yombo.utils.pretty_date # yesterday, 5 minutes ago, etc.
        self.webapp.templates.filters['format_markdown'] = self.format_markdown

    def WebInterface_configuration_set(self, **kwargs):
        """
        Hook from configuration library. Get any configuration changes.

        :param kwargs: 'section', 'option', and 'value' are sent here.
        :return:
        """
        if kwargs['section'] == 'webinterface':
            option = kwargs['option']
            if option == 'auth_pin':
                self.auth_pin = kwargs['value']
            elif option == 'auth_pin_totp':
                self.auth_pin_totp = kwargs['value']
            elif option == 'auth_pin_type':
                self.auth_pin_type = kwargs['value']
            elif option == 'auth_pin_required':
                self.auth_pin_required = kwargs['value']

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
            # print "Saving to %s..." % output
            with open(output, 'w') as outfile:
                for fname in inputs:
                    fname = 'yombo/lib/webinterface/static/' + fname
                    # print "...%s" % fname
                    with open(fname) as infile:
                        outfile.write(infile.read())
            # print ""

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
            'source/jquery/jquery.validate-1.15.0.min.js',
        ]
        CAT_SCRIPTS_OUT = 'dist/js/jquery.validate-1.15.0.min.js'
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
            'source/echarts/echarts.min.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/echarts.min.js'

        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/sb-admin/js/sha256.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/sha256.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            'source/sb-admin/js/jquery.serializejson.min.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/jquery.serializejson.min.js'
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