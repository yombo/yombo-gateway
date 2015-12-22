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
    _moduleDevicesByName = FuzzySearch({}, .92)

    _moduleDeviceRouting = {}
    _moduleDeviceRoutingByName = FuzzySearch({}, .95)

    _moduleDeviceTypesByUUID = {}
    _moduleDeviceTypesByName = FuzzySearch({}, .92)

    _deviceTypeRoutingByType = {}
    _modules = {}  # Stores a list of modules. Populated by the loader module at startup.

    def _init_(self, loader):
        """
        Init doesn't do much. Just setup a few variables. Things really happen in start.
        """
        self.loader = loader
        self._DBTools = get_dbtools()

    def _load_(self):
        """
        Loads all the module information here.
        """
        pass

    def _start_(self):
        """
        Starts the library and calls self.LoadData()
        """
        self._devicesLib = getComponent('yombo.gateway.lib.devices')
        self.loadData()

    def loadData(self):
        """
        Load up loads of data about modules, and module devices. Makes it easy for modules to get data about what
        devices and device types they manage.
        """
#        for mdt in self._DBTools.getModuleDevice():

#            if mdt['moduleuuid'] not in self._moduleDevicesByUUID:
#                self._moduleDevicesByUUID[mdt['moduleuuid']] = []
#            self._moduleDevicesByUUID[mdt['moduleuuid']].appen(mdt)

#            if mdt['modulelabel'] not in self._moduleDevicesByName:
#                self._moduleDevicesByName[mdt['modulelabel']] = []
#            self._moduleDevicesByName[mdt['modulename']].append(mdt)

        #lets clear any data, but we have to do this carefully incase of new data...
        for module in self._moduleDeviceTypesByUUID:
            del self._moduleDeviceTypesByUUID[module][:]

        for module in self._moduleDeviceTypesByName:
            del self._moduleDeviceTypesByName[module][:]

        for module in self._moduleDevicesByUUID:
            self._moduleDevicesByUUID[module].clear()

        for module in self._moduleDevicesByName:
            self._moduleDevicesByName[module].clear()

        self._moduleDeviceRouting.clear()

        for mdt in self._DBTools.getModuleRouting():
            # Create list of DeviceType by UUID, so a module can find all it's deviceTypes
            if mdt['moduleuuid'] not in self._moduleDeviceTypesByUUID:
                self._moduleDeviceTypesByUUID[mdt['moduleuuid']] = {}
            if mdt['devicetypeuuid'] not in self._moduleDeviceTypesByUUID[mdt['moduleuuid']]:
                self._moduleDeviceTypesByUUID[mdt['moduleuuid']][mdt['devicetypeuuid']] = []
            self._moduleDeviceTypesByUUID[mdt['moduleuuid']][mdt['devicetypeuuid']].append(mdt)
            # Pointers to the above, used when searching.
            if mdt['modulelabel'] not in self._moduleDeviceTypesByName:
                self._moduleDeviceTypesByName[mdt['modulelabel']] = FuzzySearch({}, .92)
            if mdt['devicetypeuuid'] not in self._moduleDeviceTypesByName[mdt['modulelabel']]:
                self._moduleDeviceTypesByName[mdt['modulelabel'].lower()][mdt['devicetypeuuid']] = []
            self._moduleDeviceTypesByName[mdt['modulelabel'].lower()][mdt['devicetypeuuid']].append(mdt['devicetypeuuid'])

            # How to route device types - It's here to detere what module to send to from existing modules
            if mdt['devicetypeuuid'] not in self._moduleDeviceRouting:
                self._moduleDeviceRouting[mdt['devicetypeuuid']] = {}
            self._moduleDeviceRouting[mdt['devicetypeuuid']][mdt['moduletype']] = {
                'moduleUUID' : mdt['moduleuuid'],
                'moduleLabel' : mdt['modulelabel'],
                }
            # Pointers to the above, used when searching.
            if mdt['devicetypelabel'] not in self._moduleDeviceRoutingByName:
                self._moduleDeviceRoutingByName[mdt['devicetypelabel'].lower()] = FuzzySearch({}, .92)
            self._moduleDeviceRoutingByName[mdt['devicetypelabel'].lower()][mdt['moduletype']] = {
                'moduleUUID' : mdt['moduleuuid'],
                'moduleLabel' : mdt['modulelabel'],
                }

            # Compile a list of devices for a particular module
            devices = self._devicesLib.getDevicesByDeviceType(mdt['devicetypeuuid'])
            logger.debug("devices = {devices}", devices=devices)
            for deviceuuid in devices:
                logger.debug("Adding deviceUUID({deviceUUID} to self._moduleDevicesByUUID.", deviceUUID=devices[deviceuuid].deviceUUID)
                if mdt['moduleuuid'] not in self._moduleDevicesByUUID:
                    self._moduleDevicesByUUID[mdt['moduleuuid']] = {}
