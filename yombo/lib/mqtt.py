# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For more information see: `MQTT @ Module Development <https://yombo.net/docs/modules/mqtt/>`_

Implements MQTT. It does 2 things:

1) Start an embedded HBMQTT MQTT Broker. This can be disabled.
2) Is allows libraries and modules to connect to MQTT brokers and subscribe to topics.

*Usage**:

.. code-block:: python

   def _init_(self):
       # Create anew connection. Hostname, port, user, password, ssl(True/False) can be specified if connection
       # to anther MQTT server. Otherwise, use the default local one.
       self.my_mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming)  # Create a new connection to the embedded MQTT server.

       # Subscribe to all topics of 'foor/bar/topic' and send them to:  self.mqtt_incoming
       self.my_mqtt.subscribe('foo/bar/topic')
       self.my_mqtt.publish('for/bar/topic/status', 'on')  # publish a message

   def mqtt_incoming(self, topic, payload, qos, retain):
       print "topic: %s" % topic
       print "message: %s" % message


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.11.0

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from __future__ import print_function
import yaml
from os.path import abspath
from os import environ
import crypt
import random
import string
from collections import deque
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
import yaml

# Import twisted libraries
from twisted.internet.ssl import ClientContextFactory
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, returnValue

# 3rd party libraries
from yombo.ext.mqtt.client.factory import MQTTFactory
from yombo.ext.mqtt.client.pubsubs import MQTTProtocol
from yombo.ext.mqtt import v311
from yombo.ext.mqtt.error import ProfileValueError

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.lib.webinterface.auth import require_auth
from yombo.utils import random_string, sleep

logger = get_logger('library.mqtt')

def sha512_crypt(password, salt=None, rounds=None):
    """
    Used for generating a crypted version for hbmqtt pasword file.

    :param password:
    :param salt:
    :param rounds:
    :return:
    """
    if salt is None:
        rand = random.SystemRandom()
        salt = ''.join([rand.choice(string.ascii_letters + string.digits)
                        for _ in range(8)])
    prefix = '$6$'
    if rounds is not None:
        rounds = max(1000, min(999999999, rounds or 5000))
        prefix += 'rounds={0}$'.format(rounds)
    return crypt.crypt(password, prefix + salt)

class MQTT(YomboLibrary):
    """
    Manages MQTT broker and client connections.
    """
    client_enabled = True

    def _init_(self):
        """
        Builds the configuration and password files. Also starts the MQTT broker if enabled.

        :return:
        """
        self.client_connections = {}
        self.hbmqtt_config_file = abspath('.') + "/usr/etc/hbmqtt.yaml"
        self.hbmqtt_pass_file = abspath('.') + "/usr/etc/hbmqtt.pw"
        self.client_enabled = self._Configs.get('mqtt', 'client_enabled', True)
        self.server_enabled = self._Configs.get('mqtt', 'server_enabled', True)
        self.server_max_connections = self._Configs.get('mqtt', 'server_max_connections', 1000)
        self.server_timeout_disconnect_delay = self._Configs.get('mqtt', 'server_timeout_disconnect_delay', 2)
        self.server_listen_ip = self._Configs.get('mqtt', 'server_listen_ip', '127.0.0.1')
        self.server_listen_port_nonsecure = self._Configs.get('mqtt', 'server_listen_port_nonsecure', 1883)
        self.server_listen_port_ssl = self._Configs.get('mqtt', 'server_listen_port_ssl', 8883)
        self.server_listen_port_websockets = self._Configs.get('mqtt', 'server_listen_port_websockets', 8081)
        self.server_allow_anonymous = self._Configs.get('mqtt', 'server_allow_anonymous', False)

        self.mqtt_local_client = None
        self.yombo_mqtt_password = self._Configs.get('mqtt_users', 'yombo', random_string(length=16))

        if not self.server_enabled:
            return

        yaml_config = {
            'listeners': {
                'default': {
                    'max_connections': self.server_max_connections,
                    'type': 'tcp'
                },
            },
            'timeout_disconnect_delay': self.server_timeout_disconnect_delay,
            'auth': {
                'password-file': self.hbmqtt_pass_file,
                'allow-anonymous': self.server_allow_anonymous,
            },
        }

        if self.server_listen_port_nonsecure > 0:
            yaml_config['listeners']['yombo-tcp-1-nonsecure'] = {
                'bind': self.server_listen_ip + ":" + str(self.server_listen_port_nonsecure),
            }
        if self.server_listen_port_ssl > 0:
            yaml_config['listeners']['yombo-tcp-2-ssl'] = {
                'bind': self.server_listen_ip + ":" + str(self.server_listen_port_ssl),
            }
        if self.server_listen_port_websockets > 0:
            yaml_config['listeners']['yom' \
                                     'bo-tcp-3-websocket'] = {
                'bind': self.server_listen_ip + ":" + str(self.server_listen_port_websockets),
                'type': 'ws',
            }

        with open(self.hbmqtt_config_file, 'w') as yaml_conf_file:
            yaml_conf_file.write( yaml.dump(yaml_config, default_flow_style=False))

        cfg_users = self._Configs.get('mqtt_users', '*')

        if cfg_users is not None:
            with open(self.hbmqtt_pass_file, 'w') as mqtt_pw_file:
                print("# File automatically generated by Yombo Gateway. Edits will be lost.", file=mqtt_pw_file)
                for username, password in cfg_users.iteritems():
                    print("%s:%s" % (username, sha512_crypt(password)), file=mqtt_pw_file)

        self.mqtt_server = MQTTServer(self.hbmqtt_config_file)
        command = ['hbmqtt', "-c", self.hbmqtt_config_file]
        self.mqtt_server_reactor = reactor.spawnProcess(self.mqtt_server, command[0], command, environ)


    def _load_(self):
        if self.server_enabled is False:
            logger.info("Embedded MQTT Disabled.")
            return

        # nasty hack..  TODO: remove nasty sleep hack
        return sleep(0.2)

    def _start_(self):
        """
        Just connect with a local client. Can later be used to send messages as needed.
        :return:
        """
        self.mqtt_local_client = self.new()  # System connection to send messages.
        # self.test()  # todo: move to unit tests..  Todo: Create unit tests.. :-)

    def _stop_(self):
        """
        Stops the client connections and shuts down the MQTT server.
        :return:
        """
        logger.debug("shutting down mqtt clients...")
        for client_id, client in self.client_connections.iteritems():
            logger.debug("in loop to try to stop mqtt client: %s" % client_id)
            try:
                logger.debug("telling client to say goodbye... %s" % client_id)
                client.factory.stopTrying(

                )  # Tell reconnecting factory to don't attempt connecting after disconnect.
                client.factory.protocol.disconnect()
                client.factory.protocol.close()
            except:
                pass
        return sleep(0.1)

    def _unload_(self):
        self.mqtt_server.shutdown()

    #def _unload_(self):
        #self.mqtt_server.transport.signalProcess(signal.SIGKILL)

    def _webinterface_add_routes_(self, **kwargs):
        """
        A demonstration of how to add menus and provide function calls to the web interface library. This would
        normally be used by modules and not libaries, this is here for documentation purposes.
        :param kwargs:
        :return:
        """
