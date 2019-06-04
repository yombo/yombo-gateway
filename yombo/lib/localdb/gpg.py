"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libs
from yombo.lib.localdb import GpgKey


class DB_GPG(object):

    @inlineCallbacks
    def delete_gpg_key(self, fingerprint):
        results = yield self.dbconfig.delete("gpg_keys",
                                             where=["fingerprint = ?", fingerprint])
        return results

    @inlineCallbacks
    def get_gpg_key(self, **kwargs):
        if "gwid" in kwargs:
            records = yield self.dbconfig.select(
                "gpg_keys",
                where=["endpoint_type = ? endpoint_id = ?", "gw", kwargs["gwid"]]
            )
        elif "keyid" in kwargs:
            records = yield self.dbconfig.select(
                "gpg_keys",
                where=["keyid = ?", kwargs["keyid"]])
        elif "fingerprint" in kwargs:
            records = yield self.dbconfig.select(
                "gpg_keys",
                where=["fingerprint = ?", kwargs["fingerprint"]])
        else:
            records = yield self.dbconfig.select("gpg_keys")

        keys = {}
        for record in records:
            key = {
                "fullname": record["fullname"],
                "comment": record["comment"],
                "email": record["email"],
                "endpoint_id": record["endpoint_id"],
                "endpoint_type": record["endpoint_type"],
                "fingerprint": record["fingerprint"],
                "keyid": record["keyid"],
                "publickey": record["publickey"],
                "length": record["length"],
                "have_private": record["have_private"],
                "ownertrust": record["ownertrust"],
                "trust": record["trust"],
                "algo": record["algo"],
                "type": record["type"],
                "expires_at": record["expires_at"],
                "created_at": record["created_at"],
            }
            keys[record["fingerprint"]] = key
        return keys

    @inlineCallbacks
    def insert_gpg_key(self, gwkey, **kwargs):
        key = GpgKey()
        key.keyid = gwkey["keyid"]
        key.fullname = gwkey["fullname"]
        key.comment = gwkey["comment"]
        key.email = gwkey["email"]
        key.endpoint_id = gwkey["endpoint_id"]
        key.endpoint_type = gwkey["endpoint_type"]
        key.fingerprint = gwkey["fingerprint"]
        key.publickey = gwkey["publickey"]
        key.length = gwkey["length"]
        key.ownertrust = gwkey["ownertrust"]
        key.trust = gwkey["trust"]
        key.algo = gwkey["algo"]
        key.type = gwkey["type"]
        key.expires_at = gwkey["expires_at"]
        key.created_at = gwkey["created_at"]
        key.have_private = gwkey["have_private"]
        if "notes" in gwkey:
            key.notes = gwkey["notes"]
        yield key.save()
        #        yield self.dbconfig.insert("gpg_keys", args, None, "OR IGNORE" )
