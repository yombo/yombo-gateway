# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Input Type @ Module Development <https://yombo.net/docs/modules/input_types/>`_

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
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import search_instance, do_search_instance, global_invoke_all

logger = get_logger('library.inputtypes')

class InputTypes(YomboLibrary):
    """
    Manages all input types available for input types.

    All modules already have a predefined reference to this library as
    `self._InputTypes`. All documentation will reference this use case.
    """
    def __contains__(self, input_type_requested):
        """
        .. note:: The input type must be enabled to be found using this method. Use :py:meth:`get <InputTypes.get>`
           to set status allowed.

        Checks to if a provided input type ID, label, or machine_label exists.

            >>> if '0kas02j1zss349k1' in self._InputTypes:

        or:

            >>> if 'living room light' in self._InputTypes:

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param input_type_requested: The input type id, label, or machine_label to search for.
        :type input_type_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(input_type_requested)
            return True
        except:
            return False

    def __getitem__(self, input_type_requested):
        """
        .. note:: The input type must be enabled to be found using this method. Use :py:meth:`get <InputTypes.get>`
           to set status allowed.

        Attempts to find the input type requested using a couple of methods.

            >>> input_type = self._InputTypes['0kas02j1zss349k1']  #by uuid

        or:

            >>> input_type = self._InputTypes['alpnum']  #by name

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param input_type_requested: The input type ID, label, or machine_label to search for.
        :type input_type_requested: string
        :return: A pointer to the input type type instance.
        :rtype: instance
        """
        return self.get(input_type_requested)

    def __setitem__(self, **kwargs):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, **kwargs):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        return self.input_types.__iter__()

    def __len__(self):
        """
        Returns an int of the number of input types configured.

        :return: The number of input types configured.
        :rtype: int
        """
        return len(self.input_types)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo input types library"

    def keys(self):
        """
        Returns the keys (input type ID's) that are configured.

        :return: A list of input type IDs. 
        :rtype: list
        """
        return self.input_types.keys()

    def items(self):
        """
        Gets a list of tuples representing the input types configured.

        :return: A list of tuples.
        :rtype: list
        """
        return self.input_types.items()

    def iteritems(self):
        return self.input_types.iteritems()

    def iterkeys(self):
        return self.input_types.iterkeys()

    def itervalues(self):
        return self.input_types.itervalues()

    def values(self):
        return self.input_types.values()

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
        Loads all input types from DB to various arrays for quick lookup.
        """
        self.load_deferred = Deferred()
        self._load_input_types_from_database()
        return self.load_deferred

    def _stop_(self):
        """
        Cleans up any pending deferreds.
        """
        if self.load_deferred is not None and self.load_deferred.called is False:
            self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    # @inlineCallbacks
    # def _load_input_types(self):
    #     """
    #     Load the input types into memory.
    #     """
    #     self.input_types.clear()
    #
    #     input_types = yield self._LocalDB.get_input_types()
    #     for input in input_types:
    #         self._add_input_type(input)
    #     logger.debug("Done _load_input_types: {input_types}", input_types=self.input_types)
    #     self.load_deferred.callback(10)
    #
    # def _add_input_type(self, record, testCommand=False):
    #     """
    #     Add an input type on data from a row in the SQL database.
    #
    #     :param record: Row of items from the SQLite3 database.
    #     :type record: dict
    #     :param test: If true, is a test and not from SQL, only used for unittest.
    #     :type test: bool
    #     :returns: Pointer to new input type. Only used during unittest
    #     """
    #     logger.debug("record: {record}", record=record)
    #     input_type_id = record.id
    #     self.input_types[input_type_id] = InputType(record)


    @inlineCallbacks
    def _load_input_types_from_database(self):
        """
        Loads input types from database and sends them to
        :py:meth:`import_input_types <InputTypes.import_input_types>`

        This can be triggered either on system startup or when new/updated input types have been saved to the
        database and we need to refresh existing input types.
        """
        input_types = yield self._LocalDB.get_input_types()
        logger.debug("input_types: {input_types}", input_types=input_types)
        for input_type in input_types:
            self.import_input_types(input_type)
        self.load_deferred.callback(10)

    def import_input_types(self, input_type, test_input_type=False):
        """
        Add a new input types to memory or update an existing input types.

        **Hooks called**:

        * _input_type_before_load_ : If added, sends input type dictionary as 'input_type'
        * _input_type_before_update_ : If updated, sends input type dictionary as 'input_type'
        * _input_type_loaded_ : If added, send the input type instance as 'input_type'
        * _input_type_updated_ : If updated, send the input type instance as 'input_type'

        :param input_type: A dictionary of items required to either setup a new input type or update an existing one.
        :type input: dict
        :param test_input_type: Used for unit testing.
        :type test_input_type: bool
        :returns: Pointer to new input. Only used during unittest
        """
        logger.debug("input_type: {input_type}", input_type=input_type)

        global_invoke_all('_input_types_before_import_',
                      **{'input_type': input_type})
        input_type_id = input_type["id"]
        if input_type_id not in self.input_types:
            global_invoke_all('_input_type_before_load_',
                              **{'input_type': input_type})
            self.input_types[input_type_id] = InputType(input_type)
            global_invoke_all('_input_type_loaded_',
                          **{'input_type': self.input_types[input_type_id]})
        elif input_type_id not in self.input_types:
            global_invoke_all('_input_type_before_update_',
                              **{'input_type': input_type})
            self.input_types[input_type_id].update_attributes(input_type)
            global_invoke_all('_input_type_updated_',
                          **{'input_type': self.input_types[input_type_id]})

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
           find input types:

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
                                                                     operation="highest")
                logger.debug("found input type by search: {input_type_id}", input_type_id=key)
                if found:
                    return item
                else:
                    raise KeyError("Input type not found: %s" % input_type_requested)
            except YomboWarning, e:
                raise KeyError('Searched for %s, but had problems: %s' % (input_type_requested, e))

    def search(self, _limiter=None, _operation=None, **kwargs):
        """
        Search for input type based on attributes for all input types.

        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the input type to check for.
        :return: 
        """
        return search_instance(kwargs,
                               self.input_types,
                               self.input_type_search_attributes,
                               _limiter,
                               _operation)

    @inlineCallbacks
    def dev_input_type_add(self, data, **kwargs):
        """
        Add a input_type at the Yombo server level, not at the local gateway level.

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
            'msg': "Input type added.",
            'input_type_id': input_type_results['data']['id'],
        }
        returnValue(results)

    @inlineCallbacks
    def dev_input_type_edit(self, input_type_id, data, **kwargs):
        """
        Edit a input_type at the Yombo server level, not at the local gateway level.

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
            'msg': "Input type edited.",
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
            'msg': "Input type deleted.",
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
            'msg': "Input type enabled.",
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
        # print("disable input_type results: %s" % input_type_results)

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
            'msg': "Input type disabled.",
            'input_type_id': input_type_id,
        }
        returnValue(results)


