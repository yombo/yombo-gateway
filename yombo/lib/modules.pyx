# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Manages all modules within the system. Provides a single reference to perform module lookup functions, etc.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2015 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
#from collections import deque
#import re
#import time

# Import twisted libraries
#from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.db import get_dbtools
from yombo.core.exceptions import YomboFuzzySearchError
from yombo.core.fuzzysearch import FuzzySearch
from yombo.core.helpers import getComponent
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger
#from yombo.core.message import Message
#from yombo.core.sqldict import SQLDict  #load at the top of the file.

logger = getLogger('library.modules')

class Modules(YomboLibrary):
    """
    A single place for modudule management and reference.
    """
    _modulesByUUID = {}
    _modulesByName = FuzzySearch({}, .92)

    _moduleDevicesByUUID = {}
    _moduleDevicesByName = FuzzySearch({}, .90)

    _moduleDeviceTypesByUUID = {}
    _moduleDeviceTypesByName = FuzzySearch({}, .92)

    _modules = {}  # Stores a list of modules. Populated by the loader module at startup.
    def _init_(self, loader):
        """
        Init doesn't do much. Just setup a few variables. Things really happen in start.
        """
        self.loader = loader
        self.dbtools = get_dbtools()

    def _load_(self):
        """
        Loads all the module information here.
        """
        pass

    def _start_(self):
        """
        Starts the library and calls self.LoadData()
        """
        self.devicesLib = getComponent('yombo.gateway.lib.devices')
        self.LoadData()


    def LoadData(self):
        """
        Load up loads of data about modules, and module devices. Makes it easy for modules to get data about what
        devices and device types they manage.
        """
#        for mdt in self.dbtools.getModuleDevice():

#            if mdt['moduleuuid'] not in self._moduleDevicesByUUID:
#                self._moduleDevicesByUUID[mdt['moduleuuid']] = []
#            self._moduleDevicesByUUID[mdt['moduleuuid']].appen(mdt)

#            if mdt['modulelabel'] not in self._moduleDevicesByName:
#                self._moduleDevicesByName[mdt['modulelabel']] = []
#            self._moduleDevicesByName[mdt['modulename']].append(mdt)

        #lets clear any data, but we have to do this carefully incase of new data...
        for module in self._moduleDeviceTypesByUUID:
            for dt in self._moduleDeviceTypesByUUID[module]:
                del self._moduleDeviceTypesByUUID[module][:]

        for module in self._moduleDeviceTypesByName:
            for dt in self._moduleDeviceTypesByName[module]:
                del self._moduleDeviceTypesByName[module][:]

        for module in self._moduleDevicesByUUID:
            for dt in self._moduleDevicesByUUID[module]:
                self._moduleDevicesByUUID[module].clear()

        for module in self._moduleDevicesByName:
            for dt in self._moduleDevicesByName[module]:
                self._moduleDevicesByName[module].clear()

        for mdt in self.dbtools.getModuleDeviceTypes():
            # Create list of DeviceType by UUID, so a module can find all it's deviceTypes
            if mdt['moduleuuid'] not in self._moduleDeviceTypesByUUID:
                self._moduleDeviceTypesByUUID[mdt['moduleuuid']] = {}
            if mdt['devicetypeuuid'] not in self._moduleDeviceTypesByUUID[mdt['moduleuuid']]:
                self._moduleDeviceTypesByUUID[mdt['moduleuuid']][mdt['devicetypeuuid']] = []
            self._moduleDeviceTypesByUUID[mdt['moduleuuid']][mdt['devicetypeuuid']].append(mdt)

            # Pointers to the above, used when searching.
            if mdt['modulelabel'] not in self._moduleDeviceTypesByName:
                self._moduleDeviceTypesByName[mdt['modulelabel']] = {}
            if mdt['devicetypeuuid'] not in self._moduleDeviceTypesByName[mdt['modulelabel']]:
                self._moduleDeviceTypesByName[mdt['modulelabel']][mdt['devicetypeuuid']] = []
            self._moduleDeviceTypesByName[mdt['modulelabel']][mdt['devicetypeuuid']].append(mdt['devicetypeuuid'])

            # Compile a list of devices for a particular module
            devices = self.devicesLib.getDevicesByDeviceType(mdt['devicetypeuuid'])
            for deviceuuid in devices:
                if mdt['moduleuuid'] not in self._moduleDevicesByUUID:
                    self._moduleDevicesByUUID[mdt['moduleuuid']] = {}
