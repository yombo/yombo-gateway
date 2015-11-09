# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
"""
Handles getting configuration updates from the Yombo servers.

.. warning::

   Module developers should not access any of these functions
   or variables.  They are used internally.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2015 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from collections import deque
import cPickle # to store dictionaries
from sqlite3 import Binary as sqlite3Binary
from time import time

# Import twisted libraries
from twisted.internet import defer, reactor
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.message import Message
import yombo.core.db
from yombo.core.db import get_dbconnection
from yombo.core.helpers import getConfigValue, setConfigValue, getComponent, getConfigTime, generateRandom
from yombo.core.log import getLogger
from yombo.core import getComponent
from yombo.core.maxdict import MaxDict
from yombo.core.exceptions import YomboWarning

logger = getLogger('library.configurationupdate')

class ConfigurationUpdate(YomboLibrary):
    """
    Responsible for processing configuration update requests.
    """
    #zope.interface.implements(ILibrary)

    def _init_(self, loader):
        """
        Setup the configuration queue, prepare the module.

        Download of all configurations. This ensures all configurations are up to date.

        This function returns a deferred to the loader.  Once all the configurations
        have been completed, the deferred will finish, allowing the gateway to finish the
        startup cycle.
        
        :param loader: The loader module.
        :type loader: :mod:`~yombo.lib.loader`
        """
        self.loader = loader

        self.__incomingConfigQueue = deque([])
        self.__incomingConfigQueueLoop = LoopingCall(self.__incomingConfigQueueCheck)

        self.__doingfullconfigs = False
        self.__pendingUpdates = []
        self.gpg_key = getConfigValue("core", "gpgkeyid", '')
        self.gpg_key_ascii = getConfigValue("core", "gpgkeyascii", '')
        self.gwuuid = getConfigValue("core", "gwuuid")

        self.dbconnection = get_dbconnection()
        if self.loader.unittest: # if we are testing, don't try to download configs
          return
        self.AMQPYombo = getComponent('yombo.gateway.lib.AMQPYombo')
        self.loadDefer = defer.Deferred()
        self.loadDefer.addCallback(self.__loadFinish)
        self.getAllConfigs()
        return self.loadDefer

    def _load_(self):
        """
        """
        pass
    
    def __loadFinish(self, nextSteps):
        """
        Called when all the configurations have been received from the Yombo servers.
        """
        return 1

    def _start_(self):
        """
        Start the timer to pool for new configurations.

        Future versions will allow fetching of some configurations without
        taking down the entire Yombo gateway service.
        """
        self.__incomingConfigQueueLoop.start(5)
        self.__incomingConfigQueueCheck()

    def _stop_(self):
        """
        Stop this module and prepare to be unloaded.
        """
        self.__incomingConfigQueueCheck()
    
    def _unload_(self):
        """
        Don't really do anything, function defined to prevent an exception.
        """
        pass

    def incomingConfigQueueAdd(self, msg):
        """
        Add a configuration response from the Yombo server to
        processing queue. After being added,
        calls __incomingConfigQueueCheck().

        :param msg: A message to be sent to the server.
        :type msg: dict
        """
        self.__incomingConfigQueue.appendleft(msg)
        self.__incomingConfigQueueCheck()

    def __incomingConfigQueueCheck(self):
        """
        Checks the incoming config queue 
        """
#        logger.warning("configQueueCheck was just called.")
        while self.__incomingConfigQueue:
            config = self.__incomingConfigQueue.pop()
            self.processConfig(config)

    def amqpDirectIncoming(self, sendInfo, deliver, props, msg):
        # do nothing on requests for now.... in future if we ever accept requests, we will.
        if props.headers['Type'] != "Response":
            raise YomboWarning("ConfigurationUpdate::amqpDirectIncoming only accepts 'Response' type message.")

        # if a response, lets make sure it's something we asked for!
#        logger.info("received: %s, deliver: %s, props: %s, msg: %s" % (sendInfo, deliver, props, msg))
#                dt = sendInfo['time_sent'] - sendInfo['time_created']
#                ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
#                logger.info("Delay between create and send: %s ms" % ms)
        configType = props.headers['ConfigItem']
        configStatus = props.headers['ConfigStatus']
 #       try:
        self.processConfig(configType, configStatus, msg)
#        except:
#            raise YomboWarning("Unable to pre")

    def processConfig(self, configType, configStatus, msg):
        payload = msg['Data']
        configTypes = {
            'Commands' : {'table': "CommandsTable", 'map' : {
                'Uri' : 'uri',
                'UUID' : 'cmdUUID',
                'voiceCmd' : 'voiceCmd',
                'machineLabel' : 'machineLabel',
                'label' : 'label',
                'description' : 'description',
                'created' : 'created',
                'updated' : 'updated',
                'status' : 'status',
                'public' : 'public',
#                '' : '',
            }},
            'Devices' : {'table': "DevicesTable"},
#            "DeviceTypeCommands",
#            "GatewayDetails",
#            "GatewayModules",
#            "GatewayModuleInterfaces",
#            "GatewayUserTokens",
#            "GatewayVariables",
#            "GatewayModuleDeviceTypes",
#            "GatewayUsers",
    }

        cmdmap = {
            'getfullconfigs': {'type': "GetFullConfigs"},
            'getfullgatewaydetailsresponse': {'type': "GatewayDetailsResponse"},
            'getfullgatewayusertokensresponse': {'table': "gwTokensTable", 'type': "fullConfig"},
            'getfullgatewayvariablesresponse': {'type': "GatewayVariablesResponse"},
            'getfullcommandsresponse': {'table': "CommandsTable", 'type': "fullConfig"},
            'getfullgatewaymoduleinterfacesresponse': {'table': "ModuleInterfacesTable", 'type': "fullConfig"},
            'getfulldevicesresponse': {'table': "DevicesTable", 'type': "fullConfig"},
            'getfulldevicetypecommandsresponse': {'table': "DeviceTypeCommandsTable", 'type': "fullConfig"},
            'getfullmoduledevicetypesresponse': {'table': "ModuleDeviceTypesTable", 'type': "fullConfig"},
            'getfullmodulesresponse': {'table': "ModulesTable", 'type': "fullConfig"},
            'getfullvariablemodulesresponse': {'table': "VariableModulesTable", 'type': "fullConfig"},
            'getfullvariabledevicesresponse': {'table': "VariableDevicesTable", 'type': "fullConfig"},
            'getfullusersresponse': {'table': "UsersTable", 'type': "fullConfig"}}

        # make sure the command exists
        if configType not in configTypes:
            logger.warning("ConfigurationUpdate::processConfig - '%s' is not a valid configuration item. Skipping.", configType)
            return
        elif configType == "GatewayDetails":
            record = payload["configdata"][0]
            items = record.items()
            for col, val in items:
                setConfigValue("core", col, val)
#            self._removeFullTableQueue('GatewayDetailsTable')
        elif configType == "GatewayVariable":
            records = payload["configdata"]
            sendUpdates = []
            for record in records:
                if getConfigTime(record['section'], record['item']) > record['updated']:
                  setConfigValue(record['section'], record['item'], record['value'])
                else: #the gateway is newer
                  sendUpdates.append({'section': record['section'],
                                      'item'   : record['item'],
                                      'value'  : record['value']})

# needs to be implemented on server first!!
#            if len(sendUpdates):
#              self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'setGatewayVariables', 'configdata':sendUpdates}))
#            self._removeFullTableQueue('GatewayVariablesTable')
#        elif cmdmap[cmd]["type"] == "GetFullConfigs":
#            logger.info("Requesting full configuration update VIA process config.")
#            logger.trace("doing GetFullConfigs!  %s", msg)
#            self.getAllConfigs()
        elif configType in configTypes:
            logger.trace("ConfigurationUpdate::processConfig - Doing config for: %s" % configType)
            upd_table = getattr(yombo.core.db, configTypes[configType]["table"])
            c = self.dbconnection.cursor()
            if not upd_table:
                logger.error("ConfigurationUpdate::processConfig - Invalid table to update: %s", upd_table.table_name)
                return
            if configStatus == "Full":  #Todo: Currently, this can only work when first started. Need to implement update while running.
                c.execute("DELETE FROM " + upd_table.table_name)

            data = []
            if msg['DataType'] == 'Object': # a single response
                logger.debug("Processing single object config response.")
                data.append(msg['Data'])
            elif msg['DataType'] == 'Objects': # An array of responses
                logger.debug("Processing multiple object config response.")
                data = msg['Data']
            self._removeFullDownloadQueue(configType)
            for record in data:
                items = record.items()
#                logger.info("Items:  %s" % items)
                savecols = []
                saveitems = []

                for col, val in items:
                    col_to_update = None
#                    logger.info("upd_table: %s, upd_table.columns: %s" % (upd_table, upd_table.columns))
                    if col not in configTypes[configType]['map']:
                        continue

                    savecols.append(configTypes[configType]['map'][col])

                    if type(val) is dict:
                        val = sqlite3Binary(cPickle.dumps(val, cPickle.HIGHEST_PROTOCOL))
#                    temp = (col, decryptPGP(val))
                    temp = (col, val)
                    saveitems.append(temp)

#                logger.info('items: %s', items)
#                logger.info('savecols: %s', savecols)
#                logger.info('saveitems: %s', saveitems)
                sql = "insert into %s (%s) values (%s)" % (upd_table.table_name,
                    ", ".join(i for i in savecols),
                    ", ".join('?' for i in saveitems),
                    )
 #               logger.info('sql: %s', sql)
 #               logger.info([i[1] for i in saveitems])
                c.execute(sql, [i[1] for i in saveitems])
            self.dbconnection.pool.commit()
#            self._removeFullTableQueue(cmdmap[cmd]["table"])
#            if cmdmap[cmd]["table"] == "gwTokensTable":
#              setConfigValue('local', 'lastUserTokens', int(time()) )

        self.__incomingConfigQueueCheck()
        
    def getAllConfigs(self):
        # don't over do it on the the full config download. Might be a quick restart of gateway.
        logger.info("About to do getAllConfigs")
        if self.__doingfullconfigs == True:
            return False
        lastTime = getConfigValue("core", "lastFullConfigDownload", 1)
        if int(lastTime) > (int(time() - 10)):
            logger.debug("Not downloading fullconfigs due to race condition.")
            return

        self.__doingfullconfigs = True
        setConfigValue("core", "lastFullConfigDownload", int(time()) )

        logger.debug("Preparing for full configuration download.")
        self.doGetAllConfigs()

    def doGetAllConfigs(self, junk=None):
        logger.trace("dogetallconfigs.....")

        allCommands = [
            "Commands",
#            "getDevices",
#            "getDeviceTypeCommands",
#            "getGatewayDetails",
#            "getGatewayModules",
#            "getGatewayModuleInterfaces",
#            "getGatewayUserTokens",
#            "getGatewayVariables",
#            "getGatewayModuleDeviceTypes",
#            "getGatewayUsers",
        ]
        for item in allCommands:
            logger.info("sending command: %s"  % item)

            self._appendFullDownloadQueue(item)
            self.AMQPYombo.sendDirectMessage(**self._generateRequest(item, "All"))

    def _generateRequest(self, request_type, requestContent):
        request = {
            "exchange_name"  : "gw_config",
            "source"        : "yombo.gateway.lib.configurationupdate",
            "destination"   : "yombo.server.configs",
            "callback" : self.amqpDirectIncoming,
            "body"          : {
              "DataType"        : "Object",
              "Request"         : requestContent,
            },
            "request_type"   : request_type,
        }
        return self.AMQPYombo.generateRequest(**request)

    def _appendFullDownloadQueue(self, table):
        """
        Adds an item to pending table queue.
        
        Will be removed as each config item is returned by _removeFullTableQueue.
        """
        logger.trace("_appendFullTableQueue:before - table: %s", table)
        if table not in self.__pendingUpdates:
            self.__pendingUpdates.append(table)

    def _removeFullDownloadQueue(self, table):
        if table in self.__pendingUpdates:
            self.__pendingUpdates.remove(table)

        if len(self.__pendingUpdates) == 0 and self.__doingfullconfigs == True:
            self.__doingfullconfigs = False
            self.loadDefer.callback(10) # a made up number.
        logger.trace("Configs pending: %s", self.__pendingUpdates)
            
