"""
A dictionary that calls a callback whenever a key value changes. This only works on the top level dictionary
and not any nested items.

**Usage**:

.. code-block:: python

   from yombo.classes.triggerdict import TriggerDict

   # Set a callback to be called whenever the dictionary changes.
   items = TriggerDict(200, {"mom" : "Jane", "dad" : "Joe"}, callback=self.some_function)
   items["brother"] = "Jeff"   # add an additional entry.

   # Change the callback method
   items.set_callback(self.anotherfunction)

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.23.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/classes/triggerdict.html>`_
"""
from typing import Callable, Optional, Union


class TriggerDict(dict):
    """
    A simple dictionary that accepts "callback" as a keywork argument that can be used to call
    a function if the dictionary changes.

    The callback can also be changed through the method "set_callback".
    """

    def __init__(self, *args, callback: Optional[Callable] = None, **kwargs):
        self.callback = callback
        dict.__init__(self, *args, **kwargs)

    def __setitem__(self, item: Union[str, int], value):
        super().__setitem__(item, value)
        if self.callback is not None:
            self.callback(item, value)

    def set_callback(self, callback: Callable):
        """
        Change the callback method.
        :param callback: Set/Change the callback method to call if the dictionary changes.
        :return:
        """
        self.callback = callback
