# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at https://yombo.net
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
import cPickle  # to store dictionaries
from sqlite3 import Binary as sqlite3Binary
from time import time

# Import twisted libraries
from twisted.internet import defer
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.library import YomboLibrary
#from yombo.core.message import Message
import yombo.core.db
from yombo.core.db import get_dbconnection
from yombo.core.helpers import getConfigValue, setConfigValue, getConfigTime
from yombo.core.log import getLogger
from yombo.core import getComponent
#from yombo.core.maxdict import MaxDict
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
        if self.loader.unittest:  # if we are testing, don't try to download configs
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
#        logger.warn("configQueueCheck was just called.")
        while self.__incomingConfigQueue:
            config = self.__incomingConlibrary.configurationupdatefigQueue.pop()
            self.processConfig(config)

    def amqpDirectIncoming(self, sendInfo, deliver, props, msg):
        # do nothing on requests for now.... in future if we ever accept requests, we will.
        if props.headers['Type'] != "Response":
            raise YomboWarning("ConfigurationUpdate::amqpDirectIncoming only accepts 'Response' type message.") # For now...

        # if a response, lets make sure it's something we asked for!
#        logger.info("received: %s, deliver: %s, props: %s, msg: %s" % (sendInfo, deliver, props, msg))
#                dt = sendInfo['time_sent'] - sendInfo['time_created']
#                ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
#                logger.info("Delay between create and send: %s ms" % ms)
        configType = props.headers['ConfigItem']
        configStatus = props.headers['ConfigStatus']
        inputType = props.headers['Type']
 #       try:
        self.processConfig(inputType, configType, configStatus, msg)
#        except:
#            raise YomboWarning("Unable to pre")

    def processConfig(self, inputType, configType, configStatus, msg):
        logger.info("processing configType: %s" % configType)
        configTypes = {
            'Commands' : {'table': "CommandsTable", 'map' : {
                'Uri' : 'uri',
                'UUID' : 'cmdUUID',
                'voiceCmd' : 'voiceCmd',
                'machineLabel' : 'machineLabel',
                'label' : 'label',
                'description' : 'description',
                'inputtype' : 'inputTypeUUID',
                'liveupdate' : 'liveUpdate',
                'created' : 'created',
                'updated' : 'updated',
                'status' : 'status',
                'public' : 'public',
#                '' : '',
            }},
            'DeviceTypes' : {'table': "DeviceTypesTable", 'map' : {
                'UUID' : 'deviceTypeUUID',
                'Uri' : 'uri',
                'MachineLabel' : 'machineLabel',
                'Label' : 'label',
                'Description' : 'description',
                'LiveUpdate' : 'liveUpdate',
                'Public' : 'public',
                'Created' : 'created',
                'Updated' : 'updated',
                'Status' : 'status',
#                '' : '',
            }},
            'DeviceTypeCommands' : {'table': "DeviceTypeCommandsTable", 'map' : {
                'UUID' : 'deviceTypeUUID',
                'CmdUUID' : 'cmdUUID',
            }},
            'GatewayConfigs' : {}, # Processed with it's own catch.
            'GatewayDevices' : {'table': "DevicesTable", 'map' : {
                'Uri' : 'uri',
                'UUID' : 'deviceUUID',
#                'machineLabel' : 'machineLabel',  #Not implemented yet.
                'Label' : 'label',
                'Description' : 'description',
                'GatewayUUID' : 'gatewayUUID',
                'Notes' : 'notes',
                'VoiceCmd' : 'voiceCmd',
                'VoiceCmdOrder' : 'voiceCmdOrder',
                'VoiceCmdSrc' : 'VoiceCmdSrc',
                'DeviceTypeUUID' : 'deviceTypeUUID',
                'PinCode' : 'pinCode',
                'PinRequired' : 'pinRequired',
                'PinTimeout' : 'pinTimeout',
                'Created' : 'created',
                'Updated' : 'updated',
                'Status' : 'status',
#                '' : '',
            }},
            'GatewayModules' : {'table': "ModulesTable", 'map' : {
                'UUID' : 'moduleUUID',
                'Uri' : 'uri',
                'MachineLabel' : 'machineLabel',
                'ModuleType' : 'moduleType',
                'Label' : 'label',
                'Description' : 'description',
                'InstallNotes' : 'installNotes',
                'DocLink' : 'docLink',
                'ProdVersion' : 'prodVersion',
                'DevVersion' : 'devVersion',
                'InstallBranch' : 'installBranch',
                'Public' : 'public',
                'Created' : 'created',
                'Updated' : 'updated',
                'Status' : 'status',
            }},
            'ModuleDeviceTypes' : {'table': "ModuleDeviceTypesTable", 'map' : {
                'UUID' : 'deviceTypeUUID',
                'ModuleUUID' : 'moduleUUID',
                'ModuleLabel' : 'moduleLabel',
                'ModuleType' : 'moduleType',
                'Priority' : 'priority',
            }},
            'ModuleConfigs' : {'table': "ModuleVariablesTable", 'map' : {
                'ModuleUUID' : 'moduleUUID',
                'VariableUUID' : 'variableUUID',
                'Weight' : 'weight',
                'DataWeight' : 'dataWeight',
                'MachineLabel' : 'machineLabel',
                'Label' : 'label',
                'Value' : 'value',
                'Updated' : 'updated',
                'Created' : 'created',
            }},

#            "GatewayDetails",
#            "GatewayModules",
#            "GatewayUserTokens",
#            "GatewayVariables",
#            "GatewayModuleDeviceTypes",
#            "GatewayUsers",
        }
        cmdmap = {
            'getfullgatewayusertokensresponse': {'table': "gwTokensTable", 'type': "fullConfig"},
            'getfullvariablemodulesresponse': {'table': "VariableModulesTable", 'type': "fullConfig"},
            'getfullvariabledevicesresponse': {'table': "VariableDevicesTable", 'type': "fullConfig"},
            'getfullusersresponse': {'table': "UsersTable", 'type': "fullConfig"}
        }

        # make sure the command exists
        if configType not in configTypes:
            logger.warn("ConfigurationUpdate::processConfig - '%s' is not a valid configuration item. Skipping.", configType)
            return
        elif configType == "GatewayConfigs":
            payload = msg['Data']
            for section in payload:
                for key in section['Values']:
                   setConfigValue(section['Section'], key['Key'], key['Value'])
        elif configType == "GatewayVariable":
            records = msg['Data']["configdata"]
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
        elif configType in configTypes:
            logger.debug("ConfigurationUpdate::processConfig - Doing config for: %s" % configType)
            upd_table = getattr(yombo.core.db, configTypes[configType]["table"])
            c = self.dbconnection.cursor()
            if not upd_table:
                logger.error("ConfigurationUpdate::processConfig - Invalid table to update: %s", upd_table.table_name)
                return
            if configStatus == "Full":  #Todo: Currently, this can only work when first started. Need to implement update while running.
                c.execute("DELETE FROM " + upd_table.table_name)

            data = []
            if 'DataType' in msg:
                if msg['DataType'] == 'Object': # a single response
                    logger.debug("Processing single object config response.")
                    data.append(msg['Data'])
                elif msg['DataType'] == 'Objects': # An array of responses
                    logger.debug("Processing multiple object config response.")
                    data = msg['Data']
            else:
                if isinstance(msg, list):
                    data = msg
                elif isinstance(msg, dict):
                    data = data.append(msg)
                else:
                    raise YomboWarning("Cannot process configuration update")

            # Preprocessing for various configTypes
            if configType == 'GatewayModules':
                if configStatus == "Full":  # DeviceTypeCommands is included in full update.
                    c.execute("DELETE FROM devicetypes")
                    c.execute("DELETE FROM devicetypecommands")
                    c.execute("DELETE FROM moduleDeviceTypes")
                    self.dbconnection.pool.commit()

            tempConfig = {}  # Usef for various tracking. Variable depends on configType being processed.
            tempIndex = {}  # Usef for various tracking. Variable depends on configType being processed.
            tempStorage = {}  # Usef for various tracking. Variable depends on configType being processed.
