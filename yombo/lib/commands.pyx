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
from yombo.core.exceptions import FuzzySearchError, CommandError
from yombo.core.library import YomboLibrary
from yombo.core.log import getLogger

logger = getLogger('library.commands')

class Commands(YomboLibrary):
    """
    Manages all commands available for devices.  Most common functions:
    * getCommands - Get a pointer to all devices.
    * search - Get a pointer to a command, using cmdUUID or command label.
    """
    def __getitem__(self, key):
        """
        Simulate a dictionary when requested with::
            >>> commands['137ab129da9318]  #by uuid
        or::
            >>> commands['living room light']  #by name

        :param key: The search key/token to look for a command with.
        :type key: string
        """
        return self.search(key)

    def init(self, loader):
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
        
    def load(self):
        """
        Loads all commands from DB to various arrays for quick lookup.
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
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass

    def clear(self):
        """
        Clear all devices. Should only be called by the loader module
        during a reconfiguration event. B{Do not call this function!}
        """
        self.__yombocommands.clear()
        self.__yombocommandsByName.clear()
        self.__yombocommandsByVoice.clear()

    def reload(self):
        self.__loadCommands()

    def getCommands(self):
        """
        Return a pointer to all commands.

        **Usage**:

        .. code-block:: python

           from yombo.core.helpers import getCommands
           commands = getCommands()
           onCmd = commands['on'] #fuzzy search match

        :return: Pointer to array of all devices.
        :rtype: dict
        """
        return self.__yombocommands

    def getCommandsByVoice(self):
        """
        Return a pointer to all commands with Voice as the key. Uses fuzzysearch to find the voice verb.

        **Usage**:

        .. code-block:: python

           from yombo.core.helpers import getCommandsByVoice
           commands = getCommands()
           onCmd = commands['on'] #fuzzy search match

        :return: Pointer to array of all devices.
        :rtype: dict
        """
        return self.__yombocommandsByVoice

    def search(self, commandRequested):
        """
        Attempts to find the command requested using a couple of methods.
        
        First, it checks if this is a cmdUUID and does a lookup. If that fails
        it performs a fuzzy search looking for a matching name. This module requires
        command B{matches to be at least 92%}.  This can be overridden by
        L{searchaccuracycommand<searchaccuracycommand>}.

        **Usage**:

        .. code-block:: python

           from yombo.core.helpers import getCommands
           commands = getCommands()
           onCmd = commands.search('on') #fuzzy search match

        :raises CommandError: Raised when device cannot be found.
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
            except FuzzySearchError, e:
                raise CommandError('Searched for %s, but no good matches found.' % e.searchFor, key=e.key, value=e.value, ratio=e.ratio, others=e.others)

    def __loadCommands(self):
        """
        Load the commands into memory. Set up various dictionaries support libraries to manage
        devices.
        """
        import itertools

        logger.info("Loading commands!")
        self.clear()

        c = self.__dbpool.cursor()
        c.execute("SELECT * FROM commands")
        row = c.fetchone()
        if row == None:
            return None
        field_names = [d[0].lower() for d in c.description]
        while row is not None:
            record = (dict(itertools.izip(field_names, row)))
#            logger.trace("record: %s", record)
            cmdUUID = record["cmduuid"]
            self.__yombocommands[cmdUUID] = Command(record)
            self.__yombocommandsByName[record["label"]] = self.__yombocommands[cmdUUID]
            if len(record["voicecmd"]) >= 2:
              self.__yombocommandsByVoice[record["voicecmd"]] = self.__yombocommands[cmdUUID]
            row = c.fetchone()
#        logger.debug("Done load_commands: %s", self.__yombodevicesByType)

class Command:
    """
    A class to manage a single command.2

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

        self.cmdUUID = command["cmduuid"]

        self.label = command["label"]
        """:ivar: Command label - as defined by the server.
        :type: string"""

        self.description = command["description"]
        """@ivar: The description of the command.
        @type: C{string}"""

        self.cmd = command["cmd"]
        """@ivar: The cmd itself..
        @type: C{string}"""

        self.inputTypeID = command["inputtypeid"]
        """@ivar: The type of input that is required as a variable.
        @type: C{string}"""

        self.voiceCmd = command["voicecmd"]
        """@ivar: The voice command of the command.
        @type: C{string}"""

    def __str__(self):
        """
        Print a string when printing the class.  This will return the cmdUUID so that
        the command can be identified and referenced easily.
        """
        return self.cmdUUID