#                    if device['deviceuuid'] not in self._moduleDevicesByUUID[mdt['moduleuuid']]:
#                        self._moduleDevicesByUUID[mdt['moduleuuid']][device['label']] = {}
                logger.debug("Adding deviceUUID({deviceUUID} to self._moduleDevicesByUUID.", deviceUUID=devices[deviceuuid].deviceUUID)
                self._moduleDevicesByUUID[mdt['moduleuuid']][devices[deviceuuid].deviceUUID] = devices[deviceuuid]

                if mdt['moduleuuid'] not in self._moduleDevicesByName:
                    self._moduleDevicesByName[mdt['moduleuuid']] = FuzzySearch({}, .92)
#                    if device['label'] not in self._moduleDevicesByName[mdt['moduleuuid']]:
#                        self._moduleDevicesByName[mdt['moduleuuid']][device['label']] = {}
                self._moduleDevicesByName[mdt['moduleuuid']][devices[deviceuuid].label] = devices[deviceuuid].deviceUUID

            # For routing messages to modules
            if mdt['devicetypeuuid'] not in self._deviceTypeRoutingByType:
                self._deviceTypeRoutingByType[mdt['devicetypeuuid']] = {}
            self._deviceTypeRoutingByType[mdt['devicetypeuuid']][mdt['moduletype']] = mdt['modulelabel']
#            self._deviceTypeRouting[mdt['devicetypeuuid']].append([mdt['moduletype']] = mdt['modulelabel']

        logger.debug("self._moduleDeviceTypesByUUID = {moduleDeviceTypesByUUID}", moduleDeviceTypesByUUID=self._moduleDeviceTypesByUUID)
        logger.debug("self._moduleDeviceTypesByName = {moduleDeviceTypesByName}", moduleDeviceTypesByName=self._moduleDeviceTypesByName)
        logger.debug("self._moduleDeviceRouting = {moduleDeviceRouting}", moduleDeviceRouting=self._moduleDeviceRouting)
        logger.debug("self._moduleDeviceRoutingByName = {moduleDeviceRoutingByName}", moduleDeviceRoutingByName=self._moduleDeviceRoutingByName)

