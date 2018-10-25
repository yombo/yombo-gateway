# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
.. rst-class:: floater

.. note::

  * End user documentation: `Modules @ User Documentation <https://yombo.net/docs/gateway/web_interface/modules>`_
  * For library documentation, see: `Modules @ Library Documentation <https://yombo.net/docs/libraries/modules>`_

Manages all modules within the system. Provides a single reference to perform module lookup functions, etc.

Also calls module hooks as requested by other libraries and modules.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/modules.html>`_
"""
# Import python libraries
import configparser
from hashlib import sha224
from functools import partial, reduce
import os.path
from pyclbr import readmodule
from time import time
import traceback

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred, Deferred, DeferredList

# Import Yombo libraries
from yombo.core.exceptions import YomboHookStopProcessing, YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.core.settings as settings
from yombo.utils import (search_instance, do_search_instance, dict_merge, read_file, bytes_to_unicode,
    get_python_package_info, global_invoke_all)

from yombo.utils.maxdict import MaxDict
import collections


logger = get_logger('library.modules')

SYSTEM_MODULES = {
    # This module was removed during the automation revamp. This is left here for future
    # reference on how to add system modules.
    # 'automationhelpers': {
    #     'id': 'automationhelpers',  # module_id
    #     'gateway_id': 'local',
    #     'module_type': 'logic',
    #     'machine_label': 'AutomationHelpers',
    #     'label': 'Automation Helpers',
    #     'short_description': "Adds basic platforms to the automation rules.",
    #     'medium_description': "Adds basic platforms to the automation rules.",
    #     'description': "Adds basic platforms to the automation rules.",
    #     'medium_description_html': "Adds basic platforms to the automation rules.",
    #     'description_html': "Adds basic platforms to the automation rules.",
    #     'install_branch': 'system',
    #     'install_count': '',
    #     'see_also': '',
    #     'prod_branch': '',
    #     'dev_branch': '',
    #     'prod_version': '',
    #     'dev_version': '',
    #     'repository_link': '',
    #     'issue_tracker_link': '',
    #     'doc_link': 'https://yg2.in/about_rules',
    #     'git_link': '',
    #     'public': '2',
    #     'status': '1',
    #     'created_at': int(time()),
    #     'updated_at': int(time()),
    #     'load_source': 'system modules',
    #     }
    }


class Modules(YomboLibrary):
    """
    A single place for modudule management and reference.
    """

    _rawModulesList = {}

    modules = {}  # Stores a list of modules. Populated by the loader module at startup.

    _localModuleVars = {}  # Used to store modules variables from file import

    def __contains__(self, module_requested):
        """
        .. note:: The command must be enabled to be found using this method. Use :py:meth:`get <Commands.get>`
           to set status allowed.

        Checks to if a provided command id, label, or machine_label exists.

            >>> if '137ab129da9318' in self._Commands:

        or:

            >>> if 'living room light' in self._Commands:

        :raises YomboWarning: Raised when request is malformed.
        :param module_requested: The command ID, label, or machine_label to search for.
        :type module_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(module_requested)
            return True
        except Exception as e:
            return False

    def __getitem__(self, module_requested):
        """
        .. note:: The module must be enabled to be found using this method. Use :py:meth:`get <Modules.get>`
           to set status allowed.

        Attempts to find the device requested using a couple of methods.

            >>> off_cmd = self._Modules['Sjho381jSASD013ug']  #by id

        or:

            >>> off_cmd = self._Modules['homevision']  #by label & machine_label

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param module_requested: The module ID, label, or machine_label to search for.
        :type module_requested: string
        :return: A pointer to the module instance.
        :rtype: instance
        """
        return self.get(module_requested)

    def __setitem__(self, module_requested, value):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, module_requested):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")
    def __iter__(self):
        """ iter modules. """
        return self.modules.__iter__()

    def __len__(self):
        """
        Returns an int of the number of modules configured.

        :return: The number of modules configured.
        :rtype: int
        """
        return len(self.modules)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo modules library"

    def keys(self):
        """
        Returns the keys (module ID's) that are configured.

        :return: A list of module IDs. 
        :rtype: list
        """
        return list(self.modules.keys())

    def items(self):
        """
        Gets a list of tuples representing the modules configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.modules.items())

    def values(self):
        return list(self.modules.values())

    def _init_(self, **kwargs):
        """
        Init doesn't do much. Just setup a few variables. Things really happen in start.
        """
        self.gateway_id = self._Configs.get('core', 'gwid', 'local', False)
        self._invoke_list_cache = {}  # Store a list of hooks that exist or not. A cache.
        self.hook_counts = {}  # keep track of hook names, and how many times it's called.
        self.hooks_called = MaxDict(400, {})
        self.module_search_attributes = ['_module_id', '_module_type', '_label', '_machine_label', '_description',
            '_short_description', '_medium_description', '_public', '_status']
        self.disabled_modules = {}
        self.modules_that_are_starting = {}  # a place for modules to register their status.

    def _notification_get_targets_(self, **kwargs):
        """ Hosting here since loader isn't properly called... """
        return {
            'module_updated': 'Module information updated.',
            'module_added': 'Module added, will work on next restart.',
            'module_enabled': 'Module has been enabled.',
            'module_disabled': 'Module has been disabled.',
            'module_removed': 'Module to be removed from system.',
        }

    @inlineCallbacks
    def init_modules(self):
        yield self._Loader.library_invoke_all("_modules_pre_init_", called_by=self)
        logger.debug("starting modules::init....")
        yield self.module_init_invoke()  # Call "_init_" of modules
        yield self._Loader.library_invoke_all("_modules_inited_", called_by=self)

    @inlineCallbacks
    def load_modules(self):
        """
        Loads the modules. Imports and calls various module hooks at startup.

        **Hooks implemented**:

        * _modules_pre_init_ : Only called to libraries, is called before modules called for _init_.
        * _init_ : Only called to modules, is called as part of the _init_ sequence.
        * _modules_inited_ : Only called to libraries, is called after modules called for _init_.
        * _preload_ : Only called to modules, is called before _load_.
        * _modules_preloaded_ : Only called to libraries, is called after modules called for _preload_.
        * _load_ : Only called to modules, is called as part of the _load_ sequence.
        * _modules_loaded_ : Only called to libraries, is called after modules called for _load_.
        * _prestart_ : Only called to modules, is called as part of the _prestart_ sequence.
        * _modules_prestarted_ : Only called to libraries, is called after modules called for _prestart_.
        * _start_ : Only called to modules, is called as part of the _start_ sequence.
        * _modules_started_ : Only called to libraries, is called after modules called for _start_.
        * _started_ : Only called to modules, is called as part of the _started_ sequence.
        * _modules_start_finished_ : Only called to libraries, is called after modules called for _started_.

        :return:
        """
        yield self.update_module_cache()

        # Pre-Load
        logger.debug("starting modules::pre-load....")
        yield self.module_invoke_all("_preload_yombo_internal_", called_by=self, allow_disable=True)
        yield self.module_invoke_all("_preload_", called_by=self, allow_disable=True)
        yield self._Loader.library_invoke_all("_modules_preloaded_", called_by=self)
        # Load
        yield self.module_invoke_all("_load_yombo_internal_", called_by=self, allow_disable=True)
        yield self.module_invoke_all("_load_", called_by=self, allow_disable=True)
        yield self._Loader.library_invoke_all("_modules_loaded_", called_by=self)

        # Pre-Start
        yield self.module_invoke_all("_prestart_yombo_internal_", called_by=self, allow_disable=True)
        yield self.module_invoke_all("_prestart_", called_by=self, allow_disable=True)
        yield self._Loader.library_invoke_all("_modules_prestarted_", called_by=self)

        # Start
        yield self.module_invoke_all("_start_yombo_internal_", called_by=self, allow_disable=True)
        yield self.module_invoke_all("_start_", called_by=self, allow_disable=True)
        yield self._Loader.library_invoke_all("_modules_started_", called_by=self)

        yield self.module_invoke_all("_started_yombo_internal_", called_by=self, allow_disable=True)
        yield self.module_invoke_all("_started_", called_by=self, allow_disable=True)
        yield self._Loader.library_invoke_all("_modules_start_finished_", called_by=self)

    @inlineCallbacks
    def unload_modules(self):
        """
        Unloads modules.

        **Hooks implemented**:

        * _module_stop_ : Only called to libraries, is called before modules called for _stop_.
        * _stop_ : Only called to modules, is called as part of the _stop_ sequence.
        * _module_unload_ : Only called to libraries, is called before modules called for _unload_.
        * _unload_ : Only called to modules, is called as part of the _unload_ sequence.

        :return:
        """
        yield self._Loader.library_invoke_all("_modules_stop_", called_by=self)
        yield self.module_invoke_all("_stop_")
        yield self._Loader.library_invoke_all("_modules_stopped_", called_by=self)

        yield self._Loader.library_invoke_all("_modules_unload_", called_by=self)
        for module_id in self.modules.keys():
            module = self.modules[module_id]
            if int(module._status) != 1:
                continue

            try:
                yield self.module_invoke(module._Name, "_unload_", called_by=self)
            except YomboWarning:
                pass
        yield self._Loader.library_invoke_all("_modules_unloaded_", called_by=self)

    @inlineCallbacks
    def prepare_modules(self):
        """
        Called by the Loader library. This simply called the build raw modules list and build requirements
        functions.

        :return:
        """
        yield self.build_raw_module_list()  # Create a list of modules, includes localmodules.ini
        yield self.build_requirements()  # Collect all the requirements files...

    @inlineCallbacks
    def build_raw_module_list(self):
        logger.debug("Building raw module list start.")
        try:
            localmodules_ini_path = "%s/localmodules.ini" % settings.arguments['working_dir']
            ini = configparser.ConfigParser()
            ini.optionxform = str
            ini.read(localmodules_ini_path)

            for section in ini.sections():
                options = ini.options(section)
                if 'mod_machine_label' in options:
                    mod_machine_label = ini.get(section, 'mod_machine_label')
                    options.remove('mod_machine_label')
                else:
                    mod_machine_label = section

                if 'mod_label' in options:
                    mod_label = ini.get(section, 'mod_label')
                    options.remove('mod_label')
                else:
                    mod_label = section

                if 'mod_short_description' in options:
                    mod_short_description = ini.get(section, 'mod_short_description')
                    options.remove('mod_short_description')
                else:
                    mod_short_description = section

                if 'mod_medium_description' in options:
                    mod_medium_description = ini.get(section, 'mod_medium_description')
                    options.remove('mod_medium_description')
                else:
                    mod_medium_description = section

                if 'mod_description' in options:
                    mod_description = ini.get(section, 'mod_description')
                    options.remove('mod_description')
                else:
                    mod_description = section

                if 'mod_medium_description_html' in options:
                    mod_medium_description_html = ini.get(section, 'mod_medium_description_html')
                    options.remove('mod_medium_description_html')
                else:
                    mod_medium_description_html = mod_medium_description

                if 'mod_description_html' in options:
                    mod_description_html = ini.get(section, 'mod_description_html')
                    options.remove('mod_description_html')
                else:
                    mod_description_html = mod_description

                if 'mod_module_type' in options:
                    mod_module_type = ini.get(section, 'mod_module_type')
                    options.remove('mod_module_type')
                else:
                    mod_module_type = ""

                if 'mod_see_also' in options:
                    mod_see_also = ini.get(section, 'mod_see_also')
                    options.remove('mod_see_also')
                else:
                    mod_see_also = ""

                if 'mod_module_type' in options:
                    mod_module_type = ini.get(section, 'mod_module_type')
                    options.remove('mod_module_type')
                else:
                    mod_module_type = ""

                if 'mod_doc_link' in options:
                    mod_doc_link = ini.get(section, 'mod_doc_link')
                    options.remove('mod_doc_link')
                else:
                    mod_doc_link = ""

                newUUID = sha224(str(mod_machine_label).encode()).hexdigest()
                self._rawModulesList[newUUID] = {
                  'id': newUUID, # module_id
                  'gateway_id': 'local',
                  'module_type': mod_module_type,
                  'machine_label': mod_machine_label,
                  'label': mod_label,
                  'short_description': mod_short_description,
                  'medium_description': mod_medium_description,
                  'description': mod_description,
                  'medium_description_html': mod_medium_description_html,
                  'description_html': mod_description_html,
                  'see_also': mod_see_also,
                  'install_count': 1,
                  'install_branch': '',
                  'prod_branch': '',
                  'dev_branch': '',
                  'repository_link': '',
                  'issue_tracker_link': '',
                  'doc_link': mod_doc_link,
                  'git_link': '',
                  'prod_version': '',
                  'dev_version': '',
                  'public': '0',
                  'status': '1',
                  'created_at': int(time()),
                  'updated_at': int(time()),
                  'load_source': 'localmodules.ini'
                }

                self._localModuleVars[mod_label] = {}
                for item in options:
                    logger.info("Adding module from localmodule.ini: {item}", item=mod_machine_label)
                    if item not in self._localModuleVars[mod_label]:
                        self._localModuleVars[mod_label][item] = {}
                    values = ini.get(section, item)
                    values = values.split(":::")
                    data = {}
                    for value in values:
                        value_hash = sha224(str(value).encode()).hexdigest()
                        data[value_hash] = {
                            'id': value_hash,
                            'weight': 0,
                            'created_at': int(time()),
                            'updated_at': int(time()),
                            'relation_id': newUUID,
                            'relation_type': 'module',
                            'value': value,
                            'value_display': value,
                            'value_orig': value,
                        }

                    variable = {
                        'data_relation_id': newUUID,
                        'data_relation_type': 'module',
                        'field_machine_label': item,
                        'field_label': item,
                        'data': data,
                        'values': [value, ],
                        'values_display': [value, ],
                        'values_orig': [value, ],
                        'data_weight': 0,
                        'field_weight': 0,
                        'encryption': "nosuggestion",
                        'input_min': -8388600,
                        'input_max': 8388600,
                        'input_casing': 'none',
                        'input_required': 0,
                        'input_type_id': "any",
                        'variable_id': 'xxx',
                        'created_at': int(time()),
                        'updated_at': int(time()),
                    }
                    self._localModuleVars[mod_label][variable['field_machine_label']] = variable

                logger.debug("Done importing variables frmom localmodule.ini")
        except IOError as xxx_todo_changeme:
            (errno, strerror) = xxx_todo_changeme.args
            logger.debug("localmodule.ini error: I/O error({errornumber}): {error}", errornumber=errno, error=strerror)

        # Local system modules.
        for module_name, data in SYSTEM_MODULES.items():
            if self._Configs.get('system_modules', data['machine_label'], 'enabled') != 'enabled':
                continue
            self._rawModulesList[data['id']] = data

        modulesDB = yield self._LocalDB.get_modules()
        for module in modulesDB:
            self._rawModulesList[module.id] = module.__dict__
            self._rawModulesList[module.id]['load_source'] = 'sql'

        logger.debug("Building raw module list done.")

    @inlineCallbacks
    def build_requirements(self):
        """
        Look thru each module and inspect it's requirements.txt file. Append/update any lines from
        these into the Loader requirements dict.

        :return:
        """
        for module_id, module in self._rawModulesList.items():
            requirements_file = 'yombo/modules/%s/requirements.txt' % module['machine_label'].lower()
            if os.path.isfile(requirements_file):
                try:
                    filesize = os.path.getsize(requirements_file)
                    if filesize == 0:
                        continue
                    input = yield read_file(requirements_file)
                except Exception as e:
                    logger.warn("Unable to process requirements file for module '{module}', reason: {e}",
                                module=module['machine_label'], e=e)
                else:
                    requirements = bytes_to_unicode(input.splitlines())
                    for line in requirements:
                        yield self._Loader.install_python_requirement(line)

    def import_modules(self):
        """
        This imports the modules into memory (using import_component) and then sets some base module
        attributes.

        :return:
        """

        for module_id, module in self._rawModulesList.items():
            module_path_name = "yombo.modules.%s" % module['machine_label']

            try:
                module_instance, module_name = self._Loader.import_component(module_path_name, module['machine_label'], 'module', module['id'])
            except ImportError as e:
                continue
            except:
                logger.error("--------==(Error: Loading Module)==--------")
                logger.error("----Name: {module_path_name}", module_path_name=module_path_name)
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.format_exc())
                logger.error("--------------------------------------------------------")
                logger.error("Not loading module: %s" % module['machine_label'])
                continue

            self.add_imported_module(module['id'], module_name, module_instance)
            self.modules[module_id]._hooks_called = {}
            self.modules[module_id]._module_id = module['id']
            self.modules[module_id]._module_type = module['module_type']
            self.modules[module_id]._machine_label = module['machine_label']
            self.modules[module_id]._label = module['label']
            self.modules[module_id]._short_description = module['short_description']
            self.modules[module_id]._medium_description = module['medium_description']
            self.modules[module_id]._description = module['description']
            self.modules[module_id]._medium_description_html = module['medium_description_html']
            self.modules[module_id]._description_html = module['description_html']
            self.modules[module_id]._install_count = module['install_count']
            self.modules[module_id]._see_also = module['see_also']
            self.modules[module_id]._repository_link = module['repository_link']
            self.modules[module_id]._issue_tracker_link = module['issue_tracker_link']
            self.modules[module_id]._doc_link = module['doc_link']
            self.modules[module_id]._git_link = module['git_link']
            self.modules[module_id]._install_branch = module['install_branch']
            self.modules[module_id]._prod_branch = module['prod_branch']
            self.modules[module_id]._dev_branch = module['prod_branch']
            self.modules[module_id]._prod_version = module['prod_version']
            self.modules[module_id]._dev_version = module['dev_version']
            self.modules[module_id]._public = module['public']
            self.modules[module_id]._status = module['status']
            self.modules[module_id]._created_at = module['created_at']
            self.modules[module_id]._updated_at = module['updated_at']
            self.modules[module_id]._load_source = module['load_source']
            self.modules[module_id]._device_types = None  # populated by Modules::module_init_invoke

            #  The following caches are built on module_init_invoke and whenever the
            #  non-cached version of the function is called.
            self.modules[module_id]._module_device_types_cached = {}  # populated by Modules::module_init_invoke
            self.modules[module_id]._module_devices_cached = {}
            self.modules[module_id]._module_variables_cached = {}

            possible_module_files = ['_devices', '_input_types']
            for possible_file_name in possible_module_files:
                try:
                    file_path = module_path_name.lower() + "." + possible_file_name
                    possible_file = __import__(file_path, globals(), locals(), [], 0)
                    module_tail = reduce(lambda p1, p2: getattr(p1, p2),
                                         [possible_file, ] + file_path.split('.')[1:])
                    classes = readmodule(file_path)
                    for name, file_class_name in classes.items():
                        klass = getattr(module_tail, name)
                        if possible_file_name == '_devices':
                            self._DeviceTypes.platforms[name.lower()] = klass
                        if possible_file_name == '_input_types':
                            self._InputTypes.platforms[name.lower()] = klass
                except Exception as e:
                    pass

    def module_invoke_failure(self, failure, module_name, hook_name):
        logger.warn("---==(failure during module invoke for hook ({module_name}::{hook_name})==----",
                    module_name=module_name, hook_name=hook_name)
        logger.warn("--------------------------------------------------------")
        logger.warn("{failure}", failure=failure)
        logger.warn("--------------------------------------------------------")
        raise RuntimeError("failure during module invoke for hook: %s" % failure)

    @inlineCallbacks
    def module_init_invoke(self):
        """
        Calls the _init_ functions of modules.
        """
        for module_id, module in self.modules.items():
            logger.debug("Starting module_init_invoke for module: {module}", module=module)
            module._module_variables = partial(
                self.module_variables,
                module._Name,
                module_id,
            )

            module._module_devices = partial(
                self.module_devices,
                module_id,
                self.gateway_id,
            )

            module._module_device_types = partial(
                self.module_device_types,
                module_id,
            )

            module._module_starting = partial(
                self.module_starting,
                module,
            )

            module._module_started = partial(
                self.module_started,
                module,
            )
            yield self.do_update_module_cache(module)

            module._event_loop = self._Loader.event_loop
            module._AMQP = self._Loader.loadedLibraries['amqp']
            module._AMQPYombo = self._Loader.loadedLibraries['amqpyombo']
            module._Atoms = self._Loader.loadedLibraries['atoms']
            module._AuthKeys = self._Loader.loadedLibraries['authkeys']
            module._Automation = self._Loader.loadedLibraries['automation']
            module._Commands = self._Loader.loadedLibraries['commands']
            module._Configs = self._Loader.loadedLibraries['configuration']
            module._CronTab = self._Loader.loadedLibraries['crontab']
            module._Devices = self._Loader.loadedLibraries['devices']  # Basically, all devices
            module._DeviceTypes = self._Loader.loadedLibraries['devicetypes']  # All device types.
            module._Discovery = self._Loader.loadedLibraries['discovery']
            module._Gateways = self._Loader.loadedLibraries['gateways']
            module._GatewayComs = self._Loader.loadedLibraries['gateways_communications']
            module._GPG = self._Loader.loadedLibraries['gpg']
            module._InputTypes = self._Loader.loadedLibraries['inputtypes']  # Input Types
            module._Intents = self._Loader.loadedLibraries['intents']
            module._Hash = self._Loader.loadedLibraries['hash']  # Input Types
            module._HashIDS = self._Loader.loadedLibraries['hashids']
            module._Libraries = self._Loader.loadedLibraries
            module._Localize = self._Loader.loadedLibraries['localize']
            module._LocalDB = self._Loader.loadedLibraries['localdb'] # Provided for testing
            module._Locations = self._Loader.loadedLibraries['locations']  # Basically, all devices
            module._Modules = self
            module._MQTT = self._Loader.loadedLibraries['mqtt']
            module._Nodes = self._Loader.loadedLibraries['nodes']
            module._Notifications = self._Loader.loadedLibraries['notifications']
            module._Queue = self._Loader.loadedLibraries['queue']
            module._Requests = self._Loader.loadedLibraries['requests']
            module._Scenes = self._Loader.loadedLibraries['scenes']
            module._SQLDict = self._Loader.loadedLibraries['sqldict']
            module._SSLCerts = self._Loader.loadedLibraries['sslcerts']
            module._States = self._Loader.loadedLibraries['states']
            module._Statistics = self._Loader.loadedLibraries['statistics']
            module._Tasks = self._Loader.loadedLibraries['tasks']
            module._Template = self._Loader.loadedLibraries['template']
            module._Times = self._Loader.loadedLibraries['times']
            module._Users = self._Loader.loadedLibraries['users']
            module._YomboAPI = self._Loader.loadedLibraries['yomboapi']
            module._Variables = self._Loader.loadedLibraries['variables']
            module._Validate = self._Loader.loadedLibraries['validate']
            module._VoiceCmds = self._Loader.loadedLibraries['voicecmds']
            module._WebSessions = self._Loader.loadedLibraries['websessions']

            module._hooks_called['_init_'] = 0
            if int(module._status) != 1:
                continue

            try:
                d = Deferred()
                d.addCallback(lambda ignored: self.modules_invoke_log('debug', module._label, 'module', '_init_', 'About to call _init_.'))
                d.addCallback(lambda ignored: maybeDeferred(module._init_))
                d.addErrback(self.module_invoke_failure, module._Name, '_init_')
                d.addCallback(self._log_hook_called, module._Name + ":_init", module, "_init_", "yombo.lib.modules")
                d.addCallback(lambda ignored: self.modules_invoke_log('debug', module._label, 'module', '_init_', 'Finished with call _init_.'))
                d.callback(1)
                results = yield d
            except RuntimeWarning as e:
                pass
            except Exception as e:
                logger.warn("Disabling module '{module}' due to exception from hook (_init_): {e}",
                            module=module._Name, e=e)
                self.disabled_modules[module_id] = "Caught exception during call '_init_': %s" % e

    def _log_hook_called(self, results, name, module, hook, calling_component):
        # logger.debug("results in _log_hook_called: {results}", results=results)
        self.hooks_called[name] = {
            'module': module._Name,
            'hook': hook,
            'time': int(time()),
            'called_by': calling_component,
        }
        return results

    @inlineCallbacks
    def update_module_cache(self, **kwargs):
        # print("starting update_module_cache: %0.3f " % time())
        for module_id, module in self.modules.items():
            yield self.do_update_module_cache(module)

    @inlineCallbacks
    def do_update_module_cache(self, module):
        """
        Updates various cache items. Can't replace the variable, want to keep the same
        memory pointer. So, we empty it and then append new entries to it.
        :param module:
        :return:
        """
        yield module._module_device_types()
        yield module._module_variables()
        yield module._module_devices()

    def module_invoke(self, requested_module, hook_name, **kwargs):
        """
        Invokes a hook for a a given module. Passes kwargs in, returns the results to caller.
        """
        if requested_module not in self:
            raise YomboWarning('Requested library is missing: %s' % requested_module)

        if 'called_by' not in kwargs:
            raise YomboWarning("Unable to call hook '%s:%s', missing 'called_by' named argument." % (requested_module, hook_name))
        calling_component = kwargs['called_by']
        final_results = None

        for hook in [hook_name, '_yombo_universal_hook_']:
            cache_key = requested_module + hook
            if cache_key in self._invoke_list_cache:
                if self._invoke_list_cache[cache_key] is False:
                    continue  # skip. We already know function doesn't exist.
            module = self.get(requested_module)
            if module._Name == 'yombo.core.module.YomboModule':
                self._invoke_list_cache[cache_key] is False
                # logger.warn("Cache module hook ({cache_key})...SKIPPED", cache_key=cache_key)
                return None
            if not (hook.startswith("_") and hook.endswith("_")):
                hook = module._Name.lower() + "_" + hook
            kwargs['hook_name'] = hook
            # self.modules_invoke_log('info', requested_module, 'module', hook, 'About to call.')
            if hasattr(module, hook):
                method = getattr(module, hook)
                if isinstance(method, collections.Callable):
                    if module._Name not in self.hook_counts:
                        self.hook_counts[module._Name] = {}
                    if hook not in self.hook_counts[module._Name]:
                        self.hook_counts[module._Name][hook] = {'Total Count': {'count': 0}}
                    if calling_component not in self.hook_counts[module._Name][hook]:
                        self.hook_counts[module._Name][hook][calling_component] = {'count': 0}
                    self.hook_counts[module._Name][hook][calling_component]['count'] = self.hook_counts[module._Name][hook][calling_component]['count'] + 1
                    self.hook_counts[module._Name][hook]['Total Count']['count'] = self.hook_counts[module._Name][hook]['Total Count']['count'] + 1

                    try:
                        # self.modules_invoke_log('debug', module._label, 'module', hook, 'About to call %s.' % hook)
                        d = Deferred()
                        d.addCallback(lambda ignored: self.modules_invoke_log('debug', module._label, 'module', hook, 'About to call %s' % hook))
                        d.addCallback(lambda ignored: maybeDeferred(method, **kwargs))
                        d.addErrback(self.module_invoke_failure, module._Name, hook)
                        d.addCallback(self._log_hook_called, module._Name + ":" + hook, module, hook, calling_component)
                        # d.addCallback(lambda ignored: self.modules_invoke_log('debug', module._label, 'module', hook, 'Finished call to %s' % hook))
                        d.callback(1)
                        return d
                        # if hook == '_yombo_universal_hook_':
                        #     yield d
                        # else:
                        #     final_results = d

                    except Exception as e:
                        if kwargs['allow_disable'] is True:
                            logger.warn("Disabling module '{module}' due to exception from hook ({hook}): {e}",
                                        module=module._Name, hook=hook, e=e)
                            self.disabled_modules[module._module_id] = "Caught exception during call '%s': %s" % (e, hook)

                else:
                    pass
            else:
                self._invoke_list_cache[cache_key] = False
            return final_results

    @inlineCallbacks
    def module_invoke_all(self, hook, full_name=None, allow_disable=None, **kwargs):
        """
        Calls module_invoke for all loaded modules.
        """
        def add_results(value, results, label):
            if value is not None:
                results[label] = value
            return value

        kwargs['allow_disable'] = allow_disable
        # logger.debug("in module_invoke_all: fullname={full_name}   hook: {hook}.",
        #              full_name=full_name, hook=hook)
        # logger.debug("in module_invoke_all: modules={modules}", modules=self.modules)
        if full_name == None:
            full_name = False
        results = {}
        # print("aaa: %s" % hook)
        dl_list = []
        if 'stoponerror' in kwargs:
            stoponerror = kwargs['stoponerror']
        else:
            kwargs['stoponerror'] = False
            stoponerror = False

        for module_id, module in self.modules.items():
            # print("aaa2")
            if module_id in self.disabled_modules:
                continue

            if int(module._status) != 1:
                continue

            label = module._FullName.lower() if full_name else module._Name.lower()
            try:
                # result = yield self.module_invoke(module._Name, hook, **kwargs)
                # if result is not None:
                #     results[label] = result
                # print("bbb1")
                d = self.module_invoke(module._Name, hook, **kwargs)
                # print("bbb2")
                if d is not None:
                    # print("bbb3 - %s" % d)
                    d.addCallback(add_results, results, module)
                    dl_list.append(d)
            except YomboWarning:
                pass
            except YomboHookStopProcessing as e:
                if stoponerror is True:
                    e.collected = results
                    e.by_who = label
                    raise
            except Exception as e:
                logger.warn("Disabling module '{module}' due to exception from hook ({hook}): {e}",
                            module=module._Name, hook=hook, e=e)
                self.disabled_modules[module_id] = "Caught exception during call '%s': %s" % (e, hook)

        dl = DeferredList(dl_list)
        yield dl
        # print("results: %s" % results)
        return results

    @inlineCallbacks
    def load_module_data(self):
        self.startDefer.callback(10)

    def add_imported_module(self, module_id, module_label, module_instance):
        logger.debug("adding module: {module_id}:{module_label}", module_id=module_id, module_label=module_label)
        self.modules[module_id] = module_instance

    def del_imported_module(self, module_id, module_label):
        logger.debug("deleting module_id: {module_id} from this list: {list}", module_id=module_id, list=self.modules)
        del self.modules[module_id]

    def get(self, module_requested, limiter=None, status=None):
        """
        Attempts to find the module requested using a couple of methods. Use the already defined pointer within a
        module to find another other:

            >>> someModule = self._Modules['137ab129da9318']  #by uuid

        or:

            >>> someModule = self._Modules['Homevision']  #by name

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param module_requested: The module id or module label to search for.
        :type module_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the module to check for.
        :type status: int
        :return: Pointer to requested device.
        :rtype: dict
        """
        if limiter is None:
            limiter = .89

        if limiter > .99999999:
            limiter = .99
        elif limiter < .10:
            limiter = .10

        if module_requested in self.modules:
            item = self.modules[module_requested]
            if status is not None and item.status != status:
                raise KeyError("Requested mdule found, but has invalid status: %s" % item._status)
            return item
        else:
            attrs = [
                {
                    'field': '_module_id',
                    'value': module_requested,
                    'limiter': limiter,
                },
                {
                    'field': '_label',
                    'value': module_requested,
                    'limiter': limiter,
                },
                {
                    'field': '_machine_label',
                    'value': module_requested,
                    'limiter': limiter,
                }
            ]
            try:
                # logger.debug("Get is about to call search...: %s" % module_requested)
                found, key, item, ratio, others = do_search_instance(attrs, self.modules,
                                                                     self.module_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest")
                # logger.debug("found module by search: {module_id}", module_id=key)
                # print("%s %s %s %s %s" % (found, key, item, ratio, others))
                if found:
                    return item
                else:
                    raise KeyError("Module not found: %s" % module_requested)
            except YomboWarning as e:
                raise KeyError('Searched for %s, but found had problems: %s' % (module_requested, e))

    def search(self, _limiter=None, _operation=None, **kwargs):
        """
        Search for modules based on attributes for all modules.

        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the module to check for.
        :return: 
        """
        for attr, value in kwargs.items():
            if "_%s" % attr in self.module_search_attributes:
                kwargs[attr]['field'] = "_%s" % attr

        return search_instance(kwargs, self.modules, self.module_search_attributes, _limiter, _operation)

    def modules_invoke_log(self, level, label, type, method, msg=""):
        """
        A common log format for loading/unloading libraries and modules.

        :param level: Log level - debug, info, warn...
        :param label: Module label "x10", "messages"
        :param type: Type of item being loaded: library, module
        :param method: Method being called.
        :param msg: Optional message to include.
        :return:
        """
        logit = getattr(logger, level)
        logit("({log_source}) {label}({type})::{method} - {msg}", label=label, type=type, method=method, msg=msg)

    def _device_changed_(self, **kwargs):
        """
        We listen for device updates so we can update module device caches.

        :param kwargs:
        :return:
        """
        for module_id, module in self.modules.items():
            self.module_devices(module_id, self.gateway_id)

    @inlineCallbacks
    def module_devices(self, module_id, gateway_id=None):
        """
        A list of devices for a given module id.

        :raises YomboWarning: Raised when module_id is not found.
        :param module_id: The Module ID to return device types for.
        :return: A dictionary of devices for a given module id.
        :rtype: list
        """
        if module_id not in self.modules:
            logger.warn("module_devices cannot find '{module_id}' in available modules.", module_id=module_id)
            return {}

        if gateway_id is None:
            gateway_id = self.gateway_id
        temp = {}
        module_device_types = yield self.module_device_types(module_id)
        for device_type_id, device_type in module_device_types.items():
            temp.update(self._DeviceTypes[device_type_id].get_devices(gateway_id=gateway_id))

        module = self.modules[module_id]
        module._module_devices_cached.clear()
        module._module_devices_cached.update(temp)
        # for device_id, device in temp.items():
        #     module._module_devices_cached[device_id] = device

        return module._module_devices_cached

    @inlineCallbacks
    def module_device_types(self, module_id):
        module_device_types = yield self._LocalDB.get_module_device_types(module_id)
        module = self.modules[module_id]
        module._module_device_types_cached.clear()
        for device_type_db in module_device_types:
            id = device_type_db['id']
            module._module_device_types_cached[id] = self._DeviceTypes.get(id)
        return module._module_device_types_cached

    def module_starting(self, module_id):
        self.modules_that_are_starting[module_id] = True
        self.update_starting_modules_notification()

    def module_started(self, module_id):
        del self.modules_that_are_starting[module_id]
        self.update_starting_modules_notification()

    def update_starting_modules_notification(self):
        if len(self.modules_that_are_starting) == 0:
            self._Notifications.delete('modules_that_are_starting')
        else:
            module_labels = []
            for module in self.modules_that_are_starting:
                module_labels.append(module._label)
            modules = "<br>".join(module_labels)
            self._Notifications.add({'title': 'Modules still starting',
                                     'message': 'The following modules are still starting:<br>%s' % modules,
                                     'source': 'Modules Library',
                                     'persist': False,
                                     'priority': 'high',
                                     'always_show': True,
                                     'always_show_allow_clear': False,
                                     'id': 'modules_that_are_starting',
                                     'local': True,
                                    })

    @inlineCallbacks
    def module_variables(self, module_name, module_id):
        variables = yield self._Variables.get_variable_fields_data(
            group_relation_type='module',
            group_relation_id=module_id,
            data_relation_id=module_id,
        )
            #
            # data_relation_type=data_relation_type,
            # data_relation_id=data_relation_id)

        if module_name in self._localModuleVars:
            variables = dict_merge(variables, self._localModuleVars[module_name])

        module = self.modules[module_id]
        module._module_variables_cached.clear()
        module._module_variables_cached.update(variables)
        # print("module_variables: variable: %s" % variables)
        # for label, data in variables:
        #     module._module_variables_cached['label'] = data

        return module._module_variables_cached

    @inlineCallbacks
    def full_list_modules(self):
        """
        Return a list of dictionaries representing all known commands to this gateway.
        :return:
        """
        items = []
        for module_id, module in self.modules.items():
            module_data = yield module.asdict()
            items.append(module_data)
        return items

    @inlineCallbacks
    def add_module(self, data, **kwargs):
        """
        Adds a module to be installed. A restart is required to complete.

        :param data:
        :param kwargs:
        :return:
        """
        api_data = {
            'module_id': data['module_id'],
            'install_branch': data['install_branch'],
            'status': 1,
        }

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            yield self._YomboAPI.request('POST', '/v1/gateway/%s/module' % self.gateway_id,
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't add module: %s" % e.message,
                'apimsg': "Couldn't add module: %s" % e.message,
                'apimsghtml': "Couldn't add module: %s" % e.html_message,
            }

        if 'session' in kwargs:
            session = kwargs['session']
        else:
            session = None

        # print("checking if var data... %s" % data)
        if 'variable_data' in data:
            # print("adding variable data...")
            variable_data = data['variable_data']
            for field_id, var_data in variable_data.items():
                # print("field_id: %s" % field_id)
                # print("var_data: %s" % var_data)
                for data_id, value in var_data.items():
                    # print("data_id: %s" % data_id)
                    if data_id.startswith('new_'):
                        # print("data_id starts with new...")
                        post_data = {
                            'gateway_id': self.gateway_id,
                            'field_id': field_id,
                            'relation_id': data['module_id'],
                            'relation_type': 'module',
                            'data_weight': 0,
                            'data': value,
                        }
                        # print("post_data: %s" % post_data)
                        try:
                            yield self._YomboAPI.request('POST', '/v1/variable/data',
                                                         post_data,
                                                         session=session)
                        except YomboWarning as e:
                            return {
                                'status': 'failed',
                                'msg': "Couldn't add module variables: %s" % e.message,
                                'apimsg': "Couldn't add module variables: %s" % e.message,
                                'apimsghtml': "Couldn't add module variables: %s" % e.html_message,
                            }
                    else:
                        post_data = {
                            'data_weight': 0,
                            'data': value,
                        }
                        # print("posting to: /v1/variable/data/%s" % data_id)
                        # print("post_data: %s" % post_data)
                        try:
                            yield self._YomboAPI.request('PATCH', '/v1/variable/data/%s' % data_id,
                                                         post_data,
                                                         session=session)
                        except YomboWarning as e:
                            return {
                                'status': 'failed',
                                'msg': "Couldn't add module variables: %s" % e.message,
                                'apimsg': "Couldn't add module variables: %s" % e.message,
                                'apimsghtml': "Couldn't add module variables: %s" % e.html_message,
                            }

        results = {
            'status': 'success',
            'msg': "Module added.",
            'module_id': data['module_id']
        }
        reactor.callLater(.0001,
                          global_invoke_all,
                          '_module_added_',
                          called_by=self,
                          module_id=data['module_id'],
                          )
        if 'module_label' in data:
            label = data['module_label']
        else:
            label = data['module_id']
        self._Notifications.add(
            {'title': 'Module added: %s' % label,
             'message': "The module '%s' has been disabled and will take affect on next reboot." % label,
             'timeout': 3600,
             'source': 'Modules Library',
             'persist': False,
             'always_show': False,
             'targets': 'module_updated',
             })
        return results

    @inlineCallbacks
    def edit_module(self, module_id, data, **kwargs):
        """
        Edit the module installation information. A reboot is required for this to take effect.

        :param data:
        :param kwargs:
        :return:
        """
        logger.debug("Editing module: {module_id} == {data}", module_id=module_id, data=data)
        api_data = {
            'install_branch': data['install_branch'],
            'status': data['status'],
        }

        if 'session' in kwargs:
            session = kwargs['session']
        else:
            session = None
        try:
            yield self._YomboAPI.request('PATCH',
                                         '/v1/gateway/%s/module/%s' % (self.gateway_id, module_id),
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                'status': 'failed',
                'msg': "Couldn't edit module: %s" % e.message,
                'apimsg': "Couldn't edit module: %s" % e.message,
                'apimsghtml': "Couldn't edit module: %s" % e.html_message,
            }

        if 'variable_data' in data:
            logger.debug("editing variable data...")
            variable_data = data['variable_data']
            for field_id, var_data in variable_data.items():
                # print("field_id: %s" % field_id)
                # print("var_data: %s" % var_data)
                for data_id, value in var_data.items():
                    # print("data_id: %s" % data_id)
                    # print("data_id: %s" % type(data_id))
                    if data_id.startswith('new_') or data_id is None or data_id.lower() == 'none':
                        # print("data_id starts with new...")
                        post_data = {
                            'gateway_id': self.gateway_id,
                            'field_id': field_id,
                            'relation_id': data['module_id'],
                            'relation_type': 'module',
                            'data_weight': 0,
                            'data': value,
                        }
                        # print("post_data: %s" % post_data)
                        try:
                            yield self._YomboAPI.request('POST', '/v1/variable/data',
                                                         post_data,
                                                         session=session)
                        except YomboWarning as e:
                            return {
                                'status': 'failed',
                                'msg': "Couldn't add module variables: %s" % e.message,
                                'apimsg': "Couldn't add module variables: %s" % e.message,
                                'apimsghtml': "Couldn't add module variables: %s" % e.html_message,
                            }
                    else:
                        post_data = {
                            'data_weight': 0,
                            'data': value,
                        }
                        # print("posting to: /v1/variable/data/%s" % data_id)
                        # print("post_data: %s" % post_data)
                        try:
                            yield self._YomboAPI.request('PATCH',
                                                         '/v1/variable/data/%s' % data_id,
                                                         post_data,
                                                         session=session)
                        except YomboWarning as e:
                            return {
                                'status': 'failed',
                                'msg': "Couldn't add module variables: %s" % e.message,
                                'apimsg': "Couldn't add module variables: %s" % e.message,
                                'apimsghtml': "Couldn't add module variables: %s" % e.html_message,
                            }

        results = {
            'status': 'success',
            'msg': "Module edited.",
            'module_id': module_id
        }
        a_module = self.get(module_id)
        reactor.callLater(.0001,
                          global_invoke_all,
                          '_module_updated_',
                          called_by=self,
                          module_id=module_id,
                          module=a_module,
                          )
        self._Notifications.add(
            {'title': 'Module edited: %s' % a_module._label,
             'message': "The module '%s' has been edited." % a_module._label,
             'timeout': 3600,
             'source': 'Modules Library',
             'persist': False,
             'always_show': False,
             'targets': 'module_updated',
             })

        return results

    @inlineCallbacks
    def remove_module(self, module_id, **kwargs):
        """
        Delete a module. Calls the API to perform this task. A restart is required to complete.

        :param module_id: The module ID to disable.
        :param kwargs:
        :return:
        """
        if module_id not in self.modules:
            raise YomboWarning("module_id doesn't exist. Nothing to remove.", 300, 'disable_module', 'Modules')

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            yield self._YomboAPI.request('DELETE',
                                         '/v1/gateway/%s/module/%s' % (self.gateway_id, module_id),
                                         session=session)
        except YomboWarning as e:
            # print("module delete results: %s" % module_results)
            return {
                'status': 'failed',
                'msg': "Couldn't delete module: %s" % e.message,
                'apimsg': "Couldn't delete module: %s" % e.message,
                'apimsghtml': "Couldn't delete module: %s" % e.html_message,
            }

        self._LocalDB.set_module_status(module_id, 2)
        self._LocalDB.del_variables('module', module_id)

        results = {
            'status': 'success',
            'msg': "Module deleted.",
            'module_id': module_id,
        }
        a_module = self.get(module_id)
        reactor.callLater(.0001,
                          global_invoke_all,
                          '_module_removed_',
                          called_by=self,
                          module_id=module_id,
                          module=a_module,
                          )
        self._Notifications.add(
            {'title': 'Module removed: %s' % a_module._label,
             'message': "The module '%s' has been removed and will take affect on next reboot." % a_module._label,
             'timeout': 3600,
             'source': 'Modules Library',
             'persist': False,
             'always_show': False,
             'targets': 'module_updated',
             })

        #todo: add task to remove files.
        #todo: add system for "do something on next startup..."
        return results

    @inlineCallbacks
    def enable_module(self, module_id, **kwargs):
        """
        Enable a module. Calls the API to perform this task. A restart is required to complete.

        :param module_id: The module ID to enable.
        :param kwargs:
        :return:
        """
        logger.debug("enabling module: {module_id}", module_id=module_id)
        api_data = {
            'status': 1,
        }

        if module_id not in self.modules:
            raise YomboWarning("module_id doesn't exist. Nothing to enable.", 300, 'enable_module', 'Modules')
        module = self.modules[module_id]
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            yield self._YomboAPI.request('PATCH',
                                         '/v1/gateway/%s/module/%s' % (self.gateway_id, module_id),
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            # print("module enable results: %s" % module_results)
            return {
                'status': 'failed',
                'msg': "Couldn't enable module: %s" % e.message,
                'apimsg': "Couldn't enable module: %s" % e.message,
                'apimsghtml': "Couldn't enable module: %s" % e.html_message,
            }

        self._LocalDB.set_module_status(module_id, 1)

        results = {
            'status': 'success',
            'msg': "Module enabled.",
            'module_id': module_id,
        }
        a_module = self.get(module_id)
        reactor.callLater(.0001,
                          global_invoke_all,
                          '_module_enabled_',
                          called_by=self,
                          module_id=module_id,
                          module=module,
                          )
        self._Notifications.add(
            {'title': 'Module enabled: %s' % a_module._label,
             'message': "The module '%s' has been enabled and will take affect on next reboot." % a_module._label,
             'timeout': 3600,
             'source': 'Modules Library',
             'persist': False,
             'always_show': False,
             'targets': 'module_updated',
             })
        return results

    @inlineCallbacks
    def disable_module(self, module_id, **kwargs):
        """
        Disable a module. Calls the API to perform this task. A restart is required to complete.

        :param module_id: The module ID to disable.
        :param kwargs:
        :return:
        """
        logger.debug("disabling module: {module_id}", module_id=module_id)
        api_data = {
            'status': 0,
        }

        if module_id not in self.modules:
            raise YomboWarning("module_id doesn't exist. Nothing to disable.", 300, 'disable_module', 'Modules')

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                session = None

            yield self._YomboAPI.request('PATCH',
                                         '/v1/gateway/%s/module/%s' % (self.gateway_id, module_id),
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            # print("module disable results: %s" % module_results)
            return {
                'status': 'failed',
                'msg': "Couldn't disable module: %s" % e.message,
                'apimsg': "Couldn't disable module: %s" % e.message,
                'apimsghtml': "Couldn't disable module: %s" % e.html_message,
            }

        self._LocalDB.set_module_status(module_id, 0)

        results = {
            'status': 'success',
            'msg': "Module disabled.",
            'module_id': module_id,
        }
        a_module = self.get(module_id)
        reactor.callLater(.0001,
                          global_invoke_all,
                          '_module_disabled_',
                          called_by=self,
                          module_id=module_id,
                          )
        self._Notifications.add(
            {'title': 'Module disabled: %s' % a_module._label,
             'message': "The module '%s' has been disabled and will take affect on next reboot." % a_module._label,
             'timeout': 3600,
             'source': 'Modules Library',
             'persist': False,
             'always_show': False,
             'targets': 'module_updated',
             })
        return results

    @inlineCallbacks
    def dev_module_add(self, data, **kwargs):
        """
        Add a module at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't add module: User session missing.",
                    'apimsg': "Couldn't add module: User session missing.",
                    'apimsghtml': "Couldn't add module: User session missing.",
                }

            module_results = yield self._YomboAPI.request('POST', '/v1/module', data,
                                                          session=session)
        except YomboWarning as e:
            # print("module add results: %s" % module_results)
            return {
                'status': 'failed',
                'msg': "Couldn't add module: %s" % e.message,
                'apimsg': "Couldn't add module: %s" % e.message,
                'apimsghtml': "Couldn't add module: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Module added.",
            'module_id': module_results['data']['id'],
        }

    @inlineCallbacks
    def dev_module_edit(self, module_id, data, **kwargs):
        """
        Edit a module at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't edit module: User session missing.",
                    'apimsg': "Couldn't edit module: User session missing.",
                    'apimsghtml': "Couldn't edit module: User session missing.",
                }
            yield self._YomboAPI.request('PATCH', '/v1/module/%s' % (module_id),
                                         data,
                                         session=session)
        except YomboWarning as e:
            # print("module edit results: %s" % module_results)
            return {
                'status': 'failed',
                'msg': "Couldn't edit module: %s" % e.message,
                'apimsg': "Couldn't edit module: %s" % e.message,
                'apimsghtml': "Couldn't edit module: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Module edited.",
            'module_id': module_id,
        }

    @inlineCallbacks
    def dev_module_delete(self, module_id, **kwargs):
        """
        Delete a module at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't delete module: User session missing.",
                    'apimsg': "Couldn't delete module: User session missing.",
                    'apimsghtml': "Couldn't delete module: User session missing.",
                }
            yield self._YomboAPI.request('DELETE', '/v1/module/%s' % module_id,
                                         session=session)
        except YomboWarning as e:
            # print("module delete results: %s" % module_results)
            return {
                'status': 'failed',
                'msg': "Couldn't delete module: %s" % e.message,
                'apimsg': "Couldn't delete module: %s" % e.message,
                'apimsghtml': "Couldn't delete module: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Module deleted.",
            'module_id': module_id,
        }

    @inlineCallbacks
    def dev_module_enable(self, module_id, **kwargs):
        """
        Enable a module at the Yombo server level, not at the local gateway level.

        :param module_id: The module ID to enable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 1,
        }

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't enable module: User session missing.",
                    'apimsg': "Couldn't enable module: User session missing.",
                    'apimsghtml': "Couldn't enable module: User session missing.",
                }
            yield self._YomboAPI.request('PATCH', '/v1/module/%s' % module_id,
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            # print("module delete results: %s" % module_results)
            return {
                'status': 'failed',
                'msg': "Couldn't enable module: %s" % e.message,
                'apimsg': "Couldn't enable module: %s" % e.message,
                'apimsghtml': "Couldn't enable module: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Module enabled.",
            'module_id': module_id,
        }

    @inlineCallbacks
    def dev_module_disable(self, module_id, **kwargs):
        """
        Enable a module at the Yombo server level, not at the local gateway level.

        :param module_id: The module ID to disable.
        :param kwargs:
        :return:
        """
        api_data = {
            'status': 0,
        }

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't disable module: User session missing.",
                    'apimsg': "Couldn't disable module: User session missing.",
                    'apimsghtml': "Couldn't disable module: User session missing.",
                }
            yield self._YomboAPI.request('PATCH', '/v1/module/%s' % module_id,
                                         api_data,
                                         session=session)
        except YomboWarning as e:
            # print("module delete results: %s" % module_results)
            return {
                'status': 'failed',
                'msg': "Couldn't disable module: %s" % e.message,
                'apimsg': "Couldn't disable module: %s" % e.message,
                'apimsghtml': "Couldn't disable module: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Module disabled.",
            'module_id': module_id,
        }

    @inlineCallbacks
    def dev_module_device_type_add(self, module_id, device_type_id, **kwargs):
        """
        Associate a device type to a module

        :param module_id: The module
        :param device_type_id: The device type to associate
        :return:
        """
        data = {
            'module_id': module_id,
            'device_type_id': device_type_id,
        }

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't associate device type to module: User session missing.",
                    'apimsg': "Couldn't associate device type to module: User session missing.",
                    'apimsghtml': "Couldn't associate device type to module: User session missing.",
                }
            yield self._YomboAPI.request('POST', '/v1/module_device_type',
                                         data,
                                         session=session)
        except YomboWarning as e:
            # print("module delete results: %s" % module_results)
            return {
                'status': 'failed',
                'msg': "Couldn't associate device type to module: %s" % e.message,
                'apimsg': "Couldn't associate device type to module: %s" % e.message,
                'apimsghtml': "Couldn't associate device type to module: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Device type associated to module.",
            'module_id': module_id,
        }

    @inlineCallbacks
    def dev_module_device_type_remove(self, module_id, device_type_id, **kwargs):
        """
        Removes an association of a device type from a module

        :param module_id: The module
        :param device_type_id: The device type to  remove association
        :return:
        """

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't remove association device type from module: User session missing.",
                    'apimsg': "Couldn't remove association device type from module: User session missing.",
                    'apimsghtml': "Couldn't remove association device type from module: User session missing.",
                }
            yield self._YomboAPI.request('DELETE',
                                         '/v1/module_device_type/%s/%s' % (module_id, device_type_id),
                                         session=session)
        except YomboWarning as e:
            # print("module delete results: %s" % module_results)
            return {
                'status': 'failed',
                'msg': "Couldn't remove association device type from module: %s" % e.message,
                'apimsg': "Couldn't remove association device type from module: %s" % e.message,
                'apimsghtml': "Couldn't remove association device type from module: %s" % e.html_message,
            }

        return {
            'status': 'success',
            'msg': "Device type removed from module.",
            'module_id': module_id,
        }

    @inlineCallbacks
    def _api_change_status(self, module_id, new_status, **kwargs):
        """
        Used to enabled, disable, or undelete a module. Calls the API

        Disable a module. Calls the API to perform this task. A restart is required to complete.

        :param module_id: The module ID to disable.
        :param kwargs:
        :return:
        """
        if module_id not in self.modules:
            raise YomboWarning("module_id doesn't exist. Nothing to disable.", 300, 'disable_module', 'Modules')

        try:
            if 'session' in kwargs:
                session = kwargs['session']
            else:
                return {
                    'status': 'failed',
                    'msg': "Couldn't %s module: User session missing." % new_status,
                    'apimsg': "Couldn't %s module: User session missing." % new_status,
                    'apimsghtml': "Couldn't %s module: User session missing." % new_status,
                }
            yield self._YomboAPI.request('PATCH',
                                         '/v1/gateway/%s/module/%s' % (self.gateway_id, module_id),
                                         session=session)
        except YomboWarning as e:
            # print("module delete results: %s" % module_results)
            return {
                'status': 'failed',
                'msg': "Couldn't %s module: %s" % (new_status, e.message),
                'apimsg': "Couldn't %s module: %s" % (new_status, e.message),
                'apimsghtml': "Couldn't %s module: %s" % (new_status, e.message),
            }

        return {
            'status': 'success',
            'msg': "Module disabled.",
            'module_id': module_id,
        }

