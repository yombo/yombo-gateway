"""
Implements MQTT. It does 2 things:

1) Start an embedded HBMQTT MQTT Broker. This can be disabled.
2) Is allows libraries and modules to connect to MQTT brokers and subscribe to topics.

*Usage**:

.. code-block:: python

   def show_mqtt_message(self, topic, message):
       print "topic: %s" % topic
       print "message: %s" % message

   my_mqtt = self._MQTT.new()  # Create a new connection to the embedded MQTT server.
   my_mqtt.subscribe('foo/bar/topic', self.show_mqtt_message)  # now all topics with 'foor/bar/topic' will be sent to show_mqtt_message

..versionadded:: 0.11.0
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from __future__ import print_function
import yaml
from os.path import abspath
from os import environ
import signal
import crypt
import random
import string
from collections import deque

# Import twisted libraries
from twisted.internet.ssl import ClientContextFactory
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.logger   import (
    Logger, LogLevel, globalLogBeginner, textFileLogObserver,
    FilteringLogObserver, LogLevelFilterPredicate)

# 3rd party libraries
from yombo.ext.mqtt.client.factory import MQTTFactory
from yombo.ext.mqtt.client.pubsubs import MQTTProtocol
from yombo.ext.mqtt import v311
from yombo.ext.mqtt.error import ProfileValueError

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.utils import random_string
from yombo.core.log import get_logger

logger = get_logger('lib.mqtt')

def sha512_crypt(password, salt=None, rounds=None):
    """
    Used for generating a crypted version for hbmqtt pasword file. Will eventually be used for the config file.
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
    Provide a database backed persistent dictionary.
    """
    def _init_(self, loader):
        self.loader = loader
        self.client_connections = {}
        self.hbmqtt_config_file = abspath('.') + "/usr/etc/hbmqtt.yaml"
        self.hbmqtt_pass_file = abspath('.') + "/usr/etc/hbmqtt.pw"
        self.client_enabled = self._Configs.get('mqtt', 'client_enabled', True)
        self.server_enabled = self._Configs.get('mqtt', 'server_enabled', True)
        self.server_listen_ip = self._Configs.get('mqtt', 'server_listen_ip', '0.0.0.0')
        self.server_listen_port_nonsecure = self._Configs.get('mqtt', 'server_listen_port_nonsecure', 1883)
        self.server_listen_port_ssl = self._Configs.get('mqtt', 'server_listen_port_ssl', 1885)
        self.server_listen_port_websockets = self._Configs.get('mqtt', 'server_listen_port_websockets', 8081)

        self.yombo_mqtt_password = self._Configs.get('mqtt_users', 'yombo', random_string(length=16))
        self.yombo_mqtt_password = self._Configs.get('mqtt_users', 'local', random_string(length=5))
        self.server_users = self._Configs.get('mqtt_users', '*')

        if not self.server_enabled:
            return

        yaml_config = {
            'listeners': {
                'default': {
                    'max_connections': 1000,
                    'type': 'tcp'
                },
            },
            'timeout_disconnect_delay': 2,
            'auth': {
                'password-file': self.hbmqtt_pass_file,
#                'allow-anonymous': False,
                'allow-anonymous': True,
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
            yaml_config['listeners']['yombo-tcp-3-websocket'] = {
                'bind': self.server_listen_ip + ":" + str(self.server_listen_port_websockets),
                'type': 'ws',
            }

        with open(self.hbmqtt_config_file, 'w') as yaml_conf_file:
            yaml_conf_file.write( yaml.dump(yaml_config, default_flow_style=False))

        cfg_users = self._Configs.get('mqtt_users', '*')

#        users = [['yombo', self.yombo_mqtt_password]]
        users = []

        if cfg_users is not None:
            for user, password in cfg_users.iteritems():
                users.append([user, password])

        with open(self.hbmqtt_pass_file, 'w') as mqtt_pw_file:
            print("# File automatically generated by Yombo Gateway. Edits will be lost.", file=mqtt_pw_file)
            for user in users:
                print("%s:%s" % (user[0], sha512_crypt(user[1])), file=mqtt_pw_file)

        self.mqtt_server = MQTTServer(self.hbmqtt_config_file)
        command = ['hbmqtt', "-c", self.hbmqtt_config_file]
        self.mqtt_server_reactor = reactor.spawnProcess(self.mqtt_server, command[0], command, environ)

        level = LogLevel.levelWithName('info')
        LLFP = LogLevelFilterPredicate()
        LLFP.setLogLevelForNamespace(namespace='mqtt', level=level)

    def _load_(self):
        if self.server_enabled is False:
            logger.info("Embedded MQTT Disabled.")
            return
        self.local_mqtt_client_id = random_string(length=10)
        self.client_connections[self.local_mqtt_client_id] = self.new(self.server_listen_ip, self.server_listen_port_nonsecure, 'yombo', self.yombo_mqtt_password, False )
#        print("localmqtt_client _id = %s" % self.local_mqtt_client_id)


    def _stop_(self):
#        print("###########################################clientid: %s" % self.local_mqtt_client_id)
#        print("client connectins: %s" % self.client_connections)
#        self.client_connections[self.local_mqtt_client_id].public('yombo/mqtt/status', 'offline')

        for client_id, client in self.client_connections.iteritems():
            client.factory.stopTrying()  # Tell reconnecting factory to don't attempt connecting after disconnect.
            client.factory.protocol.disconnect()
        self.mqtt_server.shutdown()

    #def _unload_(self):
        #self.mqtt_server.transport.signalProcess(signal.SIGKILL)


    def new(self, server_hostname=None, server_port=None, user=None, password=None, ssl=False,):
        """
        Create a new connection to MQTT. Don't worry, it's designed for many many connections. Leave all
        connection details blank or all completed. Blank will connect the MQTT client to the default Yombo
        embedded MQTT Server: HBMQTT

        :param server_hostname:
        :param server_port:
        :param user:
        :param password:
        :param ssl:
        :return:
        """
        if not self.client_enabled:
            logger.warn("MQTT Disabled. Not allowed to connect.")
            raise YomboWarning('MQTT Clients disabled, unable to connect', 'connect', 'mqtt')

        client_id = random_string(length=10)
        self.client_connections[client_id] = MQTTClient(self, server_hostname, server_port, user, password, ssl)

        return self.client_connections[client_id]


class MQTTClient(object):
    def __init__(self, mqtt_library, server_hostname, server_port, user=None, password=None, ssl=False):
        self.server_hostname = server_hostname
        self.server_port = server_port
        self.user = user
        self.password = password
        self.ssl = ssl
        self.connected = False
        self.mqtt_library = mqtt_library

        if server_hostname is None:
           raise YomboWarning("'server_host' is required.", '__init__', 'mqtt::MQTTClient')
        if server_port is None:
           raise YomboWarning("'server_port' is required.", '__init__', 'mqtt::MQTTClient')

        self.factory = MQTTTYomboFactory(profile=MQTTFactory.PUBLISHER | MQTTFactory.SUBSCRIBER)
        self.factory.set_mqtt_client(self)

        if ssl:
            self.my_reactor = reactor.connectSSL(server_hostname, self.server_port, self.factory,
                                                 ClientContextFactory())
        else:
            self.my_reactor = reactor.connectTCP(server_hostname, self.server_port, self.factory)

    def publish(self, topic, message, qos=0):
        """
        Publish a message.

        :param topic: 'yombo/devices/bedroom_light/command'
        :param message: string - Like 'on'
        :param qos: 0, 1, or 2. Default is 0.
        :return:
        """
        self.factory.protocol.publish(topic=topic, message=message, qos=qos)

    def subscribe(self, topic, callback, qos=2):
        """
        Subscribe to a topic. Inlucde the topic like 'yombo/myfunky/something'
        :param topic: string.
        :param callback: a point to a function to be called when data arrives.
        :param qos: See MQTT doco for information.
        :return:
        """
        self.factory.protocol.subscribe(topic, qos)
        self.factory.protocol.setPublishHandler(callback)

    def unsubscribe(self, topic):
        self.factory.protocol.ubsubscribe(topic)


    def client_connectionMade(self):
        self.connected = True
        self.factory.protocol.publish('yombo/service/status', 'online')

    def client_connectionLost(self, reason):
        logger.info("Lost connection to HBMQTT Broker: {reason}", reason=reason)
        self.connected = False


class MQTTYomboProtocol(MQTTProtocol):

    def connectionMade(self):  # Empty through twisted.
#        print("!!!!  connectionMade   !!!!!")
        self.connect("YomboGateway-v1", keepalive=0, version=v311)
        self.factory.mqtt_client.client_connectionMade()

    def _onDisconnect(self, reason):  # defined in MQTTProtocol in connectionLost
#        print("!!!!  connectionLost   !!!!!")
        self.factory.mqtt_client.client_connectionLost(reason)


class MQTTTYomboFactory(MQTTFactory):

    def set_mqtt_client(self, mqtt_client):
        self.mqtt_client = mqtt_client

    def buildProtocol(self, addr):
        if self.profile == self.SUBSCRIBER:
            from yombo.ext.mqtt.client.subscriber import MQTTProtocol
        elif self.profile == self.PUBLISHER:
            from yombo.ext.mqtt.client.publisher import MQTTProtocol
        elif self.profile == (self.SUBSCRIBER | self.PUBLISHER):
            from yombo.ext.mqtt.client.pubsubs import MQTTProtocol
        else:
            raise ProfileValueError("profile value not supported" , self.profile)

        v = self.queuePublishTx.get(addr, deque())
        self.queuePublishTx[addr] = v
        v = self.windowPublish.get(addr, dict() )
        self.windowPublish[addr] = v
        v = self.windowPubRelease.get(addr, dict() )
        self.windowPubRelease[addr] = v
        v = self.windowPubRx.get(addr, dict())
        self.windowPubRx[addr] = v
        v = self.windowSubscribe.get(addr, dict() )
        self.windowSubscribe[addr] = v
        v = self.windowUnsubscribe.get(addr, dict())
        self.windowUnsubscribe[addr] = v

        self.protocol = MQTTYomboProtocol(self, addr)  # Everything above is from mqtt.client.factory
        return self.protocol                           # submitted pull request to get this into source


class MQTTServer(protocol.ProcessProtocol):
    def __init__(self, config_file):
        self.config_file = config_file

    def shutdown(self):
#        self.transport.signalProcess(signal.SIGTERM)
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
