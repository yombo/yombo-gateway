# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Nodes @ Module Development <https://yombo.net/docs/modules/nodes/>`_

Nodes store generic information and are used to store information that doesn't need specific database needs.

**Besure to double check if the function being used returns a deferred. Only meta data for the node
is loaded into memory, the actual node data remains in the database.**

Nodes differ from SQLDict in that Nodes can be managed by the Yombo API, while SQLDict is only used
for local data.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import search_instance, do_search_instance, global_invoke_all

logger = get_logger('library.nodes')

class Nodes(YomboLibrary):
    """
    Manages nodes for a gateway.
    """
    def __contains__(self, node_requested):
        """
        .. note:: The node must be enabled to be found using this method.

        Checks to if a provided node ID or machine_label exists.

            >>> if '0kas02j1zss349k1' in self._Nodes:

        or:

            >>> if 'some_node_name' in self._Nodes:

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param node_requested: The node id or machine_label to search for.
        :type node_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get_meta(node_requested)
            return True
        except:
            return False

    def __getitem__(self, node_requested):
        """
        .. note:: The node must be enabled to be found using this method.

        Attempts to find the device requested using a couple of methods.

            >>> node = self._Nodes['0kas02j1zss349k1']  #by uuid

        or:

            >>> node = self._Nodes['alpnum']  #by name

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param node_requested: The node ID or machine_label to search for.
        :type node_requested: string
        :return: A pointer to the device type instance.
        :rtype: instance
        """
        return self.get_meta(node_requested)

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
        """ iter device types. """
        return self.device_types.__iter__()

    def __len__(self):
        """
        Returns an int of the number of device types configured.

        :return: The number of nodes configured.
        :rtype: int
        """
        return len(self.nodes)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return self.nodes.__str__()

    def keys(self):
        """
        Returns the keys (device type ID's) that are configured.

        :return: A list of device type IDs. 
        :rtype: list
        """
        return self.nodes.keys()

    def items(self):
        """
        Gets a list of tuples representing the device types configured.

        :return: A list of tuples.
        :rtype: list
        """
        return self.nodes.items()

    def iteritems(self):
        return self.nodes.iteritems()

    def iterkeys(self):
        return self.nodes.iterkeys()

    def itervalues(self):
        return self.nodes.itervalues()

    def values(self):
        return self.nodes.values()

    def _init_(self):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.
        self.nodes = {}
        self.node_search_attributes = ['node_id', 'gateway_id', 'node_type', 'machine_label', 'destination',
            'data_type', 'status']
        self.load_deferred = Deferred()
        self._load_nodes_from_database()
        return self.load_deferred

    # def _load_(self):
    #     """
    #     Loads all nodes from DB to various arrays for quick lookup.
    #     """

    def _stop_(self):
        """
        Cleans up any pending deferreds.
        """
        if self.load_deferred is not None and self.load_deferred.called is False:
            self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    @inlineCallbacks
    def _load_nodes_from_database(self):
        """
        Loads nodes from database and sends them to
        :py:meth:`import_node <Nodes.import_node>`

        This can be triggered either on system startup or when new/updated nodes have been saved to the
        database and we need to refresh existing nodes.
        """
        nodes = yield self._LocalDB.get_nodes()
        for node in nodes:
            self.import_node(node)
        self.load_deferred.callback(10)

    def import_node(self, node, test_node=False):
        """
        Add a new nodes to memory or update an existing nodes.

        **Hooks called**:

        * _node_before_load_ : If added, sends node dictionary as 'node'
        * _node_before_update_ : If updated, sends node dictionary as 'node'
        * _node_loaded_ : If added, send the node instance as 'node'
        * _node_updated_ : If updated, send the node instance as 'node'

        :param node: A dictionary of items required to either setup a new node or update an existing one.
        :type input: dict
        :param test_node: Used for unit testing.
        :type test_node: bool
        :returns: Pointer to new input. Only used during unittest
        """
        logger.debug("node: {node}", node=node)

        global_invoke_all('_nodes_before_import_',
                      **{'node': node})
        node_id = node["id"]
        if node_id not in self.nodes:
            global_invoke_all('_node_before_load_',
                              **{'node': node})
            self.nodes[node_id] = Node(node)
            global_invoke_all('_node_loaded_',
                          **{'node': self.nodes[node_id]})
        elif node_id not in self.nodes:
            global_invoke_all('_node_before_update_',
                              **{'node': node})
            self.nodes[node_id].update_attributes(node)
            global_invoke_all('_node_updated_',
                          **{'node': self.nodes[node_id]})

    def get_all(self):
        """
        Returns a copy of the nodes list.
        :return:
        """
        return self.nodes.copy()

    def get_meta(self, node_requested, node_type=None, limiter=None, status=None):
        """
        Performs the actual search.

        .. note::

           Can use the built in methods below or use get_meta/get to include 'node_type' limiter:

            >>> self._Nodes['13ase45']

        or:

            >>> self._Nodes['numeric']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param node_requested: The node ID or node label to search for.
        :type node_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the node to check for.
        :type status: int
        :return: Pointer to requested node.
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

        if node_requested in self.nodes:
            item = self.nodes[node_requested]
            if item.status != status:
                raise KeyError("Requested node found, but has invalid status: %s" % item.status)
            return item
        else:
            attrs = [
                {
                    'field': 'node_id',
                    'value': node_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'machine_label',
                    'value': node_requested,
                    'limiter': limiter,
                }
            ]
            try:
                # logger.debug("Get is about to call search...: %s" % node_requested)
                # found, key, item, ratio, others = self._search(attrs, operation="highest")
                found, key, item, ratio, others = do_search_instance(attrs, self.nodes,
                                                                     self.node_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest")
                # logger.debug("found node by search: others: {others}", others=others)
                if node_type is not None:
                    for other in others:
                        # print "other: %s" % other
                        if other['value'].node_type == node_type and other['ratio'] > limiter:
                            return other['value']
                else:
                    if found:
                        return item
                raise KeyError("Node not found: %s" % node_requested)
            except YomboWarning as e:
                raise KeyError('Searched for %s, but had problems: %s' % (node_requested, e))

    @inlineCallbacks
    def get(self, node_requested, node_type=None, limiter=None, status=None):
        """
        Returns a deferred! LIke get_meta, but returns a dictionaryPerforms the actual search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find devices:

            >>> self._Nodes['13ase45']

        or:

            >>> self._Nodes['numeric']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param node_requested: The node ID or node label to search for.
        :type node_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the node to check for.
        :type status: int
        :return: Pointer to requested node.
        :rtype: dict
        """
        try:
            node = self.get_meta(node_requested, node_type, limiter, status)
        except Exception as e:
            logger.warn("Unable to find requested node: {node}.  Reason: {e}", node=node_requested, e=e)
            raise YomboWarning("Cannot find requested node...")

        try:
            data = yield self._LocalDB.get_node(node.node_id)
            returnValue(data)
        except YomboWarning as e:
            raise KeyError('Cannot find node (%s) in database: %s' % (node_requested, e))

    @inlineCallbacks
    def get_parent(self, node_requested, limiter=None):
        """
        Returns a deferred! Gets the parent of a provided node.

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param node_requested: The node ID or node label to search for.
        :type node_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :return: Pointer to requested node.
        :rtype: dict
        """
        try:
            node = self.get_meta(node_requested, limiter=limiter)
        except Exception as e:
            logger.warn("Unable to find requested node: {node}.  Reason: {e}", node=node_requested, e=e)
            raise YomboWarning()

        if node.parent_id in self.nodes:
            item = self.nodes[node.parent_id]
            data = yield self._LocalDB.get_node(item.node_id)
            returnValue(data)
        else:
            raise YomboWarning("Parent ID not found.")

    @inlineCallbacks
    def get_siblings(self, node_requested, limiter=None):
        """
        Returns a deferred! A sibling is defined as nodes having the same parent id.

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param node_requested: The node ID or node label to search for.
        :type node_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :return: Pointer to requested node.
        :rtype: dict
        """
        try:
            node = self.get_meta(node_requested, limiter=limiter)
        except Exception as e:
            logger.warn("Unable to find requested node: {node}.  Reason: {e}", node=node_requested, e=e)
            raise YomboWarning()

        if node.parent_id is not None and node.data_type is not None:
            data = yield self._LocalDB.get_node_siblings(node)
            returnValue(data)
        else:
            raise YomboWarning("Node has no parent or no node_type.")

    @inlineCallbacks
    def get_children(self, node_requested, limiter=None):
        """
        Returns a deferred! A sibling is defined as nodes having the same parent id.

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param node_requested: The node ID or node label to search for.
        :type node_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :return: Pointer to requested node.
        :rtype: dict
        """
        try:
            node = self.get_meta(node_requested, limiter=limiter)
        except Exception as e:
            logger.warn("Unable to find requested node: {node}.  Reason: {e}", node=node_requested, e=e)
            raise YomboWarning()

        if node.data_type is not None:
            data = yield self._LocalDB.get_node_children(node)
            returnValue(data)
        else:
            raise YomboWarning("Node has invalid node_type.")

    def search(self, _limiter=None, _operation=None, **kwargs):
        """
        Search for node based on attributes for all nodes.

        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the node to check for.
        :return: 
        """
        return search_instance(kwargs,
                               self.nodes,
                               self.node_search_attributes,
                               _limiter,
                               _operation)

    @inlineCallbacks
    def dev_node_add(self, data, **kwargs):
        """
        Add a node at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """
        node_results = yield self._YomboAPI.request('POST', '/v1/node', data)
        # print("dt_results: %s" % node_results)

        if node_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't add node",
                'apimsg': node_results['content']['message'],
                'apimsghtml': node_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Node type added.",
            'node_id': node_results['data']['id'],
        }
        returnValue(results)

    @inlineCallbacks
    def dev_node_edit(self, node_id, data, **kwargs):
        """
        Edit a node at the Yombo server level, not at the local gateway level.

        :param data:
        :param kwargs:
        :return:
        """

        node_results = yield self._YomboAPI.request('PATCH', '/v1/node/%s' % (node_id), data)
        # print("module edit results: %s" % module_results)

        if node_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit node",
                'apimsg': node_results['content']['message'],
                'apimsghtml': node_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Device type edited.",
            'node_id': node_results['data']['id'],
        }
        returnValue(results)

    @inlineCallbacks
    def dev_node_delete(self, node_id, **kwargs):
        """
        Delete a node at the Yombo server level, not at the local gateway level.

        :param node_id: The node ID to delete.
        :param kwargs:
        :return:
        """
        node_results = yield self._YomboAPI.request('DELETE', '/v1/node/%s' % node_id)

        if node_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete node",
                'apimsg': node_results['content']['message'],
                'apimsghtml': node_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Node deleted.",
            'node_id': node_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_node_enable(self, node_id, **kwargs):
        """
        Enable a node at the Yombo server level, not at the local gateway level.

        :param node_id: The node ID to enable.
        :param kwargs:
        :return:
        """
        #        print "enabling node: %s" % node_id
        api_data = {
            'status': 1,
        }

        node_results = yield self._YomboAPI.request('PATCH', '/v1/node/%s' % node_id, api_data)

        if node_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't enable node",
                'apimsg': node_results['content']['message'],
                'apimsghtml': node_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Node enabled.",
            'node_id': node_id,
        }
        returnValue(results)

    @inlineCallbacks
    def dev_node_disable(self, node_id, **kwargs):
        """
        Enable a node at the Yombo server level, not at the local gateway level.

        :param node_id: The node ID to disable.
        :param kwargs:
        :return:
        """
#        print "disabling node: %s" % node_id
        api_data = {
            'status': 0,
        }

        node_results = yield self._YomboAPI.request('PATCH', '/v1/node/%s' % node_id, api_data)
        # print("disable node results: %s" % node_results)

        if node_results['code'] != 200:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable node",
                'apimsg': node_results['content']['message'],
                'apimsghtml': node_results['content']['html_message'],
            }
            returnValue(results)

        results = {
            'status': 'success',
            'msg': "Node disabled.",
            'node_id': node_id,
        }
        returnValue(results)


class Node:
    """
    A class to manage a single node.
    :ivar node_id: (string) The unique ID.
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

    def __init__(self, node):
        """
        Setup the node object using information passed in.

        :param node: An node with all required items to create the class.
        :type node: dict

        """
        logger.debug("node info: {node}", node=node)

        self.node_id = node['id']
        self.machine_label = node['machine_label']
        self.updated_srv = None

        # below are configure in update_attributes()
        self.parent_id = None
        self.gateway_id = None
        self.node_type = None
        self.weight = None
        self.gw_always_load = None
        self.destination = None
        self.data_type = None
        self.status = None
        self.updated = None
        self.created = None
        self.update_attributes(node)

    def update_attributes(self, node):
        """
        Sets various values from a node dictionary. This can be called when either new or
        when updating.

        :param node: 
        :return: 
        """
        self.parent_id = node['parent_id']
        self.gateway_id = node['node_type']
        self.node_type = node['node_type']
        self.weight = node['weight']
        self.machine_label = node['machine_label']
        self.gw_always_load = node['gw_always_load']
        self.destination = node['destination']
        self.data_type = node['data_type']
        self.status = node['status']
        self.created = node['created']
        self.updated = node['updated']

    def __str__(self):
        """
        Print a string when printing the class.  This will return the node id so that
        the node can be identified and referenced easily.
        """
        return self.node_id

    def __repl__(self):
        """
        Export node variables as a dictionary.
        """
        return {
            'node_id': str(self.node_id),
            'parent_id': str(self.parent_id),
            'gateway_id': str(self.gateway_id),
            'node_type': str(self.node_type),
            'weight': int(self.weight),
            'gw_always_load': int(self.gw_always_load),
            'destination': str(self.destination),
            'data_type': str(self.data_type),
            'status': int(self.status),
            'created': int(self.created),
            'updated': int(self.updated),
        }
