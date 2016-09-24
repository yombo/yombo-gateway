"""
.. rst-class:: floater

.. note::

  For more information see: `Input Types @ Projects.yombo.net <https://projects.yombo.net/projects/modules/wiki/Input_Types>`_

This library maintains a list of all available input types. The input types (plural) is a wrapper class and contains all
the individual input type classes.

The input type (singular) class represents one input type.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

.. versionadded:: 0.12.0

:copyright: Copyright 2016 by Yombo.
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

class InputTypes(YomboLibrary):
    """
    Manages all input types available for commands.

    All modules already have a predefined reference to this library as
    `self._InputTypes`. All documentation will reference this use case.
    """
    def __getitem__(self, input_type_requested):
        """
        Return an input type, searching first by input type ID and then by input type machine label.
        Modules should use `self._InputTypes` to search with:

            >>> self._InputTypes['137ab129da9318]  #by uuid
        or::
            >>> self._InputTypes['living room light']  #by name

        :param input_type_requested: The input type ID or input type machine label to search for.
        :type input_type_requested: string
        """
        return self.get(input_type_requested)

    def __len__(self):
        return len(self.input_types)

    def __contains__(self, input_type_requested):
        try:
            self.get(input_type_requested)
            return True
        except:
            return False

    def _init_(self):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        :param loader: A pointer to the L{Loader<yombo.lib.loader.Loader>}
        library.
        :type loader: Instance of Loader
        """
        self.input_types = {}
        self.input_types_by_name = FuzzySearch(None, .92)
        self._LocalDB = self._Libraries['localdb']

    def _load_(self):
        """
        Loads all commands from DB to various arrays for quick lookup.
        """
        self._load_input_types()
        self.loadDefer = Deferred()
        return self.loadDefer

    def _start_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass

    def _clear_(self):
        """
        Clear all devices. Should only be called by the loader module
        during a reconfiguration event. B{Do not call this function!}
        """
        self.input_types.clear()
        self.input_types_by_name.clear()

    def _reload_(self):
        self.__load_input_types()


    def get_all(self):
        """
        Returns a copy of the input types list.
        :return:
        """
        return self.input_types.copy()

    def get(self, input_type_requested):
        """
        Performs the actual command search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find commands: `self._Commands['8w3h4sa']`

        :raises YomboWarning: Raised when command cannot be found.
        :param input_type_requested: The input type ID or input type label to search for.
        :type input_type_requested: string
        :return: A dict containing details about the input type
        :rtype: dict
        """
        if input_type_requested in self.input_types:
            return self.input_types[input_type_requested]
        else:
            try:
                return self.input_types_by_name[input_type_requested]
            except YomboFuzzySearchError, e:
                raise YomboWarning('Searched for %s, but no good matches found.' % e.searchFor)

    @inlineCallbacks
    def _load_input_types(self):
        """
        Load the input types into memory.
        """
        self._clear_()

        input_types = yield self._LocalDB.get_input_types()
        for input in input_types:
            self._add_input_type(input)
        logger.debug("Done _load_input_types: {input_types}", input_types=self.input_types)
        self.loadDefer.callback(10)

    def _add_input_type(self, record, testCommand = False):
        """
        Add an input type on data from a row in the SQL database.

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :param test: If true, is a test and not from SQL, only used for unittest.
        :type test: bool
        :returns: Pointer to new device. Only used during unittest
        """
        logger.debug("record: {record}", record=record)
        input_type_id = record.id
        self.input_types[input_type_id] = InputType(record)
        self.input_types_by_name[record.label] = self.input_types_by_name[input_type_id]
#        if testCommand:
#            return self.__yombocommands[command_id]


class InputType:
    """
    A class to manage a single input type.
    :ivar label: Command label
    :ivar description: The description of the command.
    :ivar inputTypeID: The type of input that is required as a variable.
    :ivar voice_cmd: The voice command of the command.
    """

    def __init__(self, input_type):
        """
        Setup the input type object using information passed in.

        :cvar input_type_id: (string) The UUID of the command.

        :param command: A device as passed in from the devices class. This is a
            dictionary with various device attributes.
        :type command: dict

        """
        logger.info("command info: {command}", command=command)

        self.input_type_id = input_type.id
        self.uri = input_type.uri
        self.label = input_type.label
        self.machine_label = input_type.machine_label
        self.description = input_type.description
        self.category = input_type.category
        self.public = input_type.public
        self.status = input_type.status
        self.created = input_type.created
        self.updated = input_type.updated
        self.updated_srv = None

    def __str__(self):
        """
        Print a string when printing the class.  This will return the command_id so that
        the command can be identified and referenced easily.
        """
        return self.input_type_id

    def dump(self):
        """
        Export command variables as a dictionary.
        """
        return {
            'input_type_id': str(self.input_type_id),
            'uri'          : str(self.uri),
            'label'        : str(self.label),
            'machine_label': str(self.machine_label),
            'description'  : str(self.description),
            'category'     : str(self.category),
            'public'       : int(self.public),
            'status'       : int(self.status),
            'created'      : int(self.created),
            'updated'      : int(self.updated),
        }
