# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Nodes @ Module Development <https://yombo.net/docs/libraries/nodes>`_


Nodes store generic information and are used to store information that doesn't need specific database needs.

**Besure to double check if the function being used returns a deferred. Only meta data for the node
is loaded into memory, the actual node data remains in the database.**

Nodes differ from SQLDict in that Nodes can be managed by the Yombo API, while SQLDict is only used
for local data.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/nodes.html>`_
"""
# try:  # Prefer simplejson if installed, otherwise json will work swell.
#     import simplejson as json
# except ImportError:
#     import json
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet import reactor

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import bytes_to_unicode, do_search_instance, global_invoke_all, data_unpickle, data_pickle
from yombo.utils.triggerdict import TriggerDict

logger = get_logger('library.nodes')


class Nodes(YomboLibrary):
    """
    Manages nodes for a gateway.
    """
    def __contains__(self, node_requested):
        """
        .. note:: The node must be enabled in order to be found using this method.

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
        return "Yombo nodes library"

    def keys(self):
        """
        Returns the keys (device type ID's) that are configured.

        :return: A list of device type IDs. 
        :rtype: list
        """
        return list(self.nodes.keys())

    def items(self):
        """
        Gets a list of tuples representing the device types configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.nodes.items())

    def values(self):
        return list(self.nodes.values())

    def _init_(self, **kwargs):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        """
        self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.
        self.gateway_id = self._Configs.get2("core", "gwid", "local", False)
        self.nodes = {}
        self.node_search_attributes = ['node_id', 'gateway_id', 'node_type', 'machine_label', 'destination',
                                       'data_type', 'status',
                                      ]
        self.load_deferred = Deferred()
        self._load_nodes_from_database()
        return self.load_deferred

    def _stop_(self, **kwargs):
        """
        Cleans up any pending deferreds.
        """
        if hasattr(self, 'load_deferred'):
            if self.load_deferred is not None and self.load_deferred.called is False:
                self.load_deferred.callback(1)  # if we don't check for this, we can't stop!
        for node_id, node in self.nodes.items():
            node._stop_()

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
            self.import_node(node, source='database')
        self.load_deferred.callback(10)

    def import_node(self, node, source=None, test_node=False):
        """
        Imports a new node. This should only be called by this library on during startup or from "add_node"
        function.

        **Hooks called**:

        * _node_before_import_ : If added, sends node dictionary as 'node'
        * _node_before_update_ : If updated, sends node dictionary as 'node'
        * _node_imported_ : If added, send the node instance as 'node'
        * _node_updated_ : If updated, send the node instance as 'node'

        :param node: A dictionary of items required to either setup a new node or update an existing one.
        :type input: dict
        :param test_node: Used for unit testing.
        :type test_node: bool
        :returns: Pointer to new input. Only used during unittest
        """
        logger.debug("node: {node}", node=node)

        node_id = node["id"]
        global_invoke_all('_nodes_before_import_',
                          called_by=self,
                          node_id=node_id,
                          node=node,
                          )
        if node_id not in self.nodes:
            global_invoke_all('_node_before_load_',
                              called_by=self,
                              node_id=node_id,
                              node=node,
                              )
            self.nodes[node_id] = Node(self, node)
            global_invoke_all('_node_loaded_',
                              called_by=self,
                              node_id=node_id,
                              node=self.nodes[node_id],
                              )
        elif node_id not in self.nodes:
            global_invoke_all('_node_before_update_',
                              called_by=self,
                              node_id=node_id,
                              node=node,
                              )
            self.nodes[node_id].update_attributes(node, source)
            global_invoke_all('_node_updated_',
                              called_by=self,
                              node_id=node_id,
                              node=self.nodes[node_id],
                              )

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
                        if other['value'].node_type == node_type and other['ratio'] > limiter:
                            return other['value']
                else:
                    if found:
                        return item
                raise KeyError("Node not found: %s" % node_requested)
            except YomboWarning as e:
                raise KeyError('Searched for %s, but had problems: %s' % (node_requested, e))

    # @inlineCallbacks
    def get(self, node_requested, node_type=None, limiter=None, status=None):
        """
        Returns a deferred! Looking for a node id in memory and in the database.

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
        return node

    # @inlineCallbacks
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
            return self.nodes[node.parent_id]
        else:
            raise YomboWarning("Parent ID not found.")

    # @inlineCallbacks
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

        if node.parent_id is not None:
            siblings = {}
            for node_id, node_obj in self.nodes.items():
                if node_obj.parent_id == node.parent_id:
                    siblings[node_id] = node_obj
            return siblings
        else:
            raise YomboWarning("Node has no parent_id.")

    # @inlineCallbacks
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

        children = {}
        for node_id, node_obj in self.nodes.items():
            if node_obj.parent_id == node.node_id:
                children[node_id] = node_obj
        return children

    def search(self, criteria):
        """
        Search for nodes based on a dictionary of key=value pairs.

        :param criteria:
        :return:
        """
        results = {}
        for node_id, node in self.nodes.items():
            for key, value in criteria.items():
                if key not in self.node_search_attributes:
                    continue

                # print("searching: %s" % node._instance)
                # if value == node._instance[key]:
                if value == getattr(node, key):
                    results[node_id] = node
        return results

    @inlineCallbacks
    def create(self, data=None, data_content_type=None, node_type=None, gateway_id=None, weight=None, label=None,
               machine_label=None, parent_node=None, parent_id=None, destination=None, status=None):
        """
        A helper function to easily create new nodes. Simply submit what you have, and will pass on whatever
        that can to add_node().

        :param data:
        :param gateway_id:
        :param data_content_type:
        :param weight:
        :param label:
        :param machine_label:
        :param parent_node:
        :param parent_id:
        :param destination:
        :param status:
        :return:
        """
        if data is None:
            data = []

        if data_content_type is None:
            if isinstance(data, dict) or isinstance(data, list):
                data_content_type = 'msgpack_base85'
            elif isinstance(data, bool):
                data_content_type = 'bool'
            else:
                data_content_type = 'string'

        if weight is None:
            weight = 0

        if parent_node is None and parent_id is None:
            parent_id = None
        elif parent_node is not None and isinstance(Node, parent_node):
            parent_id = parent_node.node_id

        if destination == 'gw' and gateway_id is None:
            gateway_id = self.gateway_id()
        elif destination is None and gateway_id is not None:
            destination = 'gw'

        if status is None:
            status = 1

        api_data = {
            'gateway_id': gateway_id,
            'data': data,
            'data_content_type': data_content_type,
            'node_type': node_type,
            'weight': weight,
            'label': label,
            'machine_label': machine_label,
            'parent_id': parent_id,
            'destination': destination,
            'status': status,
        }

        # This fancy inline just removed None and '' values.
        results = yield self.add_node({k: v for k, v in api_data.items() if v})
        # print("create results: %s" % results)
        return self.nodes[results['node_id']]

    @inlineCallbacks
    def add_node(self, api_data, source=None, **kwargs):
        """
        Add a new node. Updates Yombo servers and creates a new entry locally.

        :param api_data:
        :param kwargs:
        :return:
        """
        results = None
        new_node = None
        if 'gateway_id' not in api_data:
            api_data['gateway_id'] = self.gateway_id()

        if 'data_content_type' not in api_data:
            api_data['data_content_type'] = 'json'

        if source != 'amqp':
            input_data = api_data['data'].copy()
            api_data['data'] = data_pickle(api_data['data'], api_data['data_content_type'])

            try:
                api_to_send = {k: v for k, v in bytes_to_unicode(api_data).items() if v}
                node_results = yield self._YomboAPI.request('POST', '/v1/node', api_to_send)
            except YomboWarning as e:
                results = {
                    'status': 'failed',
                    'msg': "Couldn't add node: %s" % e.message,
                    # 'data': None,
                    # 'node_id': None,
                    'apimsg': "Couldn't add node: %s" % e.message,
                    'apimsghtml': "Couldn't add node: %s" % e.html_message,
                }
                return results
            # print("added node results: %s" % node_results)
            node_id = node_results['data']['id']
            new_node = node_results['data']
            new_node['data'] = input_data

        else:
            node_id = api_data['id']
            new_node = api_data

        if 'destination' in api_data:
            if api_data['destination'] == 'gw':
                self.import_node(new_node, source)
                self.nodes[node_id].add_to_db()
                global_invoke_all('_node_added_',
                                  called_by=self,
                                  node_id=node_id,
                                  node=self.nodes[node_id],
                                  )
                return self.nodes[node_id]
        results = {
            'status': 'success',
            'msg': "Node added.",
            'node_id': node_id,
            'data': api_data,
            'apimsg': "Node edited.",
            'apimsghtml': "Node edited.",
        }
        return results

    @inlineCallbacks
    def edit_node(self, node_id, api_data, source=None, **kwargs):
        """
        This is used to save or update node information for nodes NOT in memory. This will call
        the Yombo API to update the node remotely.

        To update a local node that is in memory, simply just update it. It will automatically
        update Yombo API and local database needed.

        :param data:
        :param kwargs:
        :return:
        """
        # print("editing node: %s" % node_id)
        if isinstance(api_data, Node):
            api_data = api_data.asdict()

        if source != 'amqp':
            if 'data_content_type' not in api_data:
                raise YomboWarning("Cannot edit node, 'data_content_type' not found")
            if 'data' not in api_data:
                raise YomboWarning("Cannot edit node, 'data' not found")
            api_data['data'] = data_pickle(api_data['data'], api_data['data_content_type'])
            # print("new node data: %s" % api_data)
            try:
                api_to_send = {k: v for k, v in bytes_to_unicode(api_data).items() if v}
                node_results = yield self._YomboAPI.request('PATCH', '/v1/node/%s' % (node_id), api_to_send)
                # print("node edit results: %s" % node_results)
            except YomboWarning as e:
                results = {
                    'status': 'failed',
                    'msg': "Couldn't edit node: %s" % e.message,
                    'data': None,
                    'node_id': node_id,
                    'apimsg': "Couldn't edit node: %s" % e.message,
                    'apimsghtml': "Couldn't edit node: %s" % e.html_message,
                }
                logger.warn("Couldn't save node: {e}", e=e)
                return results

            api_data['data'] = node_results['data']


        if node_id in self.nodes:
            node = self.nodes[node_id]
            if source != 'node':
                node.update_attributes(api_data, source='parent')
                node.save_to_db()

        global_invoke_all('_node_edited_',
                          called_by=self,
                          node_id=node_id,
                          node=self.nodes[node_id],
                          )
        results = {
            'status': 'success',
            'msg': "Node edited.",
            'node_id': node_id,
            'data': node_results['data'],
            'apimsg': "Node edited.",
            'apimsghtml': "Node edited.",
            }
        return results

    @inlineCallbacks
    def delete_node(self, node_id, source=None, **kwargs):
        """
        Delete a node at the Yombo server level, not at the local gateway level.

        :param node_id: The node ID to delete.
        :param kwargs:
        :return:
        """
        results = None
        if source != 'amqp':
            try:
                node_results = yield self._YomboAPI.request('DELETE', '/v1/node/%s' % node_id)
            except YomboWarning as e:
                results = {
                    'status': 'failed',
                    'msg': "Couldn't delete node: %s" % e.message,
                    'data': None,
                    'node_id': node_id,
                    'apimsg': "Couldn't delete node: %s" % e.message,
                    'apimsghtml': "Couldn't delete node: %s" % e.html_message,
                }
                return results

        api_data = {
            'status': 2,
        }
        if node_id in self.nodes:
            node = self.nodes[node_id]
            if source != 'node':
                node.update_attributes(api_data, source='parent')
                node.save_to_db()

        global_invoke_all('_node_deleted_',
                          called_by=self,
                          node_id=node_id,
                          node=self.nodes[node_id],
                          )

        results = {
            'status': 'success',
            'msg': "Node deleted.",
            'node_id': node_id,
            'data': None,
            'apimsg': "Node deleted.",
            'apimsghtml': "Node deleted.",
            }
        return results

    @inlineCallbacks
    def enable_node(self, node_id, source=None, **kwargs):
        """
        Enable a node at the Yombo server level

        :param node_id: The node ID to enable.
        :param kwargs:
        :return:
        """
        results = None
        api_data = {
            'status': 1,
        }

        if source != 'amqp':
            try:
                node_results = yield self._YomboAPI.request('PATCH', '/v1/node/%s' % node_id, api_data)
            except YomboWarning as e:
                results = {
                    'status': 'failed',
                    'msg': "Couldn't enable node: %s" % e.message,
                    'data': None,
                    'node_id': node_id,
                    'apimsg': "Couldn't enable node: %s" % e.message,
                    'apimsghtml': "Couldn't enable node: %s" % e.html_message,
                }
                return results

        if node_id in self.nodes:
            node = self.nodes[node_id]
            if source != 'node':
                node.update_attributes(api_data, source='parent')
                node.save_to_db()

        global_invoke_all('_node_enabled_',
                          called_by=self,
                          node_id=node_id,
                          node=self.nodes[node_id],
                          )
        results = {
            'status': 'success',
            'msg': "Node enabled.",
            'node_id': node_id,
            'data': node.dump(),
            'apimsg': "Node enabled.",
            'apimsghtml': "Node enabled.",
            }
        return results

    @inlineCallbacks
    def disable_node(self, node_id, source=None, **kwargs):
        """
        Disable a node at the Yombo server level

        :param node_id: The node ID to disable.
        :param kwargs:
        :return:
        """
        results = None
        api_data = {
            'status': 0,
        }

        if source != 'amqp':
            try:
                node_results = yield self._YomboAPI.request('PATCH', '/v1/node/%s' % node_id, api_data)
            except YomboWarning as e:
                results = {
                    'status': 'failed',
                    'msg': "Couldn't disable node: %s" % e.message,
                    'data': None,
                    'node_id': node_id,
                    'apimsg': "Couldn't disable node: %s" % e.message,
                    'apimsghtml': "Couldn't disable node: %s" % e.html_message,
                }
                return results

        if node_id in self.nodes:
            node = self.nodes[node_id]
            if source != 'node':
                node.update_attributes(api_data, source='parent')
            node.save_to_db()
        global_invoke_all('_node_disabled_',
                          called_by=self,
                          node_id=node_id,
                          node=self.nodes[node_id],
                          )
        results = {
            'status': 'success',
            'msg': "Node disabled.",
            'node_id': node_id,
            'data': node.dump(),
            'apimsg': "Node disabled.",
            'apimsghtml': "Node disabled.",
        }
        return results


class Node(object):
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
    :ivar created_at: (int) EPOCH time when created
    :ivar updated_at: (int) EPOCH time when last updated
    """

    def __init__(self, parent, node):
        """
        Setup the node object using information passed in.

        :param node: An node with all required items to create the class.
        :type node: dict

        """
        logger.debug("node info: {node}", node=node)
        self._startup = True
        self._update_calllater_time = None
        self._update_calllater = None
        self._Parent = parent
        self.node_id = node['id']
        self.machine_label = node.get('machine_label', None)

        # below are configure in update_attributes()
        self.parent_id = None
        self.gateway_id = None
        self.node_type = None
        self.weight = 0
        self.gw_always_load = 1
        self.destination = None
        self.data = None
        self.data_content_type = None
        self.status = None
        self.updated_at = None
        self.created_at = None
        self.update_attributes(node, source='parent')
        self._startup = True

    def __setattr__(self, key, value):
        # print("node settr called: %s = %s" % (key, value))
        if key == 'data':
            if isinstance(value, dict):
                value = TriggerDict(value, callback=self._on_change)
        object.__setattr__(self, key, value)
        # self.key = value
        if self._startup is not True:
            self._on_change()

    def _stop_(self):
        """
        Called when the system is shutting down. If a save is pending, we save the current state to Yombo API
        and SQL.

        :return:
        """
        if self._update_calllater is not None and self._update_calllater.active():
            self._update_calllater.cancel()
            self.save()
            object.__setattr__(self, '_update_calllater', None)

    def _on_change(self, *args, **kwargs):
        """
        This function is called whenever something changes. We 10 seconds of no updates, or 120 seconds with
        continious updates, we will update the Yombo API as well as save to disk.

        Simply calls self.save() when it's time to do the actual save.

        :param args:
        :param kwargs:
        :return:
        """
        # print("%s: _on_change called: %s" % (self.node_id, self._update_calllater))
        if self._update_calllater is not None and self._update_calllater.active():
            # print("%s: _on_change called.. still active.")
            self._update_calllater.cancel()
            object.__setattr__(self, '_update_calllater', None)
            if self._update_calllater_time is not None and self._update_calllater_time < time() - 120:
                # print("forcing save now..!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                self._update_calllater_time = None
                self.save()
            else:
                # print("saving node later..")
                object.__setattr__(self, '_update_calllater', reactor.callLater(10, self.save))
        else:
            self._update_calllater_time = time()
            object.__setattr__(self, '_update_calllater', reactor.callLater(10, self.save))

    @inlineCallbacks
    def save(self):
        """
        Updates the Yombo API and saves the current information to the SQL database.

        :return:
        """
        # print("%s: save" % self.node_id)
        yield self._Parent.edit_node(self.node_id, self, source="node")
        self.save_to_db()

    def update_attributes(self, new_data, source=None):
        """
        Sets various values from a new_data dictionary. This can be called when either new or
        when updating.

        :param new_data:
        :return: 
        """
        if 'parent_id' in new_data:
            self.parent_id = new_data['parent_id']
        if 'gateway_id' in new_data:
            self.gateway_id = new_data['gateway_id']
        if 'node_type' in new_data:
            self.node_type = new_data['node_type']
        if 'weight' in new_data:
            self.weight = new_data['weight']
        if 'label' in new_data:
            self.label = new_data['label']
        if 'machine_label' in new_data:
            self.machine_label = new_data['machine_label']
        if 'always_load' in new_data:
            self.always_load = new_data['always_load']
        if 'destination' in new_data:
            self.destination = new_data['destination']
        if 'data' in new_data:
            if isinstance(new_data['data'], dict):
                self.data = TriggerDict(new_data['data'], callback=self._on_change)
            else:
                self.data = new_data['data']
        if 'data_content_type' in new_data:
            self.data_content_type = new_data['data_content_type']
        if 'status' in new_data:
            self.status = new_data['status']
        if 'created_at' in new_data:
            self.created_at = new_data['created_at']
        if 'updated_at' in new_data:
            self.updated_at = new_data['updated_at']
        if source != "parent":
            self.save_node()

    def add_to_db(self):
        if self._Parent.gateway_id() == self.gateway_id:
            self._Parent._LocalDB.add_node(self)

    def save_to_db(self):
        # print("save_to_db called")
        if self._Parent.gateway_id() == self.gateway_id:
            # print("save_to_db called....saving node to local sql now...")
            self._Parent._LocalDB.update_node(self)

    def delete_from_db(self):
        if self._Parent.gateway_id() == self.gateway_id:
            self._Parent._LocalDB.delete_node(self)

    def __str__(self):
        """
        Print a string when printing the class.  This will return the node id so that
        the node can be identified and referenced easily.
        """
        return "Node %s: %s" % (self.node_id, self.label)

    def asdict(self):
        """
        Export node variables as a dictionary.
        """
        return {
            'node_id': str(self.node_id),
            'parent_id': str(self.parent_id),
            'node_type': str(self.node_type),
            'weight': int(self.weight),
            'label': self.label,
            'machine_label': self.machine_label,
            'always_load': self.always_load,
            'gateway_id': str(self.gateway_id),
            'destination': self.destination,
            'data': self.data,
            'data_content_type': self.data_content_type,
            'status': int(self.status),
            'created_at': int(self.created_at),
            'updated_at': int(self.updated_at),
        }

