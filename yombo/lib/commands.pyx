# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
Class to maintain list of all available commands. Initially, this
is a cache with the ability and intention to expand later.

The commands (plural) class is a wrapper class and contains all
the individual commands as individual classes.  The commands class
is responsible for loading all the commands and assigning them to
an individual command class.

The command (singular) class represents one command.

The private online repository can be used to recover previous command
usage statistics.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""
from yombo.core.db import get_dbconnection
from yombo.core.fuzzysearch import FuzzySearch
from yombo.core.exceptions import YomboFuzzySearchError, YomboCommandError
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger

logger = getLogger('library.commands')

class Commands(YomboLibrary):
    """
    Manages all commands available for devices.

    All modules already have a predefined reference to this library as
    `self._Commands`. All documentation will reference this use case.
    """
    def __getitem__(self, commandRequested):
        """
        Return a command, searching first by command UUID and then by command
        function (on, off, bright, dim, open, close, etc).  Modules should use
        `self._Commands` to search with:

            >>> self._Commands['137ab129da9318]  #by uuid
        or::
            >>> self._Commands['living room light']  #by name

        See: :func:`yombo.core.helpers.getCommands` for full usage example.

        :param commandRequested: The command UUID or command label to search for.
        :type commandRequested: string
        """
        return self._search(commandRequested)

    def _init_(self, loader):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        :param loader: A pointer to the L{Loader<yombo.lib.loader.Loader>}
        library.
        :type loader: Instance of Loader
        """
        self.loader = loader
        self.__dbpool = get_dbconnection()

        self.__yombocommands = {}
        self.__yombocommandsByName = FuzzySearch(None, .92)
        self.__yombocommandsByVoice = FuzzySearch(None, .92)

        self.__loadCommands()
        
    def _load_(self):
        """
        Loads all commands from DB to various arrays for quick lookup.
        """
        pass 

    def _start_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass

    def _stop_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass

    def _unload_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass

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

    def getCommandsByVoice(self):
        """
        This function shouldn't be used by modules. Internal use only. For modules,
        use: `self._Commands['on']` to search by name.


        **Usage**:

        .. code-block:: python

           from yombo.core.helpers import getCommandsByVoice
           commands = getCommands()
           onCmd = commands['on'] #fuzzy search match

        :return: Pointer to array of all devices.
        :rtype: dict
        """
        return self.__yombocommandsByVoice

    def _search(self, commandRequested):
        """
        Performs the actual command search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find commands: `self._Commands['8w3h4sa']`

        See: :func:`yombo.core.helpers.getCommands` for full usage example.

        :raises YomboCommandError: Raised when device cannot be found.
        :param commandRequested: The device UUID or device label to search for.
        :type commandRequested: string
        :return: Pointer to array of all devices.
        :rtype: dict
        """
        if commandRequested in self.__yombocommands:
            return self.__yombocommands[commandRequested]
        else:
            try:
                return self.__yombocommandsByName[commandRequested]
            except YomboFuzzySearchError, e:
                raise YomboCommandError('Searched for %s, but no good matches found.' % e.searchFor)

    def __loadCommands(self):
        """
        Load the commands into memory. Set up various dictionaries support libraries to manage
        devices.
        """
        import itertools

        logger.info("Loading commands!")
        self._clear_()

        c = self.__dbpool.cursor()
        c.execute("SELECT * FROM commands")
        row = c.fetchone()
        if row == None:
            return None
        field_names = [d[0].lower() for d in c.description]
        while row is not None:
            record = (dict(itertools.izip(field_names, row)))
            self._addCommand(record)
            row = c.fetchone()
        logger.trace("Done load_commands: %s", self.__yombocommands)

    def _addCommand(self, record, testCommand = False):
        """
        Add a command based on data from a row in the SQL database.

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :param testCommand: If true, is a test command not from SQL, only used for unittest.
        :type testCommand: bool
        :returns: Pointer to new device. Only used during unittest
        """
        cmdUUID = record["cmduuid"]
        self.__yombocommands[cmdUUID] = Command(record)
        self.__yombocommandsByName[record["label"]] = self.__yombocommands[cmdUUID]
        if len(record["voicecmd"]) >= 2:
            self.__yombocommandsByVoice[record["voicecmd"]] = self.__yombocommands[cmdUUID]
        if testCommand:
            return self.__yombocommands[cmdUUID]


class Command:
    """
    A class to manage a single command.
    :ivar label: Command label
    :ivar description: The description of the command.
    :ivar inputTypeID: The type of input that is required as a variable.
    :ivar voiceCmd: The voice command of the command.
    """

    def __init__(self, command):
        """
        Setup the command object using information passed in.

        :cvar cmdUUID: (string) The UUID of the command.

        :param command: A device as passed in from the devices class. This is a
            dictionary with various device attributes.
        :type command: dict

        """
        logger.trace("command info: %s", command)

        self.cmd = command["machineLabel"]
        self.cmdUUID = command["cmdUUID"]
        self.label = command["label"]
        self.description = command["description"]
#        self.inputTypeID = command["inputtypeid"]
        self.voiceCmd = command["voiceCmd"]
        self.uri = command["uri"]
#        self.liveUpdate = command["liveupdate"]

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
        return {'cmdUUID'     : str(self.cmdUUID),
                'cmd'         : str(self.cmd),
                'label'       : str(self.label),
                'description' : str(self.description),
#                'inputTypeID' : int(self.inputTypeID),
                'voiceCmd'    : str(self.voiceCmd),
#                'liveUpdate'  : int(self.liveUpdate),
               }