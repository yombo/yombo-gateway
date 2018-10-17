# Import python libraries

# Import 3rd-party libs

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

from yombo.lib.localdb import Node
# Import Yombo libraries
from yombo.utils import data_pickle, data_unpickle


class DB_Nodes(object):

    @inlineCallbacks
    def get_nodes(self):
        records = yield self.dbconfig.select('nodes', where=['destination = ?', 'gw'])
        for record in records:
            record['data'] = data_unpickle(record['data'], record['data_content_type'])
        return records

    @inlineCallbacks
    def get_node(self, node_id):
        record = yield Node.select(where=['id = ?', node_id], limit=1)
        record['node_id'] = record['id']
        del record['id']
        # attempt to decode the data..
        record['data'] = data_unpickle(record['data'], record['data_content_type'])
        return record
    #
    # @inlineCallbacks
    # def get_node_siblings(self, node):
    #     records = yield Node.select(where=['parent_id = ? and node_type = ?', node.parent_id, node.node_type])
    #     for record in records:
    #         record['data'] = data_unpickle(record['data'], record['data_content_type'])
    #     return records
    #
    # @inlineCallbacks
    # def get_node_children(self, node):
    #     records = yield Node.select(where=['parent_id = ? and node_type = ?', node.id, node.node_type])
    #     for record in records:
    #         record['data'] = data_unpickle(record['data'], record['data_content_type'])
    #     return records

    @inlineCallbacks
    def add_node(self, data, **kwargs):
        node = Node()
        node.id = data.node_id
        node.parent_id = data.parent_id
        node.gateway_id = data.gateway_id
        node.node_type = data.node_type
        node.weight = data.weight
        node.label = data.label
        node.machine_label = data.machine_label
        node.always_load = data.always_load
        node.destination = data.destination
        node.data = data_pickle(data.data, data.data_content_type)
        node.data_content_type = data.data_content_type
        node.status = data.status
        node.updated_at = data.updated_at
        node.created_at = data.created_at
        yield node.save()

    @inlineCallbacks
    def update_node(self, node, **kwargs):
        args = {
            'parent_id': node.parent_id,
            'gateway_id': node.gateway_id,
            'node_type': node.node_type,
            'weight': node.weight,
            'label': node.label,
            'machine_label': node.machine_label,
            'always_load': node.always_load,
            'destination': node.destination,
            'data': data_pickle(node.data, node.data_content_type),
            'data_content_type': node.data_content_type,
            'status': node.status,
            'created_at': node.created_at,
            'updated_at': node.updated_at,
        }
        results = yield self.dbconfig.update('nodes', args, where=['id = ?', node.node_id])
        return results


    @inlineCallbacks
    def delete_node(self, node_id):
        results = yield self.dbconfig.delete('nodes', where=['id = ?', node_id])
        return results
