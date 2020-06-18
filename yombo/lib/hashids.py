"""
.. note::

  * For library documentation, see: `Hashids @ Library Documentation <https://yombo.net/docs/libraries/hashids>`_

Manages hashids.  Decodes and encodes.

To encode or decode using the primary hashid:

.. code-block:: python

  hash_int = self._HashIDS.decode("abc123")  # decodes this string to an int.
  hash_string = self._HashIDS.encode(12)  # encodes this int to a string.


A module can add custom hasher by implementing the hook "_hashids_":

.. code-block:: python


   def _hashids_(self, **kwargs):
       return [{"new_hasher": {
                   "salt": random_string(length=25)
                   "length": 30,
               },
       }]

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/hashids.html>`_
"""
# Import python libraries
from hashids import Hashids
from typing import List, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
from yombo.utils import random_string
from yombo.utils.hookinvoke import global_invoke_modules, global_invoke_libraries

logger = get_logger("library.hashids")


class HashIDS(YomboLibrary):
    """
    Provides a base API to convert various hashids.
    """
    def _init_(self, **kwargs):
        """Sets up the default hasher."""
        self.keys = {
            "main": {
                "salt": self._Configs.get("hashids.main", random_string(length=25)),
                "length": "20",
            },
        }
        for key_id, key in self.keys.items():
            key["hasher"] = Hashids(salt=key["salt"], min_length=key["length"])

    @inlineCallbacks
    def _start_(self, **kwargs):
        """
        Called after _load_ is called for all the modules.
        """
        hashids = yield global_invoke_modules("_hashids_", called_by=self)
        for component, hashid_list in hashids.items():
            for hashid, data in hashid_list.items():
                self.keys[hashid] = Hashids(salt=data["salt"], min_length=data["length"])

    @inlineCallbacks
    def _modules_imported_(self, **kwargs):
        """
        Just after all the modules are imported (but not started), check if any additional
        hashids should be setup.
        """
        results = yield global_invoke_libraries("_hashids_", called_by=self)
        for component, hashid_list in results.items():
            for hashid, data in hashid_list.items():
                self.keys[hashid] = Hashids(salt=data["salt"], min_length=data["length"])

    def encode(self, hash_name: str, id_to_hash: Union[List[int], int]) -> str:
        """
        A reversible int to string hasher. This can be used to shorten long IDs. This can accept a single
        int or a list of ints.

        :param hash_name: Name of the hash key to use.
        :param id_to_hash: id (int) to hash.
        :return:
        """
        if hash_name not in self.keys:
            hash_name = "main"

        if isinstance(id_to_hash, list) is False:
            id_to_hash = [id_to_hash]

        return self.keys[hash_name].encode(*id_to_hash)

    def decode(self, hash_name: str, hash_to_id: str) -> Union[List[int], int]:
        """
        Reverse a hashed id created by encode. This always returns a list, regardless if their is only one
        value.

        :param hash_name: Name of the hash key to use.
        :param hash_to_id: String to convert to int.
        :return:
        """
        if hash_name not in self.keys:
            hash_name = "main"
        results = self.keys[hash_name].decode(hash_to_id)

        if results is None or len(results) == 0:
            raise YomboWarning(f"Unable to un-hash string: {hash_to_id}")
        return results
