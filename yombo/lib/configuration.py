# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
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
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""

import ConfigParser
import hashlib
import time

from yombo.core.db import get_dbconnection
from yombo.core.exceptions import GWCritical
from yombo.core.helpers import getExternalIPAddress
from yombo.core.log import getLogger
from yombo.core.library import YomboLibrary

logger = getLogger('library.configuration')

yombomasterdb = None

class Configuration(YomboLibrary):
    """
    Configuration storage module for the gateway service.

    This class manages the yombo.ini file.  It reads this file on startup and
    stores the configuration items into the config table of the database. When
    the gateway shuts down, it replaces the yombo.ini file with the current
    configuration set.  This makes it possible for end users to make changes,
    if needed; however this should be rare.
    """

    MAX_KEY = 100
    MAX_VALUE = 5001

    def init(self, loader):
        """
        Open the yombo.ini file for reading.

        Import the configuration items into the database, also prime the cache for reading.

        :param loader: The loader module.
        :type loader: loader
        """
        self.cache = {}  # simple database cache.
        self.cacheMisses = 0
        self.cacheHits = 0
        
        self.loader = loader
        
        self.dbpool = get_dbconnection()
        self.cursor = self.dbpool.cursor()

        config_parser = ConfigParser.SafeConfigParser()


        try:
            fp = open('yombo.ini')
            config_parser.readfp(fp)
            ini = config_parser
            fp.close()

            # check if "deletedbconfigs" is in the local section - remove configs from db
            if ini.has_section('local') and ini.has_option('local', 'deletedbconfigs'):
                if ini.get('local', 'deletedbconfigs').lower() == "true":
                    self.cursor.execute("DELETE FROM config")
                    ini.get('local', 'deletedbconfigs', "false")
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
                    updateItem = section + "_+_" + option + "_+_hash"
                    hashValue = ""

                    # check hash in the DB, if not there or not match, update
                    theValue = self.readDB(section, option)
                    if theValue != False:
                        hashValue = hashlib.sha224( str(theValue) ).hexdigest()
                        try:
                            # compare hash, if same, then check time.
                            if hashValue == ini.get('updateinfo', updateItem):
                                updateItem = section + "_+_" + option + "_+_time"
                                theValue = self.readDB('updateinfo', updateItem)

                                #last place with higher time wins.
                                if theValue != False:
                                    if ini.get('updateinfo', updateItem) < theValue:
                                        self.cache[section][option] = value
                                        continue
                        except:
                            pass
                    # if here, then hash doesn't match and time in .ini is newer        
                    self.write(section, option, value)
            self.dbpool.commit()
        except IOError:
            raise GWCritical("ERROR: yombo.ini doesn't exist. Use ./config to setup.", 503, "startup")
        except ConfigParser.NoSectionError:
            pass
        
        # Perform DB cleanup activites based on local section.
        if 'local' in self.cache:
            if 'deletedelayedmessages' in self.cache['local']:
                if self.cache['local']['deletedelayedmessages'].lower() == "true":
                    self.cursor.execute("DELETE FROM sqldict WHERE module='yombo.gateway.lib.messages'")
                self.write('local', 'deletedelayedmessages', 'false')
            if 'deletedevicehistory' in self.cache['local']:
                if self.cache['local']['deletedevicehistory'].lower() == "true":
                    self.cursor.execute("DELETE FROM devicestatus")
                self.write('local', 'deletedevicehistory', 'false')

        lastTime = self.read("core", "externalIPAddressTime", 1000)
        if int(lastTime) < int(time.time()) - 12000:
          self.write("core", "externalIPAddress", getExternalIPAddress())
          self.write("core", "externalIPAddressTime", int(time.time()))
          
    def load(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass
  
    def start(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass
  
    def stop(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass

    def unload(self):
        """
        Save the items in the config table to yombo.ini.  This allows
        the user to see the current configuration and make any changes.
        """
        logger.trace("config stopping...Cache hits: %d, cacheMisses: %d", self.cacheHits, self.cacheMisses)
        logger.info("saving config file...")
        
        Config = ConfigParser.ConfigParser()

        for section in self.cache:
            Config.add_section(section)
            for item in self.cache[section]:
                Config.set(section, item, self.cache[section][item])

        configfile = open("yombo.ini",'w')
        Config.write(configfile)

        # Now, lets delete all the configuration items from the database.
        # This way the user can edit the yombo.ini file, which includes
        # deleting entries.
        # The DB is used to make sure configurations are persisted if the
        # gateway is terminated unexpectedly. The yombo.ini will be
        # updated on the next successful termination.
        # DB calls are faster the writing entire files on each config update.
        self.cursor.execute("DELETE FROM config")
        self.dbpool.commit()

    def message(self, message):
        """
        Defined to only catch messages sent to configuration on accident!

        :param message: A yombo message.
        :type message: :ref:`message`
        """
        logger.warning("A message was sent to configuration module.  No messages allowed.")

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
        
        Section and key will be converted to lowercase, rending the set/get function case insenstive.

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

        section = section.lower()
        key = key.lower()

        if section in self.cache:
            if key in self.cache[section]:
                self.cacheHits += 1
                return self.cache[section][key]
        
        self.cacheMisses += 1
        output = self.readDB(section, key)

        if output == False:
            return default

        if section not in self.cache:
            self.cache[section] = {}
        self.cache[section][key] = output
        return output

    def readDB(self, section, key):
        c = self.dbpool.cursor()
        c.execute("select configValue from config where configPath='%s' AND configKey='%s'" % (section, key))
        row = c.fetchone()
        output = None
        if row:
            input = row[0]
            try:
                output = int(input)
            except:
                try:
                  output = float(input)
                except:
                  output = str(input)
            return output
        return False

    def write(self, section, key, value):
        """
        Set value of configuration key for a given section.  The key length
        **cannot exceed 1000 characters**.  The value cannot exceed 5000 bytes.

        Section and key will be converted to lowercase, rending the set/get function case insenstive.

        :param section: The configuration section to use.
        :type section: string
        :param key: The key (or the config key) to use.
        :type key: string
        :param value: What to return if no result is found, default = None.
        :type value: int or string
        """
        if len(key) > self.MAX_KEY:
            raise ValueError("key (%s) cannot be more than %d chars" % (key, self.MAX_KEY) )
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


        c = self.dbpool.cursor()
        if section != 'local': # don't save local items to the DB
            c.execute("select configid from config where configPath='%s' AND configKey='%s'" % (section, key))
            row = c.fetchone()

            if row:
                configid = row[0]
                c.execute("""
                    update config set configValue=?, updated=? where configPath=? AND configId=?;""", (value, int(time.time()), section, configid) )
            else:
                c.execute("""
                    replace into config (configPath, configKey, configValue, updated)
                    values  (?, ?, ?, ?);""", (section, key, value, int(time.time())) )

        updateItem = section + "_+_" + key + "_+_time"
        self.cache['updateinfo'][updateItem] = int( time.time() )

        c.execute("select configid from config where configPath='updateinfo' AND configKey='%s'" % (updateItem))
        row = c.fetchone()

        if row:
            configid = row[0]
            c.execute("""
                update config set configValue=?, updated=? where configPath=? AND configId=?;""", (self.cache['updateinfo'][updateItem], int(time.time()), 'updateinfo', updateItem) )
        else:
            c.execute("""
                replace into config (configPath, configKey, configValue, updated)
                values  (?, ?, ?, ?);""", ('updateinfo', updateItem, self.cache['updateinfo'][updateItem], int(time.time())) )

        updateItem = section + "_+_" + key + "_+_hash"
        self.cache['updateinfo'][updateItem] = hashlib.sha224( str(value) ).hexdigest()

        c.execute("select configid from config where configPath='updateinfo' AND configKey='%s'" % (updateItem))
        row = c.fetchone()

        if row:
            configid = row[0]
            c.execute("""
                update config set configValue=?, updated=? where configPath=? AND configId=?;""", (self.cache['updateinfo'][updateItem], int(time.time()), 'updateinfo', updateItem) )
        else:
            c.execute("""
                replace into config (configPath, configKey, configValue, updated)
                values  (?, ?, ?, ?);""", ('updateinfo', updateItem, self.cache['updateinfo'][updateItem], int(time.time())) )

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

        c = self.dbpool.cursor()
        c.execute("DELETE FROM config WHERE  configPath='%s' AND configKey='%s'" % (section, key))
