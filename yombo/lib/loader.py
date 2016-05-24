#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Responsible for importing, starting, and stopping all libraries and modules.

Starts libraries and modules (components) in the following phases.  These
phases are first completed for libraries.  After "start" phase has completed
then modules startup in the same method.

#. Import all components
#. Call "init" for all components
  * Get the component ready, but not do any actual work yet.
  * Components can now see a full list of components there were imported.
#. Call "load" for all components
#. Call "start" for all components

Stops components in the following phases. Modules first, then libraries.

#. Call "stop" for all components
#. Call "unload" for all components

.. warning::

  Module developers and users should not access any of these functions
  or variables.  This is listed here for completeness. Use a :ref:`Helpers`
  function to get what is needed.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from re import search as ReSearch
import sys
import traceback

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred, returnValue, Deferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboCritical, YomboWarning, YomboNoSuchLoadedComponentError
from yombo.core.fuzzysearch import FuzzySearch
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
import yombo.utils

logger = getLogger('library.loader')

HARD_LOAD = [
    "LocalDB",
    "Configuration",
    "Modules",
    "Startup",
    "GPG",
    "Atoms",
    "States",
    "CronTab",
    "Statistics",
    "AMQPYombo",
    "ConfigurationUpdate",
    "DownloadModules",
    "Automation",
    "Times",
    "Commands",
    "VoiceCmds",
    "Devices",
    "Messages",
    "AutomationHelpers",
]

HARD_UNLOAD = [
    "DownloadModules"
    "Messages",
    "Devices",
    "AMQPYombo",
    "Configuration",
    "Statistics",
    "Modules",
]

class Loader(YomboLibrary):
    """
    Responsible for loading libraries, and then delegating loading modules to
    the modules library.

    Libraries are never reloaded, however, during a reconfiguration,
    modules are unloaded, and then reloaded after configurations are done
    being downloaded.
    """
#    zope.interface.implements(ILibrary)

    def __init__(self, testing=False):
        self.unittest = testing
        YomboLibrary.__init__(self)

        self.loadedComponents = FuzzySearch({self._FullName.lower(): self}, .95)
        self.loadedLibraries = FuzzySearch({self._FullName.lower(): self}, .95)
        self.libraryNames = {}
        self.__localModuleVars = {}
        self._SQLDictUpdates = {}
        self._moduleLibrary = None

    @inlineCallbacks
    def load(self):  #on startup, load libraried, then modules
        """
        This is effectively the main start function.

        This function is called when the gateway is to startup. In turn,
        this function will load all the components and modules of the gateway.
        """
        yield self.import_libraries() # import and init all libraries
        logger.info("Calling load functions of libraries.")
        for index, name in enumerate(HARD_LOAD):
             libraryName = name.lower()
             yield self.library_invoke(libraryName, "_load_")
        yield self.start_libraries()

    def start(self):
        self._saveSQLDictLoop = LoopingCall(self._saveSQLDictDB)
        self._saveSQLDictLoop.start(3)

    def unload(self):
        """
        Called when the gateway should stop. This will gracefully stop the gateway.

        First, unload all modules, then unload all components.
        """
        self._moduleLibrary.unload_modules("junk", getattr(self, "unload_components"))

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

    @inlineCallbacks
    def import_libraries(self):
        """
        Import then "init" all libraries. Call "loadLibraries" when done.
        """
        logger.debug("Importing server libraries.")
        for component in HARD_LOAD:
            pathName = "yombo.lib.%s" % component
            self.import_component(pathName, component, 'library')

        logger.debug("Calling init functions of libraries.")
        for index, name in enumerate(HARD_LOAD):
            component = name.lower()
            library = self.loadedLibraries[component]
            self.logLoader('info', component, 'library', 'init', 'About to call _init_.')
            library._Atoms = self.loadedLibraries['atoms']
            library._States = self.loadedLibraries['states']
            library._Modules = self._moduleLibrary
            library._Libraries = self.loadedLibraries
            if hasattr(library, '_init_') and callable(library._init_) and yombo.utils.get_method_definition_level(library._init_) != 'yombo.core.module.YomboModule':
