"""
DotDict allows for accessing nested dictionaries using dot notation.

Keys can either be separated by dots (periods) or provided a list. Each element
traverses the nested dictionary.

Based on: https://stackoverflow.com/questions/3797957/python-easily-access-deeply-nested-dict-get-and-set

**Usage**:

.. code-block:: python

   from yombo.classes.dotdict import DotDict

   items = DotDict({"one" : {"once": {"hello": "world"}}}) # Can accept a dictionary to get started.
   result = items["one.once.hello"]  # returns: world
   result = items[["one", "once", "hello"]]  # returns: world


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/classes/dotdict.html>`_
"""
from typing import Any, Union, Optional


class DotDict(dict):
    """
    Extends the dictionary class. Nested dictionaries are also converted to a DotDict to
    ensure compatibility.

    Keys with periods '.' can be used to traverse nested dictionaries.
    """
    def __init__(self, value: Optional[dict] = None):
        if value is None:
            pass
        elif isinstance(value, dict):
            for key in value:
                self.__setitem__(key, value[key])
        else:
            raise TypeError("expected dict")

    def __setitem__(self, key: Union[str, list], value: Any) -> None:
        if isinstance(key, list):
            key = ".".join(key)
        if "." in key:
            my_key, rest_of_key = key.split(".", 1)
            target = self.setdefault(my_key, DotDict())
            if not isinstance(target, DotDict):
                raise KeyError('cannot set "%s" in "%s" (%s)' % (rest_of_key, my_key, repr(target)))
            target[rest_of_key] = value
        else:
            if isinstance(value, dict) and not isinstance(value, DotDict):
                value = DotDict(value)
            dict.__setitem__(self, key, value)

    def __getitem__(self, key: Union[str, list]) -> Any:
        if isinstance(key, list):
            key = ".".join(key)
        if "." not in key:
            return dict.__getitem__(self, key)
        my_key, rest_of_key = key.split(".", 1)
        target = dict.__getitem__(self, my_key)
        if not isinstance(target, DotDict):
            raise KeyError('cannot get "%s" in "%s" (%s)' % (rest_of_key, my_key, repr(target)))
        return target[rest_of_key]

    def __contains__(self, key: Union[str, list]) -> bool:
        if isinstance(key, list):
            key = ".".join(key)
        if "." not in key:
            return dict.__contains__(self, key)
        my_key, rest_of_key = key.split(".", 1)
        try:
            target = dict.__getitem__(self, my_key)
        except KeyError:
            return False
        if not isinstance(target, DotDict):
            return False
        return rest_of_key in target

    def __delitem__(self, key: Union[str, list]) -> None:
        if isinstance(key, list):
            key = ".".join(key)
        if "." not in key:
            return dict.__delitem__(self, key)
        keys = key.split(".")
        children = self.__getitem__(keys[:-1])
        del children[keys[-1]]

    def setdefault(self, key: Union[str, list], default: Any):
        if key not in self:
            self[key] = default
        return self[key]

    __setattr__ = __setitem__
    __getattr__ = __getitem__
