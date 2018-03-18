# doesn't exist on gw
"""
Manages hashids.  Decodes and encodes.


  self._Hashids.decode('something', 'abc123')
  self._Hashids.encode('something', 12)

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2018 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from __future__ import absolute_import
from hashids import Hashids

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
from yombo.utils import random_string
from yombo.utils import global_invoke_modules, global_invoke_libraries

logger = get_logger("library.hashids")


class HashIDS(YomboLibrary, object):
    """
    Provides a base API to convert various hashids.
    """
    @inlineCallbacks
    def _init_(self):
        self.keys = {
            'main': {
                'salt': self._Configs.get('hashids', 'main', random_string(length=20)),
                'length': '20',
            },
        }
        for key_id, key in self.keys.items():
            key['hasher'] = Hashids(salt=key['salt'], min_length=key['length'])

        hashids = yield global_invoke_libraries('_hashids_', called_by=self)
        for component, hashid in hashids.items():
            self.keys[hashid] = {
                'salt': hashids[hashid]['salt'],
                'length': hashids[hashid]['length'],
                'hasher': Hashids(salt=hashids[hashid]['salt'], min_length=hashids[hashid]['length']),
            }

    @inlineCallbacks
    def _modules_loaded_(self, **kwargs):
        """
        Called after _load_ is called for all the modules.
        """
        hashids = yield global_invoke_modules('_hashids_', called_by=self)
        for component, hashid in hashids.items():
            self.keys[hashid] = {
                'salt': hashids[hashid]['salt'],
                'length': hashids[hashid]['length'],
                'hasher': Hashids(salt=hashids[hashid]['salt'], min_length=hashids[hashid]['length']),
            }

    def _configuration_details_(self, **kwargs):
        return [{'hashids': {
                    'main': {
                        'encrypt': True
                    },
                },
        }]

    def encode(self, key, id):
        if key in self.keys:
            return self.keys[key]['hasher'].encode(id)
        else:
            return self.keys['main']['hasher'].encode(id)

    def decode(self, key, id):
        # print("hashids decoding: %s: %s" % (key, id))
        if key in self.keys:
            # print "hashids key found."
            return self.keys[key]['hasher'].decode(id)
        else:
            return self.keys['main']['hasher'].decode(id)
