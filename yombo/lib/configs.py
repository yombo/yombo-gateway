"""
.. note::

  * End user documentation: `Configs @ User Documentation <https://yombo.net/docs/gateway/web_interface/basic_settings>`_
  * For library documentation, see: `Cache @ Library Documentation <https://yombo.net/docs/libraries/configuration>`_

Handles loading, storing, updating, and saving gateway configuration items.

If you wish to store persistent data for your module, use the
:py:mod:`SQLDict Library <yombo.lib.sqldicts>`.

*Usage**:

.. code-block:: python

   latitude = self._Configs.get("location.latitude", "0", True)  # also can accept default and if a default value should be saved.
   latitude = self._Configs.get("location.latitude", "0", False)  # example of default and no save if default is used.
   self._Configs.set("location.latitude", 100, ref_source=self)  # Save a new latitude location.

An instance of the configuration setting can also be be returned by simply adding "instance=True" to the list
of arguments. This allows for always getting the current configuration variable.

*Usage**:

.. code-block:: python

   def _init_(self, **kwargs):
       self.latitude = self._Configs.get("location.latitude", instance=True)

   def someother_function(self):
       print(f"System latitude: {self.latitude.value}")

A new configuration value can be set using the set() function:

.. code-block:: python

   self.latitude.set("111")

To receive updates on configuration changes, use the "_configs_set_" hook:

*Usage**:

.. code-block:: python

   def _configs_set_(self, arguments, **kwargs):
       config = arguments["config"]  # The configuration name: location.latitude
       value = arguments["value"]  # The current value.
       instance = arguments["instance"]  # Reference to the configuration instance.

       logger.info("The configuration variable '{config}' was changed to: {value}",
                   config=instance.config,  # or just config
                   value=value,  # or instance.value


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/configuration.html>`_
"""
# Import python libraries
from copy import deepcopy
from datetime import datetime
from hashlib import sha224
import os
from shutil import copy2 as copyfile
import sys
import tomlkit as tk
import tomlkit.items as tk_items
from textwrap import wrap
from time import localtime, strftime, time
import traceback
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from random import randint
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.classes.dotdict import DotDict
from yombo.core.library_child import YomboLibraryChild
from yombo.core.exceptions import YomboInvalidArgument, YomboCritical
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
import yombo.core.settings as settings
from yombo.mixins.child_storage_accessors_mixin import ChildStorageAccessorsMixin
from yombo.utils import random_string, bytes_to_unicode
from yombo.utils.dictionaries import access_dict, access_dict_set, flatten_dict
from yombo.utils.datatypes import determine_variable_type
from yombo.utils.hookinvoke import global_invoke_all
from yombo.utils.networking import get_local_network_info

logger = get_logger("library.configuration")

CONFIG_DEFAULTS = {
    "core": {
        "enabled": "bool",
        "is_master": "bool",
    }
}

MAX_CONFIG_LENGTH: int = 1000
MAX_VALUE_LENGTH: int = 20000


