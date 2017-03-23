# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
.. rst-class:: floater

.. note::

  For more information see: `Modules @ Module Features <https://yombo.net/docs/features/modules/>`_

Manages all modules within the system. Provides a single reference to perform module lookup functions, etc.

Also calls module hooks as requested by other libraries and modules.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
#import sys
#import traceback
import ConfigParser
import sys
import traceback
from time import time
import hashlib

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred, returnValue

# Import Yombo libraries
from yombo.core.exceptions import YomboFuzzySearchError, YomboHookStopProcessing, YomboWarning, YomboCritical
from yombo.utils.fuzzysearch import FuzzySearch
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.utils
from yombo.utils.maxdict import MaxDict

logger = get_logger('library.modules')

SYSTEM_MODULES = {}
SYSTEM_MODULES['automationhelpers'] = {
    'id': 'automationhelpers', # module_id
    'gateway_id': 'local',
    'module_type': 'logic',
    'machine_label': 'AutomationHelpers',
    'label': 'Automation Helpers',
    'short_description': "Adds basic platforms to the automation rules.",
    'description': "Adds basic platforms to the automation rules.",
    'description_formatting': 'text',
    'install_branch': 'system',
    'install_count': '',
    'see_also': '',
    'prod_branch': '',
    'dev_branch': '',
    'prod_version': '',
    'dev_version': '',
    'repository_link': '',
    'issue_tracker_link': '',
    'doc_link': 'https://yombo.net/docs/features/automation-rules/',
    'git_link': '',
    'public': '2',
    'status': '1',
    'created': int(time()),
    'updated': int(time()),
    'load_source': 'system modules',
    }

class Modules(YomboLibrary):
    """
    A single place for modudule management and reference.
    """

    _rawModulesList = {}

    _modulesByUUID = {}
    _modulesByName = FuzzySearch({}, .92)

    _modules = {}  # Stores a list of modules. Populated by the loader module at startup.

    _localModuleVars = {}  # Used to store modules variables from file import

    def _init_(self):
        """
        Init doesn't do much. Just setup a few variables. Things really happen in start.
        """
        self.gwid = self._Configs.get("core", "gwid")
        self._LocalDBLibrary = self._Libraries['localdb']
        self._invoke_list_cache = {}  # Store a list of hooks that exist or not. A cache.
        self.hook_counts = {}  # keep track of hook names, and how many times it's called.
        self.hooks_called = MaxDict(200, {})

    def _load_(self):
        """
        Loads all the module information here.
        """
        pass

    def _reload_(self):
        pass

    def _start_(self):
        """
        Nothing to do now...
        """
        pass

    def _stop_(self):
        """
        Stop library - stop the looping call.
        """
        pass

    def _unload_(self):
        pass

    def __len__(self):
        return len(self._modulesByUUID)

    def __getitem__(self, moduleRequested):
        """
        Attempts to find the modules requested using a couple of methods.

        See get()
        """
        return self.get(moduleRequested)

#    def __iter__(self):
#        return self._modulesByUUID.__iter__()

    def __contains__(self, moduleRequested):
        try:
            self.get(moduleRequested)
            return True
        except:
            return False

    @inlineCallbacks
    def load_modules(self):
        """
        Loads the modules. Imports and calls various module hooks at startup.

        **Hooks implemented**:

        * _module_init_ : Only called to libraries, is called before modules called for _init_.
        * _init_ : Only called to modules, is called as part of the _init_ sequence.
        * _module_preload_ : Only called to libraries, is called before modules called for _preload_.
        * _preload_ : Only called to modules, is called before _load_.
        * _module_load_ : Only called to libraries, is called before modules called for _load_.
        * _load_ : Only called to modules, is called as part of the _load_ sequence.
        * _module_prestart_ : Only called to libraries, is called before modules called for _prestart_.
        * _prestart_ : Only called to modules, is called as part of the _prestart_ sequence.
        * _module_start_ : Only called to libraries, is called before modules called for _start_.
        * _start_ : Only called to modules, is called as part of the _start_ sequence.
        * _module_started_ : Only called to libraries, is called before modules called for _load_.
        * _started_ : Only called to modules, is called as part of the _started_ sequence.

        :return:
        """
