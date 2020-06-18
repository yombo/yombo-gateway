"""
A dictionary that can be accessed as either an object or dictionary, it's seed is a dictionary.

**Usage**:

.. code-block:: python

   from yombo.classes.dictobject import DictObject

   items = LookupDict({"mom" : "Jane", "dad" : "Joe"}) # Can accept a dictionary to get started.
   result = items.mom  # Jane
   result = items["mom"]  # Jane

Original from: https://github.com/webpy/webpy/blob/master/web/utils.py
Modified for use with Yombo by Mitch

.. moduleauthor:: web.py & Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.23.0

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/classes/dictobject.html>`_
"""
from typing import Any, Optional


class DictObject(dict):
    """
    A dictionary that can be treated as a dictionary or an object.
    """
    def __getattr__(self, key: str) -> Any:
        return self[key]

    def __setattr__(self, key: str, value) -> None:
        self[key] = value

    def __delattr__(self, key: str) -> None:
        try:
            del self[key]
        except KeyError as k:
            raise AttributeError(k)

    def get(self, key: str, default: Optional = None) -> Any:
        if key in self:
            return dict.__getitem__(self, key)
        else:
            return default

    def __repr__(self) -> str:
        return f"<DictObject {dict.__repr__(self)}>"
