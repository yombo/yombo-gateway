# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * End user documentation: `Configuration @ User Documentation <https://yombo.net/docs/gateway/web_interface/basic_settings>`_
  * For library documentation, see: `Cache @ Library Documentation <https://yombo.net/docs/libraries/configuration>`_

Handles loading, storing, updating, and saving gateway configuration items.

If you wish to store persistent data for your module, use the
:py:mod:`SQLDict Library <yombo.lib.sqldict>`.

*Usage**:

.. code-block:: python

   latitude = self._Configs.get("location", "latitude", "0", True)  # also can accept default and if a default value should be saved.
   latitude = self._Configs.get("location", "latitude", "0", False)  # example of default and no save if default is used.
   self._Configs.set("location", "latitude", 100)  # Save a new latitude location.

A function can also be returned by calling get2(). This allows the a library or module to always access the
latest version of a configuration value.  The function can also accept a named parameter of "set" to set a
new value:

*Usage**:

.. code-block:: python

   latitude = self._Configs.get2("location", "latitude")  # also can accept default and if a default value should be saved.
   latitude = self._Configs.get2("location", "latitude", "0", False)  # example of default and no save if default is used.
   print("Latitude: %s" % latitude())  # print
   latitude(set=100)  # Save a new latitude location.

There are also times when you a module or library should be notified of a change. They
can simply implement the hook: _configuration_set_:

*Usage**:

.. code-block:: python

   def _configuration_set_(self, **kwargs):
       section = kwargs["section"]
       option = kwargs["option"]
       value = kwargs["value"]

       if section == "core":
           if option == "label":
               logger.info("the system label was changed to: {label}", label=value)


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/configuration.html>`_
"""
# Import python libraries
from base64 import b64encode, b64decode
import configparser
from datetime import datetime
from functools import partial
from hashlib import sha224
import msgpack
import os
from shutil import copy2 as copyfile
import sys
import textwrap
from time import time
import traceback

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from random import randint
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboInvalidArgument
from yombo.utils.networking import get_local_network_info
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
import yombo.core.settings as settings
from yombo.utils import dict_merge, global_invoke_all, save_file, data_pickle, data_unpickle
from yombo.utils.location import detect_location_info

logger = get_logger("library.configuration")


class Configuration(YomboLibrary):
    """
    Configuration storage module for the gateway service.

    This class manages the yombo.ini file. It reads this file on startup and
    stores the configuration items into a cache. The configuration is never
    stored in the database.
    """
    MAX_SECTION_LENGTH = 100
    MAX_OPTION_LENGTH = 100
    MAX_VALUE_LENGTH = 10000

    # Yombo constants. Used for versioning and misc tracking.

    configs = {"core": {}}  # Contains all the config items
    configs_details = {
        "core": {
            "gwhash": {
                "encrypt": True
            },
            "api_auth": {
                "encrypt": True
            },
        },
        "webinterface": {
            "cookie_session": {
                "encrypt": True
            },
            "cookie_pin": {
                "encrypt": True
            },
        },
        "yomboapi": {
            "login_key": {
                "encrypt": True
            },
            "auth_session": {
                "encrypt": True
            },
        },
        "rbac_authkeys": {
            "*": {
                "encrypt": True
            },
        },
    }  # Collected details from libs and modules about configurations

    def __contains__(self, configuration_requested):
        """
        Checks to if a provided configuration exists.

            >>> if "cpu.count" in self._Configs:

        :raises YomboWarning: Raised when request is malformed.
        :param configuration_requested: The configuration key to search for.
        :type configuration_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        if configuration_requested in self._Configs:
            return True
        else:
            return False

    def __getitem__(self, configuration_requested):
        """
        Attempts to find the device requested using a couple of methods. Use a double hashtag (##)
        to seperate the configuration section from the option.

            >>> gwid = self._Configs["core##gwid"]

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param configuration_requested: The configuration key to search for.
        :type configuration_requested: string
        :return: dict containing: "id", "cmd", "device"
        :rtype: dict
        """
        requested = configuration_requested.split("##")
        return self.get(requested[0], requested[1])

    def __setitem__(self, configuration_requested, value):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, configuration_requested):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo configuration library"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Open the yombo.ini file for reading.

        Import the configuration items into the database, also prime the configs for reading.
        """
        self.exit_config_file = None  # Holds a complete configuration file to save when exiting.
        self.cache_dirty = False
        self.configs = {}  # Holds actual config data
        self.cfg_loaded = False
        self.yombo_ini_last_modified = 0
        self.working_dir = settings.arguments["working_dir"]
        ini_norestore = settings.arguments["norestoreini"]
        self.yombo_ini_path = f"{self.working_dir}/yombo.ini"
        if os.path.exists(self.yombo_ini_path):
            if os.path.isfile(self.yombo_ini_path) is False:
                try:
                    os.remove(self.yombo_ini_path)
                except Exception as e:
                    logger.error("'yombo.ini' file exists, but it's not a file and it can't be deleted!")
                    reactor.stop()
                    return
                if ini_norestore:
                    self.restore_backup_yombi_ini()
            else:
                if os.path.getsize(self.yombo_ini_path) < 2:
                    logger.warn("yombo.ini appears corrupt, attempting to restore from backup.")
                    if ini_norestore:
                        self.restore_backup_yombi_ini()
        else:
            if ini_norestore:
                self.restore_backup_yombi_ini()

        self.loading_yombo_ini = True
        if settings.yombo_ini is False:
            self._Loader.operating_mode = "first_run"
        else:
            for section, options in settings.yombo_ini.items():
                for option, value in options.items():
                    try:
                        value = yield self._GPG.decrypt(value)
                    except:
                        pass
                    self.set(section, option, value, ignore_case=True)

        logger.debug("done parsing yombo.ini. Now about to parse yombo.ini.info.")
        try:
            config_parser = configparser.ConfigParser()
            config_parser.read(f"{self.working_dir}/etc/yombo.ini.info")
            logger.debug("yombo.ini.info file read into memory.")
            for section in config_parser.sections():
                if section not in self.configs:
                    continue
                for option in config_parser.options(section):
                    if option not in self.configs[section]:
                        continue
                    values = msgpack.loads(b64decode(config_parser.get(section, option)))
                    self.configs[section][option] = dict_merge(self.configs[section][option], values)
        except IOError as e:
            logger.warn("CAUGHT IOError!!!!!!!!!!!!!!!!!!  In reading meta: {error}", error=e)
        except configparser.NoSectionError:
            logger.warn("CAUGHT ConfigParser.NoSectionError!!!!  IN saving. ")

        logger.debug("done parsing yombo.ini.info")

        #setup some defaults if we are new....
        self.get("core", "gwid", "local")
        self.get("core", "gwuuid", None)

        # Perform DB cleanup activites based on local section.
        if self.get("local", "deletedelayedmessages", False, False) is True:
            self._Libraries["localdb"].delete("sqldict", ["module = ?", "yombo.gateway.lib.messages"])
            self.set("local", "deletedelayedmessages", False)

        if self.get("local", "deletedevicehistory", False, False) is True:
            self._Libraries["localdb"].truncate("devicestatus")
            self.set("local", "deletedevicehistory", False)

        current_time = int(time())
        # Ask external services what they know about us.
        # detected_location states are based off this and is set in the locations library.
        # times uses this
        self.detected_location_info = self.get("core", "locationinfo", None, False)
        if self.detected_location_info is None or \
                self.get("core", "locationinfotime", 0, False) < current_time - 3600:
            self.detected_location_info = yield detect_location_info()
            self.set("core", "locationinfo", data_pickle(self.detected_location_info, encoder="msgpack_base64", local=True))
            self.set("core", "locationinfotime", current_time)
        else:
            self.detected_location_info = data_unpickle(self.detected_location_info, encoder="msgpack_base64")
        self.set("core", "externalipaddress_v4", self.detected_location_info["ip"])

        if self.get("core", "localipaddress_v4", False, False) is False or \
                self.get("core", "localipaddresstime", False, False) is False:
            address_info = get_local_network_info()
            self.set("core", "localipaddress_v4", address_info["ipv4"]["address"])
            self.set("core", "localipaddress_netmask_v4", address_info["ipv4"]["netmask"])
            self.set("core", "localipaddress_cidr_v4", address_info["ipv4"]["cidr"])
            self.set("core", "localipaddress_network_v4", address_info["ipv4"]["network"])
            self.set("core", "localipaddress_v6", address_info["ipv6"]["address"])
            self.set("core", "localipaddress_netmask_v6", address_info["ipv6"]["netmask"])
            # self.set("core", "localipaddress_cidr_v6", address_info["ipv6"]["cidr"])
            # self.set("core", "localipaddress_network_v6", address_info["ipv6"]["network"])
            self.set("core", "localipaddresstime", int(time()))
        else:
            if int(self.configs["core"]["localipaddresstime"]["value"]) < (int(time()) - 180):
                address_info = get_local_network_info()
                self.set("core", "localipaddress_v4", address_info["ipv4"]["address"])
                self.set("core", "localipaddress_netmask_v4", address_info["ipv4"]["netmask"])
                self.set("core", "localipaddress_cidr_v4", address_info["ipv4"]["cidr"])
                self.set("core", "localipaddress_network_v4", address_info["ipv4"]["network"])
                self.set("core", "localipaddress_v6", address_info["ipv6"]["address"])
                self.set("core", "localipaddress_netmask_v6", address_info["ipv6"]["netmask"])
                # self.set("core", "localipaddress_cidr_v6", address_info["ipv6"]["cidr"])
                # self.set("core", "localipaddress_network_v6", address_info["ipv6"]["network"])
                self.set("core", "localipaddresstime", int(time()))

        self.save_loop = LoopingCall(self.save)
        self.save_loop.start(randint(12600, 14400), False)  # every 3.5-4 hours

        if self.get("core", "first_run", None, False) is None:
            self.set("core", "first_run", True)
        self.loading_yombo_ini = False

        # set system defaults. Reasons: 1) All in one place. 2) Somes values are needed before respective libraries
        # are loaded.
        self._Configs.get("mqtt", "client_enabled", True)
        self._Configs.get("mqtt", "server_enabled", True)
        self._Configs.get("mqtt", "server_max_connections", 1000)
        self._Configs.get("mqtt", "server_timeout_disconnect_delay", 2)
        self._Configs.get("mqtt", "server_listen_ip", "*")
        self._Configs.get("mqtt", "server_listen_port", 1883)
        self._Configs.get("mqtt", "server_listen_port_ss_ssl", 1884)
        self._Configs.get("mqtt", "server_listen_port_le_ssl", 1885)
        self._Configs.get("mqtt", "server_listen_port_websockets", 8081)
        self._Configs.get("mqtt", "server_listen_port_websockets_ss_ssl", 8444)
        self._Configs.get("mqtt", "server_listen_port_websockets_le_ssl", 8445)
        self._Configs.get("mqtt", "server_allow_anonymous", False)
        self._Configs.get("misc", "temperature_display", "f")
        self._Configs.get("misc", "length_display",  "imperial")  # will we ever get to metric?
        self.cfg_loaded = True

        # We define commonly used items here, so a single pointer to the function be use re-used
        self.gateway_id = self._Configs.get2("core", "gwid", "local", False)
        self.is_master = self._Configs.get2("core", "is_master", True, False)
        self.master_gateway_id = self._Configs.get2("core", "master_gateway_id", "local", False)


    # def _load_(self, **kwargs):

    def _started_(self, **kwargs):
        self.save(True, display_extra_warning=True)

    def _stop_(self, **kwargs):
        if self.save_loop is not None and self.save_loop.running:
            self.save_loop.stop()

        # if self.periodic_load_yombo_ini is not None and self.periodic_load_yombo_ini.running:
        #     self.periodic_load_yombo_ini.stop()

    @inlineCallbacks
    def _unload_(self, **kwargs):
        """
        Save the items in the config table to yombo.ini.  This allows
        the user to see the current configuration and make any changes.
        """
        yield self.save(True)



    def Configuration_i18n_atoms(self, **kwargs):
       return [
           {"configuration.yombo_ini.found": {
               "en": "True if yombo.ini was found on startup.",
               },
           },
       ]

    def restore_backup_yombi_ini(self):
        path = f"{self.working_dir}/bak/yombo_ini/"

        dated_files = [(os.path.getmtime(f"{path}/{fn}"), os.path.basename(fn))
                       for fn in os.listdir(path)]
        dated_files.sort()
        dated_files.reverse()
        if len(dated_files) > 0:
            for i in range(0, len(dated_files)):
                the_file = f"{path}/{dated_files[i][1]}"
                if os.path.getsize(the_file) > 100:
                    copyfile(the_file, self.yombo_ini_path)
                    logger.warn("yombo.ini file restored from previous backup.")
                    return True
        return False

    @inlineCallbacks
    def save(self, force_save=False, display_extra_warning=False):
        """
        Save the configuration configs to the INI file.

        #Todo: convert to fdesc for non-blocking. Need example of usage.
        """
        try:
            # If for some reason startup fails, we won't get _() defined. We just try to print _() and test...
            logger.debug("saving config file...")

            if self.exit_config_file is not None:
                yield save_file(self.yombo_ini_path, self.exit_config_file)

            elif self.configs_dirty is True or force_save is True:
                contents = yield self.generate_yombo_ini(display_extra_warning)
                yield save_file(self.yombo_ini_path, contents)

            Config = configparser.ConfigParser()
            for section, options in self.configs.items():
                Config.add_section(section)
                for item, data in options.items():
                    temp = self.configs[section][item].copy()
                    if "details" in temp:
                        del temp["details"]
                    if "value" in temp:
                        del temp["value"]
                    Config.set(section, item, b64encode(msgpack.dumps(temp)).decode())
                if len(Config.options(section)) == 0:  # Don"t save empty sections.
                    Config.remove_section(section)

            config_file = open(f"{self.working_dir}/etc/yombo.ini.info", "w")
            config_file.write("#\n")
            config_file.write("# This file stores meta information about yombo.ini. Do not edit manually!\n")
            config_file.write("#\n")
            Config.write(config_file)
            config_file.close()

        except Exception as E:
            logger.warn("Caught master error in saving ini file: {e}", e=E)
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")

        self.configs_dirty = False

        file_path = f"{self.working_dir}/bak/yombo_ini/"

        backup_files = os.listdir(os.path.dirname(file_path))
        if len(backup_files) > 5:
            for file in backup_files: # remove old yombo.ini backup files.
                fullpath = os.path.join(file_path, file)    # turns "file1.txt" into "/path/to/file1.txt"
                timestamp = os.stat(fullpath).st_ctime # get timestamp of file
                createtime = datetime.fromtimestamp(timestamp)
                now = datetime.now()
                delta = now - createtime
                if delta.days > 30:
                    os.remove(fullpath)

    @inlineCallbacks
    def generate_yombo_ini(self, display_extra_warning=False):
        """
        Generates the output for yombo.ini. If display_extra_warning is True, will display an even
        more nasty message to not edit this file while its running.

        :param shutdown:
        :return:
        """
        contents = ""
        contents += "#\n# " + _("lib::configs::yombo.ini::about") + "\n"
        if display_extra_warning is True:
            contents += "#\n#####################################################################################\n"
            contents += "#  WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING \n"
            contents += "#####################################################################################\n"
            contents += "# " + _("lib::configs::yombo.ini::still_running") + "\n"
            contents += "# " + _("lib::configs::yombo.ini::still_running_pid", number=str(self._Atoms["pid"])) + "\n"

            contents += "#####################################################################################\n#\n#\n"
        contents += "# " + _("lib::configs::yombo.ini::dont_edit") + "\n# \n"

        # first parse sections to make sure each section has a value!
        configs = {}
        for section, options in self.configs.items():
            if section not in configs:
                configs[section] = {}
            for item, data in options.items():
                if "value" not in data:  # incase it's documented, but not used. Usually bad doco.
                    continue
                configs[section][item] = data['value']

        #now we save the sections and the items...with i18n comments!
        for section, options in configs.items():
            contents += "\n################################################################################\n"
            contents += f"## {section: ^74} ##\n"

            i18n_label = _(f"config::config_section::{section}", "Well Mr Hippo, that didn't work. Now what?")
            if i18n_label != "Well Mr Hippo, that didn't work. Now what?":
                contents += "##\n"
                description = textwrap.dedent(i18n_label).strip()
                desc_out = textwrap.fill(description, initial_indent="## ", subsequent_indent="## ", width=75)
                # desc_out = re.sub("\n", " ##\n", desc_out)
                contents += f"{desc_out}\n"
            contents += "################################################################################\n"
            contents += f"[{section}]\n"


            try:
                for item, data in options.items():
                    if section in self.configs_details:
                        item_key = None
                        if item in self.configs_details[section]:
                            item_key = item
                        if "*" in self.configs_details[section]:
                            item_key = "*"
                        if item_key is not None:
                            if "encrypt" in self.configs_details[section][item_key]:
                                if self.configs_details[section][item_key]['encrypt'] is True:
                                    try:
                                        data = yield self._GPG.encrypt(data)
                                    except YomboWarning as e:
                                        logger.info("Tried to encrypt a yombo.ini value, but gpg not ready. Saving cleartext.")

                    i18n_label = _(f"config::config_item::{section}::{item}", "Well Mr Hippo, that didn't work. Now what?")
                    if i18n_label != "Well Mr Hippo, that didn't work. Now what?":
                        description = f"{section}->{item}: {i18n_label}"
                        description = textwrap.dedent(description).strip()
                        desc_out = textwrap.fill(description, initial_indent="# ", subsequent_indent="#       ", width=75)
                        contents += f"{desc_out}\n"
                        # contents += "# %s->%s: %s\n" % (section, item, i18n_label)
                    temp = str(data).split("\n")
                    temp = "\n\t".join(temp)
                    contents += f"{item} = {temp}\n"
            except Exception as e:
                logger.error("---------==( Error with config encryt)==----------------")
                logger.error("{e}", e=e)
                logger.error("{trace}", trace=traceback.format_exc())
                logger.error("--------------------------------------------------------")
                logger.warn("Caught error in saving ini file: {e}", e=e)
            contents += "\n"
        return contents

    @inlineCallbacks
    def _modules_loaded_(self, **kwargs):
        """
        Called after _load_ is called for all the modules. Get's a list of configuration items all library
        or modules define or use.

        Note: This complies with i18n translations for future use.

        **Hooks called**:

        * _configuration_details_ : Gets various details about a configuration item. Do not implement, not set
          in stone. Might migrate to i18n library.

        **Usage**:

        .. code-block:: python

           def _configuration_details_(self, **kwargs):
               return [{"webinterface": {
                           "enabled": {
                               "description": {
                                   "en": "Enables/disables the web interface.",
                               },
                               "encrypt": True
                           },
                           "port": {
                               "description": {
                                   "en": "Port number for the web interface to listen on."
                               }
                           }
                       },
               }]
        """
        config_details = yield global_invoke_all("_configuration_details_", called_by=self)

        for component, details in config_details.items():
            if details is None:
                continue
            for list in details:
#                logger.warn("For module {component}, adding details: {list}", component=component, list=list)
                self.configs_details = dict_merge(self.configs_details, list)

        for section, options in self.configs.items():
            for option, keys in options.items():
                try:
                    self.configs[section][option]["details"] = self.configs_details[section][option]
                except:
                    pass

    def get2(self, section, option, default="7vce#hvjGW%w$~bA6jYv[P:*.kv6mAg934+HQhPpbDFJF2Nw9rU+saNvpVL2",
             set_if_missing=True, set=None, **kwargs):
        """
        Like :py:meth:`get() <get>` below, however, this returns a callable to retrieve the value instead of an actual
        value. The callable can also be used to set the value of the configuration item too. See
        example for usage details.

        **Usage**:

        .. code-block:: python

           gw_label = self._Config.get2("core", "label", "Default Value")

           logger.info("The Gateway Label is: {label}", label=gw_label())

           # To set a new value, this shortcut would work too:
           gw_label(set="New label")

        .. versionadded:: 0.13.0

        :raises YomboInvalidArgument: When an argument is invalid or illegal.
        :raises KeyError: When the requested section and option are not found.
        :param section: The configuration section to use.
        :type section: string
        :param option: The option (key) to use. Use * to return all possible options as a dict.
        :type option: string
        :param default: What to return if no result is found, default = None.
        :type default: int or string
        :param set_if_missing: If value is missing, should it be set for future reference?
        :type set_if_missing: bool
        :return: The configuration value requested by section and option.
        :rtype: int or string or None
        """
        if set is not None:
            self.set(section, option, set, **kwargs)
            return set

        self.get(section, option, default, set_if_missing, set, **kwargs)

        return partial(self.get, section, option, default, set_if_missing)

    def get(self, section, option, default="7vce#hvjGW%w$~bA6jYv[P:*.kv6mAg934+HQhPpbDFJF2Nw9rU+saNvpVL2",
            set_if_missing=True, set=None, ignore_case=None, **kwargs):
        """
        Read value of configuration option, return None if it don't exist or
        default if defined.  Tries to type cast with int first before
        returning a string.
        
        If you always want the current value of a configuration item, use :py:meth:`get2() <get2>`.
        
        Section and option will be converted to lowercase, rendering the set/get
        function case insenstive.

        **Usage**:

        .. code-block:: python

           gatewayUUID = self._Config.get("core", "gwuuid", "Default Value")

        :raises YomboInvalidArgument: When an argument is invalid or illegal.
        :raises KeyError: When the requested section and option are not found.
        :param section: The configuration section to use.
        :type section: string
        :param option: The option (key) to use. Use * to return all possible options as a dict.
        :type option: string
        :param default: If set and nothing found, this will be returned. Otherwise, will raise KeyError.
        :type default: int or string
        :param set_if_missing: If value is missing, should it be set for future reference?
        :type set_if_missing: bool
        :return: The configuration value requested by section and option.
        :rtype: int or string or None
        """
        if set is not None:
            self.set(section, option, set, **kwargs)
            return set

        if len(section) > self.MAX_SECTION_LENGTH:
            self._Statistics.increment("lib.configuration.set.invalid_length", bucket_size=15, anon=True)
            raise YomboInvalidArgument(f"section cannot be more than {self.MAX_OPTION_LENGTH:d} chars")
        if len(option) > self.MAX_OPTION_LENGTH:
            self._Statistics.increment("lib.configuration.set.invalid_length", bucket_size=15, anon=True)
            raise YomboInvalidArgument(f"option cannot be more than {self.MAX_OPTION_LENGTH:d} chars")

        if ignore_case is not True:
            section = section.lower()
            option = option.lower()

        if section == "*":  # Get all sections and options.
            results = {}
            for section, options in self.configs.items():
                if section not in results:
                    results[section] = {}
                for option, data in options.items():
                    results[section][option] = self.configs[section][option]["value"]
            return results

        if section in self.configs:  # Get all options for a provided section name.
            if option == "*":
                if len(self.configs[section]) > 0:
                    results = {}
                    for key, data in self.configs[section].items():
                        if "value" in data:
                            results[key] = data["value"]
                            data["reads"] += 1
                    return results
                return KeyError(f"Requested configuration not found: {section} : {option}")

            elif option in self.configs[section]:
                self.configs[section][option]["reads"] += 1
                self._Statistics.increment("lib.configuration.get.value", bucket_size=15, anon=True)
                return self.configs[section][option]["value"]

        # it"s not here, so, if there is a default, lets save that for future reference and return it... English much?
        if default == "":
            self._Statistics.increment("lib.configuration.get.empty_string", bucket_size=15, anon=True)
            return ""

        if default != "7vce#hvjGW%w$~bA6jYv[P:*.kv6mAg934+HQhPpbDFJF2Nw9rU+saNvpVL2":
            if set_if_missing:
                self.set(section, option, default)
                self.configs[section][option]["reads"] += 1
            self._Statistics.increment("lib.configuration.get.default", bucket_size=15, anon=True)
            return default
        else:
            self._Statistics.increment("lib.configuration.get.nodefault", bucket_size=15, anon=True)
            if section not in self.configs:
                raise KeyError(f"Configuration section not found: {section}")
            else:
                raise KeyError(f"Configuration option doesn't exist: {section} -> {option}")

    @inlineCallbacks
    def set(self, section, option, value, ignore_case=None, **kwargs):
        """
        Set value of configuration option for a given section.  The option length
        **cannot exceed 1000 characters**.  The value cannot exceed 5000 bytes.

        Section and option will be converted to lowercase, rending the set/get function case insenstive.

        **Usage**:

        .. code-block:: python

           gatewayUUID = self._Config.set("section_name"
           , "myoption", "New Value")

        :raises YomboInvalidArgument: When an argument is invalid or illegal.
        :raises KeyError: When the requested section and option are not found.
        :param section: The configuration section to use.
        :type section: string
        :param option: The option (key) to use.
        :type option: string
        :param value: What to return if no result is found, default = None.
        :type value: int or string
        """
        if len(section) > self.MAX_SECTION_LENGTH:
            self._Statistics.increment("lib.configuration.set.invalid_length", bucket_size=15, anon=True)
            raise YomboInvalidArgument(f"section cannot be more than {self.MAX_OPTION_LENGTH:d} chars")
        if len(option) > self.MAX_OPTION_LENGTH:
            self._Statistics.increment("lib.configuration.set.invalid_length", bucket_size=15, anon=True)
            raise YomboInvalidArgument(f"option cannot be more than {self.MAX_OPTION_LENGTH:d} chars")

        # Can't set value!
        if section == "yombo":
            self._Statistics.increment("lib.configuration.set.no_setting_yombo", bucket_size=15, anon=True)
            raise YomboInvalidArgument("Not allowed to set value")

        if isinstance(value, str):
            if len(value) > self.MAX_VALUE_LENGTH:
                self._Statistics.increment("lib.configuration.set.value_too_long", bucket_size=15, anon=True)
                raise YomboInvalidArgument(f"value cannot be more than {self.MAX_VALUE:d} chars")

        if ignore_case is not True:
            section = section.lower()
            option = option.lower()

        if section not in self.configs:
            self.configs[section] = {}
        if option not in self.configs[section]:
            self.configs[section][option] = {
                "created_at": int(time()),
                "reads": 0,
                "writes": 0,
            }
            self._Statistics.increment("lib.configuration.set.new", bucket_size=15, anon=True)
        else:
            # already have a value. If it's the same, we won't set it.
            if self.configs[section][option]["value"] == value:
                self._Statistics.increment("lib.configuration.set.skipped_same_value", bucket_size=15, anon=True)
                return value
            self._Statistics.increment("lib.configuration.set.update", bucket_size=15, anon=True)

        self.configs[section][option] = dict_merge(self.configs[section][option], {
                "updated_at": int(time()),
                "value": value,
                "hash": sha224( str(value).encode("utf-8") ).hexdigest(),
            })
        self.configs_dirty = True
        if self.loading_yombo_ini is False:
            self.configs[section][option]["writes"] += 1
            yield global_invoke_all("_configuration_set_",
                                    called_by=self,
                                    section=section,
                                    option=option,
                                    value=value,
                                    )
        return value

    def get_meta(self, section, option, meta_type="time"):
        try:
            return self.configs_meta[section, option][meta_type]
        except:
            return None

    @inlineCallbacks
    def delete(self, section, option):
        """
        Delete a section/option value from configs (yombo.ini).

        :param section: The configuration section to use.
        :type section: string
        :param option: The option (key) to delete.
        :type option: string
        """
        if section in self.configs:
            if option in self.configs[section]:
                self.configs_dirty = True
                del self.configs[section][option]
                yield global_invoke_all("_configuration_delete_",
                                        called_by=self,
                                        section=section,
                                        option=option,
                                        value=None,
                                        )
