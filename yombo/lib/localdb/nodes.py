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
        records = yield Node.find(where=["destination = ? or always_load = 1", "gw"])
        for record in records:
            record.data = data_unpickle(record.data, record.data_content_type)
        return self.process_get_results(records)

    @inlineCallbacks
    def save_nodes(self, data):
        """
        Attempts to find the provided device state in the database. If it's found, update it. Otherwise, a new
        one is created.

        :param data: A device state instance.
        :return:
        """
        node = yield Node.find(data.node_id)
        if node is None:  # If none is found, create a new one.
            node = Node()
            node.id = data.state_id

        fields = self.get_table_columns("nodes")
        # print(f"device state fields: {fields}")
        # print(f"data: {data.__dict__}")
        # print(f"data: fake data: {data._fake_data}")
        for field in fields:
            if field == "data":
                node.data = data_pickle(data.data, data.data_content_type)
            else:
                setattr(node, field, getattr(data, field))

        yield node.save()

    @inlineCallbacks
    def delete_node(self, node_id):
        """
        Deletes a node by it's id.
        :param node_id: Node id
        :type node_id: str
        :return:
        """
        results = yield self.dbconfig.delete("nodes", where=["id = ?", node_id])
        return results
