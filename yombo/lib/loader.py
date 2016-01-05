#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Responsible for importing, starting, and stopping all libraries and modules.

Starts libraries and modules (components) in the following phases.  These
phases are first completed for libraries.  After "start" phase has completed
then modules startup in the same method.

# Import all components
# Call "init" for all components
#* Get the component ready, but not do any actual work yet.
#* Components can now see a full list of components there were imported.
# Call "load" for all components
# Call "start" for all components

Stops components in the following phases. Modules first, then libraries.

# Call "stop" for all components
# Call "unload" for all components

.. warning::

   Module developers and users should not access any of these functions
   or variables.  This is listed here for completeness. Use a :ref:`Helpers`
   function to get what is needed.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2015 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from re import search as ReSearch
import ConfigParser
import inspect
import traceback
import sys
#import hashlib
from time import time
#from collections import OrderedDict

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.db import DBTools
from yombo.core.exceptions import YomboCritical, YomboNoSuchLoadedComponentError
from yombo.core.fuzzysearch import FuzzySearch
from yombo.core.helpers import generateRandom
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger

logger = getLogger('library.loader')

HARD_LOAD = [
    "CronTab",
    "Configuration",
    "Startup",
    "Modules",
    "Statistics",
    "AMQPYombo",
    "ConfigurationUpdate",
    "DownloadModules",
    "Times",
    "Commands",
    "VoiceCmds",
    "Devices",
    "Messages",
#    "Listener",
]

HARD_UNLOAD = [
#    "Listener",
    "DownloadModules"
    "Messages",
    "AMQPYombo",
    "Controller",
    "Devices",
    "Configuration",
    "Statistics",
    "Modules",
]

class Loader(YomboLibrary):
    """
    Responsible for loading libraries, loads and reloads and modules.
    
    Libraries are never reloaded, however, during a reconfiguration,
    modules are unloaded, and then reloaded after configurations are down
    being downloaded.
    """
