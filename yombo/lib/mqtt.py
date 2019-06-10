# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `MQTT @ Library Documentation <https://yombo.net/docs/libraries/mqtt>`_

Implements MQTT. It does 2 things:

1) Generate a mostquitto config file and password file
2) send HUP signal to mosquitto to reload the files

*Usage**:

.. code-block:: python

   def _init_(self):
       # Create anew connection. Hostname, port, user, password, ssl(True/False) can be specified if connection
       # to anther MQTT server. Otherwise, use the default local one.
       self.my_mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming)  # Create a new connection to the embedded MQTT server.

       # Subscribe to all topics of "foor/bar/topic" and send them to:  self.mqtt_incoming
       self.my_mqtt.subscribe("foo/bar/topic")
       d = self.my_mqtt.publish("for/bar/topic/status", "on")  # publish a message  # returns a deferred. Can be used to
       # stack more commands or do something after the message has been published.


   def mqtt_incoming(self, topic, payload, qos, retain):
       print(f"topic: {topic}")
       print(f"message: {message}"_


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.11.0

:copyright: Copyright 2016-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/mqtt.html>`_
"""
# Import python libraries
from collections import deque, Callable, OrderedDict
from datetime import datetime

# Import twisted libraries
from twisted.internet.ssl import ClientContextFactory
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.utils import getProcessOutput

# 3rd party libraries
from yombo.ext.mqtt import v311
from yombo.ext.mqtt.client.factory import MQTTFactory
from yombo.ext.mqtt.client.pubsubs import MQTTProtocol
from yombo.ext.mqtt.error import ProfileValueError

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboCritical
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import random_string, sleep
from yombo.utils.filewriter import FileWriter

logger = get_logger("library.mqtt")


class MQTT(YomboLibrary):
    """
    Manages MQTT broker and client connections.
    """
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)

    def _import_init_(self):
        self.client_enabled = True
        self.mqtt_server = None
        self.mqtt_local_client = None

    def _init_(self, **kwargs):
        """
        Builds the configuration and password files. Also starts the MQTT broker if enabled.

        :return:
        """
        self.client_connections = {}
        self.mosquitto_enabled = self._Configs.get("mqtt", "mosquitto_enabled", False)
        self.mosquitto_config_file = "/etc/mosquitto/yombo/yombo.conf"
        self.client_enabled = self._Configs.get("mqtt", "client_enabled", True)
        self.server_enabled = self._Configs.get("mqtt", "server_enabled", True)
        self.server_max_connections = self._Configs.get("mqtt", "server_max_connections", 1000)
        self.server_timeout_disconnect_delay = self._Configs.get("mqtt", "server_timeout_disconnect_delay", 2)


        if self.is_master:
            self.server_listen_port = self._Configs.get("mqtt", "server_listen_port", 1883)
            self.server_listen_port_ss_ssl = self._Configs.get("mqtt", "server_listen_port_ss_ssl", 1884)
            self.server_listen_port_le_ssl = self._Configs.get("mqtt", "server_listen_port_le_ssl", 8883)
            self.server_listen_port_websockets = self._Configs.get("mqtt", "server_listen_port_websockets", 8081)
            self.server_listen_port_websockets_ss_ssl = \
                self._Configs.get("mqtt", "server_listen_port_websockets_ss_ssl", 8444)
            self.server_listen_port_websockets_le_ssl = \
                self._Configs.get("mqtt", "server_listen_port_websockets_le_ssl", 8445)
            self.server_allow_anonymous = self._Configs.get("mqtt", "server_allow_anonymous", False)
        else:
            self.server_listen_port = 0
            self.server_listen_port_ss_ssl = 0
            self.server_listen_port_le_ssl = 0
            self.server_listen_port_websockets = 0
            self.server_listen_port_websockets_ss_ssl = 0
            self.server_listen_port_websockets_le_ssl = 0
            self.server_allow_anonymous = None

        self.mosquitto_running = None

    @inlineCallbacks
    def _load_(self, **kwargs):
        if self.server_enabled is False:
            logger.info("Embedded MQTT Disabled.")
            return

        if self.is_master is not True:
            logger.info("Not managing MQTT broker, we are not the master!")
            if self.mosquitto_enabled is True:
                logger.info("Disabling mosquitto MQTT broker.")
                try:
                    yield getProcessOutput("sudo", ["systemctl", "disable", "mosquitto.service"])
                except Exception as e:
                    logger.warn("Error while trying to disable mosquitto (mqtt) service: {e}", e=e)
                yield self.start_mqtt_broker()
                logger.info("Sleeping for 2 seconds while MQTT broker stops.")
                self._Configs.set("mqtt", "mosquitto_enabled", False)
                self.mosquitto_enabled = False
                yield sleep(2)
            return

        ssl_self_signed = self._SSLCerts.get("selfsigned")
        ssl_lib_webinterface = self._SSLCerts.get("lib_webinterface")

        mosquitto_config = [
            "allow_anonymous false",
            "user mosquitto",
            "persistent_client_expiration 4h",
            "max_connections 512",
            "",
        ]
        if self.server_listen_port > 0:
            mosquitto_config.extend([
                "#",
                "# Insecure listen MQTT port",
                "#",
                f"port {self.server_listen_port}",
                ""
            ])

        if self.server_listen_port_ss_ssl > 0:
            mosquitto_config.extend([
                "#",
                "# Self-signed cert for mqtt",
                "#",
                f"listener {self.server_listen_port_ss_ssl}",
                f"certfile {ssl_self_signed['cert_file']}",
                f"keyfile {ssl_self_signed['key_file']}",
                "ciphers ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS",
                "tls_version tlsv1.2",
                "protocol mqtt",
                "",
            ])

        if self.server_listen_port_le_ssl > 0 and ssl_lib_webinterface["self_signed"] is False:
            mosquitto_config.extend([
                "#",
                "# Lets encrypt signed cert for mqtt",
                "#",
                f"listener {self.server_listen_port_le_ssl}",
                f"cafile {ssl_lib_webinterface['chain_file']}",
                f"certfile {ssl_lib_webinterface['cert_file']}",
                f"keyfile {ssl_lib_webinterface['key_file']}",
                "ciphers ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS",
                "tls_version tlsv1.2",
                "protocol mqtt",
                "",
            ])

        if self.server_listen_port_websockets > 0:
            mosquitto_config.extend([
                "#",
                "# Unecrypted websockets",
                "#",
                f"listener {self.server_listen_port_websockets}",
                "protocol websockets",
                "max_connections 512",
                "",
            ])

        if self.server_listen_port_websockets_ss_ssl > 0:
            mosquitto_config.extend([
                "#",
                "# Self-signed cert for websockets",
                "#",
                f"listener {self.server_listen_port_websockets_ss_ssl}",
                f"certfile {ssl_self_signed['cert_file']}",
                f"keyfile {ssl_self_signed['key_file']}",
                "ciphers ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS",
                "tls_version tlsv1.2",
                "protocol websockets",
                "",
            ])

        if self.server_listen_port_websockets_le_ssl > 0 and  ssl_lib_webinterface["self_signed"] is False:
            mosquitto_config.extend([
                "#",
                "# Lets encrypt signed cert for websockets",
                "#",
                f"listener {self.server_listen_port_websockets_le_ssl}",
                f"cafile {ssl_lib_webinterface['chain_file']}",
                f"certfile {ssl_lib_webinterface['cert_file']}",
                f"keyfile {ssl_lib_webinterface['key_file']}",
                "ciphers ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS",
                "tls_version tlsv1.2",
                "protocol websockets",
                "",
            ])

        if ssl_lib_webinterface["self_signed"] is False:
            self.server_listen_port_websockets_le_ssl = self.server_listen_port_websockets_ss_ssl

        logger.debug("Writting mosquitto_config_file to: {mosquitto_config_file}",
                    mosquitto_config_file=self.mosquitto_config_file)
        config_file = FileWriter(filename=self.mosquitto_config_file, mode="w")
        config_file.write("# File automatically generated by Yombo Gateway. Edits will be lost.\n")
        config_file.write(f"# Created  {f'{datetime.now():%Y-%m-%d %H%M%S}'}\n\n")
        config_file.write("# HTTP Auth plugin...\n")
        config_file.write("auth_plugin /usr/local/src/yombo/mosquitto-auth-plug/auth-plug.so\n")
        config_file.write("auth_opt_backends http\n")
        # config_file.write("auth_opt_acl_log_quiet true\n")
        config_file.write("auth_opt_acl_cacheseconds 600\n")
        config_file.write("auth_opt_auth_cacheseconds 30\n")
        config_file.write("auth_opt_http_ip 127.0.0.1\n")
        webinterface_port = self._Configs.get("webinterface", "nonsecure_port", fallback=8080)
        config_file.write(f"auth_opt_http_port {webinterface_port}\n")
        config_file.write("auth_opt_http_getuser_uri /api/v1/mqtt/auth/user\n")
        config_file.write("auth_opt_http_superuser_uri /api/v1/mqtt/auth/superuser\n")
        config_file.write("auth_opt_http_aclcheck_uri /api/v1/mqtt/auth/acl\n")
        config_file.write("# Base configs\n\n")
        for line_out in mosquitto_config:
            config_file.write(f"{line_out}\n")
        yield config_file.close_while_waiting()

        if self.mosquitto_enabled is False:
            logger.info("Enabling mosquitto MQTT broker.")
            try:
                yield getProcessOutput("sudo", ["systemctl", "enable", "mosquitto.service"])
            except Exception as e:
                logger.warn("Error while trying to enable mosquitto (mqtt) service: {e}", e=e)
            self._Configs.set("mqtt", "mosquitto_enabled", True)
            self.mosquitto_enabled = True

        yield self.check_mqtt_broker_running()
        if self.mosquitto_running is False:
            yield self.start_mqtt_broker()
            logger.info("Sleeping for 3 seconds while MQTT broker starts up.")
            yield sleep(3)
            if self.mosquitto_running is False:
                logger.error("Cannot connect to MQTT broker.")
                raise YomboCritical("MQTT failed to connect and/or start, shutting down.")

    @inlineCallbacks
    def _unload_(self, **kwargs):
        logger.debug("shutting down mqtt clients...")
        if hasattr(self, "client_connections"):
            for client_id, client in self.client_connections.items():
                logger.debug("in loop to try to stop mqtt client: {client_id}", client_id=client_id)
                try:
                    logger.debug(f"telling client to say goodbye... {client_id}")
                    client.factory.stopTrying(

                    )  # Tell reconnecting factory to don"t attempt connecting after disconnect.
                    client.factory.protocol.disconnect()
                    client.factory.protocol.close()
                except:
                    pass
            yield sleep(0.1)

        if hasattr(self, "_States"):
            if self._Loader.operating_mode == "run" and self.mqtt_server is not None:
                self.mqtt_server.shutdown()

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

    def new(self, server_hostname=None, server_port=None, username=None, password=None, ssl=None,
            mqtt_incoming_callback=None, mqtt_connected_callback=None, mqtt_connection_lost_callback=None,
            will_topic=None, will_message=None, will_qos=0, will_retain=None, clean_start=True,
            version=v311, keepalive=0, client_id=None, password2=None):
        """
        Create a new connection to MQTT. Don't worry, it's designed for many many connections. Leave all
        connection details blank or all completed. Blank will connect the MQTT client to the default Yombo
        embedded MQTT Server: Mostquitto

        .. code-block:: python

           self.my_mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming, client_id="my_client_name")
           self.mqtt.subscribe("yombo/devices/+/get")  # subscribe to a topic. + is a wilcard for a single section.

        :param on_connect_callback: Callback to a method when the MQTT connection is up. Used for notifications or status updates.
        :param server_hostname: Broker to connect to. If not set, uses the local broker.
        :param server_port: Port to connect to, default is the non-secure port.
        :param user: User to connect as. Default is the local yombo user.
        :param password: Password to use for connection. Default is the local yombo user password.
        :param ssl: Use SSL. Default is False. It's recommended to use SSL when connecting to a remote server.
        :return:
        """
        if not self.client_enabled or hasattr(self, "_States") is False:
            logger.warn("MQTT Clients Disabled. Not allowed to connect.")
            return

        if self._Loader.operating_mode != "run":
            logger.warn("MQTT Disabled when not in run mode.")
            return

        if client_id is None:
            client_id = f"Yombo-{self.gateway_id}-unknown-{random_string(length=10)}"
        if client_id in self.client_connections:
            logger.warn(f"client_id must be unique. Got: {client_id}")
            raise YomboWarning (f"client_id must be unique. Got: {client_id}", "MQTT::new", "mqtt")

        if server_hostname is None:
            if self._GatewayComs.client_default_host is None:
                logger.warn("Cannot create MQTT client, no default host defined.")
                return
            server_hostname = self._GatewayComs.client_default_host

        if ssl is None:
            ssl = self._GatewayComs.client_default_ssl

        if server_port is None:
            server_port = self._GatewayComs.client_default_port

        if username is None:
            username = self._GatewayComs.client_default_username

        if password is None:
            password = self._GatewayComs.client_default_password1
        if password2 is None:
            password2 = self._GatewayComs.client_default_password2

        if mqtt_incoming_callback is not None:
            if isinstance(mqtt_incoming_callback, Callable) is False:
                raise YomboWarning("If mqtt_incoming_callback is set, it must be be callable.", 200, "new", "Devices")

        if mqtt_connected_callback is not None:
            if isinstance(mqtt_connected_callback, Callable) is False:
                raise YomboWarning("If mqtt_connected_callback is set, it must be be callable.", 201, "new", "Devices")

        # print("mqtt: %s:%s" % (username, password))
        self.client_connections[client_id] = MQTTClient(self, client_id, server_hostname, server_port, username,
            password, password2, ssl, mqtt_incoming_callback, mqtt_connected_callback, mqtt_connection_lost_callback,
            will_topic, will_message, will_qos, will_retain, clean_start, version, keepalive)
        return self.client_connections[client_id]


class MQTTClient(object):
    """
    A helper class for MQTT. This class is returned back to the any module that request a new MQTT client connection.

    .. code-block:: python

       self.my_mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming, client_id="my_client_name")
       self.mqtt.subscribe("yombo/devices/+/get")  # subscribe to a topic. + is a wilcard for a single section.
    """
    def __init__(self, mqtt_library, client_id, server_hostname, server_port, username=None, password=None,
                 password2=None, ssl=False, mqtt_incoming_callback=None, mqtt_connected_callback=None,
                 mqtt_connection_lost_callback=None, will_topic=None, will_message=None,
                 will_qos=0, will_retain=None, clean_start=True, version=v311, keepalive=0):
        """
        Creates a new client connection to an MQTT broker.
        :param mqtt_library: A reference to the MQTT library above.
        :param server_hostname: Broker to connect to. If not set, uses the local broker.
        :param server_port: Port to connect to, default is the non-secure port.
        :param client_id: Client ID, either supplied from the calling library or random.
        :param username: User to connect as. Default is the local yombo user.
        :param password: Password to use for connection. Default is the local yombo user password.
        :param password2: Second password to try to use for connection. Default is the local yombo user password.
        :param ssl: Use SSL. Default is False. It's recommended to use SSL when connecting to a remote server.
        :param mqtt_incoming_callback: Callback to send incoming messages to.
        :param mqtt_connected_callback: Callback to a method when the MQTT connection is up. Used for notifications or status updates.
        :param mqtt_connection_lost_callback: Callback to a method when the MQTT connection goes down.
        :param will_topic: Last will and testimate topic. Default is None.
        :param will_message: Last will and testimate message. Default is None.
        :param will_qos: Last will and testimate qos. Default is 0.
        :param will_retain: Last will and testimate retain.
        :param clean_start:
        :param clean_start:
        :param version: Version to connect client as. Default is v311.
        :param keepalive: Send keepalive pings. Default is 0.

        :return:
        """
        self.server_hostname = server_hostname
        self.server_port = server_port
        self.username = username
        self.password = password
        self.password2 = password2
        self.ssl = ssl
        self.connected = False
        self._Parent = mqtt_library
        self.client_id = client_id

        self.incoming_duplicates = deque([], 150)

        self.mqtt_incoming_callback = mqtt_incoming_callback
        self.mqtt_connected_callback = mqtt_connected_callback
        self.mqtt_connection_lost_callback = mqtt_connection_lost_callback

        self.factory = MQTTTYomboFactory(profile=MQTTFactory.PUBLISHER | MQTTFactory.SUBSCRIBER)
        self.factory.noisy = False  # turn off Starting/stopping message
        self.factory.mqtt_client=self
        self.factory.username = username
        self.factory.password = password
        self.factory.password2 = password2
        self.factory.will_topic = will_topic
        self.factory.will_message = will_message
        self.factory.will_qos = will_qos
        self.factory.will_qos = 0
        self.factory.will_retain = will_retain
        self.factory.clean_start = clean_start
        self.factory.version = version
        self.factory.will_retain = will_retain
        self.factory.version = version
        self.factory.keepalive = keepalive
        self.queue = self._Parent._Queue.new(f"library.mqtt.{client_id}", self.process_queue)  # test calls to things that don't return deferred
        self.queue.pause()  # pause this, and will resume it when we are connected.
        self.republish_queue = OrderedDict({})  # for items that are marked "retain", this these will be replayed on reconnect.
        self.topics_subscribed = {}  # a list of topics this client subscribes too.
        self.processing_republish_queue = False
        try:
            if ssl:
                self.my_reactor = reactor.connectSSL(server_hostname, server_port, self.factory,
                                                     ClientContextFactory())
            else:
                self.my_reactor = reactor.connectTCP(server_hostname, server_port, self.factory)
        except Exception as e:
            logger.warn("Unanble to connect to MQTT: {e}", e=e)

    def publish(self, topic, message, qos=0, priority=10, retain=False, republish=None):
        """
        Publish a message.

        :param topic: "yombo/devices/bedroom_light/command"
        :param message: string - Like "on"
        :param qos: 0, 1, or 2. Default is 0.
        :return:
        """
        job = {
            "type": "publish",
            "topic": topic,
            "message": message,
            "qos": qos,
            "retain": retain,
            "priority": priority,
            "published": False,
        }
        if republish is None or republish is True:
            self.republish_queue[random_string()] = job
            self.dispatch_job_queue()
        else:
            self.queue.put(job, priority=priority)

    # @inlineCallbacks
    def subscribe(self, topic, qos=1, priority=-2, republish=None):
        """
        Subscribe to a topic. Inlucde the topic like "yombo/myfunky/something"
        :param topic: string or list of strings to subscribe to.
        :param callback: a point to a function to be called when data arrives.
        :param qos: See MQTT doco for information. We handle duplicates, no need for qos 2.
        :return:
        """
        job = {
            "type": "subscribe",
            "topic": topic,
            "qos": qos,
            "priority": priority,
            "published": False,
        }
        if republish is None or republish is True:
            job_id = random_string()
            self.topics_subscribed[topic] = job_id
            self.republish_queue[job_id] = job
            self.dispatch_job_queue()
        else:
            self.queue.put(job, priority=priority)

    def unsubscribe(self, topic, qos=1, priority=-1):
        """
        Unsubscribe from a topic.
        :param topic:
        :return:
        """
        if topic in self.topics_subscribed:
            del self.republish_queue[self.topics_subscribed[topic]]
            del self.topics_subscribed[topic]

        job = {
            "type": "unsubscribe",
            "topic": topic,
            "qos": qos,
            "priority": priority,
            "published": False,
        }
        self.queue.put(job, priority=priority)

    # @inlineCallbacks
    def mqtt_connected(self):
        """
        Call when mqtt client is connected. Subscribes, unsubscribes, and publises any queued messages. Afterwards,
        if the client has a connected callback, will also call that.
        :return:
        """
        logger.debug("client ID connected: {client_id}", client_id=self.client_id)
        self.connected = True
        self.dispatch_job_queue()
        self.queue.resume()
        if self.mqtt_connected_callback:
            self.mqtt_connected_callback()

    def dispatch_job_queue(self):
        if self.connected is True:
            for job_id, job_info in self.republish_queue.items():
                if self.republish_queue[job_id]["published"] is False:
                    self.republish_queue[job_id]["published"] = True
                    if self.queue.stopped is False:
                        self.queue.put(job_info, priority=job_info["priority"])

    @inlineCallbacks
    def process_queue(self, job):
        logger.debug("process_queue. job: {job}", job=job)
        if job["type"] == "subscribe":
            yield self.factory.protocol.subscribe(job["topic"], job["qos"])
        elif job["type"] == "unsubscribe":
            yield self.factory.protocol.unsubscribe(job["topic"])
        elif job["type"] == "publish":
            yield self.factory.protocol.publish(job["topic"], job["message"], qos=job["qos"], retain=job["retain"])
        else:
            logger.warn("process_queue received unknown job request: {job}", job=job)

    def mqtt_incoming(self, topic, payload, qos, dup, retain, mqtt_msg_id):
        """
        Incoming messages from MQTT broker come here.

        :param topic: MQTT Topic
        :param payload: Payload portion
        :param qos: Quality Service
        :param dup: Will be 1 if duplicate flag was set in MQTT message. We ignore this
        :param retain: If retain flag was set.
        :param mqtt_msg_id: MQTT Msg ID. Used to detect duplicates.
        :return:
        """
        # print("mqtt_incoming - topic:%s, payload:%s, qos:%s, dup:%s, retain:%s, mqtt_msg_id:%s" % (topic, payload, qos, dup, retain, mqtt_msg_id))
        if self.mqtt_incoming_callback:
            #  check if we already received this msg_id. This is why we don't need qos=2 for incoming, qos 1 is enough.
            if mqtt_msg_id is not None:
                if mqtt_msg_id not in self.incoming_duplicates:
                    self.incoming_duplicates.append(mqtt_msg_id)
                else:
 #                   print("dropping duplicate message: %s" % mqtt_msg_id)
                    return
            self.mqtt_incoming_callback(topic, payload, qos, retain)
        else:
            raise YomboWarning("Recieved MQTT message, but no callback defined, no where to send.", "direct_incoming",
                               "mqtt")

    def client_connectionLost(self, reason):
        """
        Called when the connection to the broker is lost. Calls a client connection lost callbacks if defined.
        :param reason:
        :return:
        """
        self.queue.pause()
        # print(f"Reason: {reason}")
        logger.info("Lost connection to MQTT Broker: {reason}", reason=str(reason))
        self.connected = False
        for job_id, job in self.republish_queue.items():
            self.republish_queue[job_id]["published"] = False

        if self.mqtt_connection_lost_callback:
            self.mqtt_connection_lost_callback()


class MQTTYomboProtocol(MQTTProtocol):
    """
    Makes minor tweaks to the MQTTProtocol for use with Yombo.
    """
    def connectionMade(self):  # Empty through stack of twisted and MQTT library
        self.onMqttConnectionMade = self.factory.mqtt_client.mqtt_connected
        self.onDisconnection = self.factory.mqtt_client.client_connectionLost
        # print("connection mqtt client: %s -> %s" % (self.factory.mqtt_client.username,
        #                                             self.factory.mqtt_client.password) )
        # print("connection mqtt client: %s -> %s:%s" % (self.factory.mqtt_client.ssl,
        #                                                self.factory.mqtt_client.server_hostname,
        #                                                self.factory.mqtt_client.server_port))
        self.connect(self.factory.mqtt_client.client_id, keepalive=self.factory.keepalive,
            willTopic=self.factory.will_topic, willMessage=self.factory.will_message,
            willQoS=self.factory.will_qos, willRetain=self.factory.will_retain,
            username=self.factory.username, password=self.factory.password,
            cleanStart=self.factory.clean_start)


class MQTTTYomboFactory(MQTTFactory):

    def buildProtocol(self, addr):
        if self.profile == self.SUBSCRIBER:
            from yombo.ext.mqtt.client.subscriber import MQTTProtocol
        elif self.profile == self.PUBLISHER:
            from yombo.ext.mqtt.client.publisher import MQTTProtocol
        elif self.profile == (self.SUBSCRIBER | self.PUBLISHER):
            from yombo.ext.mqtt.client.pubsubs import MQTTProtocol
        else:
            raise ProfileValueError("profile value not supported", self.profile)

        v = self.queuePublishTx.get(addr, deque())
        self.queuePublishTx[addr] = v
        v = self.windowPublish.get(addr, dict())
        self.windowPublish[addr] = v
        v = self.windowPubRelease.get(addr, dict())
        self.windowPubRelease[addr] = v
        v = self.windowPubRx.get(addr, dict())
        self.windowPubRx[addr] = v
        v = self.windowSubscribe.get(addr, dict())
        self.windowSubscribe[addr] = v
        v = self.windowUnsubscribe.get(addr, dict())
        self.windowUnsubscribe[addr] = v

        self.protocol = MQTTYomboProtocol(self, addr)  # Everything above is from mqtt.client.factory
        self.protocol.onPublish = self.mqtt_client.mqtt_incoming
        return self.protocol                           # submitted pull request to get this into source

    # def clientConnectionLost(self, connector, reason):
    #     print("MQTTTYomboFactory clientConnectionLost 1. Reason: %s" % reason.value)
    #     protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
    #
    # def clientConnectionFailed(self, connector, reason):
    #     logger.info("MQTTTYomboFactory clientConnectionFailed. Reason: {reason}", reason=reason)
    #     # self.AMQPClient.disconnected("failed")
    #     protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

class MQTTServer(protocol.ProcessProtocol):
    def __init__(self):
        pass

    def shutdown(self):
        self.transport.closeStdin() # tell them we're done

    # def connectionMade(self):
    #     print("connectionMade!")
    #
    # def outReceived(self, data):
    #     print("outReceived: %s" % data)
    #
    # def errReceived(self, data):
    #     print("HBQMTT ERR: %s" % data)
    #
    # def inConnectionLost(self):
    #     print("inConnectionLost! stdin is closed! (we probably did it)")
    #
    # def outConnectionLost(self):
    #     print("outConnectionLost! The child closed their stdout!")
    #     # now is the time to examine what they wrote
    #     print("I saw them write:", self.data)
    #
    # def errConnectionLost(self):
    #     print("errConnectionLost! The child closed their stderr.")
    #
    # def processExited(self, reason):
    #     print("processExited, status %d" % (reason.value.exitCode,))
    #
    # def processEnded(self, reason):
    #     print("processEnded, status %d" % (reason.value.exitCode,))
    #
