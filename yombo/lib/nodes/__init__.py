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

:copyright: Copyright 2017-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/nodes/__init__.html>`_
"""
# Import python libraries
from copy import deepcopy
from typing import Any, ClassVar, Dict, List, Optional, Type

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import STATUS, ENABLED, DISABLED, DELETED
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.schemas import NodeSchema
from yombo.lib.nodes.node import Node
from yombo.mixins.library_db_parent_mixin import LibraryDBParentMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.utils import bytes_to_unicode, sleep
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.nodes")


class Nodes(YomboLibrary, LibraryDBParentMixin, LibrarySearchMixin):
    """
    Manages nodes for a gateway.
    """
    nodes: dict = {}
    platforms: dict = {}

    # The remaining attributes are used by various mixins.
    _storage_primary_field_name: ClassVar[str] = "node_id"
    _storage_attribute_name: ClassVar[str] = "nodes"
    _storage_label_name: ClassVar[str] = "node"
    _storage_class_reference: ClassVar = Node
    _storage_schema: ClassVar = NodeSchema()
    _storage_default_where: ClassVar[list] = ["destination = ? or always_load = 1", "gw"]
    _storage_search_fields: ClassVar[List[str]] = [
        "node_id", "node_type", "machine_label", "label"
    ]
    _storage_attribute_sort_key: ClassVar[str] = "machine_label"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Loads the system node platforms.

        This loads the core Node object and any platforms. This allows the system to handle multiple node
        types.
        """
        classes = yield self._Files.extract_classes_from_files("yombo/lib/nodes/node.py")
        self.platforms.update(classes)

        files = yield self._Files.search_path_for_files("yombo/lib/nodes/platforms/*.py")
        classes = yield self._Files.extract_classes_from_files(files)
        self.platforms.update(classes)

        # load module nodes
        files = yield self._Modules.search_modules_for_files("nodes/*.py")
        classes = yield self._Files.extract_classes_from_files(files)
        self.platforms.update(classes)
        self.platforms = dict((k.lower(), v) for k, v in self.platforms.items())

    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Loads nodes from the database and imports them.

        This also loads any module defined node types.
        """
        files = yield self._Modules.search_modules_for_files("nodes/*.py")
        classes = yield self._Files.extract_classes_from_files(files)
        self.platforms.update(dict((k.lower(), v) for k, v in classes.items()))
        yield self.load_from_database()

    def _storage_class_reference_getter(self, incoming: dict) -> Type[Node]:
        """
        Return the correct class to use to create individual input types.

        This is called by load_an_item_to_memory

        :param incoming:
        :return:
        """
        node_type = incoming["node_type"].lower().replace("_", "")
        if incoming["destination"] == "gw" and node_type in self.platforms:
            return self.platforms[node_type]
        else:
            return Node

    def pickle_data_records(self, incoming):
        """
        Pickles various records as needed.

        :param incoming:
        :return:
        """
        data = deepcopy(incoming)
        data["data"] = self._Tools.data_pickle(data["data"], data["data_content_type"])
        return data

    def unpickle_data_records(self, incoming, *args, **kwargs):
        """
        Override library_db_parent_mixin::unpickle_data_records to handle variable encoding types
        set within the 'data_content_type'.

        :param incoming:
        :param pickled_columns:
        :return:
        """
        if isinstance(incoming, list):
            results = []
            for record in incoming:
                data = deepcopy(record)
                data["data"] = self._Tools.data_unpickle(data["data"], data["data_content_type"])
                results.append(data)
            return results
        else:
            data = deepcopy(incoming)
            data["data"] = self._Tools.data_unpickle(data["data"], data["data_content_type"])
            return data

    def get_parent(self, node_requested: str, limiter: Optional[float] = None) -> Node:
        """
        Looks up the requested node and attempts to locate it's parent.

        This only works on nodes loaded into the gateway! To load a node by id, use
        'yield self._Nodes.load_by_id('node_id_xyz')' first.

        :raises YomboWarning: For invalid requests, or if the parent isn't found.
        :raises KeyError: When item requested cannot be found.
        :param node_requested: The node ID, machine_label, or label to search for.
        :param limiter: Default: .90 - A value between .5 and .99. Sets how close of a match it the search should be.
        :return: Pointer to requested node.
        """
        found_node = self.get(node_requested, limiter=limiter)

        if node.node_parent_id in self.nodes:
            return self.nodes[found_node.node_parent_id]
        else:
            raise YomboWarning("Parent ID not found.")

    def get_siblings(self, node_requested: str, limiter: Optional[float] = None) -> Dict[str, Node]:
        """
        Returns a deferred! A sibling is defined as nodes having the same parent id.

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param node_requested: The node ID or node label to search for.
        :type node_requested: string
        :param limiter: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter: float
        :return: Pointer to requested node.
        :rtype: dict
        """
        found_node = self.get(node_requested, limiter=limiter)

        if found_node.node_parent_id is not None:
            siblings = {}
            for node_id, node_obj in self.nodes.items():
                if node_obj.node_parent_id == found_node.node_parent_id:
                    siblings[node_id] = node_obj
            return siblings
        else:
            raise YomboWarning("Node has no parent_id.")

    def get_children(self, node_requested: str, limiter: Optional[float] = None) -> Dict[str, Node]:
        """
        Returns a deferred! A sibling is defined as nodes having the same parent id.

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param node_requested: The node ID or node label to search for.
        :type node_requested: string
        :param limiter: Default: .90 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter: float
        :return: Pointer to requested node.
        :rtype: dict
        """
        found_node = self.get(node_requested, limiter=limiter)

        children = {}
        for node_id, node_obj in self.nodes.items():
            if node_obj.node_parent_id == found_node.node_id:
                children[node_id] = node_obj
        return children

    @inlineCallbacks
    def new(self, node_type: str, machine_label: str, label: str, data: Any, gateway_id: Optional[str] = None,
            node_parent_id: Optional[str] = None, weight: Optional[int] = None, always_load: Optional[int] = None,
            destination: Optional[str] = None, data_content_type: Optional[str] = None, status: Optional[int] = None,
            _load_source: Optional[str] = None, _request_context: Optional[str] = None,
            _authentication: Optional[Type["yombo.mixins.auth_mixin.AuthMixin"]] = None, **kwargs):
        """
        Create a new node.

        :param node_type: What kind of node this is: scene, automation, etc
        :param machine_label: Node machine_label
        :param label: Node human label.
        :param data: Node data.
        :param gateway_id: The gateway_id this node should be sent to.
        :param node_parent_id: If set, this node becomes a child node to another node.
        :param weight: Weighting is used for sorting.
        :param always_load: If the node should be loaded by the gateway.
        :param destination: Such as "gw" if it's to be loaded by a gateway. Otherwise, any string.
        :param data_content_type: Apply any processing to the data when saving/loading: string, int, float, json, msgpack
        :param status: 0 for disabled, 1 for enabled, 2 for deleted
        :param _load_source: Where the data originated from. One of: local, database, yombo, system
        :param _request_context: Context about the request. Such as an IP address of the source.
        :param _authentication: An auth item such as a websession or authkey.
        :return:
        """
        if data_content_type is None:
            if isinstance(data, dict) or isinstance(data, list):
                data_content_type = "json"
            elif isinstance(data, bool):
                data_content_type = "bool"
            else:
                data_content_type = "string"

        if destination == "gw" and gateway_id is None:
            gateway_id = self._gateway_id

        if always_load is None:
            always_load = 1

        if weight is None:
            weight = 0

        if status is None:
            status = 1

        if _load_source is None:
            _load_source = "library"

        if _load_source not in ("amqp", "api"):
            results = yield self._YomboAPI.new("nodes",
                                               {
                                                   "gateway_id": gateway_id,
                                                   "node_parent_id": node_parent_id,
                                                   "node_type": node_type,
                                                   "machine_label": machine_label,
                                                   "label": label,
                                                   "weight": weight,
                                                   "always_load": always_load,
                                                   "destination": destination,
                                                   "data": self._Tools.data_pickle(data, data_content_type),
                                                   "data_content_type": data_content_type,
                                                   "status": status,
                                               },
                                               )
        print(f"!!!! NEW node API results: {results}")

        print(f"!!!! NEW node, load_an_item_to_memory")
        results = yield self.load_an_item_to_memory(results["content"]["data"]["attributes"],
                                                    load_source=_load_source,
                                                    request_context="nodes.__init__::new",
                                                    authentication=_authentication
                                                    )
        print(f"!!!! NEW node, load_an_item_to_memory, results: {results}")

        # Todo: ensure node is uploaded to yombo!
        # api_data = {k: v for k, v in bytes_to_unicode(node_data).items() if v}
        # response = yield self._YomboAPI.request("POST", "/v1/node",
        #                                         api_data,
        #                                         authorization_header=authorization)

        return results

    @inlineCallbacks
    def edit_node(self, node_id: str, node_data: dict, source: Optional[str] = None,
                  authorization=None, **kwargs):
        """
        This shouldn't be used by outside calls, instead, to update the node, simply edit
        the node attributes directly. That will cause the node to update the database and Yombo API.

        This is used by other internal libraries to update a node's data in bulk and
        optionally

        :param node_id: Node ID to bulk update.
        :param node_data: Dictionary of items to update
        :param source: Should be: local or remote. Default is local.
        :param kwargs:
        :return:
        """
        if source is None:
            source = "local"

        # print("editing node: %s" % node_id)
        if isinstance(node_data, dict) is False:
            raise YomboWarning("edit_node() only accepts dictionaries for 'node_data' argument.")

        if "data" not in node_data:
            raise YomboWarning("Cannot edit node, 'data' not found")

        global_invoke_all("_node_before_update_",
                          called_by=self,
                          arguments={
                              "node_id": node_id,
                              "node": node_data,
                              "in_memory": node_id in self.nodes,
                              }
                          )

        if source == "local":
            api_data = deepcopy(node_data)
            node_data["data"] = self._Tools.data_pickle(api_data["data"], api_data["data_content_type"])
            # print("new node data: %s" % api_data)
            api_to_send = {k: v for k, v in bytes_to_unicode(api_data).items() if v}

            response = yield self.patch_node(node_id=node_id, api_data=api_to_send, authorization=authorization)

            node_data = response.content["data"]['attributes']

        # Now we have the final data, lets update the local info.
        node_id = node_data["id"]
        if node_id in self.nodes:
            self.nodes[node_id].update(node_data)  # Update existing node data.
            self.nodes[node_id].save_to_db()

        global_invoke_all("_node_updated_",
                          called_by=self,
                          arguments={
                              "node_id": node_id,
                              "node": self.nodes[node_id],
                              }
                          )
        return self.nodes[node_id]

    @inlineCallbacks
    def update_node_status(self, node_id: str, new_status: int, authorization=None):
        """
        Change the node's status from: enabled (1), disabled (0), or deleted (2).

        :param node_id: Node ID to alter.
        :param new_status: 0 for disabled, 1 for enabled, 2 for deleted.
        :return:
        """
        if new_status not in STATUS:
            raise YomboWarning("new_status must be an int: 0, 1, or 2.")

        global_invoke_all(f"_node_before_{STATUS[new_status]}_",
                          called_by=self,
                          arguments={
                              "node_id": node_id,
                              "node": self.nodes[node_id],
                              }
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

        global_invoke_all(f"_node_after_{STATUS[new_status]}_",
                          called_by=self,
                          arguments={
                              "node_id": node_id,
                              "node": self.nodes[node_id],
                              }
                          )
        return response

    @inlineCallbacks
    def delete_node(self, node_id: str, authorization=None):
        """
        Delete a node at the Yombo server level, will try to remove from memory and the database.

        :param node_id: The node ID to delete.
        :param authorization: Authorization token to use if user requested.
        :return:
        """
        response = yield self.update_node_status(node_id, 2, authorization)
        return response

    @inlineCallbacks
    def disable_node(self, node_id: str, authorization=None):
        """
        Disable a node at the Yombo server level, will update locally if loaded.

        :param node_id: The node ID to enable.
        :param authorization: Authorization token to use if user requested.
        :return:
        """
        response = yield self.update_node_status(node_id, 0, authorization)
        return response

    @inlineCallbacks
    def enable_node(self, node_id: str, authorization=None):
        """
        Enable a node at the Yombo server level, will update locally if loaded.

        :param node_id: The node ID to enable.
        :param authorization: Authorization token to use if user requested.
        :return:
        """
        response = yield self.update_node_status(node_id, 1, authorization)
        return response

    @inlineCallbacks
    def patch_node(self, node_id: str, api_data: dict, authorization=None):
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