#    zope.interface.implements(ILibrary)

    def __init__(self, testing=False):
        self.unittest = testing
        YomboLibrary.__init__(self)

        self.loadedComponents = FuzzySearch({self._FullName.lower(): self}, .95)
        self.loadedLibraries = {}
        self.moduleNames = {}
        self.libraryNames = {}
        self.__localModuleVars = {}
        self._SQLDictUpdates = {}
        self._DBTools = DBTools()

    def load(self):  #on startup, load libraried, then modules
        """
        This is effectively the main start function.

        This function is called when the gateway is to startup. In turn,
        this function will load all the components and modules of the gateway.
        """
        try:
            self.importLibraries() # import and init all libraries
        except YomboCritical, e:
            logger.debug("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.debug("{e}", e=e)
            logger.debug("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            e.exit()

    def start(self):
        self._saveSQLDictLoop = LoopingCall(self._saveSQLDictDB)
        self._saveSQLDictLoop.start(3)

    def unload(self):
        """
        Called when the gateway should stop. This will gracefully stop the gateway.

        First, unload all modules, then unload all components.
        """
        self.unloadModules("junk", getattr(self, "unloadComponents"))

        self._saveSQLDictDB()
        self._saveSQLDictLoop.stop()

    def logLoader(self, level, label, type, method, msg=""):
        """
        A common log format for loading/unloading libraries and modules.

        :param level: Log level - debug, info, warn...
        :param label: Module label "x10", "messages"
        :param type: Type of item being loaded: library, module
        :param method: Method being called.
        :param msg: Optional message to include.
        :return:
        """
        logit = func = getattr(logger, level)
        logit("({log_source}) Loader: {label}({type})::{method} - {msg}", label=label, type=type, method=method, msg=msg)

    def setYomboService(self, yomboservice):
        self.YomboService = yomboservice

    def _importComponent(self, pathName, componentName, componentType, componentUUID=None):
        """
        Load component of given name. Can be a core library, or a module.
        """
        pymodulename = pathName.lower()
        self.logLoader('debug', componentName, componentType, 'import', 'About to import.')
        try:
            pyclassname = ReSearch("(?<=\.)([^.]+)$", pathName).group(1)
        except AttributeError:
            self.logLoader('error', componentName, componentType, 'import', 'Not found. Path: %s' % pathName)
            logger.error("Library or Module not found: {pathName}", pathName=pathName)
            raise YomboCritical("Library or Module not found: %s", pathName)

        try:
            module_root = __import__(pymodulename, globals(), locals(), [], 0)
        except ImportError as detail:
            self.logLoader('error', componentName, componentType, 'import', 'Not found. Path: %s' % pathName)
            logger.error("--------==(Error: Library or Module not found)==--------")
            logger.error("----Name: {pathName},   Details: {detail}", pathName=pathName, detail=detail)
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")
            return

        module_tail = reduce(lambda p1,p2:getattr(p1, p2),
            [module_root,]+pymodulename.split('.')[1:])
        klass = getattr(module_tail, pyclassname)

        # Put the component into various lists for mgmt
        try:
            if componentType == 'library':
                # Instantiate the class
                moduleinst = klass() # start class and pass the loader
                self.loadedLibraries[str(componentName.lower())] = moduleinst
                self.loadedComponents[str(componentName.lower())] = moduleinst
                # this is mostly for manhole module, but maybe useful elsewhere?
                temp = componentName.split(".")
                self.libraryNames[temp[-1]] = moduleinst
            else:
                # Instantiate the class
                moduleinst = klass()  # start the class, only libraries get the loader
                self.loadedComponents[str(componentName.lower())] = moduleinst

                # this is mostly for manhole module, but maybe useful elsewhere?
                temp = componentName.split(".")
                self.moduleNames[temp[-1]] = moduleinst

                self._moduleLibrary.addModule(componentUUID, str(componentName.lower()), moduleinst)


        except YomboCritical, e:
            logger.debug("@!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.debug("{e}", e=e)
            logger.debug("@!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            e.exit()
            raise

    def getMethodDefinitionLevel(self, meth):
      for cls in inspect.getmro(meth.im_class):
        if meth.__name__ in cls.__dict__: return str(cls)
      return None

    @inlineCallbacks
    def importLibraries(self):
        """
        Import then "init" all libraries. Call "loadLibraries" when done.
        """
        logger.debug("Importing server libraries.")
        for component in HARD_LOAD:
            pathName = "yombo.lib.%s" % component
            componentName = "yombo.gateway.lib.%s" % component
            self._importComponent(pathName, componentName, 'library')

        logger.debug("Calling init functions of libraries.")
        for index, name in enumerate(HARD_LOAD):
            componentName = 'yombo.gateway.lib.%s' % name.lower()
            library = self.loadedLibraries[componentName]
            self.logLoader('debug', componentName, 'library', 'init', 'About to call _init_.')
            if hasattr(library, '_init_') and callable(library._init_) and self.getMethodDefinitionLevel(library._init_) != 'yombo.core.module.YomboModule':
#                library._init_(self)
#                continue
                try:
                    d = yield maybeDeferred(library._init_, self)
                except YomboCritical, e:
                    logger.error("---==(Critical Server Error in init function for library: {name})==----", name=name)
                    logger.error("--------------------------------------------------------")
                    logger.error("Error message: {e}", e=e)
                    logger.error("--------------------------------------------------------")
                    e.exit()
                except:
                    logger.error("-------==(Error in init function for library: {name})==---------", name=name)
                    logger.error("1:: {e}", e=sys.exc_info())
                    logger.error("---------------==(Traceback)==--------------------------")
                    logger.error("{e}", e=traceback.print_exc(file=sys.stdout))
                    logger.error("--------------------------------------------------------")

            else:
                logger.error("----==(Library doesn't have init function: {name})==-----", name=name)
        self.loadLibraries()

    @inlineCallbacks
    def loadLibraries(self):
        """
        Calls the "load" function of libraries.  Calls "startLibraries" when done.
        """
        logger.debug("Calling load functions of libraries.")
        for index, name in enumerate(HARD_LOAD):
            componentName = 'yombo.gateway.lib.%s' % name.lower()
            library = self.loadedLibraries[componentName]
            self.logLoader('debug', componentName, 'library', 'load', 'About to call _load_.')
            if hasattr(library, '_load_') and callable(library._load_) and self.getMethodDefinitionLevel(library._load_) != 'yombo.core.module.YomboModule':
#                library._load_()
#                continue
                try:
                    d = yield maybeDeferred(library._load_)
                except:
                    logger.error( sys.exc_info() )
                    logger.error("---------------==(Traceback)==--------------------------")
                    logger.error("{e}", e=traceback.print_exc(file=sys.stdout))
                    logger.error("--------------------------------------------------------")
            else:
                logger.error("----==(Library doesn't have _load_ function: {componentName})==-----", componentName=componentName)
        self.startLibraries()

    def startLibraries(self):
        """
        Called the "load" function of libraries.
        """
        self._moduleLibrary = self.loadedLibraries['yombo.gateway.lib.modules']

        logger.info("Calling start function of libraries.")
        for index, name in enumerate(HARD_LOAD):
            componentName = 'yombo.gateway.lib.%s' % name.lower()
            library = self.loadedLibraries[componentName]
            self.logLoader('debug', componentName, 'library', 'start', 'About to call _start_.')
            if hasattr(library, '_start_') and callable(library._start_) and self.getMethodDefinitionLevel(library._start_) != 'yombo.core.module.YomboModule':
#                library._start_()
#                continue
                try:
                    startResults = library._start_()
                except:
                    logger.error("----==(Error in _start_ function for library: {componentName})==-----", componentName=componentName)
                    logger.error("1:: {e}", e=sys.exc_info())
                    logger.error("---------------==(Traceback)==--------------------------")
                    logger.error("{e}", e=traceback.print_exc(file=sys.stdout))
                    logger.error("--------------------------------------------------------")
            else:
                logger.error("----==(Library doesn't have _start_ function: {componetName})==-----", componentName=componentName)

        if self.unittest: # if in test mode, skip downloading and loading modules.  Test your module by enhancing moduleunittest module
          self.loadedComponents['yombo.gateway.lib.messages'].modulesStarted()
        else:
          self.loadModules()

    @inlineCallbacks
    def loadModules(self):
        """
        Load modules configured to run at startup.
        """
        if len(self._moduleLibrary._modulesByUUID) > 0:
            logger.warn("Modules already loaded, why again??")
            return

        modules = {}
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

                modules[section] = {
                  'machinelabel' : mLabel,
                  'enabled' : "1",
                  'moduletype' : mType,
                  'moduleuuid' :  generateRandom(),
                  'installsource' : 'local',
                }

                self.__localModuleVars[section] = {}
                for item in options:
                    logger.debug("Adding module from localmodule.ini: {item}", item=item)
                    values = ini.get(section, item)
                    values = values.split(",")
                    vardata = {
                        'updated': int(time()),
                        'machinelabel': item.lower(),
                        'weight': 0,
                        'created': int(time()),
                        'value': values,
                        'label': item,
                        'dataweight': 0,
                        'moduleuuid': modules[section]['moduleuuid'],
                        'variableuuid': 'xxx',
                    }

                    self.__localModuleVars[section][item] = vardata.copy()
            logger.debug("localmodule vars: {lvars}", lvars=self.__localModuleVars)
            fp.close()
        except IOError as (errno, strerror):
            logger.debug("localmodule.ini error: I/O error({errornumber}): {error}", errornumber=errno, error=strerror)

        modulesDB = self._DBTools.getModules()
        for module in modulesDB:
            modules[module["machinelabel"]] = module

        logger.debug("Complete list of modules, before import: {modules}", modules=modules)

        for name, module in modules.iteritems():
            pathName = "yombo.modules.%s" % name
            componentName = "yombo.gateway.modules.%s" % name
            self._importComponent(pathName, componentName, 'module', module['moduleuuid'])

        logger.info("Calling init functions of modules.")
        for name, module in self._moduleLibrary._modulesByUUID.iteritems():
            # if varibles set by localmodules, use those variables.
            if module._Name in self.__localModuleVars:
                module._ModVariables = self.__localModuleVars[module._Name]
            module._preinit_(modules[module._Name])

            self.logLoader('debug', componentName, 'module', 'init', 'About to call _init_.')
            if hasattr(module, '_init_') and callable(module._init_) and self.getMethodDefinitionLevel(module._init_) != 'yombo.core.module.YomboModule':
#                module._init_()
#                continue
                try:
#                    exc_info = sys.exc_info()
                    d = yield maybeDeferred(module._init_)
                    self._register_voicecmds(module)
                    self._register_distributions(module)
                except:
                    logger.failure("Math is hard!")
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    logger.error("------==(ERROR During _init_ of module: {name})==-------", name=name)
                    logger.error("1:: {e}", e=sys.exc_info())
                    logger.error("---------------==(Traceback)==--------------------------")
                    logger.error("{e}", e=traceback.print_exc(file=sys.stdout))
                    logger.error("--------------------------------------------------------")
                    logger.error("{e}", e=traceback.print_exc())
                    logger.error("--------------------------------------------------------")
                    logger.error("{e}", e=repr(traceback.print_exception(exc_type, exc_value, exc_traceback,
                              limit=5, file=sys.stdout)))
                    logger.error("--------------------------------------------------------")
            else:
                logger.error("----==(Module doesn't have _init_ function: {name})==-----", name=name)

        logger.debug("Calling load functions of modules.")
        for name, module in self._moduleLibrary._modulesByUUID.iteritems():
            self.logLoader('debug', componentName, 'module', 'load', 'About to call _load_.')
            if hasattr(module, '_load_') and callable(module._load_) and self.getMethodDefinitionLevel(module._load_) != 'yombo.core.module.YomboModule':
#                module._load_()
#                continue
                try:
                    d = yield maybeDeferred(module._load_)
                except:
                    logger.error("------==(ERROR During _load_ of module: {name})==-------", name=name)
                    logger.error("{e}", e=traceback.print_exc(file=sys.stdout))
                    logger.error("--------------------------------------------------------")
            else:
                logger.error("----==(Module doesn't have _load_ function: {name})==-----", name=name)
        self.startModules()

    def startModules(self):
        logger.debug("Calling start functions of modules.")
        for name, module in self._moduleLibrary._modulesByUUID.iteritems():
            self.logLoader('debug', name, 'module', 'start', 'About to call _start_.')
            if hasattr(module, '_start_') and callable(module._start_) and self.getMethodDefinitionLevel(module._start_) != 'yombo.core.module.YomboModule':
#                module._start_()
#                continue
                try:
                    module._start_()
                except:
                    logger.error("------==(ERROR During _start_ of module: {name})==-------", name=name)
                    logger.error("{e}", e=traceback.print_exc(file=sys.stdout))
                    logger.error("--------------------------------------------------------")
            else:
                logger.error("----==(Module doesn't have _load_ function: {name})==-----", name=name)

        # send queued and delayed messages after all libraried and modules are started
        self.loadedComponents['yombo.gateway.lib.messages'].modulesStarted()

    def connect(self):
        self.loadedComponents['yombo.gateway.lib.gatewaycontrol'].connect()

    def _handleError(self, err):
#        logger.error("Error caught: %s", err.getErrorMessage())
#        logger.error("Error type: %s  %s", err.type, err.value)
        err.raiseException()

    def _register_distributions(self, component):
        # libraries and classes can register message distributions
        # Used as a way to broadcast messages.
        if hasattr(component, '_RegisterDistributions') and component._RegisterDistributions is not None:
            for list in component._RegisterDistributions:
                logger.debug("For module {fullName}', adding distro: {list}", fullName=component._FullName, list=list)
                self.loadedComponents['yombo.gateway.lib.messages'].updateSubscription("add", list, component._FullName)

    def _register_voicecmds(self, component):
        # libraries and classes can register message distributions
        # Used as a way to broadcast messages.
        if hasattr(component, '_RegisterVoiceCommands') and component._RegisterVoiceCommands is not None:
            for list in component._RegisterVoiceCommands:
                logger.debug("For module '{fullName}', adding voicecmd: {voiceCmd}, order: {order}", voiceCmd=list['voiceCmd'], fullName=component._FullName, order=list['order'])
                self.loadedLibraries['yombo.gateway.lib.voicecmds'].add(list['voiceCmd'], component._FullName, None, list['order'])

    def unloadModules(self, junk, callwhenDone):
        """
        Called when shutting down, durring reconfiguration, or downloading updated
        modules.
        """
        logger.info("Unloading user modules.")
        for name, module in self._moduleLibrary._modulesByUUID.iteritems():
            self.logLoader('debug', name, 'module', 'stop', 'About to call _stop_.')
            if hasattr(module, '_stop_') and callable(module._stop_) and self.getMethodDefinitionLevel(module._stop_) != 'yombo.core.module.YomboModule':
                try:
                    module._stop_()
                except AttributeError:
                    logger.warn("Module '{moduleName}' doesn't have _stop_ function defined.", moduleName=name)

        for name, module in self._moduleLibrary._modulesByUUID.iteritems():
            self.logLoader('debug', name, 'module', 'unload', 'About to call _unload_.')
            if hasattr(module, '_unload_') and callable(module._unload_) and self.getMethodDefinitionLevel(module._unload_) != 'yombo.core.module.YomboModule':
                try:
                    module._unload_()
                except AttributeError:
                    logger.warn("Module '{moduleName}' doesn't have _unload_ function defined.", moduleName=name)
                finally:
                    self._moduleLibrary.delModule(module._ModuleUUID)

            del self.loadedComponents[name]

        self.loadedComponents['yombo.gateway.lib.messages'].clearDistributions()
        callwhenDone()

    def unloadComponents(self):
        """
        Only called when server is doing shutdown. Stops controller, server control and server data..
        """
        logger.debug("Unloading core... {hardUnload}", hardUnload=HARD_UNLOAD)

        logger.info("Stopping libraries.")
        for component in HARD_UNLOAD:
            logger.debug("checking component: {component}", component=component)
            componentName = "yombo.gateway.lib.%s" % component
            if componentName in self.loadedComponents:
#                self.logLoader('debug', componentName, 'library', 'stop', 'About to call _stop_.')
                LCCN = self.loadedComponents[componentName]
                if hasattr(LCCN, '_stop_') and callable(LCCN._stop_) and self.getMethodDefinitionLevel(LCCN._stop_) != 'yombo.core.module.YomboModule':
                    self.loadedComponents[componentName]._stop_()

        logger.info("Unloading libraries.")
        for component in HARD_UNLOAD:
#            logger.debug("checking component: %s", component)
            componentName = "yombo.gateway.lib.%s" % component
            if componentName in self.loadedComponents:
#                self.logLoader('debug', componentName, 'library', 'unload', 'About to call _unload_.')
                LCCN = self.loadedComponents[componentName]
                if hasattr(LCCN, '_unload_') and callable(LCCN._unload_) and self.getMethodDefinitionLevel(LCCN._unload_) != 'yombo.core.module.YomboModule':
                    self.loadedComponents[componentName]._unload_()

    def getLoadedComponent(self, name):
        """
        Returns loaded module object by name. Module must be loaded.
        """
        try:
            return self.loadedComponents[name.lower()]
        except KeyError:
            raise YomboNoSuchLoadedComponentError("No such loaded component: %s" % str(name))

    def getAllLoadedComponents(self):
        """
        Returns loaded module object by name. Module must be loaded.
        """
        return self.loadedComponents

    def getReceiveAllComponents(self):
        return self.receive_all_components

    def saveSQLDict(self, module, dictname, key1, data1):
        """
        Called by sqldict to save a dictionary to the SQL database.

        This allows multiple updates to happen to a dictionary without the overhead of constantly updating the
        matching SQL record. This can lead to some data loss.

        :param module:
        :param dictname:
        :param key1:
        :param data1:
        :return:
        """
        if module not in self._SQLDictUpdates:
            self._SQLDictUpdates[module] = {}
        if dictname not in self._SQLDictUpdates[module]:
            self._SQLDictUpdates[module][dictname] = {}
        self._SQLDictUpdates[module][dictname][key1] = data1

    def _saveSQLDictDB(self):
        if len(self._SQLDictUpdates):
            logger.debug("Saving SQLDictDB")
            for module in self._SQLDictUpdates.keys():
                for dictname in self._SQLDictUpdates[module]:
                    for key1 in self._SQLDictUpdates[module][dictname]:
                        self._DBTools.saveSQLDict(module, dictname, key1, self._SQLDictUpdates[module][dictname][key1])
                del self._SQLDictUpdates[module]

            self._DBTools.commit()


_loader = None

def setupLoader(testing=False):
    global _loader
    if not _loader:
        _loader = Loader(testing)
    return _loader

def getLoader():
    global _loader
    return _loader

def getTheLoadedComponents():
    global _loader
    return _loader.getAllLoadedComponents()

def stopLoader():
    global _loader
    if not _loader:
        return
    else:
        _loader.unload()
    return
