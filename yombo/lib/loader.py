# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `Loader @ Library Documentation <https://yombo.net/docs/libraries/loader>`_

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
  or variables.  This is listed here for completeness. Use a :ref:`framework_utils`
  function to get what is needed.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/loader.html>`_
"""
# Import python libraries
import asyncio
from collections import Callable
from copy import deepcopy
import importlib
import os
import os.path
from packaging.requirements import Requirement as pkg_requirement
import pkg_resources
from re import search as ReSearch
from subprocess import check_output, CalledProcessError
from time import time
import traceback
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import reactor, threads
from twisted.internet.defer import inlineCallbacks, maybeDeferred, Deferred
from twisted.web import client
from functools import reduce

# Import Yombo libraries
from yombo.classes.fuzzysearch import FuzzySearch
from yombo.constants.loader import HARD_LOAD, HARD_UNLOAD, RUN_PHASE
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboCritical, YomboWarning, YomboHookStopProcessing
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.core.settings as settings
import yombo.utils

logger = get_logger("library.loader")
client._HTTP11ClientFactory.noisy = False


class Loader(YomboLibrary):
    """
    Responsible for loading libraries, and then delegating loading modules to
    the modules library.

    Libraries are never reloaded, however, during a reconfiguration,
    modules are unloaded, and then reloaded after configurations are done
    being downloaded.
    """

    @property
    def gateway_id(self):
        try:
            return self._Configs.get("core.gwid")
        except KeyError as e:
            return "local"

    @gateway_id.setter
    def gateway_id(self, val):
        return

    @property
    def is_master(self):
        if self.operating_mode != "run":
            return 1
        return self._Configs.get("core.is_master")

    @is_master.setter
    def is_master(self, val):
        return

    @property
    def master_gateway_id(self):
        if self.operating_mode != "run":
            return "local"
        return self._Configs.get("core.master_gateway_id")

    @master_gateway_id.setter
    def master_gateway_id(self, val):
        return

    @property
    def operating_mode(self):
        return self._operating_mode

    @operating_mode.setter
    def operating_mode(self, val):
        if RUN_PHASE[self._run_phase] > 1000:
            self._States.set("loader.operating_mode", val, value_type="string", request_context=self._FullName)
            if val == 'run':
                logger.debug("Operating mode set to: {mode}", mode=val)
            else:
                logger.warn("Operating mode set to: {mode}", mode=val)
        self._operating_mode = val

    @property
    def run_phase(self):
        return self._run_phase, RUN_PHASE[self._run_phase]

    @run_phase.setter
    def run_phase(self, val):
        if RUN_PHASE[val] > 500:
            self.loaded_libraries["states"]["loader.run_phase"] = val
        self._run_phase = val

    def __getitem__(self, component_requested):
        """
        Look for a requested component, either a library or a module. This searches thru libraries first, then
        modules.
        """
        logger.debug("looking for: {component_requested}", component_requested=component_requested)
        if component_requested in self.loaded_components:
            logger.debug("found by loaded_components! {component_requested}", component_requested=component_requested)
            return self.loaded_components[component_requested]
        elif component_requested in self.loaded_libraries:
            logger.debug("found by loaded_libraries! {component_requested}", component_requested=component_requested)
            return self.loaded_libraries[component_requested]
        elif component_requested in self._moduleLibrary:
            logger.debug("found by self._moduleLibrary! {component_requested}", component_requested=self._moduleLibrary)
            return self._moduleLibrary[component_requested]
        else:
            raise YomboWarning(f"Loader could not find requested component: {{component_requested}}",
                               "101", "__getitem__", "loader")

    def __init__(self, testing=False):
        super().__init__(self)
        Entity._Root = self  # Configures the _Root attributes within the Entity class.
        self.startup_events_queue = []
        self.run_phase = "system_init"  # This changes with every phase of startup.
        self.operating_mode = "system_init"  # This changes after configuration has been loaded and confirmed.
        self.unittest = testing
        self._moduleLibrary = None
        self.event_loop = None
        self.force_python_module_upgrade = False

        self.requirements = {}  # Track which python modules are required

        self.loaded_components = FuzzySearch({self._ClassPath.lower(): self}, .95)
        self.loaded_libraries = FuzzySearch({self._Name.lower(): self}, .95)
        self._invoke_list_cache = {}  # Store a list of hooks that exist or not. A cache.
        self.sigint = False  # will be set to true if SIGINT is received
        self.hook_counts = {"library": {}, "module": {}}  # keep track of hook names, and how many times it's called.

        reactor.addSystemEventTrigger("before", "shutdown", self.shutdown)

        # Setup which libraries are loaded and in what order.
        hard_load = deepcopy(HARD_LOAD)
        hard_unload = deepcopy(HARD_UNLOAD)

        cmd_line_args = settings.arguments
        app_dir: str = cmd_line_args["app_dir"]
        working_dir: str = cmd_line_args["working_dir"]

        cwd = os.getcwd()
        # Disable libraries. Format of file: Name of the library case-sensitive to skip, one per line.
        skip_libries_path = f"{working_dir}/skip_libraries"
        if os.path.exists(skip_libries_path):
            lines = open(skip_libries_path).read().splitlines()
            for line in lines:
                if line in self.hard_load:
                    del self.hard_load[line]
                if line in self.hard_unload:
                    del self.hard_unload[line]

        # Add libraries to load - one per line. Format: Name,operating_mode,order. Eg: MyLibrary,all,4350
        hard_load_libries_path = f"{working_dir}/hard_load"
        if os.path.exists(hard_load_libries_path):
            lines = open(hard_load_libries_path).read().splitlines()
            for line in lines:
                parts = line.split(",")
                if len(parts) != 3:
                    continue
                hard_load[parts[0]] = {"operating_mode": parts[1], "order": int(parts[2])}

        self.hard_load = dict(sorted(hard_load.items(), key=lambda x: x[1]["order"]))

        # Add libraries to unload - one per line. Format: Name,operating_mode,order. Eg: MyLibrary,all,4350
        hard_unload_libries_path = f"{working_dir}/hard_unload"
        if os.path.exists(hard_unload_libries_path):
            lines = open(hard_unload_libries_path).read().splitlines()
            for line in lines:
                parts = line.split(",")
                hard_unload[parts[0]] = {"operating_mode": parts[1], "order": parts[2]}

        self.hard_unload = dict(sorted(hard_unload.items(), key=lambda x: x[1]["order"]))

    def shutdown(self):
        """
        This is called if SIGINT (ctrl-c) was caught. Very useful incase it was called during startup.
        :return:
        """
        # logger.info("Yombo Gateway stopping.")
        self._run_phase = "shutdown"
        self.sigint = True
        # yield self.unload()

    @inlineCallbacks
    def start_the_gateway(self):
        """
        The primary entry point and is called by the core/GwService. This function loads all the libraries
        and starts the gateway.

        This is effectively the main start function. This loads all the other libraries and calls the modules
        library to load all the modules.
        """
        self.run_phase = "system_start"

        logger.debug("Reading Yombo requirements.txt file and checking for updates.")
        if os.path.isfile("requirements.txt"):
            try:
                f = open("requirements.txt", "r")  # This is blocking, but ok during startup. Use self._Files.read()
                requirements = f.read()
                f.close()
            except Exception as e:
                logger.warn("Unable to process requirements file for loader library, reason: {e}", e=e)
            else:
                requirements = yombo.utils.bytes_to_unicode(requirements.splitlines())
                for line in requirements:
                    yield self.install_python_requirement(line)

        # Get a reference to the asyncio event loop.
        logger.debug("Starting UVLoop")
        yield yombo.utils.sleep(0.01)  # kick the asyncio event loop
        self.event_loop = asyncio.get_event_loop()

        cmd_line_args = settings.arguments
        app_dir: str = cmd_line_args["app_dir"]
        working_dir: str = cmd_line_args["working_dir"]
        logger.debug("Setting working dir and app dir in Entity class.")
        Entity._Configure_Entity_Class_BASIC_REFERENCES_INTERNAL_ONLY_(app_dir=app_dir,
                                                                       working_dir=working_dir, )

        logger.debug("About to load library, operating mode: {operating_mode}", operating_mode=self.operating_mode)
        logger.info("Importing libraries, this can take a few moments.")
        yield self.import_and_init_libraries()  # import and init all libraries
        self._Configs = self.loaded_libraries["configs"]

        if self.sigint:
            return
        logger.debug("Calling load functions of libraries.")

        self._run_phase = "modules_import"
        self.operating_mode = self._operating_mode  # so we can update the State!
        # Sets run phase to modules_pre_init and then modules_init'
        logger.debug("About to call init_modules.")
        yield self._moduleLibrary.init_modules()

        for name, config in self.hard_load.items():
            if self.sigint:
                return
            self._log_loader("debug", name, "library", "modules_imported", "About to call _modules_imported_.")
            if self.check_operating_mode(config["operating_mode"]):
                libraryName = name.lower()
                yield self.invoke_hook("library", libraryName, "_modules_imported_", called_by=self)
                self.hard_load[name]["_modules_imported_"] = True
            else:
                self.hard_load[name]["_modules_imported_"] = False
            self._log_loader("debug", name, "library", "modules_imported", "Finished call to _modules_imported_.")

        self._run_phase = "libraries_load"
        for name, config in self.hard_load.items():
            if self.sigint:
                return
            if self.check_operating_mode(config["operating_mode"]):
                self.hard_load[name]["_load_"] = "Starting"
                libraryName = name.lower()
                yield self.invoke_hook("library", libraryName, "_load_", called_by=self)
                self.hard_load[name]["_load_"] = True
            else:
                self.hard_load[name]["_load_"] = False
            self._log_loader("debug", name, "library", "load", "Finished call to _load_.")

        self._moduleLibrary = self.loaded_libraries["modules"]

        self._run_phase = "libraries_start"
        for name, config in self.hard_load.items():
            if self.sigint:
                return
            self._log_loader("debug", name, "library", "start", "About to call _start_.")
            if self.check_operating_mode(config["operating_mode"]):
                libraryName = name.lower()
                yield self.invoke_hook("library", libraryName, "_start_", called_by=self)
                self.hard_load[name]["_start_"] = True
            else:
                self.hard_load[name]["_start_"] = False
            self._log_loader("debug", name, "library", "_start_", "Finished call to _start_.")

        yield self._moduleLibrary.load_modules()  # includes load & start

        self._run_phase = "libraries_started"
        for name, config in self.hard_load.items():
            if self.sigint:
                return
            self._log_loader("debug", name, "library", "started", "About to call _started_.")
            if self.check_operating_mode(config["operating_mode"]):
                libraryName = name.lower()
                yield self.invoke_hook("library", libraryName, "_started_", called_by=self)
                self.hard_load[name]["_started_"] = True
            else:
                self.hard_load[name]["_started_"] = False

        self._run_phase = "system_loaded"
        for name, config in self.hard_load.items():
            if self.sigint:
                return
            self._log_loader("debug", name, "library", "_libraries_started_", "About to call _libraries_started_.")
            if self.check_operating_mode(config["operating_mode"]):
                libraryName = name.lower()
                yield self.invoke_hook("library", libraryName, "_libraries_started_", called_by=self)
                self.hard_load[name]["_started_"] = True
            else:
                self.hard_load[name]["_started_"] = False

        self.loaded_libraries["notifications"].new(title="System started1",
                                                   message="System successfully started.",
                                                   timeout=300,
                                                   request_context="Yombo Gateway System",
                                                   persist=False,
                                                   always_show=False,
                                                   targets="system_startup_complete",
                                                   )

        for event in self.startup_events_queue:
            created_at = event.pop()
            self.loaded_libraries["events"].new(*event, created_at=created_at)
        self.startup_events_queue = None
        self._run_phase = "gateway_running"
        logger.info("Yombo Gateway started.")

    @inlineCallbacks
    def unload(self):
        """
        Called when the gateway should stop. This will gracefully stop the gateway.

        First, unload all modules, then unload all components.
        """
        self.sigint = True  # it"s 99.999% true - usually only shutdown due to this.
        if self._moduleLibrary is not None:
            yield self._moduleLibrary.unload_modules()
        yield self.unload_libraries()

    @inlineCallbacks
    def install_python_requirement(self, requirement, source=None):
        if source is None:
            source = "System"
        line = yombo.utils.bytes_to_unicode(requirement)
        line = line.strip()
        if len(line) == 0 or line.startswith("#") or line.startswith("git+"):
            return
        logger.debug("Processing requirement: {requirement}", requirement=line)
        requirement = pkg_requirement(line)
        package_name = requirement.name
        package_specifier = requirement.specifier

        if package_name in self.requirements:
            if self.requirements[package_name]['specifier'] == package_specifier:
                self.requirements[package_name]['used_by'].append(source)
                return
            else:
                logger.warn("Unable to install conflicting python module '{name}'. Version '{current}' already set,"
                            " requested '{new}' by: {source}",
                            name=package_name, current=self.requirements[package_name]['specifier'],
                            new=package_specifier, source=source)

                return

        try:
            pkg_info = yield self.get_python_package_info(line, events_queue=self.startup_events_queue)
            # logger.debug("Processing requirement: results: {results}", results=pkg_info)
            if pkg_info is None:
                return
        except YomboWarning as e:
            raise YomboCritical(e.message)
        # logger.debug("Have requirement details...")
        if pkg_info is not None:
            save_info = {
                "name": pkg_info.project_name,
                "version": pkg_info._version,
                "path": pkg_info.location,
                "used_by": [source, ],
                "specifier": package_specifier,
            }
        else:
            save_info = {
                "name": package_name,
                "version": "Invalid python module",
                "path": "Invalid module",
                "used_by": [source, ],
                "specifier": package_specifier,
            }

        self.requirements[package_name] = save_info

    def Loader_i18n_atoms(self, **kwargs):
        return [
            {"loader.operating_mode": {
                "en": "One of: first_run, run, config",
            },
            },
        ]

    def check_component_status(self, name, function):
        if name in self.hard_load:
            if function in self.hard_load[name]:
                return self.hard_load[name][function]
        return None

    @staticmethod
    def _log_loader(level, label, type, method, msg=""):
        """
        A common log format for loading/unloading libraries and modules.

        :param level: Log level - debug, info, warn...
        :param label: Module label "x10", "messages"
        :param type: Type of item being loaded: library, module
        :param method: Method being called.
        :param msg: Optional message to include.
        :return:
        """
        log = getattr(logger, level)
        log("Loader: {label}({type})::{method} - {msg}", label=label, type=type, method=method, msg=msg)

    @staticmethod
    def import_libraries_failure(failure, name):
        logger.error("Got failure during import of library '{name}': {failure}. Going to stop now.", name=name,
                     failure=failure)
        raise YomboCritical("Load failure for gateway library.")

    @inlineCallbacks
    def import_and_init_libraries(self):
        """
        Import then "init" all libraries. Call "loadLibraries" when done.
        """
        logger.debug("import_and_init_libraries gateway libraries.")
        self._run_phase = "libraries_import"
        try:
            for name, config in self.hard_load.items():
                if self.sigint:
                    return
                self.hard_load[name]["__init__"] = "Starting"
                path_name = f"yombo.lib.{name}"

                self.import_component(path_name, name, "library")
                self.hard_load[name]["__init__"] = True

                component = name.lower()
                library = self.loaded_libraries[component]
                if hasattr(library, "_pre_init_") and isinstance(library._pre_init_, Callable) \
                        and yombo.utils.get_method_definition_level(
                    library._pre_init_) != "yombo.core.module.YomboModule":
                    d = Deferred()
                    d.addCallback(
                        lambda ignored: self._log_loader("debug", name, "library", "init", "About to call _pre_init_."))
                    d.addCallback(lambda ignored: maybeDeferred(library._pre_init_))
                    d.callback(1)
                    yield d
        except Exception as e:
            logger.error("Error importing and initing libraries: {e}", e=e)

        magic_library_attributes = {
            "_event_loop": self.event_loop,
            # "_Modules": self._moduleLibrary,
            "_Loader": self,
        }

        # self._moduleLibrary = self.loaded_libraries["modules"]
        for name, value in self.hard_load.items():
            magic_library_attributes[f"_{name}"] = self.loaded_libraries[name.lower()]

        # Setup external references.
        Entity._Configure_Entity_Class_Library_References_INTERNAL_ONLY_(
            magic_library_attributes)  # Configures the _Root attributes within the Entity class.
        yombo.utils.setup_yombo_reference(self)

        self._run_phase = "libraries_init"

        logger.debug("Calling init functions of libraries.")

        # For every library, add a reference to every other library.
        for name, current_library_reference in magic_library_attributes.items():
            current_library_name = name[1:]
            if current_library_name == "event_loop":
                continue
            for library_name, library_reference in magic_library_attributes.items():
                try:
                    setattr(current_library_reference, library_name, library_reference)
                except Exception as e:
                    logger.warn("Error adding library references.")

        # For every library, start it up (call _init_).
        for name, config in self.hard_load.items():
            component = name.lower()
            library = self.loaded_libraries[component]

            self.hard_load[name]["_init_"] = False
            # self._log_loader("debug", name, "library", "init", "Done with load magic attributes.")

            if self.check_operating_mode(config["operating_mode"]) is False:
                continue
            self.hard_load[name]["_init_"] = "Starting"
            if hasattr(library, "_init_") and isinstance(library._init_, Callable) \
                    and yombo.utils.get_method_definition_level(library._init_) != \
                    "yombo.core.module.YomboModule":
                d = Deferred()
                d.addCallback(lambda ignored: self._log_loader("debug", name, "library", "init",
                                                               "About to call _init_."))
                d.addCallback(lambda ignored: maybeDeferred(library._init_))
                d.addErrback(self.import_libraries_failure, name)
                d.callback(1)
                yield d
                self.hard_load[name]["_init_"] = True
            else:
                logger.error("----==(Library doesn't have init function: {name})==-----", name=name)

    def check_operating_mode(self, allowed):
        """
        Checks if something should be run based on the current operating_mode.

        :param allowed: Either string or list or possible operating_modes
        :return: True/False
        """
        operating_mode = self.operating_mode
        if operating_mode is None:
            return True

        def check_operating_mode_inside(mode, operating_mode):
            if mode == "all":
                return True
            elif mode == operating_mode:
                return True
            return False

        if isinstance(allowed, str):  # we have a string
            return check_operating_mode_inside(allowed, operating_mode)
        else:  # we have something else
            for item in allowed:
                if check_operating_mode_inside(item, operating_mode):
                    return True

    def invoke_failure(self, failure, requested_library, hook_name):
        logger.error("Got failure during library invoke for hook ({requested_library}::{hook_name}): {failure}",
                     requested_library=requested_library,
                     hook_name=hook_name,
                     failure=failure)

    @inlineCallbacks
    def invoke_all(self, item_type: str, hook_name: str, called_by, stop_on_error: Optional[bool] = None,
                   hook_items: Optional[list] = None, arguments: Optional = None, _force_debug: Optional[bool] = None):
        """
        Calls invoke_hook for all loaded item_type.

        :param item_type: Either library or module.
        :param hook_name: Name of the hook to call within the library or module.
        :param called_by: Reference of the caller.
        :param stop_on_error: If an exception is raise, should hooks in other item_type be called - default is False.
        :param hook_items: Call only these modules and/or libraries.
        :param arguments: Pass any arguments to the hook. Accepts anything, hook dependant.
        """
        results = {}

        if _force_debug:
            print(f"invoke_all- starting: hook: {hook_name}")
        if item_type not in ("library", "module"):
            raise YomboWarning(f"Unknown item type for invoke_all: {item_type}")

        if hook_items is not None:
            hook_items = hook_items
        else:
            if item_type == "library":
                hook_items = self.loaded_libraries
            elif item_type == "module":
                hook_items = self._Modules.modules
        if stop_on_error is None:
            stop_on_error = False

        # if _force_debug:
        #     print(f"invoke_all- starting: hook_items: {hook_items}")

        for item_name, item in hook_items.items():
            if item._Entity_type == "module" and item._status != 1:  # Only enabled modules.
                continue
            if _force_debug:
                logger.info("invoke all: {item_type}::{item_name} -> {hook_name}",
                         item_type=item._Entity_type, item_name=item._FullName, hook_name=hook_name
                         )
            try:
                response = yield self.do_invoke_hook(item, hook_name, called_by, arguments, _force_debug)
                if response is None:
                    continue
                results[item._FullName] = response
            except (YomboWarning, YomboHookStopProcessing) as e:
                if stop_on_error is True:
                    e.collected = results
                    e.by_who = item._FullName
                    print(f"invoke_all caught error: {e}")
                    raise
            except TypeError as e:
                logger.error("-------------==(TypeError calling hook)==--------------")
                logger.error("----Name: {item},  Details: {hook}", item=item._FullName, hook=hook_name)
                logger.error("-----------------==(arguments)==-----------------------")
                logger.error("{arguments}", arguments=arguments)
                logger.error("-----------------==(Traceback)==-----------------------")
                logger.error("{trace}", trace=traceback.format_exc())
                logger.error("--------------------------------------------------------")
                raise ImportError("Cannot import module, not found.")

        return results

    @inlineCallbacks
    def invoke_hook(self, item_type: str, item_name: str, hook_name: str, called_by,
                    arguments: Optional = None):
        """
        Invokes a hook for a given item_type (libary or module) and the name of the item.

        This is called when only a single library or module should be called.

        :param item_type: Either library or module.
        :param item_name: Name of the library or module to call.
        :param hook_name: Name of the hook to call within the library or module.
        :param called_by: Reference of the caller.
        :param arguments: Pass any arguments to the hook. Accepts anything, hook dependant.
        """
        if item_type == "library":
            item = self.get_library(item_name)
        elif item_type == "module":
            item = self.get_module(item_name)
        else:
            raise YomboWarning(f"Unknown item type for invoke_hook: {item_type}")

        try:
            results = yield self.do_invoke_hook(item, hook_name, called_by, arguments)
        except Exception as e:
            logger.warn("Error calling do_invoke_hook: {e}", e=e)
        return results

    @inlineCallbacks
    def do_invoke_hook(self, item, hook_name: str, called_by, arguments: Optional = None,
                       _force_debug: Optional[bool] = None):
        """
        Does the actual call to the hook.

        :param item: The library or module the hook resides in.
        :param hook_name: Name of the hook to call within the library or module.
        :param called_by: Reference of the caller.
        :param arguments: Pass any arguments to the hook. Accepts anything, hook dependant.
        """
        cache_key = f"{item._Entity_type}.{item._Name.lower()}."
        # logger.info("do_invoke_hook, cache_key: {cache_key}", cache_key=cache_key)
        item_type = item._Entity_type
        final_results = None
        for hook in [hook_name]:
            cache_key_local = f"{cache_key}.{hook}"
        # for hook in [hook_name, "_yombo_universal_hook_"]:
            if cache_key in self._invoke_list_cache:
                if self._invoke_list_cache[cache_key_local] is False:
                    if _force_debug:
                        logger.info("Cache hook ({cache_key_local})...SKIPPED", cache_key_local=cache_key_local)
                    continue  # skip. We already know function doesn"t exist.

            if item._Name.lower() == "loader" and item._Entity_type == "library":
                return

            if not (hook.startswith("_") and hook.endswith("_")):
                actual_hook_name = item._Name.lower() + "_" + hook
            else:
                actual_hook_name = hook

            attributes = {
                "called_by": called_by,
                "hook_name": actual_hook_name,
            }

            if hasattr(item, actual_hook_name):
                method = getattr(item, actual_hook_name)
                if isinstance(method, Callable):
                    if item._Name not in self.hook_counts[item_type]:
                        self.hook_counts[item_type][item._Name] = {}
                    if hook not in self.hook_counts[item_type]:
                        self.hook_counts[item_type][item._Name][actual_hook_name] = {"Total Count": {"count": 0}}
                    if called_by._FullName not in self.hook_counts[item_type][item._Name][actual_hook_name]:
                        self.hook_counts[item_type][item._Name][actual_hook_name][called_by._FullName] = {"count": 0}
                    self.hook_counts[item_type][item._Name][actual_hook_name][called_by._FullName]["count"] = \
                        self.hook_counts[item_type][item._Name][actual_hook_name][called_by._FullName]["count"] + 1
                    self.hook_counts[item_type][item._Name][actual_hook_name]["Total Count"]["count"] = \
                        self.hook_counts[item_type][item._Name][actual_hook_name]["Total Count"]["count"] + 1
                    self._invoke_list_cache[cache_key_local] = True

                    try:
                        d = Deferred()
                        if hook != "_yombo_universal_hook_":
                            d.addCallback(lambda ignored: self._log_loader(
                                "debug", item._Name, item_type, actual_hook_name, f"About to call {actual_hook_name}"))
                        d.addCallback(lambda ignored: maybeDeferred(method,
                                                                    attributes=attributes,
                                                                    arguments=arguments)
                                      )
                        d.addErrback(self.invoke_failure, item, actual_hook_name)
                        d.callback(1)
                        if actual_hook_name == "_yombo_universal_hook_":
                            yield d
                        else:
                            final_results = yield d
                    except RuntimeWarning as e:
                        logger.error("Error calling {item_type} '{item_name}' hook ({hook}): {e}",
                                     item_type=item_type, item_name=item._Name, hook=hook, e=e)

                else:
                    if _force_debug:
                        logger.warn("Cache library hook ({item_name}:{actual_hook_name}) is false: not callable",
                                    item_name=item._FullName, actual_hook_name=actual_hook_name)
                    self._invoke_list_cache[cache_key_local] = False
                    raise YomboWarning(f"Hook is not callable: {actual_hook_name}")
            else:
                if _force_debug:
                    logger.warn("Cache library hook ({item_name}:{actual_hook_name}) is false: non-existent",
                                item_name=item._FullName, actual_hook_name=actual_hook_name)
                self._invoke_list_cache[cache_key_local] = False
        return final_results

    def import_component(self, path_name, component_name, component_type):
        """
        Load component of given name. Can be a core library, or a module.
        """
        pymodulename = path_name.lower()
        self._log_loader("debug", component_name, component_type, "import", "About to import.")
        try:
            pyclassname = ReSearch("(?<=\.)([^.]+)$", path_name).group(1)
        except AttributeError:
            self._log_loader("error", component_name, component_type, "import", f"Not found. Path: {path_name}")
            logger.error("Library or Module not found: {path_name}", path_name=path_name)
            return
        try:
            module_root = __import__(pymodulename, globals(), locals(), [], 0)
        except ImportError as detail:
            self._log_loader("error", component_name, component_type, "import", f"Not found. Path: {path_name}")
            logger.error("--------==(Error: Library or Module not found)==--------")
            logger.error("----Name: {path_name},  Details: {detail}", path_name=path_name, detail=detail)
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.format_exc())
            logger.error("--------------------------------------------------------")
            raise ImportError("Cannot import module, not found.")
        except Exception as e:
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.format_exc())
            logger.error("--------------------------------------------------------")
            logger.warn("An exception of type {etype} occurred in yombo.lib.nodes:import_component. Message: {msg}",
                        etype=type(e), msg=e)
            logger.error("--------------------------------------------------------")
            raise ImportError(e)

        module_tail = reduce(lambda p1, p2: getattr(p1, p2), [module_root, ] + pymodulename.split(".")[1:])
        try:
            klass = getattr(module_tail, pyclassname)
        except Exception as e:
            logger.error("Error getting class instance: {e}", e=e)
            exit()

        # Put the component into various lists
        if not isinstance(klass, Callable):
            logger.error("Unable to start class '{classname}', it's not callable.", classname=pyclassname)
            raise ImportError(f"Unable to start class '{pyclassname}', it's not callable.")
        try:
            # Instantiate the class
            # logger.debug("Instantiate class: {pyclassname}", pyclassname=pyclassname)
            if component_type == "library":
                module_instance = klass(self)  # Start the library class
                if component_name.lower() == "modules":
                    self._moduleLibrary = module_instance
                self.loaded_components["yombo.lib." + str(component_name.lower())] = module_instance
                self.loaded_libraries[str(component_name.lower())] = module_instance
            else:
                # print(f"importing module klass: {klass}")
                module_instance = klass(self._moduleLibrary)  # Start the modules class.
                self.loaded_components["yombo.modules." + str(component_name.lower())] = module_instance
                return module_instance, component_name.lower()
            # logger.debug("Instantiate class: {pyclassname}, done.", pyclassname=pyclassname)

        except YomboCritical as e:
            logger.debug("@!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.debug("{e}", e=e)
            logger.debug("@!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            e.exit()
            raise

    @inlineCallbacks
    def unload_libraries(self):
        """
        Only called when server is doing shutdown. Stops controller, server control and server data..
        """
        logger.debug("Stopping libraries: {stuff}", stuff=self.hard_unload)
        self._run_phase = "libraries_stop"
        yield yombo.utils.sleep(.2)
        for name, config in self.hard_unload.items():
            if self.check_operating_mode(config["operating_mode"]):
                logger.debug("stopping: {name}", name=name)
                yield self.invoke_hook("library", name, "_stop_", called_by=self)
        yield yombo.utils.sleep(1)

        self._run_phase = "libraries_unload"
        for name, config in self.hard_unload.items():
            if self.check_operating_mode(config["operating_mode"]):
                logger.debug("_unload_: {name}", name=name)
                yield self.invoke_hook("library", name, "_unload_", called_by=self)
        yield yombo.utils.sleep(.2)

    def get_library(self, name):
        """ Get a library by it's name. """
        try:
            return self.loaded_libraries[name.lower()]
        except KeyError:
            raise KeyError("No such library: " + str(name))

    def get_module(self, name):
        """ Get a module by it's name. """
        try:
            return self._Modules.loaded_modules[name.lower()]
        except KeyError:
            raise KeyError("No such module: " + str(name))

    def get_loaded_component(self, name):
        """
        Returns loaded module object by name. Module must be loaded.
        """
        return self.loaded_components[name.lower()]

    def get_all_loaded_components(self):
        """
        Returns loaded module object by name. Module must be loaded.
        """
        return self.loaded_components

    def find_function(self, component_type, component_name, component_function):
        """
        Finds a function within the system by name. This is useful for when you need to
        save a pointer to a callback to sql or a dictionary, but cannot save pointers to
        a function because the system may restart. This offers another method to reach
        various functions within the system.

        :param component_type: Either "module" or "library".
        :param component_name: Module or library name.
        :param component_function: Name of the function. A string for direct access to the function or a list
            can be provided and it will search the a dictionary of items for a callback.
        :return:
        """

        if component_type == "library":
            if component_name not in self.loaded_libraries:
                logger.info("Library not found: {loaded_libraries}", loaded_libraries=self.loaded_libraries)
                raise YomboWarning("Cannot library name.")

            if isinstance(component_function, list):
                if hasattr(self.loaded_libraries[component_name], component_function[0]):
                    remote_attribute = getattr(self.loaded_libraries[component_name],
                                               component_function[0])  # the dictionary
                    if component_function[1] in remote_attribute:
                        if not isinstance(remote_attribute[component_function[1]],
                                          Callable):  # the key should be callable.
                            logger.info(
                                "Could not find callable library function by name: '{component_type} ::"
                                " {component_name} :: (list) {component_function}'",
                                component_type=component_type, component_name=component_name,
                                component_function=component_function)
                            raise YomboWarning("Cannot find callable")
                        else:
                            logger.info("Look ma, I found a cool function here.")
                            return remote_attribute[component_function[1]]
            else:
                if hasattr(self.loaded_libraries[component_name], component_function):
                    method = getattr(self.loaded_libraries[component_name], component_function)
                    if not isinstance(method, Callable):
                        logger.info(
                            "Could not find callable modoule function by name: '{component_type} :: {component_name} :: {component_function}'",
                            component_type=component_type, component_name=component_name,
                            component_function=component_function)
                        raise YomboWarning("Cannot find callable")
                    else:
                        return method
        elif component_type == "module":
            modules = self._moduleLibrary
            if component_name not in modules._modulesByName:
                raise YomboWarning("Cannot module name.")

            if hasattr(modules._modulesByName[component_name], component_function[0]):
                remote_attribute = getattr(modules._modulesByName[component_name], component_function[0])
                if component_function[1] in remote_attribute:
                    if not isinstance(remote_attribute[component_function[1]], Callable):  # the key should be callable.
                        logger.info(
                            "Could not find callable module function by name: '{component_type} :: {component_name} :: (list){component_function}'",
                            component_type=component_type, component_name=component_name,
                            component_function=component_function)
                        raise YomboWarning("Cannot find callable")
                    else:
                        logger.info("Look ma, I found a cool function here.")
                        return remote_attribute[component_function[1]]
            else:
                if hasattr(modules._modulesByName[component_name], component_function):
                    method = getattr(modules._modulesByName[component_name], component_function)
                    if not isinstance(method, Callable):
                        logger.info(
                            "Could not find callable module function by name: '{component_type} :: {component_name} :: {component_function}'",
                            component_type=component_type, component_name=component_name,
                            component_function=component_function)
                        raise YomboWarning("Cannot find callable")
                    else:
                        return method
        else:
            logger.warn("Not a valid component_type: {component_type}", component_type=component_type)
            raise YomboWarning("Invalid component_type.")

    @classmethod
    @inlineCallbacks
    def get_python_package_info(cls, required_package_name, install=None, events_queue=None):
        """
        Checks if a given python package name is installed. If so, returns it's info, otherwise returns None.

        :param required_package_name:
        :return:
        """
        global _Yombo
        if install is None:
            install = True

        conditions = ("==", "<=", ">=")
        if any(s in required_package_name for s in conditions) is False:
            logger.warn("Invalid python requirement line: {package_name}", package_name=required_package_name)
            raise YomboWarning("python requirement must specify a version or version with wildcard.")

        requirement = pkg_requirement(required_package_name)
        package_name = requirement.name

        try:
            pkg_info = pkg_resources.get_distribution(required_package_name)
        except pkg_resources.DistributionNotFound as e:
            if events_queue is not None:
                events_queue.append(["pip", "not_found", (str(required_package_name)), time()])
            else:
                _Yombo._Events.new("pip", "not_found", (str(required_package_name)))
            logger.info("Python package {required_package} is missing.",
                        required_package=required_package_name,
                        )
            if install is False:
                return None
        except pkg_resources.VersionConflict as e:
            pkg_info = pkg_resources.get_distribution(package_name)
            logger.info("Python package {required_package} is old. Found: {version_installed}, want: {wanted}",
                        required_package=package_name,
                        version_installed=pkg_info.version,
                        wanted=str(requirement.specifier),
                        )
            if events_queue is not None:
                events_queue.append(["pip", "update_needed",
                                     (package_name, str(pkg_info.version), str(requirement.specifier)), time()])
            else:
                _Yombo._Events.new("pip", "update_needed",
                                   (package_name, str(pkg_info.version), str(requirement.specifier)))
            if install is False:
                return pkg_info

        else:
            return pkg_info

        # We now install the package...
        start_time = time()
        yield cls.install_python_package(required_package_name)
        duration = round(float(time()) - start_time, 4)
        importlib.reload(pkg_resources)
        try:
            pkg_info = pkg_resources.get_distribution(required_package_name)
            logger.info("Python package installed: {name} = {version}",
                        name=pkg_info.project_name, version=pkg_info.version)

            if events_queue is not None:
                events_queue.append(["pip", "installed",
                                     (str(pkg_info.project_name), str(pkg_info.version), duration), time()])
            else:
                _Yombo._Events.new("pip", "installed", (str(pkg_info.project_name), str(pkg_info.version), duration))
            return pkg_info
        except pkg_resources.DistributionNotFound as e:
            raise YomboWarning(f"Unable to upgrade package: {e}")
        return None

    @staticmethod
    @inlineCallbacks
    def install_python_package(package_name):
        def update_pip_module(module_name):
            try:
                logger.info("About to install/upgrade python package: {module_name}", module_name=module_name)
                out = check_output(["pip3", "install", "-U", module_name])
                t = 0, out
            except CalledProcessError as e:
                t = e.returncode, e.message
            return t

        try:
            pip_results = yield threads.deferToThread(update_pip_module, package_name)
            if pip_results[0] != 0:
                raise Exception(pip_results[1])
        except Exception as e:
            logger.error("Unable to install/upgrade python package '{package_name}', reason: {e}",
                         package_name=package_name, e=e)
            logger.error("Try to manually install/update required packages: pip3 install -U -r requirements.txt")
            raise YomboWarning("Unable to install/upgrade python package.")


_loader = None


def setup_loader(testing=False):
    global _loader
    if not _loader:
        _loader = Loader(testing)
    return _loader


def get_loader():
    global _loader
    return _loader


def get_the_loaded_components():
    global _loader
    return _loader.get_all_loaded_components()


def get_library(name):
    global _loader
    return _loader.get_library(name)


def get_module(name):
    global _loader
    return _loader.get_module(name)


def stop_loader():
    global _loader
    if not _loader:
        return
    else:
        _loader.unload()
    return
