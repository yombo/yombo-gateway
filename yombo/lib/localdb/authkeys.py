"""
Authkeys mixing for localdb.

"""
# Import python libraries

# Import 3rd-party libs

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.lib.localdb import AuthKeys
# Import Yombo libraries
from yombo.utils import data_pickle, data_unpickle
from yombo.utils.datatypes import coerce_value


class DB_Authkeys(object):
    @inlineCallbacks
    def get_auth_key(self, auth_id=None):
        if auth_id is None:
            records = yield AuthKeys.all()
            if len(records) == 0:
                return []
            output = []
            for record in records:
                auth_data = data_unpickle(record.auth_data)
                record.roles = data_unpickle(record.roles)
                output.append({
                    'auth_id': record.id,
                    'label': record.label,
                    'description': record.description,
                    'enabled': coerce_value(record.enabled, 'bool'),
                    'auth_data': auth_data,
                    'roles': record.roles,
                    'created_by': record.created_by,
                    'created_by_type': record.created_by_type,
                    'created_at': record.created_at,
                    'last_access_at': record.last_access_at,
                    'updated_at': record.updated_at,
                })
            return output
        else:
            record = yield AuthKeys.find(auth_id, where=['enabled = 1'])
            if record is None:
                raise YomboWarning("No Auth Keys found.")
            auth_data = data_unpickle(record.auth_data)
            record.roles = data_unpickle(record.roles)
            return {
                'auth_id': record.id,
                'label': record.label,
                'description': record.description,
                'enabled': coerce_value(record.enabled, 'bool'),
                'auth_data': auth_data,
                'roles': record.roles,
                'created_by': record.created_by,
                'created_by_type': record.created_by_type,
                'created_at': record.created_at,
                'last_access_at': record.last_access_at,
                'updated_at': record.updated_at,
            }

    @inlineCallbacks
    def save_auth_key(self, auth_key):
        args = {
            'id': auth_key.auth_id,
            'label': auth_key.label,
            'description': auth_key.description,
            'enabled': coerce_value(auth_key.enabled, 'int'),
            'auth_data': data_pickle(auth_key.auth_data),
            'roles': data_pickle(list(auth_key.roles)),
            'created_by': auth_key.created_by,
            'created_by_type': auth_key.created_by_type,
            'created_at': auth_key.created_at,
            'last_access_at': auth_key.last_access_at,
            'updated_at': auth_key.updated_at,
        }
        # print("save_auth_key: %s" % args)
        yield self.dbconfig.insert('auth_keys', args, None, 'OR IGNORE')

    @inlineCallbacks
    def update_auth_key(self, auth_key):
        args = {
            'label': auth_key.label,
            'description': auth_key.description,
            'auth_data': data_pickle(auth_key.auth_data),
            'roles': data_pickle(list(auth_key.roles)),
            'enabled': coerce_value(auth_key.enabled, 'bool'),
            'last_access_at': auth_key.last_access_at,
            'updated_at': auth_key.updated_at,
            }
        yield self.dbconfig.update('auth_keys', args, where=['id = ?', auth_key.auth_id])

    @inlineCallbacks
    def rotate_auth_key(self, old_id, new_id):
        args = {
            'id': new_id,
            }
        yield self.dbconfig.update('auth_keys', args, where=['id = ?', old_id])

    @inlineCallbacks
    def delete_auth_key(self, auth_id):
        yield self.dbconfig.delete('auth_keys', where=['id = ?', auth_id])