#        logger.debug("starting modules::load_modules !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        yield self.build_raw_module_list()  # Create a list of modules, includes localmodules.ini
        yield self.import_modules()  # Just call "import moduleName"

        logger.debug("starting modules::init....")
        # Init
        yield self._Loader.library_invoke_all("_module_init_", called_by=self)
        yield self.module_init_invoke()  # Call "_init_" of modules

        # Pre-Load
        logger.debug("starting modules::pre-load....")
        yield self._Loader.library_invoke_all("_module_preload_", called_by=self)
        yield self.module_invoke_all("_preload1_", called_by=self)
        yield self.module_invoke_all("_preload_", called_by=self)

        # Load
        yield self._Loader.library_invoke_all("_module_load_", called_by=self)
        yield self.module_invoke_all("_load1_", called_by=self)
        yield self.module_invoke_all("_load_", called_by=self)

        # Pre-Start
        yield self._Loader.library_invoke_all("_module_prestart_", called_by=self)
        yield self.module_invoke_all("_prestart1_", called_by=self)
        yield self.module_invoke_all("_prestart_", called_by=self)

        # Start
        yield self._Loader.library_invoke_all("_module_start_", called_by=self)
        yield self.module_invoke_all("_start1_", called_by=self)
        yield self.module_invoke_all("_start_", called_by=self)

        yield self._Loader.library_invoke_all("_module_started_", called_by=self)
        yield self.module_invoke_all("_started1_", called_by=self)
        yield self.module_invoke_all("_started_", called_by=self)

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
        self._Loader.library_invoke_all("_module_stop_", called_by=self)
        self.module_invoke_all("_stop_")

        keys = self._modulesByUUID.keys()
        self._Loader.library_invoke_all("_module_unload_", called_by=self)
        for module_id in keys:
            module = self._modulesByUUID[module_id]
            if int(module._status) != 1:
                continue

            try:
                self.module_invoke(module._Name, "_unload_", called_by=self)
            except YomboWarning:
                pass
            finally:
                yield self._Loader.library_invoke_all("_module_unloaded_", called_by=self)
                delete_component = module._FullName
                self.del_imported_module(module_id, module._Name.lower())
                if delete_component.lower() in self._Loader.loadedComponents:
                    del self._Loader.loadedComponents[delete_component.lower()]

    @inlineCallbacks
    def build_raw_module_list(self):
        try:
            fp = open("localmodules.ini")
            ini = ConfigParser.SafeConfigParser()
            ini.optionxform=str
            ini.readfp(fp)
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

                if 'mod_description' in options:
                    mod_description = ini.get(section, 'mod_description')
                    options.remove('mod_description')
                else:
                    mod_description = section

                if 'mod_description_formatting' in options:
                    mod_description_formatting = ini.get(section, 'mod_description_formatting')
                    options.remove('mod_description_formatting')
                else:
                    mod_description_formatting = 'text'

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

                newUUID = hashlib.md5(mod_machine_label).hexdigest()
                self._rawModulesList[newUUID] = {
                  'id': newUUID, # module_id
                  'gateway_id': 'local',
                  'module_type': mod_module_type,
                  'machine_label': mod_machine_label,
                  'label': mod_label,
                  'short_description': mod_short_description,
                  'description': mod_description,
                  'description_formatting': mod_description_formatting,
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
                  'created': int(time()),
                  'updated': int(time()),
                  'load_source': 'localmodules.ini'
                }

                self._localModuleVars[mod_label] = {}
                for item in options:
                    logger.debug("Adding module from localmodule.ini: {item}", item=item)
                    if item not in self._localModuleVars[mod_label]:
                        self._localModuleVars[mod_label][item] = []
                    values = ini.get(section, item)
                    values = values.split(":::")
                    for value in values:
                        variable = {
                            'relation_id': newUUID,
                            'relation_type': 'module',
                            'field_machine_label': item,
                            'field_label': item,
                            'value': value,
                            'data_weight': 0,
                            'field_weight': 0,
                            'encryption': "nosuggestion",
                            'input_min': -8388600,
                            'input_max': 8388600,
                            'input_casing': 'none',
                            'input_required': 0,
                            'input_type_id': "any",
                            'variable_id': 'xxx',
                            'created': int(time()),
                            'updated': int(time()),
                        }
                        self._localModuleVars[mod_label][variable['field_machine_label']].append(variable)

