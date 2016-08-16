# cython: embedsignature=True
# This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
.. rst-class:: floater

.. note::

  For more information see: `Commands @ Projects.yombo.net <https://projects.yombo.net/projects/modules/wiki/Commands>`_

This library maintains a list of all available commands. The commands (plural) is a wrapper class and contains all
the individual command classes.

The command (singular) class represents one command.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred

# Import Yombo libraries
from yombo.core.exceptions import YomboFuzzySearchError, YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils.fuzzysearch import FuzzySearch

logger = get_logger('library.commands')

class Commands(YomboLibrary):
    """
    Manages all commands available for devices.

    All modules already have a predefined reference to this library as
    `self._Commands`. All documentation will reference this use case.
    """
    def __getitem__(self, command_requested):
        """
        Return a command, searching first by command UUID and then by command
        function (on, off, bright, dim, open, close, etc).  Modules should use
        `self._Commands` to search with:

            >>> self._Commands['137ab129da9318]  #by uuid
        or::
            >>> self._Commands['living room light']  #by name

        See: :func:`yombo.core.helpers.getCommands` for full usage example.

        :param command_requested: The command UUID or command label to search for.
        :type command_requested: string
        """
        return self.get_command(command_requested)

    def __len__(self):
        return len(self.__yombocommands)

    def __contains__(self, command_requested):
        try:
            self.get_command(command_requested)
            return True
        except:
            return False

    def _init_(self, loader):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        :param loader: A pointer to the L{Loader<yombo.lib.loader.Loader>}
        library.
        :type loader: Instance of Loader
        """
        self.loader = loader

        self.__yombocommands = {}
        self.__yombocommandsByName = FuzzySearch(None, .92)
        self.__yombocommandsByVoice = FuzzySearch(None, .92)
        self.local_db = self._Libraries['localdb']

    def _load_(self):
        """
        Loads all commands from DB to various arrays for quick lookup.
        """
        pass 

    def _start_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        self.__loadCommands()
        self.loadDefer = Deferred()
        return self.loadDefer

    def _clear_(self):
        """
        Clear all devices. Should only be called by the loader module
        during a reconfiguration event. B{Do not call this function!}
        """
        self.__yombocommands.clear()
        self.__yombocommandsByName.clear()
        self.__yombocommandsByVoice.clear()

    def _reload_(self):
        self.__loadCommands()

    def _get_commands_by_voice(self):
        """
        This function shouldn't be used by modules. Internal use only. For modules,
        use: `self._Commands['on']` to search by name.

        :return: Pointer to array of all devices.
        :rtype: dict
        """
        return self.__yombocommandsByVoice

    def get_command(self, command_requested):
        """
        Performs the actual command search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find commands: `self._Commands['8w3h4sa']`

        :raises YomboWarning: Raised when command cannot be found.
        :param command_requested: The command ID or command label to search for.
        :type command_requested: string
        :return: Pointer to array of all command.
        :rtype: dict
        """
        if command_requested in self.__yombocommands:
            return self.__yombocommands[command_requested]
        else:
            try:
                return self.__yombocommandsByName[command_requested]
            except YomboFuzzySearchError, e:
                raise YomboWarning('Searched for %s, but no good matches found.' % e.searchFor)

    @inlineCallbacks
    def __loadCommands(self):
        """
        Load the commands into memory. Set up various dictionaries support libraries to manage
        devices.
        """

        self._clear_()

        commands = yield self.local_db.get_commands()
        for command in commands:
            self._addCommand(command)
        logger.debug("Done load_commands: {yombocommands}", yombocommands=self.__yombocommands)
        self.loadDefer.callback(10)
#        print self.__yombocommandsByName

    def _addCommand(self, record, testCommand = False):
        """
        Add a command based on data from a row in the SQL database.

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :param testCommand: If true, is a test command not from SQL, only used for unittest.
        :type testCommand: bool
        :returns: Pointer to new device. Only used during unittest
        """
        logger.debug("record: {record}", record=record)
        cmd_id = record.id
        self.__yombocommands[cmd_id] = Command(record)
        self.__yombocommandsByName[record.label] = self.__yombocommands[cmd_id]
        if record.voice_cmd is not None:
            self.__yombocommandsByVoice[record.voice_cmd] = self.__yombocommands[cmd_id]
#        if testCommand:
#            return self.__yombocommands[cmdUUID]


class Command:
    """
    A class to manage a single command.
    :ivar label: Command label
    :ivar description: The description of the command.
    :ivar inputTypeID: The type of input that is required as a variable.
    :ivar voice_cmd: The voice command of the command.
    """

    def __init__(self, command):
        """
        Setup the command object using information passed in.

        :cvar cmdUUID: (string) The UUID of the command.

        :param command: A device as passed in from the devices class. This is a
            dictionary with various device attributes.
        :type command: dict

        """
        logger.debug("command info: {command}", command=command)

        self.cmdUUID = command.id
        self.uri = command.uri
        self.voice_cmd = command.voice_cmd
        self.cmd = command.machine_label
        self.label = command.label
        self.description = command.description
        self.input_type_id = command.input_type_id
        self.live_update = command.live_update
        self.public = command.public
        self.status = command.status
        self.created = command.created
        self.updated = command.updated

    def __str__(self):
        """
        Print a string when printing the class.  This will return the cmdUUID so that
        the command can be identified and referenced easily.
        """
        return self.cmdUUID

    def dump(self):
        """
        Export command variables as a dictionary.
        """
        return {
            'cmdUUID'       : str(self.cmdUUID),
            'uri'           : str(self.uri),
            'voice_cmd'      : str(self.voice_cmd),
            'cmd'           : str(self.cmd), # AKA machineLabel
            'label'         : str(self.label),
            'description'   : str(self.description),
            'input_type_id' : int(self.input_type_id),
            'live_update' : int(self.live_update),
            'public'        : int(self.public),
            'status'        : int(self.status),
            'created'       : int(self.created),
            'updated'       : int(self.updated),
        }
