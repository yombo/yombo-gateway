"""
Provides web interface for configuration of the Yombo system.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import shutil
from collections import OrderedDict
from os import path, listdir, mkdir
from os.path import dirname, abspath
from time import strftime, gmtime, time
from urlparse import parse_qs, urlparse

import jinja2
from klein import Klein

try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

# Import twisted libraries
from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, succeed

# Import 3rd party libraries

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.exceptions import YomboRestart
import yombo.utils

from yombo.lib.webinterface.sessions import Sessions
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


class WebInterface(YomboLibrary):
    """
    Web interface framework.
    """
    webapp = Klein()  # Like Flask, but for twisted


    visits = 0
    alerts = OrderedDict()

    def _init_(self, loader):
        self.loader = loader
        self.enabled = self._Configs.get('webinterface', 'enabled', True)
        if not self.enabled:
            return

        self._current_dir = dirname(dirname(dirname(abspath(__file__))))
        self._dir = '/lib/webinterface/'
        self._build_dist()

        self.data = {}
        self.sessions = Sessions(self.loader)

        self._port = self._Configs.get('webinterface', 'port', 8080)

        self.webapp.templates = jinja2.Environment(loader=jinja2.FileSystemLoader(self._current_dir))
        self.setup_basic_filters()

    @inlineCallbacks
    def _load_(self):
        yield self.sessions.init()

    def _start_(self):
        if not self.enabled:
            return
        self._op_mode = self._Atoms['loader_operation_mode']
        self.data['gateway_configured'] = self._home_gateway_configured()
        self.data['gateway_label'] = self._Configs.get('core', 'label', 'Yombo Gateway', False)
        self.data['operation_mode'] = self._op_mode

        self.auth_pin = self._Configs.get('webinterface', 'auth_pin', yombo.utils.random_string(length=6, letters=yombo.utils.human_alpabet()))
        self.auth_pin_totp = self._Configs.get('webinterface', 'auth_pin_totp', yombo.utils.random_string(length=16))
        self.auth_pin_type = self._Configs.get('webinterface', 'auth_pin_type', 'pin')
        self.auth_pin_required = self._Configs.get('webinterface', 'auth_pin_required', True)

        self.web_factory = Site(self.webapp.resource(), None, logPath='/dev/null')
#        self.web_factory.sessionFactory = YomboSession
        self.displayTracebacks = False

        self.web_interface_listener = reactor.listenTCP(self._port, self.web_factory)

    def _started_(self):
        if self._op_mode != 'run':
            self._display_pin_console_time = int(time())
            self.display_pin_console()

    def _unload_(self):
        pass

    def WebInterface_configuration_details(self, **kwargs):
        return [{'webinterface': {
                    'enabled': {
                        'description': {
                            'en': 'Enables/disables the web interface.',
                        }
                    },
                    'port': {
                        'description': {
                            'en': 'Port number for the web interface to listen on.'
                        }
                    }
                },
        }]

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

    def get_alerts(self, type='session'):
        """
        Retrieve a list of alerts for display.
        """
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
        return succeed(None)

    def require_auth(self, request, check_pin_only=False):
        session = self.sessions.load(request)

        if self.require_auth_pin:
            print "auth pin:::: %s" % session
            # had to break these up... - kept dieing on me
            has_pin = False
            if session is not None:
                if 'auth_pin' in session:
                    if session['auth_pin'] is True:
                        has_pin = True

            if has_pin is False:
                if self._display_pin_console_time < int(time())-30:
                    self._display_pin_console_time = int(time())
                    self.display_pin_console()
                if has_pin is False:
                    if self._display_pin_console_time < int(time())-30:
                        self._display_pin_console_time = int(time())
                        self.display_pin_console()
                page = self.get_template(request, self._dir + 'pages/login_pin.html')
                return page.render(alerts=self.get_alerts(),
                                   data=self.data,
                                   )
        if check_pin_only:
            return None

        if session is not None:
            if 'auth' in session:
                if session['auth'] is True:
                    print "ddd:33"
                    session['last_access'] = int(time())
                    try:
                        del session['login_redirect']
                    except:
                        pass
                    return None

        page = self.get_template(request, self._dir + 'pages/login_user.html')
        print "require_auth..session: %s" % session
        return page.render(alerts=self.get_alerts(),
                           data=self.data,
                           )

    def require_auth_pin(self, request, alerts={}):
        print "require_auth_pin"
        return self.require_auth(request, True)

    def check_op_mode(self, request, router, **kwargs):
        if self._op_mode == 'config':
            method = getattr(self, 'config_'+ router)
            return method(request, **kwargs)
        if self._op_mode == 'firstrun':
            method = getattr(self, 'firstrun_'+ router)
            return method(request, **kwargs)
        method = getattr(self, 'run_'+ router)
        return method(request, **kwargs)

    @webapp.route('/')
    def home(self, request):
        auth = self.require_auth(request)
        if auth is not None:
            return auth
        return self.check_op_mode(request, 'home')

    def run_home(self, request):
        print "home"
        self.check_op_mode(request, 'home')
        auth = self.require_auth(request)
        if auth is not None:
            return auth

        page = self.webapp.templates.get_template(self._dir + 'pages/index.html')
        return page.render(alerts=self.get_alerts(),
                           data=self.data,
                           devices=self._Libraries['devices']._devicesByUUID,
                           modules=self._Libraries['modules']._modulesByUUID,
                           states=self._Libraries['states'].get_states(),
                           )

    def config_home(self, request):
        print "aaaaaaaa"
        auth = self.require_auth(request)
        if auth is not None:
            return auth

        page = self.get_template(request, self._dir + 'config_pages/index.html')
        return page.render(alerts=self.get_alerts(),
                           data=self.data,
                           )

    def firstrun_home(self, request):
        print "bbbbbbbbbbbbbbbbbbbbbb"
        return self.redirect(request, '/setup_wizard/1')


    @webapp.route('/setup_wizard/1')
    def page_setup_wizard_1(self, request):
        if self.sessions.get(request, 'setup_wizard_done') is True:
            return self.redirect(request, '/setup_wizard/6')

        print "page_setup_wizard_1"
        self.sessions.set(request, 'login_redirect', '/setup_wizard/2')
        auth = self.require_auth_pin(request)
        if auth is not None:
            return auth


        self.sessions.set(request, 'setup_wizard_last_step', 3)
        page = self.get_template(request, self._dir + 'pages/setup_wizard/1.html')
        return page.render(alerts={},
                           data=self.data,
                           )

    @webapp.route('/setup_wizard/2')
    def page_setup_wizard_2(self, request):
        if self.sessions.get(request, 'setup_wizard_done') is True:
            return self.redirect(request, '/setup_wizard/6')
        if self.sessions.get(request, 'setup_wizard_last_step') not in (1, 2, 3):
            self.add_alert("Invalid wizard state. Please don't use the forward or back buttons.")
            return self.redirect(request, '/setup_wizard/1')

        auth = self.require_auth(request)  # Notice difference. Now we want to log the user in.
        if auth is not None:
            return auth

#        print "selected gateawy: %s" % self.sessions.get(request, 'setup_wizard_gateway_id')

        # simulate fetching possible gateways:
        available_gateways = simulate_gw #(include_new=True)

        self.sessions.set(request, 'setup_wizard_last_step', 2)
        page = self.get_template(request, self._dir + 'pages/setup_wizard/2.html')
        return page.render(alerts={},
                           data=self.data,
                           existing_gateways=available_gateways,
                           selected_gateway=self.sessions.get(request, 'setup_wizard_gateway_id'),
                           )

    @webapp.route('/setup_wizard/3', methods=['GET'])
    def page_setup_wizard_3_get(self, request):
        if self.sessions.get(request, 'setup_wizard_done') is True:
            return self.redirect(request, '/setup_wizard/6')
        if self.sessions.get(request, 'setup_wizard_last_step') not in (2, 3, 4):
            print "wiz step: %s" % self.sessions.get(request, 'setup_wizard_last_step')
            return self.redirect(request, '/setup_wizard/1')

        submitted_gateway_id = self.sessions.get(request, 'setup_wizard_gateway_id')
        if submitted_gateway_id == None:
            return self.redirect(request, "setup_wizard/2")

        auth = self.require_auth(request)  # Notice difference. Now we want to log the user in.
        if auth is not None:
            return auth

        # simulate fetching possible gateways:
        available_gateways = simulate_gw #(include_new=True)

        if submitted_gateway_id not in available_gateways:
            self.add_alert("Selected gateway not found. Try again.")
            self.redirect(request, 'setup_wizard/2')

        return self.page_setup_wizard_3_show_form(request, submitted_gateway_id, available_gateways)

    @webapp.route('/setup_wizard/3', methods=['POST'])
    def page_setup_wizard_3_post(self, request):
        if self.sessions.get(request, 'setup_wizard_done') is True:
            return self.redirect(request, '/setup_wizard/6')
        if self.sessions.get(request, 'setup_wizard_last_step') not in (2, 3, 4):
            self.add_alert("Invalid wizard state. Please don't use the forward or back buttons.")
            print "bad nav!!!"
            return self.redirect(request, '/setup_wizard/1')

        auth = self.require_auth(request)  # Notice difference. Now we want to log the user in.
        if auth is not None:
            return auth

        valid_submit = True
        try:
            submitted_gateway_id = request.args.get('gateway-id')[0]
        except:
            valid_submit = False

        if submitted_gateway_id == "" or valid_submit == False:
            self.add_alert("Invalid gateway selected. Try again.")
            return self.redirect(request, '/setup_wizard/2')

        # simulate fetching possible gateways:
        available_gateways = simulate_gw #(include_new=True)

        if submitted_gateway_id not in available_gateways:
            self.add_alert("Selected gateway not found. Try again.")
            return self.redirect(request, "setup_wizard/2")

        return self.page_setup_wizard_3_show_form(request, submitted_gateway_id, available_gateways)

    def page_setup_wizard_3_show_form(self, request, wizard_gateway_id, available_gateways):
        session = self.sessions.load(request)

        if 'setup_wizard_gateway_id' not in session or session['setup_wizard_gateway_id'] != wizard_gateway_id:
            available_gateways = simulate_gw #(include_new=True)
            session['setup_wizard_gateway_id'] = wizard_gateway_id
            session['setup_wizard_gateway_label'] = available_gateways[wizard_gateway_id]['label']
            session['setup_wizard_gateway_description'] = available_gateways[wizard_gateway_id]['description']
            session['setup_wizard_gateway_latitude'] = available_gateways[wizard_gateway_id]['variables']['latitude']
            session['setup_wizard_gateway_longitude'] = available_gateways[wizard_gateway_id]['variables']['longitude']
            session['setup_wizard_gateway_elevation'] = available_gateways[wizard_gateway_id]['variables']['elevation']

        print "session: %s" % session
        print "available_gateways[wizard_gateway_id]: %s" % available_gateways[wizard_gateway_id]
        fields = {
              'id' : session['setup_wizard_gateway_id'],
              'label': session['setup_wizard_gateway_label'],
              'description': session['setup_wizard_gateway_description'],
              'variables': {
                  'latitude': session['setup_wizard_gateway_latitude'],
                  'longitude': session['setup_wizard_gateway_longitude'],
                  'elevation': session['setup_wizard_gateway_elevation'],
                  },
        }

        session['setup_wizard_last_step'] = 3
        page = self.get_template(request, self._dir + 'pages/setup_wizard/3.html')
        return page.render(alerts=self.get_alerts(),
                           data=self.data,
                           gw_fields=fields,
                           )

    @webapp.route('/setup_wizard/4', methods=['GET'])
    def page_setup_wizard_4_get(self, request):
        if self.sessions.get(request, 'setup_wizard_done') is True:
            return self.redirect(request, '/setup_wizard/6')
        if self.sessions.get(request, 'setup_wizard_last_step') not in (3, 4, 5):
            self.add_alert("Invalid wizard state. Please don't use the forward or back buttons.")
            return self.redirect(request, '/setup_wizard/1')

        auth = self.require_auth(request)  # Notice difference. Now we want to log the user in.
        if auth is not None:
            return auth

        return self.page_setup_wizard_4_show_form(request)

    @webapp.route('/setup_wizard/4', methods=['POST'])
    def page_setup_wizard_4_post(self, request):
        if self.sessions.get(request, 'setup_wizard_done') is True:
            return self.redirect(request, '/setup_wizard/6')
        if self.sessions.get(request, 'setup_wizard_last_step') not in (3, 4, 5):
            self.add_alert("Invalid wizard state. Please don't use the forward or back buttons.")
            return self.redirect(request, '/setup_wizard/1')

        auth = self.require_auth(request)  # Notice difference. Now we want to log the user in.
        if auth is not None:
            return auth

        valid_submit = True
        try:
            submitted_gateway_label = request.args.get('gateway-label')[0]
        except:
            valid_submit = False
            self.add_alert("Invalid Gateway Label.")

        try:
            submitted_gateway_description = request.args.get('gateway-description')[0]
        except:
            valid_submit = False
            self.add_alert("Invalid Gateway Description.")

        try:
            submitted_gateway_latitude = request.args.get('gateway-latitude')[0]
        except:
            valid_submit = False
            self.add_alert("Invalid Gateway Latitude.")

        try:
            submitted_gateway_longitude = request.args.get('gateway-longitude')[0]
        except:
            valid_submit = False
            self.add_alert("Invalid Gateway Longitude.")

        try:
            submitted_gateway_elevation = request.args.get('gateway-elevation')[0]
        except:
            valid_submit = False
            self.add_alert("Invalid Gateway Elevation.")

        if valid_submit is False:
            page = self.get_template(request, self._dir + 'pages/setup_wizard/4.html')
            return page.render(alerts=self.get_alerts(),
                               data=self.data,
                               )
        session = self.sessions.load(request)

        session['setup_wizard_gateway_label'] = submitted_gateway_label
        session['setup_wizard_gateway_description'] = submitted_gateway_description
        session['setup_wizard_gateway_latitude'] = submitted_gateway_latitude
        session['setup_wizard_gateway_longitude'] = submitted_gateway_longitude
        session['setup_wizard_gateway_elevation'] = submitted_gateway_elevation

        return self.page_setup_wizard_4_show_form(request)

    def page_setup_wizard_4_show_form(self, request):
        session = self.sessions.load(request)
        security_items = {
            'status': session.get('setup_wizard_security_status', '1'),
            'gps_status': session.get('setup_wizard_security_gps_status', '1'),
        }

        session['setup_wizard_last_step'] = 4
        page = self.get_template(request, self._dir + 'pages/setup_wizard/4.html')
        return page.render(alerts=self.get_alerts(),
                           data=self.data,
                           security_items=security_items,
                           )

    @webapp.route('/setup_wizard/5', methods=['GET'])
    def page_setup_wizard_5_get(self, request):
        if self.sessions.get(request, 'setup_wizard_done') is True:
            return self.redirect(request, '/setup_wizard/6')
        if self.sessions.get(request, 'setup_wizard_last_step') not in (4, 5, 6):
            self.add_alert("Invalid wizard state. Please don't use the forward or back buttons.")
            return self.redirect(request, '/setup_wizard/1')

        auth = self.require_auth(request)  # Notice difference. Now we want to log the user in.
        if auth is not None:
            return auth

        return self.page_setup_wizard_5_show_form(request)

    @webapp.route('/setup_wizard/5', methods=['POST'])
    def page_setup_wizard_5_post(self, request):
        if self.sessions.get(request, 'setup_wizard_done') is True:
            return self.redirect(request, '/setup_wizard/6')
        if self.sessions.get(request, 'setup_wizard_last_step') not in (4, 5, 6):
            self.add_alert("Invalid wizard state. Please don't use the forward or back buttons.")
            return self.redirect(request, '/setup_wizard/1')

        auth = self.require_auth(request)  # Notice difference. Now we want to log the user in.
        if auth is not None:
            return auth

        valid_submit = True
        try:
            submitted_security_status = request.args.get('security-status')[0]
        except:
            valid_submit = False
            self.add_alert("Invalid Gateway Device Send Status.")


        try:
            submitted_security_gps_status = request.args.get('security-gps-status')[0]
        except:
            valid_submit = False
            self.add_alert("Invalid Gateway GPS Locations Send Status.")

        if valid_submit is False:
            return self.redirect(request, '/setup_wizard/4')

        session = self.sessions.load(request)

        session['setup_wizard_security_status'] = submitted_security_status
        session['setup_wizard_security_gps_status'] = submitted_security_gps_status

        return self.page_setup_wizard_5_show_form(request)

    def page_setup_wizard_5_show_form(self, request):
        gpg_selected = "new"

        self.sessions.set(request, 'setup_wizard_last_step', 5)
        page = self.get_template(request, self._dir + 'pages/setup_wizard/5.html')
        return page.render(alerts={},
                           data=self.data,
                           gpg_selected=gpg_selected
                           )

    @webapp.route('/setup_wizard/5_gpg_section')
    def page_setup_wizard_5_gpg_section(self, request):
        auth = self.require_auth(request)  # Notice difference. Now we want to log the user in.
        if auth is not None:
            return "Not authorizaed"

        if self.sessions.get(request, 'setup_wizard_last_step') != 5:
            return "Invalid wizard state. No content found."

        available_keys = {} # simulate getting available keys from GPG library.

        valid_submit = True
        try:
            submitted_gpg_action = request.args.get('gpg_action')[0]
        except:
            valid_submit = False
            self.add_alert("Invalid Gateway Label.")

        if valid_submit is False:
            return "invalid submit"

        if submitted_gpg_action == "new":
            page = self.get_template(request, self._dir + 'pages/setup_wizard/5_gpg_new.html')
            return page.render(alerts=self.get_alerts(),
                               data=self.data,
                               )
        elif submitted_gpg_action == "import":
            page = self.get_template(request, self._dir + 'pages/setup_wizard/5_gpg_import.html')
            return page.render(alerts=self.get_alerts(),
                               data=self.data,
                               )
        elif submitted_gpg_action in available_keys:
            page = self.get_template(request, self._dir + 'pages/setup_wizard/5_gpg_existing.html')
            return page.render(alerts=self.get_alerts(),
                               data=self.data,
                               )
        else:
            return "Invalid GPG selection."

    @webapp.route('/setup_wizard/6', methods=['GET'])
    def page_setup_wizard_6_get(self, request):
        auth = self.require_auth(request)  # Notice difference. Now we want to log the user in.
        if auth is not None:
            return auth

        if self.sessions.get(request, 'setup_wizard_done') is not True:
            self.redirect(request, '/setup_wizard/5')

        page = self.get_template(request, self._dir + 'pages/setup_wizard/6.html')
        return page.render(alerts={},
                           data=self.data,
                           )

    @webapp.route('/setup_wizard/6', methods=['POST'])
    def page_setup_wizard_6_post(self, request):
        print "111"
        if self.sessions.get(request, 'setup_wizard_done') is True:
            print "aaa"
            return self.redirect(request, '/setup_wizard/6')
        auth = self.require_auth(request)  # Notice difference. Now we want to log the user in.
        if auth is not None:
            return auth

        valid_submit = True
        try:
            submitted_gpg_actions = request.args.get('gpg_action')[0]  # underscore here due to jquery
        except:
            valid_submit = False
            self.add_alert("Please select an appropriate GPG/PGP Key action.")

        if submitted_gpg_actions == 'import':  # make GPG keys!
            try:
                submitted_gpg_private = request.args.get('gpg-private-key')[0]
            except:
                valid_submit = False
                self.add_alert("When importing, must have a valid private GPG/PGP key.")

            try:
                submitted_gpg_public = request.args.get('gpg-public-key')[0]
            except:
                valid_submit = False
                self.add_alert("When importing, must have a valid public GPG/PGP key.")

        if valid_submit is False:
            return self.redirect('/setup_wizard/5')


        if submitted_gpg_actions == 'new':  # make GPG keys!
#            gpg-make-new key here...
            pass
        elif submitted_gpg_actions == 'import':  # make GPG keys!
#            gpg-import-new-key-here...
            pass
        elif submitted_gpg_actions == 'existing':  # make GPG keys!
#            gpg-import-new-key-here...
            pass

        gpg_info = {  # will be returned from the GPG import/create/select existing funciton
            'keyid': '63EE4EA472E49634',
            'keypublicascii': """-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.12 (GNU/Linux)
