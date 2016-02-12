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
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall

from yombo.ext.expiringdict import ExpiringDict

# Import Yombo libraries
from yombo.core.library import YomboLibrary
#from yombo.core.message import Message
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

    configTypes = {
            'Commands' : {'table': "commands", 'map' : {
                'Uri' : 'uri',
                'UUID' : 'id',
                'machineLabel' : 'machine_label',
                'voice_cmd' : 'voice_cmd',
                'label' : 'label',
                'description' : 'description',
                'inputtype' : 'input_type_id',
                'liveupdate' : 'live_update',
                'created' : 'created',
                'updated' : 'updated',
                'status' : 'status',
                'public' : 'public',
#                '' : '',
            }},
            'CommandDeviceTypes' : {'table': "command_device_types", 'map' : {
                'device_type_id' : 'device_type_id',
                'command_id' : 'command_id',
            }},
            'GatewayDevices' : {'table': "devices", 'map' : {
                'UUID' : 'id',
                'Uri' : 'uri',
#                'machineLabel' : 'machineLabel',  #Not implemented yet.
                'Label' : 'label',
                'Notes' : 'notes',
                'Description' : 'description',
                'GatewayUUID' : 'gateway_id',
                'DeviceTypeUUID' : 'device_type_id',
                'VoiceCmd' : 'voice_cmd',
                'VoiceCmdOrder' : 'voice_cmd_order',
                'voiceCmdSrc' : 'Voice_cmd_src',
                'PinCode' : 'pin_code',
                'PinRequired' : 'pin_required',
                'PinTimeout' : 'pin_timeout',
                'Created' : 'created',
                'Updated' : 'updated',
                'Status' : 'status',
            }},
            'DeviceTypes' : {'table': "device_types", 'map' : {
                'UUID' : 'id',
                'Uri' : 'uri',
                'MachineLabel' : 'machine_label',
                'Label' : 'label',
                'DeviceClass' : 'device_class',
                'Description' : 'description',
                'LiveUpdate' : 'live_update',
                'Public' : 'public',
                'Created' : 'created',
                'Updated' : 'updated',
                'Status' : 'status',
#                '' : '',
            }},
            'DeviceTypeModules' : {'table': "device_type_modules", 'map' : {
                'device_type_id' : 'device_type_id',
                'module_id' : 'module_id',
                'priority' : 'priority',
            }},

            'GatewayModules' : {'table': "modules", 'map' : {
                'UUID' : 'id',
                'Uri' : 'uri',
                'MachineLabel' : 'machine_label',
                'ModuleType' : 'module_type',
                'Label' : 'label',
                'Description' : 'description',
                'InstallNotes' : 'instal_notes',
                'DocLink' : 'doc_link',
                'ProdVersion' : 'prod_version',
                'DevVersion' : 'dev_version',
                'InstallBranch' : 'install_branch',
                'Public' : 'public',
                'Created' : 'created',
                'Updated' : 'updated',
                'Status' : 'status',
            }},

            'GatewayConfigs' : {}, # Processed with it's own catch.
            'Variables' : {'table': "variables", 'map' : {
                'VariableType' : 'variable_type',
                'ForeignUUID' : 'foreign_id',
                'VariableUUID' : 'variable_id',
                'Weight' : 'weight',
                'DataWeight' : 'data_weight',
                'MachineLabel' : 'machine_label',
                'Label' : 'label',
                'Value' : 'value',
                'Updated' : 'updated',
                'Created' : 'created',
            }},

#            "GatewayDetails",
#            "GatewayModules",
#            "GatewayUserTokens",
#            "GatewayVariables",
#            "GatewayUsers",
        }

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

        if self.loader.unittest:  # if we are testing, don't try to download configs
            return
        self.AMQPYombo = getComponent('yombo.gateway.lib.AMQPYombo')
        self.loadDefer = defer.Deferred()
        self.loadDefer.addCallback(self.__loadFinish)
        self._LocalDBLibrary = self._Libraries['localdb']
        self.get_all_configs()