#        logger.info("self._moduleDeviceTypesByUUID: %s" % self._moduleDeviceTypesByUUID)

    def _stop_(self):
        """
        Stop library - stop the looping call.
        """
        pass

    def _unload_(self):
        pass

    def addModule(self, moduleUUID, moduleLabel, modulePointer):
        logger.debug("adding module: {moduleUUID}:{moduleLabel}", moduleUUID=moduleUUID, moduleLabel=moduleLabel)
        self._modulesByUUID[moduleUUID] = modulePointer
        self._modulesByName[moduleLabel] = moduleUUID

    def delModule(self, moduleUUID):
        del self._modulesByName[self._modulesByUUID[moduleUUID]._FullName]
        del self._modulesByUUID[moduleUUID]

    def getModule(self, requestedItem):
        """
        Attempts to find the module requested using a couple of methods. Use the already defined pointer within a
        module to find another other:

            >>> someModule = self._ModulesLibrary.getModule('137ab129da9318')  #by uuid
        or:
            >>> someModule = self._ModulesLibrary.getModule('Homevision')  #by name

        See: :func:`yombo.core.helpers.getModule` for usage example.

        :raises KeyError: Raised when module cannot be found.
        :param requestedItem: The module UUID or module name to search for.
        :type requestedItem: string
        :return: Pointer to module.
        :rtype: module
        """
        logger.debug("Looking for {requestedItem} in {modulesByUUID}", requestedItem=requestedItem, modulesByUUID=self._modulesByUUID)
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

            >>> devices = self._ModulesLibrary.getModuleDevices('137ab129da9318')  #by uuid
        or:
            >>> devices = self._ModulesLibrary.getModuleDevices('Homevision')  #by name

        :raises KeyError: Raised when module cannot be found.
        :param requestedItem: The module UUID or module name to search for.
        :type requestedItem: string
        :return: Pointer to module.
        :rtype: module
        """
        logger.debug("getModuleDevices::requestedItem: {requestedItem}", requestedItem=requestedItem)
        logger.debug("getModuleDevices::_moduleDevicesByUUID: {moduleDevicesByUUID}", moduleDevicesByUUID=self._moduleDevicesByUUID)
        if requestedItem in self._moduleDevicesByUUID:
            return self._moduleDevicesByUUID[requestedItem]
        else:
            try:
                requestedUUID = self._moduleDevicesByName[requestedItem.lower()]
                return self._moduleDevicesByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
                return {} # no devices setup for a requested module.

    def getModuleDeviceTypes(self, requestedItem):
        """
        Returns all device types for a given module uuid or module name, This is used by the module library to setup a
        list of device types on startup.

            >>> deviceTypes = self._ModulesLibrary.getModuleDeviceTypes('137ab129da9318')  #by uuid
        or:
            >>> deviceTypes = self._ModulesLibrary.getModuleDeviceTypes('Homevision')  #by name

        :raises KeyError: Raised when module cannot be found.
        :param requestedItem: The module UUID or module name to search for.
        :type requestedItem: string
        :return: Pointer to module.
        :rtype: module
        """
        logger.debug("getModuleDeviceTypes::requestedItem: {requestedItem}", requestedItem=requestedItem)
        logger.debug("getModuleDeviceTypes::_moduleDeviceTypesByUUID: {moduleDeviceTypesByUUID}", moduleDeviceTypesByUUID=self._moduleDeviceTypesByUUID)
        if requestedItem in self._moduleDeviceTypesByUUID:
            return self._moduleDeviceTypesByUUID[requestedItem]
        else:
            try:
                logger.debug("self._moduleDeviceTypesByName: {moduleDeviceTypesByName}", moduleDeviceTypesByName=self._moduleDeviceTypesByName)
                requestedUUID = self._moduleDeviceTypesByName[requestedItem.lower()]
                return self._moduleDeviceTypesByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
                logger.debug("No module found for a given device type {deviceType}", deviceType=requestedItem)
                return {}

    def getDeviceRouting(self, requestedItem, moduleType, returnType = 'moduleUUID'):
        """
        Device routing is used by the gateway to route a device command to the correct module. For example, a
        Z-Wave applicance module should be routed to the Z-Wave command module. From there, it needs to be routed
        to the Z-Wave interface module (the interface module is what bridges the command module to the outside world
        such as though a USB/Serial/Network interface).

        This function allows you to get the ``moduleUUID``, ``moduleLabel`` or a pointer to the ``module`` itself.

            >>> moduleUUID = self._ModulesLibrary.getDeviceRouting('137ab129da9318', 'Interface', 'module')  #by uuid, get the actual module pointer
        or:
            >>> deviceTypes = self._ModulesLibrary.getDeviceRouting('X10 Appliance', 'Command', 'moduleUUID')  #by name, get the moduleUUID
        or:
            >>> moduleUUID = self._ModulesLibrary.getDeviceRouting('137ab129da9318', 'Interface', 'moduleLabel')  #by uuid. get the moduleLabel

        :raises KeyError: Raised when module cannot be found.
        :param requestedItem: The module UUID or module name to search for.
        :type requestedItem: string
        :param moduleType: The module type to return. One of: Command, Interface, Logic, Other
        :type moduleType: string
        :param returnType: What type of string to return. One of: moduleUUID, moduleLabel, module
        :type returnType: string
        :return: Pointer to module.
        :rtype: module or string
        """
#        logger.debug("getModuleDeviceTypes::requestedItem: {requestedItem}", requestedItem=requestedItem)
#        logger.debug("getModuleDeviceTypes::_moduleDeviceTypesByUUID: {moduleDeviceTypesByUUID}", moduleDeviceTypesByUUID=self._moduleDeviceTypesByUUID)
        temp = None
        if requestedItem in self._moduleDeviceRouting:
            temp = self._moduleDeviceRouting[requestedItem]
        else:
            try:
                temp = self._moduleDeviceRoutingByName[requestedItem.lower()]
            except YomboFuzzySearchError, e:
                logger.debug("No route for {requestedItem}", requestedItem=requestedItem)
                return None

        if moduleType == "Command":
            if 'Command' in temp:
                temp = temp['Command']
            elif 'Interface' in temp:
                temp = temp['Interface']
            elif 'Logic' in temp:
                temp = temp['Logic']
            elif 'Other' in temp:
                temp = temp['Other']
        elif moduleType == "Interface":
             if 'Interface' in temp:
                temp = temp['Interface']
             elif 'Logic' in temp:
                temp = temp['Logic']
             elif 'Other' in temp:
                temp = temp['Other']
        elif moduleType == "Logic":
            if 'Logic' in temp:
                temp = temp['Logic']
            elif 'Other' in temp:
                temp = temp['Other']
        elif moduleType == "Other":
            if 'Other' in temp:
                temp = temp['Other']

        logger.debug("temp2 = {temp2}", temp2=temp)
        logger.debug("returnValue = {returnType}", returnType=returnType)

        if returnType in ("moduleUUID", "moduleLabel"):
            if temp is not None:
                return temp[returnType]
        elif returnType is 'module':
            if temp is not None:
                return self.getModule(temp['moduleUUID'])
        return None

