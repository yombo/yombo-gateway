# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
Handles incoming connections from remote controllers. This allows remote
applications to send direct messages to this gateway.

Once a remote client is authenticated, all system broadcast messages
(Commands, Status) are sent to the client.

.. note::

  Netstrings (http://cr.yp.to/proto/netstrings.txt and
  http://en.wikipedia.org/wiki/Netstring) are used to parse/split
  the messages up. When communicating with the controller, netstrings
  must be used.

.. warning::

  Module developers and users should not access any of these functions
  or variables.  This is listed here for completeness. Use a
  :mod:`helpers` function to get what is needed.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""
from base64 import b64encode, b64decode
import json
import time
import re

from yombo.core.library import YomboLibrary
from twisted.protocols import basic
from twisted.python import log
from twisted.internet import reactor, protocol
from twisted.internet.protocol import ServerFactory

from yombo.core import getComponent
from yombo.core.auth import generateToken, validateNonce, checkToken
from yombo.core.exceptions import AuthError, GWCritical
from yombo.core.helpers import getConfigValue, setConfigValue, generateRandom, getUserGWToken, generateUUID
from yombo.core.log import getLogger
from yombo.core.message import Message

logger = getLogger('library.listener')

DID_CONTROL = 1
# 1 - Network connection control commands such as saying "goodbye" to drop
# the connection. Used to address network functions.

DID_CONF = 2
#2 - Used for configuration processing. Add, update, delete configurations.

DID_ALERTS = 3
#3 - Deliver alerts for display on screen. Provides the ability to display alert
#pop-ups or add to the notification stack.

DID_APPCMD = 4
#4 - Controller application commands - Controlling various aspects of the
#remote controller application.

DID_DIRECT = 10
#10 - Typically from Controller Apps to address Yombo Gateway libraries and
#resources. Provides the ability to send commands directly to an Yombo Gateway
#library and avoids yombo.lib.Controller_cmd SQLite lookups.

DID_YOMBOSRV_RESOURCE = 11
#11 - Typically from Controller apps to address a yombo.svc resource. None
#have been defined yet.

class ListenerProtocol(basic.NetstringReceiver):
    """
    Protocol for remote/mobile applications to communicate directly with
    the gateway.

    The communication protocol uses standard Yombo Messages to communicate.
    However, netstrings http://cr.yp.to/proto/netstrings.txt are used as a
    wrapper to separate yombo messages.
    """
    def __init__(self):
        self._Name = "listener.protocol"
        self._FullName = "yombo.gateway.lib.listener.protocol"

        self.protocol_version = "1.0"
        self.min_protocol_version = "1.0"
        self.authenticated = False
        self.snonce = generateRandom()
        self.session = generateRandom(length=24)

        self.badStringCount = 0
        self.lastValidMsg = 0
        self.username = None

        self.gwuuid = getConfigValue("core", "gwuuid")

    def connectionMade(self):
        """
        Called when a new connection is recieved from a client.
        """
        logger.info("Got new client! Sending greeting")
        gwuuidtoken = generateToken(self.snonce, self.gwuuid)
        outline = {'protocol_version': self.protocol_version, 'min_protocol_version': self.min_protocol_version, 'snonce': self.snonce, 'gwuuid': gwuuidtoken, 'cmd': 'authrequest'}
        self.sendMessage(outline)

    def connectionLost(self, reason):
        """
        Called when connection to client is lost.

        :param reason: Reason for connection was closed.
        :type msgOrigin: string
        """
        logger.info("Lost a client! Removing from pool.")
        if self.authenticated:
            del self.factory.gwclients[self.session]
            del self.factory.users[self.username]
            del self.factory.appdeviceuuid[self.appdeviceuuid]

    def sendMessage(self, message):
        """
        Send message to remote client.  Message can be either a yombo message or a dict.
        Developers should use the L{Message} class to deliver a message to a remote client.

        :param msg: A dictionary of the message to send TO the yombo server.
        :type msg: dict
        """
        logger.trace("send to yombo: %s", message)
        if type(message) is dict:
            json_string = json.dumps(message)
            self.sendString(json_string)
        else:
            json_string = json.dumps(message.dumpToExternal())
            self.sendString(json_string)

    def stringReceived(self, string):
        """
        Received a string from a remote client. At this point, it's not at a point
        that we can understand.  It needs to be processed to a JSON and then to a
        Message.

        This is a JSON string. Processing order:
        1) If not authed, then send the packet to the auth function.
        2) Else, create a message from 'string', and tell it to send itself.

        :param string: Sent from the remote client.
        :type string: string
        """
        msg = None
        logger.info("Got listener string..")
        try:
            msg = json.loads(string)
        except ValueError, e:
            if self.authenticated == False:
                logger.warning("Client sent an invalid json message, disconnecting due to non-auth.")
                self.transport.write("{'error': 'Invalid syntax. Good bye.'}")
                self.transport.loseConnection()
            else:
                self.badStringCount = self.badStringCount + 1
                if self.badStringCount > 5:
                  logger.warning("Client sent an invalid json message, disconnecting due too many bad strings.")
                  self.transport.write("{'error': 'You sent too many bad messages. Good bye.'}")
                  self.transport.loseConnection()
                else:
                  logger.warning("Client sent an invalid json message, discarding bad string")
                  self.transport.write("{'error': 'Invalid JSON syntax.'}")
            return

        if self.authenticated == False:
            try:
                self.doAuth(msg)
            except AuthError, e:
                self.sendString("%s" % e)
                self.transport.loseConnection()
                logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                logger.error("%s" % e)
                logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            except GWCritical, e:
                logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                logger.error("%s" % e)
                logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                self.transport.loseConnection()
                e.exit()
        else:
            logger.trace("got message: %s", msg)

        try:            
            message = Message(msg)
            if message.msgType == 'control':
                if message.payload['ping']:
                  self.pong(msg)
            
            self.lastValidMsg = int(time.time())
            message.send()
        except:
            logger.warning("Message couldn't be created and/or sent due to error")

    def doAuth(self, msg):
        """
        Responsible for completing the authentication phase of the connection.

        The authentication phase validates the remote user and the remote user will need to
        validate that it's talking to a valid gateway. This is performed without reveling
        the actual credentials to each other using nonces.

        If authentication fails, an AuthError is raised.

        It validates the users gwtoken (gateway authentication token). If the token isn't
        local, it will send a request to Yombo service for the gw token.

        :param msg: A dictionary of the message sent from the remote client. We don't use
            full message object internally in the auth phase.
        :type msg: dict
        """
        if "error" in msg:
            logger.error("A critical error occuring during authentication.")
            logger.error("Reason: %s", msg["error"])
            raise AuthError("Authentication to client failed.", 5100)
        if "cmd" not in msg:
            raise AuthError("Invalid message packet during auth.", 1001)

        self._authState0(msg)


    def _authState0(self, msg):
        if "cmd" not in msg:
            self.transport.write("{'error': 'No authresponse.'}")
            logger.info("Protocol error, no auth response. Dropping.  %s", msg)
            reactor.callLater(.5, self.transport.loseConnection)
            return

        if msg.get('cmd') != "authresponse":
            self.transport.write("{'error': 'No authresponse.'}")
            logger.info("Protocol error, didn't get authresponse. Dropping.")
            reactor.callLater(.5, self.transport.loseConnection)
            return

        if "username" not in msg:
            logger.warning("Client didn't provide a username.  Dropping.")
            self.transport.write("{'error': 'No username.'}")
            reactor.callLater(.5, self.transport.loseConnection)
            return

        if "gwtokenid" not in msg:
            logger.warning("Client didn't provide a username.  Dropping.")
            self.transport.write("{'error': 'No username.'}")
            reactor.callLater(.5, self.transport.loseConnection)
            return

        if "authtoken" not in msg:
            logger.warning("Client didn't provide an authtoken.  Dropping.")
            self.transport.write("{'error': 'No authtoken.'}")
            reactor.callLater(.5, self.transport.loseConnection)
            return

        if "appdeviceuuid" not in msg:
            logger.warning("Client didn't provide an appdeviceuuid.  Dropping.")
            self.transport.write("{'error': 'No application device UUID.'}")
            reactor.callLater(.5, self.transport.loseConnection)
            return

        if "cnonce" not in msg:
            logger.warning("Client didn't provide a cnonce.  Dropping.")
            self.transport.write("{'error': 'No cnonce found.'}")
            reactor.callLater(.5, self.transport.loseConnection)
            return

        if validateNonce(msg['cnonce']) == False:
            logger.warning("Client didn't provide a valid cnonce.  Dropping.")
            self.transport.write("{'error': 'Invalid cnonce.'}")
            reactor.callLater(.5, self.transport.loseConnection)
            return

        if re.match('^[\w-]+$', msg['appdeviceuuid']) is None:
            logger.warning("Client provided a malformed appdeviceuuid.  Dropping.")
            self.sendMessage({'error': 'Invalid appdeviceuuid.'})
            self.transport.loseConnection()
            return

        if re.match('^[\w-]+$', msg['gwtokenid']) is None:
            logger.warning("Client provided a mailformed gwtokenid.  Dropping.")
            self.sendMessage({'error': 'Invalid gwtokenid.'})
            self.transport.loseConnection()
            return

        if "protocolversion" not in msg:
            logger.warning("Client didn't provide a valid protocol version.  Dropping.")
            self.transport.write("{'error': 'Invalid or missing protocol version.'}")
            reactor.callLater(.5, self.transport.loseConnection)
            return

        tokeninfo = getUserGWToken(msg['username'], msg['gwtokenid'], True)
        if isinstance(tokeninfo, dict):
           if checkToken(self.authMsg['authtoken'], tokeninfo['gwtoken'], self.snonce, self.auth['cnonce']):
              logger.info('Client auth is ok.')

              self.username = msg['username']
              self.appdeviceuuid = msg['appdeviceuuid']  #@todo: send this to pysrv for auth record keeping / user warning
              self.peerIP = self.transport.getPeer().host
              self.authenticated = True

              outline = {'cmd' : "authok"}
              logger.info('authstate0 sending: %s', outline)
              self.sendMessage(outline)

              self.factory.gwclients[self.session] = self
              self.factory.users[self.usernamesession] = self.session
              self.factory.gwclients[self.appdeviceuuid] = self.session
              return

        logger.warning("Client auth is bad.")
        outline = {'cmd' : "authfailed"}
        self.sendMessage(outline)
        self.transport.loseConnection()

    def shutDown(self):
        msg = {'msgOrigin'      : "yombo.gateway.lib.listener",
               'msgDestination' : "remoteapp:%s" % self.appdeviceuuid,
               'msgType'        : "control",
               'msgUUID'        : str(generateUUID()),
               'payload'        : {'cmd':'shutdown'},
              }
        logger.debug("1::: %s", msg)
        self.sendMessage(msg)
        reactor.callLater(1, self.transport.loseConnection)

    def ping(self):
        """
        Send a ping message to client to see if it's alive.
#@todo: If no response within 10 (??) seconds, drop connection.
        """
        msg = {'msgOrigin'      : "yombo.gateway.lib.listener",
               'msgDestination' : "remoteapp:%s" % self.appdeviceuuid,
               'msgType'        : "control",
               'msgStatus'      : "new",
               'msgUUID'        : str(generateUUID()),
               'payload'        : {'cmd':'ping'},
              }
        self.sendMessage(msg)

    def pong(self, msg):
        """
        Response to a ping message.
        """
        msg = {'msgOrigin'      : "yombo.gateway.lib.listener",
               'msgDestination' : "remoteapp:%s" % self.appdeviceuuid,
               'msgType'        : "control",
               'msgStatus'      : "reply",
               'msgUUID'        : msg['msgUUID'],
               'payload'        : {'cmd':'pong'},
              }
        self.sendMessage(msg)

    def controllerBroadcast(self, message):
        logger.info("Sending message to all:", message)
        for c in self.factory.clients:
            c._sendString(message)

class ListenerFactory(ServerFactory):
    protocol = ListenerProtocol #this configures the protocol, and sets self.factory inside the protocol

    def __init__(self):
      self.gwclients = {}
      self.users = {}
      self.appdeviceuuid = {}

      logger.trace('Listener Factory Init')

    def shutDown(self):
        for client in self.gwclients:
            client.shutDown()

    def sendToUsername(self, username, msg):
        if username in self.users:
          self.gwclient[self.users[username]].sendMessage(msg)
        else:
          msg.getReply(msgStatus="done", msgStatusExtra="User not logged in here.")


#    def broadcast(self, outgoing

    def startFactory(self):
        pass

    def stopFactory(self):
        pass


class Listener(YomboLibrary):
    """
    Listener library accepts connections for remote control application.

    This can be used as an API to various remote control applications.  However, it
    may be easier to implement other API's through module if special use cases are
    needed. All gateway functions can be accessed through this API.
    """
    def _init_(self, loader):
        self._Name = "listener"
        self._FullName = "yombo.gateway.lib.listener"

        self.loader = loader
        self.clients = []
        self.myreactor = None

    def _load_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass

    def _start_(self):
        #@TODO: Houstin, uhh, is anyone else listening to this?
        # GET SSL!!
        
        self.myfactory = ListenerFactory()
        controllerPort = int(getConfigValue("listner", "port", 8443))
        self.myreactor = reactor.listenTCP(controllerPort, self.myfactory)

    def _stop_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """

    def _unload_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        if hasattr(self, 'myreactor') and self.myreactor != None:
          self.myreactor.stopListening()