class ConfigItem(YomboLibraryChild, ChildStorageAccessorsMixin):
    """
    Represents one config item.
    """
    _Entity_type: ClassVar[str] = "Config item"
    _Entity_label_attribute: ClassVar[str] = "config"

    config: str
    value: Any
    value_type: str
    created_at: int
    updated_at: int
    fetches: int = 0
    writes: int = 0
    checksum: str

    def __init__(self,
                 parent,
                 config: str,
                 value: Any,
                 created_at: Optional[int] = None,
                 updated_at: Optional[int] = None,
                 value_type: Optional[str] = None,
                 fetches: Optional[int] = None,
                 writes: Optional[int] = None,
                 checksum: Optional[str] = None,
                 ref_source: Optional[str] = None,
                 **kwargs  # Toss away any extra items.
                 ):
        self._meta = {}

        super().__init__(parent)
        self._storage_fields = self._Parent._storage_fields

        if isinstance(config, list):
            self.config = ".".join(config)
        else:
            self.config = config
        self._primary_field_id = self.config
        self.value = value
        self.ref_source = ref_source
        self.created_at = created_at if isinstance(created_at, int) else int(time())
        self.updated_at = updated_at if isinstance(updated_at, int) else int(time())
        self.value_type = value_type if isinstance(value_type, str) else determine_variable_type(value_type)
        self.fetches = fetches if isinstance(fetches, int) else 0
        self.writes = writes if isinstance(writes, int) else 0
        self.checksum = checksum if isinstance(checksum, str) else sha224(str(value).encode("utf-8")).hexdigest()

    def __str__(self) -> str:
        if isinstance(self.value_type, str):
            return self.value
        elif self.value_type is None:
            return ""
        else:
            return str(self.value)

    def set(self, value: Any, value_type: Optional[str] = None,
            ref_source: Optional = None,  # the instance that is calling this function.
            request_context: Optional[str] = None,
            authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None
            ) -> None:
        """
        Set a new new value for the config.

        :param value: Value to set.
        :param value_type: Type of value, used to help display to humans. such as string, int, float, bool...
        :param ref_source:
        :param request_context:
        :param authentication:
        :return:
        """
        self.check_authorization(authentication, "modify", required=False)

        self.value = value
        self.value_type = value_type if isinstance(value_type, str) else determine_variable_type(value)
        self.updated_at = int(time())
        self.writes += 1
        if ref_source is not None:
            self.ref_source = ref_source
        reactor.callLater(0.0001, self.broadcast, ref_source=ref_source)

    def broadcast(self, ref_source: Optional[Type["yombo.core.entity.Entity"]] = None):
        ref_source = ref_source if ref_source is not None else self
        yield global_invoke_all("_configs_set_",
                                called_by=ref_source,
                                arguments={
                                    "config": self.config,
                                    "instance": self,
                                    "value": self.value,
                                }
                                )


