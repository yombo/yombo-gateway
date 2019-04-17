# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Checks for basic requirements.  If anything is wrong/missing, displays an error and put the system into configuration
mode.

.. warning::

  Module developers and users should not access any of these functions
  or variables.  This is listed here for completeness.


.. note::

  * For library documentation, see: `Startup @ Library Documentation <https://yombo.net/docs/libraries/startup>`_


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/startup.html>`_
"""
# Import twisted libraries
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboRestart
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

from yombo.utils import sleep, search_for_executable

logger = get_logger("library.startup")


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
        """
        Gets various configuration items and determines if the system is running for the first time,
        needs configuration setup, or should run as normal.

        It also validates that the system has a valid API login and API session. This is used to interact
        with the Yombo API cloud.
        :param kwargs:
        :return:
        """
        self.configs_needed = []
        self.configs_needed_human = []
        self.gwid = self._Configs.get2("core", "gwid", "local", False)
        self.gwhash = self._Configs.get2("core", "gwhash", None, False)
        self.has_valid_gw_auth = False

        self.cache_updater_running = False
        self.system_stopping = False
        if self._Loader.operating_mode == "first_run":  # will know if first_run already or yombo.ini is missing.
            self.configs_needed = ['gwid', 'gwhash']
            return
        first_run = self._Configs.get("core", "first_run", False, False)
        if first_run is True:
            self._Loader.operating_mode = "first_run"
            self.configs_needed = ['gwid', 'gwhash']
            return

        gwid = self.gwid()
        if gwid is None or gwid == "":
            self.configs_needed_human.append("Gateway ID is missing. Please complete the setup wizard again.")
            self._Loader.operating_mode = "first_run"
            self.configs_needed = ['gwid']
            return

        gwhash = self.gwhash()
        if gwhash is None or gwhash == "":
            print("setting to config mode ... 11")
            self._Loader.operating_mode = "config"
            self.configs_needed = ['gwhash']
            self.configs_needed_human.append("Gateway password is missing.")

        if len(self.configs_needed_human) == 0:
            has_valid_credentials = self._YomboAPI.gateway_credentials_is_valid
            if has_valid_credentials is False:
                # print("setting to config mode ... 22")
                self._Loader.operating_mode = "config"
                self.configs_needed_human.append("Gateway ID is invalid or has invalid authentication info.")
            else:  # If we have a valid gateway, download it's details.
                try:
                    response = yield self._YomboAPI.request("GET",
                                                            f"/v1/gateways/{gwid}")

                except YomboWarning as e:
                    logger.warn("Unable to get gateway details:{e}", e=e)
                    self._Loader.operating_mode = "config"
                    self.configs_needed = ['gwhash']
                    self.configs_needed_human.append("Gateway password is missing.")
                    return

                gateway = response.content["data"]["attributes"]
                self._Configs.set("core", "is_master", gateway["is_master"])
                self._Configs.set("core", "master_gateway_id", gateway["master_gateway_id"])
                self._Configs.set("core", "created_at", gateway["created_at"])
                self._Configs.set("core", "updated_at", gateway["updated_at"])
                self._Configs.set("core", "machine_label", gateway["label"])
                self._Configs.set("core", "label", gateway["label"])
                self._Configs.set("core", "description", gateway["description"])
                self._Configs.set("core", "owner_id", gateway["user_id"])
                self._Configs.set("dns", "fqdn", gateway["dns_name"])

                if gateway["dns_name"] is not None:
                    try:
                        response = yield self._YomboAPI.request("GET",
                                                                    f"/v1/gateways/{gwid}/dns")

                    except YomboWarning as e:
                        logger.warn("Unable to get gateway dns details:{e}", e=e)
                        self._Loader.operating_mode = "config"
                        self.configs_needed = ['gwhash']
                        self.configs_needed_human.append("Gateway password is missing.")
                        return
                    gateway_dns = response.content["data"]["attributes"]
                    print(f"gateway_dns: {gateway_dns}")
                    self._Configs.set("dns", "domain_id", gateway_dns["dns_domain_id"])
                    self._Configs.set("dns", "name", gateway_dns["name"])
                    self._Configs.set("dns", "allow_change_at", gateway_dns["allow_change_at"])
                    self._Configs.set("dns", "domain", gateway_dns["domain"])
                    self._Configs.set("dns", "fqdn", f"{gateway_dns['name']}.{gateway_dns['domain']}")
                else:
                    self._Configs.set("dns", "dns_domain_id", None)
                    self._Configs.set("dns", "name", None)
                    self._Configs.set("dns", "allow_change_at", None)
                    self._Configs.set("dns", "domain", None)
                    self._Configs.set("dns", "fqdn", None)

        is_master = self._Configs.get("core", "is_master", True)
        if is_master is False:
            master_gateway_id = self._Configs.get("core", "master_gateway_id", None, False)
            if master_gateway_id is None or master_gateway_id == "":
                self.configs_needed_human.append("Gateway is marked as slave, but no master gateway set.")

        if len(self.configs_needed_human) > 0:
            needed_text = "</li><li>".join(self.configs_needed_human)
            self._Notifications.add({"title": "Need configurations",
                                     "message":
                                         f"System has been placed into configuration mode. The following "
                                         f"configurations are needed:<p><ul><li>{needed_text}</li></ul>",
                                     "source": "Yombo Startup Library",
                                     "persist": False,
                                     "priority": "high",
                                     "always_show": True,
                                     "always_show_allow_clear": True,
                                     })
            print("setting to config mode ... 33")
            self._Loader.operating_mode = "config"

        self._Loader.operating_mode = "run"
        yield self._GPG._init_from_startup_()

    @inlineCallbacks
    def _load_(self, **kwargs):
        results = yield threads.deferToThread(search_for_executable, 'ffmpeg')
        self._Atoms.set("ffmpeg_bin", results, source=self)
        results = yield threads.deferToThread(search_for_executable, 'ffprobe')
        self._Atoms.set("ffprobe_bin", results, source=self)

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

        This will be removed in a future version due the new caching library.
        :return:
        """
        if self.cache_updater_running is True and force is True:
            self.cache_updater_running == None
            return

        if self._Loader.operating_mode != "run" or self.cache_updater_running is not False or \
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
