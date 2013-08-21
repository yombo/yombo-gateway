# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
Establishes a connection the Yombo servers for command / data control. This
connection it used for settings, command messages, data traffic control and
authorization, etc, between the gateway and the yombo service.  Without
this connection, nothing can be done. This data stream supports bi-direct,
simultaneous, traffic.

This connection is for text only, gatawaydata library is used for transfering
binary data.

The Yombo service also acts as a router to deliver a :ref:`Message`_ from
remote sources, including remote controllers that couldn't reach the gateway
directly.

Connection should be maintained 100% of the time.  It's easier on the yombo
servers to maintain an idle connection than to keep rasing and dropping
connections.

Depending on the security options the user has selected, it can be used to
transmit real time data to the servers for further processing and event
handling.  See the Yombo privacy policy regarding users data: In short, it's
the users data, Yombo keeps it private.

.. warning::

  Module developers and users should not access any of these function or
  variables.  This is listed here for completeness. Use a :mod:`helpers`
  function to get what is needed.

:TODO: The gateway needs to check for a non-responsive server or
if it doesn't get a response in a timely manor. It should respond
in MS, but it could have died/hung.  Perhaps disconnect and reconnect to
another server? -Mitch
  
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""

import re
import json
from collections import deque

from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols import basic
from twisted.internet import reactor, ssl
from twisted.internet.task import LoopingCall

from yombo.core.auth import generateToken, checkToken, validateNonce
from yombo.core import getComponent
from yombo.core.exceptions import GWCritical, AuthError
from yombo.core.helpers import getConfigValue, setConfigValue, getLocalIPAddress, generateRandom, pgpFetchKey
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
from yombo.core.message import Message

logger = getLogger('library.gatewaycontrol')

