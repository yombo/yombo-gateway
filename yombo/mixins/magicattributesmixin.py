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
        self._AMQP = parent._Loader.loadedLibraries['amqp']
        self._AMQPYombo = parent._Loader.loadedLibraries['amqpyombo']
        self._Atoms = parent._Loader.loadedLibraries['atoms']
        self._AuthKeys = parent._Loader.loadedLibraries['authkeys']
        self._Automation = parent._Loader.loadedLibraries['automation']
        self._Commands = parent._Loader.loadedLibraries['commands']
        self._Configs = parent._Loader.loadedLibraries['configuration']
        self._CronTab = parent._Loader.loadedLibraries['crontab']
        self._Devices = parent._Loader.loadedLibraries['devices']  # Basically, all devices
        self._DeviceTypes = parent._Loader.loadedLibraries['devicetypes']  # All device types.
        self._Discovery = parent._Loader.loadedLibraries['discovery']
        self._Events = parent._Loader.loadedLibraries['events']
        self._Gateways = parent._Loader.loadedLibraries['gateways']
        self._GatewayComs = parent._Loader.loadedLibraries['gateways_communications']
        self._GPG = parent._Loader.loadedLibraries['gpg']
        self._InputTypes = parent._Loader.loadedLibraries['inputtypes']  # Input Types
        self._Intents = parent._Loader.loadedLibraries['intents']
        self._Hash = parent._Loader.loadedLibraries['hash']  # Input Types
        self._HashIDS = parent._Loader.loadedLibraries['hashids']
        self._Libraries = parent._Loader.loadedLibraries
        self._Localize = parent._Loader.loadedLibraries['localize']
        self._LocalDB = parent._Loader.loadedLibraries['localdb']  # Provided for testing
        self._Locations = parent._Loader.loadedLibraries['locations']  # Basically, all devices
        self._Modules = parent._Loader._moduleLibrary
        self._MQTT = parent._Loader.loadedLibraries['mqtt']
        self._Nodes = parent._Loader.loadedLibraries['nodes']
        self._Notifications = parent._Loader.loadedLibraries['notifications']
        self._Queue = parent._Loader.loadedLibraries['queue']
        self._Requests = parent._Loader.loadedLibraries['requests']
        self._Scenes = parent._Loader.loadedLibraries['scenes']
        self._SQLDict = parent._Loader.loadedLibraries['sqldict']
        self._SSLCerts = parent._Loader.loadedLibraries['sslcerts']
        self._States = parent._Loader.loadedLibraries['states']
        self._Statistics = parent._Loader.loadedLibraries['statistics']
        self._Tasks = parent._Loader.loadedLibraries['tasks']
        self._Template = parent._Loader.loadedLibraries['template']
        self._Times = parent._Loader.loadedLibraries['times']
        self._Users = parent._Loader.loadedLibraries['users']
        self._YomboAPI = parent._Loader.loadedLibraries['yomboapi']
        self._Variables = parent._Loader.loadedLibraries['variables']
        self._Validate = parent._Loader.loadedLibraries['validate']
        self._WebSessions = parent._Loader.loadedLibraries['websessions']
