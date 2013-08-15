#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
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
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""
from re import search as ReSearch
import ConfigParser
import traceback
import sys

from twisted.internet import reactor, defer
from twisted.internet.task import LoopingCall

from yombo.core.db import DBTools
from yombo.core.exceptions import GWCritical, NoSuchLoadedComponentError
from yombo.core.fuzzysearch import FuzzySearch
from yombo.core.helpers import generateRandom
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger

logger = getLogger('library.loader')

HARD_LOAD = [
    "Configuration",
    "Startup",
    "GatewayControl",
    "ConfigurationUpdate",
    "Times",
    "Commands",
    "VoiceCmds",
    "Devices",
    "Messages",
    "Listener",
]

HARD_UNLOAD = [
    "Listener",
    "Messages",
    "GatewayControl",
    "Controller",
    "Devices",
    "Configuration",
]

class Loader(YomboLibrary):
    """
    Responsible for loading libraries, loads and reloads and modules.
    
    Libraries are never reloaded, however, during a reconfiguration,
    modules are unloaded, and then reloaded after configurations are down
    being downloaded.
    """
#    zope.interface.implements(ILibrary)

    def __init__(self):
        YomboLibrary.__init__(self)

        self.loadedComponents = FuzzySearch({self._FullName.lower(): self}, .95)
        self.loadedLibraries = {}
        self.loadedModules = {}
        self.moduleNames = {}
        self.libraryNames = {}
        self.__modulesByUUID = {}
        self.__modulesByName = FuzzySearch(None, .92)
        self.__localModuleVars = {}
        self._SQLDictUpdates = {}

    def load(self):  #on startup, load libraried, then modules
        """
        This is effectively the main start function.

        This function is called when the gateway is to startup. In turn,
        this function will load all the components and modules of the gateway.
        """
        self.dbtools = DBTools()

        try:
            self.importLibraries() # import and init all libraries
        except GWCritical, e:
            logger.debug("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.debug("%s" % e)
            logger.debug("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            e.exit()

    def start(self):
        self._saveSQLDictLoop = LoopingCall(self._saveSQLDictDB)
        self._saveSQLDictLoop.start(6)

    def unload(self):
        """
        Called when the gateway should stop. This will gracefully stop the gateway.

        First, unload all modules, then unload all components.
        """
        self.unloadModules("junk", getattr(self, "unloadComponents"))

        self._saveSQLDictDB()
        self._saveSQLDictLoop.stop()

    def setYomboService(self, yomboservice):
        self.YomboService = yomboservice

    def _importComponent(self, pathName, componentName, componentType):
        """
        Load component of given name. Can be a core library, or a module.
        """
        pymodulename = pathName.lower()
        logger.trace("Importing: '%s', with full name: %s. pymodulename: %s", pathName, componentName, pymodulename)
        try:
            pyclassname = ReSearch("(?<=\.)([^.]+)$", pathName).group(1)
        except AttributeError:
            logger.error("Library or Module not found: %s", pathName)
            return False

        try:
            module_root = __import__(pymodulename, globals(), locals(), [], 0)
        except ImportError as detail:
            logger.error("--------==(Error: Library or Module not found)==--------")
            logger.error("----Name: %s,   Details: %s" % (pathName, detail))
            logger.error("--------------------------------------------------------")
            logger.error("1:: %s",sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error(traceback.print_exc(file=sys.stdout))
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
                self.loadedModules[str(componentName.lower())] = moduleinst
                self.loadedComponents[str(componentName.lower())] = moduleinst

                # this is mostly for manhole module, but maybe useful elsewhere?
                temp = componentName.split(".")
                self.moduleNames[temp[-1]] = moduleinst

        except GWCritical, e:
            logger.debug("@!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.debug("%s" % e)
            logger.debug("@!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            e.exit()
            raise

    @defer.deferredGenerator
    def importLibraries(self):
        """
        Import then "init" all libraries. Call "loadLibraries" when done.
        """
        logger.info("Importing gateway libraries.")
        for component in HARD_LOAD:
            pathName = "yombo.lib.%s" % component
            componentName = "yombo.gateway.lib.%s" % component
            self._importComponent(pathName, componentName, 'library')

        logger.info("Calling init functions of libraries.")
        logger.trace("Imported libraries: %s", self.loadedLibraries)
        logger.trace("Imported components: %s", self.loadedComponents)
        for index, name in enumerate(HARD_LOAD):
            componentName = 'yombo.gateway.lib.%s' % name.lower()
            library = self.loadedLibraries[componentName]
#            library.init(self)
#            continue
            if hasattr(library, 'init'):
                logger.trace("Calling init function for library: %s" % componentName)
                try:
#                    wfd = defer.waitForDeferred(defer.maybeDeferred(library.init, self))
                    d = defer.maybeDeferred(library.init, self)
                    d.addErrback(self._handleError)
                    wfd = defer.waitForDeferred(d)
                    yield wfd
                    self.loadingResults = wfd.getResult()
                except GWCritical, e:
                    logger.error("---==(Critical GW Error in init function for library: %s)==----", name)
                    logger.error("--------------------------------------------------------")
                    logger.error("Error message: %s" % e)
                    logger.error("--------------------------------------------------------")
                    e.exit()
                except:
                    logger.error("-------==(Error in init function for library: %s)==---------", name)
                    logger.error("--------------------------------------------------------")
                    logger.error("1:: %s",sys.exc_info())
                    logger.error("---------------==(Traceback)==--------------------------")
                    logger.error(traceback.print_exc(file=sys.stdout))
                    logger.error("--------------------------------------------------------")

            else:
                logger.error("----==(Library doesn't have init function: %s)==-----", name)
        self.loadLibraries()

    @defer.deferredGenerator
    def loadLibraries(self):
        """
        Called the "load" function of libraries.  Calls "startLibraries" when done.
        """
        logger.debug("Calling load functions of libraries.")
        for index, name in enumerate(HARD_LOAD):
            componentName = 'yombo.gateway.lib.%s' % name.lower()
            library = self.loadedLibraries[componentName]
            logger.trace("Calling load function for component: %s", componentName)
            if hasattr(library, 'load'):
#                library.load()
#                continue
                try:
#                    wfd = defer.waitForDeferred(defer.maybeDeferred(library.load))
                    d = defer.maybeDeferred(library.load)
                    d.addErrback(self._handleError)
                    wfd = defer.waitForDeferred(d)
                    yield wfd
                    self.loadingResults = wfd.getResult()
                except:
                    logger.error("1:: %s",sys.exc_info())
                    logger.error("---------------==(Traceback)==--------------------------")
                    logger.error(traceback.print_exc(file=sys.stdout))
                    logger.error("--------------------------------------------------------")
            else:
                logger.error("----==(Library doesn't have load function: %s)==-----", componentName)
        
        self.startLibraries()
        

    @defer.deferredGenerator
    def startLibraries(self):
        """
        Called the "load" function of libraries.
        """
        logger.debug("Calling start function of libraries.")
        for index, name in enumerate(HARD_LOAD):
            componentName = 'yombo.gateway.lib.%s' % name.lower()
            library = self.loadedLibraries[componentName]
            logger.trace("Calling start function for component: %s", componentName)
            if hasattr(library, 'start'):
#                library.start()
#                continue

                try:
#                    wfd = defer.waitForDeferred(defer.maybeDeferred(library.start))
                    d = defer.maybeDeferred(library.start)
                    d.addErrback(self._handleError)
                    wfd = defer.waitForDeferred(d)
                    yield wfd
                    self.loadingResults = wfd.getResult()
                except:
                    logger.error("----==(Error in start function for library: %s)==-----", componentName)
                    logger.error("1:: %s",sys.exc_info())
                    logger.error("---------------==(Traceback)==--------------------------")
                    logger.error(traceback.print_exc(file=sys.stdout))
                    logger.error("--------------------------------------------------------")
            else:
                logger.error("----==(Library doesn't have init function: %s)==-----", componentName)

        self.downloadModules()

    def downloadModules(self):
        from yombo.lib.downloadmodules import DownloadModules
        DLModule = DownloadModules()
        DLModule.init(self)
        d = DLModule.load()
        d.addCallback(self.loadModules)
        
    @defer.deferredGenerator
    def loadModules(self, tossmeaway):
        """
        Load modules configured to run at startup.
        """
        if len(self.loadedModules) > 0:
            logger.warning("Modules already loaded, why again??")
            return

        modules = {}
        try:
            fp = open("localmodules.ini")
            ini = ConfigParser.SafeConfigParser()
            ini.readfp(fp)
            for section in ini.sections():
                options = ini.options(section)
                mLabel = ''
                mType = ''
                if 'label' in options:
                    mLabel = ini.get(section, 'label')
                    options.remove('label')
                else:
                    mLabel = section

                if 'typel' in options:
                    type = ini.get(section, 'type')
                else:
                    type = 'other'
                    options.remove('type')
                    
                modules[section] = { 
                  'modulelabel' : mLabel,
                  'enabled' : "1",
                  'moduletype' : mType,
                  'moduleuuid' :  generateRandom(),
                  'installsource' : 'local',
                }
                
                self.__localModuleVars[section.lower()] = {}
                for item in options:
                    self.__localModuleVars[section.lower()][item.lower()] = (ini.get(section, item),)


            fp.close()
        except IOError as (errno, strerror):
            logger.trace("localmodule.ini error: I/O error(%s): %s", errno, strerror)

        modulesDB = self.dbtools.getModules()
        for module in modulesDB:
            modules[module["modulelabel"]] = module

        logger.trace("Complete list of modules, before import: %s", modules)

        for module in modules:
            pathName = "yombo.modules.%s" % module
            componentName = "yombo.gateway.modules.%s" % module
            self._importComponent(pathName, componentName, 'module')

        logger.debug("Calling init functions of modules.")
        for name, module in self.loadedModules.iteritems():
            self.__modulesByName[modules[module._Name]['modulelabel'].lower()] = self.loadedModules[name]
            self.__modulesByUUID[modules[module._Name]['moduleuuid']] = self.loadedModules[name]

            # if varibles set by localmodules, use those variables.
            if module._Name.lower() in self.__localModuleVars:
                module._ModVariables = self.__localModuleVars[module._Name.lower()]

            logger.trace("Calling init function of module: %s, %s ", name, modules[module._Name]['moduleuuid'])
#            module.init()
#            module._Loader(modules[module._Name])
#            continue
            if hasattr(module, 'init'):
                try:
                    module._Loader(modules[module._Name])
#                    wfd = defer.waitForDeferred(defer.maybeDeferred(module.init))
                    d = defer.maybeDeferred(module.init)
                    d.addErrback(self._handleError)
                    wfd = defer.waitForDeferred(d)
                    yield wfd
                    self.loadingResults = wfd.getResult()
                    self._register_voicecmds(module)
                    self._register_distributions(module)
                except:
                    logger.error("------==(ERROR During init of module: %s)==-------", name)
                    traceback.print_exc(file=sys.stdout)
                    logger.error("--------------------------------------------------------")
            else:
                logger.error("----==(Module doesn't have init function: %s)==-----", name)
            
                

        logger.debug("Calling load functions of modules.")
        for name, module in self.loadedModules.iteritems():
            logger.debug("Calling load function of module: %s, %s, from: %s", name, module, module._Name)
#            module.load()
#            continue
            if hasattr(module, 'load'):
                try:
                    d = defer.maybeDeferred(module.load)
                    d.addErrback(self._handleError)
                    wfd = defer.waitForDeferred(d)
                    yield wfd
                    self.loadingResults = wfd.getResult()
                except Exception as err:
                    logger.error("------==(ERROR During loading of module: %s)==-------", name)
                    traceback.print_exc(file=sys.stdout)
                    logger.error("--------------------------------------------------------")
            else:
                logger.error("----==(Module doesn't have load function: %s)==-----", name)

        self.startModules()
    
    def startModules(self):
        logger.debug("Calling start functions of modules.")
        for name, module in self.loadedModules.iteritems():
            logger.trace("Calling start function of module: %s, %s", name, module)
#            module.start()
#            continue
            if hasattr(module, 'start'):
                try:
                    module.start()
                except:
                    logger.error("---------==(ERROR During starting of module)==-----------")
                    traceback.print_exc(file=sys.stdout)
                    logger.error("--------------------------------------------------------")
            else:
                logger.error("----==(Module doesn't have start function: %s, %s)==-----", name, module)

        # send queued and delayed messages after all libraried and modules are started
        self.loadedComponents['yombo.gateway.lib.messages'].modulesStarted()

    def _handleError(self, err):
#        logger.error("Error caught: %s", err.getErrorMessage())
#        logger.error("Error type: %s  %s", err.type, err.value)
        err.raiseException()

    def _register_distributions(self, component):
        # libraries and classes can register message distributions
        # Used as a way to broadcast messages.
        if hasattr(component, '_RegisterDistributions'):
            for list in component._RegisterDistributions:
                logger.debug("For module '%s', adding distro: %s", component._FullName, list)
                self.loadedComponents['yombo.gateway.lib.messages'].updateSubscription("add", list, component._FullName)

    def _register_voicecmds(self, component):
        # libraries and classes can register message distributions
        # Used as a way to broadcast messages.
        if hasattr(component, '_RegisterVoiceCommands'):
            for list in component._RegisterVoiceCommands:
                logger.debug("For module '%s', adding voicecmd: %s, order: %s", list['voiceCmd'], component._FullName, list['order'])
                self.loadedLibraries['yombo.gateway.lib.voicecmds'].add(list['voiceCmd'], component._FullName, 0, list['order'])

    def unloadModules(self, junk, callwhenDone):
        """
        Called when shutting down, durring reconfiguration, or downloading updated
        modules.
        """
        logger.info("Unloading user modules.")
        logger.trace("Modules to unload: %s\n", self.loadedModules)
        for name, module in self.loadedModules.items():
            logger.trace("Calling stop function in module: %s, %s", name, module)
            if hasattr(module, 'stop'):
                try:
                    module.stop()
                except AttributeError:
                    logger.warning("Module '%s' doesn't have stop function defined.", name)

        for name, module in self.loadedModules.items():
            logger.trace("Calling unload function in: %s", name)
            if hasattr(module, 'unload'):
                try:
                    module.unload()
                except AttributeError:
                    logger.warning("Module '%s' doesn't have unload function defined.", name)

            del self.loadedComponents[name]


        self.loadedModules.clear()
        self.loadedComponents['yombo.gateway.lib.messages'].clearDistributions()
        callwhenDone()

    def unloadComponents(self):
        """
        Only called when gateway is doing shutdown. Stops controller, gateway control and gateway data..
        """
        logger.debug("Unloading core... %s", HARD_UNLOAD)
        
        logger.info("Stopping libraries.")
        for component in HARD_UNLOAD:
            logger.debug("checking component: %s", component)
            componentName = "yombo.gateway.lib.%s" % component
            if componentName in self.loadedComponents:
                logger.debug("checking to unload component: %s", componentName)
                if hasattr(self.loadedComponents[componentName], 'stop'):
                    logger.debug("checking component: 333 %s", component)
                    self.loadedComponents[componentName].stop()
                    
        logger.info("Unloading libraries.")
        for component in HARD_UNLOAD:
            logger.debug("checking component: %s", component)
            componentName = "yombo.gateway.lib.%s" % component
            if componentName in self.loadedComponents:
                logger.debug("checking to unload component: %s", componentName)
                if hasattr(self.loadedComponents[componentName], 'unload'):
                    logger.debug("checking component: 333 %s", component)
                    self.loadedComponents[componentName].unload()

    def getLoadedComponent(self, name):
        """
        Returns loaded module object by name. Module must be loaded.
        """
        try:
            return self.loadedComponents[name.lower()]
        except KeyError:
            raise NoSuchLoadedComponentError("No such loaded component: %s" % str(name))

    def getAllLoadedComponents(self):
        """
        Returns loaded module object by name. Module must be loaded.
        """
        return self.loadedComponents

    def getReceiveAllComponents(self):
        return self.receive_all_components


    def getModule(self, moduleRequested):
        """
        Attempts to find the module requested using a couple of methods.

            >>> getModule('137ab129da9318')  #by uuid
        or:
            >>> getModule('Homevision')  #by name

        See: :func:`yombo.core.helpers.getModule` for usage example.

        :raises KeyError: Raised when module cannot be found.
        :param moduleRequested: The module UUID or module name to search for.
        :type moduleRequested: string
        :return: Pointer to module.
        :rtype: module
        """

        if moduleRequested in self.__yombodevices:
            return self.__modulesByUUID[byUUID]
        else:
            try:
                return self.__modulesByName[moduleRequested.lower()]
            except FuzzySearchError, e:
                raise KeyError('Module not found.')

    def saveSQLDict(self, module, dictname, key1, data1):
        if module not in self._SQLDictUpdates:
            self._SQLDictUpdates[module] = {}
        if dictname not in self._SQLDictUpdates[module]:
            self._SQLDictUpdates[module][dictname] = {}
        self._SQLDictUpdates[module][dictname][key1] = data1

    def _saveSQLDictDB(self):
        logger.debug("Saving SQLDictDB")
        for module in self._SQLDictUpdates:
            for dictname in self._SQLDictUpdates[module]:
                for key1 in self._SQLDictUpdates[module][dictname]:
                    self.dbtools.saveSQLDict(module, dictname, key1, self._SQLDictUpdates[module][dictname][key1])

        self.dbtools.commit()
        self._SQLDictUpdates.clear()


_loader = None

def setupLoader():
    global _loader
    if not _loader:
        _loader = Loader()
    return _loader

def getLoader():
    global _loader
    return _loader

def getTheLoadedComponents():
    global _loader
#    if not _loader:
#        _loader = Loader()
#        _loader.load()
    return _loader.getAllLoadedComponents()

def stopLoader():
    global _loader
    if not _loader:
        return
    else:
        _loader.unload()
    return