#            logger.debug("localmodule vars: {lvars}", lvars=self._localModuleVars)
            fp.close()
        except IOError as (errno, strerror):
            logger.debug("localmodule.ini error: I/O error({errornumber}): {error}", errornumber=errno, error=strerror)

        # Local system modules.
        for module_name, data in SYSTEM_MODULES.iteritems():
            # print data
            if self._Configs.get('system_modules', data['machine_label'], 'enabled') != 'enabled':
                continue
            self._rawModulesList[data['id']] = data

        modulesDB = yield self._LocalDBLibrary.get_modules()
        # print "modulesdb: %s" % modulesDB
        # print " "
        for module in modulesDB:
            # print "module: %s" % module
            self._rawModulesList[module.id] = module.__dict__
            self._rawModulesList[module.id]['load_source'] = 'sql'
        # print "_rawModulesList: %s" % self._rawModulesList

#        logger.debug("Complete list of modules, before import: {rawModules}", rawModules=self._rawModulesList)

    def import_modules(self):
        logger.debug("Import modules: self._rawModulesList: {_rawModulesList}", _rawModulesList=self._rawModulesList)
        for module_id, module in self._rawModulesList.iteritems():
            pathName = "yombo.modules.%s" % module['machine_label']
            # print "loading: %s" % pathName
            try:
                module_instance, module_name = self._Loader.import_component(pathName, module['machine_label'], 'module', module['id'])
            except:
                logger.error("--------==(Error: Loading Module)==--------")
                logger.error("----Name: {pathName}", pathName=pathName)
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.format_exc())
                logger.error("--------------------------------------------------------")
                logger.error("Not loading module: %s" % module['machine_label'])
                continue

            self.add_imported_module(module['id'], module_name, module_instance)
            self._modulesByUUID[module_id]._hooks_called = {}
            self._modulesByUUID[module_id]._module_id = module['id']
            self._modulesByUUID[module_id]._module_type = module['module_type']
            self._modulesByUUID[module_id]._machine_label = module['machine_label']
            self._modulesByUUID[module_id]._label = module['label']
            self._modulesByUUID[module_id]._short_description = module['short_description']
            self._modulesByUUID[module_id]._description = module['description']
            self._modulesByUUID[module_id]._description_formatting = module['description_formatting']
            self._modulesByUUID[module_id]._install_count = module['install_count']
            self._modulesByUUID[module_id]._see_also = module['see_also']
            self._modulesByUUID[module_id]._repository_link = module['repository_link']
            self._modulesByUUID[module_id]._issue_tracker_link = module['issue_tracker_link']
            self._modulesByUUID[module_id]._doc_link = module['doc_link']
            self._modulesByUUID[module_id]._git_link = module['git_link']
            self._modulesByUUID[module_id]._install_branch = module['install_branch']
            self._modulesByUUID[module_id]._prod_branch = module['prod_branch']
            self._modulesByUUID[module_id]._dev_branch = module['prod_branch']
            self._modulesByUUID[module_id]._prod_version = module['prod_version']
            self._modulesByUUID[module_id]._dev_version = module['dev_version']
            self._modulesByUUID[module_id]._public = module['public']
            self._modulesByUUID[module_id]._status = module['status']
            self._modulesByUUID[module_id]._created = module['created']
            self._modulesByUUID[module_id]._updated = module['updated']
            self._modulesByUUID[module_id]._load_source = module['load_source']
            self._modulesByUUID[module_id]._device_types = []  # populated by Modules::module_init_invoke

    @inlineCallbacks
    def module_init_invoke(self):
        """
        Calls the _init_ functions of modules. Can't use basic hook for this due to complex items.
        **Hooks called**:

        * _module_devicetypes_ :  Gets a list of device type ids or labels.

        **Usage**:

        .. code-block:: python

           def _module_devicetypes_(self, **kwargs):
               '''
               Adds additional platforms to the source platform. Creates additional rule triggers.
               '''
               return [
                 'x10_lamp', 'x10_applicance',
               ]

        """
        module_init_deferred = []
        for module_id, module in self._modulesByUUID.iteritems():
            self.modules_invoke_log('debug', module._FullName, 'module', 'init', 'About to call _init_.')

            # Get variables, and merge with any local variable settings
            # print "getting vars for module: %s" % module_id
            module_variables = yield self._LocalDBLibrary.get_variables('module', module_id)
            # print "getting vars: %s "% module_variables
            module._ModuleVariables = module_variables

            if module._Name in self._localModuleVars:
                module._ModuleVariables = yombo.utils.dict_merge(module._ModuleVariables, self._localModuleVars[module._Name])
                del self._localModuleVars[module._Name]

            # if yombo.utils.get_method_definition_level(module._init_) != 'yombo.core.module.YomboModule':
            module._ModuleType = self._rawModulesList[module_id]['module_type']

            module._Atoms = self._Loader.loadedLibraries['atoms']
            module._Automation = self._Loader.loadedLibraries['automation']
            module._AMQP = self._Loader.loadedLibraries['amqp']
            module._Commands = self._Loader.loadedLibraries['commands']
            module._Configs = self._Loader.loadedLibraries['configuration']
            module._CronTab = self._Loader.loadedLibraries['crontab']
            module._GPG = self._Loader.loadedLibraries['gpg']
            module._Libraries = self._Loader.loadedLibraries
            module._Libraries = self._Loader.loadedLibraries
            module._Localize = self._Loader.loadedLibraries['localize']
            module._Modules = self
            module._MQTT = self._Loader.loadedLibraries['mqtt']
            module._Notifications = self._Loader.loadedLibraries['notifications']
            module._SQLDict = self._Loader.loadedLibraries['sqldict']
            module._States = self._Loader.loadedLibraries['states']
            module._Statistics = self._Loader.loadedLibraries['statistics']
            module._Tasks = self._Loader.loadedLibraries['tasks']
            module._Times = self._Loader.loadedLibraries['times']
            module._VoiceCmds = self._Loader.loadedLibraries['voicecmds']

            module._Devices = self._Loader.loadedLibraries['devices']  # Basically, all devices
            module._DeviceTypes = self._Loader.loadedLibraries['devicetypes']  # All device types.
            module._InputTypes = self._Loader.loadedLibraries['inputtypes']  # Input Types

            module._hooks_called['_init_'] = 0
            if int(module._status) != 1:
                continue

            module_device_types = yield self._LocalDBLibrary.get_module_device_types(module_id)
            # print "module_device_types = %s" % module_device_types
            for module_device_type in module_device_types:
                if module_device_type.id in module._DeviceTypes:
                    self._modulesByUUID[module_id]._device_types.append(module_device_type.id)

            module._DeviceTypes.add_registered_module(module)
