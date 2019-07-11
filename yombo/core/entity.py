#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Entity Core @ Module Development <https://yombo.net/docs/core/entity>`_


Used by all classes to show various information about any Yombo related class.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/entity.html>`_
"""

from os import getcwd
import sys


class Entity:
    """All classes should inherit this class first. This setups basic attributes that are helpfull to all classes."""
    _Root = None

    @classmethod
    def _Configure_Entity_Class_Do_Not_Call_Me_By_My_Name_(cls):
        cls._AMQP = cls._Root.loaded_libraries["amqp"]
        cls._AMQPYombo = cls._Root.loaded_libraries["amqpyombo"]
        cls._Atoms = cls._Root.loaded_libraries["atoms"]
        cls._AuthKeys = cls._Root.loaded_libraries["authkeys"]
        cls._Automation = cls._Root.loaded_libraries["automation"]
        cls._Cache = cls._Root.loaded_libraries["cache"]
        cls._Calllater = cls._Root.loaded_libraries["calllater"]
        cls._Commands = cls._Root.loaded_libraries["commands"]
        cls._Configs = cls._Root.loaded_libraries["configuration"]
        cls._CronTab = cls._Root.loaded_libraries["crontab"]
        cls._Devices = cls._Root.loaded_libraries["devices"]  # Basically, all devices
        cls._DeviceCommands = cls._Root.loaded_libraries["devicecommands"]  # Basically, all devices
        cls._DeviceCommandInputs = cls._Root.loaded_libraries["devicecommandinputs"]  # Basically, all devices
        cls._DeviceTypeCommands = cls._Root.loaded_libraries["devicetypes"]  # All device types.
        cls._DeviceTypes = cls._Root.loaded_libraries["devicetypes"]  # All device types.
        cls._Discovery = cls._Root.loaded_libraries["discovery"]
        cls._DownloadModules = cls._Root.loaded_libraries["downloadmodules"]
        cls._Events = cls._Root.loaded_libraries["events"]
        cls._Gateways = cls._Root.loaded_libraries["gateways"]
        cls._GatewayComs = cls._Root.loaded_libraries["gatewayscommunications"]
        cls._GPG = cls._Root.loaded_libraries["gpg"]
        cls._InputTypes = cls._Root.loaded_libraries["inputtypes"]  # Input Types
        cls._Intents = cls._Root.loaded_libraries["intents"]
        cls._Hash = cls._Root.loaded_libraries["hash"]  # Input Types
        cls._HashIDS = cls._Root.loaded_libraries["hashids"]
        cls._Loader = cls._Root
        cls._Localize = cls._Root.loaded_libraries["localize"]
        cls._LocalDB = cls._Root.loaded_libraries["localdb"]  # Provided for testing
        cls._Locations = cls._Root.loaded_libraries["locations"]  # Basically, all devices
        cls._Modules = cls._Root.loaded_libraries["modules"]
        cls._ModuleDeviceTypes = cls._Root.loaded_libraries["moduledevicetypes"]
        cls._MQTT = cls._Root.loaded_libraries["mqtt"]
        cls._Nodes = cls._Root.loaded_libraries["nodes"]
        cls._Notifications = cls._Root.loaded_libraries["notifications"]
        cls._Queue = cls._Root.loaded_libraries["queue"]
        cls._Requests = cls._Root.loaded_libraries["requests"]
        cls._Scenes = cls._Root.loaded_libraries["scenes"]
        cls._SQLDict = cls._Root.loaded_libraries["sqldict"]
        cls._SSLCerts = cls._Root.loaded_libraries["sslcerts"]
        cls._States = cls._Root.loaded_libraries["states"]
        cls._Statistics = cls._Root.loaded_libraries["statistics"]
        cls._Storage = cls._Root.loaded_libraries["storage"]
        cls._Tasks = cls._Root.loaded_libraries["tasks"]
        cls._Template = cls._Root.loaded_libraries["template"]
        cls._Times = cls._Root.loaded_libraries["times"]
        cls._Users = cls._Root.loaded_libraries["users"]
        cls._YomboAPI = cls._Root.loaded_libraries["yomboapi"]
        cls._VariableData = cls._Root.loaded_libraries["variabledata"]
        cls._VariableFields = cls._Root.loaded_libraries["variablefields"]
        cls._VariableGroups = cls._Root.loaded_libraries["variablegroups"]
        cls._Validate = cls._Root.loaded_libraries["validate"]
        cls._WebInterface = cls._Root.loaded_libraries["webinterface"]
        cls._WebSessions = cls._Root.loaded_libraries["websessions"]

        # cls.gateway_id = cls._Root.gateway_id
        # cls.is_master = cls._Root.is_master
        # cls.master_gateway_id = cls._Root.master_gateway_id

    @property
    def gateway_id(self):
        return self._Root.gateway_id

    @gateway_id.setter
    def gateway_id(self, val):
        return

    @property
    def is_master(self):
        return self._Root.is_master

    @is_master.setter
    def is_master(self, val):
        return

    @property
    def master_gateway_id(self):
        return self._Root.master_gateway_id

    @property
    def _app_dir(self):
        return self._Atoms.get('app_dir')

    @property
    def _app_dir(self):
        return self._Atoms.get('working_dir')

    def __init__(self, parent, *args, **kwargs):
        if hasattr(self, "_Entity_type") is False:
            self._Entity_type = f"unknown-{self.__class__.__name__}"

        try:  # Some exceptions not being caught & displayed. So, catch, display and release.
            self._Name = self.__class__.__name__
            file = sys.modules[self.__class__.__module__].__file__
            self._ClassPath = file[len(getcwd())+1:].split(".")[0].replace("/", ".")
            self._FullName = f"{self._ClassPath}:{self._Name}"
            self._Parent = parent
            super().__init__(*args, **kwargs)
        except Exception as e:
            print(f"YomboLibrary caught init exception: {e}")
            raise e

        # self._app_dir = self._Atoms.get('app_dir')

    # def __str__(self):
    #     """
    #     Returns the name of the entity and it's full name.
    #
    #     :return: Type of entity and it's full name.
    #     :rtype: string
    #     """
    #     return f"{self._Entity_type} - {self._Name}"
    #
    # def __repr__(self):
    #     """
    #     Returns the name of the entity and it's full name.
    #
    #     :return: Type of entity and it's full name.
    #     :rtype: string
    #     """
    #     return f"{self._Entity_type} - {self._FullName}"
