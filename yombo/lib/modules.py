# cython: embedsignature=True
# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. rst-class:: floater

.. note::

  For more information see: `Modules @ Projects.yombo.net <https://projects.yombo.net/projects/modules/wiki/Modules>`_

Manages all modules within the system. Provides a single reference to perform module lookup functions, etc.

Also calls module hooks as requested by other libraries and modules.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
#import sys
#import traceback
import ConfigParser
import sys
import traceback
from time import time

# Import twisted libraries
#from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred, DeferredList, Deferred

# Import Yombo libraries
from yombo.core.exceptions import YomboFuzzySearchError, YomboNoSuchLoadedComponentError, YomboWarning, YomboCritical
from yombo.utils.fuzzysearch import FuzzySearch
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.utils

logger = get_logger('library.modules')

class Modules(YomboLibrary):
    """
    A single place for modudule management and reference.
    """

    _rawModulesList = {}

    _modulesByUUID = {}
    _modulesByName = FuzzySearch({}, .92)

    _modules = {}  # Stores a list of modules. Populated by the loader module at startup.

    _localModuleVars = {}  # Used to store modules variables from file import

    def _init_(self, loader):
        """
        Init doesn't do much. Just setup a few variables. Things really happen in start.
        """
        self.loader = loader
        self._DevicesLibrary = self._Libraries['devices']
        self._LocalDBLibrary = self._Libraries['localdb']

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

        See get_module()
        """
        return self.get_module(moduleRequested)

#    def __iter__(self):
#        return self._modulesByUUID.__iter__()

    def __contains__(self, moduleRequested):
        try:
            self.get_module(moduleRequested)
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
        yield self.loader.library_invoke_all("_module_init_")
        yield self.module_init_invoke()  # Call "_init_" of modules

        # Pre-Load
        logger.debug("starting modules::pre-load....")
        yield self.loader.library_invoke_all("_module_preload_")
        yield self.module_invoke_all("_preload_")

        # Load
        yield self.loader.library_invoke_all("_module_load_")
        yield self.module_invoke_all("_load_")

        # Pre-Start
        yield self.loader.library_invoke_all("_module_prestart_")
        yield self.module_invoke_all("_prestart_")

        # Start
        yield self.loader.library_invoke_all("_module_start_")
        yield self.module_invoke_all("_start_")

        yield self.loader.library_invoke_all("_module_started_")
        yield self.module_invoke_all("_started_")

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
        self.loader.library_invoke_all("_module_stop_")
        self.module_invoke_all("_stop_")

        keys = self._modulesByUUID.keys()
        self.loader.library_invoke_all("_module_unload_")
        for moduleUUID in keys:
            module = self._modulesByUUID[moduleUUID]
            try:
                self.module_invoke(module._Name, "_unload_")
            except YomboWarning:
                pass
            finally:
                yield self.loader.library_invoke_all("_module_unloaded_")
                delete_component = module._FullName
                self.del_module(moduleUUID, module._Name.lower())
                del self.loader.loadedComponents[delete_component.lower()]

    @inlineCallbacks
    def build_raw_module_list(self):
        try:
            fp = open("localmodules.ini")
            ini = ConfigParser.SafeConfigParser()
            ini.optionxform=str
            ini.readfp(fp)
            for section in ini.sections():
                options = ini.options(section)
                mLabel = section
                mType = ''
                if 'label' in options:
                    mLabel = ini.get(section, 'label')
                    options.remove('label')
                else:
                    mLabel = section

                if 'type' in options:
                    mType = ini.get(section, 'type')
                    options.remove('type')
                else:
                    mType = 'other'

                newUUID = yombo.utils.random_string()
                self._rawModulesList[newUUID] = {
                  'localsection': section,
                  'machine_label': mLabel,
                  'enabled': "1",
                  'module_type': mType,
                  'id': newUUID, # module_id
                  'install_branch': '__local__',
                }

                self._localModuleVars[mLabel] = {}
                for item in options:
                    logger.debug("Adding module from localmodule.ini: {item}", item=item)
                    if item not in self._localModuleVars[mLabel]:
                        self._localModuleVars[mLabel][item] = []
                    values = ini.get(section, item)
                    values = values.split(",")
                    for value in values:
                        variable = {
                            'machine_label': item,
                            'weight': 0,
                            'value': value,
                            'label': item,
                            'data_weight': 0,
                            'module_id': newUUID,
                            'variable_id': 'xxx',
                            'created': int(time()),
                            'updated': int(time()),
                        }
                        self._localModuleVars[mLabel][variable['machine_label']].append(variable)

#            logger.debug("localmodule vars: {lvars}", lvars=self._localModuleVars)
            fp.close()
        except IOError as (errno, strerror):
            logger.debug("localmodule.ini error: I/O error({errornumber}): {error}", errornumber=errno, error=strerror)


        modulesDB = yield self._LocalDBLibrary.get_modules()
#        print "modulesdb: %s" % modulesDB
        for module in modulesDB:
            self._rawModulesList[module.id] = module.__dict__

#        logger.debug("Complete list of modules, before import: {rawModules}", rawModules=self._rawModulesList)

    def import_modules(self):
        for module_id, module in self._rawModulesList.iteritems():
#            print "module : %s" % module
            pathName = "yombo.modules.%s" % module['machine_label']
            self.loader.import_component(pathName, module['machine_label'], 'module', module['id'])

    @inlineCallbacks
    def module_init_invoke(self):
        """
        Calls the _init_ functions of modules. Can't use basic hook for this due to complex items.
        """
        logger.debug("Calling init functions of modules. {modules}", modules=self._modulesByUUID)
        module_init_deferred = []
        for module_id, module in self._modulesByUUID.iteritems():
            self.modules_invoke_log('debug', module._FullName, 'module', 'init', 'About to call _init_.')
            if yombo.utils.get_method_definition_level(module._init_) != 'yombo.core.module.YomboModule':
#                logger.warn("self.get_module_devices(module['{module_id}'])", module_id=module.dump())
                module._ModuleType = self._rawModulesList[module_id]['module_type']
                module._ModuleUUID = module_id

                module._Atoms = self.loader.loadedLibraries['atoms']
                module._Commands = self.loader.loadedLibraries['commands']
                module._Configs = self.loader.loadedLibraries['configuration']
                module._CronTab = self.loader.loadedLibraries['crontab']
                module._Libraries = self.loader.loadedLibraries
                module._Modules = self
                module._MQTT = self.loader.loadedLibraries['mqtt']
                module._States = self.loader.loadedLibraries['states']
                module._Statistics = self.loader.loadedLibraries['statistics']
                module._Localize = self.loader.loadedLibraries['localize']

                module._DevicesLibrary = self.loader.loadedLibraries['devices']  # Basically, all devices
                module._Devices = self._DevicesLibrary.get_devices_for_module(module_id)
                module._DevicesByType = getattr(self._DevicesLibrary, "get_devices_by_device_type")
                module._DeviceTypes = self._DevicesLibrary.get_devices_type_for_module(module_id)

                # Get variables, and merge with any local variable settings
                module_variables = yield self._LocalDBLibrary.get_variables('module', module_id)
                module._ModuleVariables = module_variables


                if module._Name in self._localModuleVars:
                    module._ModuleVariables = yombo.utils.dict_merge(module._ModuleVariables, self._localModuleVars[module._Name])
                    del self._localModuleVars[module._Name]
#                module._init_()
#                continue
                module_init_deferred.append(maybeDeferred(module._init_))
                continue
                try:
                    d = yield maybeDeferred(module._init_)
#                    d.errback(self.SomeError)
#                    yield d
                except YomboCritical, e:
                    logger.error("---==(Critical Server Error in _init_ function for module: {name})==----", name=module._FullName)
                    logger.error("--------------------------------------------------------")
                    logger.error("Error message: {e}", e=e)
                    logger.error("--------------------------------------------------------")
                    e.exit()
                except:
                    logger.error("-------==(Error in init function for library: {name})==---------", name=module._FullName)
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
        yield DeferredList(module_init_deferred)
#        logger.debug("!!!!!!!!!!!!!!!!!!!!!2 Done yielding for while waiting for module_init's to be done!")

    def SomeError(self, error):
        logger.error("Received an error: {error}", error=error)

#    @inlineCallbacks
    def module_invoke(self, requestedModule, hook, **kwargs):
        """
        Invokes a hook for a a given module. Passes kwargs in, returns the results to caller.
        """
        module = self.get_module(requestedModule)
        if module._Name == 'yombo.core.module.YomboModule':
            raise YomboWarning("Cannot call YomboModule hooks")
        if not (hook.startswith("_") and hook.endswith("_")):
            hook = module._Name + "_" + hook
        self.modules_invoke_log('debug', requestedModule, 'module', hook, 'About to call.')
        if hasattr(module, hook):
            method = getattr(module, hook)
            if callable(method):
#                return method(**kwargs)
                try:
#                    results = yield maybeDeferred(method, **kwargs)
                    return method(**kwargs)
                except YomboCritical, e:
                    logger.error("---==(Critical Server Error in {hook} function for module: {name})==----", hook=hook, name=module._FullName)
                    logger.error("--------------------------------------------------------")
                    logger.error("Error message: {e}", e=e)
                    logger.error("--------------------------------------------------------")
                    e.exit()
#                except:
#                    exc_type, exc_value, exc_traceback = sys.exc_info()
#                    logger.error("------==(ERROR During {hooke} of module: {name})==-------", hook=hook, name=module._FullName)
#                    logger.error("1:: {e}", e=sys.exc_info())
#                    logger.error("---------------==(Traceback)==--------------------------")
#                    logger.error("{e}", e=traceback.print_exc(file=sys.stdout))
#                    logger.error("--------------------------------------------------------")
#                    logger.error("{e}", e=traceback.print_exc())
#                    logger.error("--------------------------------------------------------")
#                    logger.error("{e}", e=repr(traceback.print_exception(exc_type, exc_value, exc_traceback,
#                              limit=5, file=sys.stdout)))
#                    logger.error("--------------------------------------------------------")
            else:
                logger.debug("----==(Module {module} doesn't have a callable function: {function})==-----", module=module._FullName, function=hook)

    def module_invoke_all(self, hook, fullName=False, **kwargs):
        """
        Calls module_invoke for all loaded modules.
        """
        logger.debug("in module_invoke_all: hook: {hook}", hook=hook)
        results = {}
        for moduleUUID, module in self._modulesByUUID.iteritems():
            label = module._FullName.lower() if fullName else module._Name.lower()
            try:
                 result = self.module_invoke(module._Name, hook, **kwargs)
                 if result is not None:
                     results[label] = result
            except YomboWarning:
                pass

        return results

    @inlineCallbacks
    def load_module_data(self):

        self.startDefer.callback(10)

    def add_module(self, module_id, module_label, modulePointer):
        logger.debug("adding module: {module_id}:{module_label}", module_id=module_id, module_label=module_label)
        self._modulesByUUID[module_id] = modulePointer
        self._modulesByName[module_label] = module_id

    def del_module(self, module_id, module_label):
        logger.debug("deleting module_id: {module_id} from this list: {list}", module_id=module_id, list=self._modulesByUUID)
        del self._modulesByName[module_label]
        del self._modulesByUUID[module_id]

    def get_module(self, requestedItem):
        """
        Attempts to find the module requested using a couple of methods. Use the already defined pointer within a
        module to find another other:

            >>> someModule = self._Modules['137ab129da9318']  #by uuid
        or:
            >>> someModule = self._Modules['Homevision']  #by name

        See: :func:`yombo.core.helpers.getModule` for usage example.

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