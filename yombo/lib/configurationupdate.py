# cython: embedsignature=True
# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Handles getting configuration updates from the Yombo servers.

.. warning::

   Module developers should not access any of these functions
   or variables.  They are used internally.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2016 by Yombo.
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
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.exceptions import YomboWarning

logger = get_logger('library.configurationupdate')

class ConfigurationUpdate(YomboLibrary):
    """
    Responsible for processing configuration update requests.
    """
    #zope.interface.implements(ILibrary)

    config_items = {
            'commands' : {'table': "commands", 'map' : {
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
            'command_device_types' : {'table': "command_device_types", 'map' : {
                'device_type_id' : 'device_type_id',
                'command_id' : 'command_id',
            }},
            'gateway_devices' : {'table': "devices", 'map' : {
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
            'device_types' : {'table': "device_types", 'map' : {
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
            'device_type_modules' : {'table': "device_type_modules", 'map' : {
                'device_type_id' : 'device_type_id',
                'module_id' : 'module_id',
                'priority' : 'priority',
            }},

            'gateway_modules' : {'table': "modules", 'map' : {
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

            'gateway_configs' : {}, # Processed with it's own catch.
            'variables' : {'table': "variables", 'map' : {
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
#            "gateway_modules",
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
        self.gpg_key = self._Configs.get("core", "gpgkeyid", '')
        self.gpg_key_ascii = self._Configs.get("core", "gpgkeyascii", '')
        self.gwuuid = self._Configs.get("core", "gwuuid")

        if self.loader.unittest:  # if we are testing, don't try to download configs
            return
        self.AMQPYombo = self._Libraries['AMQPYombo']
        self.loadDefer = defer.Deferred()
#        self.loadDefer.addCallback(self.__loadFinish)
        self._LocalDBLibrary = self._Libraries['localdb']

    def _load_(self):
        """
        """
        self._fullDownloadStartTime = time()
        self.get_all_configs()
        self._getAllConfigsLoggerLoop = LoopingCall(self._show_pending_configs)
        self._getAllConfigsLoggerLoop.start(5, False)  # Display a log line for pending downloaded, false - Dont' show now


#        self.cache = ExpiringDict(max_len=100, max_age_seconds=30)
        return self.loadDefer
    
    # def __loadFinish(self, nextSteps):
    #     """
    #     Called when all the configurations have been received from the Yombo servers.
    #     """
    #     return 1

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

    def incoming_config_queue_add(self, msg):
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
            self.process_config(config)

    def amqp_direct_incoming(self, send_info, deliver, props, msg):
        # do nothing on requests for now.... in future if we ever accept requests, we will.
        if props.headers['type'] != "response":
            raise YomboWarning("ConfigurationUpdate::amqp_direct_incoming only accepts 'Response' type message.") # For now...

        config_item = props.headers['config_item']
        config_type = props.headers['config_type']
        inputType = props.headers['type']
 #       try:
        self.process_config(inputType, config_item, config_type, msg)
#        except:
#            raise YomboWarning("Unable to pre")

    @inlineCallbacks
    def process_config(self, inputType, config_item, config_type, msg):
        logger.debug("in process_config ->> config_item: {config_item}", config_item=config_item)

        # make sure the command exists
        if config_item not in self.config_items:
            logger.warn("ConfigurationUpdate::process_config - '{config_item}' is not a valid configuration item. Skipping.", config_item=config_item)
            return
        elif config_item == "gateway_configs":
            payload = msg['data']
            for section in payload:
                for key in section['Values']:
                   self._Configs.set(section['Section'], key['Key'], key['Value'])
        elif config_item == "gateway_variable":
            records = msg['data']["configdata"]
            sendUpdates = []
            for record in records:
                if self._Libraries['configuration'].get_config_time(record['section'], record['item']) > record['updated']:
                  self._Configs.set(record['section'], record['item'], record['value'])
                else: #the gateway is newer
                  sendUpdates.append({'section': record['section'],
                                      'item'   : record['item'],
                                      'value'  : record['value']})

# needs to be implemented on server first!!
#            if len(sendUpdates):
#              self.gateway_control.sendQueueAdd(self._generateMessage({'cmd' : 'setGatewayVariables', 'configdata':sendUpdates}))
#            self._removeFullTableQueue('GatewayVariablesTable')
        elif config_item in self.config_items:
            logger.debug("ConfigurationUpdate::process_config - Doing config for: {config_item}", config_item=config_item)
            configs_db = self.config_items[config_item]

            data = []
            if 'data_type' in msg:
                if msg['data_type'] == 'object': # a single response
                    logger.debug("Processing single object config response.")
                    data.append(msg['data'])
                elif msg['data_type'] == 'objects': # An array of responses
                    logger.debug("Processing multiple object config response.")
                    data = msg['data']
            else:
                if isinstance(msg, list):
                    data = msg
                elif isinstance(msg, dict):
                    data = data.append(msg)
                else:
                    raise YomboWarning("Cannot process configuration update")

            tempConfig = {}  # Usef for various tracking. Variable depends on config_item being processed.
            tempIndex = {}  # Usef for various tracking. Variable depends on config_item being processed.
            tempStorage = {}  # Usef for various tracking. Variable depends on config_item being processed.

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

#                logger.debug("Pre checking nested %s" % config_item)
                # process any nested items here.
                if config_item == 'gateway_modules':
                    if '1' not in tempConfig:
                        tempConfig['1'] = {
                            'inputType' : 'nested',
                            'config_item' : 'device_type_modules',
                        }
                        tempConfig['2'] = {
                            'inputType' : 'nested',
                            'config_item' : 'command_device_types',
                        }
                        tempConfig['3'] = {
                            'inputType' : 'nested',
                            'config_item' : 'device_types',
                        }
                        tempConfig['4'] = {
                            'inputType' : 'nested',
                            'config_item' : 'variables',
                        }
                        tempIndex['1'] = []  # device_type_modules
                        tempIndex['2'] = []  # command_device_types
                        tempIndex['3'] = []  # device_types
                        tempIndex['4'] = []  # variables
                        tempStorage['1'] = []
                        tempStorage['2'] = []
                        tempStorage['3'] = []
                        tempStorage['4'] = []

#                    logger.info("devicetypes: %s" % record['device_types'][)
                    if 'DeviceTypes' in record:
#                        logger.debug("Call nested: {record}" % record=record)
                        for tempDT in record['DeviceTypes']:
                            if tempDT['UUID'] not in tempIndex['3']:
#                                print "adding device type: %s" % tempDT
                                tempIndex['3'].append(tempDT['UUID'])
                                tempStorage['3'].append(tempDT)

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
                                        'command_id' : dtc['UUID'],  #dtc = Commanddevice_types
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
                # end if config_item == 'gateway_modules'

                elif config_item == 'gateway_devices':
                    if '1' not in tempConfig:
                        tempConfig['1'] = {
                            'inputType' : inputType,
                            'config_item' : 'variables',
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
                self.process_config(tempConfig[key]['inputType'], tempConfig[key]['config_item'], config_type, tempStorage[key])

            if len(save_records) > 0:
#                for record in save_records:
#                    yield self._LocalDBLibrary.insert(configs_db['table'], record)
#                print "saving records: (%s): %s" % (configs_db['table'], save_records)
                yield self._LocalDBLibrary.insert_many(configs_db['table'], save_records)
        else:
            raise YomboWarning("Unknown type on processing configuration update.")
        if inputType == "response" and config_type == "full":
            self._removeFullDownloadQueue("get_" + config_item)
        self.__incomingConfigQueueCheck()

    @inlineCallbacks
    def get_all_configs(self):
        # don't over do it on the the full config download. Might be a quick restart of gateway.
        logger.debug("About to do get_all_configs")
        if self.__doingfullconfigs is True:
            returnValue(False)
        lastTime = self._Configs.get("core", "lastFullConfigDownload", 1)
        if int(lastTime) > (int(time() - 10)):
            logger.debug("Not downloading fullconfigs due to race condition.")
            returnValue(None)

        self.__doingfullconfigs = True
        self._Configs.set("core", "lastFullConfigDownload", int(time()) )

        logger.debug("Preparing for full configuration download.")
        for key, item in self.config_items.iteritems():
            if 'table' not in item:
                continue
            yield self._LocalDBLibrary.delete(item['table'])

        self.do_get_all_configs()

    def do_get_all_configs(self, junk=None):
        logger.debug("do_get_all_configs.....")

        allCommands = [
            "get_commands",
            "get_device_types",
            "get_gateway_devices",
            "get_gateway_modules", # includes Moduledevice_types, Commanddevice_types
            "get_gateway_configs",
#            "GetModuleVariables",
#            "getGatewayUserTokens",
#            "getGatewayUsers",
        ]
        for item in allCommands:
            logger.debug("sending command: {item}", item=item)

            self._appendFullDownloadQueue(item)
            self.AMQPYombo.send_amqp_message(**self._generate_request_message(item, "All"))
        #todo: Put in a looping call and track re-requests for 'lost' items'.

    def _generate_request_message(self, request_type, requestContent):
        request = {
            "exchange_name": "ysrv.e.gw_config",
            "source"       : "yombo.gateway.lib.configurationupdate",
            "destination"  : "yombo.server.configs",
            "callback"     : self.amqp_direct_incoming,
            "body": {
              "data_type": "object",
              "request"  : requestContent,
            },
            "request_type": request_type,
        }
        return self.AMQPYombo.generate_request_message(**request)

    def _appendFullDownloadQueue(self, table):
        """
        Adds an item to pending table queue.
        
        Will be removed as each config item is returned by _removeFullTableQueue.
        """
        if table not in self.__pendingUpdates:
            logger.debug("Adding table to request queue: {table}", table=table)
            self.__pendingUpdates.append(table)

    def _removeFullDownloadQueue(self, table):
        logger.debug("Removing table from request queue: {table}", table=table)
        logger.debug("Configs pending: {pendingUpdates}", pendingUpdates=self.__pendingUpdates)
        if table in self.__pendingUpdates:
            self.__pendingUpdates.remove(table)
        logger.debug("Configs pending: {pendingUpdates}", pendingUpdates=self.__pendingUpdates)

        if len(self.__pendingUpdates) == 0 and self.__doingfullconfigs is True:
            self.__doingfullconfigs = False
            self._getAllConfigsLoggerLoop.stop()
            reactor.callLater(0.1, self.loadDefer.callback, 10) # give DB some breathing room

    def _show_pending_configs(self):
        waitingTime = time() - self._fullDownloadStartTime
        logger.info("Waited %s for startup; pending these configurations: %s" % (waitingTime, self.__pendingUpdates))