#                stuff = yield library._init_(self)
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


    def start_libraries(self):
        """
        Called the "load" function of libraries.
        """
        self._moduleLibrary = self.loadedLibraries['modules']

        logger.debug("Calling start function of libraries.")
        for index, name in enumerate(HARD_LOAD):
             libraryName =  name.lower()
             self.library_invoke(libraryName, "_start_")

        if self.unittest: # if in test mode, skip downloading and loading modules.  Test your module by enhancing moduleunittest module
          self.loadedComponents['yombo.gateway.lib.messages'].modulesStarted()
        else:
          self._moduleLibrary.load_modules()

    @inlineCallbacks
    def library_invoke(self, requestedLibrary, hook, **kwargs):
        """
        Invokes a hook for a a given library. Passes kwargs in, returns the results to caller.
        """
        kwargs['_modulesLibrary'] = self._moduleLibrary

        library = self.loadedLibraries[requestedLibrary]
        isCoreFunction = True
        if requestedLibrary == 'Loader':
            returnValue(None)
        if not (hook.startswith("_") and hook.endswith("_")):
            isCoreFunction = False
            hook = library._Name + "_" + hook
        if hasattr(library, hook):
            method = getattr(library, hook)
            self.logLoader('debug',requestedLibrary, 'library', 'library_invoke', 'About to call: %s' % hook)
            if callable(method):
               if isCoreFunction:
                   results = yield maybeDeferred(method)
               else:
                   results = yield maybeDeferred(method, **kwargs)
               self.logLoader('debug',requestedLibrary, 'library', 'library_invoke', 'Finished with call: %s' % hook)
               returnValue(results)
#                 try:
#                     if isCoreFunction:
#                         results = yield maybeDeferred(method)
# #                        results = method()
#                     else:
#                         results = method(**kwargs)
#                         returnValue(results)
#                     returnValue(results)
#                 except YomboCritical, e:
#                     logger.error("---==(Critical Server Error in {hook} function for library: {name})==----", hook=hook, name=library._FullName)
#                     logger.error("--------------------------------------------------------")
#                     logger.error("Error message: {e}", e=e)
#                     logger.error("--------------------------------------------------------")
#                     e.exit()
# #                except:
# #                    exc_type, exc_value, exc_traceback = sys.exc_info()
# #                    logger.error("------==(ERROR in function: {hook} in Library: {library})==-------", hook=hook, library=library._FullName)
# #                    logger.error("1:: {e}", e=sys.exc_info())
# #                    logger.error("---------------==(Traceback)==--------------------------")
# #                    logger.error("{e}", e=traceback.print_exc(file=sys.stdout))
# #                    logger.error("--------------------------------------------------------")
# #                    logger.error("{e}", e=traceback.print_exc())
# #                    logger.error("--------------------------------------------------------")
# #                    logger.error("{e}", e=repr(traceback.print_exception(exc_type, exc_value, exc_traceback,
# #                              limit=5, file=sys.stdout)))
# #                    logger.error("--------------------------------------------------------")
            else:
                logger.error("----==(Library {library} doesn't have a callable function: {function})==-----", library=library._FullName, function=hook)
                raise YomboWarning("Hook is not callable: %s" % hook)

    def library_invoke_all(self, hook, fullName=False, **kwargs):
        """
        Calls library_invoke for all loaded libraries.
        """
        results = {}
        for libraryName, library in self.loadedLibraries.iteritems():
            label = library._FullName.lower() if fullName else library._Name.lower()
            logger.debug("invoke all:{libraryName} -> {hook}", libraryName=libraryName, hook=hook )
            try:
                d = self.library_invoke(libraryName, hook, **kwargs)
                if isinstance(d, Deferred):
                    result = getattr(d, 'result', None)
                    if result is not None:
