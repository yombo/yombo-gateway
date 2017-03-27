#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
A dictionary that can be access as either an object or dictionary.

**Usage**:

.. code-block:: python

   from yombo.utils.dictobject import DictObject

   items = LookupDict({'mom' : 'Jane', 'dad' : 'Joe'}) # Can accept a dictionary to get started.
   result = items.mom  # Jane
   result = items['mom']  # Jane

Original from: https://github.com/webpy/webpy/blob/master/web/utils.py
Modified for use with Yombo by Mitch

.. moduleauthor:: web.py & Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""

class DictObject(dict):
    """
    A dictionary that can be treated as a dictionary or an object.
    """
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k

    def get(self, key, default=None):
        if key in self:
            return dict.__getitem__(self, key)
        else:
            return default

    def __repr__(self):
        return '<DictObject ' + dict.__repr__(self) + '>'