class GatewayControlProtocol(basic.NetstringReceiver):
    def __init__(self):
        """
        Setup a few basic settings for the gateway control protocol.
        """
        self.protocolVersion = 3
        self._Name = "gatewaycontrolprotocol"
        self._FullName = "yombo.gateway.lib.gatewaycontrolprotocol"

        self.configUpdate = getComponent('yombo.gateway.lib.ConfigurationUpdate')

    def connectionMade(self):
        """
        Called when a connection is made to the yombo servers.
        """
        self.YomboReconnect = True
        self.authenticated = False
        self.authState = 0
        # Say hello to server.
        self.__cnonce = generateRandom()
        outgoing = {
                    'type' : 'gateway',
                    'protocolversion' : 3,
                    'cnonce' : self.__cnonce,
                    'clientuuid' : getConfigValue("core", "gwuuid"),
                   }
        self.sendMessage(outgoing)        

    def sendMessage(self, msg):
        """
        Send message to Yombo Servers.  Msg needs to be a dict at this point.
        Developers should use the :ref:`Message`_ class to deliver messages to
        the server.

        :param msg: A dictionary of the message to send TO the yombo server.
        :type msg: dict
        """
        if self.authenticated == False:
            themsg = json.dumps(msg)
            logger.trace("sending: %s" % themsg)
            self.sendString(themsg)
            return

        newmsg = { 'msgDestination' : msg['msgDestination'],
                   'msgOrigin'      : msg['msgOrigin'],
                   'data'           : {},
                 }
        del msg['msgDestination']
        del msg['msgOrigin']
        msgItemsSkip = ( 'uuidType', 'uuidSubType', 'notBefore', 'maxDelay')
        for item in msg:
            if item in msgItemsSkip:
                continue
            newmsg['data'][item] = msg[item]

        self.factory.outgoingUUID.append(msg['msgUUID'])

        themsg = json.dumps(newmsg)
        logger.trace("sending: %s" % themsg)
        self.sendString(themsg)

    def stringReceived(self, string):
        """
        Received a string from Yombo Servers. At this point, it's not at a point
        that we can understand.  It needs to be processed to a JSON and then
        possibly to a Message, depending on the destination.

        This is a JSON string. Processing order:
        1) If not authed, then send the packet to the auth function.
        2) If it's a config item, send directly to configurationupdate.py - done for speed.
        3) Else, create a message from 'string', and tell it to send itself.

        :param string: A string sent from the Yombo server.
        :type string: string
        """
        logger.trace("received: %s" % string)
        msg = None
        try:
            msg = json.loads(string)
            self.badStringCount = 0
        except ValueError, e:
            logger.warning("Server sent invalid json. Bad server. Hanging up.")
            self.transport.loseConnection()            

        if not isinstance(msg, dict):
            logger.warning("Received message that is not a dict.")
            self.transport.loseConnection()
            
        if self.authenticated == False:
            try:
                self.doAuth(msg)
            except AuthError, e:
                self.sendString("%s" % e)
                logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                logger.error("%s" % e)
                logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                self.transport.loseConnection()
            except GWCritical, e:
                logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                logger.error("%s" % e)
                logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                self.transport.loseConnection()
                e.exit()
        else:
            # as of Aug 13, 2013 - messages between gateway and server enclose
            # the meat of the message in 'data' portion of message.  This allows
            # the data portion to be signed and/or fully encrypted.

            msgKeys = ('msgOrigin', 'msgDestination', 'data')
            if not all(item in msgKeys for item in msg): # missing message parts. Discard.
              return

            newmsg = { 'msgDestination' : msg['msgDestination'],
                       'msgOrigin' : msg['msgOrigin'],
                     }
            for item in msg['data']:
                newmsg[item] = msg['data'][item]

            msgOriginParts = newmsg['msgOrigin'].split(':')
            msgOriginTypeParts = msgOriginParts[0].split('.')

            if len(msgOriginParts) != 2:
              return logger.warning("GatewayControl dropped packet: Incorrect number of msgOrigin components.")
            if re.match('^[.\w-]+$', msgOriginParts[0]) is None:
              return logger.warning("GatewayControl dropped packet: Invalid characters in message origin.")
            if re.match('^[\w-]+$', msgOriginParts[1]) is None:
              return logger.warning("GatewayControl dropped packet: Invalid characters in message origin.")

            msgDestParts = newmsg['msgDestination'].split(':')
            msgDestTypeParts = msgDestParts[0].split('.')
            if len(msgDestParts) != 2:
              return logger.warning("GatewayControl dropped packet: Incorrect number of msgDestination components.")
            if re.match('^[.\w-]+$', msgDestParts[0]) is None:
              return logger.warning("GatewayControl dropped packet: Invalid characters in message origin.")
            if re.match('^[\w-]+$', msgDestParts[1]) is None:
              return logger.warning("GatewayControl dropped packet: Invalid characters in message origin.")

            msgDest2 = "%s.%s" % (msgDestTypeParts[0], msgDestTypeParts[1])
            if msgDest2 != 'yombo.gateway':
              return self.disconnect("Server trying something wierd.")

            if newmsg['msgType'] == "config":
                self.configUpdate.processConfig(newmsg)
            else:
              # Make sure msg has a msgUUID and that it's not already sent!
              if 'msgUUID' not in newmsg:
                logger.warning("Message didn't have msgUUID, dropping!")
                return

              if newmsg['msgUUID'] in self.factory.incomingUUID:
                logger.warning("Recent duplicate msgUUID, dropping!")
                return

              self.factory.incomingUUID.append(msg['msgUUID'])

              # if new, it won't have a msgOrigUUID field, otherwise it must.
              # Check that it does contain an OrigUUID field and that it is
              # a valid msgUUID sent by us.

              if 'status' not in newmsg:
                logger.warning("Message should have a status, but didn't. Dropping!")
                return
              if newmsg['status'] != 'new':
                if 'msgOrigUUID' not in newmsg:
                  logger.warning("Message should have msgOrigUUID, but didn't. Dropping!")
                  return
              if newmsg['msgOrigUUID'] in self.factory.outgoingUUID:
                logger.warning("This is not a valid response for this session.")
                return

              try:
                logger.trace("got message: %s", newmsg)
                message = Message(**newmsg)
                message.send()
              except:
                return logger.warning("GatewayControl dropped packet: Couldn't create a Message instance.")
                

    def doAuth(self, msg):
        """
        Responsible for completing the authentication phase of the connection.
        
        It checks for error messages returned from the gateway, and raises an AuthError
        if authentication credentials are invalid.  It will exit the service and display
        an error on how to correct the problem.
        
        It also validates that the remote Yombo server really has our gateway hash. If it
        doesn't find a valid response, it will disconnect from the current yombo server and
        try another server.
        
        :param msg: A dictionary of the message sent from the yombo server. We don't use
            full message object in the auth phase.
        :type msg: dict
        """
        logger.info("auth state = %d" % self.authState)
        if "error" in msg:
            logger.error("A critical error occuring during authentication.")
            logger.error("Reason: %s", msg["error"])
            raise AuthError("Authentication to server failed: %s" % msg['error'], 5010)

        if self.authState == 0: # if waiting for greeting, process that.
          msgKeys = ('snonce', 'pgpkeyid', 'protocolversion', 'minprotocolversion')
          if not all(item in msgKeys for item in msg): # missing message parts. Discard.
            logger.warning("Server didn't send our required items back. Good bye.")
            raise AuthError("Server didn't send our required items back. Good bye.", 5010)

          try:
              minProtocolVersion = int(msg['minprotocolversion'])
              logger.debug("if %f > %f", minProtocolVersion, self.protocolVersion)
              if minProtocolVersion > self.protocolVersion:
                raise AuthError("You must upgrade the gateway software. Protocol communication is out of date.", 5012)
          except:
              raise AuthError("Error reading/processing remote protocol. Is your gateway software up to date?", 5013)
            
          if validateNonce(msg["snonce"]) != True:
              logger.warning("Server sent us a bad nonce.  Dropping connection and will attempt a reconnect.")
              self.factory.router.reconnectToDifferent()

          self.__snonce = msg["snonce"]
          self.__gwhash = getConfigValue("core", "gwhash")

          authtoken = generateToken(self.__gwhash, self.__snonce, self.__cnonce)
          response = {
                       'authtoken'   : authtoken,
                       'listenerport': getConfigValue("core", "controllerport", 443),
                       'localip'     : getLocalIPAddress(),
                       'externalip'  : getConfigValue("core", "externalIPAddress", "0.0.0.0"),
                     }
          self.sendMessage(response)
          self.authState = 1
          return

        elif self.authState == 1:
            if 'cmd' in msg:
              if msg['cmd'] == 'authok':
                logger.trace("my auth msg: %s", msg)
                auth = checkToken(msg['authtoken'], self.__gwhash[:15], self.__cnonce, self.__snonce)
                if(auth == True):
                  self.authenticated = True
                  self.dataAuthID_svr = msg["dataAuthID_svr"]
                  self.dataAuthID_client = msg["dataAuthID_client"]
                  self.factory.router.connected(self)
                  logger.debug("GatewayControlProtocol::stringReceived() - Got authok - I'm authenticated")
                  setConfigValue('server', 'svcpgpkeyid', msg["pgpkeyid"])
                  #pgpFetchKey(msg["pgpkeyid"])
                else:
                  logger.warning("Yombo server doesn't know our hash, dropping connection and attempt to connect elsewhere.")
                  self.factory.router.reconnectToDifferent()
              else:
                logger.warning("Yombo server says out auth is bad!")
                self.factory.router.reconnectToDifferent()