class Configs(YomboLibrary):
    """
    Configuration storage module for the gateway service.

    This class manages the yombo.toml file. It reads this file on startup and
    stores the configuration items into a cache. The configuration is never
    stored in the database.
    """
    _loaded_toml: ClassVar[bool] = False  # Will be set to True once config file is properly loaded.
    _storage_primary_field_name: ClassVar[str] = "config"
    _storage_attribute_name: ClassVar[str] = "configs"
    _storage_label_name: ClassVar[str] = "config"
    _storage_fields: ClassVar[list] = ["config", "value", "created_at", "updated_at", "value_type", "fetches",
                                       "writes", "checksum", "ref_source"]

    configs: ClassVar[DotDict] = DotDict({"core": {}})
    configs_dirty: ClassVar = False
    cmd_line_args: ClassVar = settings.arguments
    app_dir: ClassVar[str] = cmd_line_args["app_dir"]
    working_dir: ClassVar[str] = cmd_line_args["working_dir"]
    yombo_toml_path: ClassVar[str] = ""
    yombo_toml_loaded: ClassVar[bool] = False

    config_settings: DotDict = DotDict({  # Various settings for various configuration items.
        "core": {
            "gwhash": {
                "value_type": "string"
            },
        },
        "webinterface": {
            "cookie_session": {
                "value_type": "string"
            },
            "cookie_pin": {
                "value_type": "string"
            },
        },
        "yomboapi": {
            "login_key": {
                "value_type": "string"
            },
            "auth_session": {
                "value_type": "string"
            },
        },
        "rbac_authkeys": {
            "*": {
                "value_type": "string"
            },
        },
    })

    def __contains__(self, config_requested: str) -> bool:
        """
        Checks to if a provided configuration exists.

            >>> if "cpu.count" in self._Configs:

        :raises YomboWarning: Raised when request is malformed.
        :param config_requested: The configuration key to search for.
        :type config_requested: string
        :return: Returns true if exists, otherwise false.
        """
        try:
            self.get(config_requested)
            return True
        except:
            return False

    def __getitem__(self, config_requested: str) -> Union[bool, dict, float, list, int, set, tuple]:
        """
        Attempts to find the configuration item. Use dot notation to retrieve the item.

            >>> gwid = self._Configs["core.gwid"]

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param config_requested: The configuration key to search for.
        :return: dict containing: "id", "cmd", "device"
        :rtype: dict
        """
        return self.get(config_requested).value

    def __setitem__(self, config_requested: str,
                    value: Union[bool, dict, float, list, int]) -> None:
        """
        Set a configuration item.
        """
        self.set(config_requested, value)

    def __delitem__(self, config_requested: str) -> None:
        """
        Delete a configuration item.
        """
        self.delete(config_requested)

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Reads the yombo.toml file and stores the settings in memory for fast access.
        """
        self.pid = os.getpid()
        self.exit_config_file = None  # Holds a complete configuration file to save when exiting.
        self.yombo_toml_path = f"{self._working_dir}/yombo.toml"
        self.yombo_toml_meta_path = f"{self._working_dir}/etc/yombo_meta.toml"
        self.save_loop = LoopingCall(self.save, force_save=False, display_extra_warning=True)
        self.save_loop.start(randint(12600, 14400), False)  # every 3.5-4 hours

        self.setup_defaults()
        has_cfg_file = self.check_yombo_toml_file()
        if has_cfg_file is False:
            logger.warn("yombo.toml file not found, creating a new one.")
            yield self.save(force_save=True)
        try:
            yield self.import_toml_file()
        except TypeError as e:
            logger.error("{e}", e=e)
            logger.error("Check validate the yombo.toml file at: {yombo_toml_path}",
                         yombo_toml_path=self.yombo_toml_path)
            logger.error("Validate the syntax at the line/position at the line noted above.")
            raise YomboCritical(str(e))
        else:
            self.yombo_toml_loaded = True
            if self.get("core.gwid") == "local":
                self._Loader.operating_mode = "config"
            else:
                self._Loader.operating_mode = "run"
        yield self.update_network_details()
        self._loaded_toml = True

    def _started_(self, **kwargs) -> None:
        self.save(force_save=True, display_extra_warning=True)

    def _stop_(self, **kwargs) -> None:
        if self.save_loop is not None and self.save_loop.running:
            self.save_loop.stop()

    @inlineCallbacks
    def _unload_(self, **kwargs):
        """
        Save the items in the config table to yombo.toml.  This allows
        the user to see the current configuration and make any changes.
        """
        if self._loaded_toml is True:
            yield self.save(force_save=True)

    def check_yombo_toml_file(self) -> None:
        """
        Checks the yombo.toml file, if it's missing, or seems invalid it attempts to restore the file from a backup.

        :return:
        """
        restore_toml = settings.arguments["restoretoml"]
        if os.path.exists(self.yombo_toml_path):
            if os.path.isfile(self.yombo_toml_path) is False:
                try:
                    os.remove(self.yombo_toml_path)
                except Exception as e:
                    raise IOError(f"'yombo.toml' file exists, but it's not a file and cannot be deleted: {e}")
                if restore_toml:
                    return self.restore_backup_yombo_toml()
            else:
                if os.path.getsize(self.yombo_toml_path) < 5:
                    print("yombo.toml appears to be corrupt (too small), attempting to restore from backup.")
                    if restore_toml:
                        return self.restore_backup_yombo_toml()
                return True
        elif restore_toml:
            return self.restore_backup_yombo_toml()

    def restore_backup_yombo_toml(self) -> bool:
        """
        Restores the last backup if needed/requested.

        :param arguments:
        :return: Return True on success, else False if nothing happened.
        """
        backup_yombo_toml_path = f"{self._working_dir}/bak/yombo_toml"
        dated_files = [(os.path.getmtime(f"{backup_yombo_toml_path}/{fn}"), os.path.basename(fn))
                       for fn in os.listdir(backup_yombo_toml_path)]
        dated_files.sort()
        dated_files.reverse()
        logger.warn("Attempting to restore yombo.toml file from backup.")
        if len(dated_files) > 0:
            for i in range(0, len(dated_files)):
                the_restore_file = f"{backup_yombo_toml_path}/{dated_files[i][1]}"
                if os.path.getsize(the_restore_file) > 100:
                    copyfile(the_restore_file, self.yombo_toml_path)
                    logger.warn(f" - yombo.toml file restored from previous backup: {the_restore_file}")
                    return True
        return False

    @inlineCallbacks
    def import_toml_file(self) -> None:
        """
        Reads the configuration file, and it's meta, and sets the self.configs dictionary.
        """
        yombo_toml, yombo_toml_meta = yield self.read_yombo_toml()

        def get_toml_value(input):
            """Converts from tomlkit class to python class."""
            if isinstance(input, bool) or isinstance(input, tk_items.Bool):
                return bool(input)
            if isinstance(input, tk_items.AoT):
                return input.value
            if isinstance(input, tk_items.Array):
                return input._value
            if isinstance(input, tk_items.DateTime):
                return input._new()
            if isinstance(input, tk_items.Date):
                return input.as_string()
            if isinstance(input, tk_items.Float):
                return float(input.as_string())
            if isinstance(input, tk_items.Integer):
                return int(input.as_string())
            if isinstance(input, tk_items.Null):
                return None
            if isinstance(input, tk_items.String):
                return str(input)
            if isinstance(input, tk_items.InlineTable):
                return input._value
            if isinstance(input, tk_items.Table):
                return input._value
            if isinstance(input, tk_items.Time):
                return input.as_string()

        def setup_configs(current_path, data):
            if isinstance(data, dict):  # Process a dictionary
                for config, items in data.items():
                    temp_path = deepcopy(current_path)
                    temp_path.append(config)
                    setup_configs(temp_path, items)
            else:  # Process a single item
                try:
                    temp_path = deepcopy(current_path[:-1])
                    temp_path.append(f"{current_path[-1]}")
                    meta = access_dict(temp_path, yombo_toml_meta)
                except:
                    meta = {}
                config_path = ".".join(current_path)
                logger.debug("converting to final_data: '{value}' - type: {value_type}",
                             value=get_toml_value(data), value_type=type(get_toml_value(data)))
                self.configs[current_path] = ConfigItem(self, config=config_path, value=get_toml_value(data), **meta)

        try:
            setup_configs([], yombo_toml)
        except Exception as e:
            logger.warn("Caught exception while processing toml config file: {e}", e=e)
        logger.debug("configs file: {configs}", configs=self.configs)
        logger.debug("done parsing yombo.toml and yombo_meta.toml")

    @inlineCallbacks
    def read_yombo_toml(self) -> Tuple[Union["tomlkit.toml_document.TOMLDocument", dict],
                                       Union["tomlkit.toml_document.TOMLDocument", dict]]:
        """
        Called to actually read the yombo.toml and it's matching meta file. Makes a backup copy before it's read.

        :return:
        """
        try:
            toml_contents = yield self._Files.read(self.yombo_toml_path)
            yombo_toml = tk.parse(toml_contents)
        except Exception as e:
            raise TypeError(f"Problem reading yombo.toml file: {e}")

        yield self.backup_toml_file()

        yombo_toml_meta = {}
        try:
            toml_contents = yield self._Files.read(self.yombo_toml_meta_path)
            yombo_toml_meta = tk.parse(toml_contents)
        except Exception as e:
            logger.info(f"Error loading yombo_meta.toml: {e}")
        return yombo_toml, yombo_toml_meta

    @inlineCallbacks
    def backup_toml_file(self) -> None:
        """Do a quick backup of the toml file."""
        yield self._Files.copy_file(
            self.yombo_toml_path,
            f'{self._working_dir}/bak/yombo_toml/{strftime("%Y-%m-%d_%H:%M:%S", localtime())}_yombo.toml')

    def setup_defaults(self) -> None:
        """
        Setups some basic configurations. Very helpful for new gateways or reinstalls until a recovered
        yombo.toml can be uploaded/installed.
        """
        if self.get("core.first_run", None) is None:
            self.set("core.first_run", True)

        # Allows gateway control commands from yombo servers.
        self.get("security.amqp.allow_system_control", True)
        # Allows remove device control from yombo servers. If this is disabled, commands cannot be relayed if remove
        # devices cannot directly access the gateway.
        self.get("security.amqp.allow_device_control", True)
        # Send device states to yombo servers. Used by user's remote devices to get device states.
        self.get("security.amqp.send_device_states", True)
        # Send private statistics. This doesn't provice much details, mostly usage details.
        self.get("security.amqp.send_private_stats", True)
        # Send public statistics. Nothing relating to the user's activities and devices.
        self.get("security.amqp.send_anon_stats", True)

        self.get("core.gwid", "local")
        self.get("core.is_master", True)
        self.get("core.master_gateway_id", "local")
        self.get("core.rand_seed", random_string(length=80))
        self.get("core.system_user_prefix", "gw")

        if self.get("database.type", "sqlite") == "sqlite":
            self.get("database.path", f"{self._working_dir}/etc/yombo.sqlite3")

        # set system defaults. Reasons: 1) All in one place. 2) Somes values are needed before respective libraries
        # are loaded.
        self.get("mqttyombo.enabled", True)
        self.get("mosquitto.enabled", True)
        self.get("mosquitto.max_connections", 1000)
        self.get("mosquitto.timeout_disconnect_delay", 2)
        self.get("mosquitto.server_listen_ip", "*")
        self.get("mosquitto.server_listen_port", 1883)
        self.get("mosquitto.server_listen_port_ss_ssl", 1884)
        self.get("mosquitto.server_listen_port_le_ssl", 1885)
        self.get("mosquitto.server_listen_port_websockets", 8081)
        self.get("mosquitto.server_listen_port_websockets_ss_ssl", 8444)
        self.get("mosquitto.server_listen_port_websockets_le_ssl", 8445)
        self.get("mosquitto.server_allow_anonymous", False)
        self.get("misc.temperature_display", "f")
        self.get("misc.length_display", "imperial")  # will we ever get to metric?

        self.get("webinterface.nonsecure_port", 8080)
        self.get("webinterface.secure_port", 8443)

    @inlineCallbacks
    def update_network_details(self) -> None:
        """
        Updates various networking details such as ip address and location information based
        of various sources.

        :return:
        """
        current_time = int(time())
        # Ask external services what they know about us.
        # detected_location states are based off this and is set in the locations library.
        # times uses this
        self.detected_location_info = self.get("detected_location.info", None)
        if self.detected_location_info is None or \
                self.get("detected_location.time", 0) < current_time - 3600:
            self.detected_location_info = yield self._Locations.detect_location_info()

            self.set("detected_location.info", self._Tools.data_pickle(self.detected_location_info,
                                                                       content_type="msgpack_base64",
                                                                       local=True))
            self.set("detected_location.time", current_time)
        else:
            self.detected_location_info = self._Tools.data_unpickle(self.detected_location_info,
                                                                    content_type="msgpack_base64")

        self.set("networking.externalipaddress.v4", self.detected_location_info["ipv4"])
        self.set("networking.externalipaddress.v6", self.detected_location_info["ipv6"])

        if self.get("networking.localipaddress.v4", False) is False or \
                self.get("networking.localipaddress.time", False) is False or \
                self.get("networking.localipaddress.time", 0) < (int(time()) - 300):
            address_info = get_local_network_info()
            self.set("networking.localipaddress.v4", address_info["ipv4"]["address"])
            self.set("networking.localipaddress.netmask_v4", address_info["ipv4"]["netmask"])
            self.set("networking.localipaddress.cidr_v4", address_info["ipv4"]["cidr"])
            self.set("networking.localipaddress.network_v4", address_info["ipv4"]["network"])
            self.set("networking.localipaddress.v6", address_info["ipv6"]["address"])
            self.set("networking.localipaddress.netmask_v6", address_info["ipv6"]["netmask"])
            # self.set("networking.localipaddress.cidr_v6", address_info["ipv6"]["cidr"])
            # self.set("networking.localipaddress.network_v6", address_info["ipv6"]["network"])
            self.set("networking.localipaddress.time", int(time()))

    def Configuration_i18n_atoms(self, **kwargs) -> List[Dict[str, any]]:
        return [
            {"configuration.yombo_toml.found": {
                "en": "True if yombo.toml was found on startup.",
            },
            }
        ]

    @inlineCallbacks
    def save(self, force_save: Optional[bool] = None, display_extra_warning: Optional[bool] = None) -> None:
        """
        Save the configuration configs to the INI file.
        """
        try:
            # If for some reason startup fails, we won't get _() defined. We just try to print _() and test...
            logger.debug("saving config file...")

            if self.exit_config_file is not None:
                yield self._Files.save(self.yombo_toml_path, self.exit_config_file)
                self.exit_config_file = None

            elif self.configs_dirty is True or force_save is True:
                ini_contents, meta_contents = self.generate_yombo_toml(display_extra_warning)
                yield self._Files.save(self.yombo_toml_path, ini_contents)
                yield self._Files.save(self.yombo_toml_meta_path, meta_contents)

        except Exception as e:
            logger.warn("Caught master error in saving ini file: {e}", e=e)
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")

        self.configs_dirty = False

        file_path = f"{self._working_dir}/bak/yombo_toml/"

        backup_files = os.listdir(os.path.dirname(file_path))
        if len(backup_files) > 5:
            for file in backup_files:  # remove old yombo.toml backup files.
                fullpath = os.path.join(file_path, file)  # turns "file1.txt" into "/path/to/file1.txt"
                timestamp = os.stat(fullpath).st_ctime  # get timestamp of file
                createtime = datetime.fromtimestamp(timestamp)
                now = datetime.now()
                delta = now - createtime
                if delta.days > 30:
                    os.remove(fullpath)

    def generate_yombo_toml(self, display_extra_warning: Optional[bool] = None) -> List[str]:
        """
        Generates the output for yombo.toml in TOML format - like INI, but better.

        If display_extra_warning is True, will display an even more nasty message to not edit this file while its
        running.

        :param display_extra_warning:
        :return:
        """

        def wrap_comment_lines(text, trailing_comment: Optional[bool] = None, contents: Optional = None):
            """ Creates a comment that wraps long lines. """
            output = wrap(text, 75, break_long_words=False)
            if contents is None:
                contents = ini_contents

            for line in output:
                if trailing_comment is True:
                    contents.add(tk.comment(f"{line: <76} #"))
                else:
                    contents.add(tk.comment(f"{line}"))

        ini_contents = tk.document()
        meta_contents = tk.document()
        meta_contents.add(
            tk.comment("################################################################################"))
        meta_contents.add(tk.comment("  Stores additional information about yombo.toml, non-essential."))
        meta_contents.add(
            tk.comment("################################################################################"))
        meta_contents.add(tk.nl())

        ini_contents.add(tk.comment(" "))
        ini_contents.add(tk.comment(_("lib.configs.yombo_toml.about")))
        ini_contents.add(tk.comment(" "))
        if display_extra_warning is True:
            ini_contents.add(tk.comment(" "))
            ini_contents.add(
                tk.comment("###############################################################################"))
            ini_contents.add(tk.comment(f'{_("lib.configs.yombo_toml.warning"):^76}'))
            ini_contents.add(
                tk.comment("###############################################################################"))
            ini_contents.add(tk.comment(_("lib.configs.yombo_toml.still_running")))
            ini_contents.add(tk.comment(_("lib.configs.yombo_toml.still_running_pid", number=str(self.pid))))
            ini_contents.add(
                tk.comment("###############################################################################"))

        else:
            wrap_comment_lines(_("lib.configs.yombo_toml.dont_edit"), False)
        ini_contents.add(tk.comment(" "))
        ini_contents.add(tk.comment(" "))

        def add_config_item(section, current_path, data):
            """ Recursive function to output config contents. """
            config_data = data.to_dict(include_meta=False)

            item_msgid = f'lib.configs.item.{".".join(current_path)}'
            item_description = _(item_msgid)

            if item_msgid != item_description:
                wrap_comment_lines(item_description, contents=section)
            section.add(current_path[-1], config_data["value"])
            if item_msgid != item_description:
                section.add(tk.nl())

            meta_data = {key: config_data[key] for key in config_data.keys() - {'value', 'config'}}
            access_dict_set(config_data["config"], meta_contents, meta_data)

        def add_dictionary(current_path, data):
            """ Recursive function to output config contents. """
            section = tk.table()
            if len(current_path):
                ini_contents.add(tk.nl())
                ini_contents.add(tk.nl())
                ini_contents.add(
                    tk.comment("##############################################################################"))
                ini_contents.add(tk.comment(f'{".".join(current_path): ^76} #'))
                ini_contents.add(tk.comment(f"{'': <76} #"))
                wrap_comment_lines(_(f'lib.configs.section.{".".join(current_path)}'), True, contents=ini_contents)
                ini_contents.add(
                    tk.comment("##############################################################################"))

            for config, items in data.items():
                temp_path = deepcopy(current_path)
                temp_path.append(config)
                if isinstance(items, ConfigItem):
                    if items.value is None:
                        continue
                    add_config_item(section, temp_path, items)
                else:
                    add_dictionary(temp_path, items)
            if len(current_path):
                ini_contents[".".join(current_path)] = section

        add_dictionary([], self.configs)
        return tk.dumps(ini_contents), tk.dumps(meta_contents)

    def get(self,
            config: Union[list, str],
            default: Any = "7vce#hvjGW%w$~bA6jYv[P:*.kv6mAg934+HQhPpbDFJF2Nw9rU+saNvpVL2",
            create: Optional[bool] = None,
            instance: Optional[bool] = None,
            ignore_case: Optional[bool] = None,
            ref_source: Optional = None,
            **kwargs) -> Any:
        """
        Read value of configuration option, return None if it don't exist or
        default if defined.  Tries to type cast with int first before
        returning a string.

        If you always want the current value of a configuration item, use :py:meth:`get2() <get2>`.

        Section and option will be converted to lowercase, rendering the set/get
        function case insenstive.

        **Usage**:

        .. code-block:: python

           gateway_id = self._Config.get("core.gwid", "Default Value")

        :raises YomboInvalidArgument: When an argument is invalid or illegal.
        :raises KeyError: When the requested section and option are not found.
        :param config: The configuration section to use.
        :param default: If set and nothing found, this will be returned. Otherwise, will raise KeyError.
        :param create: If the config value is missing, and a default exists, it'll be created.
        :param instance: If true, returns the ConfigItem instance, default is to just return the value.
        :param ignore_case: If true, the config string will be set to lower case for case insensitive searches.
        :param ref_source: If the value will be set due to a default value, the source should be supplied - reference
            to the instance calling this function.
        :return: The configuration value requested by config argument.
        """

        def return_value(config_item):
            if instance is True:
                return config_item
            return config_item.value

        if len(config) > MAX_CONFIG_LENGTH:
            raise YomboInvalidArgument(f"config path cannot be more than {MAX_CONFIG_LENGTH:d} chars")

        if ignore_case in (None, True):
            config = config.lower()

        if config.endswith("*"):  # Get all configs.
            if config == "*":
                flattened = flatten_dict(self.configs)
            else:
                flattened = flatten_dict(self.configs[config[:-2]])  # get the config, removing the .*
            if instance is True:
                return flattened
            results = {}
            for key, item in flattened.items():
                results[key] = item.value
            return results

        if config in self.configs:  # Get all options for a provided config name.
            config_item = self.configs[config]
            # print(f"config_item: {config_item.__dict__}")
            config_item.fetches += 1
            return return_value(config_item)

        # it"s not here, so, if there is a default, lets save that for future reference and return it... English much?
        if default != "7vce#hvjGW%w$~bA6jYv[P:*.kv6mAg934+HQhPpbDFJF2Nw9rU+saNvpVL2":
            if create in (True, None) or instance is True:
                self.set(config, default, ref_source=ref_source)
                config_item = self.configs[config]
                config_item.fetches += 1
                if instance is True:
                    return config_item
                return config_item.value
            else:
                return default
        else:
            raise KeyError(f"Config item not found, no default provided. {default}")

    def set(self, config: str, value: Any, value_type: Optional[str] = None, ignore_case: Optional[bool] = None,
            ref_source: Optional = None, **kwargs) -> ConfigItem:
        """
        Set value of configuration option for a given config.  The option length
        **cannot exceed 1000 characters**.  The value cannot exceed 5000 bytes.

        Section and option will be converted to lowercase, rending the set/get function case insenstive.

        **Usage**:

        .. code-block:: python

           self._Config.set("core.something", "New Value")

        :raises YomboInvalidArgument: When an argument is invalid or illegal.
        :raises KeyError: When the requested config is not found.
        :param config: The configuration to use.
        :param value: What to return if no result is found, default = None.
        :param value_type:
        :param ignore_case:
        :param ref_source:
        """
        if config.endswith("*"):
            raise YomboInvalidArgument("Config item label cannot end with '*'.")
        if len(config) > MAX_CONFIG_LENGTH:
            raise YomboInvalidArgument(f"section cannot be more than {MAX_CONFIG_LENGTH:d} chars")
        # Can't set value!
        if config.startswith("security") and self._Loader.operating_mode == "run":
            raise YomboInvalidArgument("Not allowed to set value: cannot edit security items.")

        value = bytes_to_unicode(value)
        if isinstance(value, str):
            if len(value) > MAX_VALUE_LENGTH:
                raise YomboInvalidArgument(f"value cannot be more than {MAX_VALUE_LENGTH} chars")

        if ignore_case is not True:
            config = config.lower()

        # If the gateway ID changes.
        if config == "core.gwid" and config in self.configs:
            self._Atoms.change_gateway_id(self.configs[config].value, value)
            self._States.change_gateway_id(self.configs[config].value, value)

        if config in self.configs:
            config_item = self.configs[config]
            if self.configs[config].value == value:
                return value
            config_item.set(value, value_type=value_type)
        else:
            self.configs[config] = ConfigItem(self, config=config, value=value, value_type=value_type,
                                              ref_source=ref_source)

        self.configs_dirty = True
        return self.configs[config]

    def get_meta(self, section: str, option: str, meta_type="time"):
        try:
            return self.configs_meta[section, option][meta_type]
        except:
            return None

    def delete(self, config: str) -> None:
        """
        Delete a config value from configs (yombo.toml).

        :param config: The configuration section to use.
        """
        del self.configs[config]

    def sorted(self, key: Optional[str] = None) -> dict:
        """
        Returns a dict, sorted by key.  If key is not set, then default is "config".

        :param key: Attribute contained in a configuration to sort by.
        """
        if key is None:
            key = "config"
        return dict(sorted(iter(self.configs.items()), key=lambda i: getattr(i[1], key)))

    def to_dict_all(self) -> dict:
        """
        Returns all items as a dictionary.

        :return:
        """
        results = {}
        storage = self.get("*", instance=True)
        for item_id, item in storage.items():
            results[item_id] = item.to_dict(include_meta=False)
        return results

    def get_all(self, filters: Optional[dict] = None, **kwargs) -> list:
        """
        Returns all items as a list. Typically used to output to API.

        :return:
        """
        def check_filter(input):
            print("check_filter....")
            for key, value in filters.items():
                if key in input:
                    if input[key] == value:
                        return True
            return False

        results = []
        storage = self.get("*", instance=True)
        for item_id, item in storage.items():
            if filters is not None:
                data = item.to_dict(include_meta=False)
                if check_filter(data) is False:
                    continue
            results.append(item)
        return results
