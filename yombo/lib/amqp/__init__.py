# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `AMQP @ Library Documentation <https://yombo.net/docs/libraries/amqp>`_

All AMQP connetions are managed by this library. To create a new connection use the
:py:meth:`self._AMQP.new() <AMQP.new>` function to create a new connection. This will return a
:class:`AMQPClient` instance which allows for creating exchanges, queues, queue bindings,
and sending/receiving messages.

To learn more about AMQP, see the `RabbitMQ Tutorials <https://www.rabbitmq.com/getstarted.html>`_.

Yombo Gateway interacts with Yombo servers using AMQPYombo which depends on this library.

.. seealso::

   The :doc:`mqtt library </lib/mqtt>` can connect to MQTT brokers, this a light weight message broker.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

.. versionchanged:: 0.24

    Removed tracking correlations and duplicat message checking. This is now handled within AMQPYombo.

:copyright: Copyright 2015-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/amqp/__init__.html>`_
"""
# Import python libraries
from typing import Callable, ClassVar, List, Optional, Type, Union

# Import twisted libraries

# Import Yombo libraries
from yombo.constants.amqp import KEEPALIVE, PREFETCH_COUNT
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.lib.amqp.amqpclient import AMQPClient
from yombo.mixins.parent_storage_accessors_mixin import ParentStorageAccessorsMixin
from yombo.utils import random_string

logger = get_logger("library.amqp")


class AMQP(YomboLibrary, ParentStorageAccessorsMixin):
    """
    Base, or root class that manages all AMQP connections.
    """
    client_connections: ClassVar[dict] = {}
    _storage_attribute_name: ClassVar[str] = "client_connections"
    _storage_attribute_sort_key: ClassVar[str] = "client_id"

    def _unload_(self, **kwargs):
        """
        Force disconnects all AMQP clients.

        :param kwargs:
        :return:
        """
        logger.debug("shutting down amqp clients...")
        for client_id, client in self.client_connections.items():
            if client.is_connected:
                try:
                    client.disconnect()  # this tells the factory to tell the protocol to close.
                except:
                    pass

    def check_callbacks(self, callbacks: Union[Callable, List[Callable]], callback_type: str) -> List[Callable]:
        """
        Checks if callbacks are valid. Ensures the callbacks are within a list.

        :param callbacks: A single or list of callbacks.
        :param callback_type: A string label for error output.
        :return:
        """
        if callbacks is None:
            return None

        if isinstance(callbacks, list) is False:
            callbacks = [callbacks]
        for callback in callbacks:
            if callable(callback) is False:
                raise YomboWarning(f"If {callback_type} is set, all items must be be callable.")
        return callbacks

    def new(self, hostname: Optional[str] = None, port: Optional[int] = None, virtual_host: Optional[str] = None,
            username: Optional[str] = None, password: Optional[str] = None, use_ssl: Optional[bool] = None,
            connected_callbacks: Optional[Callable] = None, disconnected_callbacks: Optional[Callable] = None,
            error_callbacks: Optional[Callable] = None, client_id: Optional[str] = None,
            keepalive: Optional[int] = None, prefetch_count: Optional[int] = 10,
            critical_connection: Optional[bool] = None, _request_context: Optional[str] = None,
            _authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None) -> AMQPClient:
        """
        Creates a new :py:class:AMQPClient instance. It will not auto-connect, just simply call the connect method
        when you're ready for the instance to start connecting. It will continue to attempt to connect if connection
        is not initially made or connection is dropped. It implements an auto-backup feature so as not to overload
        the server.  For example, it will make connection attempts pretty fast, but will increase the rate of
        connection attempts of time.

        For the connection details, defaults will use the local mosquitto broker.

        :param hostname: IP address or hostname to connect to.
        :param port: Port number to connect to.
        :param virtual_host: AMQP virtual host name to connect to.
        :param username: Username to connect as. Use "" to not use a username & password.
        :param password: Password to to connect with. Use "" to not use a password.
        :param use_ssl: Use SSL when attempting to connect to server, default is True.
        :param connected_callbacks: method - If you want a function called when connected to server.
        :param disconnected_callbacks: method - If you want a function called when disconnected from server.
        :param error_callbacks: method - A function to call if something goes wrong.
        :param client_id: (default - random) - A client id to use for logging.
        :param keepalive: (default 60) - How many seconds a ping should be performed if there's not recent
          traffic.
        :param prefetch_count: (default 10) - How many outstanding messages the client should have at any
          given time.
        :param critical_connection: If True and unable to connect to AMQP server, will stop the gateway.
        :param _request_context: Context about the request. Such as an IP address of the source.
        :param _authentication: An auth item such as a websession or authkey.
        :return:
        """
        port = port if port is not None else 5671
        use_ssl = use_ssl if use_ssl is not None else True

        keepalive = keepalive if keepalive is not None else self._Configs.get("amqp.keepalive", KEEPALIVE, False)
        prefetch_count = prefetch_count if prefetch_count is not None else \
            self._Configs.get("amqp.keepalive", PREFETCH_COUNT, False)

        critical_connection = critical_connection if critical_connection is not None else False

        if client_id is None:
            client_id = random_string(length=15)

        if client_id in self.client_connections:
            raise YomboWarning(f"client_id must be unique. Got: {client_id}", 200, "MQTT::new", "mqtt")

        if hostname is None:
            raise YomboWarning("New AMQP client must has a servername or IP to connect to.", 200, "new", "AMQP")

        if port is None:
            raise YomboWarning("New AMQP client must has a port number to connect to.", 200, "new", "AMQP")

        if username is "" or password is "":
            username = None
            password = None

        if virtual_host is None:
            raise YomboWarning("New AMQP client must has a virtual host to connect to.", 200, "new", "AMQP")

        if use_ssl is None:
            raise YomboWarning("New AMQP client must have use_ssl set as True or False..", 200, "new", "AMQP")

        connected_callbacks = self.check_callbacks(connected_callbacks, "connected_callbacks")
        disconnected_callbacks = self.check_callbacks(disconnected_callbacks, "disconnected_callbacks")
        error_callbacks = self.check_callbacks(error_callbacks, "error_callbacks")

        self.client_connections[client_id] = AMQPClient(
            self, client_id=client_id, hostname=hostname, port=port, virtual_host=virtual_host,
            username=username, password=password, use_ssl=use_ssl, connected_callbacks=connected_callbacks,
            disconnected_callbacks=disconnected_callbacks, error_callbacks=error_callbacks,
            keepalive=keepalive, prefetch_count=prefetch_count, critical_connection=critical_connection)
        self._Events.new(event_type="amqp",
                         event_subtype="new",
                         attributes=(client_id, hostname, port, username, use_ssl),
                         _authentication=_authentication if _authentication is not None else self.AUTH_USER)
        return self.client_connections[client_id]