#                module_init_deferred.append(maybeDeferred(module._init_))
#                continue
            try:
#                module_init_deferred.append(maybeDeferred(module._init_))
                d = yield maybeDeferred(module._init_)
                module._hooks_called['_init_'] = 1
#                    d.errback(self.SomeError)
#                    yield d
            except YomboCritical, e:
                logger.error("---==(Critical Server Error in _init_ function for module: {name})==----", name=module._FullName)
                logger.error("--------------------------------------------------------")
                logger.error("Error message: {e}", e=e)
                logger.error("--------------------------------------------------------")
                e.exit()
            except:
                logger.error("-------==(Error in init function for module: {name})==---------", name=module._FullName)
                logger.error("1:: {e}", e=sys.exc_info())
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{e}", e=traceback.print_exc(file=sys.stdout))
                logger.error("--------------------------------------------------------")
                # except:
                #     exc_type, exc_value, exc_traceback = sys.exc_info()
                #     logger.error("------==(ERROR During _init_ of module: {module})==-------", module=module._FullName)
                #     logger.error("1:: {e}", e=sys.exc_info())
                #     logger.error("---------------==(Traceback)==--------------------------")
                #     logger.error("{e}", e=traceback.print_exc(file=sys.stdout))
                #     logger.error("--------------------------------------------------------")
                #     logger.error("{e}", e=traceback.print_exc())
                #     logger.error("--------------------------------------------------------")
                #     logger.error("{e}", e=repr(traceback.print_exception(exc_type, exc_value, exc_traceback,
                #               limit=5, file=sys.stdout)))
                #     logger.error("--------------------------------------------------------")
#        logger.debug("!!!!!!!!!!!!!!!!!!!!!1 About to yield while waiting for module_init's to be done!")
#        yield DeferredList(module_init_deferred)
#        logger.debug("!!!!!!!!!!!!!!!!!!!!!2 Done yielding for while waiting for module_init's to be done!")

    def SomeError(self, error):
        logger.error("Received an error: {error}", error=error)

