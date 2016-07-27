"""
Provides web interface for configuration of the Yombo system.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from os import path, listdir, mkdir
import shutil

from zope.interface import Interface, Attribute, implements
import jinja2
from klein import Klein
from os.path import dirname, abspath
from time import strftime, gmtime
from urlparse import parse_qs, urlparse
from collections import OrderedDict

from twisted.web.server import Site
from twisted.web.static import File

from twisted.internet import threads, reactor
from twisted.internet.defer import inlineCallbacks, returnValue, succeed
from twisted.python.components import registerAdapter
from twisted.web.server import Session
from twisted.web.resource import Resource


# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboHookStopProcessing
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.utils

logger = get_logger("library.webconfig")

class IAuth(Interface):
    value = Attribute("A bool which stores authentication state.")

class AuthState(object):
    implements(IAuth)
    def __init__(self, session):
        self.value = False

registerAdapter(AuthState, Session, IAuth)

class WebInterface(YomboLibrary):
    """
    Web interface framework.
    """
    webapp = Klein()  # Like Flask, but for twisted
    visits = 0

    def _init_(self, loader):

        self.enabled = self._Configs.get('webinterface', 'enabled', 1)
        self._port = self._Configs.get('webinterface', 'port', 8080)

        self.loader = loader
        self._current_dir = dirname(abspath(__file__))
        self.webapp.templates = jinja2.Environment(loader=jinja2.FileSystemLoader(dirname(self._current_dir)))
        self._dir = '/lib/webinterface/'
        self.setup_basic_filters()

        self.alerts = OrderedDict()
        self.data = {}

        self.data['gateway_configured'] = self._home_gateway_configured()
        self.data['gateway_label'] = self._Configs.get("core", 'label', 'Yombo Gateway')

        self.auth_pin = yombo.utils.random_string(length=6)

        if not self.data['gateway_configured']:
            self.alerts[yombo.utils.random_string(length=10)] = {
                'level': 'info',
                'message': 'gateway not properly configed',
                'dismissable': False,
                'removeable': False,
            }

        self._build_dist()
        # self.alerts[yombo.utils.random_string(length=10)] = {
        #     'level': 'warning',
        #     'message': 'warn',
        # }

    def _load_(self):
        self.httpListener = reactor.listenTCP(self._port, Site(self.webapp.resource(), None, logPath='/dev/null'))

    def _start_(self):
        pass

    def _stop_(self):
        pass

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


    def setup_basic_filters(self):
        def epoch_to_human(the_time):
            return strftime("%b %d %Y %H:%M:%S", gmtime(the_time))
        self.webapp.templates.filters['epoch_to_human'] = epoch_to_human

    def require_auth(self, request):
        session = request.getSession()
        auth_state = IAuth(session)
#        if auth_state.value is False:
#        print 'Your session id is: ' + session.id
        print 'Your auth state is: %s ' % auth_state.value
        page = self.webapp.templates.get_template(self._dir + 'pages/login.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           )

    def require_auth_pin(self, request):
        print request.getAllHeaders()
        print 'Your session id is: ' + request.getSession().uid


    @webapp.route('/')
    def home(self, request):
        if self.loader.operation_mode == 'config':
            return self.config_home(request)

        # auth = self.require_auth(request)
        # if len(auth) is not True:
        #     return auth

        page = self.webapp.templates.get_template(self._dir + 'pages/index.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           devices=self._Libraries['devices']._devicesByUUID,
                           modules=self._Libraries['modules']._modulesByUUID,
                           states=self._Libraries['states'].get_states(),
                           )

    def config_home(self, request):
        auth = self.require_auth(request)
        if len(auth) is not True:
            return auth

        logger.error("Auth pin required: {auth_pin}", auth_pin=self.auth_pin)
        page = self.webapp.templates.get_template(self._dir + 'config_pages/index.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           )

    @webapp.route('/login', methods=['GET', 'POST'])
    def page_login_post(self, request):
        print request.args.get('email')
        request.redirect('/')
        return succeed(None)



    @webapp.route('/atoms')
    def page_atoms(self, request):
        page = self.webapp.templates.get_template(self._dir + 'pages/atoms/index.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           atoms=self._Libraries['atoms'].get_atoms(),
                           )

    @webapp.route('/devices')
    def page_devices(self, request):
        page = self.webapp.templates.get_template(self._dir + 'pages/devices/index.html')
        return page.render(alerts=self.alerts,
                           data=self.data, devices=self._Libraries['devices']._devicesByUUID,
                           )

    @webapp.route('/commands')
    def page_commands(self, request):
        page = self.webapp.templates.get_template(self._dir + 'pages/commands/index.html')
        return page.render(alerts=self.alerts,
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
        page = self.webapp.templates.get_template(self._dir + 'commands/index.html')
        return page.render()



    @webapp.route('/configs')
    def page_configs(self, request):
        page = self.webapp.templates.get_template(self._dir + 'pages/configs/index.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           configs=self._Libraries['configuration'].configs
                           )

    @webapp.route('/configs/basic')
    def page_configs_basic(self, request):
        config = {"core": {}, "webinterface": {}, "times": {}}
        config['core']['label'] = self._Configs.get("core", 'label', 'Yombo Gateway')
        config['core']['description'] = self._Configs.get("core", 'description', "")
        config['core']['description'] = self._Configs.get("core", 'description', "")
        config['times']['twilighthorizon'] = self._Configs.get("times", 'twilighthorizon')
        config['webinterface']['enabled'] = self._Configs.get("webinterface", "enabld")
        config['webinterface']['port'] = self._Configs.get("webinterface", "port")

        page = self.webapp.templates.get_template(self._dir + 'pages/configs/basic.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           config=config,
                           )

    @webapp.route('/configs/yombo_ini')
    def page_configs_yombo_ini(self, request):
        page = self.webapp.templates.get_template(self._dir + 'pages/configs/yombo_ini.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           configs=self._Libraries['configuration'].configs
                           )

    @webapp.route('/modules')
    def page_modules(self, request):
        page = self.webapp.templates.get_template(self._dir + 'pages/modules/index.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           modules=self._Libraries['modules']._modulesByUUID,
                           )

    @webapp.route('/states')
    def page_states(self, request):
        page = self.webapp.templates.get_template(self._dir + 'pages/states/index.html')
        return page.render(alerts=self.alerts,
                           data=self.data,
                           states=self._Libraries['states'].get_states(),
                           )


    @webapp.route('/gpg_keys')
    def page_gpg_keys(self, request):
        page = self.webapp.templates.get_template('gpg_keys/index.html')
        return page.render()

    @webapp.route('/gpg_keys/generate_key')
    def page_gpg_keys_generate_key(self, request):
        request_id = yombo.utils.random_string(length=16)
#        self._Libraries['gpg'].generate_key(request_id)
        page = self.webapp.templates.get_template('gpg_keys/generate_key_started.html')
        return page.render(request_id=request_id, getattr=getattr, type=type)

    @webapp.route('/gpg_keys/genrate_key_status')
    def page_gpg_keys_generate_key_status(self, request):
        page = self.webapp.templates.get_template('gpg_keys/generate_key_status.html')
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
        page = self.webapp.templates.get_template('status/index.html')
        return page.render(has=has,
                           operation_mode=self.loader.operation_mode,
                           yombo_server_is_connected=self._States.get('yombo_server_is_connected'),
                           )



    @webapp.route('/static/', branch=True)
    def static(self, request):
        return File(self._current_dir + "/webinterface/static/dist")

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

#if has basic configuration (gwuuid, hash, )
#yomboapi - stores master account credentails. Will prompt if needed with a warning




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
#            print "Saving to %s..." % output
            with open(output, 'w') as outfile:
                for fname in inputs:
                    fname = 'yombo/lib/webinterface/static/' + fname
#                    print "...%s" % fname
                    with open(fname) as infile:
                        outfile.write(infile.read())
            print ""

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

        # Just copy files
        copytree('source/font-awesome/fonts/', 'dist/fonts/')
        copytree('source/bootstrap/dist/fonts/', 'dist/fonts/')