#                    if device['deviceuuid'] not in self._moduleDevicesByUUID[mdt['moduleuuid']]:
#                        self._moduleDevicesByUUID[mdt['moduleuuid']][device['label']] = {}
                self._moduleDevicesByUUID[mdt['moduleuuid']][devices[deviceuuid].deviceUUID] = devices[deviceuuid]

                if mdt['moduleuuid'] not in self._moduleDevicesByName:
                    self._moduleDevicesByName[mdt['moduleuuid']] = {}
#                    if device['label'] not in self._moduleDevicesByName[mdt['moduleuuid']]:
#                        self._moduleDevicesByName[mdt['moduleuuid']][device['label']] = {}
                self._moduleDevicesByName[mdt['moduleuuid']][devices[deviceuuid].label] = devices[deviceuuid].deviceUUID

    def _stop_(self):
        """
        Stop library - stop the looping call.
        """
        pass

    def _unload_(self):
        pass

    def addModule(self, moduleUUID, moduleLabel, modulePointer):
        self._modulesByUUID[moduleUUID] = modulePointer
        self._modulesByName[moduleLabel] = moduleUUID

    def getModule(self, requestedItem):
        """
        Attempts to find the module requested using a couple of methods. Use the already defined pointer within a
        module to find another other:



            >>> someModule = self._ModuleLibrary.getModule('137ab129da9318')  #by uuid
        or:
            >>> someModule = self._ModuleLibrary.getModule('Homevision')  #by name

        See: :func:`yombo.core.helpers.getModule` for usage example.

        :raises KeyError: Raised when module cannot be found.
        :param requestedItem: The module UUID or module name to search for.
        :type requestedItem: string
        :return: Pointer to module.
        :rtype: module
        """
        logger.trace("requestedItem: %s" % requestedItem)
        logger.trace("self._modulesByUUID: %s" % self._modulesByUUID)
        if requestedItem in self._modulesByUUID:
            return self._modulesByUUID[requestedItem]
        else:
            try:
                requestedUUID = self._modulesByName[requestedItem.lower()]
                return self._modulesByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
                raise KeyError('Module not found.')

    def getModuleDevices(self, requestedItem):
        """
        Returns all devices for a given module uuid or module name, This is used by the module library to setup a
        list of devices on startup.

            >>> getModuleDevices('137ab129da9318')  #by uuid
        or:
            >>> getModuleDevices('Homevision')  #by name

        :raises KeyError: Raised when module cannot be found.
        :param requestedItem: The module UUID or module name to search for.
        :type requestedItem: string
        :return: Pointer to module.
        :rtype: module
        """
        if requestedItem in self._moduleDevicesByUUID:
            return self._moduleDevicesByUUID[requestedItem]
        else:
            try:
                requestedUUID = self._moduleDevicesByName[requestedItem.lower()]
                return self._moduleDevicesByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
                raise KeyError('Module not found, looking for devices.')

    def getModuleDeviceTypes(self, requestedItem):
        """
        Returns all device types for a given module uuid or module name, This is used by the module library to setup a
        list of device types on startup.

            >>> getModuleDeviceTypes('137ab129da9318')  #by uuid
        or:
            >>> getModuleDeviceTypes('Homevision')  #by name

        :raises KeyError: Raised when module cannot be found.
        :param requestedItem: The module UUID or module name to search for.
        :type requestedItem: string
        :return: Pointer to module.
        :rtype: module
        """
        logger.trace("requestedItem: %s" % requestedItem)
        logger.trace("self._moduleDeviceTypesByUUID: %s" % self._moduleDeviceTypesByUUID)
        if requestedItem in self._moduleDeviceTypesByUUID:
            return self._moduleDeviceTypesByUUID[requestedItem]
        else:
            try:
                logger.trace("self._moduleDeviceTypesByName: %s" % self._moduleDeviceTypesByName)
                requestedUUID = self._moduleDeviceTypesByName[requestedItem.lower()]
                return self._moduleDeviceTypesByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
                raise KeyError('Module not found, looking for device types.')
