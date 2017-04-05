# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For more information see: `Commands @ command Development <https://yombo.net/docs/modules/commands/>`_

This library maintains a list of all available commands. The commands (plural) is a wrapper class and contains all
the individual command classes.

The command (singular) class represents one command.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import search_instance, do_search_instance
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

            >>> self._Commands['137ab129da9318']  #by uuid
            
        or:
        
            >>> self._Commands['living room light']  #by name

        See: :func:`yombo.core.helpers.getCommands` for full usage example.

        :param command_requested: The command UUID or command label to search for.
        :type command_requested: string
        """
        return self.get(command_requested)

    def __len__(self):
        return len(self.commands)

    def __contains__(self, command_requested):
        try:
            self.get(command_requested)
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
        self.load_deferred = None  # Prevents loader from moving on past _start_ until we are done.
        self.commands = {}
        self.__yombocommandsByVoice = {}
        self.command_search_attributes = ['command_id', 'label', 'machine_label', 'description', 'status']

    def _load_(self):
        """
        Loads all commands from DB to various arrays for quick lookup.
        """
        self.__loadCommands()
        self.load_deferred = Deferred()
        return self.load_deferred

    def _start_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass

    def _stop_(self):
        if self.load_deferred is not None and self.load_deferred.called is False:
            self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    def _clear_(self):
        """
        Clear all devices. Should only be called by the loader module
        during a reconfiguration event. B{Do not call this function!}
        """
        self.commands.clear()
        self.__yombocommandsByVoice.clear()

    def _reload_(self):
        self.__loadCommands()

    def get(self, command_requested, limiter=None, status=None):
        """
        Returns details about a command. If not loaded, will force load a command from the database.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find commands: `self._Commands['8w3h4sa']`

        :raises YomboWarning: Raised when command cannot be found.
        :param command_requested: The command ID or command label to search for.
        :type command_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the device to check for.
        :return: Pointer to requested device.
        :type status: int
        :rtype: dict
        """
        if command_requested in self.commands:
            return self.commands[command_requested]
        else:
            attrs = [
                {
                    'field': 'command_id',
                    'value': command_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'label',
                    'value': command_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'machine_label',
                    'value': command_requested,
                    'limiter': limiter,
                }
            ]
            try:
                logger.debug("Get is about to call search...: %s" % command_requested)
                # found, key, item, ratio, others = self._search(attrs, operation="highest")
                found, key, item, ratio, others = do_search_instance(attrs, self.commands,
                                                                     self.command_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest",
                                                                     status=status)
                logger.debug("found device by search: {device_id}", device_id=key)
                if found:
                    return self.commands[key]
                else:
                    raise KeyError("Command not found: %s" % command_requested)
            except YomboWarning, e:
                raise KeyError('Searched for %s, but had problems: %s' % (command_requested, e))

    def search(self, _limiter=None, _operation=None, _status=None, **kwargs):
        """
        Search for commands based on attributes for all commands.

        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the device to check for.
        :type status: int
        :param kwargs: Named params specifiy attribute name = value keypairs. 
        :return: 
        """
        return search_instance(kwargs,
                               self.commands,
                               self.command_search_attributes,
                               _limiter,
                               _operation,
                               _status)

    def get_commands_by_voice(self):
        """
        This function shouldn't be used by modules. Internal use only. For modules,
        use: `self._Commands['on']` to search by name.

        :return: Pointer to array of all devices.
        :rtype: dict
        """
        return self.__yombocommandsByVoice

    def get_local_commands(self):
        """
        Return a dictionary with all the public commands.

        :return:
        """
        results = {}
        for command_id, command in self.commands.iteritems():
            if command.public <= 1:
                results[command_id] = command
        return results

    def get_public_commands(self):
        """
        Return a dictionary with all the public commands.

        :return:
        """
        results = {}
        for command_id, command in self.commands.iteritems():
            if command.public == 2:
                results[command_id] = command
        return results

    @inlineCallbacks
    def __loadCommands(self):
        """
        Load the commands into memory. Set up various dictionaries support libraries to manage
        devices.
        """

        self._clear_()

        commands = yield self._LocalDB.get_commands()
        for command in commands:
            self._addCommand(command)
        logger.debug("Done load_commands: {commands}", commands=self.commands)
        self.load_deferred.callback(10)

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
        self.commands[cmd_id] = Command(record)
        if record.voice_cmd is not None:
            self.__yombocommandsByVoice[record.voice_cmd] = self.commands[cmd_id]
#        if testCommand:
#            return self.commands[command_id]

    @inlineCallbacks
    def dev_command_add(self, data, **kwargs):
        """
        Add a command at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        command_results = yield self._YomboAPI.request('POST', '/v1/command', data)
        # print("command edit results: %s" % command_results)

        if command_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't add command",
                'apimsg': command_results['content']['message'],
                'apimsghtml': command_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Command added.",
            'command_id': command_results['data']['id'],
        }
        returnValue(results)

    @inlineCallbacks
    def dev_command_edit(self, command_id, data, **kwargs):
        """
        Edit a command at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """

        command_results = yield self._YomboAPI.request('PATCH', '/v1/command/%s' % (command_id), data)
        # print("command edit results: %s" % command_results)

        if command_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit command",
                'apimsg': command_results['content']['message'],
                'apimsghtml': command_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Command edited.",
            'command_id': command_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_command_delete(self, command_id, **kwargs):
        """
        Delete a command at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        command_results = yield self._YomboAPI.request('DELETE', '/v1/command/%s' % command_id)

        if command_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete command",
                'apimsg': command_results['content']['message'],
                'apimsghtml': command_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Command deleted.",
            'command_id': command_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_command_enable(self, command_id, **kwargs):
        """
        Enable a command at the Yombo server level, not at the local gateway level.

        :param command_id: The command ID to enable.
        :param kwargs:
        :return:
        """
#        print "enabling command: %s" % command_id
        api_data = {
            'status': 1,
        }

        command_results = yield self._YomboAPI.request('PATCH', '/v1/command/%s' % command_id, api_data)

        if command_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't enable command",
                'apimsg': command_results['content']['message'],
                'apimsghtml': command_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Command enabled.",
            'command_id': command_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_command_disable(self, command_id, **kwargs):
        """
        Enable a command at the Yombo server level, not at the local gateway level.

        :param command_id: The command ID to disable.
        :param kwargs:
        :return:
        """
#        print "disabling command: %s" % command_id
        api_data = {
            'status': 0,
        }

        command_results = yield self._YomboAPI.request('PATCH', '/v1/command/%s' % command_id, api_data)
 #       print("disable command results: %s" % command_results)

        if command_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable command",
                'apimsg': command_results['content']['message'],
                'apimsghtml': command_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Command disabled.",
            'command_id': command_id,
        }
        returnValue(results)


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

        :cvar command_id: (string) The UUID of the command.

        :param command: A device as passed in from the devices class. This is a
            dictionary with various device attributes.
        :type command: dict

        """
        logger.debug("command info: {command}", command=command)

        self.command_id = command.id
        self.cmd = command.machine_label
        self.machine_label = command.machine_label
        self.label = command.label
        self.description = command.description
        self.voice_cmd = command.voice_cmd
        self.always_load = command.always_load
        self.public = command.public
        self.status = command.status
        self.created = command.created
        self.updated = command.updated
        self.updated_srv = None

    def __str__(self):
        """
        Print a string when printing the class.  This will return the command_id so that
        the command can be identified and referenced easily.
        """
        return self.command_id

    def dump(self):
        """
        Export command variables as a dictionary.
        """
        return {
            'command_id'   : str(self.command_id),
            'always_load'          : str(self.always_load),
            'voice_cmd'    : str(self.voice_cmd),
            'cmd'          : str(self.cmd), # AKA machineLabel
            'label'        : str(self.label),
            'machine_label': str(self.machine_label),
            'description'  : str(self.description),
            'input_type_id': int(self.input_type_id),
            'public'       : int(self.public),
            'status'       : int(self.status),
            'created'      : int(self.created),
            'updated'      : int(self.updated),
        }
