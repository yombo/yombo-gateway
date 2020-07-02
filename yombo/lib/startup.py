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

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/startup.html>`_
"""
# Import twisted libraries
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboRestart
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

from yombo.utils import is_true_false, search_for_executable

logger = get_logger("library.startup")


class Startup(YomboLibrary):
    """
    Start-up checks

    Checks to make sure basic configurations are valid and other start-up operations.
    """
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
        self.gwid = self._Configs.get("core.gwid", "local", False)
        self.gwhash = self._Configs.get("core.gwhash", None, False)
        self.has_valid_gw_auth = False

        if self._Loader.operating_mode == "first_run" or self._Configs.get("core.first_run", False, False):
            self._Loader.operating_mode = "first_run"
            self.configs_needed = ['gwid', 'gwhash']
            return

        if self.gwid is None or self.gwid == "":
            self.configs_needed_human.append("Gateway ID is missing. Please complete the setup wizard again.")
            self._Loader.operating_mode = "first_run"
            self.configs_needed = ['gwid']
            return

        if self.gwhash is None or self.gwhash == "":
            print("setting to config mode ... 11")
            self._Loader.operating_mode = "config"
            self.configs_needed = ['gwhash']
            self.configs_needed_human.append("Gateway password is missing.")
            return

        if len(self.configs_needed_human) == 0:
            has_valid_credentials = self._YomboAPI.gateway_credentials_is_valid
            if has_valid_credentials is False:
                print("setting to config mode ... 22")
                self._Loader.operating_mode = "config"
                self.configs_needed_human.append("Gateway ID is invalid or has invalid authentication info.")
                return

            else:  # If we have a valid gateway, download it's details.
                try:
                    response = yield self._YomboAPI.request("GET",
                                                            f"/v1/gateways/{self.gwid}")

                except YomboWarning as e:
                    logger.warn("Unable to get gateway details:{e}", e=e)
                    self._Loader.operating_mode = "config"
                    self.configs_needed = ['gwhash']
                    self.configs_needed_human.append("Gateway password is missing.")
                    return

                gateway = response.content["data"]["attributes"]
                self._Configs.set("core.is_master", is_true_false(gateway["is_master"]), ref_source=self)
                self._Configs.set("core.master_gateway_id", gateway["master_gateway_id"], ref_source=self)
                self._Configs.set("core.created_at", gateway["created_at"], ref_source=self)
                self._Configs.set("core.updated_at", gateway["updated_at"], ref_source=self)
                self._Configs.set("core.machine_label", gateway["label"], ref_source=self)
                self._Configs.set("core.label", gateway["label"], ref_source=self)
                self._Configs.set("core.description", gateway["description"], ref_source=self)
                self._Configs.set("core.owner_id", gateway["user_id"], ref_source=self)
                self._Configs.set("dns.fqdn", gateway["dns_name"], ref_source=self)

                if gateway["dns_name"] is not None:
                    try:
                        response = yield self._YomboAPI.request("GET",
                                                                f"/v1/gateways/{self.gwid}/dns")

                    except YomboWarning as e:
                        logger.warn("Unable to get gateway dns details:{e}", e=e)
                        self._Loader.operating_mode = "config"
                        self.configs_needed = ['gwhash']
                        self.configs_needed_human.append("Gateway password is missing.")
                        return
                    gateway_dns = response.content["data"]["attributes"]
                    self._Configs.set("dns.domain_id", gateway_dns["dns_domain_id"], ref_source=self)
                    self._Configs.set("dns.name", gateway_dns["name"], ref_source=self)
                    self._Configs.set("dns.allow_change_at", gateway_dns["allow_change_at"], ref_source=self)
                    self._Configs.set("dns.domain", gateway_dns["domain"], ref_source=self)
                    self._Configs.set("dns.fqdn", f"{gateway_dns['name']}.{gateway_dns['domain']}", ref_source=self)
                else:
                    self._Configs.set("dns.domain_id", None, ref_source=self)
                    self._Configs.set("dns.name", None, ref_source=self)
                    self._Configs.set("dns.allow_change_at", None, ref_source=self)
                    self._Configs.set("dns.domain", None, ref_source=self)
                    self._Configs.set("dns.fqdn", None, ref_source=self)

        is_master = self._Configs.get("core.is_master", True)
        if is_master is False:
            master_gateway_id = self._Configs.get("core.master_gateway_id", None, False)
            if master_gateway_id is None or master_gateway_id == "":
                self.configs_needed_human.append("Gateway is marked as slave, but no master gateway set.")

        if len(self.configs_needed_human) > 0:
            needed_text = "</li><li>".join(self.configs_needed_human)
            yield self._Notifications.new(title="Need configurations",
                                          message=f"System has been placed into configuration mode. The following "
                                                  f"configurations are needed:<p><ul><li>{needed_text}</li></ul>",
                                          persist=False,
                                          priority="high",
                                          always_show=True,
                                          always_show_allow_clear=True,
                                          _request_context=self._FullName,
                                          _authentication=self.AUTH_USER
                                          )

            self._Loader.operating_mode = "config"
            return

        self._Loader.operating_mode = "run"

    @inlineCallbacks
    def _load_(self, **kwargs):
        results = yield threads.deferToThread(search_for_executable, 'ffmpeg')
        yield self._Atoms.set_yield("ffmpeg_bin", results, value_type="string", authentication=self.AUTH_USER)
        results = yield threads.deferToThread(search_for_executable, 'ffprobe')
        yield self._Atoms.set_yield("ffprobe_bin", results, value_type="string", authentication=self.AUTH_USER)