#            tempIndex2 = []  # Usef for various tracking. Variable depends on configType being processed.
#            tempStorage2 = []  # Usef for various tracking. Variable depends on configType being processed.

            for record in data:
                items = record.items()
                savecols = []
                saveitems = []

                for col, val in items:
                    col_to_update = None
                    if col not in configTypes[configType]['map']:
#                        logger.debug("## Col (%s) not in table.." % col)
                        continue
                    tableCol = configTypes[configType]['map'][col]
                    savecols.append(configTypes[configType]['map'][col])

                    if upd_table.columnsByName[configTypes[configType]['map'][col]] == "INTEGER":
                        val=int(val)
                    elif upd_table.columnsByName[configTypes[configType]['map'][col]] == "REAL":
                        val=float(val)
                    elif type(val) is dict:
                        val = sqlite3Binary(cPickle.dumps(val, cPickle.HIGHEST_PROTOCOL))
#                    temp = (col, decryptPGP(val))
                    temp = (col, val)
                    saveitems.append(temp)

                sql = "insert into %s (%s) values (%s)" % (upd_table.table_name,
                    ", ".join(i for i in savecols),
                    ", ".join('?' for i in saveitems),
                    )
#                logger.info('sql: %s', sql)
                c.execute(sql, [i[1] for i in saveitems])

