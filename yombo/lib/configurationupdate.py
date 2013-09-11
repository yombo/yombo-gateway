# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
Handles getting configuration updates from the Yombo servers.

.. warning::

   Module developers should not access any of these functions
   or variables.  They are used internally.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""

from collections import deque
import cPickle # to store dictionaries
from sqlite3 import Binary as sqlite3Binary
import time


from twisted.internet import defer, reactor
from twisted.internet.task import LoopingCall

from yombo.core.library import YomboLibrary
from yombo.core.message import Message
#TODO: Consolidate.
import yombo.core.db
from yombo.core.db import get_dbconnection
from yombo.core.helpers import getConfigValue, setConfigValue, getComponent, getConfigTime, generateUUID
from yombo.core.log import getLogger
from yombo.core import getComponent

logger = getLogger('library.configurationupdate')

class ConfigurationUpdate(YomboLibrary):
    """
    Responsbile for processing configuration update requests.

    Currently, only handles full configuration downloads.
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

        self.gateway_control = getComponent('yombo.gateway.lib.GatewayControl')
        self.dbconnection = get_dbconnection()
        if self.loader.unittest: # if we are testing, don't try to download configs
          return
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
        self.timerQueue.stop()
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
        if len(self.__incomingConfigQueue) > 0:
            config = self.__incomingConfigQueue.pop()
            self.processConfig(config)        

    def processConfig(self, msg):
#        cfg = getComponent("yombo.lib.Configuration")
        payload = msg['payload']
        cmd = payload['cmd'].lower()
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

        logger.trace("Config Type: %s", cmdmap[cmd]['type'])
        # make sure the command exists
        if cmd not in cmdmap:
            logger.warning("ConfigurationUpdate::processConfig - Command '%s' doesn't exist. Skipping.", cmd)
            return
        elif 'type' not in cmdmap[cmd]:
            logger.warning("ConfigurationUpdate::processConfig - Invalid commandMap. Skipping.")
            return
        elif cmdmap[cmd]["type"] == "fullConfig":
            logger.trace("ConfigurationUpdate::processConfig - 'fullConfig' - %s.", cmdmap[cmd]["table"])
            upd_table = getattr(yombo.core.db, cmdmap[cmd]["table"])
            c = self.dbconnection.cursor()
            if not upd_table:
                logger.error("ConfigurationUpdate::processConfig - Invalid table to update: %s", upd_table.table_name)
                return
            c.execute("DELETE FROM " + upd_table.table_name)

            logger.debug("ProcessConfig payload: %s", upd_table.table_name)

            for record in payload["configdata"]:
                items = record.items()
                saveitems = []
                for col, val in items:
                    col_to_update = None
                    for col_ in upd_table.columns:
                        if col_.name == col:
                            col_to_update = col_
                    if not col_to_update:
                        logger.error("ConfigurationUpdate::processConfig - Error while updating table: %s", upd_table.table_name)
                        logger.error("ConfigurationUpdate::processConfig - Invalid column: %s", col)
                        return 
                    logger.trace("type = %s, col = '%s', val = '%s'", type(val), col, val)
                    if type(val) is dict:
                        val = sqlite3Binary(cPickle.dumps(val, cPickle.HIGHEST_PROTOCOL))
#                    temp = (col, decryptPGP(val))
                    temp = (col, val)
                    saveitems.append(temp)

                logger.trace('items: %s', items)
                logger.trace('saveitems: %s', saveitems)
                sql = "insert into %s (%s) values (%s)" % (upd_table.table_name,
                    ", ".join(i[0] for i in items),
                    ", ".join('?' for i in saveitems),
                    )
                logger.trace('sql: %s', sql)
                logger.trace([i[1] for i in saveitems])
                c.execute(sql, [i[1] for i in saveitems])               
            self.dbconnection.pool.commit()
            self._removeFullTableQueue(cmdmap[cmd]["table"])
            if cmdmap[cmd]["table"] == "gwTokensTable":
              setConfigValue('local', 'lastUserTokens', int(time.time()) )
        elif cmdmap[cmd]["type"] == "partialConfig":
            logger.error("ConfigurationUpdate::processConfig - 'partialConfig'.")
        elif cmdmap[cmd]["type"] == "GatewayDetailsResponse":
            record = payload["configdata"][0]
            items = record.items()
            for col, val in items:
                setConfigValue("core", col, val)
            self._removeFullTableQueue('GatewayDetailsTable')
        elif cmdmap[cmd]["type"] == "GatewayVariablesResponse":
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
            self._removeFullTableQueue('GatewayVariablesTable')
        elif cmdmap[cmd]["type"] == "GetFullConfigs":
            logger.info("Requesting full configuration update VIA process config.")
            logger.trace("doing GetFullConfigs!  %s", msg)
            self.getAllConfigs()

        self.__incomingConfigQueueCheck()
        
    def getAllConfigs(self):
        # don't over do it on the the full config download.  Might be
        # multiple sources for this on bootup!!
        if self.__doingfullconfigs == True:
            return False
        lastTime = getConfigValue("core", "lastFullConfigDownload", 30)
        if int(lastTime) > int(time.time()):
            logger.debug("Not downloading fullconfigs due to race condition.")
            return

        self.__doingfullconfigs = True
        setConfigValue("core", "lastFullConfigDownload", int(time.time()) )

        logger.debug("Preparing for full configuration download.")
        self.doGetAllConfigs()

    def doGetAllConfigs(self, junk=None):
        logger.trace("dogetallconfigs.....")
        self._appendFullTableQueue("CommandsTable")
        self._appendFullTableQueue("DevicesTable")
        self._appendFullTableQueue("DeviceTypeCommandsTable")
        self._appendFullTableQueue("GatewayDetailsTable")
        self._appendFullTableQueue("GatewayVariablesTable")
        self._appendFullTableQueue("ModuleInterfacesTable")
        self._appendFullTableQueue("ModuleDeviceTypesTable")
        self._appendFullTableQueue("ModulesTable")
        self._appendFullTableQueue("UsersTable")
        self._appendFullTableQueue("VariableDevicesTable")
        self._appendFullTableQueue("VariableModulesTable")
        
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'GPGKEY', 'gpgkeyid' : self.gpg_key, 'gpgkeyascii' : self.gpg_key_ascii}))
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'getFullCommands', 'type' : "outgoing"}))
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'getFullDevices'}))
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'getFullDeviceTypeCommands'}))
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'getFullGatewayModuleInterfaces'}))
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'getFullGatewayDetails'}))
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'getFullGatewayUserTokens'}))
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'getFullGatewayVariables'}))
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'getFullModuleDeviceTypes'}))
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'getFullModules'}))
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'getFullUsers'}))
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'getFullVariableDevices'}))
        self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'getFullVariableModules'}))
        return True

    def _generateMessage(self, payload):
        return {'msgOrigin'     : "yombo.gateway.lib.configurationupdate:%s" % self.gwuuid,
               'msgDestination' : "yombo.svc.gwhandler",
               'msgType'        : "config",
               'msgStatus'      : "new",
               'msgUUID'        : str(generateUUID(mainType='Y', subType='cu0')),
               'payload'        : payload,
              }

    def _appendFullTableQueue(self, table):
        """
        Adds an item to pending table queue.
        
        Will be removed as each config item is returned by _removeFullTableQueue.
        """
        logger.trace("_appendFullTableQueue:before - table: %s", table)
        if table not in self.__pendingUpdates:
            self.__pendingUpdates.append(table)

    def _removeFullTableQueue(self, table):
        if table in self.__pendingUpdates:
            self.__pendingUpdates.remove(table)

        if len(self.__pendingUpdates) == 0 and self.__doingfullconfigs == True:
            self.__doingfullconfigs = False
            self.loadDefer.callback(10) # a made up number.
        logger.trace("Configs pending: %s", self.__pendingUpdates)
            
