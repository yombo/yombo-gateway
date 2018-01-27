# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Responsible for downloading gateway configuration items from the yombo API servers.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
    and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import os
import shutil
import time
import zipfile


from pprint import pprint

# Import twisted libraries
from twisted.internet import defer
from twisted.web.client import downloadPage

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger('library.configuration_download')

class ConfigurationDownload(YomboLibrary):
    """
    Handle downloading of configurations on startup.

    A semaphore is used to allow processing and downloading of multple configurations
    at once.
    """
    MAX_DOWNLOAD_CONCURRENT = 5  # config: misc:configdownloadconcurrent
    # too many, and our database gets SLOW
    config_item_map = {
        'devices': 'gateway_devices'
    }

    config_items = {
            'categories': {
                'dbclass': "Category",
                'table': "categories",
                'library': None,
                'functions': {
                    # 'process': "enable_command",
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'purgeable': False,
                'map': {
                    'id': 'id',
                    'category_type': 'category_type',
                    'machine_label': 'machine_label',
                    'label': 'label',
                    'description': 'description',
                    'status': 'status',
                    'created_at': 'created',
                    'updated_at': 'updated',
                    # '': '',
                }
            },

            'gateway_dns_name': {
                'dbclass': "none",
                'table': "none",
                'library': None,
                'functions': {
                },
                'purgeable': False,
                'map': {
                }
            },

            'gateway_commands': {
                'dbclass': "Command",
                'table': "commands",
                'library': "commands",
                'functions': {
                    # 'process': "enable_command",
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'purgeable': False,
                'map': {
                    'id': 'id',
                    'machine_label': 'machine_label',
                    'voice_cmd': 'voice_cmd',
                    'label': 'label',
                    'description': 'description',
                    'always_load': 'always_load',
                    'created_at': 'created',
                    'updated_at': 'updated',
                    'status': 'status',
                    'public': 'public',
                    # '': '',
                }
            },

            'gateway_devices': {
                'dbclass': "Device",
                'table': "devices",
                'library': "devices",
                'functions': {
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'purgeable': True,
                'map': {
                    'id': 'id',
                    'area_id': 'area_id',
                    'location_id': 'location_id',
                    'machine_label': 'machine_label',
                    'label': 'label',
                    'notes': 'notes',
                    'attributes': 'attributes',
                    'description': 'description',
                    'gateway_id': 'gateway_id',
                    'device_type_id': 'device_type_id',
                    'voice_cmd': 'voice_cmd',
                    'voice_cmd_order': 'voice_cmd_order',
                    'voice_cmd_src': 'voice_cmd_src',
                    'pin_code': 'pin_code',
                    'pin_required': 'pin_required',
                    'pin_timeout': 'pin_timeout',
                    'statistic_label': 'statistic_label',
                    'energy_type': 'energy_type',
                    'energy_tracker_source': 'energy_tracker_source',
                    'energy_tracker_device': 'energy_tracker_device',
                    'energy_map': 'energy_map',
                    'created_at': 'created',
                    'updated_at': 'updated',
                    'status': 'status',
                }
            },

            'gateway_device_command_inputs': {
                'dbclass': "DeviceCommandInput",
                'table': "device_command_inputs",
                'library': None,
                'functions': {
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'purgeable': False,
                'map': {
                    'id': 'id',
                    'category_id': 'category_id',
                    'device_type_id': 'device_type_id',
                    'command_id': 'command_id',
                    'input_type_id': 'input_type_id',
                    'machine_label': 'machine_label',
                    'label': 'label',
                    'live_update': 'live_update',
                    'value_required': 'value_required',
                    'value_max': 'value_max',
                    'value_min': 'value_min',
                    'value_casing': 'value_casing',
                    'encryption': 'encryption',
                    'notes': 'notes',
                    'always_load': 'always_load',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

            'gateway_device_locations': {
                'dbclass': "DeviceLocation",
                'table': "device_locations",
                'library': None,
                'functions': {
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'purgeable': False,
                'map': {
                    'id': 'id',
                    'machine_label': 'machine_label',
                    'label': 'label',
                    'description': 'description',
                    'public': 'public',
                    'status': 'status',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

            'gateway_device_types': {
                'dbclass': "DeviceType",
                'table': "device_types",
                'library': "devicestypes",
                'functions': {
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'purgeable': False,
                'map': {
                    'id': 'id',
                    'category_id': 'category_id',
                    'platform': 'platform',
                    'machine_label': 'machine_label',
                    'label': 'label',
                    'description': 'description',
                    'always_load': 'always_load',
                    'created_at': 'created',
                    'updated_at': 'updated',
                    'public': 'public',
                    'status': 'status',
                }
            },

            'gateway_device_type_commands': {
                'dbclass': "DeviceTypeCommand",
                'table': "device_type_commands",
                'library': None,
                'functions': {
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'purgeable': False,
                'map': {
                    'id': 'id',
                    'device_type_id': 'device_type_id',
                    'command_id': 'command_id',
                    'created_at': 'created',
                }
            },

            'gateway_input_types': {
                'dbclass': "InputType",
                'table': "input_types",
                'library': "inputtypes",
                'functions': {
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'purgeable': False,
                'map': {
                    'id': 'id',
                    'category_id': 'category_id',
                    'machine_label': 'machine_label',
                    'label': 'label',
                    'description': 'description',
                    'input_regex': 'input_regex',
                    'always_load': 'always_load',
                    'created_at': 'created',
                    'updated_at': 'updated',
                    'public': 'public',
                    'status': 'status',
                }
            },

            'gateway_modules': {
                'dbclass': "Modules",
                'table': "modules",
                'library': "modules",
                'functions': {
                    # 'enabled': "enable_command",
                    # 'disabled': "enable_command",
                    # 'deleted': "enable_command",
                },
                'purgeable': True,
                'map': {
                    'module_id': 'id',
                    'gateway_id': 'gateway_id',
                    'machine_label': 'machine_label',
                    'module_type': 'module_type',
                    'label': 'label',
                    'short_description': 'short_description',
                    'medium_description': 'medium_description',
                    'description': 'description',
                    'see_also': 'see_also',
                    'repository_link': 'repository_link',
                    'issue_tracker_link': 'issue_tracker_link',
                    'install_count': 'install_count',
                    'doc_link': 'doc_link',
                    'git_link': 'git_link',
                    'prod_branch': 'prod_branch',
                    'dev_branch': 'dev_branch',
                    'prod_version': 'prod_version',
                    'dev_version': 'dev_version',
                    'install_branch': 'install_branch',
                    'always_load': 'always_load',
                    'public': 'public',
                    'status': 'status',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

            'gateway_configs': {},  # Processed with it's own catch.

            'gateway_users': {
                'dbclass': "Users",
                'table': "users",
                'library': None,
                'functions': {
                },
                'purgeable': True,
                'map': {
                    'id': 'id',
                    'gateway_id': 'gateway_id',
                    'user_id': 'user_id',
                    'email': 'email',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

            'module_device_type': {
                'dbclass': "ModuleDeviceTypes",
                'table': "module_device_types",
                'library': None,
                'functions': {
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'purgeable': False,
                'map': {
                    'id': 'id',
                    'module_id': 'module_id',
                    'device_type_id': 'device_type_id',
                    'created_at': 'created',
                }
            },

            'gateway_nodes': {
                'dbclass': "Node",
                'table': "nodes",
                'library': None,
                'functions': {
                    # 'enabled': "enable_device",
                    # 'disabled': "disable_device",
                    # 'deleted': "delete_device",
                },
                'purgeable': True,
                'map': {
                    'id': 'id',
                    'parent_id': 'parent_id',
                    'gateway_id': 'gateway_id',
                    'node_type': 'node_type',
                    'weight': 'weight',
                    'label': 'label',
                    'machine_label': 'machine_label',
                    'gw_always_load': 'gw_always_load',
                    'destination': 'destination',
                    'data': 'data',
                    'data_content_type': 'data_content_type',
                    'status': 'status',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

            'variable_groups': {
                'dbclass': "VariableGroups",
                'table': "variable_groups",
                'library': "configuration",
                'functions': {
                },
                'purgeable': False,
                'map': {
                    'id': 'id',
                    'relation_id': 'group_relation_id',
                    'relation_type': 'group_relation_type',
                    'group_machine_label': 'group_machine_label',
                    'group_label': 'group_label',
                    'group_description': 'group_description',
                    'group_weight': 'group_weight',
                    'status': 'status',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

            'variable_fields': {
                'dbclass': "VariableFields",
                'table': "variable_fields",
                'library': "configuration",
                'functions': {
                },
                'purgeable': False,
                'map': {
                    'id': 'id',
                    'group_id': 'group_id',
                    'field_machine_label': 'field_machine_label',
                    'field_label': 'field_label',
                    'field_description': 'field_description',
                    'field_weight': 'field_weight',
                    'value_required': 'value_required',
                    'value_max': 'value_max',
                    'value_min': 'value_min',
                    'value_casing': 'value_casing',
                    'encryption': 'encryption',
                    'input_type_id': 'input_type_id',
                    'default_value': 'default_value',
                    'field_help_text': 'field_help_text',
                    'multiple': 'multiple',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

            'variable_data': {
                'dbclass': "VariableData",
                'table': "variable_data",
                'library': "configuration",
                'functions': {
                },
                'purgeable': True,
                'map': {
                    'id': 'id',
                    'gateway_id': 'gateway_id',
                    'field_id': 'field_id',
                    'relation_id': 'data_relation_id',
                    'relation_type': 'data_relation_type',
                    'data': 'data',
                    'data_weight': 'data_weight',
                    'created_at': 'created',
                    'updated_at': 'updated',
                }
            },

    }

    def _init_(self, **kwargs):
        """
        Gets the library setup and preconfigures some items.  Sets up the
        semaphore for queing downloads.
        """
        self.download_deferred = None
        self.gateway_id = self._Configs.get('core', 'gwid')

        self.maxDownloadConcurrent = self._Configs.get("misc", 'configdownloadconcurrent', self.MAX_DOWNLOAD_CONCURRENT, False)
        self.allDownloads = []   # to start deferreds
        self.mysemaphore = defer.DeferredSemaphore(self.maxDownloadConcurrent)  #used to queue deferreds
        self.download_configs()

    def _stop_(self, **kwargs):
        if self.download_deferred is not None and self.download_deferred.called is False:
            self.download_deferred.callback(1)  # if we don't check for this, we can't stop!

    @defer.inlineCallbacks
    def download_configs(self):
        """
        Create all the YomboAPI requests to download configs.
        """
        logger.info("Requesting system configurations from server. This can take a few seconds.")
        gwid = self.gateway_id

        allCommands = [
            {
                'api': "v1/category",
                'config_item': "categories",
            },
            {
                'api': "v1/gateway/%s/commands" % gwid,
                'config_item': "commands",
            },
            {
                'api': "v1/gateway/%s/cluster" % gwid,
                'config_item': "gateways",
            },
            {
                'api': "v1/devices/cluster",
                'config_item': "devices",
            },
            {
                'api': "v1/device_locations",
                'config_item': "device_locations",
            },
            {
                'api': "v1/modules",
                'config_item': "modules",
            },
            {
                'api': "v1/device_type_commands",
                'config_item': "device_type_commands",
            },
            {
                'api': "v1/category",
                'config_item': "",
            },
        ]
            "get_gateway_commands",
            "get_gateway_devices",  # Includes device variable groups/fields/data
            "get_gateway_device_locations",  # Includes device variable groups/fields/data
            "get_gateway_device_types",
            "get_gateway_modules",  # Includes module variable groups/fields/data

            "get_gateway_device_type_commands",
            "get_gateway_device_command_inputs",
            "get_gateway_input_types",
            "get_gateway_users",
            "get_gateway_dns_name",

            # "get_gateway_nodes",  # Includes module variable groups/fields/data

            # "get_gateway_input_types",
            # "get_gateway_configs",

            #            "GetModuleVariables",
            #            "getGatewayUserTokens",
            #            "getGatewayUsers",
        ]
        modules = yield self._LocalDBLibrary.get_modules_view()
        if len(modules) == 0:
            defer.returnValue(None)

        deferredList = []
        for module in modules:
            modulelabel = module.machine_label.lower()
            moduleuuid = module.id
            #pprint(module)

            if ( ( ( module.prod_version != '' and module.prod_version != None and module.prod_version != "*INVALID*") or
              ( module.dev_version != '' and module.dev_version != None and module.dev_version != "*INVALID*") ) and
#              module.install_branch != 'local') and ( not os.path.exists("yombo/modules/%s/.git" % modulelabel )  ):
              module.install_branch != 'local') and ( not os.path.exists("yombo/modules/%s/.git" % modulelabel) and not os.path.exists("yombo/modules/%s/.freeze" % modulelabel)  ):
                logger.debug("Module doesn't have freeze: yombo/modules/{modulelabel}/.freeze", modulelabel=modulelabel)

                modulus = moduleuuid[0:1]
                clouduri = self.cloudfront + "modules/%s/%s/" % (str(modulus), str(moduleuuid))
                data = {}

                if module.install_branch == 'production' and module.installed_version != module.prod_version:
                    print("version compare: %s != %s" % (module.installed_version, module.prod_version))
                    data = {'download_uri'    : str(clouduri + module.prod_version + ".zip"),
                            'zip_file'   : self.download_path + modulelabel + "_" + module.prod_version + ".zip",
                            'type'      : "prod_version",
                            'install_version': module.prod_version,
                            'module'    : module,
                            }
                elif module.install_branch == 'development' and module.dev_version != "" and module.installed_version != module.dev_version:
                    data = {'download_uri': str(clouduri + module.dev_version + ".zip"),
                            'zip_file': self.download_path + modulelabel + "_" + module.dev_version + ".zip",
                            'type': "dev_version",
                            'install_version': module.dev_version,
                            'module': module,
                            }
                else:
                    logger.debug("Either no correct version to install, or version already installed..")
                    continue

                logger.debug("Adding to download module queue: {modulelable} (zipurl})", modulelabel=modulelabel, zipurl=data['zip_file'])
               
#                d = self.mysemaphore.run(downloadPage, data['zip_uri'], data['zip_file'])
                d = self.mysemaphore.run(self.download_file, data)
                self.allDownloads.append(d)
                d.addErrback(self.download_file_failed, data)
                d.addCallback(self.unzip_file, data)
                d.addErrback(self.unzip_file_failed, data)
                d.addCallback(self.update_database, data)
                d.addErrback(self.update_database_failed, data)

        self.download_list_deferred = yield defer.DeferredList(self.allDownloads)
        defer.returnValue(self.download_list_deferred)
    
    def download_cleanup(self, something):
        """
        When the downloads are completed, come here for any house cleaning.
        """
        logger.info("Done with downloads!")

    def download_file(self, data):
        """
        Helper function to download the module as a zip file.
        """
        logger.debug("download_file data:  {data}", data=data)
        download_uri =  data['download_uri']
        zip_file =  data['zip_file']
        logger.debug("getting uri: {download_uri}  saving to:{zip_file}", download_uri=download_uri, zip_file=zip_file)
        d = downloadPage(data['download_uri'], data['zip_file'])
        return d

    def download_file_failed(self, data, data2):
        """
        Helper function for cleanup is called when the download failed.  Won't
        continue processing the zip file.
        """
        logger.warn("Couldn't download the file...")
        return defer.fail()

    def unzip_file(self, tossaway, data):
        """
        Helper function to unzip the module and place the module in the
        final location.
        
        :param tossaway: Blank, nothing to see here.
        :type data: None
        :param data: Contains the module information, passed on.
        :type data: dict
        """
        logger.debug("unzip_file data:  {data}", data=data)
        logger.debug("unzip_file data:  {data_module}", data_module=data['module'])
        logger.debug("unzip_file data:  {data_module_label}", data_module_label=data['module'].machine_label)
        moduleLabel = data['module'].machine_label
        moduleLabel = moduleLabel.lower()
        logger.debug("Modulelabel = {moduleLabel}", moduleLabel=moduleLabel)
        zip_file = data['zip_file']
        modDir = 'yombo/modules/' + moduleLabel

        if not os.path.exists(modDir):
            os.makedirs(modDir)
        else:
            for root, dirs, files in os.walk('modDir'):
                for f in files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    shutil.rmtree(os.path.join(root, d))
        z = zipfile.ZipFile(zip_file)
        z.extractall(modDir)
        # listing = os.listdir(modDir)
        return "1"

    def unzip_file_failed(self, data, data2):
        """
        Helper function for cleanup when the zip process fails
        or unable to move the module to it's final destination.
        """
        logger.warn("unzip failed ({data}) ({data2})", data=data, data2=data2)
        if data != None:
          return defer.fail()

    def update_database(self, tossaway, data):
        """

        :param tossaway: Blank, nothing to see here.
        :type data: None
        :param data: Contains the module information, passed on.
        :type data: dict
        :return:
        """
        module = data['module']
        module_id = module.id

        ModuleInstalled = self._LocalDBLibrary.get_model_class("ModuleInstalled")

        if module.install_at is None:
            module_installed = self._LocalDBLibrary.modules_install_new(
                {'module_id': module_id,
                 'installed_version': data['install_version'],
                 'install_at': int(time.time())
                 })
        else:
            module_installed = ModuleInstalled.find(['module_id = ?', module_id])
            module_installed.installed_version = data['install_version']
            module_installed.install_at = int(time.time())
            module_installed.save()
        return "1"

    def update_database_failed(self, data, data2):
        """
        Helper function for cleanup is called when unable to update the database.
        """
        logger.warn("Download Version, updateDatabase failed ({data}) ({data2})", data=data, data2=data2)
        if data != None:
          return defer.fail()
