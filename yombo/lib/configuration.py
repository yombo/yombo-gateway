# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For more information see:
  `Configuration @ Module Development <https://yombo.net/docs/modules/configuration/>`_

Handles loading, storing, updating, and saving gateway configuration items.

If you wish to store persistent data for your module, use the
:py:mod:`SQLDict Library <yombo.lib.sqldict>`.

*Usage**:

.. code-block:: python

   latitude = self._Configs.get("location", "latitude")  # also can accept default and if a default value should be saved.
   latitude = self._Configs.get("location", "latitude", "0", False)  # example of default and no save if default is used.
   self._Configs.set("location", "latitude", 100)  # Save a new latitude location.

A function can also be returned by calling get2(). This allows the a library or module to always access the
latest version of a configuration value.  The function can also accept a named parameter of 'set' to set a
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
       section = kwargs['section']
       option = kwargs['option']
       value = kwargs['value']

       if section == 'core':
           if option == 'label':
               logger.info("the system label was changed to: {label}", label=value)


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import ConfigParser
import hashlib
from time import time, localtime, strftime
import cPickle
from shutil import move, copy2 as copyfile
import os
from datetime import datetime
import sys
import traceback
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from functools import partial

# Import twisted libraries
from twisted.internet.task import LoopingCall
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.utils import get_external_ip_address_v4, get_local_network_info
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
from yombo.utils import dict_merge, global_invoke_all, is_string_bool, fopen, file_last_modified, dict_diff

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
        self.automation_startup_check = []
        self._loaded = False
        self.yombo_ini_last_modified = 0

        ini_norestore = not os.path.exists('yombo.ini.norestore')

        if os.path.exists('yombo.ini'):
            if os.path.isfile('yombo.ini') is False:
                try:
                    os.remove('yombo.ini')
                except Exception, e:
                    logger.error("'yombo.ini' file exists, but it's not a file and it can't be deleted!")
                    reactor.stop()
                    return
                if ini_norestore:
                    self.restore_backup_yombi_ini()
            else:
                if os.path.getsize('yombo.ini') < 5:
                    logger.warn('yombo.ini appears corrupt, attempting to restore from backup.')
                    if ini_norestore:
                        self.restore_backup_yombi_ini()
        else:
            if ini_norestore:
                self.restore_backup_yombi_ini()

        self.loading_yombo_ini = True
        self.last_yombo_ini_read = self.read_yombo_ini()

        try:
            config_parser = ConfigParser.SafeConfigParser()
            fp = open('usr/etc/yombo.ini.info')
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
            logger.warn("CAUGHT IOError!!!!!!!!!!!!!!!!!!  In reading meta: {error}", error=e)
        except ConfigParser.NoSectionError:
            logger.warn("CAUGHT ConfigParser.NoSectionError!!!!  IN saving. ")
        # print self.configs

        # Perform DB cleanup activites based on local section.
        if self.get('local', 'deletedelayedmessages') is True:
            self._Libraries['localdb'].delete('sqldict', ['module = ?', 'yombo.gateway.lib.messages'])
            self.set('local', 'deletedelayedmessages', False)

        if self.get('local', 'deletedevicehistory') is True:
            self._Libraries['localdb'].truncate('devicestatus')
            self.set('local', 'deletedevicehistory', False)

        if self.get('core', 'externalipaddress') is not None and self.get('core', 'externalipaddresstime') is not None:
            if int(self.configs['core']['externalipaddresstime']['value']) < (int(time()) - 3600):
                self.set("core", "externalipaddress_v4", get_external_ip_address_v4())
                self.set("core", "externalipaddresstime", int(time()))
        else:
            #            print "didn't find external ip address"
            self.set("core", "externalipaddress_v4", get_external_ip_address_v4())
            self.set("core", "externalipaddresstime", int(time()))

        if self.get('local', 'localipaddress') is not None and self.get('local', 'localipaddresstime') is not None:
            if int(self.configs['core']['localipaddresstime']['value']) < (int(time()) - 180):
                address_info = get_local_network_info()
                self.set("core", "localipaddress_v4", address_info['ipv4']['address'])
                self.set("core", "localipaddress_netmask_v4", address_info['ipv4']['netmask'])
                self.set("core", "localipaddress_cidr_v4", address_info['ipv4']['cidr'])
                self.set("core", "localipaddress_network_v4", address_info['ipv4']['network'])
                self.set("core", "localipaddress_v6", address_info['ipv6']['address'])
                self.set("core", "localipaddress_netmask_v6", address_info['ipv6']['netmask'])
                # self.set("core", "localipaddress_cidr_v6", address_info['ipv6']['cidr'])
                # self.set("core", "localipaddress_network_v6", address_info['ipv6']['network'])
                self.set("core", "localipaddresstime", int(time()))
        else:
            address_info = get_local_network_info()
            self.set("core", "localipaddress_v4", address_info['ipv4']['address'])
            self.set("core", "localipaddress_netmask_v4", address_info['ipv4']['netmask'])
            self.set("core", "localipaddress_cidr_v4", address_info['ipv4']['cidr'])
            self.set("core", "localipaddress_network_v4", address_info['ipv4']['network'])
            self.set("core", "localipaddress_v6", address_info['ipv6']['address'])
            self.set("core", "localipaddress_netmask_v6", address_info['ipv6']['netmask'])
            # self.set("core", "localipaddress_cidr_v6", address_info['ipv6']['cidr'])
            # self.set("core", "localipaddress_network_v6", address_info['ipv6']['network'])
            self.set("core", "localipaddresstime", int(time()))

        self.periodic_save_yombo_ini = LoopingCall(self.save)
        self.periodic_save_yombo_ini.start(14400, False)
        # self.periodic_load_yombo_ini = LoopingCall(self.check_if_yombo_ini_modified)
        # self.periodic_load_yombo_ini.start(5)

        if self.get('core', 'setup_stage') is None:
            self.set('core', 'setup_stage', 'first_run')
        self.loading_yombo_ini = False

    def _load_(self):
        self._loaded = True

    def _start_(self):
        """
        Define some default configuration items.
        :return:
        """
        self.set('misc', 'tempurature_display', 'f')
        self.set('misc', 'length_display', 'imperial')  # will we ever get to metric?

    def _stop_(self):
        if self.periodic_save_yombo_ini is not None and self.periodic_save_yombo_ini.running:
            self.periodic_save_yombo_ini.stop()

        # if self.periodic_load_yombo_ini is not None and self.periodic_load_yombo_ini.running:
        #     self.periodic_load_yombo_ini.stop()

    def _unload_(self):
        """
        Save the items in the config table to yombo.ini.  This allows
        the user to see the current configuration and make any changes.
        """
        self.save(True)

    def read_yombo_ini(self, update_self=True):
        config_parser = ConfigParser.SafeConfigParser()

        temp = {}
        try:
            fp = fopen('yombo.ini')
            config_parser.readfp(fp)
            fp.close()

            for section in config_parser.sections():
                temp[section] = {}

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
                                if value == "None":
                                    value = None
                                else:
                                    value = str(value)

                    temp[section][option] = value
                    if update_self:
                        self.set(section, option, value)

        except IOError:
            self._Atoms.set('configuration.yombo_ini.found', False)
            self._Loader.operation_mode = 'firstrun'
            logger.warn("yombo.ini doesn't exist. Setting run mode to 'firstrun'.")
            self._Atoms.set('configuration.yombo_ini.found', False)
            self.loading_yombo_ini = False
            return False
            # return
        except ConfigParser.NoSectionError, e:
            self._Atoms.set('configuration.yombo_ini.found', False)
            logger.warn("CAUGHT ConfigParser.NoSectionError!!!!  In Loading. {error}", error=e)
            return False
        else:
            self._Atoms.set('configuration.yombo_ini.found', True)
            timeString  = strftime("%Y-%m-%d_%H:%M:%S", localtime())
            copyfile('yombo.ini', "usr/bak/yombo_ini/%s_yombo.ini" % timeString)
            return temp

    # def check_if_yombo_ini_modified(self):
    #     last_modified = file_last_modified('yombo.ini')
    #
    #     if self.yombo_ini_last_modified == 0:
    #         self.yombo_ini_last_modified = last_modified
    #         print "yombo.ini last modified: %s" % self.yombo_ini_last_modified
    #         return
    #
    #     if self.yombo_ini_last_modified < last_modified:
    #         self.yombo_ini_last_modified = last_modified
    #         print "yombo file updated...  should read it?"
    #         configs = self.read_yombo_ini(update_self=False)
    #         added, removed, modified, same = dict_diff(self.last_yombo_ini_read, configs)
    #
    #         print "added: %s" % added
    #         print "removed: %s" % removed
    #         print "modified: %s" % modified
    #         print "same: %s" % same
    #
    #         for section in added:
    #             for option, value in configs[section].iteritems():
    #                  print "adding: %s: %s: %s" % (section, option, value)
    #                  # self.set(section, option, value)
    #
    #         for section, options in configs.iteritems():
    #             for option, value in options.iteritems():

            # for section in removed:
            #     self.configs[section][option]
            #     for option, value in configs[section].iteritems():
            #         print "adding: %s: %s: %s" % (section, option, value)
            #         # self.set(section, option, value)

                    #     for value in options:
            #
            #
            #
            # for section, options in added.iteritems():
            #     print "adding: %s: %s" % (section, option)
            #     for value in options:
            #         self.set(section, option, value)



    def Configuration_i18n_atoms(self, **kwargs):
       return [
           {'configuration.yombo_ini.found': {
               'en': 'True if yombo.ini was found on startup.',
               },
           },
       ]

    def restore_backup_yombi_ini(self):
        path = "usr/bak/yombo_ini/"

        dated_files = [(os.path.getmtime("%s/%s" % (path, fn)), os.path.basename(fn))
                       for fn in os.listdir(path)]
        dated_files.sort()
        dated_files.reverse()
        if len(dated_files) > 0:
            for i in range(0, len(dated_files)):
                the_file = "%s/%s" % (path, dated_files[i][1])
                if os.path.getsize(the_file) > 100:
                    copyfile(the_file, 'yombo.ini')
                    logger.warn("yombo.ini file restored from previous backup.")
                    return True
        return False

    def save(self, force_save=False):
        """
        Save the configuration configs to the INI file.

        #Todo: convert to fdesc for non-blocking. Need example of usage.
        """
        try:
            # If for some reason startup fails, we won't get _() defined. We just try to print _() and test...
            logger.debug(_('system', 'Current locale: None'))

            if self.configs_dirty is True or force_save is True:
                logger.debug("saving config file...")
                config_file = open("yombo.ini",'w')
                config_file.write("#\n# " + _('configuration', "This file stores configuration information about the gateway.") + "\n")
                config_file.write("# " + _('configuration', "WARNING: Do not edit this file while the gateway is running, any changes will be lost.") + "\n# \n")

                # first parse sections to make sure each section has a value!
                configs = {}
                for section, options in self.configs.iteritems():
                    if section == 'zz_configmetadata':
                        continue
                    if section not in configs:
                        configs[section] = {}
                    for item, data in options.iteritems():
                        if 'value' not in data:  # incase it's documented, but not used. Usually bad doco.
                            continue
                        configs[section][item] = data['value']

                #now we save the sections and the items...with i18n comments!
                for section, options in configs.iteritems():
                    i18n_label = _('config_section', "%s" % section)
                    if i18n_label != "%s" % section:
                        config_file.write("# %s: %s\n" % (section, i18n_label))
                    # else:
                    #     config_file.write("# %s: " % section + _('system', "No translation found for: {section}").format(section=section) + "\n" )
                    config_file.write("[%s]\n" % section)

                    try:
                        for item, data in options.iteritems():
                            i18n_label = _('config_item', "%s:%s" % (section, item))
                            if i18n_label != "%s:%s" % (section, item):
                                config_file.write("# %s: %s\n" % (item, i18n_label))
                            temp = str(data).split("\n")
                            temp = "\n\t".join(temp)
                            config_file.write("%s = %s\n" % (item, temp))
                    except Exception as E:
                        logger.warn("Caught error in saving ini file: {e}", e=E)
                    config_file.write('\n')

                config_file.close()

                Config = ConfigParser.ConfigParser()
                for section, options in self.configs.iteritems():
                    Config.add_section(section)
                    for item, data in options.iteritems():
                        temp = self.configs[section][item].copy()
                        # if 'reads' in temp:
                        #     del temp['reads']
                        if 'details' in temp:
                            del temp['details']
                        # if 'writes' in temp:
                        #     del temp['writes']
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

            backup_files = os.listdir(os.path.dirname(path))
            if len(backup_files) > 5:
                for file in backup_files: # remove old yombo.ini backup files.
                    fullpath   = os.path.join(path,file)    # turns 'file1.txt' into '/path/to/file1.txt'
                    timestamp  = os.stat(fullpath).st_ctime # get timestamp of file
                    createtime = datetime.fromtimestamp(timestamp)
                    now        = datetime.now()
                    delta      = now - createtime
                    if delta.days > 30:
                        os.remove(fullpath)

        except Exception as E:
            logger.warn("Caught master error in saving ini file: {e}", e=E)
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")

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

    def get2(self, section, option=None, default=None, set_if_missing=True, set=None, **kwargs):
        """
        Like :py:meth:`get() <get>` below, however, returns a callable to retrieve the value instead of an actual
        value. The callable can also be used to set the value of the configuration item too. See
        example for usage details.

        **Usage**:

        .. code-block:: python

           gw_label = self._Config.get2("core", "label", "Default Value")
           logger.info("The Gateway Label is: {labe}", label=gw_label)
           # set a new label.  Don't really ever do this.
           gw_label(set="New label")

        .. versionadded:: 0.13.0

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

        if set is not None:
            return self.set(section, option, set, **kwargs)
        if option is None:
            raise YomboWarning("get operation must have option.")

        section = section.lower()
        option = option.lower()

        return partial(self.get, section, option, default, set_if_missing)

    def get(self, section, option=None, default=None, set_if_missing=True, set=None, **kwargs):
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
            return self.set(section, option, set, **kwargs)

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

    def set(self, section, option, value, **kwargs):
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

        # print "setting section: %s, option: %s, value: %s" % (section, option, value)
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
            # already have a value. If it's the same, we won't set it.
            if self.configs[section][option]['value'] == value:
                self._Statistics.increment("lib.configuration.set.skipped_same_value", bucket_time=15, anon=True)
                return
            self._Statistics.increment("lib.configuration.set.update", bucket_time=15, anon=True)

        self.configs[section][option] = dict_merge(self.configs[section][option], {
                'set_time': int(time()),
                'value': value,
                'hash': hashlib.sha224( str(value) ).hexdigest(),
            })
        self.configs_dirty = True
        if self.loading_yombo_ini is False:
            self.configs[section][option]['writes'] += 1
            global_invoke_all('_configuration_set_', **{'section':section, 'option': option, 'value': value, 'action': 'set'})


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
                self.configs_dirty = True
                del self.configs[section][option]
                global_invoke_all('_configuration_set_', **{'section': section, 'option': option, 'value': None, 'action': 'delete'})

    ##############################################################################################################
    # The remaining functions implement automation hooks. These should not be called by anything other than the  #
    # automation library!                                                                                        #
    #############################################################################################################

    def check_trigger(self, section, option, value):
        """
        Called by the configs.set function when a new value is set. It asks the automation library if this key is
        trigger, and if so, fire any rules.

        True - Rules fired, fale - no rules fired.
        """
        input = {'s': section, 'o':option}
        key = json.dumps(input, separators=(',',':') )
        if self._loaded:
            results = self.automation.triggers_check('configs', key, value)

    def _automation_source_list_(self, **kwargs):
        """
        hook_automation_source_list called by the automation library to get a list of possible sources.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'configs',
              'description': 'Allows configurations to be used as a source (trigger).',
              'validate_source_callback': self.configs_validate_source_callback,  # function to call to validate a trigger
              'add_trigger_callback': self.configs_add_trigger_callback,  # function to call to add a trigger
              'startup_trigger_callback': self.configs_startup_trigger_callback,  # function to call to check all triggers
              'get_value_callback': self.configs_get_value_callback,  # get a value
              'field_details': [
                  {
                  'label': 'section',
                  'description': 'The section of the configuration to monitor.',
                  'required': True
                  },
                  {
                  'label': 'option',
                  'description': 'The option of the configuration to monitor. Example: section.option',
                  'required': True
                  },
                  {
                  'label': 'default',
                  'description': "A default value to use if the configuration value doesn't exist.",
                  'required': False
                  },
              ]
            }
         ]

    def configs_validate_source_callback(self, rule, portion, **kwargs):
        """
        A callback to check if a provided source is valid before being added as a possible source.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the portion of rule being fired. Includes source, filter, etc.
        :return:
        """
        if all( required in portion['source'] for required in ['platform', 'section', 'option']):
            return True
        raise YomboWarning("Source doesn't have required parameters: platform, section, and option",
                101, 'configs_validate_source_callback', 'configs')

    def configs_add_trigger_callback(self, rule, **kwargs):
        """
        Called to add a trigger.  We simply use the automation library for the heavy lifting.

        :param rule: The potential rule being added.
        :param kwargs: None
        :return:
        """
        if 'run_on_start' in rule:
            if rule['run_on_start'] is True:
                section = rule['trigger']['source']['section']
                option = rule['trigger']['source']['option']
                input = {'s': section, 'o':option}
                key = json.dumps(input, separators=(',',':') )
                self.automation_startup_check.append(key)
        self.automation.triggers_add(rule['rule_id'], 'configs', key)

    def configs_startup_trigger_callback(self):
        """
        Called when automation rules are active. Check for any automation rules that are marked with run_on_start

        :return:
        """
        for key in self.automation_startup_check:
            input = json.loads(key)
            section = input['s']
            option = input['o']
            if section in self.configs:
                if option in self.configs[section]:
                    if self._loaded:
                        results = self.automation.triggers_check('configs', key, self.configs[section][option]['value'])

    def configs_get_value_callback(self, rule, portion, **kwargs):
        """
        A callback to the value for platform "states". We simply just do a get based on key_name.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the portion of rule being fired. Includes source, filter, etc.
        :return:
        """
        if 'default' in portion['source']:
            default = portion['source']['default']
        else:
            default = None
        return self.get(portion['source']['section'], portion['source']['section'], default, None)

    def _automation_action_list_(self, **kwargs):
        """
        hook_automation_action_list called by the automation library to list possible actions this module can
        perform.

        This implementation allows automation rules set easily set Atom values.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'configs',
              'description': 'Allows configs to be changed as an action.',
              'validate_action_callback': self.configs_validate_action_callback,  # function to call to validate an action is possible.
              'do_action_callback': self.configs_do_action_callback,  # function to be called to perform an action
              'field_details': [
                  {
                  'label': 'section',
                  'description': 'The section of the configuration to change.',
                  'required': True
                  },
                  {
                  'label': 'option',
                  'description': 'The option of the configuration to change. Example: section.option',
                  'required': True
                  },
                  {
                  'label': 'value',
                  'description': 'The value that should be set.',
                  'required': True
                  }
              ]
            }
         ]

    def configs_validate_action_callback(self, rule, action, **kwargs):
        """
        A callback to check if a provided action is valid before being added as a possible action.

        :param rule: The potential rule being added.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        if all( required in action for required in ['section', 'option', 'value']):
            return True
        raise YomboWarning("configs_validate_action_callback: action is required to have parameters: section, option, and value",
                101, 'configs_validate_action_callback', 'configs')

    def configs_do_action_callback(self, rule, action, **kwargs):
        """
        A callback to perform an action.

        :param rule: The complete rule being fired.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        return self.set(action['section'], action['option'], action['value'])
