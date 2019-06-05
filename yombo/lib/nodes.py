# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Nodes @ Library Documentation <https://yombo.net/docs/libraries/nodes>`_

Nodes store generic information and are used to store information that doesn't need specific database needs.

**Besure to double check if the function being used returns a deferred. Many times, the node may be in the
database and needs to be retrieved using a Deferred.**

Nodes differ from SQLDict in that Nodes can be managed by the Yombo API, while SQLDict is only used
for local data.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2017-2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/nodes.html>`_
"""
from copy import deepcopy
from time import time

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.classes.triggerdict import TriggerDict
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.utils import bytes_to_unicode, data_pickle, sleep
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.nodes")


class Nodes(YomboLibrary, LibrarySearchMixin):
    """
    Manages nodes for a gateway.
    """
    nodes = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_attribute_name = "nodes"
    _class_storage_fields = [
        "node_id", "machine_label", "label", "parent_id", "user_id", "node_type", "destination"
    ]
    _class_storage_sort_key = "node_type"

    def __contains__(self, node_requested):
        """

        .. note::

          The node must be enabled and loaded in order to be found using this method.

        Checks to if a provided node ID or machine_label exists.

            >>> if "0kas02j1zss349k1" in self._Nodes:

        or:

            >>> if "some_node_name" in self._Nodes:

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param node_requested: The node id or machine_label to search for.
        :type node_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(node_requested)
            return True
        except:
            return False

    def __getitem__(self, node_requested):
        """
        .. note::

          The node must be enabled and loaded in order to be found using this method.

        Attempts to find the device requested using a couple of methods.

            >>> node = self._Nodes["0kas02j1zss349k1"]  #by uuid

        or:

            >>> node = self._Nodes["alpnum"]  #by name

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param node_requested: The node ID or machine_label to search for.
        :type node_requested: string
        :return: A pointer to the device type instance.
        :rtype: instance
        """
        return self.get(node_requested)

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
        return self.nodes.__iter__()

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

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Setups up the basic framework and loads nodes marked for always load or the gateway_id is
        set for us.
        """
        yield self._load_nodes_from_database()

    @inlineCallbacks
    def _stop_(self, **kwargs):
        """
        Cleans up any pending deferreds.
        """
        for node_id, node in self.nodes.items():
            yield node._stop_()

    @inlineCallbacks
    def _load_nodes_from_database(self):
        """
        Loads nodes from database and sends them to :py:meth:`_load_node_into_memory <Nodes._load_node_into_memory>`. This only
        loads nodes marked as 'always_load' = 1, or the gateway_id matches this gateway and the
        destination is 'gw'.

        This function shuold only be be called on system startup by the nodes _init_ function.
        """
        nodes = yield self._LocalDB.get_nodes()
        for node in nodes:
            self._load_node_into_memory(node)

    def _load_node_into_memory(self, node, test_node=False):
        """
        Loads a dictionary representing a node into memory. This should only be used by this library to
        import from the database or after 'add_node' has completed.

        **Hooks called**:

        * _node_before_load_ : Called before the node is loaded into memory.
        * _node_after_load_ : Called after the node is loaded into memory.

        :param node: A dictionary of items required to either setup a new node or update an existing one.
        :type node: dict
        :param test_node: Used for unit testing.
        :type test_node: bool
        :returns: Pointer to new node. Only used during unittest
        """
        # print(f"Node keys installed: {list(self.nodes.keys())}")
        logger.debug("node: {node}", node=node)

        node_id = node["id"]
        if node_id in self.nodes:
            raise YomboWarning(f"Cannot add node to memory, already exists: {node_id}")

        try:
            global_invoke_all("_node_before_load_",
                              called_by=self,
                              node_id=node_id,
                              node=node,
                              )
        except Exception as e:
            pass
        self.nodes[node_id] = Node(self, node)  # Create a new node in memory
        try:
            global_invoke_all("_node_after_load_",
                              called_by=self,
                              node_id=node_id,
                              node=self.nodes[node_id],
                              )
        except Exception as e:
            pass


    def get_parent(self, node_requested, limiter=None):
        """
        Looks up the requested node and attempts to locate it's parent.

        This only works on nodes loaded into the gateway! To load a node by id, use
        'yield self._Nodes.load_by_id('node_id_xyz')' first.

        :raises YomboWarning: For invalid requests, or if the parent isn't found.
        :raises KeyError: When item requested cannot be found.
        :param node_requested: The node ID, machine_label, or label to search for.
        :type node_requested: string
        :param limiter_override: Default: .90 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :return: Pointer to requested node.
        :rtype: dict
        """
        node = self.get(node_requested, limiter=limiter)

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
        node = self.get(node_requested, limiter=limiter)

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
        :param limiter_override: Default: .90 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :return: Pointer to requested node.
        :rtype: dict
        """
        node = self.get(node_requested, limiter=limiter)

        children = {}
        for node_id, node_obj in self.nodes.items():
            if node_obj.parent_id == node.node_id:
                children[node_id] = node_obj
        return children

    @inlineCallbacks
    def add_node(self, node_data, source=None, authorization=None, **kwargs):
        """
        Used to create new nodes. Node data should be a dictionary. This will:

        1) Send the node information to Yombo cloud for persistence.
        2) Save the node information to local database.
        3) Load the node into memory for usage.

        This adds the node at Yombo, adds to the local DB store if the gateway_id matches outs,
        and loads it into memory if the gateways is ours and destination is 'gw' or 'always_load' is 1.

        Required:
        node_type
        weight (defaults to 0 if not set)
        always_load (defaults to 1 - true if not set)
        data
        data_content_type - Usually msgpack_base85 or json.
        status (defaults to 1 - enabled)

        Optional:
        gateway_id - Will not save to localdb or load into memory if not set to this gateway.
        machine_label
        label
        destination

        :param node_data:
        :param kwargs:
        :return:
        """
        print("nodes:: new_new 1")

        if source is None:
            source = "local"

        gateway_id = self.gateway_id
        if "data" not in node_data or node_data["data"] is None:
            raise YomboWarning("Node must have data!")

        if "data_content_type" not in node_data or node_data["data_content_type"] is None:
            if isinstance(node_data["data"], dict) or isinstance(node_data["data"], list):
                node_data["data_content_type"] = "json"
            elif isinstance(node_data["data"], bool):
                node_data["data_content_type"] = "bool"
            else:
                node_data["data_content_type"] = "string"

        if "parent_id" not in node_data:
            node_data["parent_id"] = None

        if "gateway_id" not in node_data:
            node_data["gateway_id"] = gateway_id

        if "destination" in node_data and node_data["destination"] == "gw" and \
                ("gateway_id" not in node_data or node_data["gateway_id"] is None):
            node_data["gateway_id"] = gateway_id

        if "always_load" not in node_data or node_data["always_load"] is None:
            node_data["always_load"] = 1

        if "weight" not in node_data or node_data["weight"] is None:
            node_data["weight"] = 0

        if "status" not in node_data or node_data["status"] is None:
            node_data["status"] = 1

        if source == "local":
            # api_data = deepcopy(node_data)
            node_data["data"] = data_pickle(node_data["data"], node_data["data_content_type"])

            api_data = {k: v for k, v in bytes_to_unicode(node_data).items() if v}

            print("nodes:: new_new 10")
            response = yield self._YomboAPI.request("POST", "/v1/node",
                                                    api_data,
                                                    authorization_header=authorization)

            # print("added node results: %s" % node_results)
            node_data = response.content["data"]['attributes']
            print(f"new node data: {node_data}")

        node_id = node_data["id"]
        if "gateway_id" in node_data and node_data["gateway_id"] == gateway_id:
            self.nodes[node_id].add_to_db()

        if "destination" in node_data and node_data["destination"] == "gw" and \
                "gateway_id" in node_data and node_data["gateway_id"] == gateway_id:
            print("Loading new node data into memory...")
            self._load_node_into_memory(node_data)
            global_invoke_all("_node_added_",
                              called_by=self,
                              node_id=node_id,
                              node=self.nodes[node_id],
                              )
        return node_id

    @inlineCallbacks
    def edit_node(self, node_id, node_data, source=None, authorization=None, **kwargs):
        """
        This shouldn't be used by outside calls, instead, tp update the node, simply edit
        the node attributes directly. That will cause the node to update the database and Yombo API.

        This is used by other internal libraries to update a node's data in bulk and
        optionally

        :param node_id: Node ID to bulk update.
        :param node_data: Dictionary of items to update
        :param source: Should be: local or remote. Default is local.
        :param kwargs:
        :return:
        """
        gateway_id = self.gateway_id

        if source is None:
            source = "local"

        # print("editing node: %s" % node_id)
        if isinstance(node_data, dict) is False:
            raise YomboWarning("edit_node() only accepts dictionaries for 'node_data' argument.")

        if "data" not in node_data:
            raise YomboWarning("Cannot edit node, 'data' not found")


        global_invoke_all("_node_before_update_",
                          called_by=self,
                          node_id=node_id,
                          node=node_data,
                          in_memory=node_id in self.nodes,
                          )

        if source == "local":
            api_data = deepcopy(node_data)
            node_data["data"] = data_pickle(api_data["data"], api_data["data_content_type"])
            # print("new node data: %s" % api_data)
            api_to_send = {k: v for k, v in bytes_to_unicode(api_data).items() if v}

            response = yield self.patch_node(node_id=node_id, api_data=api_to_send, authorization=authorization)

            node_data = response.content["data"]['attributes']

        # Now we have the final data, lets update the local info.
        node_id = node_data["id"]
        if node_id in self.nodes:
            self.nodes[node_id].update_attributes(node_data)  # Update existing node data.
            self.nodes[node_id].save_to_db()

        global_invoke_all("_node_updated_",
                          called_by=self,
                          node_id=node_id,
                          node=self.nodes[node_id],
                          )
        return self.nodes[node_id]

    @inlineCallbacks
    def update_node_status(self, node_id, new_status, authorization=None):
        """
        Change the node's status from: enabled (1), disabled (0), or deleted (2).

        :param node_id: Node ID to alter.
        :param new_status: 0 for disabled, 1 for enabled, 2 for deleted.
        :return:
        """
        node_status_values = {
            0: "disable",
            1: "enable",
            2: "delete",
        }

        if new_status not in node_status_values:
            raise YomboWarning("new_status must be an int: 0, 1, or 2.")

        global_invoke_all(f"_node_before_{node_status_values}_",
                          called_by=self,
                          node_id=node_id,
                          node=self.nodes[node_id],
                          )
        response = yield self.patch_node(node_id=node_id, api_data={"status": new_status},
                                         authorization=authorization)

        if node_id in self.nodes:
            node = self.nodes[node_id]
            node._status = new_status
            if new_status == 2:
                yield node.delete_from_db()
                del self.nodes[node_id]
            else:
                yield node.save_to_db()

        global_invoke_all(f"_node_after_{node_status_values}_",
                          called_by=self,
                          node_id=node_id,
                          node=self.nodes[node_id],
                          )
        return response

    @inlineCallbacks
    def delete_node(self, node_id, authorization=None):
        """
        Delete a node at the Yombo server level, will try to remove from memory and the database.

        :param node_id: The node ID to delete.
        :param authorization: Authorization token to use if user requested.
        :return:
        """
        response = yield self.update_node_status(node_id, 2, authorization)
        return response

    @inlineCallbacks
    def disable_node(self, node_id, authorization=None):
        """
        Disable a node at the Yombo server level, will update locally if loaded.

        :param node_id: The node ID to enable.
        :param authorization: Authorization token to use if user requested.
        :return:
        """
        response = yield self.update_node_status(node_id, 0, authorization)
        return response

    @inlineCallbacks
    def enable_node(self, node_id, authorization=None):
        """
        Enable a node at the Yombo server level, will update locally if loaded.

        :param node_id: The node ID to enable.
        :param authorization: Authorization token to use if user requested.
        :return:
        """
        response = yield self.update_node_status(node_id, 1, authorization)
        return response

    @inlineCallbacks
    def patch_node(self, node_id, api_data, authorization=None):
        """
        Sends the data within the node to the server.

        :param node_id: A string containing the node id.
        :param api_data: A dictionary of data to send.
        :param authorization: An optional header to use for authorization
        :return:
        """
        yield sleep(1)
        # response = yield self._YomboAPI.request("PATCH", f"/v1/node/{node_id}",
        #                                         api_data,
        #                                         authorization_header=authorization)
        # return response


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
    @property
    def parent_id(self):
        return self._parent_id

    @parent_id.setter
    def parent_id(self, val):
        self._parent_id = val
        self.on_change()
        return

    @property
    def gateway_id(self):
        return self._gateway_id

    @gateway_id.setter
    def gateway_id(self, val):
        self._gateway_id = val
        self.on_change()
        return

    @property
    def node_type(self):
        return self._node_type

    @node_type.setter
    def node_type(self, val):
        self._node_type = val
        self.on_change()
        return

    @property
    def weight(self):
        return self._weight

    @weight.setter
    def weight(self, val):
        self._weight = val
        self.on_change()
        return

    @property
    def gw_always_load(self):
        return self._gw_always_load

    @gw_always_load.setter
    def gw_always_load(self, val):
        self._gw_always_load = val
        self.on_change()
        return

    @property
    def destination(self):
        return self._destination

    @destination.setter
    def destination(self, val):
        self._destination = val
        self.on_change()
        return

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, val):
        self._data = val
        self.on_change()
        return

    @property
    def data_content_type(self):
        return self._data_content_type

    @data_content_type.setter
    def data_content_type(self, val):
        self._data_content_type = val
        self.on_change()
        return

    @property
    def status(self):
        """int: If the node is enabled. 1 for yes, 0 for no, 2 for about to be deleted."""
        return self._status

    @status.setter
    def status(self, val):
        self._status = val
        self.on_change()
        return

    @property
    def updated_at(self):
        """int: When the node was last updated."""
        return self._updated_at

    @updated_at.setter
    def updated_at(self, val):
        return

    @property
    def created_at(self):
        return self._created_at

    @created_at.setter
    def created_at(self, val):
        return

    @property
    def node_id(self):
        return self._node_id

    @node_id.setter
    def node_id(self, val):
        return

    def __init__(self, parent, node):
        """
        Setup the node object using information passed in.

        :param parent: Reference to the Node library.
        :param node: A dictionary containing all the required values to create a node instance.
        :param source: Where the data is coming from. Should be: local, remote, database
        :type node: dict
        """
        logger.debug("node info: {node}", node=node)
        self._startup = True
        self._update_calllater_time = None
        self._update_calllater = None
        self._Parent = parent
        self._node_id = node["id"]
        self.machine_label = node.get("machine_label", None)

        # below are configure in update_attributes()
        self._parent_id = None
        self._gateway_id = None
        self._node_type = None
        self._weight = 0
        self._gw_always_load = 1
        self._destination = None
        self._data = TriggerDict(callback=self.on_change)
        self._data_content_type = None
        self._status = 1
        self._updated_at = time()
        self._created_at = time()
        self.update_attributes(node)

    @inlineCallbacks
    def _stop_(self):
        """
        Called when the system is shutting down. If a save is pending, we save the current state to Yombo API
        and SQL.

        :return:
        """
        if self._update_calllater is not None and self._update_calllater.active():
            self._update_calllater.cancel()
            yield self.save()
            object.__setattr__(self, "_update_calllater", None)

    def update_attributes(self, new_data, force_save=None):
        """
        Sets various values from a new_data dictionary.

        This is primarily used internally to bulk set attributes on startup and when data arrives from
        the Yombo cloud so that it won't create a circle and update Yombo API of any changes.

        :param new_data: Any new data attributes to set in bulk
        :type new_data: dict
        :param force_save: If this function is called outside of the nodes library, set this to true to save it!
        :return:
        """
        if "parent_id" in new_data:
            self.parent_id = new_data["parent_id"]
        if "gateway_id" in new_data:
            self.gateway_id = new_data["gateway_id"]
        if "node_type" in new_data:
            self.node_type = new_data["node_type"]
        if "weight" in new_data:
            self.weight = new_data["weight"]
        if "label" in new_data:
            self.label = new_data["label"]
        if "machine_label" in new_data:
            self.machine_label = new_data["machine_label"]
        if "always_load" in new_data:
            self.always_load = new_data["always_load"]
        if "destination" in new_data:
            self.destination = new_data["destination"]
        if "data" in new_data:
            if isinstance(new_data["data"], dict):
                self.data = TriggerDict(new_data["data"], callback=self.on_change)
            else:
                self.data = new_data["data"]
        if "data_content_type" in new_data:
            self.data_content_type = new_data["data_content_type"]
        if "status" in new_data:
            self.status = new_data["status"]
        if "created_at" in new_data:
            self.created_at = new_data["created_at"]
        if "updated_at" in new_data:
            self.updated_at = new_data["updated_at"]

        if force_save is True:  # Tell Yombo cloud, save to database
            self.on_change()

    def on_change(self, *args, **kwargs):
        """
        This function is called whenever something changes. We wait for 10 seconds of no updates,
        with a max delay of 120 seconds, even if the node is still being updated.

        This saves to the database as well as to Yombo API.

        Simply calls self.save() when it's time to do the actual save.

        :param args:
        :param kwargs:
        :return:
        """
        global_invoke_all("_node_updated_",
                          called_by=self._Parent,
                          node_id=self.node_id,
                          node=self,
                          )
        # print("Node onchange: %s: on_change called: %s" % (self.node_id, self._update_calllater))
        if self._update_calllater is not None and self._update_calllater.active():
            # print("%s: on_change called.. still active.")
            self._update_calllater.cancel()
            object.__setattr__(self, "_update_calllater", None)
            if self._update_calllater_time is not None and self._update_calllater_time < time() - 120:
                # print("forcing save now..!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                object.__setattr__(self, "_update_calllater_time", None)
                self.save()
            else:
                # print("saving node later..")
                object.__setattr__(self, "_update_calllater", reactor.callLater(10, self.save))
        else:
            self._update_calllater_time = time()
            object.__setattr__(self, "_update_calllater", reactor.callLater(10, self.save))

    @inlineCallbacks
    def save(self):
        """
        Updates the Yombo API and saves the current information to the SQL database.

        :return:
        """
        # print("%s: save" % self.node_id)
        if self._update_calllater is not None and self._update_calllater.active():
            self._update_calllater.cancel()
        response = yield self._Parent.patch_node(node_id=self.node_id,
                                                 api_data=self.asdict(include_id=False, pickle_data=True),
                                                 )
        yield self.save_to_db()

    def add_to_db(self):
        if self._Parent.gateway_id == self.gateway_id:
            self._Parent._LocalDB.add_node(self)

    @inlineCallbacks
    def save_to_db(self):
        # print("save_to_db called")
        if self._Parent.gateway_id == self.gateway_id:
            # print("save_to_db called....saving node to local sql now...")
            yield self._Parent._LocalDB.update_node(self)

    def delete_from_db(self):
        if self._Parent.gateway_id == self.gateway_id:
            self._Parent._LocalDB.delete_node(self)

    def __str__(self):
        """
        Print a string when printing the class.  This will return the node id so that
        the node can be identified and referenced easily.
        """
        return f"Node {self.node_id}: {self.label}"

    def asdict(self, include_id=None, pickle_data=None):
        """
        Export node variables as a dictionary.
        """
        data = {
            "id": str(self.node_id),
            "parent_id": str(self.parent_id),
            "gateway_id": str(self.gateway_id),
            "node_type": str(self.node_type),
            "weight": int(self.weight),
            "machine_label": self.machine_label,
            "label": self.label,
            "always_load": int(self.always_load),
            "destination": self.destination,
            "data": self.data,
            "data_content_type": str(self.data_content_type),
            "status": int(self.status),
            "created_at": int(self.created_at),
            "updated_at": int(self.updated_at),
        }
        # print(f"asdict for node: {data}")
        if include_id is False:
            del data["id"]
        if pickle_data is True:
            data["data"] = data_pickle(data["data"], data["data_content_type"])
        return data

    def __repl__(self):
        return self.asdict()