#        if self.loadedLibraries['atoms']['loader.operation_mode'] = val
        if self.client_enabled:
            return {
                'nav_side': [
                    {
                    'label1': 'Tools',
                    'label2': 'MQTT',
                    'priority1': None,  # Even with a value, 'Tools' is already defined and will be ignored.
                    'priority2': 10000,
                    'icon': 'fa fa-wrench fa-fw',
                    'url': '/tools/mqtt',
                    'tooltip': '',
                    'opmode': 'run',
                    },
                ],
                'routes': [
                    self.web_interface_routes,
               ],
            }

    def web_interface_routes(self, webapp):
        """
        Adds routes to the webinterface module. Normally, a module will store any template files within the module,
        but for this example, we will store the templates within the webinterface module.

        :param webapp: A pointer to the webapp, it's used to setup routes.
        :return:
        """
        with webapp.subroute("/") as webapp:
            @webapp.route("/tools/mqtt")
            @require_auth()
            def page_tools_mqtt(webinterface, request, session):
                page = webinterface.webapp.templates.get_template(webinterface._dir + 'pages/mqtt/index.html')
                return page.render(alerts=webinterface.get_alerts(),
                                   )

                return "These stairs lead to the lair of beasts of the mqtt world: "

            @webapp.route("/api/v1/mqtt")
            @require_auth()
            @inlineCallbacks
            def api_v1_mqtt(webinterface, request, session):
                topic = request.args.get('topic')[0]  # please do some validation!!
                message = request.args.get('message')[0]  # please do some validation!!
                qos = int(request.args.get('qos')[0])  # please do some validation!!

                try:
                    yield self.mqtt_local_client.publish(topic, message, qos)
                    results = {'status':200, 'message': 'MQTT message sent successfully.'}
                    returnValue(json.dumps(results))
                except Exception, e:
                    # print("whathahtahthat %s" % e)
                    results = {'status':500, 'message': 'MQTT message count not be sent.'}
                    returnValue(json.dumps(results))


    def new(self, server_hostname=None, server_port=None, username=None, password=None, ssl=False,
            mqtt_incoming_callback=None, mqtt_connected_callback=None, mqtt_connection_lost_calback=None,
            mqtt_connection_lost_callback=None, will_topic=None, will_message=None, will_qos=0, will_retain=None,
            clean_start=True, version=v311, keepalive=0, client_id=None):
        """
        Create a new connection to MQTT. Don't worry, it's designed for many many connections. Leave all
        connection details blank or all completed. Blank will connect the MQTT client to the default Yombo
        embedded MQTT Server: HBMQTT

        .. code-block:: python

           self.my_mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming, client_id='my_client_name')
           self.mqtt.subscribe("yombo/devices/+/get")  # subscribe to a topic. + is a wilcard for a single section.

        :param on_connect_callback: Callback to a method when the MQTT connection is up. Used for notifications or status updates.
        :param server_hostname: Broker to connect to. If not set, uses the local broker.
        :param server_port: Port to connect to, default is the non-secure port.
        :param user: User to connect as. Default is the local yombo user.
        :param password: Password to use for connection. Default is the local yombo user password.
        :param ssl: Use SSL. Default is False. It's recommended to use SSL when connecting to a remote server.
        :return:
        """
        if not self.client_enabled:
            logger.warn("MQTT Clients Disabled. Not allowed to connect.")
            return

        if client_id is None:
            client_id = random_string(length=10)
        if client_id in self.client_connections:
            logger.warn("client_id must be unique. Got: %s" % client_id)
            raise YomboWarning ("client_id must be unique. Got: %s" % client_id, 'MQTT::new', 'mqtt')

        if server_hostname is None:
            server_hostname = self.server_listen_ip

        if server_port is None:
            server_port = self.server_listen_port_nonsecure

        if username is None:
            username = 'yombo'

        if password is None:
            password = self.yombo_mqtt_password

        if mqtt_incoming_callback is not None:
            if callable(mqtt_incoming_callback) is False:
                raise YomboWarning("If mqtt_incoming_callback is set, it must be be callable.", 200, 'new', 'Devices')

        if mqtt_connected_callback is not None:
            if callable(mqtt_connected_callback) is False:
                raise YomboWarning("If mqtt_connected_callback is set, it must be be callable.", 201, 'new', 'Devices')

        self.client_connections[client_id] = MQTTClient(self, client_id, server_hostname, server_port, username,
            password, ssl, mqtt_incoming_callback, mqtt_connected_callback, mqtt_connection_lost_callback, will_topic,
            will_message, will_qos, will_retain, clean_start, version, keepalive)
        return self.client_connections[client_id]

    def test(self):
