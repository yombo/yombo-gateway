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


class Entity(object):
    """
    All classes should inherit this class first. This setups some
    """
    @property
    def gateway_id(self):
        return self._Loader.gateway_id

    @gateway_id.setter
    def gateway_id(self, val):
        return

    @property
    def is_master(self):
        return self._Loader.is_master

    @is_master.setter
    def is_master(self, val):
        return

    @property
    def master_gateway_id(self):
        return self._Loader.master_gateway_id

    @master_gateway_id.setter
    def master_gateway_id(self, val):
        return

    def __init__(self, parent, *args, **kwargs):
        self._Entity_type = None
        self._Parent = parent
        if "_dont_call_entity_init" not in kwargs:
            self._entity_init_()
        else:
            if kwargs["_dont_call_entity_init"] is not True:
                self._entity_init_()
            del kwargs["_dont_call_entity_init"]
        super().__init__(*args, **kwargs)

    def _entity_init_(self):
        libraries = self._Parent._Loader.loadedLibraries
        self._AMQP = libraries["amqp"]
        self._AMQPYombo = libraries["amqpyombo"]
        self._Atoms = libraries["atoms"]
        self._AuthKeys = libraries["authkeys"]
        self._Automation = libraries["automation"]
        self._Cache = libraries["cache"]
        self._Calllater = libraries["calllater"]
        self._Commands = libraries["commands"]
        self._Configs = libraries["configuration"]
        self._CronTab = libraries["crontab"]
        self._Devices = libraries["devices"]  # Basically, all devices
        self._DeviceCommands = libraries["devicecommands"]  # Basically, all devices
        self._DeviceCommandInputs = libraries["devicecommandinputs"]  # Basically, all devices
        self._DeviceTypeCommands = libraries["devicetypes"]  # All device types.
        self._DeviceTypes = libraries["devicetypes"]  # All device types.
        self._Discovery = libraries["discovery"]
        self._DownloadModules = libraries["downloadmodules"]
        self._Events = libraries["events"]
        self._Gateways = libraries["gateways"]
        self._GatewayComs = libraries["gateways_communications"]
        self._GPG = libraries["gpg"]
        self._InputTypes = libraries["inputtypes"]  # Input Types
        self._Intents = libraries["intents"]
        self._Hash = libraries["hash"]  # Input Types
        self._HashIDS = libraries["hashids"]
        self._Libraries = libraries
        self._Loader = self._Parent._Loader
        self._Localize = libraries["localize"]
        self._LocalDB = libraries["localdb"]  # Provided for testing
        self._Locations = libraries["locations"]  # Basically, all devices
        self._Modules = libraries["modules"]
        self._ModuleDeviceTypes = libraries["moduledevicetypes"]
        self._MQTT = libraries["mqtt"]
        self._Nodes = libraries["nodes"]
        self._Notifications = libraries["notifications"]
        self._Queue = libraries["queue"]
        self._Requests = libraries["requests"]
        self._Scenes = libraries["scenes"]
        self._SQLDict = libraries["sqldict"]
        self._SSLCerts = libraries["sslcerts"]
        self._States = libraries["states"]
        self._Statistics = libraries["statistics"]
        self._Storage = libraries["storage"]
        self._Tasks = libraries["tasks"]
        self._Template = libraries["template"]
        self._Times = libraries["times"]
        self._Users = libraries["users"]
        self._YomboAPI = libraries["yomboapi"]
        self._Variables = libraries["variables"]
        self._Validate = libraries["validate"]
        self._WebInterface = libraries["webinterface"]
        self._WebSessions = libraries["websessions"]
