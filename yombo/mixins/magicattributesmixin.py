# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For library documentation, see: `Devices @ Module Development <https://yombo.net/docs/libraries/users>`_

Mixin class to add various Yombo library references.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.23.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""


class MagicAttributesMixin(object):

    def __init__(self, parent, *args, **kwargs):
        libraries = parent._Loader.loadedLibraries
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
        self._Libraries = parent._Loader
        self._Loader = libraries["loader"]
        self._Localize = libraries["localize"]
        self._LocalDB = libraries["localdb"]  # Provided for testing
        self._Locations = libraries["locations"]  # Basically, all devices
        self._Modules = parent._Loader._moduleLibrary
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
