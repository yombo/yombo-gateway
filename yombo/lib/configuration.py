#cython: embedsignature=True
# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Handles loading, storing, updating, and saving gateway configuration items.

Module developers do not need to access any methods or variables here.
Instead, module developers should user L{SQLDict} to store any values
that need to be persistent. This includes module specific settings or
configuration not set using the standard module variables portion
for the module as defined in the 'Deverlopers Corner'.

Implements a basic cache system for speed so database reads
are kept to a minimum.

.. warning::

   These resources are NOT meant for direct access.  To get and set configuration
   values, use :ref:`getConfigValue` and :ref:`setConfigValue>.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2015 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import ConfigParser
import hashlib
from time import time, localtime, strftime
import cPickle
from shutil import copyfile
import os
from datetime import datetime

# Import twisted libraries
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.utils import get_external_ip_address, get_local_ip_address
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
from yombo.utils import dict_merge, global_invoke_all, is_string_bool

logger = get_logger('library.configuration')


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
    yombo_vars = {
        'version': '0.12.0',
    }
    configs = {'core': {}, 'zz_configmetadata': {}}  # Contains all the config items
    configs_details = {}  # Collected details from libs and modules about configurations

    def _init_(self):
        """
        Open the yombo.ini file for reading.

        Import the configuration items into the database, also prime the configs for reading.
        """
        self.cache_dirty = False
        

        self.loading_yombo_ini = True
        try:
            config_parser = ConfigParser.SafeConfigParser()
            fp = open('yombo.ini')
            config_parser.readfp(fp)
            fp.close()

            for section in config_parser.sections():
                for option in config_parser.options(section):
                    value = config_parser.get(section, option)
                    try:
                        value = is_string_bool(value)
                    except:
                        try:
                            value = int(value)
                        except:
                            try:
                                value = float(value)
                            except:
                                value = str(value)
                    self.set(section, option, value)
        except IOError:
            self._Atoms.set('configuration.yombo_ini.found', False)
            self._Loader.operation_mode = 'firstrun'
            logger.warn("yombo.ini doesn't exist. Setting run mode to 'firstrun'.")
            self._Atoms.set('configuration.yombo_ini.found', False)
            return
        except ConfigParser.NoSectionError, e:
            self._Atoms.set('configuration.yombo_ini.found', False)
            print "CAUGHT ConfigParser.NoSectionError!!!!  In Loading. %s" % e
        else:
            self._Atoms.set('configuration.yombo_ini.found', True)
            timeString  = strftime("%Y-%m-%d_%H:%M:%S", localtime())
            copyfile('yombo.ini', 'usr/bak/yombo_ini/yombo.ini.' + timeString)

        try:
            config_parser = ConfigParser.SafeConfigParser()
            fp = open('usr/etc/yombo.ini.meta')
            config_parser.readfp(fp)
            fp.close()

            for section in config_parser.sections():
                if section not in self.configs:
                    continue
                for option in config_parser.options(section):
                    if option not in self.configs[section]:
                        continue
                    values = cPickle.loads(config_parser.get(section, option))
                    self.configs[section][option] = dict_merge(self.configs[section][option], values)
        except IOError, e:
            print "CAUGHT IOError!!!!!!!!!!!!!!!!!!  In reading meta: %s" % e
        except ConfigParser.NoSectionError:
            print "CAUGHT ConfigParser.NoSectionError!!!!  IN saving. "

        # Perform DB cleanup activites based on local section.
        if self.get('local', 'deletedelayedmessages') is True:
            self._Libraries['localdb'].delete('sqldict', ['module = ?', 'yombo.gateway.lib.messages'])
            self.set('local', 'deletedelayedmessages', False)

        if self.get('local', 'deletedevicehistory') is True:
            self._Libraries['localdb'].truncate('devicestatus')
            self.set('local', 'deletedevicehistory', False)

        if self.get('core', 'externalipaddress') is not None and self.get('core', 'externalipaddresstime') is not None:
            if int(self.configs['core']['externalipaddresstime']['value']) < (int(time()) - 3600):
                self.set("core", "externalipaddress", get_external_ip_address())
                self.set("core", "externalipaddresstime", int(time()))
        else:
#            print "didn't find external ip address"
            self.set("core", "externalipaddress", get_external_ip_address())
            self.set("core", "externalipaddresstime", int(time()))

        # if self.get('local', 'localipaddress') is not None and self.get('local', 'localipaddresstime') is not None:
        #     if int(self.configs['core']['localipaddresstime']['value']) < (int(time()) - 180):
        #         self.set("core", "localipaddress", get_local_ip_address())
        #         self.set("core", "localipaddresstime", int(time()))
        # else:
        #     self.set("core", "localipaddress", get_local_ip_address())
        #     self.set("core", "localipaddresstime", int(time()))


        self.periodic_save_ini = LoopingCall(self.save)
        self.periodic_save_ini.start(14400, False)

        if self.get('core', 'setup_stage') is None:
            self.set('core', 'setup_stage', 'first_run')
        self.loading_yombo_ini = False

    def _unload_(self):
        """
        Save the items in the config table to yombo.ini.  This allows
        the user to see the current configuration and make any changes.
        """
        self.save(True)

    def Configuration_i18n_atoms(self, **kwargs):
       return [
           {'configuration.yombo_ini.found': {
               'en': 'True if yombo.ini was found on startup.',
               },
           },
       ]
    def save(self, force_save=False):
        """
        Save the configuration configs to the INI file.

        #Todo: convert to fdesc for non-blocking. Need example of usage.
        """
        if self.configs_dirty is True or force_save is True:
            logger.debug("saving config file...")
            Config = ConfigParser.ConfigParser()
            for section, options in self.configs.iteritems():
                Config.add_section(section)
                for item, data in options.iteritems():
                    if 'value' not in data:  # incase it's documented, but not used. Usually bad doco.
                        continue
                    Config.set(section, item, data['value'])
                if len(Config.options(section)) == 0:  # Don't save empty sections.
                    Config.remove_section(section)

            config_file = open("yombo.ini",'w')
            Config.write(config_file)
            config_file.close()

            Config = ConfigParser.ConfigParser()
            for section, options in self.configs.iteritems():
                Config.add_section(section)
                for item, data in options.iteritems():
                    temp = self.configs[section][item].copy()
                    if 'reads' in temp:
                        del temp['reads']
                    if 'details' in temp:
                        del temp['details']
                    if 'writes' in temp:
                        del temp['writes']
                    if 'value' in temp:
                        del temp['value']
                    Config.set(section, item, cPickle.dumps(temp) )
                if len(Config.options(section)) == 0:  # Don't save empty sections.
                    Config.remove_section(section)

            config_file = open("usr/etc/yombo.ini.info",'w')
            config_file.write('#\n')
            config_file.write('# This file stores meta information about yombo.ini. Do not edit manually!\n')
            config_file.write('#\n')
            Config.write(config_file)
            config_file.close()

        self.configs_dirty = False

        path = "usr/bak/yombo_ini/"

        for file in os.listdir(os.path.dirname(path)):
            fullpath   = os.path.join(path,file)    # turns 'file1.txt' into '/path/to/file1.txt'
            timestamp  = os.stat(fullpath).st_ctime # get timestamp of file
            createtime = datetime.fromtimestamp(timestamp)
            now        = datetime.now()
            delta      = now - createtime
            if delta.days > 30:
                os.remove(fullpath)

    def _module_prestart_(self, **kwargs):
        """
        Called after _init_ is called for all the modules. Get's a list of configuration items all library
        or modules define or use.

        Note: This complies with i18n translations for future use.

        **Hooks called**:

        * _configuration_details_ : Gets various details about a configuration item. Do not implement, not set
        in stone. Might migrate to i18n library.

        **Usage**:

        .. code-block:: python

           def _configuration_details_(self, **kwargs):
               return [{'webinterface': {
                           'enabled': {
                               'description': {
                                   'en': 'Enables/disables the web interface.',
                               }
                           },
                           'port': {
                               'description': {
                                   'en': 'Port number for the web interface to listen on.'
                               }
                           }
                       },
               }]
        """
        config_details = global_invoke_all('_configuration_details_')

        for component, details in config_details.iteritems():
            if details is None:
                continue
            for list in details:
#                logger.warn("For module {component}, adding details: {list}", component=component, list=list)
                self.configs_details = dict_merge(self.configs_details, list)

        for section, options in self.configs.iteritems():
            for option, keys in options.iteritems():
                try:
                    self.configs[section][option]['details'] = self.configs_details[section][option]
                except:
                    pass

    def get(self, section, option=None, default=None, set_if_missing=True):
        """
        Read value of configuration option, return None if it don't exist or
        default if defined.  Tries to type cast with int first before
        returning a string.
        
        Section and option will be converted to lowercase, rendering the set/get
        function case insenstive.

        **Usage**:

        .. code-block:: python

           gatewayUUID = self._Config.get("core", "gwuuid", "Default Value")

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
        if len(section) > self.MAX_SECTION_LENGTH:
            self._Statistics.increment("lib.configuration.set.invalid_length", bucket_time=15, anon=True)
            raise ValueError("section cannot be more than %d chars" % self.MAX_OPTION_LENGTH)
        if len(option) > self.MAX_OPTION_LENGTH:
            self._Statistics.increment("lib.configuration.set.invalid_length", bucket_time=15, anon=True)
            raise ValueError("option cannot be more than %d chars" % self.MAX_OPTION_LENGTH)

        if option is None:
            raise YomboWarning("get operation must have option.")

        section = section.lower()
        option = option.lower()

        if section == 'yombo':
            if option in self.yombo_vars:
                self._Statistics.increment("lib.configuration.get.value", bucket_time=15, anon=True)
                return self.yombo_vars[option]
            else:
                self._Statistics.increment("lib.configuration.get.none", bucket_time=15, anon=True)
            return None

        if section == "*":  # we now allow to get all config items. Useful for the web.
            results = {}
            for section, options in self.configs.iteritems():
                if section not in results:
                    results[section] = {}
                for option, data in options.iteritems():
                    results[section][option] = self.configs[section][option]['value']
            return results

        if section in self.configs:
            if option == "*":
                if len(self.configs[section]) > 0:
                    results = {}
                    for key, data in self.configs[section].iteritems():
                        if 'value' in data:
                            results[key] = data['value']
                            data['reads'] += 1
                    return results
                return None

            if option in self.configs[section]:
                self.configs[section][option]['reads'] += 1
#                returnValue(self.configs[section][option])
                self._Statistics.increment("lib.configuration.get.value", bucket_time=15, anon=True)
                return self.configs[section][option]['value']

        # it's not here, so, if there is a default, lets save that for future reference and return it... English much?
        if default == "":
            self._Statistics.increment("lib.configuration.get.empty_string", bucket_time=15, anon=True)
            return ""

        if default is not None:
            if set_if_missing:
                self.set(section, option, default)
                self.configs[section][option]['reads'] += 1
            self._Statistics.increment("lib.configuration.get.default", bucket_time=15, anon=True)
            return default
        else:
            self._Statistics.increment("lib.configuration.get.nodefault", bucket_time=15, anon=True)
            return None

    def set(self, section, option, value):
        """
        Set value of configuration option for a given section.  The option length
        **cannot exceed 1000 characters**.  The value cannot exceed 5000 bytes.

        Section and option will be converted to lowercase, rending the set/get function case insenstive.

        **Usage**:

        .. code-block:: python

           gatewayUUID = self._Config.set("section_name", "myoption", "New Value")

        :param section: The configuration section to use.
        :type section: string
        :param option: The option (key) to use.
        :type option: string
        :param value: What to return if no result is found, default = None.
        :type value: int or string
        """
        if len(section) > self.MAX_SECTION_LENGTH:
            self._Statistics.increment("lib.configuration.set.invalid_length", bucket_time=15, anon=True)
            raise ValueError("section cannot be more than %d chars" % self.MAX_OPTION_LENGTH)
        if len(option) > self.MAX_OPTION_LENGTH:
            self._Statistics.increment("lib.configuration.set.invalid_length", bucket_time=15, anon=True)
            raise ValueError("option cannot be more than %d chars" % self.MAX_OPTION_LENGTH)

        # Can't set value!
        if section == 'yombo':
            self._Statistics.increment("lib.configuration.set.no_setting_yombo", bucket_time=15, anon=True)
            raise ValueError("Not allowed to set value")

        if isinstance(value, str):
            if len(value) > self.MAX_VALUE_LENGTH:
                self._Statistics.increment("lib.configuration.set.value_too_long", bucket_time=15, anon=True)
                raise ValueError("value cannot be more than %d chars" %
                    self.MAX_VALUE)

#        print "section: %s, option: %s, value: %s" % (section, option, value)
        section = section.lower()
        option = option.lower()

        if section not in self.configs:
            self.configs[section] = {}
        if option not in self.configs[section]:
            self.configs[section][option] = {
                'create_time': int(time()),
                'reads': 0,
                'writes': 0,
            }
            self._Statistics.increment("lib.configuration.set.new", bucket_time=15, anon=True)
        else:
            self._Statistics.increment("lib.configuration.set.update", bucket_time=15, anon=True)

        self.configs[section][option] = dict_merge(self.configs[section][option], {
                'set_time': int(time()),
                'value': value,
                'hash': hashlib.sha224( str(value) ).hexdigest(),
            })
        self.configs[section][option]['writes'] += 1
        self.configs_dirty = True
        if self.loading_yombo_ini is False:
            global_invoke_all('_configuration_set_', **{'section':section, 'option': option, 'value': value})


    def get_meta(self, section, option, meta_type='time'):
        try:
            return self.configs_meta[section, option][meta_type]
        except:
            return None

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
                del self.configs[section][option]

    def i18n_gettext(self):
        """
        Starting to implement i18n.

        :return:
        """
        strings = {}
        for section, options in self.configs.iteritems():
            for option, data in options.iteritems():
                has_string = False
                if 'details' in data:
                    if 'description' in data['details']:
                        for lang, value in data['details'].iteritems():
                            if lang not in strings:
                                strings[lang] = {}
                            strings[lang]['config.%s.%s' % (section, option)] = {
                                'msgstr': data['details'][lang]
                            }
                            has_string = True

                if has_string is False:
                    strings['en']['config.%s.%s' % (section, option)] = {
                        'msgstr': "Configuration: %s - %s" % (section, option)
                    }
        return strings