#    @inlineCallbacks
    def module_invoke(self, requestedModule, hook, called_by=None, **kwargs):
        """
        Invokes a hook for a a given module. Passes kwargs in, returns the results to caller.
        """
        if called_by is not None:
            called_by = called_by._FullName
        else:
            called_by = 'Unknown'
        cache_key = requestedModule + hook
        if cache_key in self._invoke_list_cache:
            if self._invoke_list_cache[cache_key] is False:
                return  # skip. We already know function doesn't exist.
        module = self.get(requestedModule)
        if module._Name == 'yombo.core.module.YomboModule':
            self._invoke_list_cache[cache_key] is False
            # logger.warn("Cache module hook ({cache_key})...SKIPPED", cache_key=cache_key)
            return
            # raise YomboWarning("Cannot call YomboModule hooks")
        if not (hook.startswith("_") and hook.endswith("_")):
            hook = module._Name.lower() + "_" + hook
        self.modules_invoke_log('debug', requestedModule, 'module', hook, 'About to call.')
        if hasattr(module, hook):
            method = getattr(module, hook)
            if callable(method):
                if module._Name not in self.hook_counts:
                    self.hook_counts[module._Name] = {}
                if hook not in self.hook_counts[module._Name]:
                    self.hook_counts[module._Name][hook] = {'Total Count': {'count': 0}}
                # print "hook counts: %s" % self.hook_counts
                # print "hook counts: %s" % self.hook_counts[library._Name][hook]
                if called_by not in self.hook_counts[module._Name][hook]:
                    self.hook_counts[module._Name][hook][called_by] = {'count': 0}
                self.hook_counts[module._Name][hook][called_by]['count'] = self.hook_counts[module._Name][hook][called_by]['count'] + 1
                self.hook_counts[module._Name][hook]['Total Count']['count'] = self.hook_counts[module._Name][hook]['Total Count']['count'] + 1
                self.hooks_called[int(time())] = {
                    'module': module._Name,
                    'hook': hook,
                    'called_by': called_by,
                }

                try:
#                    results = yield maybeDeferred(method, **kwargs)
                    self._invoke_list_cache[cache_key] = True
                    if hook not in module._hooks_called:
                        module._hooks_called[hook] = 1
                    else:
                        module._hooks_called[hook] += 1
                    return method(**kwargs)
                # except Exception, e:
                #     logger.error("---==(Error in {hook} function for module: {name})==----", hook=hook, name=module._FullName)
                #     logger.error("--------------------------------------------------------")
                #     logger.error("Error message: {e}", e=e)
                #     logger.error("--------------------------------------------------------")
                except Exception, e:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    logger.error("------==(ERROR During {hook} of module: {name})==-------", hook=hook, name=module._FullName)
                    logger.error("1:: {e}", e=sys.exc_info())
                    logger.error("---------------==(Traceback)==--------------------------")
                    logger.error("{e}", e=traceback.print_exc())
                    logger.error("--------------------------------------------------------")
                    # logger.error("{e}", e=repr(traceback.print_exception(exc_type, exc_value, exc_traceback,
                    #           limit=10, file=sys.stdout)))
                    # logger.error("--------------------------------------------------------")
            else:
                logger.debug("----==(Module {module} doesn't have a callable function: {function})==-----", module=module._FullName, function=hook)
        else:
            self._invoke_list_cache[cache_key] = False
            # logger.debug("Cache module hook ({library}:{hook})...setting false", library=module._FullName, hook=hook)

    def module_invoke_all(self, hook, fullName=False, called_by=None, **kwargs):
        """
        Calls module_invoke for all loaded modules.
        """
        logger.debug("in module_invoke_all: hook: {hook}", hook=hook)
        results = {}
        for module_id, module in self._modulesByUUID.iteritems():
            if int(module._status) != 1:
                continue

            label = module._FullName.lower() if fullName else module._Name.lower()
            try:
                 result = self.module_invoke(module._Name, hook, called_by=called_by, **kwargs)
                 if result is not None:
                     results[label] = result
            except YomboWarning:
                pass
            except YomboHookStopProcessing as e:
                e.collected = results
                e.by_who =  label
                raise

        return results

    @inlineCallbacks
    def load_module_data(self):

        self.startDefer.callback(10)

    def add_imported_module(self, module_id, module_label, module_instance):
        logger.debug("adding module: {module_id}:{module_label}", module_id=module_id, module_label=module_label)
        self._modulesByUUID[module_id] = module_instance
        self._modulesByName[module_label] = module_id

    def del_imported_module(self, module_id, module_label):
        logger.debug("deleting module_id: {module_id} from this list: {list}", module_id=module_id, list=self._modulesByUUID)
        del self._modulesByName[module_label]
        del self._modulesByUUID[module_id]

    def get(self, requestedItem):
        """
        Attempts to find the module requested using a couple of methods. Use the already defined pointer within a
        module to find another other:

            >>> someModule = self._Modules['137ab129da9318']  #by uuid

        or:

            >>> someModule = self._Modules['Homevision']  #by name

        :raises KeyError: Raised when module cannot be found.
        :param requestedItem: The module UUID or module name to search for.
        :type requestedItem: string
        :return: Pointer to module.
        :rtype: module
        """
        if requestedItem in self._modulesByUUID:
#            logger.debug("Looking for {requestedItem} by UUID!", requestedItem=requestedItem)
            return self._modulesByUUID[requestedItem]
        else:
            try:
                requestedUUID = self._modulesByName[requestedItem.lower()]
#                logger.debug("Looking for {requestedItem}, found: {modules}", requestedItem=requestedItem, modules=requestedUUID)
                return self._modulesByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
#                print self._modulesByUUID
                logger.warn("Cannot find module: {requestedItem}", requestedItem=requestedItem)
#                logger.info("Module search error message: {error}", error=e)
                raise KeyError('Module not found.')

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

    def module_devices(self, module_id, return_value='dict'):
        """
        A list of devices types for a given module id.

        :raises YomboWarning: Raised when module_id is not found.
        :param module_id: The Module ID to return device types for.
        :return: A list of device type id's.
        :rtype: list
        """
        if return_value is None:
            return_value = 'dict'
        elif return_value not in (['id', 'dict']):
            raise YomboWarning("module_device_types 'return_value' accepts: 'id' or 'dict'")

        if module_id not in self._modulesByUUID:
            if return_value == 'id':
                return []
            elif return_value == 'dict':
                return {}

        if return_value == 'id':
            temp = []
            if module_id in self._modulesByUUID:
                # print "dt..module_id: %s" % module_id
                # print "dt..self._Modules._modulesByUUID[module_id].device_types: %s" % self._Modules._moduleClasses[module_id].device_types
                for dt in self._modulesByUUID[module_id]._device_types:
                    temp.extend(self._DeviceTypes[dt].get_devices(return_value=return_value))
            tempset = set(temp)
            return list(tempset)
        elif return_value == 'dict':
            temp = {}
            if module_id in self._modulesByUUID:
                # print "dt..module_id: %s" % module_id
                # print "dt..self._Modules._modulesByUUID[module_id].device_types: %s" % self._Modules._moduleClasses[module_id].device_types
                for dt in self._modulesByUUID[module_id]._device_types:
                    temp.update(self._DeviceTypes[dt].get_devices(return_value=return_value))
            # tempset = set(temp)
            # return list(temp)
            return temp

    def module_device_types(self, module_id, return_value=None):
        if return_value is None:
            return_value = 'dict'
        elif return_value not in (['id', 'dict']):
            raise YomboWarning("module_device_types 'return_value' accepts: 'id' or 'dict'")

        if module_id not in self._modulesByUUID:
            if return_value == 'id':
                return []
            elif return_value == 'dict':
                return {}

        if return_value == 'id':
            return self._modulesByUUID[module_id]._device_types
        elif return_value == 'dict':
            results = {}
            for device_type_id in self._modulesByUUID[module_id]._device_types:
                results[device_type_id] = self._DeviceTypes[device_type_id]
            return results


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

        module_results = yield self._YomboAPI.request('POST', '/v1/gateway/%s/module' % self.gwid, api_data)
        print("add module results: %s" % module_results)

        if module_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't add module",
                'apimsg': module_results['content']['message'],
                'apimsghtml': module_results['content']['html_message'],
                'module_id': data['module_id'],
            }
            returnValue(results)

        print("checking if var data... %s" % data)
        if 'variable_data' in data:
            print("adding variable data...")
            variable_data = data['variable_data']
            for field_id, var_data in variable_data.iteritems():
                print("field_id: %s" % field_id)
                print("var_data: %s" % var_data)
                for data_id, value in var_data.iteritems():
                    print("data_id: %s" % data_id)
                    if data_id.startswith('new_'):
                        print("data_id starts with new...")
                        post_data = {
                            'gateway_id': self.gwid,
                            'field_id': field_id,
                            'relation_id': data['module_id'],
                            'relation_type': 'module',
                            'data_weight': 0,
                            'data': value,
                        }
                        # print("post_data: %s" % post_data)
                        var_data_results = yield self._YomboAPI.request('POST', '/v1/variable/data', post_data)
                        print "var_data_results: %s"  % var_data_results
                        if var_data_results['code'] != 200:
                            results = {
                                'status': 'failed',
                                'msg': "Couldn't add module variables",
                                'apimsg': var_data_results['content']['message'],
                                'apimsghtml': var_data_results['content']['html_message'],
                                'module_id': data['module_id']
                            }
                            returnValue(results)
                    else:
                        post_data = {
                            'data_weight': 0,
                            'data': value,
                        }
                        # print("posting to: /v1/variable/data/%s" % data_id)
                        # print("post_data: %s" % post_data)
                        var_data_results = yield self._YomboAPI.request('PATCH', '/v1/variable/data/%s' % data_id, post_data)
                        if var_data_results['code'] != 200:
                            # print("bad results module_results: %s" % module_results)
                            # print("bad results var_data_results: %s" % var_data_results)
                            results = {
                                'status': 'failed',
                                'msg': "Couldn't add module variables",
                                'apimsg': var_data_results['content']['message'],
                                'apimsghtml': var_data_results['content']['html_message'],
                                'module_id': data['module_id']
                            }
                            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Module added.",
            'module_id': data['module_id']
        }
        returnValue(results)

    @inlineCallbacks
    def edit_module(self, module_id, data, **kwargs):
        """
        Edit the module installation information. A reboot is required for this to take effect.

        :param data:
        :param kwargs:
        :return:
        """
        api_data = {
            'install_branch': data['install_branch'],
            'status': data['status'],
        }

        module_results = yield self._YomboAPI.request('PATCH', '/v1/gateway/%s/module/%s' % (self.gwid, module_id), api_data)
        print("module edit results: %s" % module_results)

        if module_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit module",
                'apimsg': module_results['content']['message'],
                'apimsghtml': module_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Module edited.",
            'module_id': module_id
        }
        returnValue(results)

    @inlineCallbacks
    def remove_module(self, module_id, **kwargs):
        """
        Delete a module. Calls the API to perform this task. A restart is required to complete.

        :param module_id: The module ID to disable.
        :param kwargs:
        :return:
        """
        if module_id not in self._modulesByUUID:
            raise YomboWarning("module_id doesn't exist. Nothing to remove.", 300, 'disable_module', 'Modules')

        module_results = yield self._YomboAPI.request('DELETE', '/v1/gateway/%s/module/%s' % (self.gwid, module_id))
        print("delete module results: %s" % module_results)

        if module_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete module",
                'apimsg': module_results['content']['message'],
                'apimsghtml': module_results['content']['html_message'],
            }
            returnValue(results)

        self._LocalDBLibrary.set_module_status(module_id, 2)
        self._LocalDBLibrary.del_variables('module', module_id)

        results = {
            'status': 'success',
            'msg': "Module deleted.",
            'module_id': module_id,
        }
        #todo: add task to remove files.
        #todo: add system for "do something on next startup..."
        returnValue(results)

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

        if module_id not in self._modulesByUUID:
            raise YomboWarning("module_id doesn't exist. Nothing to enable.", 300, 'enable_module', 'Modules')

        module_results = yield self._YomboAPI.request('PATCH', '/v1/gateway/%s/module/%s' % (self.gwid, module_id), api_data)
        print("enable module results: %s" % module_results)

        if module_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't enable module",
                'apimsg': module_results['content']['message'],
                'apimsghtml': module_results['content']['html_message'],
            }
            returnValue(results)

        self._LocalDBLibrary.set_module_status(module_id, 1)

        results = {
            'status': 'success',
            'msg': "Module enabled.",
            'module_id': module_id,
        }
        returnValue(results)

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

        if module_id not in self._modulesByUUID:
            raise YomboWarning("module_id doesn't exist. Nothing to disable.", 300, 'disable_module', 'Modules')

        module_results = yield self._YomboAPI.request('PATCH', '/v1/gateway/%s/module/%s' % (self.gwid, module_id), api_data)
        print("disable module results: %s" % module_results)

        if module_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable module",
                'apimsg': module_results['content']['message'],
                'apimsghtml': module_results['content']['html_message'],
            }
            returnValue(results)

        self._LocalDBLibrary.set_module_status(module_id, 0)

        results = {
            'status': 'success',
            'msg': "Module disabled.",
            'module_id': module_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_module_add(self, data, **kwargs):
        """
        Add a module at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        module_results = yield self._YomboAPI.request('POST', '/v1/module', data)
        # print("module edit results: %s" % module_results)

        if module_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't add module",
                'apimsg': module_results['content']['message'],
                'apimsghtml': module_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Module added.",
            'module_id': module_results['data']['id'],
        }
        returnValue(results)

    @inlineCallbacks
    def dev_module_edit(self, module_id, data, **kwargs):
        """
        Edit a module at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        module_results = yield self._YomboAPI.request('PATCH', '/v1/module/%s' % (module_id), data)
        # print("module edit results: %s" % module_results)

        if module_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit module",
                'apimsg': module_results['content']['message'],
                'apimsghtml': module_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Module edited.",
            'module_id': module_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_module_delete(self, module_id, **kwargs):
        """
        Delete a module at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        module_results = yield self._YomboAPI.request('DELETE', '/v1/module/%s' % module_id)

        if module_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete module",
                'apimsg': module_results['content']['message'],
                'apimsghtml': module_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Module deleted.",
            'module_id': module_id,
        }
        returnValue(results)

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

        module_results = yield self._YomboAPI.request('PATCH', '/v1/module/%s' % module_id, api_data)

        if module_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't enable module",
                'apimsg': module_results['content']['message'],
                'apimsghtml': module_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Module enabled.",
            'module_id': module_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_module_disable(self, module_id, **kwargs):
        """
        Enable a module at the Yombo server level, not at the local gateway level.

        :param module_id: The module ID to disable.
        :param kwargs:
        :return:
        """
        print "disabling module: %s" % module_id
        api_data = {
            'status': 0,
        }

        module_results = yield self._YomboAPI.request('PATCH', '/v1/module/%s' % module_id, api_data)

        if module_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable module",
                'apimsg': module_results['content']['message'],
                'apimsghtml': module_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Module disabled.",
            'module_id': module_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_module_device_type_add(self, module_id, device_type_id):
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

        module_results = yield self._YomboAPI.request('POST', '/v1/module_device_type', data)
        # print("module edit results: %s" % module_results)

        if module_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't associate device type to module",
                'apimsg': module_results['content']['message'],
                'apimsghtml': module_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Device type associated to module.",
            'module_id': module_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_module_device_type_remove(self, module_id, device_type_id):
        """
        Removes an association of a device type from a module

        :param module_id: The module
        :param device_type_id: The device type to  remove association
        :return:
        """

        module_results = yield self._YomboAPI.request('DELETE', '/v1/module_device_type/%s/%s' % (module_id, device_type_id))
        # print("module edit results: %s" % module_results)

        if module_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't remove association device type from module",
                'apimsg': module_results['content']['message'],
                'apimsghtml': module_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Device type removed from module.",
            'module_id': module_id,
        }
        returnValue(results)

    @inlineCallbacks
    def _api_change_status(self, module_id, new_status, **kwargs):
        """
        Used to enabled, disable, or undelete a module. Calls the API

        Disable a module. Calls the API to perform this task. A restart is required to complete.

        :param module_id: The module ID to disable.
        :param kwargs:
        :return:
        """
        # print "disabling module: %s" % module_id
        api_data = {
            'module_id': data['module_id'],
            'install_branch': data['install_branch'],
            'status': 1,
        }

        if module_id not in self._modulesByUUID:
            raise YomboWarning("module_id doesn't exist. Nothing to disable.", 300, 'disable_module', 'Modules')

        module_results = yield self._YomboAPI.request('PATCH', '/v1/gateway/%s/module/%s' % (self.gwid, module_id))
        # print("disable module results: %s" % module_results)

        if module_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable module",
                'apimsg': module_results['content']['message'],
                'apimsghtml': module_results['content']['html_message'],
                'module_id': module_id,
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Module disabled.",
            'module_id': module_id,
        }
        returnValue(results)