#                logger.debug("Pre checking nested %s" % configType)
                # process any nested items here.
                if configType == 'GatewayModules':
                    if '1' not in tempConfig:
                        tempConfig['1'] = {
                            'inputType' : 'nested',
                            'configType' : 'ModuleDeviceTypes',
                        }
                        tempConfig['2'] = {
                            'inputType' : 'nested',
                            'configType' : 'DeviceTypeCommands',
                        }
                        tempConfig['3'] = {
                            'inputType' : 'nested',
                            'configType' : 'DeviceTypes',
                        }
                        tempConfig['4'] = {
                            'inputType' : 'nested',
                            'configType' : 'ModuleConfigs',
                        }
                        tempIndex['1'] = []  # ModuleDeviceTypes
                        tempIndex['2'] = []  # DeviceTypeCommands
                        tempIndex['3'] = []  # DeviceTypes
                        tempIndex['4'] = []  # ModuleConfigs
                        tempStorage['1'] = []
                        tempStorage['2'] = []
                        tempStorage['3'] = []
                        tempStorage['4'] = []

#                    logger.info("devicetypes: %s" % record['DeviceTypes'][)
                    if 'DeviceTypes' in record:
                        for tempDT in record['DeviceTypes']:
                            if tempDT['UUID'] not in tempIndex['3']:
                                tempIndex['3'].append(tempDT['UUID'])
                                tempStorage['3'].append(tempDT)

    #                    logger.info("Call nested: %s" % record)
                        for dt in record['DeviceTypes']:
                            if dt['UUID'] not in tempIndex['1']:
                                tempStorage['1'].append({
                                    'UUID' : dt['UUID'],
                                    'Priority' : dt['Priority'],
                                    'ModuleUUID' : record['UUID'],  # record = module
                                    'ModuleLabel' : record['MachineLabel'],
                                    'ModuleType' : record['ModuleType'],
                                })

                            for dtc in dt['Commands']:
                                if dt['UUID'] not in tempIndex['2']:
                                    tempStorage['2'].append({
                                        'UUID' : dt['UUID'],    #dt = devicetype
                                        'CmdUUID' : dtc['UUID'],  #dtc = devicetypecommands
                                    })

                    # ModuleConfigs
                    if 'ModuleConfigs' in record:
                        for tempGroup in record['ModuleConfigs']:
                            for tempField in tempGroup['Fields']:
                                if tempField['FieldUUID'] not in tempIndex['4']:
                                    tempIndex['4'].append(tempField['FieldUUID'])

                                field = {
                                    'ModuleUUID' : record['UUID'],  # record = module
                                    'VariableUUID' : tempGroup['VariableUUID'],
                                    'Weight' : tempGroup['Weight'],
                                    'DataWeight' : tempField['Weight'],
                                    'MachineLabel' : tempField['MachineLabel'],
                                    'Label' : tempField['Label'],
                                    'Value' : tempField['Value'],
                                    'Updated' : tempField['Updated'],
                                    'Created' : tempField['Created'],
                                }
                                tempStorage['4'].append(field)
                # end if configType == 'GatewayModules'

            for key, value in tempStorage.iteritems():
#                logger.info("key: %s, value: %s" %(key, value))
                self.processConfig(tempConfig[key]['inputType'], tempConfig[key]['configType'], configStatus, tempStorage[key])

            self.dbconnection.pool.commit()
#            if cmdmap[cmd]["table"] == "gwTokensTable":
#              setConfigValue('local', 'lastUserTokens', int(time()) )
        else:
            raise YomboWarning("Unknown type on processing configuration update.")

        if inputType == "Response" and configStatus == "Full":
            self._removeFullDownloadQueue("Get" + configType)
        self.__incomingConfigQueueCheck()
        
    def getAllConfigs(self):
        # don't over do it on the the full config download. Might be a quick restart of gateway.
        logger.info("About to do getAllConfigs")
        if self.__doingfullconfigs is True:
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
        logger.debug("dogetallconfigs.....")

        allCommands = [
            "GetCommands",
            "GetDeviceTypes",
            "GetGatewayDevices",
            "GetGatewayModules", # includes ModuleDeviceTypes, DeviceTypeCommands
            "GetGatewayConfigs",
#            "GetModuleVariables",
#            "getGatewayUserTokens",
#            "getGatewayUsers",
        ]
        for item in allCommands:
            logger.debug("sending command: %s"  % item)

            self._appendFullDownloadQueue(item)
            self.AMQPYombo.sendDirectMessage(**self._generateRequest(item, "All"))
        #todo: Put in a looping call and track re-requests for 'lost' items'.

    def _generateRequest(self, request_type, requestContent):
        request = {
            "exchange_name"  : "ysrv.e.gw_config",
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
        if table not in self.__pendingUpdates:
            logger.debug("Adding table to request queue: %s" % table)
            self.__pendingUpdates.append(table)

    def _removeFullDownloadQueue(self, table):
        logger.debug("Removing table to request queue: %s" % table)
        logger.debug("Configs pending: {pendingUpdates}", pendingUpdates=self.__pendingUpdates)
        if table in self.__pendingUpdates:
            self.__pendingUpdates.remove(table)
        logger.debug("Configs pending: {pendingUpdates}", pendingUpdates=self.__pendingUpdates)

        if len(self.__pendingUpdates) == 0 and self.__doingfullconfigs is True:
            self.__doingfullconfigs = False
            self.loadDefer.callback(10) # a made up number.

