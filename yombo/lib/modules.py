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

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/modules.html>`_
"""
# Import python libraries
import configparser
from functools import partial, reduce
import os.path
from pyclbr import readmodule
from time import time
import traceback
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred, Deferred, DeferredList

# Import Yombo libraries
from yombo.constants import MODULE_API_VERSION
from yombo.core.exceptions import YomboHookStopProcessing, YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.utils import bytes_to_unicode, random_string
from yombo.utils.hookinvoke import global_invoke_all

from yombo.classes.maxdict import MaxDict
import collections

logger = get_logger("library.modules")

SYSTEM_MODULES = {
    # This module was removed during the automation revamp. This is left here for future
    # reference on how to add system modules.
    "storagefile": {
        "id": "modulestoragefile",  # module_id
        "gateway_id": "local",
        "user_id": "local",
        "original_user_id": "local",
        "module_type": "logic",
        "machine_label": "StorageFile",
        "label": "Storage - File",
        "short_description": "Adds support to storing files within the filesystem.",
        "medium_description": "Adds support to storing files within the filesystem.",
        "description": "Adds support to storing files within the filesystem.",
        "medium_description_html": "Adds support to storing files within the filesystem.",
        "description_html": "Adds support to storing files within the filesystem.",
        "see_also": "",
        "repository_link": "",
        "issue_tracker_link": "",
        "install_count": 0,
        "doc_link": "",
        "git_link": "",
        "git_auto_approve": "1",
        "public": 2,
        "status": 1,
        "install_branch": "system",
        "require_approved": 0,
        "created_at": int(time()),
        "updated_at": int(time()),
        "load_source": "system modules",
        }
    }


class Modules(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    A single place for modudule management and reference.
    """
    modules: ClassVar[dict] = {}  # Stores a list of modules. Populated by the loader module at startup.
    loaded_modules: ClassVar[dict] = {}  # Stores the machine label with a reference to the module instance

    _rawModulesList: ClassVar[dict] = {}  # used during boot-up. Combined system modules, localmodules.ini, and DB loaded modules.
    disabled_modules: ClassVar[dict] = {}  # List of modules that are blacklisted from the server.

    _storage_attribute_name: ClassVar[str] = "modules"
    _storage_label_name: ClassVar[str] = "module"
    _storage_attribute_sort_key: ClassVar[str] = "_Name"
    _storage_primary_field_name: ClassVar[str] = "_module_id"
    _storage_fields: ClassVar[list] = ["task_id", "description", "call_time", "created_at"]
    _storage_class_reference: ClassVar = None
    _storage_search_fields: ClassVar[List[str]] = [
        "_module_id", "_label", "_machine_label", "_description", "_short_description", "_medium_description",
        "_module_type"
    ]
    module_api_version: ClassVar[str] = MODULE_API_VERSION

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Init doesn't do much. Just setup a few variables. Things really happen in start.
        """
        self._invoke_list_cache = {}  # Store a list of hooks that exist or not. A cache.
        self.hook_counts = {}  # keep track of hook names, and how many times it"s called.
        self.hooks_called = MaxDict(400, {})
        self.disabled_modules = {}
        self.modules_that_are_starting = {}  # a place for modules to register their status.
        if self._Loader.operating_mode == "run":
            logger.debug("Calling load functions of libraries.")
            yield self.build_raw_module_list()  # Create a list of modules, includes localmodules.ini
            yield self.build_requirements()  # Collect all the requirements files...
            yield self.import_modules()

    @inlineCallbacks
    def init_modules(self):
        logger.debug("modules::init_modules....")
        self._Loader._run_phase = "modules_pre_init"
        logger.debug("starting modules::_modules_pre_init_....")
        yield self._Loader.invoke_all("library", "_modules_pre_init_", called_by=self)
        logger.debug("starting modules::init....")
        self._Loader._run_phase = "modules_init"
        yield self.module_init_invoke()  # Call "_init_" of modules
        yield self._Loader.invoke_all("library", "_modules_inited_", called_by=self)

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
        # Pre-Load
        logger.debug("starting modules::pre-load....")
        self._Loader._run_phase = "modules_preload"
        yield self._Loader.invoke_all("module", "_preload_yombo_internal_", called_by=self)
        yield self._Loader.invoke_all("module", "_preload_", called_by=self)
        yield self._Loader.invoke_all("library", "_modules_preloaded_", called_by=self)
        # Load
        self._Loader._run_phase = "modules_load"
        yield self._Loader.invoke_all("module", "_load_yombo_internal_", called_by=self)
        yield self._Loader.invoke_all("module", "_load_", called_by=self)
        yield self._Loader.invoke_all("library", "_modules_loaded_", called_by=self)

        # Pre-Start
        self._Loader._run_phase = "modules_prestart"
        yield self._Loader.invoke_all("module", "_prestart_yombo_internal_", called_by=self)
        yield self._Loader.invoke_all("module", "_prestart_", called_by=self)
        yield self._Loader.invoke_all("library", "_modules_prestarted_", called_by=self)

        # Start
        self._Loader._run_phase = "modules_start"
        yield self._Loader.invoke_all("module", "_start_yombo_internal_", called_by=self)
        yield self._Loader.invoke_all("module", "_start_", called_by=self)
        yield self._Loader.invoke_all("library", "_modules_started_", called_by=self)

        self._Loader._run_phase = "modules_started"
        yield self._Loader.invoke_all("module", "_started_yombo_internal_", called_by=self)
        yield self._Loader.invoke_all("module", "_started_", called_by=self)
        yield self._Loader.invoke_all("library", "_modules_start_finished_", called_by=self)

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
        try:
            self._Loader._run_phase = "modules_unload"
            yield self._Loader.invoke_all("library", "_modules_stop_", called_by=self)
            yield self._Loader.invoke_all("module", "_stop_", called_by=self)
            yield self._Loader.invoke_all("library", "_modules_stopped_", called_by=self)
            yield self._Loader.invoke_all("library", "_modules_unload_", called_by=self)
            yield self._Loader.invoke_all("module", "_unload_", called_by=self)
            yield self._Loader.invoke_all("library", "_modules_unloaded_", called_by=self)
        except Exception as e:
            logger.error("Error unloading modules: {e}", e=e)

    @inlineCallbacks
    def prepare_modules(self) -> None:
        """
        Called by the Loader library. This simply called the build raw modules list and build requirements
        functions.

        In short, this prepares a list of modules to be loaded and all their requirements files are gathered.

        :return:
        """

    @inlineCallbacks
    def build_raw_module_list(self) -> None:
        """
        Creates a complete list of modules to load.
        :return:
        """
        logger.debug("Building raw module list start.")
        try:
            localmodules_ini_path = f"{self._Configs.working_dir}/localmodules.ini"
            logger.debug("Trying to load local modules: {path}", path=localmodules_ini_path)
            ini = configparser.ConfigParser()
            ini.optionxform = str
            ini.read(localmodules_ini_path)

            for section in ini.sections():
                logger.debug("Adding module from localmodules.ini: {section}", section=section)
                options = ini.options(section)
                if "mod_machine_label" in options:
                    mod_machine_label = ini.get(section, "mod_machine_label")
                    options.remove("mod_machine_label")
                else:
                    mod_machine_label = section

                if "mod_label" in options:
                    mod_label = ini.get(section, "mod_label")
                    options.remove("mod_label")
                else:
                    mod_label = section

                if "mod_short_description" in options:
                    mod_short_description = ini.get(section, "mod_short_description")
                    options.remove("mod_short_description")
                else:
                    mod_short_description = section

                if "mod_medium_description" in options:
                    mod_medium_description = ini.get(section, "mod_medium_description")
                    options.remove("mod_medium_description")
                else:
                    mod_medium_description = section

                if "mod_description" in options:
                    mod_description = ini.get(section, "mod_description")
                    options.remove("mod_description")
                else:
                    mod_description = section

                if "mod_medium_description_html" in options:
                    mod_medium_description_html = ini.get(section, "mod_medium_description_html")
                    options.remove("mod_medium_description_html")
                else:
                    mod_medium_description_html = mod_medium_description

                if "mod_description_html" in options:
                    mod_description_html = ini.get(section, "mod_description_html")
                    options.remove("mod_description_html")
                else:
                    mod_description_html = mod_description

                if "mod_module_type" in options:
                    mod_module_type = ini.get(section, "mod_module_type")
                    options.remove("mod_module_type")
                else:
                    mod_module_type = ""

                if "mod_see_also" in options:
                    mod_see_also = ini.get(section, "mod_see_also")
                    options.remove("mod_see_also")
                else:
                    mod_see_also = ""

                if "mod_module_type" in options:
                    mod_module_type = ini.get(section, "mod_module_type")
                    options.remove("mod_module_type")
                else:
                    mod_module_type = ""

                if "mod_doc_link" in options:
                    mod_doc_link = ini.get(section, "mod_doc_link")
                    options.remove("mod_doc_link")
                else:
                    mod_doc_link = ""

                logger.info("Adding module from localmodule.ini: {item}", item=mod_machine_label)

                new_module_id = self._Hash.sha224_compact(str(mod_machine_label).encode())
                self._rawModulesList[new_module_id] = {
                  "id": new_module_id,  # module_id
                  "gateway_id": "local",
                  "user_id": "local",
                  "original_user_id": "local",
                  "module_type": mod_module_type,
                  "machine_label": mod_machine_label,
                  "label": mod_label,
                  "short_description": mod_short_description,
                  "medium_description": mod_medium_description,
                  "description": mod_description,
                  "medium_description_html": mod_medium_description_html,
                  "description_html": mod_description_html,
                  "see_also": mod_see_also,
                  "install_count": 1,
                  "install_branch": "",
                  "require_approved": 0,
                  "repository_link": "",
                  "issue_tracker_link": "",
                  "doc_link": mod_doc_link,
                  "git_link": "",
                  "git_auto_approve": "local",
                  "public": "0",
                  "status": "1",
                  "created_at": int(time()),
                  "updated_at": int(time()),
                  "load_source": "localmodules.ini"
                }

                for field_label in options:
                    variable_field_id = random_string(length=25)
                    field = {
                        "id": variable_field_id,
                        "user_id": self._gateway_id,
                        "variable_group_id": "",
                        "field_machine_label": field_label,
                        "field_label": field_label,
                        "field_description": mod_machine_label,
                        "field_weight": 0,
                        "value_required": 1,
                        "value_max": -8388600,
                        "value_min": 8388600,
                        "value_casing": "none",
                        "encryption": "nosuggestion",
                        "input_type_id": "19oQjpvxx6FLeyPlZ",  # Pretty much anything.
                        # "input_type_id": self._InputTypes.get("string"),
                        "default_value": "",
                        "field_help_text": "localmodules.ini supplied value. Cannot be edited.",
                        "multiple": 1,
                        "created_at": int(time()),
                        "updated_at": int(time()),
                        "_fake_data": True,
                    }
                    logger.debug(" - Module variable field: {label}", label=field_label)
                    self._VariableFields.load_an_item_to_memory(
                        field,
                        load_source="database",
                        request_context="modules::build_raw_module_list",
                        authentication=self.AUTH_USER
                    )

                    values = ini.get(section, field_label)
                    values = values.split(":::")
                    for value in values:
                        value_hash = random_string(length=20)
                        logger.debug(" - Module variable data, value: {value}", value=value)
                        yield self._VariableData.load_an_item_to_memory(
                            {
                                "id": value_hash,
                                "user_id": self._gateway_id,
                                "gateway_id": self._gateway_id,
                                "variable_field_id": variable_field_id,
                                "variable_relation_id": new_module_id,
                                "variable_relation_type": "module",
                                "data": value,
                                "data_content_type": "string",
                                "data_weight": 0,
                                "created_at": int(time()),
                                "updated_at": int(time()),
                            },
                            load_source="database",
                            request_context="modules::build_raw_module_list",
                            authentication=self.AUTH_USER
                        )

        except IOError as xxx_todo_changeme:
            (errno, strerror) = xxx_todo_changeme.args
            logger.debug("localmodule.ini error: I/O error({errornumber}): {error}", errornumber=errno, error=strerror)

        # Local system modules.
        for module_name, data in SYSTEM_MODULES.items():
            if self._Configs.get(f"system_modules.{data['machine_label']}", True) != True:
                continue
            self._rawModulesList[data["id"]] = data

        all_modules = yield self.db_select(orderby="label ASC")
        for module in all_modules:
            self._rawModulesList[module["id"]] = module
            self._rawModulesList[module["id"]]["load_source"] = "database"

        logger.debug("Building raw module list done.")

    @inlineCallbacks
    def build_requirements(self):
        """
        Look thru each module and inspect it's requirements.txt file. Append/update any lines from
        these into the Loader requirements dict.

        :return:
        """
        for module_id, module in self._rawModulesList.items():
            requirements_file = f"yombo/modules/{module['machine_label'].lower()}/requirements.txt"
            logger.debug("checking module requirements file: {file}", file=requirements_file)
            if os.path.isfile(requirements_file):
                try:
                    filesize = os.path.getsize(requirements_file)
                    if filesize == 0:
                        continue
                    input = yield self._Files.read(requirements_file)
                except Exception as e:
                    logger.warn("Unable to process requirements file for module '{module}', reason: {e}",
                                module=module["machine_label"], e=e)
                else:
                    requirements = bytes_to_unicode(input.splitlines())
                    for line in requirements:
                        yield self._Loader.install_python_requirement(line, f"module:{module['machine_label']}")

    @inlineCallbacks
    def import_modules(self):
        """
        This imports the modules into memory (using import_component) and then sets some base module
        attributes.

        :return:
        """
        for module_id, module in self._rawModulesList.items():
            module_path_name = f"yombo.modules.{module['machine_label']}"
            logger.debug("Importing module: {label}", label=module_path_name)
            try:
                module_instance, module_name = self._Loader.import_component(module_path_name,
                                                                             module["machine_label"],
                                                                             "module")
            except ImportError as e:
                logger.error("----------==(Import Error: Loading Module)==------------")
                logger.error("----Name: {module_path_name}", module_path_name=module_path_name)
                logger.error("---------------==(Error)==--------------------------")
                logger.error("{e}", e=e)
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.format_exc())
                logger.error("--------------------------------------------------------")
                logger.error("Not loading module: {label}", label=module["machine_label"])
                continue
            except:
                logger.error("--------------==(Error: Loading Module)==--------------")
                logger.error("----Name: {module_path_name}", module_path_name=module_path_name)
                logger.error("---------------==(Traceback)==--------------------------")
                logger.error("{trace}", trace=traceback.format_exc())
                logger.error("--------------------------------------------------------")
                logger.error("Not loading module: {label}", label=module["machine_label"])
                continue

            try:
                module_instance.AUTH_TYPE = "module"
                module_instance.AUTH_PLATFORM = f"yombo.module.{module['machine_label']}"
                module_instance.AUTH_USER = yield self._Users.new_component_user(
                    "module", module['machine_label'],
                    _request_context="modules::import_modules",
                    _authentication=self.AUTH_USER)
                module_instance._hooks_called = {}
                module_instance._module_id = module["id"]
                module_instance._primary_field_id = module["id"]
                module_instance._user_id = module["user_id"]
                module_instance._original_user_id = module["original_user_id"]
                module_instance._module_type = module["module_type"]
                module_instance._machine_label = module["machine_label"]
                module_instance._label = module["label"]
                module_instance._short_description = module["short_description"]
                module_instance._medium_description = module["medium_description"]
                module_instance._description = module["description"]
                module_instance._medium_description_html = module["medium_description_html"]
                module_instance._description_html = module["description_html"]
                module_instance._see_also = module["see_also"]
                module_instance._repository_link = module["repository_link"]
                module_instance._issue_tracker_link = module["issue_tracker_link"]
                module_instance._install_count = int(module["install_count"])
                module_instance._doc_link = module["doc_link"]
                module_instance._git_link = module["git_link"]
                module_instance._git_auto_approve = module["git_auto_approve"]
                module_instance._public = int(module["public"])
                module_instance._status = int(module["status"])
                module_instance._install_branch = module["install_branch"]
                module_instance._require_approved = int(module["require_approved"])
                module_instance._created_at = int(module["created_at"])
                module_instance._updated_at = int(module["updated_at"])
                module_instance._load_source = module["load_source"]

                self.add_imported_module(module["id"], module_name, module_instance)
            except Exception as e:
                logger.warn("Yombo Library Modules issue loading module magic vars: {e}", e=e)
                raise e

    def module_invoke_failure(self, failure, module_name, hook_name):
        logger.warn("---==(failure during module invoke for hook ({module_name}::{hook_name})==----",
                    module_name=module_name, hook_name=hook_name)
        logger.warn("--------------------------------------------------------")
        logger.warn("{failure}", failure=failure)
        logger.warn("--------------------------------------------------------")
        raise RuntimeError(f"failure during module invoke for hook: {failure}")

    @inlineCallbacks
    def module_init_invoke(self):
        """
        Calls the _init_ functions of modules.
        """
        for module_id, module in self.modules.items():
            logger.debug("Starting module_init_invoke for module: {module}", module=module)

            module._module_starting = partial(
                self.module_starting,
                module,
            )

            module._module_started = partial(
                self.module_started,
                module,
            )

            module._event_loop = self._Loader.event_loop

            module._hooks_called["_init_"] = 0
            if int(module._status) != 1:
                continue

            # logger.debug("Starting module_init_invoke for module: {module} - init starting", module=module)

            try:
                d = Deferred()
                # d.addCallback(lambda ignored: self.modules_invoke_log("debug", module._label, "module", "_init_", "About to call _init_."))
                d.addCallback(lambda ignored: maybeDeferred(module._init_))
                d.addErrback(self.module_invoke_failure, module._Name, "_init_")
                d.addCallback(self._log_hook_called, module._Name + ":_init", module, "_init_", "yombo.lib.modules")
                d.addCallback(lambda ignored: self.modules_invoke_log("debug", module._label, "module", "_init_", "Finished with call _init_."))
                d.callback(1)
                results = yield d
            except RuntimeWarning as e:
                pass
            except Exception as e:
                logger.warn("Disabling module '{module}' due to exception from hook (_init_): {e}",
                            module=module._Name, e=e)
                self.disabled_modules[module_id] = f"Caught exception during call '_init_': {e}"
            # logger.debug("Starting module_init_invoke for module: {module} - init finished", module=module)

    def _log_hook_called(self, results, name, module, hook, called_by):
        # logger.debug("results in _log_hook_called: {results}", results=results)
        self.hooks_called[name] = {
            "module": module._Name,
            "hook": hook,
            "time": int(time()),
            "called_by": called_by,
        }
        return results

    def add_imported_module(self, module_id, module_label, module_instance):
        # logger.debug("adding module: {module_id}:{module_label}", module_id=module_id, module_label=module_label)
        self.modules[module_id] = module_instance
        self.loaded_modules[module_instance] = module_instance._machine_label

    def del_imported_module(self, module_id, module_label):
        logger.debug("deleting module_id: {module_id} from this list: {list}", module_id=module_id, list=self.modules)
        del self.modules[module_id]

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

    @inlineCallbacks
    def module_starting(self, module):
        """ Called by a module that is still bootstrapping. """
        self.modules_that_are_starting[module] = True
        yield self.update_starting_modules_notification(module)

    @inlineCallbacks
    def module_started(self, module):
        """ Called by a module that has finished bootstrapping. """
        del self.modules_that_are_starting[module]
        yield self.update_starting_modules_notification(module)

    @inlineCallbacks
    def update_starting_modules_notification(self, module):
        """
        Update the active list of modules that are still starting.

        :param module:
        :return:
        """
        if len(self.modules_that_are_starting) == 0:
            self._Notifications.delete("modules_that_are_starting")
        else:
            module_labels = []
            for module in self.modules_that_are_starting:
                module_labels.append(module._label)
            modules = "<br>".join(module_labels)
            yield self._Notifications.new(title="Modules still starting",
                                          message=f"The following modules are still starting:<br>{modules}",
                                          persist=False,
                                          priority="high",
                                          always_show=True,
                                          always_show_allow_clear=False,
                                          notice_id="modules_that_are_starting",
                                          local=True,
                                          _request_context=self._FullName,
                                          _authentication=self.AUTH_USER
                                          )

    @inlineCallbacks
    def full_list_modules(self):
        """
        Return a list of dictionaries representing all known commands to this gateway.
        :return:
        """
        items = []
        for module_id, module in self.modules.items():
            module_data = yield module.to_dict()
            items.append(module_data)
        return items

    @inlineCallbacks
    def search_modules_for_files(self, filename: str, recursive: Optional[bool] = None):
        """
        Is used to search through the modules directory, looking for various files. This is primarily used for
        magic file features.

        Examples:
        self._Modules.search_modules_for_files("frontend_configs/index.vue")
        This will return all files within all modules that match the have index.vue files.

        self._Modules.search_modules_for_files("**/somethingelse.txt")
        This will return the full path for the file "somethingelse.txt", regardless of what subdirectory it's in.

        :param filename:
        :param recursive: If true, will do a recursive search. Default: True
        :return:
        """
        results = {}
        for module_id, module in self.modules.items():
            if module._status != 1:
                continue
            more_files = yield self._Files.search_path_for_files(
                f"yombo/modules/{module._machine_label.lower()}/{filename}", recursive)
            results.update(more_files)
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
            "module_id": data["module_id"],
            "install_branch": data["install_branch"],
            "require_approved": data["require_approved"],
            "status": 1,
        }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            yield self._YomboAPI.request("POST",
                                         f"/v1/gateway/{self._gateway_id}/module",
                                         body=api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't add module: {e.message}",
                "apimsg": f"Couldn't add module: {e.message}",
                "apimsghtml": f"Couldn't add module: {e.html_message}",
            }

        if "session" in kwargs:
            session = kwargs["session"]
        else:
            session = None

        if "variable_data" in data:
            # print("adding variable data...")
            variable_data = data["variable_data"]
            for field_id, var_data in variable_data.items():
                # print("field_id: %s" % field_id)
                # print("var_data: %s" % var_data)
                for data_id, value in var_data.items():
                    # print("data_id: %s" % data_id)
                    if data_id.startswith("new_"):
                        # print("data_id starts with new...")
                        post_data = {
                            "gateway_id": self._gateway_id,
                            "field_id": field_id,
                            "relation_id": data["module_id"],
                            "relation_type": "module",
                            "data_weight": 0,
                            "data": value,
                        }
                        # print("post_data: %s" % post_data)
                        try:
                            yield self._YomboAPI.request("POST", "/v1/variable/data",
                                                         body=post_data,
                                                         session=session)
                        except YomboWarning as e:
                            return {
                                "status": "failed",
                                "msg": f"Couldn't add module variables: {e.message}",
                                "apimsg": f"Couldn't add module variables: {e.message}",
                                "apimsghtml": f"Couldn't add module variables: {e.html_message}",
                            }
                    else:
                        post_data = {
                            "data_weight": 0,
                            "data": value,
                        }
                        # print("posting to: /v1/variable/data/%s" % data_id)
                        # print("post_data: %s" % post_data)
                        try:
                            yield self._YomboAPI.request("PATCH",
                                                         f"/v1/variable/data/{data_id}",
                                                         body=post_data,
                                                         session=session)
                        except YomboWarning as e:
                            return {
                                "status": "failed",
                                "msg": f"Couldn't add module variables: {e.message}",
                                "apimsg": f"Couldn't add module variables: {e.message}",
                                "apimsghtml": f"Couldn't add module variables: {e.html_message}",
                            }

        results = {
            "status": "success",
            "msg": "Module added.",
            "module_id": data["module_id"]
        }
        reactor.callLater(.0001,
                          global_invoke_all,
                          "_module_added_",
                          called_by=self,
                          arguments={
                              "module_id": data["module_id"],
                              }
                          )
        if "module_label" in data:
            label = data["module_label"]
        else:
            label = data["module_id"]
        yield self._Notifications.new(title=f"Module added: {label}",
                                      message=f"The module '{label}' has been disabled and will take affect on next reboot.",
                                      timeout=3600,
                                      persist=False,
                                      always_show=False,
                                      targets="module_updated",
                                      _request_context=self._FullName,
                                      _authentication=self.AUTH_USER
                                      )
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
            "install_branch": data["install_branch"],
            "require_approved": data["require_approved"],
            "status": data["status"],
        }

        if "session" in kwargs:
            session = kwargs["session"]
        else:
            session = None
        try:
            yield self._YomboAPI.request("PATCH",
                                         f"/v1/gateway/{self._gateway_id}/module/{module_id}",
                                         body=api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't edit module: {e.message}",
                "apimsg": f"Couldn't edit module: {e.message}",
                "apimsghtml": f"Couldn't edit module: {e.html_message}",
            }

        if "variable_data" in data:
            logger.debug("editing variable data...")
            variable_data = data["variable_data"]
            for field_id, var_data in variable_data.items():
                # print("field_id: %s" % field_id)
                # print("var_data: %s" % var_data)
                for data_id, value in var_data.items():
                    # print("data_id: %s" % data_id)
                    # print("data_id: %s" % type(data_id))
                    if data_id.startswith("new_") or data_id is None or data_id.lower() == "none":
                        # print("data_id starts with new...")
                        post_data = {
                            "gateway_id": self._gateway_id,
                            "field_id": field_id,
                            "relation_id": data["module_id"],
                            "relation_type": "module",
                            "data_weight": 0,
                            "data": value,
                        }
                        # print("post_data: %s" % post_data)
                        try:
                            yield self._YomboAPI.request("POST", "/v1/variable/data",
                                                         body=post_data,
                                                         session=session)
                        except YomboWarning as e:
                            return {
                                "status": "failed",
                                "msg": f"Couldn't add module variables: {e.message}",
                                "apimsg": f"Couldn't add module variables: {e.message}",
                                "apimsghtml": f"Couldn't add module variables: {e.html_message}",
                            }
                    else:
                        post_data = {
                            "data_weight": 0,
                            "data": value,
                        }
                        # print("posting to: /v1/variable/data/%s" % data_id)
                        # print("post_data: %s" % post_data)
                        try:
                            yield self._YomboAPI.request("PATCH",
                                                         f"/v1/variable/data/{data_id}",
                                                         body=post_data,
                                                         session=session)
                        except YomboWarning as e:
                            return {
                                "status": "failed",
                                "msg": f"Couldn't add module variables: {e.message}",
                                "apimsg": f"Couldn't add module variables: {e.message}",
                                "apimsghtml": f"Couldn't add module variables: {e.html_message}",
                            }

        results = {
            "status": "success",
            "msg": "Module edited.",
            "module_id": module_id
        }
        a_module = self.get(module_id)
        reactor.callLater(.0001,
                          global_invoke_all,
                          "_module_updated_",
                          called_by=self,
                          module_id=module_id,
                          module=a_module,
                          )
        yield self._Notifications.new(title=f"Module edited: {a_module._label}",
                                      message=f"The module '{a_module._label}' has been edited.",
                                      timeout=3600,
                                      persist=False,
                                      always_show=False,
                                      targets="module_updated",
                                      _request_context=self._FullName,
                                      _authentication=self.AUTH_USER
                                      )

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
            raise YomboWarning("module_id doesn't exist. Nothing to remove.", 300, "disable_module", "Modules")

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            yield self._YomboAPI.request("DELETE",
                                         f"/v1/gateway/{self._gateway_id}/module/{module_id}",
                                         session=session)
        except YomboWarning as e:
            # print("module delete results: %s" % module_results)
            return {
                "status": "failed",
                "msg": f"Couldn't delete module: {e.message}",
                "apimsg": f"Couldn't delete module: {e.message}",
                "apimsghtml": f"Couldn't delete module: {e.html_message}",
            }

        self._LocalDB.set_module_status(module_id, 2)
        self._LocalDB.del_variables("module", module_id)

        results = {
            "status": "success",
            "msg": "Module deleted.",
            "module_id": module_id,
        }
        a_module = self.get(module_id)
        reactor.callLater(.0001,
                          global_invoke_all,
                          "_module_removed_",
                          called_by=self,
                          arguments={
                              "module_id": module_id,
                              "module": a_module,
                              }
                          )
        yield self._Notifications.new(title=f"Module removed: {a_module._label}",
                                      message=f"The module '{a_module._label}' has been removed and will take affect on next reboot.",
                                      timeout=3600,
                                      persist=False,
                                      always_show=False,
                                      targets="module_updated",
                                      _request_context=self._FullName,
                                      _authentication=self.AUTH_USER
                                      )
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
            "status": 1,
        }

        if module_id not in self.modules:
            raise YomboWarning("module_id doesn't exist. Nothing to enable.", 300, "enable_module", "Modules")
        module = self.modules[module_id]
        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            yield self._YomboAPI.request("PATCH",
                                         f"/v1/gateway/{self._gateway_id}/module/{module_id}",
                                         body=api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't enable module: {e.message}",
                "apimsg": f"Couldn't enable module: {e.message}",
                "apimsghtml": f"Couldn't enable module: {e.html_message}",
            }

        self._LocalDB.set_module_status(module_id, 1)

        results = {
            "status": "success",
            "msg": "Module enabled.",
            "module_id": module_id,
        }
        a_module = self.get(module_id)
        reactor.callLater(.0001,
                          global_invoke_all,
                          "_module_enabled_",
                          called_by=self,
                          arguments={
                              "module_id": module_id,
                              "module": module,
                              }
                          )
        yield self._Notifications.new(title=f"Module enabled: {a_module._label}",
                                      message=f"The module '{a_module._label}' has been enabled and will take affect on next reboot.",
                                      timeout=3600,
                                      persist=False,
                                      always_show=False,
                                      targets="module_updated",
                                      _request_context=self._FullName,
                                      _authentication=self.AUTH_USER
                                      )
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
            "status": 0,
        }

        if module_id not in self.modules:
            raise YomboWarning("module_id doesn't exist. Nothing to disable.", 300, "disable_module", "Modules")

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                session = None

            yield self._YomboAPI.request("PATCH",
                                         f"/v1/gateway/{self._gateway_id}/module/{module_id}",
                                         body=api_data,
                                         session=session)
        except YomboWarning as e:
            # print("module disable results: %s" % module_results)
            return {
                "status": "failed",
                "msg": f"Couldn't disable module: {e.message}",
                "apimsg": f"Couldn't disable module: {e.message}",
                "apimsghtml": f"Couldn't disable module: {e.html_message}",
            }

        self._LocalDB.set_module_status(module_id, 0)

        results = {
            "status": "success",
            "msg": "Module disabled.",
            "module_id": module_id,
        }
        a_module = self.get(module_id)
        reactor.callLater(.0001,
                          global_invoke_all,
                          "_module_disabled_",
                          called_by=self,
                          arguments={
                              "module_id": module_id,
                              }
                          )
        yield self._Notifications.new(title=f"Module disabled: {a_module._label}",
                                      message=f"The module '{a_module._label}' has been disabled and will take affect on next reboot.",
                                      timeout=3600,
                                      persist=False,
                                      always_show=False,
                                      targets="module_updated",
                                      _request_context=self._FullName,
                                      _authentication=self.AUTH_USER
                                      )
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
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't add module: User session missing.",
                    "apimsg": "Couldn't add module: User session missing.",
                    "apimsghtml": "Couldn't add module: User session missing.",
                }

            module_results = yield self._YomboAPI.request("POST", "/v1/module",
                                                          body=data,
                                                          session=session)
        except YomboWarning as e:
            # print("module add results: %s" % module_results)
            return {
                "status": "failed",
                "msg": f"Couldn't add module: {e.message}",
                "apimsg": f"Couldn't add module: {e.message}",
                "apimsghtml": f"Couldn't add module: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Module added.",
            "module_id": module_results["data"]["id"],
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
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't edit module: User session missing.",
                    "apimsg": "Couldn't edit module: User session missing.",
                    "apimsghtml": "Couldn't edit module: User session missing.",
                }
            yield self._YomboAPI.request("PATCH",
                                         f"/v1/module/{module_id}",
                                         body=data,
                                         session=session)
        except YomboWarning as e:
            # print("module edit results: %s" % module_results)
            return {
                "status": "failed",
                "msg": f"Couldn't edit module: {e.message}",
                "apimsg": f"Couldn't edit module: {e.message}",
                "apimsghtml": f"Couldn't edit module: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Module edited.",
            "module_id": module_id,
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
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't delete module: User session missing.",
                    "apimsg": "Couldn't delete module: User session missing.",
                    "apimsghtml": "Couldn't delete module: User session missing.",
                }
            yield self._YomboAPI.request("DELETE",
                                         f"/v1/module/{module_id}",
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't delete module: {e.message}",
                "apimsg": f"Couldn't delete module: {e.message}",
                "apimsghtml": f"Couldn't delete module: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Module deleted.",
            "module_id": module_id,
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
            "status": 1,
        }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't enable module: User session missing.",
                    "apimsg": "Couldn't enable module: User session missing.",
                    "apimsghtml": "Couldn't enable module: User session missing.",
                }
            yield self._YomboAPI.request("PATCH",
                                         f"/v1/module/{module_id}",
                                         body=api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't enable module: {e.message}",
                "apimsg": f"Couldn't enable module: {e.message}",
                "apimsghtml": f"Couldn't enable module: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Module enabled.",
            "module_id": module_id,
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
            "status": 0,
        }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't disable module: User session missing.",
                    "apimsg": "Couldn't disable module: User session missing.",
                    "apimsghtml": "Couldn't disable module: User session missing.",
                }
            yield self._YomboAPI.request("PATCH",
                                         f"/v1/module/{module_id}",
                                         body=api_data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't disable module: {e.message}",
                "apimsg": f"Couldn't disable module: {e.message}",
                "apimsghtml": f"Couldn't disable module: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Module disabled.",
            "module_id": module_id,
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
            "module_id": module_id,
            "device_type_id": device_type_id,
        }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't associate device type to module: User session missing.",
                    "apimsg": "Couldn't associate device type to module: User session missing.",
                    "apimsghtml": "Couldn't associate device type to module: User session missing.",
                }
            yield self._YomboAPI.request("POST",
                                         "/v1/module_device_type",
                                         body=data,
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't associate device type to module: {e.message}",
                "apimsg": f"Couldn't associate device type to module: {e.message}",
                "apimsghtml": f"Couldn't associate device type to module: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Device type associated to module.",
            "module_id": module_id,
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
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't remove association device type from module: User session missing.",
                    "apimsg": "Couldn't remove association device type from module: User session missing.",
                    "apimsghtml": "Couldn't remove association device type from module: User session missing.",
                }
            yield self._YomboAPI.request("DELETE",
                                         f"/v1/module_device_type/{module_id}/{device_type_id}",
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't remove association device type from module: {e.message}",
                "apimsg": f"Couldn't remove association device type from module: {e.message}",
                "apimsghtml": f"Couldn't remove association device type from module: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Device type removed from module.",
            "module_id": module_id,
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
            raise YomboWarning("module_id doesn't exist. Nothing to disable.", 300, "disable_module", "Modules")

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": f"Couldn't {new_status} module: User session missing.",
                    "apimsg": f"Couldn't {new_status} module: User session missing.",
                    "apimsghtml": f"Couldn't {new_status} module: User session missing.",
                }
            yield self._YomboAPI.request("PATCH",
                                         f"/v1/gateway/{self._gateway_id}/module/{module_id}",
                                         session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't {new_status} module: {e.message}",
                "apimsg": f"Couldn't {new_status} module: {e.message}",
                "apimsghtml": f"Couldn't {new_status} module: {e.message}",
            }

        return {
            "status": "success",
            "msg": "Module disabled.",
            "module_id": module_id,
        }

