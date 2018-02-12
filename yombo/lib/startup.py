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
# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

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

    def _init_(self, **kwargs):
        self.cache_updater_running = False
        self.system_stopping = False
        first_run = self._Configs.get('core', 'first_run', False, False)
        if self._Loader.operating_mode == 'first_run':  # will know if first_run already or yombo.ini is missing.
            return
        if first_run is True:
            self._Loader.operating_mode = 'first_run'
            return True
        items_needed = []

        gwid = self._Configs.get('core', 'gwid', 'local', False)
        if gwid is None or gwid == "":
            items_needed.append("Gateway ID")
        gwuuid = self._Configs.get("core", "gwuuid", None)
        if gwuuid is None or gwuuid == "":
            items_needed.append("Gateway private UUID")
        hash = self._Configs.get("core", "gwhash", None)
        if hash is None or hash == "":
            items_needed.append("Gateway login password hash")
        is_master = self._Configs.get("core", "is_master", True)
        if is_master is False:
            master_gateway = self._Configs.get("core", "master_gateway", None, False)
            if master_gateway is None or master_gateway == "":
                items_needed.append("Gateway is marked as slave, but not master gateway set.")
        else:
            master_gateway = self._Configs.get("core", "master_gateway", None, False)

        if len(items_needed) > 0:
            needed_text = '</li><li>'.join(items_needed)
            print("start needetext: %s" % needed_text)
            self._Notifications.add({'title': 'Need configurations',
                                     'message': 'System has been placed into configuration mode. Reason: The following configurations are needed:<p><ul><li>%s</li></ul>' % needed_text,
                                     'source': 'Yombo Startup Library',
                                     'persist': False,
                                     'priority': 'high',
                                     'always_show': True,
                                     'always_show_allow_clear': True,
                                     })
            self._Loader.operating_mode = 'config'
        else:
            self._Loader.operating_mode = 'run'

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
