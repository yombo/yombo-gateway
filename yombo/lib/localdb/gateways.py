# Import python libraries

# Import 3rd-party libs

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks


# Import Yombo libraries
from yombo.lib.localdb import Gateway


class DB_Gateways(object):

    @inlineCallbacks
    def get_gateways(self, status=None):
        if status is True:
            records = yield self.dbconfig.select("gateways")
            return records
        elif status is None:
            records = yield self.dbconfig.select("gateways", where=["status = ? OR status = ?", 1, 0])
            return records
        else:
            records = yield self.dbconfig.select("gateways", where=["status = ?", status])
            return records

    @inlineCallbacks
    def save_gateways(self, data):
        """
        Attempts to find the provided gateway in the database. If it's found, it's updated. Otherwise, a new
        one is created.

        :param data: A gateway instance.
        :return:
        """
        if data.gateway_id in ("local", "cluster"):
            return
        gateway = yield Gateway.find(data.gateway_id)
        if gateway is None:  # If none is found, create a new one.
            gateway = Gateway()
            gateway.id = data.gateway_id

        for field in self.db_fields_gateway():
            setattr(gateway, field, getattr(data, field))

        yield gateway.save()

    @inlineCallbacks
    def delete_gateways(self, gateway_id):
        """
        Deletes a gateway by it's id.

        :param gateway_id: Node id
        :type gateway_id: str
        :return:
        """
        gateway = yield Gateway.find(gateway_id)
        if gateway is not None:
            gateway.delete()
        # results = yield self.dbconfig.delete("gateways", where=["id = ?", gateway_id])
        # return results
