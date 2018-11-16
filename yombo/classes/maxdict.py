#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
Allows for creation of a dictionary with a maximum size.

**Usage**:

.. code-block:: python

   from yombo.classes.maxdict import MaxDict

   items = MaxDict(200, {"mom" : "Jane", "dad" : "Joe"}) # Can accept a dictionary to get started.
   items["brother"] = "Jeff"   # add an additional entry.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2015-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import collections

class MaxDict(collections.MutableMapping):
    """
    A size limited dictionary.
    """
    def __init__(self, maxlen, *a, **k):
        """
        Construct a new size limited dictionary.

        :param maxlen: Max length of dictionary.
        :type maxlen: int
        """
        self.maxlen = maxlen
        self.d = dict(*a, **k)
        while len(self) > maxlen:
           self.popitem()

    def __iter__(self):
        return iter(self.d)

    def __len__(self):
        return len(self.d)

    def __getitem__(self, k):
        return self.d[k]

    def __delitem__(self, k):
        del self.d[k]

    def __setitem__(self, k, v):
        if k not in self and len(self) == self.maxlen:
            self.popitem()
        self.d[k] = v

    def __str__(self):
        return self.d.__str__()