class GatewayControlFactory(ReconnectingClientFactory):
    """
    The interface between the gateway system and the protocol layer.
    """
    protocol = GatewayControlProtocol
    def __init__(self, router):
        """
        Setup low level protocol.
        """
        # DO NOT CHANGE THESE!  Mitch Schwenk @ yombo.net
        # Reconnect sort of fast, but random. 15 min max wait
        self._Name = "GatewayControlFactory"
        self._FullName = "yombo.gateway.lib.GatewayControlFactory"
        self.initialDelay = 2
        self.jitter = 0.2
        self.factor = 2.42503912
        self.router = router
        self.maxDelay = 60
        # These are in the factory incase the connection is dropped and remade.
        self.incomingUUID = deque([],600) # Make sure the last few message UUIDs are unique
        self.outgoingUUID = deque([],600) # Make sure the last few message UUIDs are unique
        

    def startedConnecting(self, connector):
        logger.debug("Attempting connecting to yombo servers.")

    def buildProtocol(self, addr):
        logger.debug("Building protocol.")
        p = self.protocol()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        self.router.disconnected()
        logger.info('Lost connection.  Reason: %s' % reason)
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        logger.info('Connection failed. Reason: %s' % reason)
        ReconnectingClientFactory.clientConnectionFailed(self, connector,reason)

    def receivedMessage(self, incoming):
        """
        Received a message from Yombo Servers.
        
        :param incoming: An incoming message from Yombo servers.
        :type incoming: dict
        """
        logger.debug("Gateway Control factory got incoming message:%s", incoming)
        msg = {"msgOrigin" : incoming["msgOrigin"],
               "msgDestination" : incoming["msgDestination"],
               "msgType" : incoming["msgDestination"],
               "msgUUID" : incoming["msgUUID"],
               "payload" : incoming["payload"] }
        if 'msgPath' in incoming:
            msg['msgPath'] = incoming['msgPath']
        message = Message(**msg)
        message.addPathLocal('lib.gatewaycontrol', 'yes')
        self.router.receivedMessage(message)

    def disconnected(self, reconnect):
        self.router.disconnected(reconnect)


