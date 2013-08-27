# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
Establishes a connection the Yombo servers to send bulk data transfers.
Having a seperate connection allows commands to be send on the control
link while bulkier data blob transfers can happen on a separate stream.

This data stream supports bi-direct, simultaneous, traffic.  Authorization
and data control is handled is handled by
L{GatewayControl<yombo.lib.gatewaycontrol.GatewayControl>}.

@author: U{Mitch Schwenk<mitch-api@yombo.net>}
@organization: U{Yombo <http://www.yombo.net>}
@copyright: 2010-2012 Yombo
@license: see LICENSE.TXT from Yombo Gateway Software distribution
@contact: U{Yombo Support <support-api@yombo.net>}
"""
__docformat__ = 'epytext en' 

import json
import os

from collections import deque
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols import basic, FileSender
from twisted.internet import reactor, ssl
from twisted.internet.task import LoopingCall

from yombo.core.library import YomboLibrary
from yombo.core.message import Message
from yombo.core.helpers import getConfigValue, getLocalIPAddress
from yombo.core.log import getLogger
from yombo.core import getComponent

logger = getLogger()

class TransferCancelled(Exception):
    """Exception for a user cancelling a transfer"""
    pass

class GatewayDataProtocol(LineReceiver):
    def __init__(self, path, sess_key, file_key, controller):
        self._Name = "GatewayDataProtocol"
        self._FullName = "yombo.lib.GatewayDataProtocol"
        
        self.GatewayControlProtocol = getComponent('yombo.gateway.lib.GatewayControlProtocol')

        self.path = path
        self.sess_key = sess_key
        self.file_key = file_key
        self.controller = controller

        self.infile = open(self.path, 'rb')
        self.insize = os.stat(self.path).st_size

        self.result = None
        self.completed = False

        self.controller.file_sent = 0
        self.controller.file_size = self.insize

    def _monitor(self, data):
        self.controller.file_sent += len(data)
        self.controller.total_sent += len(data)

        # Check with controller to see if we've been cancelled and abort
        # if so.
        if self.controller.cancel:
            # Need to unregister the producer with the transport or it will
            # wait for it to finish before breaking the connection
            self.transport.unregisterProducer()
            self.transport.loseConnection()
            # Indicate a user cancelled result
            self.result = TransferCancelled('User cancelled transfer')

        return data

    def cbTransferCompleted(self, lastsent):
        self.completed = True
        self.transport.loseConnection()

    def connectionMade(self):
        self.transport.write('%s %s %s\r\n' % (str(self.sess_key),
                                               str(self.file_key),
                                               self.insize))
        sender = FileSender()
        sender.CHUNK_SIZE = 2 ** 16
        d = sender.beginFileTransfer(self.infile, self.transport,
                                     self._monitor)
        d.addCallback(self.cbTransferCompleted)

    def connectionLost(self, reason):
        LineReceiver.connectionLost(self, reason)
        self.infile.close()
        if self.completed:
            self.controller.completed.callback(self.result)
        else:
            self.controller.completed.errback(reason)

class GatewayDataFactory(ReconnectingClientFactory):
    protocol = GatewayDataProtocol
    # DO NOT CHANGE THESE!  Mitch Schwenk @ yombo.net
    # Reconnect sort of fast, but random. 15 min max wait
    maxDelay = 600
#    factor = 2.5
#    jitter = 0.25

    def __init__(self, path, sess_key, file_key, controller):
        self.maxDelay = 60
        self.path = path
        self.sess_key = sess_key
        self.file_key = file_key
        self.controller = controller
        
    def clientConnectionFailed(self, connector, reason):
        ClientFactory.clientConnectionFailed(self, connector, reason)
        self.controller.completed.errback(reason)

    def buildProtocol(self, addr):
        p = self.protocol(self.path, self.sess_key, self.file_key,
                          self.controller)
        p.factory = self
        return p


class GatwayData(YomboLibrary):
    """
    Send/Receive data blobs to/from Yombo Service.
    """
    commandTimeOut = 0
    configUpdate = None

    def __init__(self, loader):
        YomboLibrary.__init__(self)

        self.loader = loader
        
        self._connection = None #Protocol object
        self._connecting = False
        self.yombofactory = None
        self.timeout_disconnect_task = None
        self.myreactor = None

        self.sendQueue = deque([])

    def load(self):
        logger.debug("!!!!!!!!!!!!1")
        self.configUpdate = getComponent('yombo.lib.ConfigurationUpdate')
        logger.debug("configUpdate = %s", self.configUpdate)
        self.gwuuid = getConfigValue("core", "gatewayuuid")

    def start(self):
        self.loopCmdQueue = LoopingCall(self.sendQueueCheck)
        self.loopCmdQueue.start(1)

    def stop(self):
        pass

    def unload(self):
        logger.debug("Disonnecting due to unload.")
        if self._connection != None:
            self.disconnect()

    def connect(self):
        logger.debug("Yombo Client trying to connect to Yombo service server...")
        if self._connecting == True:
            logger.trace("Already trying to connect, connect attempt aborted.")
            return
        self._connecting = True

        host = getConfigValue("svcsvr", "yombosvchost", "localhost")
        port = int(getConfigValue("svcsvr", "yombosvcport", "5600"))

        logger.trace("Going to connect to Yombo server at %s:%d " % (host, port) )

        self.yombofactory = GatewayDataFactory(self)
        self.myreactor =  reactor.connectSSL(host, port, self.yombofactory,
            ssl.ClientContextFactory())

    def connected(self, connection):
        logger.info("Connected to Yombo server.")

        self._connection = connection
        self._connecting = False
        self.timeout_reconnect_task = False
        self.sendQueueCheck()

    def disconnect(self):
        self.yombofactory.stopTrying() 
        self.myreactor.disconnect()

    def disconnected(self):
        logger.info("Disconnected from Yombo server.")
## enabled?        self.loopCmdQueue.stop()
        self._connection = None
        self._connecting = True

    def message(self, message):
        """
        Yombo Gateway Data sends most messages here for items targeting Yombo servers.

        If the message is for us, don't forward.  Otherwise, check to make sure
        destination is valid before sending to Yombo servers.
        """
        dest = message.msgDestination.split(":")
        if len(dest) == 1:
            if dest[0][:10].lower() != "yombo.gateway":
                logger.trace("Forwarded non-gateway message to Yombo server for processing.")
                self._connection.sendMessage(message.dump())
                return
        elif len(dest) == 2:
            if dest[1] == self.gwuuid:
                logger.warning("Not routing message to Yombo Service since the message is for us.: %s", message.dump())
                return
            else:
                logger.trace("Forwarded message to Yombo Service for processing.")
                self._connection.sendMessage(message.dump())
        else:
            logger.trace("Message has too few or too many parts.  Dropping.")
            return

    def sendQueueAdd(self, message):
        if type(message) is not dict:
            message = message.dump()
        logger.trace("Adding command to queue: %s", message)
        self.sendQueue.appendleft(message)
        self.sendQueueCheck()

    def sendQueueCheck(self):
        logger.trace("Yombo Gateway Data::sendQueueCheck(). Connecting: %s Count: %d" % (self._connecting, len(self.sendQueue) ) )
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
                logger.trace("trying to connect from sendQueueCheck")
                self.connect()
