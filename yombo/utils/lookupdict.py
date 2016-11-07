#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
A dictionary that can search by either key or by value.

**Usage**:

.. code-block:: python

   from yombo.utils.lookupdict import LookupDict

   items = LookupDict({'mom' : 'Jane', 'dad' : 'Joe'}) # Can accept a dictionary to get started.
   result = items['mom'] # Jane
   result = items['Jane'] # mom

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""

class LookupDict(dict):
    """
    A size limited dictionary.
    """
    def __init__(self, items=[]):
        """items can be a list of pair_lists or a dictionary"""
        dict.__init__(self, items)

    def get_key(self, value):
        """find the key as a list given a value"""
        if type(value) == type(dict()):
            items = [item[0] for item in self.items() if item[1][value.items()[0][0]] == value.items()[0][1]]
        else:
            items = [item[0] for item in self.items() if item[1] == value]
        return items[0]

    def get_keys(self, value):
        """find the key(s) as a list given a value"""
        return [item[0] for item in self.items() if item[1] == value]

    def get_value(self, key):
        """find the value given a key"""
        return self[key]