class GatewayControl(YomboLibrary):
    """
    Gateway Control: Route messages between local gateway and master servers
    """
    commandTimeOut = 0
    configUpdate = None

    def init(self, loader):
        self.loader = loader
        
        self._connection = None #Protocol object
        self._connecting = False
        self.GCfactory = None
        self.timeout_disconnect_task = None
        self.myreactor = None

        self.sendQueue = deque([])
        self.configUpdate = getComponent('yombo.gateway.lib.ConfigurationUpdate')
        self.gwuuid = getConfigValue("core", "gwuuid")

    def load(self):
        pass

    def start(self):
        self.loopCmdQueue = LoopingCall(self.sendQueueCheck)
        self.loopCmdQueue.start(1)

    def stop(self):
        pass

    def unload(self):
        logger.debug("Disonnecting due to unload.")
        if self._connection != None:
            self.disconnect()
    
    def reconnectToDifferent(self):
        logger.debug("I'm supposed to reconnect to different server!")
        self.disconnect()
        self.updateSvcList()
        
    def updateSvcList(self):
        self.connect()

    def connect(self):
        logger.debug("Yombo Client trying to connect to master server...")
        if self._connecting == True:
            logger.trace("Already trying to connect, connect attempt aborted.")
            return
        self._connecting = True

        environment = getConfigValue('server', 'environment', "production")
        if getConfigValue("server", 'hostname', "") != "":
            host = getConfigValue("server", 'hostname')
        else:
            if(environment == "production"):
                host = "svc1.yombo.net"
            elif (environment == "staging"):
                host = "svcstg.yombo.net"
            elif (environment == "development"):
                host = "svcdev.yombo.net"
            else:
                host = "svc2.yombo.net"
            
        port = int(getConfigValue("svcsvr", "yombosvcport", "5400"))

        logger.info("Going to connect to Yombo server at %s:%d " % (host, port) )

        self.GCfactory = GatewayControlFactory(self)
        self.myreactor =  reactor.connectSSL(host, port, self.GCfactory,
            ssl.ClientContextFactory())

    def connected(self, connection):
        logger.debug("Connected to Yombo servers.")

        self._connection = connection
        self._connecting = False
        self.timeout_reconnect_task = False
        self.sendQueueCheck()

    def disconnect(self):
        self.GCfactory.stopTrying() 
        self.myreactor.disconnect()

    def disconnected(self):
        logger.info("Disconnected from Yombo service.")
## enabled?        self.loopCmdQueue.stop()
        self._connection = None
        self._connecting = True

    def message(self, message):
        """
        Yombo Gateway sends most messages here for items targeting Yombo service.

        If the message is for us, don't forward.  Otherwise, check to make sure
        destination is valid before sending to Yombo servers.
        """
        forUs = message.checkDestinationAsLocal()

        if forUs == False:
            self._connection.sendMessage(message.dumpToExternal())
        else:
            logger.warning("Not routing message to YomboSvc since the message is for us.: %s", message.dump())

    def sendQueueAdd(self, message):
        if type(message) is not dict:
            message = message.dumpToExternal()
        logger.trace("Adding command to queue: %s", message)
        self.sendQueue.appendleft(message)
        self.sendQueueCheck()

    def sendQueueCheck(self):
        logger.trace("YomboClient:cmdQueueCheck(). Connecting: %s Count: %d" % (self._connecting, len(self.sendQueue) ) )
        if len(self.sendQueue) == 0:
            return

        if self._connection:
            while True:
                try:
                    self._connection.sendMessage(self.sendQueue.pop())
                except IndexError:
                    break
        else:
            if not self._connecting:
                logger.trace("trying to connect from send_queue_check")
                self.connect()
