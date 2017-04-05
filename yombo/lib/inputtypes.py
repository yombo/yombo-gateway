# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Input Types @ Projects.yombo.net <https://projects.yombo.net/projects/modules/wiki/Input_Types>`_

This library maintains a list of all available input types. The input types (plural) is a wrapper class and contains all
the individual input type classes.

The input type (singular) class represents one input type.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue

# Import Yombo libraries
from yombo.core.exceptions import YomboFuzzySearchError, YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils.fuzzysearch import FuzzySearch
from yombo.utils import search_instance, do_search_instance

logger = get_logger('library.inputtypes')

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

            >>> input_type = self._InputTypes['137ab129da9318']  #by uuid
            
        or:
        
            >>> input_type = self._InputTypes['alpnum']  #by name

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
        """
        self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.
        self.input_types = {}
        self.input_type_search_attributes = ['input_type_id', 'category_id', 'label', 'machine_label', 'description',
            'status', 'always_load', 'public']

    def _load_(self):
        """
        Loads all commands from DB to various arrays for quick lookup.
        """
        self._load_input_types()
        self.load_deferred = Deferred()
        return self.load_deferred

    def _stop_(self):
        if self.load_deferred is not None and self.load_deferred.called is False:
            self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    def _reload_(self):
        self.__load_input_types()


    def get_all(self):
        """
        Returns a copy of the input types list.
        :return:
        """
        return self.input_types.copy()

    def get(self, input_type_requested, limiter=None, status=None):
        """
        Performs the actual search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find devices:

            >>> self._InputTypes['13ase45']

        or:

            >>> self._InputTypes['numeric']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param input_type_requested: The input type ID or input type label to search for.
        :type input_type_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the input type to check for.
        :type status: int
        :return: Pointer to requested input type.
        :rtype: dict
        """
        if limiter is None:
            limiter = .89

        if limiter > .99999999:
            limiter = .99
        elif limiter < .10:
            limiter = .10

        if status is None:
            status = 1

        if input_type_requested in self.input_types:
            item = self.input_types[input_type_requested]
            if item.status != status:
                raise KeyError("Requested input type found, but has invalid status: %s" % item.status)
            return item
        else:
            attrs = [
                {
                    'field': 'input_type_id',
                    'value': input_type_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'label',
                    'value': input_type_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'machine_label',
                    'value': input_type_requested,
                    'limiter': limiter,
                }
            ]
            try:
                logger.debug("Get is about to call search...: %s" % input_type_requested)
                # found, key, item, ratio, others = self._search(attrs, operation="highest")
                found, key, item, ratio, others = do_search_instance(attrs, self.input_types,
                                                                     self.input_type_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest",
                                                                     status=status)
                logger.debug("found input type by search: {input_type_id}", input_type_id=key)
                if found:
                    return item
                else:
                    raise KeyError("Command not found: %s" % input_type_requested)
            except YomboWarning, e:
                raise KeyError('Searched for %s, but had problems: %s' % (input_type_requested, e))

    def search(self, _limiter=None, _operation=None, _status=None, **kwargs):
        """
        Search for input type based on attributes for all input types.

        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the input type to check for.
        :type status: int
        :param kwargs: Named params specifiy attribute name = value keypairs. 
        :return: 
        """
        return search_instance(kwargs,
                               self.input_types,
                               self.input_type_search_attributes,
                               _limiter,
                               _operation,
                               _status)

    @inlineCallbacks
    def _load_input_types(self):
        """
        Load the input types into memory.
        """
        self.input_types.clear()

        input_types = yield self._LocalDB.get_input_types()
        for input in input_types:
            self._add_input_type(input)
        logger.debug("Done _load_input_types: {input_types}", input_types=self.input_types)
        self.load_deferred.callback(10)

    def _add_input_type(self, record, testCommand = False):
        """
        Add an input type on data from a row in the SQL database.

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :param test: If true, is a test and not from SQL, only used for unittest.
        :type test: bool
        :returns: Pointer to new input type. Only used during unittest
        """
        logger.debug("record: {record}", record=record)
        input_type_id = record.id
        self.input_types[input_type_id] = InputType(record)
#        if testCommand:
#            return self.__yombocommands[command_id]

    @inlineCallbacks
    def dev_input_type_add(self, data, **kwargs):
        """
        Add a module at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        input_type_results = yield self._YomboAPI.request('POST', '/v1/input_type', data)
        # print("dt_results: %s" % input_type_results)

        if input_type_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't add input type",
                'apimsg': input_type_results['content']['message'],
                'apimsghtml': input_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Device type added.",
            'input_type_id': input_type_results['data']['id'],
        }
        returnValue(results)

    @inlineCallbacks
    def dev_input_type_edit(self, input_type_id, data, **kwargs):
        """
        Edit a module at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """

        input_type_results = yield self._YomboAPI.request('PATCH', '/v1/input_type/%s' % (input_type_id), data)
        # print("module edit results: %s" % module_results)

        if input_type_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit input type",
                'apimsg': input_type_results['content']['message'],
                'apimsghtml': input_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Device type edited.",
            'input_type_id': input_type_results['data']['id'],
        }
        returnValue(results)

    @inlineCallbacks
    def dev_input_type_delete(self, input_type_id, **kwargs):
        """
        Delete a input_type at the Yombo server level, not at the local gateway level.

        :param input_type_id: The input_type ID to delete.
        :param kwargs:
        :return:
        """
        input_type_results = yield self._YomboAPI.request('DELETE', '/v1/input_type/%s' % input_type_id)

        if input_type_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete input type",
                'apimsg': input_type_results['content']['message'],
                'apimsghtml': input_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Command deleted.",
            'input_type_id': input_type_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_input_type_enable(self, input_type_id, **kwargs):
        """
        Enable a input_type at the Yombo server level, not at the local gateway level.

        :param input_type_id: The input_type ID to enable.
        :param kwargs:
        :return:
        """
        #        print "enabling input_type: %s" % input_type_id
        api_data = {
            'status': 1,
        }

        input_type_results = yield self._YomboAPI.request('PATCH', '/v1/input_type/%s' % input_type_id, api_data)

        if input_type_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't enable input type",
                'apimsg': input_type_results['content']['message'],
                'apimsghtml': input_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Command enabled.",
            'input_type_id': input_type_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_input_type_disable(self, input_type_id, **kwargs):
        """
        Enable a input_type at the Yombo server level, not at the local gateway level.

        :param input_type_id: The input_type ID to disable.
        :param kwargs:
        :return:
        """
#        print "disabling input_type: %s" % input_type_id
        api_data = {
            'status': 0,
        }

        input_type_results = yield self._YomboAPI.request('PATCH', '/v1/input_type/%s' % input_type_id, api_data)
 #       print("disable input_type results: %s" % input_type_results)

        if input_type_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable input_type",
                'apimsg': input_type_results['content']['message'],
                'apimsghtml': input_type_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Command disabled.",
            'input_type_id': input_type_id,
        }
        returnValue(results)


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
        logger.debug("input_type info: {input_type}", input_type=input_type)

        self.input_type_id = input_type.id
        self.category_id = input_type.category_id
        self.machine_label = input_type.machine_label
        self.label = input_type.label
        self.description = input_type.description
        self.input_regex = input_type.input_regex
        self.always_load = input_type.always_load
        self.status = input_type.status
        self.public = input_type.public
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
            'category_id'          : str(self.category_id),
            'machine_label': str(self.machine_label),
            'label'        : str(self.label),
            'description'  : str(self.encryption),
            'input_regex': str(self.input_regex),
            'always_load'  : str(self.always_load),
            'public'       : int(self.public),
            'status'       : int(self.status),
            'created'      : int(self.created),
            'updated'      : int(self.updated),
        }