#        self.cache = ExpiringDict(max_len=100, max_age_seconds=30)
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

    @inlineCallbacks
    def processConfig(self, inputType, configType, configStatus, msg):
        logger.debug("processing configType: {configType}", configType=configType)

        # make sure the command exists
        if configType not in self.configTypes:
            logger.warn("ConfigurationUpdate::processConfig - '{configType}' is not a valid configuration item. Skipping.", configType=configType)
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
        elif configType in self.configTypes:
            logger.debug("ConfigurationUpdate::processConfig - Doing config for: {configType}", configType=configType)
            configs_db = self.configTypes[configType]

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

            tempConfig = {}  # Usef for various tracking. Variable depends on configType being processed.
            tempIndex = {}  # Usef for various tracking. Variable depends on configType being processed.
            tempStorage = {}  # Usef for various tracking. Variable depends on configType being processed.

            save_records = []
            for record in data:
                items = record.items()
                temp_record = {}

                for col, val in items:
                    if col not in configs_db['map']:
#                        logger.debug("## Col (%s) not in table.." % col)
                        continue
#                    print "col = %s (%s)" % (col, configs_db['map'][col])
                    if self._LocalDBLibrary.db_model[configs_db['table']][configs_db['map'][col]]['type'] == "INTEGER":
                        val=int(val)
                    elif self._LocalDBLibrary.db_model[configs_db['table']][configs_db['map'][col]]['type'] == "REAL":
                        val=float(val)
                    elif type(val) is dict:
                        val = sqlite3Binary(cPickle.dumps(val, cPickle.HIGHEST_PROTOCOL))
#                    temp = (col, decryptPGP(val))
                    temp_record[configs_db['map'][col]] = val
                save_records.append(temp_record)

#                logger.debug("Pre checking nested %s" % configType)
                # process any nested items here.
                if configType == 'GatewayModules':
                    if '1' not in tempConfig:
                        tempConfig['1'] = {
                            'inputType' : 'nested',
                            'configType' : 'DeviceTypeModules',
                        }
                        tempConfig['2'] = {
                            'inputType' : 'nested',
                            'configType' : 'CommandDeviceTypes',
                        }
                        tempConfig['3'] = {
                            'inputType' : 'nested',
                            'configType' : 'DeviceTypes',
                        }
                        tempConfig['4'] = {
                            'inputType' : 'nested',
                            'configType' : 'Variables',
                        }
                        tempIndex['1'] = []  # DeviceTypeModules
                        tempIndex['2'] = []  # CommandDeviceTypes
                        tempIndex['3'] = []  # DeviceTypes
                        tempIndex['4'] = []  # Variables
                        tempStorage['1'] = []
                        tempStorage['2'] = []
                        tempStorage['3'] = []
                        tempStorage['4'] = []

#                    logger.info("devicetypes: %s" % record['DeviceTypes'][)
                    if 'DeviceTypes' in record:
                        for tempDT in record['DeviceTypes']:
                            if tempDT['UUID'] not in tempIndex['3']:
#                                print "adding device type: %s" % tempDT
                                tempIndex['3'].append(tempDT['UUID'])
                                tempStorage['3'].append(tempDT)

    #                    logger.info("Call nested: %s" % record)
                        for dt in record['DeviceTypes']:
                            if dt['UUID'] not in tempIndex['1']:
                                tempStorage['1'].append({
                                    'device_type_id' : dt['UUID'],
                                    'module_id' : record['UUID'],  # record = module
                                    'priority' : dt['Priority'],
                                })

                            for dtc in dt['Commands']:
                                if dt['UUID'] not in tempIndex['2']:
                                    tempStorage['2'].append({
                                        'device_type_id' : dt['UUID'],    #dt = devicetype
                                        'command_id' : dtc['UUID'],  #dtc = CommandDeviceTypes
                                    })
                    # ModuleConfigs
                    if 'ModuleConfigs' in record:
                        for tempGroup in record['ModuleConfigs']:
                            for tempField in tempGroup['Fields']:
                                if tempField['FieldUUID'] not in tempIndex['4']:
                                    tempIndex['4'].append(tempField['FieldUUID'])

                                field = {
                                    'VariableType': 'module',
                                    'ForeignUUID' : record['UUID'],  # record = module
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

                elif configType == 'GatewayDevices':
                    if '1' not in tempConfig:
                        tempConfig['1'] = {
                            'inputType' : inputType,
                            'configType' : 'Variables',
                        }
                        tempIndex['1'] = []  # DeviceConfigs
                        tempStorage['1'] = []
                    # DeviceConfigs
                    if 'DeviceConfigs' in record:
                        for tempGroup in record['DeviceConfigs']:
                            for tempField in tempGroup['Fields']:
                                if tempField['FieldUUID'] not in tempIndex['1']:
                                    tempIndex['1'].append(tempField['FieldUUID'])

                                field = {
                                    'VariableType': 'device',
                                    'ForeignUUID' : record['UUID'],  # record = device
                                    'VariableUUID' : tempGroup['VariableUUID'],
                                    'Weight' : tempGroup['Weight'],
                                    'DataWeight' : tempField['Weight'],
                                    'MachineLabel' : tempField['MachineLabel'],
                                    'Label' : tempField['Label'],
                                    'Value' : tempField['Value'],
                                    'Updated' : tempField['Updated'],
                                    'Created' : tempField['Created'],
                                }
                                tempStorage['1'].append(field)
            for key, value in tempStorage.iteritems():
#                logger.info("key: {key}, value: {value}", key=key, value=value)
                self.processConfig(tempConfig[key]['inputType'], tempConfig[key]['configType'], configStatus, tempStorage[key])

            if len(save_records) > 0:
#                for record in save_records:
#                    yield self._LocalDBLibrary.insert(configs_db['table'], record)
                yield self._LocalDBLibrary.insert_many(configs_db['table'], save_records)
        else:
            raise YomboWarning("Unknown type on processing configuration update.")

        if inputType == "Response" and configStatus == "Full":
            self._removeFullDownloadQueue("Get" + configType)
        self.__incomingConfigQueueCheck()

    @inlineCallbacks
    def get_all_configs(self):
        # don't over do it on the the full config download. Might be a quick restart of gateway.
        logger.info("About to do get_all_configs")
        if self.__doingfullconfigs is True:
            returnValue(False)
        lastTime = getConfigValue("core", "lastFullConfigDownload", 1)
        if int(lastTime) > (int(time() - 10)):
            logger.debug("Not downloading fullconfigs due to race condition.")
            returnValue(None)

        self.__doingfullconfigs = True
        setConfigValue("core", "lastFullConfigDownload", int(time()) )

        logger.debug("Preparing for full configuration download.")
        for key, item in self.configTypes.iteritems():
            if 'table' not in item:
                continue
#            print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! DELETE START  %s !!!!!!!!!!!!!!!!!!!!!!!!!!!!111" % item['table']
            yield self._LocalDBLibrary.delete(item['table'])
#            print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! DELETE DONE %s !!!!!!!!!!!!!!!!!!!!!!!!!!!!111" %item['table']

        self.do_get_all_configs()

    def do_get_all_configs(self, junk=None):
        logger.debug("do_get_all_configs.....")

        allCommands = [
            "GetCommands",
            "GetDeviceTypes",
            "GetGatewayDevices",
            "GetGatewayModules", # includes ModuleDeviceTypes, CommandDeviceTypes
            "GetGatewayConfigs",
#            "GetModuleVariables",
#            "getGatewayUserTokens",
#            "getGatewayUsers",
        ]
        for item in allCommands:
            logger.debug("sending command: {item}", item=item)

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
            logger.debug("Adding table to request queue: {table}", table=table)
            self.__pendingUpdates.append(table)

    def _removeFullDownloadQueue(self, table):
        logger.debug("Removing table to request queue: {table}", table=table)
        logger.debug("Configs pending: {pendingUpdates}", pendingUpdates=self.__pendingUpdates)
        if table in self.__pendingUpdates:
            self.__pendingUpdates.remove(table)
        logger.debug("Configs pending: {pendingUpdates}", pendingUpdates=self.__pendingUpdates)

        if len(self.__pendingUpdates) == 0 and self.__doingfullconfigs is True:
            self.__doingfullconfigs = False
            self.loadDefer.callback(10) # a made up number.

