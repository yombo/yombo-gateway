"""
A dictionary whose keys are not case sensitive.

**Usage**:

.. code-block:: python

   from yombo.classes.caseinsensitivedict import CaseInsensitiveDict

   items = CaseInsensitiveDict({"mOm" : "Jane", "DaD" : "Joe"}) # Can accept a dictionary to get started.
   result = items["mom"]  # Jane


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.23.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/classes/caseinsensitivedict.html>`_
"""
from typing import Any

class CaseInsensitiveDict(dict):
    """
    A dictionary whose index keys are not case sensitive. Caution: Can't have multiple keys with different casing.
    """
    def __setitem__(self, key: str, value) -> None:
        """Sets the value, however, the key is forced to lowercase."""
        super().__setitem__(key.lower(), value)

    def __getitem__(self, key: str) -> Any:
        """Gets the requested key, but force it to lowercase first"""
        return super().__getitem__(key.lower())