class InputType(object):
    """
    A class to manage a single input type.
    :ivar input_type_id: (string) The unique ID.
    :ivar label: (string) Human label
    :ivar machine_label: (string) A non-changable machine label.
    :ivar category_id: (string) Reference category id.
    :ivar input_regex: (string) A regex to validate if user input is valid or not.
    :ivar always_load: (int) 1 if this item is loaded at startup, otherwise 0.
    :ivar status: (int) 0 - disabled, 1 - enabled, 2 - deleted
    :ivar public: (int) 0 - private, 1 - public pending approval, 2 - public
    :ivar created: (int) EPOCH time when created
    :ivar updated: (int) EPOCH time when last updated
    """

    def __init__(self, input_type):
        """
        Setup the input type object using information passed in.

        :param input_type: An input type with all required items to create the class.
        :type input_type: dict

        """
        logger.debug("input_type info: {input_type}", input_type=input_type)

        self.input_type_id = input_type['id']
        self.machine_label = input_type['machine_label']
        self.updated_srv = None

        # below are configure in update_attributes()
        self.category_id = None
        self.label = None
        self.description = None
        self.input_regex = None
        self.always_load = None
        self.status = None
        self.public = None
        self.created = None
        self.updated = None
        self.update_attributes(input_type)

    def update_attributes(self, input_type):
        """
        Sets various values from a input type dictionary. This can be called when either new or
        when updating.

        :param input_type: 
        :return: 
        """
        self.category_id = input_type['category_id']
        self.label = input_type['label']
        self.description = input_type['description']
        self.input_regex = input_type['input_regex']
        self.always_load = input_type['always_load']
        self.status = input_type['status']
        self.public = input_type['public']
        self.created = input_type['created']
        self.updated = input_type['updated']

    def __str__(self):
        """
        Print a string when printing the class.  This will return the input type id so that
        the input type can be identified and referenced easily.
        """
        return self.input_type_id

    def __repl__(self):
        """
        Export input type variables as a dictionary.
        """
        return {
            'input_type_id': str(self.input_type_id),
            'category_id': str(self.category_id),
            'machine_label': str(self.machine_label),
            'label': str(self.label),
            'description': str(self.description),
            'input_regex': str(self.input_regex),
            'always_load': str(self.always_load),
            'public': int(self.public),
            'status': int(self.status),
            'created': int(self.created),
            'updated': int(self.updated),
        }