#        self.local_mqtt_client_id = random_string(length=10)

        self.mqtt_test_connection = self.new(self.server_listen_ip,
            self.server_listen_port_nonsecure, 'yombo', self.yombo_mqtt_password, False,
            self.test_mqtt_in, self.test_on_connect )

        self.mqtt_test_connection.subscribe("yombo/#")

        self.sendDataLoop = LoopingCall(self.test_send_data)
        self.sendDataLoop.start(5, True)

    def test_on_connect(self):
        print("in on connect in library...")
        self.test_send_data()

    def test_send_data(self):
        print("mqtt sending test package")
        self.mqtt_test_connection.publish("yombo/devices/asdf/asdf", 'open')

    def test_mqtt_in(self, topic, payload, qos, retain):
        print("i got this: %s / %s" % (topic, payload))

class MQTTClient(object):
    """
    A helper class for MQTT. This class is returned back to the any module that request a new MQTT client connection.

    .. code-block:: python

       self.my_mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming, client_id='my_client_name')
       self.mqtt.subscribe("yombo/devices/+/get")  # subscribe to a topic. + is a wilcard for a single section.
    """
    def __init__(self, mqtt_library, client_id, server_hostname, server_port, username=None, password=None, ssl=False,
                 mqtt_incoming_callback=None, mqtt_connected_callback=None, mqtt_connection_lost_callback=None,
                 will_topic=None, will_message=None, will_qos=0, will_retain=None, clean_start=True, version=v311,
                 keepalive=0):
        """
        Creates a new client connection to an MQTT broker.
        :param mqtt_library: A reference to the MQTT library above.
        :param server_hostname: Broker to connect to. If not set, uses the local broker.
        :param server_port: Port to connect to, default is the non-secure port.
        :param client_id: Client ID, either supplied from the calling library or random.
        :param username: User to connect as. Default is the local yombo user.
        :param password: Password to use for connection. Default is the local yombo user password.
        :param ssl: Use SSL. Default is False. It's recommended to use SSL when connecting to a remote server.
        :param mqtt_incoming_callback: Callback to send incomming messages to.
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
        self.ssl = ssl
        self.connected = False
        self.mqtt_library = mqtt_library
        self.client_id = client_id

        self.incoming_duplicates = deque([], 150)

        self.mqtt_incoming_callback = mqtt_incoming_callback
        self.mqtt_connected_callback = mqtt_connected_callback
        self.mqtt_connection_lost_callback = mqtt_connection_lost_callback

        self.send_queue = deque() # stores any received items like publish and subscribe until fully connected

        self.factory = MQTTTYomboFactory(profile=MQTTFactory.PUBLISHER | MQTTFactory.SUBSCRIBER)
        self.factory.noisy = False  # turn off Starting/stopping message
        self.factory.mqtt_client=self
        self.factory.username = username
        self.factory.password = password
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

        if ssl:
            self.my_reactor = reactor.connectSSL(server_hostname, server_port, self.factory,
                                                 ClientContextFactory())
        else:
            self.my_reactor = reactor.connectTCP(server_hostname, server_port, self.factory)

    @inlineCallbacks
    def publish(self, topic, message, qos=0, retain=False):
        """
        Publish a message.

        :param topic: 'yombo/devices/bedroom_light/command'
        :param message: string - Like 'on'
        :param qos: 0, 1, or 2. Default is 0.
        :return:
        """
        # print("publishing (%s): %s" % (topic, message))
        if self.connected:
            # print("publishing now")
            yield self.factory.protocol.publish(topic=topic, message=message, qos=qos)
            self.mqtt_library._Statistics.increment("lib.mqtt.client.publish", bucket_size=10, anon=True)
        if self.connected:
            self.send_queue.append({
                'type': 'publish',
                'topic': topic,
                'message': message,
                'qos': qos,
                'retain': False,
            })

    @inlineCallbacks
    def subscribe(self, topic, qos=1):
        """
        Subscribe to a topic. Inlucde the topic like 'yombo/myfunky/something'
        :param topic: string or list of strings to subscribe to.
        :param callback: a point to a function to be called when data arrives.
        :param qos: See MQTT doco for information. We handle duplicates, no need for qos 2.
        :return:
        """
        if self.connected:
            yield self.factory.protocol.subscribe(topic, qos)
            self.mqtt_library._Statistics.increment("lib.mqtt.client.subscribe", bucket_size=10, anon=True)
        else:
            self.send_queue.append({
                'type': 'subscribe',
                'topic': topic,
                'qos': qos,
            })

    @inlineCallbacks
    def unsubscribe(self, topic):
        """
        Unsubscribe from a topic.
        :param topic:
        :return:
        """
        if self.connected:
            yield self.factory.protocol.unsubscribe(topic)
            self.mqtt_library._Statistics.increment("lib.mqtt.client.unsubscribe", bucket_size=10, anon=True)
        if self.connected:
            self.send_queue.append({
                'type': 'unsubscribe',
            })

    @inlineCallbacks
    def mqtt_connected(self):
        """
        Call when mqtt client is connected. Subscribes, unsubscribes, and publises any queued messages. Afterwards,
        if the client has a connected callback, will also call that.
        :return:
        """
        logger.debug("client ID connected: {client_id}", client_id=self.client_id)
        self.connected = True
        while True:
            try:
                item = self.send_queue.popleft()
                logger.debug("mqtt_connected. Item: {item}", item=item)
                if item['type'] == 'subscribe':
                    yield self.subscribe(item['topic'], item['qos'])
                elif item['type'] == 'unsubscribe':
                    yield self.unsubscribe(item['topic'])
                if item['type'] == 'publish':
                    yield self.publish(item['topic'], item['message'], qos=item['qos'], retain=item['retain'])
            except IndexError:
                break

        if self.mqtt_connected_callback:
            self.mqtt_connected_callback()

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

#        print("client ID incomin: %s" % self.client_id)
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
            raise YomboWarning("Recieved MQTT message, but no callback defined, no where to send.", 'direct_incoming',
                               'mqtt')

    def client_connectionLost(self, reason):
        """
        Called when the connection to the broker is lost. Calls a client connection lost callbacks if defined.
        :param reason:
        :return:
        """
        logger.info("Lost connection to HBMQTT Broker: {reason}", reason=reason)
        self.connected = False
        if self.mqtt_connection_lost_callback:
            self.mqtt_connection_lost_callback()


class MQTTYomboProtocol(MQTTProtocol):
    """
    Makes minor tweaks to the MQTTProtocol for use with Yombo.
    """
    def connectionMade(self):  # Empty through stack of twisted and MQTT library
        #
        # print("connectionMade!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # call the mqtt_client.mqtt_connectin function once fully connected. This allows to send queued messages.
        self.onMqttConnectionMade = self.factory.mqtt_client.mqtt_connected
        self.connect("Yombo-%s" % self.factory.mqtt_client.client_id, keepalive=self.factory.keepalive,
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


class MQTTServer(protocol.ProcessProtocol):
    def __init__(self, config_file):
        self.config_file = config_file

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
