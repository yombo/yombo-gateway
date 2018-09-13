"""
.. note::

  * For library documentation, see: `Hashids @ Library Documentation <https://yombo.net/docs/libraries/hashids>`_

Manages hashids.  Decodes and encodes.

To encode or decode using the primary hashid:

.. code-block:: python

  hash_int = self._Hashids.decode('abc123')  # decodes this string to an int.
  hash_string = self._Hashids.encode(12)  # encodes this int to a string.


A module can add custom hasher by implementing the hook '_hashids_':

.. code-block:: python


   def _hashids_(self, **kwargs):
       return [{'new_hasher': {
                   'salt': random_string(length=25)
                   'length': 30,
               },
       }]

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
                'salt': self._Configs.get('hashids', 'main', random_string(length=25)),
                'length': '20',
            },
        }
        for key_id, key in self.keys.items():
            key['hasher'] = Hashids(salt=key['salt'], min_length=key['length'])

        hashids = yield global_invoke_libraries('_hashids_', called_by=self)
        for component, hashid_list in hashids.items():
            for hashid, data in hashid_list.items():
                self.keys[hashid] = {
                    'salt': data['salt'],
                    'length': data['length'],
                    'hasher': Hashids(salt=data['salt'], min_length=data['length']),
                }

    @inlineCallbacks
    def _modules_loaded_(self, **kwargs):
        """
        Called after _load_ is called for all the modules.
        """
        hashids = yield global_invoke_modules('_hashids_', called_by=self)
        for component, hashid_list in hashids.items():
            for hashid, data in hashid_list.items():
                self.keys[hashid] = {
                    'salt': data['salt'],
                    'length': data['length'],
                    'hasher': Hashids(salt=data['salt'], min_length=data['length']),
                }

    def _configuration_details_(self, **kwargs):
        return [{'hashids': {
                    'main': {
                        'encrypt': True
                    },
                },
        }]

    def encode(self, hashedid, hasher_name):
        if hasher_name in self.keys:
            return self.keys[hasher_name]['hasher'].encode(hashedid)
        else:
            return self.keys[hasher_name]['hasher'].encode(hashedid)

    def decode(self, id_to_hash, hasher_name):
        if hasher_name in self.keys:
            return self.keys[hasher_name]['hasher'].decode(id_to_hash)
        else:
            return self.keys[hasher_name]['hasher'].decode(id_to_hash)
