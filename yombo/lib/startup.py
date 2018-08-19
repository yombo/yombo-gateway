# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Checks for basic requirements.  If anything is wrong/missing, displays an error and put the system into configuration
mode.

.. warning::

  Module developers and users should not access any of these functions
  or variables.  This is listed here for completeness.


.. note::

  For more information see: `Startup @ Module Development <https://yombo.net/docs/libraries/startup>`_


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/startup.html>`_
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboRestart
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

from yombo.utils import sleep

logger = get_logger('library.startup')

class Startup(YomboLibrary):
    """
    Start-up checks

    Checks to make sure basic configurations are valid and other start-up operations.
    """
    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo startup library"

    @inlineCallbacks
    def _init_(self, **kwargs):
        self.gwid = self._Configs.get2('core', 'gwid', 'local', False)
        self.gwuuid = self._Configs.get2("core", "gwuuid", None, False)
        self.gwhash = self._Configs.get2("core", "gwhash", None, False)
        self.api_auth = self._Configs.get2("core", "api_auth", None, False)
        self.has_valid_gw_auth = False

        self.cache_updater_running = False
        self.system_stopping = False
        if self._Loader.operating_mode == 'first_run':  # will know if first_run already or yombo.ini is missing.
            return
        first_run = self._Configs.get('core', 'first_run', False, False)
        if first_run is True:
            self._Loader.operating_mode = 'first_run'
            return True

        operating_mode, items_needed = yield self.check_has_valid_gw_auth()

        is_master = self._Configs.get("core", "is_master", True)
        if is_master is False:
            master_gateway_id = self._Configs.get("core", "master_gateway_id", None, False)
            if master_gateway_id is None or master_gateway_id == "":
                items_needed.append("Gateway is marked as slave, but no master gateway set.")

        if len(items_needed) > 0:
            needed_text = '</li><li>'.join(items_needed)
            self._Notifications.add({'title': 'Need configurations',
                                     'message': 'System has been placed into configuration mode. The following configurations are needed:<p><ul><li>%s</li></ul>' % needed_text,
                                     'source': 'Yombo Startup Library',
                                     'persist': False,
                                     'priority': 'high',
                                     'always_show': True,
                                     'always_show_allow_clear': True,
                                     })
            self._Loader.operating_mode = 'config'
        else:
            self._Loader.operating_mode = operating_mode
        yield self._GPG._init_from_startup_()

    @inlineCallbacks
    def check_has_valid_gw_auth(self, session=None):
        @inlineCallbacks
        def try_get_api_auth_keys(try_session):
            try:
                yield self._YomboAPI.get_api_auth_keys(session=try_session)
            except YomboRestart:
                logger.error("System going down for restart, have new auth credentials")
                yield sleep(120)
                return operating_mode, items_needed
            except YomboWarning:
                pass

        operating_mode = 'run'
        items_needed = []
        gwid = self.gwid()
        if gwid is None or gwid == "":
            items_needed.append("Gateway ID is missing. Please complete the setup wizard again.")
            operating_mode = 'first_run'
            return operating_mode, items_needed
        gwuuid = self.gwuuid()
        if gwuuid is None or gwuuid == "":
            operating_mode = 'config'
            items_needed.append("Gateway UUID is missing.")
        gwhash = self.gwhash()
        if gwhash is None or gwhash == "":
            operating_mode = 'config'
            items_needed.append("Gateway password is missing.")

        is_valid_system = yield self._YomboAPI.check_api_auth_valid()
        if is_valid_system is False:
            # System doesn't have valid auth info. Lets search through the session database and try to
            # find a user that will has access to refresh our auth information.

            try:
                sessions = yield self._LocalDB.get_web_session()
                if session is not None and isinstance(session, str):
                    yield try_get_api_auth_keys(session)
            except YomboWarning:
                pass
            else:
                for session in sessions:
                    data = session['session_data']
                    if 'yomboapi_session' in data and isinstance(data['yomboapi_session'], str):
                        yield try_get_api_auth_keys(data['yomboapi_session'])

            # If we here, then no valid session was found. Put system into config mode. It will be attempted
            # when the user access its. We will also display a notice.
            operating_mode = 'config'
            items_needed.append('System is unable to authenticate itself with the server. The owner simply needs to'
                                ' log into the system. This will activate the reauthorization.')
        return operating_mode, items_needed

    def _start_(self, **kwargs):
        """
        Handles making sure caches are regularly updated and cleaned.
        :return:
        """
        self.update_caches_loop = LoopingCall(self.update_caches)
        self.update_caches_loop.start(60*60*6, False)

    def _stop_(self, **kwargs):
        self.system_stopping = True

    @inlineCallbacks
    def update_caches(self, force=None, quick=False):
        """
        Iterates through all libraries to update the cache, then tells the modules to do the same.
        :return:
        """
        if self.cache_updater_running is True and force is True:
            self.cache_updater_running == None
            return

        if self._Loader.operating_mode != 'run' or self.cache_updater_running is not False or \
                self.system_stopping is True:
            return

        logger.info("Starting cache updates.")

        # Copied from Modules library, but with sleeps and checks.
        for module_id, module in self._Modules.modules.items():
            if self.cache_updater_running is None or self.system_stopping is True:
                self.cache_updater_running = False
                self.update_caches_loop.reset()
                return

            yield self._Modules.do_update_module_cache(module)
            yield sleep(1)

        for device_id, device in self._Devices.devices.items():
            if self.cache_updater_running is None or self.system_stopping is True:
                self.cache_updater_running = False
                self.update_caches_loop.reset()
                return

            yield device.device_variables()
            yield sleep(0.5)
