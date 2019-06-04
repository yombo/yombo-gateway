"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from time import time
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import 3rd-party libs
from yombo.lib.localdb import Users


class DB_Users(object):

    @inlineCallbacks
    def get_users(self):
        records = yield Users.all()
        for record in records:
            record = record.__dict__
        return records

    @inlineCallbacks
    def update_user(self, user):
        """
        Updates the user in the database. This receives a User() instance from the Users library.

        :param user: User instance from the User library.
        :type user: User instance
        :param kwargs:
        :return:
        """
        args = {
            "refresh_token": user.refresh_token,
            "access_token": user.access_token,
        }
        results = yield self.dbconfig.update("users", args, where=["id = ?", user.user_id])
        return results
