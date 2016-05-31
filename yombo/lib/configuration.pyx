# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Handles loading, storing, updating, and saving gateway configuration items.

Module developers do not need to access any methods or variables here.
Instead, module developers should user L{SQLDict} to store any values
that need persistency.  This include module specific settings or
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
import time

# Import twisted libraries
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboCritical
from yombo.core.helpers import getExternalIPAddress
from yombo.core.log import getLogger
from yombo.core.library import YomboLibrary

logger = getLogger('library.configuration')

class Configuration(YomboLibrary):
    """
    Configuration storage module for the gateway service.

    This class manages the yombo.ini file. It reads this file on startup and
    stores the configuration items into a cache. The configuration is never
    stored in the database.
    """
    MAX_KEY = 100
    MAX_VALUE = 5001

    # Yombo constants. Used for versioning and misc tracking.
    yombo_vars = {
        'version': '0.10.0',
    }

    def _init_(self, loader):
        """
        Open the yombo.ini file for reading.

        Import the configuration items into the database, also prime the cache for reading.

        :param loader: The loader module.
        :type loader: loader
        """
        self.cache = {'core':{}}  # simple cache
        self.cacheMisses = 0
        self.cacheHits = 0

        self.loader = loader
        self.cacheDirty = False
        
        config_parser = ConfigParser.SafeConfigParser()

        try:
            fp = open('yombo.ini')
            config_parser.readfp(fp)
            ini = config_parser
            fp.close()

            for section in ini.sections():
                if section == 'updateinfo':
                    continue
                self.cache[section] = {}
                for option in ini.options(section):
                    value =  ini.get(section, option)
                    try:
                        value = int(value)
                    except:
                        try:
                          value = float(value)
                        except:
                          value = str(value)
                    self.cache[section][option] = value

        except IOError:
            raise YomboCritical("ERROR: yombo.ini doesn't exist. Use ./config to setup.", 503, "startup")
        except ConfigParser.NoSectionError:
            pass
        
        # Perform DB cleanup activites based on local section.
        if 'local' in self.cache:
            if 'deletedelayedmessages' in self.cache['local']:
                if self.cache['local']['deletedelayedmessages'].lower() == "true":
                    self._Libraries['localdb'].delete('sqldict', ['module = ?', 'yombo.gateway.lib.messages'])
                self.cache['local']['deletedelayedmessages'] = 'false'
                self.cacheDirty = True

            if 'deletedevicehistory' in self.cache['local']:
                if self.cache['local']['deletedevicehistory'].lower() == "true":
                    self._Libraries['localdb'].truncage('devicestatus')
                self.cache['local']['deletedevicehistory'] = 'false'
                self.cacheDirty = True
        if 'externalIPAddressTime' in self.cache['core']:
            if int(self.cache['core']['externalIPAddressTime']) < int(time.time()) - 12000:
              self.write("core", "externalIPAddress", getExternalIPAddress())
              self.write("core", "externalIPAddressTime", int(time.time()))
        else:
            self.write("core", "externalIPAddress", getExternalIPAddress())
            self.write("core", "externalIPAddressTime", int(time.time()))

        self.periodic_save_ini = LoopingCall(self._save_ini)
        self.periodic_save_ini.start(300, False)

    def _load_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass
  
    def _start_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
