"""
A dictionary whose keys are not case sensitive.

**Usage**:

.. code-block:: python

   from yombo.classes.caseinsensitivedict import CaseInsensitiveDict

   items = CaseInsensitiveDict({"mOm" : "Jane", "DaD" : "Joe"}) # Can accept a dictionary to get started.
   result = items["mom"]  # Jane


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""


class CaseInsensitiveDict(dict):
    """
    A dictionary whose index keys are not case sensitive. Caution: Can't have multiple keys with different casing.
    """
    def __setitem__(self, key, value):
        super().__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super().__getitem__(key.lower())
