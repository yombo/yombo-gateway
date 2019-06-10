"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.lib.localdb import Location


class DB_Locations(object):

    @inlineCallbacks
    def get_locations(self):
        records = yield Location.all()
        return self.process_get_results(records)

    @inlineCallbacks
    def save_locations(self, data):
        """
        Attempts to find the provided location in the database. If it's found, it's updated. Otherwise, a new
        one is created.

        :param data: A location instance.
        :return:
        """
        location = yield Location.find(data.location_id)
        if location is None:  # If none is found, create a new one.
            location = Location()
            location.id = data.location_id

        for field in self.db_fields("locations"):
            setattr(location, field, getattr(data, field))

        yield location.save()

    # @inlineCallbacks
    # def insert_locations(self, data, **kwargs):
    #     location = Location()
    #     location.id = data["id"]
    #     location.location_type = data["location_type"]
    #     location.label = data["label"]
    #     location.machine_label = data["machine_label"]
    #     location.description = data.get("description", None)
    #     location.created_at = data["created_at"]
    #     location.updated_at = data["updated_at"]
    #     yield location.save()
    #
    # @inlineCallbacks
    # def update_locations(self, location, **kwargs):
    #     args = {
    #         "location_type": location.location_type,
    #         "label": location.label,
    #         "machine_label": location.machine_label,
    #         "description": location.description,
    #         "updated_at": location.updated_at,
    #     }
    #     # print("saving notice update_locations: %s" % args)
    #     results = yield self.dbconfig.update("locations", args, where=["id = ?", location.location_id])
    #     return results
    #
    # @inlineCallbacks
    # def delete_locations(self, location_id, **kwargs):
    #     results = yield self.dbconfig.delete("locations", where=["id = ?", location_id])
    #     return results