"""
A dictionary that be sliced like a list. This has been combined from the following 2 items:

Source: http://stackoverflow.com/questions/30975339/slicing-a-python-ordereddict
Author: http://stackoverflow.com/users/1307905/anthon

and

Source: http://stackoverflow.com/questions/16664874/how-can-i-add-an-element-at-the-top-of-an-ordereddict-in-python
Author: http://stackoverflow.com/users/846892/ashwini-chaudhary

**Usage**:

.. code-block:: python

   from yombo.classes.sliceableordereddict import SliceableOrderedDict

   items = SliceableOrderedDict({"mom" : "Jane", "dad" : "Joe", "brother": "Sam"}) # Can accept a dictionary to get started.
   result = items[1:2]  # Returns an OrderedDict with Dad in it.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/classes/sliceableordereddict.html>`_
"""
from collections import OrderedDict
from itertools import islice


class SliceableOrderedDict(OrderedDict):
    """
    An OrderedDict that is sliceable like a list or string.
    """
    def __getitem__(self, k):
        if not isinstance(k, slice):
            return OrderedDict.__getitem__(self, k)
        return SliceableOrderedDict(islice(self.items(), k.start, k.stop))

    def prepend(self, key, value):
        """
        Add an element to the front of the dictionary.
        :param key:
        :param value:
        :return:
        """
        self.update({key: value})
        self.move_to_end(key, last=False)