#        self._save_ini_ptr = LoopingCall(self._save_init)
#        self._save_ini_ptr.start(30)
        pass
  
    def _stop_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass

    def _unload_(self):
        """
        Save the items in the config table to yombo.ini.  This allows
        the user to see the current configuration and make any changes.
        """
        logger.debug("config stopping...Cache hits: {cacheHits}, cacheMisses: {cacheMisses}", cacheHits=self.cacheHits, cacheMisses=self.cacheMisses)  # todo: add to stats
        logger.info("saving config file...")
        self._save_ini(True)

    def _save_ini(self, force_save=False):
        """
        Save the configuration cache to the INI file.

        #Todo: convert to fdesc for non-blocking. Need example of usage.
        """
        if self.cacheDirty is True or force_save is True:
            Config = ConfigParser.ConfigParser()
            for section in self.cache:
                Config.add_section(section)
                for item in self.cache[section]:
                    Config.set(section, item, self.cache[section][item])

            configfile = open("yombo.ini",'w')
            Config.write(configfile)
            configfile.close()

    def message(self, message):
        """
        Defined to only catch messages sent to configuration on accident!

        :param message: A yombo message.
        :type message: :ref:`message`
        """
        logger.debug("A message was sent to configuration module.  No messages allowed.")

    def getConfigTime(self, section, key):
        updateItem = section + "_+_" + key + "_+_time"
        if updateItem in self.cache['updateinfo']:
            return self.cache['updateinfo'][updateItem]
        else:
            return None

    def read(self, section, key, default=None):
        """
        Read value of configuration key, return None if it don't exist or
        default if defined.  Tries to type cast with int first before
        returning a string.
        
        Section and key will be converted to lowercase, rendering the set/get
        function case insenstive.

        **Usage**:

        .. code-block:: python

           from yombo.core.helpers import getConfigValue
           gatewayUUID = getConfigValue("core", "gwuuid", "Default Value")

        :param section: The configuration section to use.
        :type section: string
        :param key: The key (or the config key) to use.
        :type key: string
        :param default: What to return if no result is found, default = None.
        :type default: int or string
        :return: The configuration value requested by section and key.
        :rtype: int or string or None
        """
        if len(key) > self.MAX_KEY:
            raise ValueError("key cannot be more than %d chars" % self.MAX_KEY)

        if section == 'yombo':
            if key in self.yombo_vars:
                return self.yombo_vars[key]
            else:
                return None

        section = section.lower()
        key = key.lower()
        if section in self.cache:
            if key in self.cache[section]:
                self.cacheHits += 1
#                returnValue(self.cache[section][key])
                return self.cache[section][key]

        self.cacheMisses += 1

        # it's not here, so, if there is a default, lets save that for future reference and return it... English much?
        if default is not None:
            if section not in self.cache:
               self.cache[section] = {}
            self.cache[section][key] = default
            return default
        else:
            return None

    def write(self, section, key, value):
        """
        Set value of configuration key for a given section.  The key length
        **cannot exceed 1000 characters**.  The value cannot exceed 5000 bytes.

        Section and key will be converted to lowercase, rending the set/get function case insenstive.

        **Usage**:

        .. code-block:: python

           from yombo.core.helpers import setConfigValue
           gatewayUUID = setConfigValue("section_name", "mykey", "New Value")

        :param section: The configuration section to use.
        :type section: string
        :param key: The key (or the config key) to use.
        :type key: string
        :param value: What to return if no result is found, default = None.
        :type value: int or string
        """
        if len(key) > self.MAX_KEY:
            raise ValueError("key (%s) cannot be more than %d chars" % (key, self.MAX_KEY) )

        # Can't set value!
        if section == 'yombo':
            raise ValueError("Not allowed to set value")

        if isinstance(value, str):
            if section != 'updateinfo' and (len(value) > self.MAX_VALUE):
                raise ValueError("value cannot be more than %d chars" %
                    self.MAX_VALUE)

        section = section.lower()
        key = key.lower()

        if section not in self.cache:
            self.cache[section] = {}
        self.cache[section][key] = value

        if 'updateinfo' not in self.cache:
            self.cache['updateinfo'] = {}

        updateItem = section + "_+_" + key + "_+_time"
        self.cache['updateinfo'][updateItem] = int( time.time() )

        updateItem = section + "_+_" + key + "_+_hash"
        self.cache['updateinfo'][updateItem] = hashlib.sha224( str(value) ).hexdigest()

        self.cacheDirty = True

    def delete(self, section, key):
        """
        Delete a section/key value from the cache and database.

        :param section: The configuration section to use.
        :type section: string
        :param key: The key (or the config key) to use.
        :type key: string
        """

        if section in self.cache:
            if key in self.cache[section]:
                del self.cache[section][key]

        if section == 'local': # don't save local items to the DB
          return
        if section in self.cache:
            if key in self.cache[section]:
                del self.cache[section][key]