mI0ETyeLqwEEANsXSCvR9H5eSqRDusnqZpaxIj9uKanS+/R8yj23Yo2fl0r1BCwv
EnYF8h2tnowFQb59fuv821ZH7LoT4HZeDpNL8WGjaBSYpnxfGK3GBahM65a2WISb
nA+lkCuh7C6MA1zrNuKp5splsi/fg7hm7kaax5H2NJAUSuT3xsmLpZUTABEBAAG0
P0dlbmVyYXRlZCBieSBBSFggKGdwZ19nZW5lcmF0ZWtleXMucHkpIDxTRldFenA0
M1l6TEpmUERAYWh4Lm1lPoi4BBMBAgAiBQJPJ4urAhsvBgsJCAcDAgYVCAIJCgsE
FgIDAQIeAQIXgAAKCRBj7k6kcuSWNOs8A/4qTI+gw4SLwarGEVt0APFhKHQncXim
XRIV0dpHp6fX4JBN2yGFfAFP9dl+/xBJnOklRlnEvIb7D0cjwtRHSbNntKQb3pWT
v2WF64dX9flI/lICvwfTsaE7FPaFHiG6flXfizYYyQttNB9RFF6AZqV0t6+1/FHC
46JXipvbzmtNJQ==
=NXHA
-----END PGP PUBLIC KEY BLOCK-----""",
        }
#        if gpg_ok is False:
#            return self.redirect('/setup_wizard/5')

        # Call Yombo API to save Gateway. Will get back all the goodies we need!
        # Everything is done! Lets save all the configs!

        session = self.sessions.load(request)

        api_results = {
            'gwuuid': 'L2rwJHeKuRSUQoxQFOQP7RnB',  # A dummy test gateway UUID...just for testing...
            'label': session['setup_wizard_gateway_label'],
            'gwhash': 'tP.dLfPaCzmU5H84pDhrk3HDo4FQMEDeb7B',
        }

        self._Configs.set('core', 'gwuuid', api_results['gwuuid'])
        self._Configs.set('core', 'label', session['setup_wizard_gateway_label'])
        self._Configs.set('core', 'description', session['setup_wizard_gateway_description'])
        self._Configs.set('core', 'gwhash', api_results['gwhash'])
        self._Configs.set('gpg', 'keyid', gpg_info['keyid'])
        self._Configs.set('gpg', 'keypublicascii', gpg_info['keypublicascii'])
        self._Configs.set('security', 'amqpsendstatus', session['setup_wizard_security_status'])
        self._Configs.set('security', 'amqpsendgpsstatus', session['setup_wizard_security_gps_status'])
        self._Configs.set('location', 'latitude', session['setup_wizard_gateway_latitude'])
        self._Configs.set('location', 'longitude', session['setup_wizard_gateway_longitude'])
        self._Configs.set('location', 'elevation', session['setup_wizard_gateway_elevation'])
        self._Configs.set('core', 'firstrun', False)

        # Remove wizard settings...
        for k in session.keys():
            if k.startswith('setup_wizard_'):
                session.pop(k)
        session['setup_wizard_done'] = True
        session['setup_wizard_last_step'] = 6

        page = self.get_template(request, self._dir + 'pages/setup_wizard/6.html')
        return page.render(alerts={},
                           data=self.data,
                           )


    @webapp.route('/setup_wizard/6_restart', methods=['GET'])
    def page_setup_wizard_6_restart(self, request):
#        auth = self.require_auth(request)  # Notice difference. Now we want to log the user in.
#        if auth is not None:
#            return auth

#        if self.sessions.get(request, 'setup_wizard_done') is not True:
#            return self.redirect(request, '/setup_wizard/5')

        raise YomboRestart("Web Interface setup wizard complete.")

    @webapp.route('/logout', methods=['GET'])
    def page_logout_get(self, request):
        print "logout"
        self.sessions.close_session(request)
        request.received_cookies[self.sessions.config.cookie_name] = 'LOGOFF'
        return self.home(request)

    @webapp.route('/login/user', methods=['GET'])
    def page_login_user_get(self, request):
        auth = self.require_auth(request)
        if auth is not None:
            return auth

        print request.args.get('email')
        return self.redirect(request, '/')

    @webapp.route('/login/user', methods=['POST'])
    def page_login__user_post(self, request):
        auth = self.require_auth_pin(request)
        if auth is not None:
            return auth
        submitted_email = request.args.get('email')[0]
        submitted_password = request.args.get('password')[0]
        print "111"
        # if submitted_pin.isalnum() is False:
        #     alerts = { '1234': self.make_alert('Invalid authentication.', 'warning')}
        #     return self.require_auth(request, alerts)

        if submitted_email == 'one' and submitted_password == '6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b':
            session = self.sessions.load(request)
            session['auth'] = True
            session['auth_id'] = submitted_email
            session['auth_time'] = submitted_email
            request.received_cookies[self.sessions.config.cookie_name] = session['session_id']
            print "session: %s" % session
        else:
            self.sessions.load(request)
            page = self.get_template(request, self._dir + 'pages/login_user.html')
            return page.render(alerts={},
                               data=self.data,
                               )

        login_redirect = "/"
        if 'login_redirect' in session:
            login_redirect = session['login_redirect']
        print "delete login redirect... %s" % self.sessions.delete(request, 'login_redirect')
        print "login/user:login_redirect: %s" % login_redirect
        print "after delete session: %s" % session
        return self.redirect(request, login_redirect)

    @webapp.route('/login/pin', methods=['POST'])
    def page_login_pin_post(self, request):
        submitted_pin = request.args.get('authpin')[0]
        valid_pin = False
        if submitted_pin.isalnum() is False:
            self.add_alert('Invalid authentication.', 'warning')
            return self.require_auth(request)

        if self.auth_pin_type == 'pin':
            if submitted_pin == self.auth_pin:
                print "pin post444"
                session = self.sessions.create(request)
                session['auth_pin'] = True
                session['auth_pin_time'] = int(time())
                request.received_cookies[self.sessions.config.cookie_name] = session['session_id']
#                print "session: %s" % session
            else:
                return self.redirect(request, '/login/pin')
        return self.home(request)

    @webapp.route('/login/pin', methods=['GET'])
    def page_login_pin_get(self, request):
        auth = self.require_auth(request)
        if auth is not None:
            return auth
        return self.redirect(request, '/')

        # if self.has_auth_pin(request):
        #     request.redirect('/')
        #     return succeed(None)
        #
        # page = self.webapp.templates.get_template(self._dir + 'pages/login_pin.html')
        # return page.render(alerts={},
        #                    data=self.data,
        #                    )

    @webapp.route('/atoms')
    def page_atoms(self, request):
        page = self.get_template(request, self._dir + 'pages/atoms/index.html')
        return page.render(alerts=self.get_alerts(),
                           data=self.data,
                           atoms=self._Libraries['atoms'].get_atoms(),
                           )

    @webapp.route('/devices')
    def page_devices(self, request):
        page = self.get_template(request, self._dir + 'pages/devices/index.html')
        return page.render(alerts=self.get_alerts(),
                           data=self.data, devices=self._Libraries['devices']._devicesByUUID,
                           )

    @webapp.route('/commands')
    def page_commands(self, request):
        page = self.get_template(request, self._dir + 'pages/commands/index.html')
        return page.render(alerts=self.get_alerts(),
                           data=self.data,
                           )

    @webapp.route('/commands/amqp')
    def page_commands_amqp(self, request):
        params = self._get_parms(request)
        print "111"
        if 'command' in params:
            print "222"
            print params['command'][0]
            if params['command'][0] == 'connect':
                self.loader._Libraries['AMQPYombo'].connect()
            if params['command'][0] == 'disconnect':
                print "33a"
#                self.loader._Libraries['AMQPYombo'].disconnect()
        page = self.get_template(request, self._dir + 'commands/index.html')
        return page.render()



    @webapp.route('/configs')
    def page_configs(self, request):
        page = self.get_template(request, self._dir + 'pages/configs/index.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           configs=self._Libraries['configuration'].configs
                           )

    @webapp.route('/configs/basic')
    def page_configs_basic(self, request):
        config = {"core": {}, "webinterface": {}, "times": {}}
        config['core']['label'] = self._Configs.get('core', 'label', '', False)
        config['core']['description'] = self._Configs.get('core', 'description', '', False)
        config['times']['twilighthorizon'] = self._Configs.get('times', 'twilighthorizon')
        config['webinterface']['enabled'] = self._Configs.get('webinterface', 'enabled')
        config['webinterface']['port'] = self._Configs.get('webinterface', 'port')

        page = self.get_template(request, self._dir + 'pages/configs/basic.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           config=config,
                           )

    @webapp.route('/configs/yombo_ini')
    def page_configs_yombo_ini(self, request):
        page = self.get_template(request, self._dir + 'pages/configs/yombo_ini.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           configs=self._Libraries['configuration'].configs
                           )

    @webapp.route('/modules')
    def page_modules(self, request):
        page = self.get_template(request, self._dir + 'pages/modules/index.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           modules=self._Libraries['modules']._modulesByUUID,
                           )

    @webapp.route('/states')
    def page_states(self, request):
        page = self.get_template(request, self._dir + 'pages/states/index.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           states=self._Libraries['states'].get_states(),
                           )


    @webapp.route('/gpg_keys')
    def page_gpg_keys(self, request):
        page = self.get_template(request, 'gpg_keys/index.html')
        return page.render()

    @webapp.route('/gpg_keys/generate_key')
    def page_gpg_keys_generate_key(self, request):
        request_id = yombo.utils.random_string(length=16)
#        self._Libraries['gpg'].generate_key(request_id)
        page = self.get_template(request, 'gpg_keys/generate_key_started.html')
        return page.render(request_id=request_id, getattr=getattr, type=type)

    @webapp.route('/gpg_keys/genrate_key_status')
    def page_gpg_keys_generate_key_status(self, request):
        page = self.get_template(request, 'gpg_keys/generate_key_status.html')
        return page.render(atoms=self._Libraries['atoms'].get_atoms(), getattr=getattr, type=type)

    @webapp.route('/status')
    def page_status(self, request):

        gwuuid = self._Configs.get("core", "gwuuid", None)
        gwhash = self._Configs.get("core", "gwhash", None)
        gpgkeyid = self._Configs.get('core', 'gpgkeyid', None)

        has = {}

        has['gateway_uuid'] = 'True' if gwuuid is not None else 'False'
        has['gateway_hash'] = 'True' if gwhash is not None else 'False'
        has['gpg_keyid'] = 'True' if gpgkeyid is not None else 'False'
        page = self.get_template(request, 'status/index.html')
        return page.render(data=self.data,
                           yombo_server_is_connected=self._States.get('yombo_server_is_connected'),
                           )

    @webapp.route('/api/v1/notifications', methods=['GET'])
    def ajax_alert_get(self, request):
        action = request.args.get('action')[0]
        results = {}
        if action == "closed":
            id = request.args.get('id')[0]
            print "alert - id: %s" % id
            if id in self.alerts:
                del self.alerts[id]
                results = {"status":200}
        return json.dumps(results)



    @webapp.route('/static/', branch=True)
    def static(self, request):
        return File(self._current_dir + "/lib/webinterface/static/dist")

    @webapp.route('/setup_wizard/static/', branch=True)
    def setup_wizard_static(self, request):
        return File(self._current_dir + "/lib/webinterface/pages/setup_wizard/static")

    def display_pin_console(self):
        local = "http://localhost:%s" % self._port
        internal = "http://%s:%s" %(self._Configs.get('core', 'localipaddress'), self._port)
        external = "http://%s:%s" % (self._Configs.get('core', 'externalipaddress'), self._port)
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

    def _tpl_home_gateway_configured(self):
        if not self._home_gateway_configured():
            return "This gateway is not properly configured. Click _here_ to run the configuration wizard."
        else:
            return ""

    def _home_gateway_configured(self):
        gwuuid = self._Configs.get("core", "gwuuid", None)
        gwhash = self._Configs.get("core", "gwhash", None)
        gpgkeyid = self._Configs.get('core', 'gpgkeyid', None)

        if gwuuid is None or gwhash is None or gpgkeyid is None:
            return False
        else:
            return True

    def _get_parms(self, request):
        return parse_qs(urlparse(request.uri).query)

    def setup_basic_filters(self):
        def epoch_to_human(the_time):
            return strftime("%b %d %Y %H:%M:%S", gmtime(the_time))
        self.webapp.templates.filters['epoch_to_human'] = epoch_to_human

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
            return
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
            'source/bootstrap/dist/css/bootstrap.min.css',
            'source/metisMenu/metisMenu.min.css',
        ]
        CAT_SCRIPTS_OUT = 'dist/css/bootsrap-metisMenu.min.css'
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
            'source/font-awesome/css/font-awesome.min.css',
            ]
        CAT_SCRIPTS_OUT = 'dist/css/admin2-font_awesome.min.css'
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
            'source/chartist/chartist.min.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/chartist.min.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)
        CAT_SCRIPTS = [
            'source/chartist/chartist.min.css',
            ]
        CAT_SCRIPTS_OUT = 'dist/css/chartist.min.css'
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
            'source/sb-admin/js/sha256.js',
            ]
        CAT_SCRIPTS_OUT = 'dist/js/sha256.js'
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        # Just copy files
        copytree('source/font-awesome/fonts/', 'dist/fonts/')
        copytree('source/bootstrap/dist/fonts/', 'dist/fonts/')
