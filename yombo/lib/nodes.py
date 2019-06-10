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

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_db_child_mixin import LibraryDBChildMixin
from yombo.mixins.sync_to_everywhere_mixin import SyncToEverywhereMixin
from yombo.mixins.library_db_model_mixin import LibraryDBModelMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.utils import bytes_to_unicode, data_pickle, sleep
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.nodes")


class Node(Entity, LibraryDBChildMixin, SyncToEverywhereMixin):
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
    _primary_column = "node_id"  # Used by mixins

    def __init__(self, parent, incoming, source=None):
        """
        Setup the node object using information passed in.

        :param parent: Reference to the Node library.
        :param node: A dictionary containing all the required values to create a node instance.
        :param source: Where the data is coming from. Should be: local, remote, database
        :type node: dict
        """
        self._Entity_type = "Node"
        self._Entity_label_attribute = "node_id"

        super().__init__(parent)
        self._setup_class_model(incoming, source=source)


class Nodes(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Manages nodes for a gateway.
    """
    nodes = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "node"
    _class_storage_load_db_class = Node
    _class_storage_attribute_name = "nodes"
    _class_storage_search_fields = [
        "node_id", "node_type", "machine_label", "label"
    ]
    _class_storage_sort_key = "machine_label"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Loads nodes from the database and imports them.
        """
        yield self._class_storage_load_from_database()

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
