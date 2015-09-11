# cython: embedsignature=True
"""
Allows fuzzy key search on dictionary keys, expands on the base dictionary class.

This class is helpful for finding dictionary keys when the key only needs
to be approximate and not exact.

**Usage**:

.. code-block:: python

   from yombo.core.fuzzysearch import FuzzySearch

   items = FuzzySearch({'mom' : 'Jane', 'dad' : 'Joe'}, .95) # Lets be strict, much match 95%
   items['brother'] = 'Jeff'   # add an additional entry.

   momName = ''
   try:
       momName = items['mum']  #this will result in a YomboFuzzySearchError due to our 95% requirement
                               #if we lowered the requirement to 70%, it would find it.
   catch YomboFuzzySearchError, e:  #e contains a bunch of attributes that are useful.
           momName = e.value   #Use the highest value that was found.
   print momName               #this will output Jane

   # We can also specifically call the search function
   momName = items.search('mum', .50)   # Search, but only require 50% match.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
:license: LICENSE for details.
"""


import collections

from yombo.core.log import getLogger
from yombo.core.exceptions import YomboWarning

logger = getLogger('core.fuzzysearch')


class YomboDict(collections.MutableMapping):
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