# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. warning::

   This library is not intended to be accessed by module developers or end users. These functions, variables,
   and classes were not intended to be accessed directly by modules. These are documented here for completeness.

.. note::

  * For library documentation, see: `Mosquitto @ Library Documentation <https://yombo.net/docs/libraries/mosquitto>`_

Manages the mosquitto configuration file. If this is the master gateway, manages the mosquitto software.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/mosquitto.html>`_
"""
# Import python libraries
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet.utils import getProcessOutput

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import random_string, sleep

logger = get_logger("library.mosquitto")


class Mosquitto(YomboLibrary):
    """
    Manages Mosquitto broker and it's configuration.
    """
    # mqtt_server: ClassVar = None
    mqtt_local_client: ClassVar = None
    listen_port: ClassVar[int] = None
    listen_port_ss_ssl: ClassVar[int] = None
    listen_port_le_ssl: ClassVar[int] = None
    listen_port_websockets: ClassVar[int] = None
    listen_port_websockets_ss_ssl: ClassVar[int] = None
    listen_port_websockets_le_ssl: ClassVar[int] = None
    server_allow_anonymous: ClassVar[int] = None

    def _init_(self, **kwargs):
        """
        Builds the configuration and password files. Also starts the MQTT broker if enabled.

        :return:
        """
        self.enabled = self._Configs.get("mosquitto.enabled", True, False)
        self.config_file_path = self._Configs.get("mosquitto.config_file", "/etc/mosquitto/yombo/yombo.conf")
        self.max_connections = self._Configs.get("mosquitto.max_connections", 1000)
        self.timeout_disconnect_delay = self._Configs.get("mosquitto.timeout_disconnect_delay", 2)

        if self._is_master:
            self.listen_port = self._Configs.get("mosquitto.listen_port", 1883)
            self.listen_port_ss_ssl = self._Configs.get("mosquitto.listen_port_ss_ssl", 1884)
            self.listen_port_le_ssl = self._Configs.get("mosquitto.listen_port_le_ssl", 8883)
            self.listen_port_websockets = self._Configs.get("mosquitto.listen_port_websockets", 8081)
            self.listen_port_websockets_ss_ssl = \
                self._Configs.get("mosquitto.listen_port_websockets_ss_ssl", 8444)
            self.listen_port_websockets_le_ssl = \
                self._Configs.get("mosquitto.listen_port_websockets_le_ssl", 8445)
            self.server_allow_anonymous = self._Configs.get("mqtt.server_allow_anonymous", False)
        else:
            self.listen_port = 0
            self.listen_port_ss_ssl = 0
            self.listen_port_le_ssl = 0
            self.listen_port_websockets = 0
            self.listen_port_websockets_ss_ssl = 0
            self.listen_port_websockets_le_ssl = 0
            self.server_allow_anonymous = None

        self.mosquitto_running = None

    @inlineCallbacks
    def _load_(self, **kwargs):
        if self.enabled is False:
            logger.info("Mosquitto MQTT broker management has been disabled by configuration setting.")
            return

        if self._is_master is not True:
            logger.info("Not managing MQTT broker, we are not the master.")
            if self.enabled is True:
                self._Configs.set("mqtt.enabled", False, ref_source=self)
                self.enabled = False 
            return

        ssl_self_signed = yield self._SSLCerts.get("selfsigned")
        ssl_lib_webinterface = yield self._SSLCerts.get("lib_webinterface")

        mosquitto_config = [
            "allow_anonymous false",
            "user mosquitto",
            "persistent_client_expiration 4h",
            "max_connections 512",
            "",
        ]
        if self.listen_port > 0:
            mosquitto_config.extend([
                "#",
                "# Insecure listen MQTT port",
                "#",
                f"port {self.listen_port}",
                ""
            ])

        if self.listen_port_ss_ssl > 0:
            mosquitto_config.extend([
                "#",
                "# Self-signed cert for mqtt",
                "#",
                f"listener {self.listen_port_ss_ssl}",
                f"certfile {ssl_self_signed['cert_path']}",
                f"keyfile {ssl_self_signed['key_path']}",
                "ciphers ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS",
                "tls_version tlsv1.2",
                "protocol mqtt",
                "",
            ])

        if self.listen_port_le_ssl > 0 and ssl_lib_webinterface["self_signed"] is False:
            mosquitto_config.extend([
                "#",
                "# Lets encrypt signed cert for mqtt",
                "#",
                f"listener {self.listen_port_le_ssl}",
                f"cafile {ssl_lib_webinterface['chain_path']}",
                f"certfile {ssl_lib_webinterface['cert_path']}",
                f"keyfile {ssl_lib_webinterface['key_path']}",
                "ciphers ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS",
                "tls_version tlsv1.2",
                "protocol mqtt",
                "",
            ])

        if self.listen_port_websockets > 0:
            mosquitto_config.extend([
                "#",
                "# Unecrypted websockets",
                "#",
                f"listener {self.listen_port_websockets}",
                "protocol websockets",
                "max_connections 512",
                "",
            ])

        if self.listen_port_websockets_ss_ssl > 0:
            mosquitto_config.extend([
                "#",
                "# Self-signed cert for websockets",
                "#",
                f"listener {self.listen_port_websockets_ss_ssl}",
                f"certfile {ssl_self_signed['cert_path']}",
                f"keyfile {ssl_self_signed['key_path']}",
                "ciphers ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS",
                "tls_version tlsv1.2",
                "protocol websockets",
                "",
            ])

        if self.listen_port_websockets_le_ssl > 0 and  ssl_lib_webinterface["self_signed"] is False:
            mosquitto_config.extend([
                "#",
                "# Lets encrypt signed cert for websockets",
                "#",
                f"listener {self.listen_port_websockets_le_ssl}",
                f"cafile {ssl_lib_webinterface['chain_path']}",
                f"certfile {ssl_lib_webinterface['cert_path']}",
                f"keyfile {ssl_lib_webinterface['key_path']}",
                "ciphers ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS",
                "tls_version tlsv1.2",
                "protocol websockets",
                "",
            ])

        if ssl_lib_webinterface["self_signed"] is False:
            self.listen_port_websockets_le_ssl = self.listen_port_websockets_ss_ssl

        logger.debug("Writing config_file_path to: {config_file_path}", config_file_path=self.config_file_path)
        config_file = yield self._Files.save_stream(filename=self.config_file_path, mode="w")
        config_file.write("# File automatically generated by Yombo Gateway. Edits will be lost.\n")
        config_file.write(f"# Created  {f'{datetime.now():%Y-%m-%d %H%M%S}'}\n\n")
        config_file.write("# HTTP Auth plugin...\n")
        config_file.write("auth_plugin /usr/local/src/yombo/mosquitto-auth-plug/auth-plug.so\n")
        config_file.write("auth_opt_backends http\n")
        config_file.write("auth_opt_acl_cacheseconds 300\n")
        config_file.write("auth_opt_auth_cacheseconds 15\n")
        config_file.write("auth_opt_http_ip 127.0.0.1\n")
        webinterface_port = self._Configs.get("webinterface.nonsecure_port", 8080)
        config_file.write(f"auth_opt_http_port {webinterface_port}\n")
        config_file.write("auth_opt_http_getuser_uri /api/v1/mosquitto_auth/auth/user\n")
        config_file.write("auth_opt_http_superuser_uri /api/v1/mosquitto_auth/auth/superuser\n")
        config_file.write("auth_opt_http_aclcheck_uri /api/v1/mosquitto_auth/auth/acl\n")
        config_file.write("# Base configs\n\n")
        for line_out in mosquitto_config:
            config_file.write(f"{line_out}\n")
        yield config_file.close()

        if self.enabled is False:
            logger.info("Enabling mosquitto MQTT broker.")
            try:
                yield getProcessOutput("sudo", ["systemctl", "enable", "mosquitto.service"])
            except Exception as e:
                logger.warn("Error while trying to enable mosquitto (mqtt) service: {e}", e=e)
            self._Configs.set("mqtt.enabled", True, ref_source=self)
            self.enabled = True

        yield self.check_mqtt_broker_running()
        if self.mosquitto_running is False:
            yield self.start_mqtt_broker()
            logger.info("Sleeping for 3 seconds while MQTT broker starts up.")
            yield sleep(3)
            if self.mosquitto_running is False:
                logger.error("Cannot connect to MQTT broker.")
                # Todo: need a better way to handle MQTT broker issues.....
                # raise YomboCritical("MQTT failed to connect and/or start, shutting down.")

    # @inlineCallbacks
    # def _unload_(self, **kwargs):
    #     logger.debug("shutting down mqtt clients...")
    #
    #     if self._is_master is True and self.enabled is True:
    #         if self._Loader.operating_mode == "run" and self.mqtt_server is not None:
    #             self.mqtt_server.shutdown()

    @inlineCallbacks
    def check_mqtt_broker_running(self):
        """
        Checks if the mqtt broker is running.
        :return:
        """
        try:
            process_results = yield getProcessOutput("ps", ["-A"])
        except Exception as e:
            logger.warn("Error while trying to check is mosquitto (mqtt) service is running: {e}", e=e)
            return None

        # print("process results: %s" % process_results)
        if b"mosquitto" in process_results:
            self.mosquitto_running = True
            return True
        else:
            self.mosquitto_running = False
            return False

    @inlineCallbacks
    def start_mqtt_broker(self):
        """
        Start the mqtt broker. Note: this will sleep for 2 seconds to ensure it starts.
        :return:
        """
        logger.warn("starting mosquitto service.")
        if self.enabled is False:
            return
        try:
            yield getProcessOutput("sudo", ["systemctl", "start", "mosquitto.service"])
        except Exception as e:
            logger.warn("Error while trying to start mosquitto (mqtt) service: {e}", e=e)
        yield sleep(0.5)
        running = yield self.check_mqtt_broker_running()
        return running

    @inlineCallbacks
    def stop_mqtt_broker(self):
        """
        Stop the mqtt broker. Note: This will sleep for 2 seconds to ensure it stops.
        :return:
        """
        logger.warn("stopping mosquitto service.")
        try:
            yield getProcessOutput("sudo", ["systemctl", "stop", "mosquitto.service"])
        except Exception as e:
            logger.warn("Error while trying to stop mosquitto (mqtt) service: {e}", e=e)
        yield sleep(0.5)
        running = yield self.check_mqtt_broker_running()
        return running