#                      logger.warn("1111aaa:: {libraryName} {hook} {result}", libraryName=libraryName, hook=hook, result=result)
                      results[label] = result
            except YomboWarning:
                pass
        return results

    def import_component(self, pathName, componentName, componentType, componentUUID=None):
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
#        module_root = __import__(pymodulename, globals(), locals(), [], 0)
        try:
            module_root = __import__(pymodulename, globals(), locals(), [], 0)
            pass
        except ImportError as detail:
            self.logLoader('error', componentName, componentType, 'import', 'Not found. Path: %s' % pathName)
            logger.error("--------==(Error: Library or Module not found)==--------")
            logger.error("----Name: {pathName},  Details: {detail}", pathName=pathName, detail=detail)
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")
            return

        module_tail = reduce(lambda p1,p2:getattr(p1, p2),
            [module_root,]+pymodulename.split('.')[1:])
        class_ = getattr(module_tail, pyclassname)

        # Put the component into various lists for mgmt
        try:
            # Instantiate the class
            moduleinst = class_()  # start the class, only libraries get the loader
            if componentType == 'library':
                if componentName.lower() == 'modules':
                    self._moduleLibrary = moduleinst

                self.loadedComponents["yombo.gateway.lib." + str(componentName.lower())] = moduleinst
                self.loadedLibraries[str(componentName.lower())] = moduleinst
                # this is mostly for manhole module, but maybe useful elsewhere?
                temp = componentName.split(".")
                self.libraryNames[temp[-1]] = moduleinst
            else:
                self.loadedComponents["yombo.gateway.modules." + str(componentName.lower())] = moduleinst
                self._moduleLibrary.add_module(componentUUID, str(componentName.lower()), moduleinst)

        except YomboCritical, e:
            logger.debug("@!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.debug("{e}", e=e)
            logger.debug("@!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            e.exit()
            raise

    def unload_components(self):
        """
        Only called when server is doing shutdown. Stops controller, server control and server data..
        """
        logger.debug("Stopping libraries.")
        for component in HARD_UNLOAD:
            logger.debug("checking component: {component}", component=component)
            componentName = "yombo.gateway.lib.%s" % component
            if componentName in self.loadedComponents:
#                self.logLoader('debug', componentName, 'library', 'stop', 'About to call _stop_.')
                LCCN = self.loadedComponents[componentName]
                if hasattr(LCCN, '_stop_') and callable(LCCN._stop_) and yombo.utils.get_method_definition_level(LCCN._stop_) != 'yombo.core.module.YomboModule':
                    self.loadedComponents[componentName]._stop_()

        logger.debug("Unloading libraries.")
        for component in HARD_UNLOAD:
#            logger.debug("checking component: %s", component)
            componentName = "yombo.gateway.lib.%s" % component
            if componentName in self.loadedComponents:
#                self.logLoader('debug', componentName, 'library', 'unload', 'About to call _unload_.')
                LCCN = self.loadedComponents[componentName]
                if hasattr(LCCN, '_unload_') and callable(LCCN._unload_) and yombo.utils.get_method_definition_level(LCCN._unload_) != 'yombo.core.module.YomboModule':
                    self.loadedComponents[componentName]._unload_()

    def _handleError(self, err):
#        logger.error("Error caught: %s", err.getErrorMessage())
#        logger.error("Error type: %s  %s", err.type, err.value)
        err.raiseException()

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
        return
        if module not in self._SQLDictUpdates:
            self._SQLDictUpdates[module] = {}
        if dictname not in self._SQLDictUpdates[module]:
            self._SQLDictUpdates[module][dictname] = {}
        self._SQLDictUpdates[module][dictname][key1] = data1

    @inlineCallbacks
    def _saveSQLDictDB(self):
        if len(self._SQLDictUpdates):
            logger.debug("Saving SQLDictDB")
            for module in self._SQLDictUpdates.keys():
                for dictname in self._SQLDictUpdates[module]:
                    for key1 in self._SQLDictUpdates[module][dictname]:
                        yield self.loadedLibraries['localdb'].set_sql_dict(module, dictname, key1, self._SQLDictUpdates[module][dictname][key1])
                del self._SQLDictUpdates[module]

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