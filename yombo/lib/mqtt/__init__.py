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
       self.my_mqtt = self._MQTT.new(on_message_callback=self.mqtt_incoming)  # Create a new connection to the embedded MQTT server.

       # Subscribe to all topics of "foor/bar/topic" and send them to:  self.mqtt_incoming
       self.my_mqtt.subscribe("foo/bar/topic")
       d = self.my_mqtt.publish("for/bar/topic/status", "on")  # publish a message  # returns a deferred. Can be used to
       # stack more commands or do something after the message has been published.


   def mqtt_incoming(self, topic, payload, qos, retain):
       print(f"topic: {topic}")
       print(f"message: {message}"_


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.11.0
   Original version
.. versionadded:: 0.24.0
   Split off mosquitto to it's own library. Change to use qmqtt module.


:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/mqtt/__init__.html>`_
"""
# Import python libraries
from collections import deque, Callable
from gmqtt import Message as QMessage
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.lib.mqtt.mqttclient import MQTTClient
from yombo.utils import random_string, sleep

logger = get_logger("library.mqtt")


class MQTT(YomboLibrary):
    """
    Manages MQTT broker and client connections.
    """
    client_connections: ClassVar[dict] = {}
    _storage_attribute_name: ClassVar[str] = "client_connections"
    _storage_attribute_sort_key: ClassVar[str] = "client_id"

    def _init_(self, **kwargs):
        """
        Builds the configuration and password files. Also starts the MQTT broker if enabled.

        :return:
        """
        self.messages_processed = None  # Track incoming and outgoing messages. Meta data only.
        self.message_correlations = None  # Track various bits of information for sent correlation_ids.

    @inlineCallbacks
    def _unload_(self, **kwargs):
        logger.debug("shutting down mqtt clients...")
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

    def last_will(self, topic, message, will_delay_interval=None, **kwargs):
        """
        Creates a last will message to be used on "new()" method.

        .. code-block:: python

           last_will = self._MQTTYombo.last_will("yombo/something", "disconencted..."coming, client_id="my_client_name")
           self.mqtt.subscribe("yombo/devices/+/get")  # subscribe to a topic. + is a wilcard for a single section.

        :param topic: Topic to send message to.
        :param message: The message to send.
        :param will_delay_interval: How many seconds to send after client disconnects without saying goodbye.
        :param kwargs: Any additional arugments to send to message constructor.
        :return:
        """
        will_delay_interval = will_delay_interval or 10
        return QMessage(topic, message, will_delay_interval=will_delay_interval, **kwargs)

    @inlineCallbacks
    def new(self, hostname: Optional[str] = None, port: Optional[int] = None, username: Optional[str] = None,
            password: Optional[str] = None, use_ssl: Optional[bool] = None, version: Optional[str] = None,
            keepalive: Optional[int] = None, session_expiry: Optional[int] = None,
            receive_maximum: Optional[int] = None, user_property: Optional[Union[tuple, List[tuple]]] = None,
            last_will: Optional = None, maximum_packet_size: Optional[int] = None,
            on_message_callback: Callable = None, subscribe_callback: Callable = None,
            unsubscribe_callback: Callable = None,
            connected_callback: Optional[Callable] = None, disconnected_callback: Optional[Callable] = None,
            error_callback: Optional[Callable] = None, client_id: Optional[str] = None,
            password2: Optional[str] = None):
        """
        Create a new connection to MQTT. Don't worry, it's designed for many many connections. Leave all
        connection details blank or all completed. Blank will connect the MQTT client to the default Yombo
        embedded MQTT Server: Mostquitto

        .. code-block:: python

           self.my_mqtt = self._MQTTYombo.new(coming_callback=self.mqtt_incoming, client_id="my_client_name")
           self.mqtt.subscribe("yombo/devices/+/get")  # subscribe to a topic. + is a wilcard for a single section.

        session_expiry - This determines of the brother should retain messages after

        :param hostname: IP address or hostname to connect to.
        :param port: Port number to connect to.
        :param username: Username to connect as. Use "" to not use a username & password.
        :param password: Password to to connect with. Use "" to not use a password.
        :param use_ssl: Use SSL when attempting to connect to server, default is True.
        :param version: MQTT version to use, default: MQTTv50. Other: MQTTv311
        :param keepalive: How often the connection should be checked that it's still alive.
        :param session_expiry: How many seconds the session should be valid. Defaults to 0.
        :param receive_maximum: The Client uses this value to limit the number of QoS 1 and QoS 2 publications that it
               is willing to process concurrently.
        :param user_property: Connection user_property. A tuple or list of tuples.
        :param last_will: Last will message generated by 'will()'.
        :param maximum_packet_size: The maximum size the mqtt payload should be, in size.
        :param on_message_callback: (required) method - Method to send messages to.
        :param connected_callback: method - If you want a function called when connected to server.
        :param disconnected_callback: method - If you want a function called when disconnected from server.
        :param subscribe_callback: method - This method will be called when successfully subscribed to topic.
        :param unsubscribe_callback: method - This method will be called when successfully unsubscribed from topic.
        :param error_callback: method - A function to call if something goes wrong.
        :param client_id: (default - random) - A client id to use for logging.
        :param password2: A second password to try. Used by MQTTYombo.
        :return:
        """
        if self._Loader.operating_mode != "run":
            logger.warn("MQTT Disabled when not in run mode.")
            return

        if on_message_callback is None:
            raise YomboWarning("Missing on_message_callback, must be a callable.")
        if isinstance(on_message_callback, Callable) is False:
            raise YomboWarning("on_message_callback is not a callable (function).", 200, "new", "mqtt")

        for callback_name in ("connected_callback", "disconnected_callback", "subscribe_callback",
                              "unsubscribe_callback", "error_callback"):
            callback = locals()[callback_name]
            if callback is not None and isinstance(callback, Callable) is False:
                raise YomboWarning(f"If {callback_name} is set, it must be be callable.", 201, "new", "mqtt")

        if client_id is None:
            client_id = f"ygw-{self._gateway_id}-{random_string(length=15)}"

        if client_id in self.client_connections:
            logger.warn(f"client_id must be unique. Got: {client_id}")
            raise YomboWarning(f"client_id must be unique. Got: {client_id}", 201, "new", "mqtt")

        if hostname is None:
            if self._MQTTYombo.default_host is None:
                logger.warn("Cannot create MQTT client, no default host defined.")
                return
            hostname = self._MQTTYombo.default_host

        if use_ssl is None:
            use_ssl = hostname = self._MQTTYombo.default_host

        if port is None:
            port = self._MQTTYombo.default_port

        if username is None:
            username = self._MQTTYombo.default_username

        if password is None:
            password = self._MQTTYombo.default_password1
        if password2 is None and client_id.startswith("mqttyombo-"):
            password2 = self._MQTTYombo.default_password2

        keepalive = keepalive or 60
        session_expiry = session_expiry or 0
        receive_maximum = receive_maximum or 65535
        maximum_packet_size = maximum_packet_size or 1048574  # 1 megabyte - 1.

        version = version or "MQTTv50"
        if version not in ("MQTTv50", "MQTTv311"):
            raise YomboWarning(f"version must be one of: MQTTv50, MQTTv311 Got: {version}", 201, "new", "mqtt")

        self.client_connections[client_id] = MQTTClient(
            self, client_id=client_id, hostname=hostname, port=port, username=username, password=password,
            password2=password2, use_ssl=use_ssl, version=version, keepalive=keepalive, session_expiry=session_expiry,
            receive_maximum=receive_maximum, user_property=user_property,
            last_will=last_will, maximum_packet_size=maximum_packet_size, on_message_callback=on_message_callback,
            subscribe_callback=subscribe_callback, unsubscribe_callback=unsubscribe_callback,
            connected_callback=connected_callback, disconnected_callback=disconnected_callback,
            error_callback=error_callback)

        client = self.client_connections[client_id]
        logger.debug("mqtt client: created: {client}", client=client)
        yield client.connect()
        return client

    def subscribe(self, topic, **kwargs):
        """
        Subscribe to a topic.

        :param topic:
        :param kwargs:
        :return:
        """
        self.client.subscribe(topic, **kwargs)

    def unsubscribe(self, topic, **kwargs):
        """
        Unsubscribe to a topic.

        :param topic:
        :param kwargs:
        :return:
        """
        self.client.unsubscribe(topic, **kwargs)
